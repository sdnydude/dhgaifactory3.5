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
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from test_coverage_schemas import (
    TestCoverageCreate,
    TestCoverageResponse,
    TestCoverageList,
    TestCoverageSearch,
    VALID_CATEGORIES,
)
import test_coverage_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/test-coverage", tags=["test-coverage"])


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

        row, created = svc.upsert_test_coverage(db, payload, embedding)

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
        rows, total = svc.list_test_coverage(
            db, project_name=project_name, category=category,
            limit=limit, offset=offset,
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
        rows, total = svc.search_test_coverage(
            db, body.query,
            project_name=body.project_name, category=body.category,
            limit=body.limit,
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
        row = svc.delete_test_coverage(db, item_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_test_coverage_failed").inc()
        logger.error("delete_test_coverage failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
