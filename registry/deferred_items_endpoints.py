"""Deferred Items API endpoints — work discovered but intentionally not fixed, logged for later.

Routes:
  POST   /api/deferred-items              capture a deferred item
  GET    /api/deferred-items              list with filters (project/category/priority/status/limit/offset)
  POST   /api/deferred-items/search       full-text search across deferred items
  GET    /api/deferred-items/stats        aggregate stats (status/priority/category/age distributions)
  PATCH  /api/deferred-items/{item_id}    update status/priority with optional resolution reason
  DELETE /api/deferred-items/{item_id}    delete a deferred item record
"""
import time
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from database import get_db
from deferred_items_schemas import (
    DeferredItemCreate,
    DeferredItemResponse,
    DeferredItemList,
    DeferredItemSearch,
    DeferredItemUpdate,
    DeferredItemStatsResponse,
    VALID_PRIORITIES,
    VALID_CATEGORIES,
    VALID_STATUSES,
)
import deferred_items_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/deferred-items", tags=["deferred-items"])


@router.post("", response_model=DeferredItemResponse, status_code=status.HTTP_201_CREATED)
async def create_deferred_item(
    payload: DeferredItemCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> DeferredItemResponse:
    start = time.time()
    if payload.priority not in VALID_PRIORITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid priority '{payload.priority}'. Valid: {sorted(VALID_PRIORITIES)}",
        )
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category '{payload.category}'. Valid: {sorted(VALID_CATEGORIES)}",
        )
    if payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{payload.status}'. Valid: {sorted(VALID_STATUSES)}",
        )
    try:
        embedding = None
        try:
            from embedding_utils import get_embedding
            text_for_embed = f"{payload.title} {payload.description} {payload.reason}"
            embedding = await get_embedding(text_for_embed)
        except Exception as embed_err:
            logger.warning("Deferred item embedding failed: %s", embed_err)

        row, created = svc.upsert_deferred_item(db, payload, embedding)

        if not created:
            response.status_code = status.HTTP_200_OK

        registry_write_operations.labels(operation="create_deferred_item").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_deferred_item_failed").inc()
        logger.error("%s failed: %s", "deferred_items_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=DeferredItemList)
async def list_deferred_items(
    project_name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> DeferredItemList:
    start = time.time()
    try:
        rows, total = svc.list_deferred_items(
            db, project_name=project_name, category=category,
            priority=priority, status_filter=status_filter,
            limit=limit, offset=offset,
        )

        registry_read_operations.labels(operation="list_deferred_items").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return DeferredItemList(deferred_items=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_deferred_items_failed").inc()
        logger.error("%s failed: %s", "deferred_items_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=DeferredItemList)
async def search_deferred_items(
    body: DeferredItemSearch,
    db: Session = Depends(get_db),
) -> DeferredItemList:
    start = time.time()
    try:
        rows, total = svc.search_deferred_items(
            db, body.query,
            project_name=body.project_name, category=body.category,
            priority=body.priority, status_filter=body.status,
            limit=body.limit,
        )

        registry_read_operations.labels(operation="search_deferred_items").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return DeferredItemList(deferred_items=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="search_deferred_items_failed").inc()
        logger.error("%s failed: %s", "deferred_items_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats", response_model=DeferredItemStatsResponse)
async def deferred_item_stats(
    project_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Aggregate stats: status/priority/category distributions, age histogram, stale count."""
    start = time.time()
    try:
        result = svc.deferred_item_stats(db, project_name=project_name)

        registry_read_operations.labels(operation="deferred_item_stats").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return result
    except Exception as e:
        registry_errors.labels(error_type="deferred_item_stats_failed").inc()
        logger.error("%s failed: %s", "deferred_items_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{item_id}", response_model=DeferredItemResponse)
async def update_deferred_item(
    item_id: UUID,
    payload: DeferredItemUpdate,
    db: Session = Depends(get_db),
):
    """Update status/priority with optional resolution reason."""
    start = time.time()
    if payload.status is not None and payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{payload.status}'. Valid: {sorted(VALID_STATUSES)}",
        )
    if payload.priority is not None and payload.priority not in VALID_PRIORITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid priority '{payload.priority}'. Valid: {sorted(VALID_PRIORITIES)}",
        )
    try:
        row = svc.update_deferred_item(db, item_id, payload)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")

        registry_write_operations.labels(operation="update_deferred_item").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="update_deferred_item_failed").inc()
        logger.error("update_deferred_item failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deferred_item(
    item_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        row = svc.delete_deferred_item(db, item_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_deferred_item_failed").inc()
        logger.error("delete_deferred_item failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
