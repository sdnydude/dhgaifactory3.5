"""Doc Pages API endpoints.

Routes:
  POST   /api/doc-pages              upsert a single doc page
  POST   /api/doc-pages/bulk         bulk upsert with optional mark-and-sweep
  GET    /api/doc-pages              list with filters (project_name, source_file, limit, offset)
  POST   /api/doc-pages/search       hybrid FTS + vector search with RRF
  DELETE /api/doc-pages/project/:name  delete all pages for a project
"""
import os
import sys
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, text, tuple_ as sa_tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from embedding_utils import get_embedding
from models import DocPage
from doc_pages_schemas import (
    DocPageCreate,
    DocPageResponse,
    DocPageList,
    DocPageSearch,
    DocPageBulkIngest,
)

logger = logging.getLogger(__name__)

try:
    from api import (
        registry_read_latency,
        registry_read_operations,
        registry_write_latency,
        registry_write_operations,
        registry_errors,
    )
except ImportError:
    from prometheus_client import Counter, Histogram
    registry_read_latency = Histogram(
        "registry_read_latency", "Read latency",
        buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
    )
    registry_read_operations = Counter(
        "registry_read_operations", "Read operations", ["operation"],
    )
    registry_write_latency = Histogram(
        "registry_write_latency", "Write latency",
        buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
    )
    registry_write_operations = Counter(
        "registry_write_operations", "Write operations", ["operation"],
    )
    registry_errors = Counter(
        "registry_errors", "Registry errors", ["error_type"],
    )


router = APIRouter(prefix="/api/doc-pages", tags=["doc-pages"])


async def _generate_embedding(content: str, title: Optional[str] = None) -> Optional[list]:
    try:
        embed_text = f"{title or ''} {content}"
        return await get_embedding(embed_text)
    except Exception as e:
        logger.warning("Embedding generation failed: %s", e)
        return None


def _upsert_page(db: Session, page: DocPageCreate, embedding: Optional[list] = None) -> tuple[DocPage, bool]:
    """Upsert a doc page by (project_name, source_file, chunk_index). Returns (row, created)."""
    existing = (
        db.query(DocPage)
        .filter(
            DocPage.project_name == page.project_name,
            DocPage.source_file == page.source_file,
            DocPage.chunk_index == page.chunk_index,
        )
        .first()
    )

    if existing:
        existing.title = page.title
        existing.content = page.content
        existing.heading_path = page.heading_path
        existing.tags = page.tags
        existing.meta_data = page.meta_data
        if embedding:
            existing.embedding = embedding
            existing.embedding_model = "nomic-embed-text"
        return existing, False

    row = DocPage(**page.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
        return row, True
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(DocPage)
            .filter(
                DocPage.project_name == page.project_name,
                DocPage.source_file == page.source_file,
                DocPage.chunk_index == page.chunk_index,
            )
            .first()
        )
        if existing:
            existing.title = page.title
            existing.content = page.content
            existing.heading_path = page.heading_path
            existing.tags = page.tags
            existing.meta_data = page.meta_data
            if embedding:
                existing.embedding = embedding
                existing.embedding_model = "nomic-embed-text"
            return existing, False
        raise


