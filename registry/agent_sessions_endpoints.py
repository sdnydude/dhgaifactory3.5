"""Agent Sessions API endpoints.

Routes:
  POST   /api/agent-sessions              create session record
  GET    /api/agent-sessions              list with filters (project, source, limit, offset)
  GET    /api/agent-sessions/{session_id} get by session_id
"""
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from agent_sessions_schemas import (
    AgentSessionCreate,
    AgentSessionResponse,
    AgentSessionList,
)
import agent_sessions_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/agent-sessions", tags=["agent-sessions"])


@router.post("", response_model=AgentSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_session(
    payload: AgentSessionCreate,
    db: Session = Depends(get_db),
) -> AgentSessionResponse:
    start = time.time()
    try:
        try:
            row = svc.create_agent_session(db, payload)
        except RuntimeError as re:
            raise HTTPException(status_code=409, detail=str(re))

        registry_write_operations.labels(operation="create_agent_session").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_agent_session_failed").inc()
        logger.exception("create_agent_session failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=AgentSessionList)
async def list_agent_sessions(
    project: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> AgentSessionList:
    start = time.time()
    try:
        rows, total = svc.list_agent_sessions(
            db, project=project, source=source,
            limit=limit, offset=offset,
        )

        registry_read_operations.labels(operation="list_agent_sessions").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return AgentSessionList(sessions=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_agent_sessions_failed").inc()
        logger.exception("list_agent_sessions failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{session_id}", response_model=AgentSessionResponse)
async def get_agent_session(
    session_id: str,
    db: Session = Depends(get_db),
) -> AgentSessionResponse:
    start = time.time()
    try:
        row = svc.get_agent_session(db, session_id)
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")

        registry_read_operations.labels(operation="get_agent_session").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        registry_errors.labels(error_type="get_agent_session_failed").inc()
        logger.exception("get_agent_session failed")
        raise HTTPException(status_code=500, detail="Internal server error")
