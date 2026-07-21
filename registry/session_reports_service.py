"""Session Reports service layer — all database operations for session_reports."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import SessionReport
from session_reports_schemas import SessionReportCreate

logger = logging.getLogger(__name__)


def upsert_session_report(
    db: Session, payload: SessionReportCreate, embedding=None,
) -> tuple[SessionReport, bool]:
    """Upsert by (project_name, title). Returns (row, created)."""
    existing = db.query(SessionReport).filter(
        SessionReport.project_name == payload.project_name,
        SessionReport.title == payload.title,
    ).first()

    if existing:
        _apply_fields(existing, payload, embedding)
        db.commit()
        db.refresh(existing)
        return existing, False

    row = SessionReport(**payload.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(SessionReport).filter(
            SessionReport.project_name == payload.project_name,
            SessionReport.title == payload.title,
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


def list_session_reports(
    db: Session,
    *,
    project_name: str | None = None,
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[SessionReport], int]:
    query = db.query(SessionReport)
    if project_name:
        query = query.filter(SessionReport.project_name == project_name)
    if category:
        query = query.filter(SessionReport.category == category)

    total = query.count()
    rows = (
        query
        .order_by(SessionReport.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def search_session_reports(
    db: Session,
    query_text: str,
    *,
    project_name: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> tuple[list[SessionReport], int]:
    ts_query = sa_func.plainto_tsquery("english", query_text)
    query = (
        db.query(SessionReport)
        .filter(SessionReport.search_vector.op("@@")(ts_query))
    )
    if project_name:
        query = query.filter(SessionReport.project_name == project_name)
    if category:
        query = query.filter(SessionReport.category == category)

    total = query.count()
    rows = (
        query
        .order_by(sa_func.ts_rank(SessionReport.search_vector, ts_query).desc())
        .limit(limit)
        .all()
    )
    return rows, total


def delete_session_report(db: Session, item_id: UUID) -> SessionReport | None:
    row = db.query(SessionReport).filter(SessionReport.id == item_id).first()
    if not row:
        return None
    db.delete(row)
    db.commit()
    return row


def _apply_fields(existing: SessionReport, payload: SessionReportCreate, embedding) -> None:
    existing.session_span = payload.session_span
    existing.report_md = payload.report_md
    existing.prs = payload.prs
    existing.learnings = payload.learnings
    existing.insights = payload.insights
    existing.deferred = payload.deferred
    existing.category = payload.category
    existing.source_file = payload.source_file
    existing.tags = payload.tags
    existing.session_id = payload.session_id
    existing.model_name = payload.model_name
    existing.meta_data = payload.meta_data
    if embedding:
        existing.embedding = embedding
        existing.embedding_model = "nomic-embed-text"
