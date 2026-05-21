"""Corrections service layer — all database operations for corrections."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Correction
from corrections_schemas import CorrectionCreate

logger = logging.getLogger(__name__)


def compute_upsert_hash(user_message: str) -> str:
    return hashlib.md5(user_message.encode("utf-8")).hexdigest()


def upsert_correction(
    db: Session, payload: CorrectionCreate, upsert_hash: str, embedding=None,
) -> tuple[Correction, bool]:
    """Upsert by (project_name, category, upsert_key_hash). Returns (row, created)."""
    existing = db.query(Correction).filter(
        Correction.project_name == payload.project_name,
        Correction.category == payload.category,
        Correction.upsert_key_hash == upsert_hash,
    ).first()

    if existing:
        _apply_fields(existing, payload, embedding)
        db.commit()
        db.refresh(existing)
        return existing, False

    row = Correction(**payload.model_dump())
    row.upsert_key_hash = upsert_hash
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(Correction).filter(
            Correction.project_name == payload.project_name,
            Correction.category == payload.category,
            Correction.upsert_key_hash == upsert_hash,
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


def list_corrections(
    db: Session,
    *,
    project_name: str | None = None,
    category: str | None = None,
    since_days: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Correction], int]:
    q = db.query(Correction)
    if project_name:
        q = q.filter(Correction.project_name == project_name)
    if category:
        q = q.filter(Correction.category == category)
    if since_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
        q = q.filter(Correction.created_at >= cutoff)

    total = q.count()
    rows = q.order_by(Correction.created_at.desc()).offset(offset).limit(limit).all()
    return rows, total


def search_corrections(
    db: Session,
    query_text: str,
    *,
    project_name: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> tuple[list[Correction], int]:
    ts_query = sa_func.plainto_tsquery("english", query_text)
    q = db.query(Correction).filter(Correction.search_vector.op("@@")(ts_query))
    if project_name:
        q = q.filter(Correction.project_name == project_name)
    if category:
        q = q.filter(Correction.category == category)

    total = q.count()
    rows = (
        q.order_by(sa_func.ts_rank(Correction.search_vector, ts_query).desc())
        .limit(limit)
        .all()
    )
    return rows, total


def correction_stats(
    db: Session,
    *,
    project_name: str | None = None,
    since_days: int = 7,
) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    q = db.query(
        Correction.category,
        sa_func.count(Correction.id).label("count"),
    ).filter(Correction.created_at >= cutoff)
    if project_name:
        q = q.filter(Correction.project_name == project_name)

    rows = q.group_by(Correction.category).order_by(sa_func.count(Correction.id).desc()).all()
    return [{"category": r.category, "count": r.count} for r in rows]


def delete_correction(db: Session, item_id: UUID) -> Correction | None:
    row = db.query(Correction).filter(Correction.id == item_id).first()
    if not row:
        return None
    db.delete(row)
    db.commit()
    return row


def _apply_fields(existing: Correction, payload: CorrectionCreate, embedding) -> None:
    existing.user_message = payload.user_message
    existing.context = payload.context
    existing.claude_action = payload.claude_action
    existing.session_id = payload.session_id
    existing.tags = payload.tags
    existing.model_name = payload.model_name
    existing.meta_data = payload.meta_data
    if embedding:
        existing.embedding = embedding
        existing.embedding_model = "nomic-embed-text"
