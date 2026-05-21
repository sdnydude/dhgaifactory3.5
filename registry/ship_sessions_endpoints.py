"""Ship Sessions API endpoints.

Routes:
  POST   /api/ship-sessions          create a ship session record
  GET    /api/ship-sessions          list with filters (project_name, status, limit, offset)
  POST   /api/ship-sessions/search   full-text search across ship sessions
  DELETE /api/ship-sessions/{item_id} delete a ship session
"""
import os
import sys
import time
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from ship_sessions_schemas import (
    ShipSessionCreate,
    ShipSessionResponse,
    ShipSessionList,
    ShipSessionSearch,
)
import ship_sessions_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/ship-sessions", tags=["ship-sessions"])


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

        row, created = svc.upsert_ship_session(db, payload, embedding)

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
        rows, total = svc.list_ship_sessions(
            db, project_name=project_name, status_filter=status_filter,
            limit=limit, offset=offset,
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
        rows, total = svc.search_ship_sessions(
            db, body.query,
            project_name=body.project_name, status_filter=body.status,
            limit=body.limit,
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
        row = svc.delete_ship_session(db, item_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_ship_session_failed").inc()
        logger.error("delete_ship_session failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
