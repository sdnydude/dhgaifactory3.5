"""CME stats endpoints — aggregate telemetry for Mission Control dashboard."""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from metrics import registry_errors, registry_read_latency, registry_read_operations
import cme_stats_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cme/stats", tags=["cme-stats"])


@router.get("/pipeline")
async def pipeline_stats(db: Session = Depends(get_db)):
    start = time.time()
    try:
        data = svc.get_pipeline_stats(db)
        registry_read_operations.labels(operation="cme_pipeline_stats").inc()
        return data
    except Exception:
        registry_errors.labels(error_type="cme_pipeline_stats_failed").inc()
        logger.exception("GET /api/cme/stats/pipeline failed")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        registry_read_latency.observe((time.time() - start) * 1000)


@router.get("/services")
async def service_health(db: Session = Depends(get_db)):
    start = time.time()
    try:
        data = svc.get_service_health(db)
        registry_read_operations.labels(operation="cme_service_health").inc()
        return data
    except Exception:
        registry_errors.labels(error_type="cme_service_health_failed").inc()
        logger.exception("GET /api/cme/stats/services failed")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        registry_read_latency.observe((time.time() - start) * 1000)
