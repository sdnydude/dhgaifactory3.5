"""Corrections API endpoints — Loop 4 self-training data.

Routes:
  POST   /api/corrections              capture a user correction
  GET    /api/corrections              list with filters (project/category/since)
  POST   /api/corrections/search       FTS + vector RRF search
  GET    /api/corrections/stats        aggregate counts by category for briefing
  DELETE /api/corrections/{item_id}    delete a correction

The corrections table captures user pushback patterns so Claude can learn
what behaviors to avoid. Queryable via the unified KB search endpoint and
surfaced in SessionStart briefing Section 8.
"""
import os
import sys
import time
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from corrections_schemas import (
    CorrectionCreate,
    CorrectionResponse,
    CorrectionList,
    CorrectionSearch,
    VALID_CATEGORIES,
)
import corrections_service as svc

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


router = APIRouter(prefix="/api/corrections", tags=["corrections"])


@router.post("", response_model=CorrectionResponse, status_code=201)
async def create_correction(
    payload: CorrectionCreate,
    response: Response,
    db: Session = Depends(get_db),
):
    start = time.time()
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category '{payload.category}'. Valid: {sorted(VALID_CATEGORIES)}",
        )
    try:
        upsert_hash = svc.compute_upsert_hash(payload.user_message)

        embedding = None
        try:
            from embedding_utils import get_embedding
            embed_text = f"{payload.category} {payload.user_message} {payload.context or ''}"
            embedding = await get_embedding(embed_text)
        except Exception as embed_err:
            logger.warning("Correction embedding failed: %s", embed_err)

        row, created = svc.upsert_correction(db, payload, upsert_hash, embedding)

        if not created:
            response.status_code = 200

        registry_write_operations.labels(operation="create_correction").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_correction_failed").inc()
        logger.error("%s failed: %s", "corrections_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=CorrectionList)
async def list_corrections(
    project_name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    since_days: Optional[int] = Query(None, ge=1, le=365,
                                      description="Filter to corrections in last N days"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    start = time.time()
    try:
        rows, total = svc.list_corrections(
            db, project_name=project_name, category=category,
            since_days=since_days, limit=limit, offset=offset,
        )

        registry_read_operations.labels(operation="list_corrections").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return CorrectionList(corrections=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_corrections_failed").inc()
        logger.error("%s failed: %s", "corrections_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=CorrectionList)
async def search_corrections(
    body: CorrectionSearch,
    db: Session = Depends(get_db),
):
    start = time.time()
    try:
        rows, total = svc.search_corrections(
            db, body.query,
            project_name=body.project_name, category=body.category,
            limit=body.limit,
        )

        registry_read_operations.labels(operation="search_corrections").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return CorrectionList(corrections=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="search_corrections_failed").inc()
        logger.error("%s failed: %s", "corrections_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def correction_stats(
    project_name: Optional[str] = Query(None),
    since_days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Aggregate stats for briefing — total + per-category counts in last N days."""
    start = time.time()
    try:
        by_category = svc.correction_stats(
            db, project_name=project_name, since_days=since_days,
        )
        total = sum(r["count"] for r in by_category)

        registry_read_operations.labels(operation="correction_stats").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return {
            "since_days": since_days,
            "project_name": project_name,
            "total": total,
            "by_category": by_category,
        }
    except Exception as e:
        registry_errors.labels(error_type="correction_stats_failed").inc()
        logger.error("%s failed: %s", "corrections_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{item_id}", status_code=204)
async def delete_correction(
    item_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        row = svc.delete_correction(db, item_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_correction_failed").inc()
        logger.error("delete_correction failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
