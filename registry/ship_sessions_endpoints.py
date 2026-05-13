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

from fastapi import APIRouter, Depends, HTTPException, Query, status
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


@router.post("", response_model=ShipSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_ship_session(
    payload: ShipSessionCreate,
    db: Session = Depends(get_db),
) -> ShipSessionResponse:
    start = time.time()
    try:
        row = ShipSession(**payload.model_dump())

        try:
            from embedding_utils import get_embedding
            text_for_embed = f"{payload.feature} {payload.approach or ''}"
            embedding = await get_embedding(text_for_embed)
            if embedding:
                row.embedding = embedding
                row.embedding_model = "nomic-embed-text"
        except Exception as embed_err:
            logger.warning("Embedding generation failed: %s", embed_err)

        db.add(row)
        db.commit()
        db.refresh(row)

        registry_write_operations.labels(operation="create_ship_session").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_ship_session_failed").inc()
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))
