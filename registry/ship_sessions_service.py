"""Ship Sessions service layer — all database operations for ship_sessions."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import ShipSession
from ship_sessions_schemas import ShipSessionCreate

logger = logging.getLogger(__name__)


def upsert_ship_session(
    db: Session, payload: ShipSessionCreate, embedding=None,
) -> tuple[ShipSession, bool]:
    """Upsert by (project_name, feature). Returns (row, created)."""
    existing = db.query(ShipSession).filter(
        ShipSession.project_name == payload.project_name,
        ShipSession.feature == payload.feature,
    ).first()

    if existing:
        _apply_fields(existing, payload, embedding)
        db.commit()
        db.refresh(existing)
        return existing, False

    row = ShipSession(**payload.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(ShipSession).filter(
            ShipSession.project_name == payload.project_name,
            ShipSession.feature == payload.feature,
        ).first()
        if not existing:
            raise RuntimeError("Conflict: row vanished between insert and re-query")
        _apply_fields(existing, payload, embedding)
        db.commit()
        db.refresh(existing)
        return existing, False

    db.commit()
    db.refresh(row)
    return row, True


def list_ship_sessions(
    db: Session,
    *,
    project_name: str | None = None,
    status_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[ShipSession], int]:
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
    return rows, total


def search_ship_sessions(
    db: Session,
    query_text: str,
    *,
    project_name: str | None = None,
    status_filter: str | None = None,
    limit: int = 20,
) -> tuple[list[ShipSession], int]:
    ts_query = sa_func.plainto_tsquery("english", query_text)
    query = (
        db.query(ShipSession)
        .filter(ShipSession.search_vector.op("@@")(ts_query))
    )
    if project_name:
        query = query.filter(ShipSession.project_name == project_name)
    if status_filter:
        query = query.filter(ShipSession.status == status_filter)

    total = query.count()
    rows = (
        query
        .order_by(sa_func.ts_rank(ShipSession.search_vector, ts_query).desc())
        .limit(limit)
        .all()
    )
    return rows, total


def delete_ship_session(db: Session, item_id: UUID) -> ShipSession | None:
    row = db.query(ShipSession).filter(ShipSession.id == item_id).first()
    if not row:
        return None
    db.delete(row)
    db.commit()
    return row


def _apply_fields(existing: ShipSession, payload: ShipSessionCreate, embedding) -> None:
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
