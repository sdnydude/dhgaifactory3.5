"""Test Coverage service layer — all database operations for test_coverage."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import TestCoverage
from test_coverage_schemas import TestCoverageCreate

logger = logging.getLogger(__name__)


def upsert_test_coverage(
    db: Session, payload: TestCoverageCreate, embedding=None,
) -> tuple[TestCoverage, bool]:
    """Upsert by (project_name, title). Returns (row, created)."""
    existing = db.query(TestCoverage).filter(
        TestCoverage.project_name == payload.project_name,
        TestCoverage.title == payload.title,
    ).first()

    if existing:
        _apply_fields(existing, payload, embedding)
        db.commit()
        db.refresh(existing)
        return existing, False

    row = TestCoverage(**payload.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(TestCoverage).filter(
            TestCoverage.project_name == payload.project_name,
            TestCoverage.title == payload.title,
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


def list_test_coverage(
    db: Session,
    *,
    project_name: str | None = None,
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[TestCoverage], int]:
    query = db.query(TestCoverage)
    if project_name:
        query = query.filter(TestCoverage.project_name == project_name)
    if category:
        query = query.filter(TestCoverage.category == category)

    total = query.count()
    rows = (
        query
        .order_by(TestCoverage.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def search_test_coverage(
    db: Session,
    query_text: str,
    *,
    project_name: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> tuple[list[TestCoverage], int]:
    ts_query = sa_func.plainto_tsquery("english", query_text)
    query = (
        db.query(TestCoverage)
        .filter(TestCoverage.search_vector.op("@@")(ts_query))
    )
    if project_name:
        query = query.filter(TestCoverage.project_name == project_name)
    if category:
        query = query.filter(TestCoverage.category == category)

    total = query.count()
    rows = (
        query
        .order_by(sa_func.ts_rank(TestCoverage.search_vector, ts_query).desc())
        .limit(limit)
        .all()
    )
    return rows, total


def delete_test_coverage(db: Session, item_id: UUID) -> TestCoverage | None:
    row = db.query(TestCoverage).filter(TestCoverage.id == item_id).first()
    if not row:
        return None
    db.delete(row)
    db.commit()
    return row


def _apply_fields(existing: TestCoverage, payload: TestCoverageCreate, embedding) -> None:
    existing.test_count_before = payload.test_count_before
    existing.test_count_after = payload.test_count_after
    existing.delta = payload.delta
    existing.tests_added = payload.tests_added
    existing.tests_removed = payload.tests_removed
    existing.tests_modified = payload.tests_modified
    existing.files_affected = payload.files_affected
    existing.category = payload.category
    existing.trigger = payload.trigger
    existing.tags = payload.tags
    existing.session_id = payload.session_id
    existing.model_name = payload.model_name
    existing.meta_data = payload.meta_data
    if embedding:
        existing.embedding = embedding
        existing.embedding_model = "nomic-embed-text"
