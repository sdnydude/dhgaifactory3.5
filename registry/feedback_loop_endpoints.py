"""Feedback Loop API — unified pipeline health across all 7 memreg capture types.

Routes:
  GET /api/feedback-loop/health   pipeline status + per-type event counts (7d)
"""
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
import feedback_loop_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_errors,
)

router = APIRouter(prefix="/api/feedback-loop", tags=["feedback-loop"])


@router.get("/health")
async def feedback_loop_health(
    project_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Unified pipeline health: per-type counts (7d), last capture, overall status."""
    start = time.time()
    try:
        result = svc.feedback_loop_health(db, project_name=project_name)

        registry_read_operations.labels(operation="feedback_loop_health").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return result
    except Exception as e:
        registry_errors.labels(error_type="feedback_loop_health_failed").inc()
        logger.error("feedback_loop_health failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
