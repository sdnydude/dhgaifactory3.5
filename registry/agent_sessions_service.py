"""Agent Sessions service layer — all database operations for agent_sessions."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from models import AgentSession
from agent_sessions_schemas import AgentSessionCreate

logger = logging.getLogger(__name__)


def create_agent_session(
    db: Session, payload: AgentSessionCreate,
) -> AgentSession:
    """Create a new agent session. Raises RuntimeError if session_id already exists."""
    existing = db.query(AgentSession).filter(
        AgentSession.session_id == payload.session_id,
    ).first()
    if existing:
        raise RuntimeError(f"Session {payload.session_id} already exists")

    row = AgentSession(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_agent_sessions(
    db: Session,
    *,
    project: str | None = None,
    source: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AgentSession], int]:
    query = db.query(AgentSession)
    if project:
        query = query.filter(AgentSession.project == project)
    if source:
        query = query.filter(AgentSession.source == source)

    total = query.count()
    rows = (
        query
        .order_by(AgentSession.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def get_agent_session(db: Session, session_id: str) -> AgentSession | None:
    return db.query(AgentSession).filter(
        AgentSession.session_id == session_id,
    ).first()
