"""Ship Sessions API endpoints.

Routes:
  POST   /api/ship-sessions          create a ship session record
  GET    /api/ship-sessions          list with filters (project_name, status, limit, offset)
  POST   /api/ship-sessions/search   full-text search across ship sessions
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
from models import ShipSession
from ship_sessions_schemas import (
    ShipSessionCreate,
    ShipSessionResponse,
    ShipSessionList,
    ShipSessionSearch,
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


router = APIRouter(prefix="/api/ship-sessions", tags=["ship-sessions"])


def _upsert_ship_session(
    db: Session, payload: ShipSessionCreate, embedding=None,
) -> tuple[ShipSession, bool]:
    """Upsert by (project_name, feature). Returns (row, created)."""
    existing = db.query(ShipSession).filter(
        ShipSession.project_name == payload.project_name,
        ShipSession.feature == payload.feature,
    ).first()

    if existing:
        existing.approach = payload.approach
        existing.status = payload.status
        existing.complexity = payload.complexity
        existing.tdd = payload.tdd
        existing.pr_url = payload.pr_url
        existing.branch = payload.branch
        existing.commits = payload.commits
        existing.deferred = payload.deferred
        existing.surprises = payload.surprises
        existing.decisions = payload.decisions
        existing.review = payload.review
        existing.verification = payload.verification
        existing.file_map = payload.file_map
        existing.tags = payload.tags
        existing.session_id = payload.session_id
        existing.model_name = payload.model_name
        existing.meta_data = payload.meta_data
        existing.completed_at = payload.completed_at
        if embedding:
            existing.embedding = embedding
            existing.embedding_model = "nomic-embed-text"
        return existing, False

    row = ShipSession(**payload.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
        return row, True
    except IntegrityError:
        db.rollback()
        existing = db.query(ShipSession).filter(
            ShipSession.project_name == payload.project_name,
            ShipSession.feature == payload.feature,
        ).first()
        if existing:
            existing.approach = payload.approach
            existing.status = payload.status
            existing.complexity = payload.complexity
            existing.tdd = payload.tdd
            existing.pr_url = payload.pr_url
            existing.branch = payload.branch
            existing.commits = payload.commits
            existing.deferred = payload.deferred
            existing.surprises = payload.surprises
            existing.decisions = payload.decisions
            existing.review = payload.review
            existing.verification = payload.verification
            existing.file_map = payload.file_map
            existing.tags = payload.tags
            existing.session_id = payload.session_id
            existing.model_name = payload.model_name
            existing.meta_data = payload.meta_data
            existing.completed_at = payload.completed_at
            if embedding:
                existing.embedding = embedding
                existing.embedding_model = "nomic-embed-text"
            return existing, False
        raise


@router.post("", response_model=ShipSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_ship_session(
    payload: ShipSessionCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> ShipSessionResponse:
    start = time.time()
    try:
        embedding = None
        try:
            from embedding_utils import get_embedding
            text_for_embed = f"{payload.feature} {payload.approach or ''}"
            embedding = await get_embedding(text_for_embed)
        except Exception as embed_err:
            logger.warning("Embedding generation failed: %s", embed_err)

        row, created = _upsert_ship_session(db, payload, embedding)
        db.commit()
        db.refresh(row)

        if not created:
            response.status_code = status.HTTP_200_OK

        registry_write_operations.labels(operation="create_ship_session").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_ship_session_failed").inc()
        logger.error("%s failed: %s", "ship_sessions_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=ShipSessionList)
async def list_ship_sessions(
    project_name: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> ShipSessionList:
    start = time.time()
    try:
        query = db.query(ShipSession)
        if project_name:
            query = query.filter(ShipSession.project_name == project_name)
        if status_filter:
            query = query.filter(ShipSession.status == status_filter)

        total = query.count()
        rows = (
            query
            .order_by(ShipSession.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        registry_read_operations.labels(operation="list_ship_sessions").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return ShipSessionList(ship_sessions=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_ship_sessions_failed").inc()
        logger.error("%s failed: %s", "ship_sessions_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=ShipSessionList)
async def search_ship_sessions(
    body: ShipSessionSearch,
    db: Session = Depends(get_db),
) -> ShipSessionList:
    start = time.time()
    try:
        ts_query = sa_func.plainto_tsquery("english", body.query)
        query = (
            db.query(ShipSession)
            .filter(ShipSession.search_vector.op("@@")(ts_query))
        )
        if body.project_name:
            query = query.filter(ShipSession.project_name == body.project_name)
        if body.status:
            query = query.filter(ShipSession.status == body.status)

        total = query.count()
        rows = (
            query
            .order_by(sa_func.ts_rank(ShipSession.search_vector, ts_query).desc())
            .limit(body.limit)
            .all()
        )

        registry_read_operations.labels(operation="search_ship_sessions").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return ShipSessionList(ship_sessions=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="search_ship_sessions_failed").inc()
        logger.error("%s failed: %s", "ship_sessions_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ship_session(
    item_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        row = db.query(ShipSession).filter(ShipSession.id == item_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        db.delete(row)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_ship_session_failed").inc()
        logger.error("delete_ship_session failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
