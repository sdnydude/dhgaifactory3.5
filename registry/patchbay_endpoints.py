"""Patchbay status API endpoint.

Route:
  GET /api/patchbay/status   TCP liveness of the docs-hub service map (cached)
"""
import logging
import time

from fastapi import APIRouter, HTTPException

import patchbay_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_errors,
)

router = APIRouter(prefix="/api/patchbay", tags=["patchbay"])


@router.get("/status")
async def patchbay_status() -> dict:
    """Return {services: {key: "up"|"down"}, checked_at} for the homepage LEDs."""
    start = time.time()
    try:
        result = await svc.get_status()
        registry_read_operations.labels(operation="patchbay_status").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return result
    except Exception as e:
        logger.error("patchbay_status failed: %s", e)
        registry_errors.labels(error_type="patchbay_status_failed").inc()
        raise HTTPException(status_code=500, detail="Status probe failed")
