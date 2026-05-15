"""Decision Logs API endpoints.

Routes:
  POST   /api/decision-logs          create a decision log
  GET    /api/decision-logs          list with filters (project_name, domain, limit, offset)
  POST   /api/decision-logs/search   full-text search across decision logs
"""
import os
import sys
import time
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from models import DecisionLog
from decision_logs_schemas import (
    DecisionLogCreate,
    DecisionLogResponse,
    DecisionLogList,
    DecisionLogSearch,
)

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


router = APIRouter(prefix="/api/decision-logs", tags=["decision-logs"])


def _upsert_decision_log(
    db: Session, payload: DecisionLogCreate, embedding=None,
) -> tuple[DecisionLog, bool]:
    """Upsert by (project_name, title). Returns (row, created)."""
    existing = db.query(DecisionLog).filter(
        DecisionLog.project_name == payload.project_name,
        DecisionLog.title == payload.title,
    ).first()

    if existing:
        existing.choice = payload.choice
        existing.alternatives_rejected = payload.alternatives_rejected
        existing.rationale = payload.rationale
        existing.domain = payload.domain
        existing.supersedes = payload.supersedes
        existing.source_file = payload.source_file
        existing.tags = payload.tags
        existing.session_id = payload.session_id
        existing.model_name = payload.model_name
        existing.meta_data = payload.meta_data
        if embedding:
            existing.embedding = embedding
            existing.embedding_model = "nomic-embed-text"
        return existing, False

    row = DecisionLog(**payload.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
        return row, True
    except IntegrityError:
        db.rollback()
        existing = db.query(DecisionLog).filter(
            DecisionLog.project_name == payload.project_name,
            DecisionLog.title == payload.title,
        ).first()
        if existing:
            existing.choice = payload.choice
            existing.alternatives_rejected = payload.alternatives_rejected
            existing.rationale = payload.rationale
            existing.domain = payload.domain
            existing.supersedes = payload.supersedes
            existing.source_file = payload.source_file
            existing.tags = payload.tags
            existing.session_id = payload.session_id
            existing.model_name = payload.model_name
            existing.meta_data = payload.meta_data
            if embedding:
                existing.embedding = embedding
                existing.embedding_model = "nomic-embed-text"
            return existing, False
        raise


@router.post("", response_model=DecisionLogResponse, status_code=status.HTTP_201_CREATED)
async def create_decision_log(
    payload: DecisionLogCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> DecisionLogResponse:
    start = time.time()
    try:
        embedding = None
        try:
            from embedding_utils import get_embedding
            text_for_embed = f"{payload.title} {payload.choice} {payload.rationale}"
            embedding = await get_embedding(text_for_embed)
        except Exception as embed_err:
            logger.warning("Embedding generation failed: %s", embed_err)

        row, created = _upsert_decision_log(db, payload, embedding)
        db.commit()
        db.refresh(row)

        if not created:
            response.status_code = status.HTTP_200_OK

        registry_write_operations.labels(operation="create_decision_log").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_decision_log_failed").inc()
        logger.error("create_decision_log failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=DecisionLogList)
async def list_decision_logs(
    project_name: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> DecisionLogList:
    start = time.time()
    try:
        query = db.query(DecisionLog)
        if project_name:
            query = query.filter(DecisionLog.project_name == project_name)
        if domain:
            query = query.filter(DecisionLog.domain == domain)

        total = query.count()
        rows = (
            query
            .order_by(DecisionLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        registry_read_operations.labels(operation="list_decision_logs").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return DecisionLogList(decision_logs=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_decision_logs_failed").inc()
        logger.error("%s failed: %s", "decision_logs_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=DecisionLogList)
async def search_decision_logs(
    body: DecisionLogSearch,
    db: Session = Depends(get_db),
) -> DecisionLogList:
    start = time.time()
    try:
        ts_query = sa_func.plainto_tsquery("english", body.query)
        query = (
            db.query(DecisionLog)
            .filter(DecisionLog.search_vector.op("@@")(ts_query))
        )
        if body.project_name:
            query = query.filter(DecisionLog.project_name == body.project_name)
        if body.domain:
            query = query.filter(DecisionLog.domain == body.domain)

        total = query.count()
        rows = (
            query
            .order_by(sa_func.ts_rank(DecisionLog.search_vector, ts_query).desc())
            .limit(body.limit)
            .all()
        )

        registry_read_operations.labels(operation="search_decision_logs").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return DecisionLogList(decision_logs=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="search_decision_logs_failed").inc()
        logger.error("%s failed: %s", "decision_logs_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_decision_log(
    item_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        row = db.query(DecisionLog).filter(DecisionLog.id == item_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        db.delete(row)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_decision_log_failed").inc()
        logger.error("delete_decision_log failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
