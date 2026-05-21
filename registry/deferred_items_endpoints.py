"""Deferred Items API endpoints — work discovered but intentionally not fixed, logged for later.

Routes:
  POST   /api/deferred-items              capture a deferred item
  GET    /api/deferred-items              list with filters (project/category/priority/status/limit/offset)
  POST   /api/deferred-items/search       full-text search across deferred items
  DELETE /api/deferred-items/{item_id}    delete a deferred item record
"""
import os
import sys
import time
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from models import DeferredItem
from deferred_items_schemas import (
    DeferredItemCreate,
    DeferredItemResponse,
    DeferredItemList,
    DeferredItemSearch,
    VALID_PRIORITIES,
    VALID_CATEGORIES,
    VALID_STATUSES,
)

logger = logging.getLogger(__name__)

try:
    from api import (
        registry_read_latency,
        registry_read_operations,
        registry_write_latency,
        registry_write_operations,
        registry_errors,
    )
except ImportError:
    from prometheus_client import Counter, Histogram
    registry_read_latency = Histogram(
        "registry_read_latency", "Read latency",
        buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
    )
    registry_read_operations = Counter(
        "registry_read_operations", "Read operations", ["operation"],
    )
    registry_write_latency = Histogram(
        "registry_write_latency", "Write latency",
        buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
    )
    registry_write_operations = Counter(
        "registry_write_operations", "Write operations", ["operation"],
    )
    registry_errors = Counter(
        "registry_errors", "Registry errors", ["error_type"],
    )


router = APIRouter(prefix="/api/deferred-items", tags=["deferred-items"])


def _upsert_deferred_item(
    db: Session, payload: DeferredItemCreate, embedding=None,
) -> tuple[DeferredItem, bool]:
    """Upsert by (project_name, title). Returns (row, created)."""
    existing = db.query(DeferredItem).filter(
        DeferredItem.project_name == payload.project_name,
        DeferredItem.title == payload.title,
    ).first()

    if existing:
        existing.description = payload.description
        existing.reason = payload.reason
        existing.source_context = payload.source_context
        existing.priority = payload.priority
        existing.category = payload.category
        existing.status = payload.status
        existing.affected_files = payload.affected_files
        existing.tags = payload.tags
        existing.session_id = payload.session_id
        existing.model_name = payload.model_name
        existing.meta_data = payload.meta_data
        if embedding:
            existing.embedding = embedding
            existing.embedding_model = "nomic-embed-text"
        return existing, False

    row = DeferredItem(**payload.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
        return row, True
    except IntegrityError:
        db.rollback()
        existing = db.query(DeferredItem).filter(
            DeferredItem.project_name == payload.project_name,
            DeferredItem.title == payload.title,
        ).first()
        if existing:
            existing.description = payload.description
            existing.reason = payload.reason
            existing.source_context = payload.source_context
            existing.priority = payload.priority
            existing.category = payload.category
            existing.status = payload.status
            existing.affected_files = payload.affected_files
            existing.tags = payload.tags
            existing.session_id = payload.session_id
            existing.model_name = payload.model_name
            existing.meta_data = payload.meta_data
            if embedding:
                existing.embedding = embedding
                existing.embedding_model = "nomic-embed-text"
            return existing, False
        raise HTTPException(status_code=409, detail="Conflict: duplicate record")


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

        row, created = _upsert_deferred_item(db, payload, embedding)
        db.commit()
        db.refresh(row)

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
        query = db.query(DeferredItem)
        if project_name:
            query = query.filter(DeferredItem.project_name == project_name)
        if category:
            query = query.filter(DeferredItem.category == category)
        if priority:
            query = query.filter(DeferredItem.priority == priority)
        if status_filter:
            query = query.filter(DeferredItem.status == status_filter)

        total = query.count()
        rows = (
            query
            .order_by(DeferredItem.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
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
        ts_query = sa_func.plainto_tsquery("english", body.query)
        query = (
            db.query(DeferredItem)
            .filter(DeferredItem.search_vector.op("@@")(ts_query))
        )
        if body.project_name:
            query = query.filter(DeferredItem.project_name == body.project_name)
        if body.category:
            query = query.filter(DeferredItem.category == body.category)
        if body.priority:
            query = query.filter(DeferredItem.priority == body.priority)
        if body.status:
            query = query.filter(DeferredItem.status == body.status)

        total = query.count()
        rows = (
            query
            .order_by(sa_func.ts_rank(DeferredItem.search_vector, ts_query).desc())
            .limit(body.limit)
            .all()
        )

        registry_read_operations.labels(operation="search_deferred_items").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return DeferredItemList(deferred_items=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="search_deferred_items_failed").inc()
        logger.error("%s failed: %s", "deferred_items_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deferred_item(
    item_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        row = db.query(DeferredItem).filter(DeferredItem.id == item_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        db.delete(row)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_deferred_item_failed").inc()
        logger.error("delete_deferred_item failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
