"""Corrections API endpoints — Loop 4 self-training data.

Routes:
  POST   /api/corrections              capture a user correction
  GET    /api/corrections              list with filters (project/category/since)
  POST   /api/corrections/search       FTS + vector RRF search
  GET    /api/corrections/stats        aggregate counts by category for briefing

The corrections table captures user pushback patterns so Claude can learn
what behaviors to avoid. Queryable via the unified KB search endpoint and
surfaced in SessionStart briefing Section 8.
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from embedding_utils import get_embedding
from models import Correction
from corrections_schemas import (
    CorrectionCreate,
    CorrectionResponse,
    CorrectionList,
    CorrectionSearch,
    VALID_CATEGORIES,
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


router = APIRouter(prefix="/api/corrections", tags=["corrections"])


@router.post("", response_model=CorrectionResponse, status_code=201)
async def create_correction(
    payload: CorrectionCreate,
    db: Session = Depends(get_db),
):
    start = time.time()
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category '{payload.category}'. Valid: {sorted(VALID_CATEGORIES)}",
        )
    try:
        row = Correction(**payload.model_dump())
        try:
            embed_text = f"{payload.category} {payload.user_message} {payload.context or ''}"
            embedding = await get_embedding(embed_text)
            if embedding:
                row.embedding = embedding
                row.embedding_model = "nomic-embed-text"
        except Exception as embed_err:
            logger.warning("Correction embedding failed: %s", embed_err)

        db.add(row)
        db.commit()
        db.refresh(row)

        registry_write_operations.labels(operation="create_correction").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_correction_failed").inc()
        raise HTTPException(status_code=500, detail=str(e))


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
        q = db.query(Correction)
        if project_name:
            q = q.filter(Correction.project_name == project_name)
        if category:
            q = q.filter(Correction.category == category)
        if since_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
            q = q.filter(Correction.created_at >= cutoff)

        total = q.count()
        rows = q.order_by(Correction.created_at.desc()).offset(offset).limit(limit).all()

        registry_read_operations.labels(operation="list_corrections").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return CorrectionList(corrections=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_corrections_failed").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=CorrectionList)
async def search_corrections(
    body: CorrectionSearch,
    db: Session = Depends(get_db),
):
    start = time.time()
    try:
        ts_query = sa_func.plainto_tsquery("english", body.query)
        q = db.query(Correction).filter(Correction.search_vector.op("@@")(ts_query))
        if body.project_name:
            q = q.filter(Correction.project_name == body.project_name)
        if body.category:
            q = q.filter(Correction.category == body.category)

        total = q.count()
        rows = (
            q.order_by(sa_func.ts_rank(Correction.search_vector, ts_query).desc())
            .limit(body.limit)
            .all()
        )

        registry_read_operations.labels(operation="search_corrections").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return CorrectionList(corrections=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="search_corrections_failed").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def correction_stats(
    project_name: Optional[str] = Query(None),
    since_days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Aggregate stats for briefing — total + per-category counts in last N days."""
    start = time.time()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
        q = db.query(
            Correction.category,
            sa_func.count(Correction.id).label("count"),
        ).filter(Correction.created_at >= cutoff)
        if project_name:
            q = q.filter(Correction.project_name == project_name)

        rows = q.group_by(Correction.category).order_by(sa_func.count(Correction.id).desc()).all()
        by_category = [{"category": r.category, "count": r.count} for r in rows]
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
        raise HTTPException(status_code=500, detail=str(e))
