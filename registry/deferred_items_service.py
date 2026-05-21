"""Deferred Items service layer — all database operations for deferred_items."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import DeferredItem
from deferred_items_schemas import DeferredItemCreate

logger = logging.getLogger(__name__)


def upsert_deferred_item(
    db: Session, payload: DeferredItemCreate, embedding=None,
) -> tuple[DeferredItem, bool]:
    """Upsert by (project_name, title). Returns (row, created)."""
    existing = db.query(DeferredItem).filter(
        DeferredItem.project_name == payload.project_name,
        DeferredItem.title == payload.title,
    ).first()

    if existing:
        _apply_fields(existing, payload, embedding)
        db.commit()
        db.refresh(existing)
        return existing, False

    row = DeferredItem(**payload.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(DeferredItem).filter(
            DeferredItem.project_name == payload.project_name,
            DeferredItem.title == payload.title,
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


def list_deferred_items(
    db: Session,
    *,
    project_name: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    status_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[DeferredItem], int]:
    query = db.query(DeferredItem)
    if project_name:
        query = query.filter(DeferredItem.project_name == project_name)
    if category:
        query = query.filter(DeferredItem.category == category)
    if priority:
        query = query.filter(DeferredItem.priority == priority)
    if status_filter:
        query = query.filter(DeferredItem.status == status_filter)

    total = query.count()
    rows = (
        query
        .order_by(DeferredItem.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def search_deferred_items(
    db: Session,
    query_text: str,
    *,
    project_name: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    status_filter: str | None = None,
    limit: int = 20,
) -> tuple[list[DeferredItem], int]:
    ts_query = sa_func.plainto_tsquery("english", query_text)
    query = (
        db.query(DeferredItem)
        .filter(DeferredItem.search_vector.op("@@")(ts_query))
    )
    if project_name:
        query = query.filter(DeferredItem.project_name == project_name)
    if category:
        query = query.filter(DeferredItem.category == category)
    if priority:
        query = query.filter(DeferredItem.priority == priority)
    if status_filter:
        query = query.filter(DeferredItem.status == status_filter)

    total = query.count()
    rows = (
        query
        .order_by(sa_func.ts_rank(DeferredItem.search_vector, ts_query).desc())
        .limit(limit)
        .all()
    )
    return rows, total


def delete_deferred_item(db: Session, item_id: UUID) -> DeferredItem | None:
    row = db.query(DeferredItem).filter(DeferredItem.id == item_id).first()
    if not row:
        return None
    db.delete(row)
    db.commit()
    return row


def _apply_fields(existing: DeferredItem, payload: DeferredItemCreate, embedding) -> None:
    existing.description = payload.description
    existing.reason = payload.reason
    existing.source_context = payload.source_context
    existing.priority = payload.priority
    existing.category = payload.category
    existing.status = payload.status
    existing.affected_files = payload.affected_files
    existing.tags = payload.tags
    existing.session_id = payload.session_id
    existing.model_name = payload.model_name
    existing.meta_data = payload.meta_data
    if embedding:
        existing.embedding = embedding
        existing.embedding_model = "nomic-embed-text"
