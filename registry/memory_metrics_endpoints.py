"""Memory Metrics API endpoints.

Routes:
  POST   /api/memory-metrics   create a memory metrics snapshot
  GET    /api/memory-metrics   list with filters (project, limit, offset)
"""
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from memory_metrics_schemas import (
    MemoryMetricsCreate,
    MemoryMetricsResponse,
    MemoryMetricsList,
)
import memory_metrics_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/memory-metrics", tags=["memory-metrics"])


@router.post("", response_model=MemoryMetricsResponse, status_code=status.HTTP_201_CREATED)
async def create_memory_metrics(
    payload: MemoryMetricsCreate,
    db: Session = Depends(get_db),
) -> MemoryMetricsResponse:
    start = time.time()
    try:
        row = svc.create_memory_metrics(db, payload)

        registry_write_operations.labels(operation="create_memory_metrics").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_memory_metrics_failed").inc()
        logger.exception("create_memory_metrics failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=MemoryMetricsList)
async def list_memory_metrics(
    project: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> MemoryMetricsList:
    start = time.time()
    try:
        rows, total = svc.list_memory_metrics(
            db, project=project, limit=limit, offset=offset,
        )

        registry_read_operations.labels(operation="list_memory_metrics").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return MemoryMetricsList(metrics=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_memory_metrics_failed").inc()
        logger.exception("list_memory_metrics failed")
        raise HTTPException(status_code=500, detail="Internal server error")
