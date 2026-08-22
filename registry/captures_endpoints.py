"""Captures lookup endpoint.

Routes:
  GET /api/captures/lookup   landing verification by pipeline + project + natural key

Read-open by design, matching the registry's existing read posture (list and
search endpoints on every capture table already return full row content
without auth). Consumer: capture-guarantee Stop hook landing-diff (P2).
"""
import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
import captures_service as svc
from metrics import (
    registry_errors,
    registry_read_latency,
    registry_read_operations,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/captures", tags=["captures"])


class CaptureLookupResponse(BaseModel):
    found: bool
    pipeline: str
    id: UUID


@router.get("/lookup", response_model=CaptureLookupResponse)
async def lookup_capture(
    pipeline: str = Query(...),
    project: str = Query(..., min_length=1),
    key: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> CaptureLookupResponse:
    start = time.time()
    if pipeline not in svc.PIPELINES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown pipeline; valid: {sorted(svc.PIPELINES)}",
        )
    try:
        row = svc.lookup_capture(db, pipeline, project, key)
        registry_read_operations.labels(operation="lookup_capture").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
    except Exception as e:
        registry_errors.labels(error_type="lookup_capture_failed").inc()
        logger.error("lookup_capture failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
    if row is None:
        raise HTTPException(status_code=404, detail="Capture not found")
    return CaptureLookupResponse(found=True, pipeline=pipeline, id=row.id)
