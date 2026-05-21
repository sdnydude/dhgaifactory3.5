"""Memory Metrics service layer — all database operations for memory_metrics."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from models import MemoryMetrics
from memory_metrics_schemas import MemoryMetricsCreate

logger = logging.getLogger(__name__)


def create_memory_metrics(
    db: Session, payload: MemoryMetricsCreate,
) -> MemoryMetrics:
    """Create a new memory metrics snapshot."""
    row = MemoryMetrics(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_memory_metrics(
    db: Session,
    *,
    project: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> tuple[list[MemoryMetrics], int]:
    query = db.query(MemoryMetrics)
    if project:
        query = query.filter(MemoryMetrics.project == project)

    total = query.count()
    rows = (
        query
        .order_by(MemoryMetrics.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total
