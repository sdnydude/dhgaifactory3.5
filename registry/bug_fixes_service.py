"""Bug Fixes service layer — all database operations for bug_fixes."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import BugFix
from bug_fixes_schemas import BugFixCreate

logger = logging.getLogger(__name__)


def upsert_bug_fix(
    db: Session, payload: BugFixCreate, embedding=None,
) -> tuple[BugFix, bool]:
    """Upsert by (project_name, tldr). Returns (row, created)."""
    existing = db.query(BugFix).filter(
        BugFix.project_name == payload.project_name,
        BugFix.tldr == payload.tldr,
    ).first()

    if existing:
        _apply_fields(existing, payload, embedding)
        db.commit()
        db.refresh(existing)
        return existing, False

    row = BugFix(**payload.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(BugFix).filter(
            BugFix.project_name == payload.project_name,
            BugFix.tldr == payload.tldr,
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


def list_bug_fixes(
    db: Session,
    *,
    project_name: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[BugFix], int]:
    query = db.query(BugFix)
    if project_name:
        query = query.filter(BugFix.project_name == project_name)
    if category:
        query = query.filter(BugFix.category == category)
    if severity:
        query = query.filter(BugFix.severity == severity)

    total = query.count()
    rows = (
        query
        .order_by(BugFix.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def search_bug_fixes(
    db: Session,
    query_text: str,
    *,
    project_name: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    limit: int = 20,
) -> tuple[list[BugFix], int]:
    ts_query = sa_func.plainto_tsquery("english", query_text)
    query = (
        db.query(BugFix)
        .filter(BugFix.search_vector.op("@@")(ts_query))
    )
    if project_name:
        query = query.filter(BugFix.project_name == project_name)
    if category:
        query = query.filter(BugFix.category == category)
    if severity:
        query = query.filter(BugFix.severity == severity)

    total = query.count()
    rows = (
        query
        .order_by(sa_func.ts_rank(BugFix.search_vector, ts_query).desc())
        .limit(limit)
        .all()
    )
    return rows, total


def delete_bug_fix(db: Session, item_id: UUID) -> BugFix | None:
    row = db.query(BugFix).filter(BugFix.id == item_id).first()
    if not row:
        return None
    db.delete(row)
    db.commit()
    return row


def _apply_fields(existing: BugFix, payload: BugFixCreate, embedding) -> None:
    existing.symptom = payload.symptom
    existing.root_cause = payload.root_cause
    existing.fix_applied = payload.fix_applied
    existing.files_affected = payload.files_affected
    existing.severity = payload.severity
    existing.category = payload.category
    existing.source_file = payload.source_file
    existing.tags = payload.tags
    existing.session_id = payload.session_id
    existing.model_name = payload.model_name
    existing.meta_data = payload.meta_data
    if embedding:
        existing.embedding = embedding
        existing.embedding_model = "nomic-embed-text"
