"""Assets API endpoints — design/media asset catalog capture.

Routes:
  POST   /api/assets            capture one asset (upsert by project_name + sha256)
  POST   /api/assets/bulk       bulk upsert a batch of assets
  GET    /api/assets            list with filters (project/category/source_drive/design_system)
  POST   /api/assets/search     full-text search across assets
  GET    /api/assets/{item_id}  fetch one
  DELETE /api/assets/{item_id}  delete one
"""
import time
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from database import get_db
from assets_schemas import (
    AssetCreate,
    AssetResponse,
    AssetList,
    AssetBulkIngest,
    AssetSearch,
    VALID_CATEGORIES,
)
import assets_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/assets", tags=["assets"])


def _validate_category(cat: Optional[str]) -> None:
    if cat is not None and cat not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category '{cat}'. Valid: {sorted(VALID_CATEGORIES)}",
        )


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    payload: AssetCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> AssetResponse:
    start = time.time()
    _validate_category(payload.category)
    try:
        row, created = svc.upsert_asset(db, payload)
        if not created:
            response.status_code = status.HTTP_200_OK
        registry_write_operations.labels(operation="create_asset").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_asset_failed").inc()
        logger.error("create_asset failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/bulk", response_model=dict, status_code=status.HTTP_200_OK)
async def bulk_ingest_assets(
    payload: AssetBulkIngest,
    db: Session = Depends(get_db),
) -> dict:
    """Bulk upsert a batch of assets (idempotent by project_name + sha256)."""
    start = time.time()
    for a in payload.assets:
        _validate_category(a.category)
    try:
        created, updated = svc.bulk_upsert(db, payload.project_name, payload.assets)
        registry_write_operations.labels(operation="bulk_ingest_assets").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return {
            "created": created,
            "updated": updated,
            "total": created + updated,
            "project_name": payload.project_name,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="bulk_ingest_assets_failed").inc()
        logger.error("bulk_ingest_assets failed: %s", e)
        raise HTTPException(status_code=500, detail="Bulk ingest failed")


@router.get("", response_model=AssetList)
async def list_assets_ep(
    project_name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    source_drive: Optional[str] = Query(None),
    design_system: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> AssetList:
    start = time.time()
    try:
        rows, total = svc.list_assets(
            db, project_name=project_name, category=category,
            source_drive=source_drive, design_system=design_system,
            limit=limit, offset=offset,
        )
        registry_read_operations.labels(operation="list_assets").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return AssetList(assets=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_assets_failed").inc()
        logger.error("list_assets failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=AssetList)
async def search_assets_ep(
    body: AssetSearch,
    db: Session = Depends(get_db),
) -> AssetList:
    start = time.time()
    try:
        rows, total = svc.search_assets(
            db, body.query, project_name=body.project_name,
            category=body.category, limit=body.limit,
        )
        registry_read_operations.labels(operation="search_assets").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return AssetList(assets=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="search_assets_failed").inc()
        logger.error("search_assets failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{item_id}", response_model=AssetResponse)
async def get_asset_ep(
    item_id: UUID,
    db: Session = Depends(get_db),
) -> AssetResponse:
    row = svc.get_asset(db, item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return row


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset_ep(
    item_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        row = svc.delete_asset(db, item_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_asset_failed").inc()
        logger.error("delete_asset failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