@router.post("", response_model=DocPageResponse, status_code=status.HTTP_201_CREATED)
async def upsert_doc_page(
    payload: DocPageCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> DocPageResponse:
    start = time.time()
    try:
        embedding = await _generate_embedding(payload.content, payload.title)
        row, created = _upsert_page(db, payload, embedding)
        db.commit()
        db.refresh(row)

        if not created:
            response.status_code = status.HTTP_200_OK

        registry_write_operations.labels(operation="upsert_doc_page").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("upsert_doc_page failed: %s", e)
        registry_errors.labels(error_type="upsert_doc_page_failed").inc()
        raise HTTPException(status_code=500, detail="Upsert failed")


@router.post("/bulk", response_model=dict, status_code=status.HTTP_200_OK)
async def bulk_ingest(
    payload: DocPageBulkIngest,
    db: Session = Depends(get_db),
) -> dict:
    """Bulk upsert doc pages with optional mark-and-sweep stale cleanup."""
    start = time.time()
    try:
        seen_keys: set[tuple[str, str, int]] = set()
        upserted = 0

        for page in payload.pages:
            page_data = page.model_copy(update={"project_name": payload.project_name})
            embedding = await _generate_embedding(page_data.content, page_data.title)
            _upsert_page(db, page_data, embedding)
            seen_keys.add((payload.project_name, page_data.source_file, page_data.chunk_index))
            upserted += 1

        swept = 0
        if payload.sweep_stale:
            seen_pairs = [
                (source_file, chunk_index)
                for (_, source_file, chunk_index) in seen_keys
            ]
            swept = (
                db.query(DocPage)
                .filter(
                    DocPage.project_name == payload.project_name,
                    sa_tuple(DocPage.source_file, DocPage.chunk_index).notin_(seen_pairs),
                )
                .delete(synchronize_session=False)
            )

        db.commit()

        registry_write_operations.labels(operation="bulk_ingest_doc_pages").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return {"upserted": upserted, "swept": swept, "project_name": payload.project_name}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("bulk_ingest failed for project %s: %s", payload.project_name, e)
        registry_errors.labels(error_type="bulk_ingest_doc_pages_failed").inc()
        raise HTTPException(status_code=500, detail="Bulk ingest failed")


@router.get("", response_model=DocPageList)
async def list_doc_pages(
    project_name: Optional[str] = Query(None),
    source_file: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> DocPageList:
    start = time.time()
    try:
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

        registry_read_operations.labels(operation="list_doc_pages").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return DocPageList(doc_pages=rows, total=total)
    except Exception as e:
        logger.error("list_doc_pages failed: %s", e)
        registry_errors.labels(error_type="list_doc_pages_failed").inc()
        raise HTTPException(status_code=500, detail="List failed")


@router.post("/search", response_model=DocPageList)
async def search_doc_pages(
    body: DocPageSearch,
    db: Session = Depends(get_db),
) -> DocPageList:
    """Hybrid search using Reciprocal Rank Fusion (RRF) over FTS + vector."""
    start = time.time()
    K = 60  # RRF constant

    try:
        query_embedding = await get_embedding(body.query)

        fts_results: list[tuple] = []
        vec_results: list[tuple] = []

        ts_query = sa_func.plainto_tsquery("english", body.query)
        fts_q = (
            db.query(DocPage, sa_func.ts_rank(DocPage.search_vector, ts_query).label("rank"))
            .filter(DocPage.search_vector.op("@@")(ts_query))
        )
        if body.project_name:
            fts_q = fts_q.filter(DocPage.project_name == body.project_name)
        if body.tags:
            fts_q = fts_q.filter(DocPage.tags.overlap(body.tags))
        fts_results = fts_q.order_by(text("rank DESC")).limit(body.limit * 2).all()

        if query_embedding:
            vec_q = db.query(DocPage).filter(DocPage.embedding.isnot(None))
            if body.project_name:
                vec_q = vec_q.filter(DocPage.project_name == body.project_name)
            if body.tags:
                vec_q = vec_q.filter(DocPage.tags.overlap(body.tags))
            vec_results_raw = (
                vec_q
                .order_by(DocPage.embedding.l2_distance(query_embedding))
                .limit(body.limit * 2)
                .all()
            )
            vec_results = [(row, i) for i, row in enumerate(vec_results_raw)]

        scores: dict[str, float] = {}
        pages: dict[str, DocPage] = {}

        for rank_pos, (page, _) in enumerate(fts_results):
            pid = str(page.id)
            scores[pid] = scores.get(pid, 0) + 1.0 / (K + rank_pos + 1)
            pages[pid] = page

        for page, rank_pos in vec_results:
            pid = str(page.id)
            scores[pid] = scores.get(pid, 0) + 1.0 / (K + rank_pos + 1)
            pages[pid] = page

        sorted_ids = sorted(scores, key=lambda k: scores[k], reverse=True)[:body.limit]
        result_pages = [pages[pid] for pid in sorted_ids]

        registry_read_operations.labels(operation="search_doc_pages").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return DocPageList(doc_pages=result_pages, total=len(result_pages))
    except Exception as e:
        logger.error("search_doc_pages failed: %s", e)
        registry_errors.labels(error_type="search_doc_pages_failed").inc()
        raise HTTPException(status_code=500, detail="Search failed")


@router.delete("/project/{project_name}", status_code=status.HTTP_200_OK)
async def delete_project_pages(
    project_name: str,
    db: Session = Depends(get_db),
) -> dict:
    start = time.time()
    try:
        count = db.query(DocPage).filter(DocPage.project_name == project_name).delete(synchronize_session=False)
        db.commit()

        registry_write_operations.labels(operation="delete_project_pages").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return {"deleted": count, "project_name": project_name}
    except Exception as e:
        db.rollback()
        logger.error("delete_project_pages failed for %s: %s", project_name, e)
        registry_errors.labels(error_type="delete_project_pages_failed").inc()
        raise HTTPException(status_code=500, detail="Delete failed")
