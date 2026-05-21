"""Bug Fixes API endpoints — structured root-cause analysis capture.

Routes:
  POST   /api/bug-fixes              capture a bug fix
  GET    /api/bug-fixes              list with filters (project/category/severity/limit/offset)
  POST   /api/bug-fixes/search       full-text search across bug fixes
  DELETE /api/bug-fixes/{item_id}    delete a bug fix record
"""
import time
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from database import get_db
from bug_fixes_schemas import (
    BugFixCreate,
    BugFixResponse,
    BugFixList,
    BugFixSearch,
    VALID_SEVERITIES,
    VALID_CATEGORIES,
)
import bug_fixes_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/bug-fixes", tags=["bug-fixes"])


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

        row, created = svc.upsert_bug_fix(db, payload, embedding)

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
        rows, total = svc.list_bug_fixes(
            db, project_name=project_name, category=category,
            severity=severity, limit=limit, offset=offset,
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
        rows, total = svc.search_bug_fixes(
            db, body.query,
            project_name=body.project_name, category=body.category,
            severity=body.severity, limit=body.limit,
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
        row = svc.delete_bug_fix(db, item_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_bug_fix_failed").inc()
        logger.error("delete_bug_fix failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
