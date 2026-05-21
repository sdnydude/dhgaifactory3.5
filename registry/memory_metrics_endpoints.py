"""Memory Metrics API endpoints.

Routes:
  POST   /api/memory-metrics   create a memory metrics snapshot
  GET    /api/memory-metrics   list with filters (project, limit, offset)
"""
import os
import sys
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from memory_metrics_schemas import (
    MemoryMetricsCreate,
    MemoryMetricsResponse,
    MemoryMetricsList,
)
import memory_metrics_service as svc

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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))
