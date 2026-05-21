"""Decision Logs service layer — all database operations for decision_logs."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import DecisionLog
from decision_logs_schemas import DecisionLogCreate

logger = logging.getLogger(__name__)


def upsert_decision_log(
    db: Session, payload: DecisionLogCreate, embedding=None,
) -> tuple[DecisionLog, bool]:
    """Upsert by (project_name, title). Returns (row, created)."""
    existing = db.query(DecisionLog).filter(
        DecisionLog.project_name == payload.project_name,
        DecisionLog.title == payload.title,
    ).first()

    if existing:
        _apply_fields(existing, payload, embedding)
        db.commit()
        db.refresh(existing)
        return existing, False

    row = DecisionLog(**payload.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(DecisionLog).filter(
            DecisionLog.project_name == payload.project_name,
            DecisionLog.title == payload.title,
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


def list_decision_logs(
    db: Session,
    *,
    project_name: str | None = None,
    domain: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[DecisionLog], int]:
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
    return rows, total


def search_decision_logs(
    db: Session,
    query_text: str,
    *,
    project_name: str | None = None,
    domain: str | None = None,
    limit: int = 20,
) -> tuple[list[DecisionLog], int]:
    ts_query = sa_func.plainto_tsquery("english", query_text)
    query = (
        db.query(DecisionLog)
        .filter(DecisionLog.search_vector.op("@@")(ts_query))
    )
    if project_name:
        query = query.filter(DecisionLog.project_name == project_name)
    if domain:
        query = query.filter(DecisionLog.domain == domain)

    total = query.count()
    rows = (
        query
        .order_by(sa_func.ts_rank(DecisionLog.search_vector, ts_query).desc())
        .limit(limit)
        .all()
    )
    return rows, total


def delete_decision_log(db: Session, item_id: UUID) -> DecisionLog | None:
    row = db.query(DecisionLog).filter(DecisionLog.id == item_id).first()
    if not row:
        return None
    db.delete(row)
    db.commit()
    return row


def _apply_fields(existing: DecisionLog, payload: DecisionLogCreate, embedding) -> None:
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
