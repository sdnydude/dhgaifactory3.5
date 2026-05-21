"""Doc pages service — DB operations for documentation page CRUD and hybrid search."""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, text, tuple_ as sa_tuple

from models import DocPage

logger = logging.getLogger(__name__)

_RRF_K = 60


def _apply_fields(row: DocPage, page_data, embedding: Optional[list] = None) -> None:
    row.title = page_data.title
    row.content = page_data.content
    row.heading_path = page_data.heading_path
    row.tags = page_data.tags
    row.meta_data = page_data.meta_data
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"


def upsert_page(
    db: Session, page_data, embedding: Optional[list] = None,
) -> tuple[DocPage, bool]:
    """Upsert by (project_name, source_file, chunk_index). Returns (row, created)."""
    existing = (
        db.query(DocPage)
        .filter(
            DocPage.project_name == page_data.project_name,
            DocPage.source_file == page_data.source_file,
            DocPage.chunk_index == page_data.chunk_index,
        )
        .first()
    )

    if existing:
        _apply_fields(existing, page_data, embedding)
        db.commit()
        db.refresh(existing)
        return existing, False

    row = DocPage(**page_data.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(DocPage)
            .filter(
                DocPage.project_name == page_data.project_name,
                DocPage.source_file == page_data.source_file,
                DocPage.chunk_index == page_data.chunk_index,
            )
            .first()
        )
        if existing:
            _apply_fields(existing, page_data, embedding)
            db.commit()
            db.refresh(existing)
            return existing, False
        raise
    db.commit()
    db.refresh(row)
    return row, True


def bulk_upsert(
    db: Session,
    project_name: str,
    pages_with_embeddings: list[tuple],
    sweep_stale: bool,
) -> tuple[int, int]:
    """Bulk upsert pages. Returns (upserted_count, swept_count)."""
    seen_keys: set[tuple[str, str, int]] = set()
    upserted = 0

    for page_data, embedding in pages_with_embeddings:
        upsert_page(db, page_data, embedding)
        seen_keys.add((project_name, page_data.source_file, page_data.chunk_index))
        upserted += 1

    swept = 0
    if sweep_stale:
        seen_pairs = [
            (source_file, chunk_index)
            for (_, source_file, chunk_index) in seen_keys
        ]
        swept = (
            db.query(DocPage)
            .filter(
                DocPage.project_name == project_name,
                sa_tuple(DocPage.source_file, DocPage.chunk_index).notin_(seen_pairs),
            )
            .delete(synchronize_session=False)
        )

    db.commit()
    return upserted, swept


def list_doc_pages(
    db: Session,
    *,
    project_name: str | None = None,
    source_file: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[DocPage], int]:
    query = db.query(DocPage)
    if project_name:
        query = query.filter(DocPage.project_name == project_name)
    if source_file:
        query = query.filter(DocPage.source_file == source_file)

    total = query.count()
    rows = (
        query
        .order_by(DocPage.project_name, DocPage.source_file, DocPage.chunk_index)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def search_doc_pages(
    db: Session,
    query_text: str,
    query_embedding: Optional[list[float]],
    *,
    project_name: str | None = None,
    tags: list[str] | None = None,
    limit: int = 10,
) -> list[DocPage]:
    """Hybrid FTS + vector search with RRF. Returns ranked list of DocPage."""
    fts_results: list[tuple] = []
    vec_results: list[tuple] = []

    ts_query = sa_func.plainto_tsquery("english", query_text)
    fts_q = (
        db.query(DocPage, sa_func.ts_rank(DocPage.search_vector, ts_query).label("rank"))
        .filter(DocPage.search_vector.op("@@")(ts_query))
    )
    if project_name:
        fts_q = fts_q.filter(DocPage.project_name == project_name)
    if tags:
        fts_q = fts_q.filter(DocPage.tags.overlap(tags))
    fts_results = fts_q.order_by(text("rank DESC")).limit(limit * 2).all()

    if query_embedding:
        vec_q = db.query(DocPage).filter(DocPage.embedding.isnot(None))
        if project_name:
            vec_q = vec_q.filter(DocPage.project_name == project_name)
        if tags:
            vec_q = vec_q.filter(DocPage.tags.overlap(tags))
        vec_results_raw = (
            vec_q
            .order_by(DocPage.embedding.l2_distance(query_embedding))
            .limit(limit * 2)
            .all()
        )
        vec_results = [(row, i) for i, row in enumerate(vec_results_raw)]

    scores: dict[str, float] = {}
    pages: dict[str, DocPage] = {}

    for rank_pos, (page, _) in enumerate(fts_results):
        pid = str(page.id)
        scores[pid] = scores.get(pid, 0) + 1.0 / (_RRF_K + rank_pos + 1)
        pages[pid] = page

    for page, rank_pos in vec_results:
        pid = str(page.id)
        scores[pid] = scores.get(pid, 0) + 1.0 / (_RRF_K + rank_pos + 1)
        pages[pid] = page

    sorted_ids = sorted(scores, key=lambda k: scores[k], reverse=True)[:limit]
    return [pages[pid] for pid in sorted_ids]


def delete_project_pages(db: Session, project_name: str) -> int:
    """Delete all pages for a project. Returns count deleted."""
    count = db.query(DocPage).filter(
        DocPage.project_name == project_name,
    ).delete(synchronize_session=False)
    db.commit()
    return count
