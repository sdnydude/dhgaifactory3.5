"""Bug Fixes API endpoints — structured root-cause analysis capture.

Routes:
  POST   /api/bug-fixes              capture a bug fix
  GET    /api/bug-fixes              list with filters (project/category/severity/limit/offset)
  POST   /api/bug-fixes/search       full-text search across bug fixes
  DELETE /api/bug-fixes/{item_id}    delete a bug fix record
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
from models import BugFix
from bug_fixes_schemas import (
    BugFixCreate,
    BugFixResponse,
    BugFixList,
    BugFixSearch,
    VALID_SEVERITIES,
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


router = APIRouter(prefix="/api/bug-fixes", tags=["bug-fixes"])


def _upsert_bug_fix(
    db: Session, payload: BugFixCreate, embedding=None,
) -> tuple[BugFix, bool]:
    """Upsert by (project_name, tldr). Returns (row, created)."""
    existing = db.query(BugFix).filter(
        BugFix.project_name == payload.project_name,
        BugFix.tldr == payload.tldr,
    ).first()

    if existing:
        existing.symptom = payload.symptom
        existing.root_cause = payload.root_cause
        existing.fix_applied = payload.fix_applied
        existing.files_affected = payload.files_affected
        existing.severity = payload.severity
        existing.category = payload.category
        existing.source_file = payload.source_file
        existing.tags = payload.tags
        existing.session_id = payload.session_id
        existing.model_name = payload.model_name
        existing.meta_data = payload.meta_data
        if embedding:
            existing.embedding = embedding
            existing.embedding_model = "nomic-embed-text"
        return existing, False

    row = BugFix(**payload.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
        return row, True
    except IntegrityError:
        db.rollback()
        existing = db.query(BugFix).filter(
            BugFix.project_name == payload.project_name,
            BugFix.tldr == payload.tldr,
        ).first()
        if existing:
            existing.symptom = payload.symptom
            existing.root_cause = payload.root_cause
            existing.fix_applied = payload.fix_applied
            existing.files_affected = payload.files_affected
            existing.severity = payload.severity
            existing.category = payload.category
            existing.source_file = payload.source_file
            existing.tags = payload.tags
            existing.session_id = payload.session_id
            existing.model_name = payload.model_name
            existing.meta_data = payload.meta_data
            if embedding:
                existing.embedding = embedding
                existing.embedding_model = "nomic-embed-text"
            return existing, False
        raise


@router.post("", response_model=BugFixResponse, status_code=status.HTTP_201_CREATED)
async def create_bug_fix(
    payload: BugFixCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> BugFixResponse:
    start = time.time()
    if payload.severity not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid severity '{payload.severity}'. Valid: {sorted(VALID_SEVERITIES)}",
        )
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category '{payload.category}'. Valid: {sorted(VALID_CATEGORIES)}",
        )
    try:
        embedding = None
        try:
            from embedding_utils import get_embedding
            text_for_embed = f"{payload.tldr} {payload.symptom} {payload.root_cause} {payload.fix_applied}"
            embedding = await get_embedding(text_for_embed)
        except Exception as embed_err:
            logger.warning("Bug fix embedding failed: %s", embed_err)

        row, created = _upsert_bug_fix(db, payload, embedding)
        db.commit()
        db.refresh(row)

        if not created:
            response.status_code = status.HTTP_200_OK

        registry_write_operations.labels(operation="create_bug_fix").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_bug_fix_failed").inc()
        logger.error("%s failed: %s", "bug_fixes_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=BugFixList)
async def list_bug_fixes(
    project_name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> BugFixList:
    start = time.time()
    try:
        query = db.query(BugFix)
        if project_name:
            query = query.filter(BugFix.project_name == project_name)
        if category:
            query = query.filter(BugFix.category == category)
        if severity:
            query = query.filter(BugFix.severity == severity)

        total = query.count()
        rows = (
            query
            .order_by(BugFix.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        registry_read_operations.labels(operation="list_bug_fixes").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return BugFixList(bug_fixes=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_bug_fixes_failed").inc()
        logger.error("%s failed: %s", "bug_fixes_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=BugFixList)
async def search_bug_fixes(
    body: BugFixSearch,
    db: Session = Depends(get_db),
) -> BugFixList:
    start = time.time()
    try:
        ts_query = sa_func.plainto_tsquery("english", body.query)
        query = (
            db.query(BugFix)
            .filter(BugFix.search_vector.op("@@")(ts_query))
        )
        if body.project_name:
            query = query.filter(BugFix.project_name == body.project_name)
        if body.category:
            query = query.filter(BugFix.category == body.category)
        if body.severity:
            query = query.filter(BugFix.severity == body.severity)

        total = query.count()
        rows = (
            query
            .order_by(sa_func.ts_rank(BugFix.search_vector, ts_query).desc())
            .limit(body.limit)
            .all()
        )

        registry_read_operations.labels(operation="search_bug_fixes").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return BugFixList(bug_fixes=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="search_bug_fixes_failed").inc()
        logger.error("%s failed: %s", "bug_fixes_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bug_fix(
    item_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        row = db.query(BugFix).filter(BugFix.id == item_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        db.delete(row)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_bug_fix_failed").inc()
        logger.error("delete_bug_fix failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
