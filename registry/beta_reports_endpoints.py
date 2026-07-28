"""Beta Reports API endpoints — beta-tester bug/feedback report capture.

Routes:
  POST   /api/beta-reports               create a beta report
  GET    /api/beta-reports               list with filters (project/status/severity/limit/offset)
  PATCH  /api/beta-reports/{report_id}   update status (and optionally area/severity)
"""
import time
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from beta_reports_schemas import (
    BetaReportCreate,
    BetaReportResponse,
    BetaReportList,
    BetaReportUpdate,
    VALID_SEVERITIES,
    VALID_STATUSES,
)
import beta_reports_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/beta-reports", tags=["beta-reports"])


@router.post("", response_model=BetaReportResponse, status_code=status.HTTP_201_CREATED)
async def create_beta_report(
    payload: BetaReportCreate,
    db: Session = Depends(get_db),
) -> BetaReportResponse:
    start = time.time()
    if payload.severity not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid severity '{payload.severity}'. Valid: {sorted(VALID_SEVERITIES)}",
        )
    try:
        row = svc.create_beta_report(db, payload)

        registry_write_operations.labels(operation="create_beta_report").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_beta_report_failed").inc()
        logger.error("create_beta_report failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=BetaReportList)
async def list_beta_reports(
    project_name: Optional[str] = Query(None),
    report_status: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> BetaReportList:
    start = time.time()
    try:
        rows, total = svc.list_beta_reports(
            db, project_name=project_name, status=report_status,
            severity=severity, limit=limit, offset=offset,
        )

        registry_read_operations.labels(operation="list_beta_reports").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return BetaReportList(beta_reports=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_beta_reports_failed").inc()
        logger.error("list_beta_reports failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{report_id}", response_model=BetaReportResponse)
async def update_beta_report(
    report_id: UUID,
    payload: BetaReportUpdate,
    db: Session = Depends(get_db),
) -> BetaReportResponse:
    start = time.time()
    if payload.status and payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{payload.status}'. Valid: {sorted(VALID_STATUSES)}",
        )
    if payload.severity and payload.severity not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid severity '{payload.severity}'. Valid: {sorted(VALID_SEVERITIES)}",
        )
    try:
        row = svc.update_beta_report(db, report_id, payload)
        if not row:
            raise HTTPException(status_code=404, detail="Beta report not found")

        registry_write_operations.labels(operation="update_beta_report").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="update_beta_report_failed").inc()
        logger.error("update_beta_report failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
