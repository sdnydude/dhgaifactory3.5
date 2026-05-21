"""Insights service layer — all database operations for insights."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Insight
from insights_schemas import InsightCreate

logger = logging.getLogger(__name__)


def upsert_insight(
    db: Session, payload: InsightCreate, embedding=None,
) -> tuple[Insight, bool]:
    """Upsert by (project_name, tldr). Returns (row, created)."""
    existing = db.query(Insight).filter(
        Insight.project_name == payload.project_name,
        Insight.tldr == payload.tldr,
    ).first()

    if existing:
        _apply_fields(existing, payload, embedding)
        db.commit()
        db.refresh(existing)
        return existing, False

    row = Insight(**payload.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(Insight).filter(
            Insight.project_name == payload.project_name,
            Insight.tldr == payload.tldr,
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


def list_insights(
    db: Session,
    *,
    project_name: str | None = None,
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Insight], int]:
    query = db.query(Insight)
    if project_name:
        query = query.filter(Insight.project_name == project_name)
    if category:
        query = query.filter(Insight.category == category)

    total = query.count()
    rows = (
        query
        .order_by(Insight.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def search_insights(
    db: Session,
    query_text: str,
    *,
    project_name: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> tuple[list[Insight], int]:
    ts_query = sa_func.plainto_tsquery("english", query_text)
    query = (
        db.query(Insight)
        .filter(Insight.search_vector.op("@@")(ts_query))
    )
    if project_name:
        query = query.filter(Insight.project_name == project_name)
    if category:
        query = query.filter(Insight.category == category)

    total = query.count()
    rows = (
        query
        .order_by(sa_func.ts_rank(Insight.search_vector, ts_query).desc())
        .limit(limit)
        .all()
    )
    return rows, total


def delete_insight(db: Session, item_id: UUID) -> Insight | None:
    row = db.query(Insight).filter(Insight.id == item_id).first()
    if not row:
        return None
    db.delete(row)
    db.commit()
    return row


def _apply_fields(existing: Insight, payload: InsightCreate, embedding) -> None:
    existing.insight_statement = payload.insight_statement
    existing.category = payload.category
    existing.subcategory = payload.subcategory
    existing.source_file = payload.source_file
    existing.source_language = payload.source_language
    existing.source_framework = payload.source_framework
    existing.tags = payload.tags
    existing.session_id = payload.session_id
    existing.model_name = payload.model_name
    existing.meta_data = payload.meta_data
    if embedding:
        existing.embedding = embedding
        existing.embedding_model = "nomic-embed-text"
