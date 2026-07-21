"""Session Reports API endpoints — narrative end-of-session reports.

Routes:
  POST   /api/session-reports              capture a session report
  GET    /api/session-reports              list with filters (project/category/limit/offset)
  POST   /api/session-reports/search       full-text search across session reports
  DELETE /api/session-reports/{item_id}    delete a session report
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
from session_reports_schemas import (
    SessionReportCreate,
    SessionReportResponse,
    SessionReportList,
    SessionReportSearch,
    VALID_CATEGORIES,
)
import session_reports_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/session-reports", tags=["session-reports"])


@router.post("", response_model=SessionReportResponse, status_code=status.HTTP_201_CREATED)
async def create_session_report(
    payload: SessionReportCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> SessionReportResponse:
    start = time.time()
    if payload.category is not None and payload.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category '{payload.category}'. Valid: {sorted(VALID_CATEGORIES)}",
        )
    try:
        embedding = None
        try:
            from embedding_utils import get_embedding
            text_for_embed = f"{payload.title} {payload.report_md[:4000]}"
            embedding = await get_embedding(text_for_embed)
        except Exception as embed_err:
            logger.warning("Session report embedding failed: %s", embed_err)

        row, created = svc.upsert_session_report(db, payload, embedding)

        if not created:
            response.status_code = status.HTTP_200_OK

        registry_write_operations.labels(operation="create_session_report").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_session_report_failed").inc()
        logger.error("%s failed: %s", "session_reports_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=SessionReportList)
async def list_session_reports(
    project_name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> SessionReportList:
    start = time.time()
    try:
        rows, total = svc.list_session_reports(
            db, project_name=project_name, category=category,
            limit=limit, offset=offset,
        )

        registry_read_operations.labels(operation="list_session_reports").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return SessionReportList(session_reports=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_session_reports_failed").inc()
        logger.error("%s failed: %s", "session_reports_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=SessionReportList)
async def search_session_reports(
    body: SessionReportSearch,
    db: Session = Depends(get_db),
) -> SessionReportList:
    start = time.time()
    try:
        rows, total = svc.search_session_reports(
            db, body.query,
            project_name=body.project_name, category=body.category,
            limit=body.limit,
        )

        registry_read_operations.labels(operation="search_session_reports").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return SessionReportList(session_reports=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="search_session_reports_failed").inc()
        logger.error("%s failed: %s", "session_reports_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session_report(
    item_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        row = svc.delete_session_report(db, item_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_session_report_failed").inc()
        logger.error("delete_session_report failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
