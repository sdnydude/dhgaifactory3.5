"""Test Coverage API endpoints — track test suite changes across the project.

Routes:
  POST   /api/test-coverage              capture a test coverage change event
  GET    /api/test-coverage              list with filters (project/category/limit/offset)
  POST   /api/test-coverage/search       full-text search across test coverage events
  DELETE /api/test-coverage/{item_id}    delete a test coverage record
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
from models import TestCoverage
from test_coverage_schemas import (
    TestCoverageCreate,
    TestCoverageResponse,
    TestCoverageList,
    TestCoverageSearch,
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


router = APIRouter(prefix="/api/test-coverage", tags=["test-coverage"])


def _upsert_test_coverage(
    db: Session, payload: TestCoverageCreate, embedding=None,
) -> tuple[TestCoverage, bool]:
    """Upsert by (project_name, title). Returns (row, created)."""
    existing = db.query(TestCoverage).filter(
        TestCoverage.project_name == payload.project_name,
        TestCoverage.title == payload.title,
    ).first()

    if existing:
        existing.test_count_before = payload.test_count_before
        existing.test_count_after = payload.test_count_after
        existing.delta = payload.delta
        existing.tests_added = payload.tests_added
        existing.tests_removed = payload.tests_removed
        existing.tests_modified = payload.tests_modified
        existing.files_affected = payload.files_affected
        existing.category = payload.category
        existing.trigger = payload.trigger
        existing.tags = payload.tags
        existing.session_id = payload.session_id
        existing.model_name = payload.model_name
        existing.meta_data = payload.meta_data
        if embedding:
            existing.embedding = embedding
            existing.embedding_model = "nomic-embed-text"
        return existing, False

    row = TestCoverage(**payload.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
        return row, True
    except IntegrityError:
        db.rollback()
        existing = db.query(TestCoverage).filter(
            TestCoverage.project_name == payload.project_name,
            TestCoverage.title == payload.title,
        ).first()
        if existing:
            existing.test_count_before = payload.test_count_before
            existing.test_count_after = payload.test_count_after
            existing.delta = payload.delta
            existing.tests_added = payload.tests_added
            existing.tests_removed = payload.tests_removed
            existing.tests_modified = payload.tests_modified
            existing.files_affected = payload.files_affected
            existing.category = payload.category
            existing.trigger = payload.trigger
            existing.tags = payload.tags
            existing.session_id = payload.session_id
            existing.model_name = payload.model_name
            existing.meta_data = payload.meta_data
            if embedding:
                existing.embedding = embedding
                existing.embedding_model = "nomic-embed-text"
            return existing, False
        raise


@router.post("", response_model=TestCoverageResponse, status_code=status.HTTP_201_CREATED)
async def create_test_coverage(
    payload: TestCoverageCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> TestCoverageResponse:
    start = time.time()
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category '{payload.category}'. Valid: {sorted(VALID_CATEGORIES)}",
        )
    try:
        embedding = None
        try:
            from embedding_utils import get_embedding
            text_for_embed = f"{payload.title} {payload.trigger or ''}"
            embedding = await get_embedding(text_for_embed)
        except Exception as embed_err:
            logger.warning("Test coverage embedding failed: %s", embed_err)

        row, created = _upsert_test_coverage(db, payload, embedding)
        db.commit()
        db.refresh(row)

        if not created:
            response.status_code = status.HTTP_200_OK

        registry_write_operations.labels(operation="create_test_coverage").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_test_coverage_failed").inc()
        logger.error("%s failed: %s", "test_coverage_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=TestCoverageList)
async def list_test_coverage(
    project_name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> TestCoverageList:
    start = time.time()
    try:
        query = db.query(TestCoverage)
        if project_name:
            query = query.filter(TestCoverage.project_name == project_name)
        if category:
            query = query.filter(TestCoverage.category == category)

        total = query.count()
        rows = (
            query
            .order_by(TestCoverage.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        registry_read_operations.labels(operation="list_test_coverage").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return TestCoverageList(test_coverage_events=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_test_coverage_failed").inc()
        logger.error("%s failed: %s", "test_coverage_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=TestCoverageList)
async def search_test_coverage(
    body: TestCoverageSearch,
    db: Session = Depends(get_db),
) -> TestCoverageList:
    start = time.time()
    try:
        ts_query = sa_func.plainto_tsquery("english", body.query)
        query = (
            db.query(TestCoverage)
            .filter(TestCoverage.search_vector.op("@@")(ts_query))
        )
        if body.project_name:
            query = query.filter(TestCoverage.project_name == body.project_name)
        if body.category:
            query = query.filter(TestCoverage.category == body.category)

        total = query.count()
        rows = (
            query
            .order_by(sa_func.ts_rank(TestCoverage.search_vector, ts_query).desc())
            .limit(body.limit)
            .all()
        )

        registry_read_operations.labels(operation="search_test_coverage").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return TestCoverageList(test_coverage_events=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="search_test_coverage_failed").inc()
        logger.error("%s failed: %s", "test_coverage_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_coverage(
    item_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        row = db.query(TestCoverage).filter(TestCoverage.id == item_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        db.delete(row)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_test_coverage_failed").inc()
        logger.error("delete_test_coverage failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
