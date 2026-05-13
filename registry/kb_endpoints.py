"""Unified Knowledge Base search endpoint.

Routes:
  POST /api/kb/search  — Hybrid FTS + vector RRF search across 4 tables, searched sequentially.
                         Sources: doc_pages, insights, decision_logs, ship_sessions.
"""
import os
import sys
import time
import logging
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, text as sa_text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from embedding_utils import get_embedding
from models import DocPage, Insight, DecisionLog, ShipSession
from kb_schemas import KBSearchRequest, KBSearchResponse, KBSearchResult, VALID_SOURCES

logger = logging.getLogger(__name__)

try:
    from api import (
        registry_read_latency,
        registry_read_operations,
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
    registry_errors = Counter(
        "registry_errors", "Registry errors", ["error_type"],
    )


router = APIRouter(prefix="/api/kb", tags=["kb"])

_RRF_K = 60


def _extract_doc_page(row: DocPage) -> tuple[str, str, dict[str, Any]]:
    title = row.title or (row.content.split("\n")[0][:120] if row.content else "Untitled")
    content = row.content
    metadata: dict[str, Any] = {
        "source_file": row.source_file,
        "chunk_index": row.chunk_index,
        "heading_path": row.heading_path,
    }
    return title, content, metadata


def _extract_insight(row: Insight) -> tuple[str, str, dict[str, Any]]:
    title = row.tldr
    content = row.insight_statement
    metadata: dict[str, Any] = {
        "category": row.category,
        "subcategory": row.subcategory,
        "tags": row.tags,
    }
    return title, content, metadata


def _extract_decision_log(row: DecisionLog) -> tuple[str, str, dict[str, Any]]:
    title = row.title
    parts = [f"Choice: {row.choice}"]
    if row.rationale:
        parts.append(f"\n\nRationale: {row.rationale}")
    if row.alternatives_rejected:
        parts.append(f"\n\nRejected: {row.alternatives_rejected}")
    content = "".join(parts)
    metadata: dict[str, Any] = {
        "domain": row.domain,
        "supersedes": row.supersedes,
        "tags": row.tags,
    }
    return title, content, metadata


def _extract_ship_session(row: ShipSession) -> tuple[str, str, dict[str, Any]]:
    title = row.feature
    parts = []
    if row.approach:
        parts.append(f"Approach: {row.approach}")
    if row.complexity:
        parts.append(f"\n\nComplexity: {row.complexity}")
    content = "".join(parts) if parts else row.feature
    metadata: dict[str, Any] = {
        "status": row.status,
        "pr_url": row.pr_url,
        "complexity": row.complexity,
        "tdd": row.tdd,
        "branch": row.branch,
    }
    return title, content, metadata


_SOURCE_CONFIG: dict[str, tuple[Any, Callable]] = {
    "docs": (DocPage, _extract_doc_page),
    "insights": (Insight, _extract_insight),
    "decisions": (DecisionLog, _extract_decision_log),
    "ship_sessions": (ShipSession, _extract_ship_session),
}


def _search_source(
    source_name: str,
    db: Session,
    query: str,
    query_embedding: Optional[list[float]],
    project_name: Optional[str],
    candidate_limit: int,
) -> list[tuple[str, float, Any, str, str, str, dict[str, Any]]]:
    """Run hybrid FTS + vector search for one source table.

    Returns list of (row_id, rrf_score, row, source_name, title, content, metadata).
    Handles FTS and vector sub-failures independently — logs and returns empty list
    if both legs fail. Other unexpected exceptions (e.g., extractor failures, missing
    config keys) propagate to the caller.
    """
    model_cls, extractor = _SOURCE_CONFIG[source_name]
    scores: dict[str, float] = {}
    rows: dict[str, Any] = {}

    try:
        ts_query = sa_func.plainto_tsquery("english", query)
        fts_q = (
            db.query(
                model_cls,
                sa_func.ts_rank(model_cls.search_vector, ts_query).label("rank"),
            )
            .filter(model_cls.search_vector.op("@@")(ts_query))
        )
        if project_name:
            fts_q = fts_q.filter(model_cls.project_name == project_name)
        fts_results = (
            fts_q
            .order_by(sa_text("rank DESC"))
            .limit(candidate_limit)
            .all()
        )
        for rank_pos, (row, _) in enumerate(fts_results):
            rid = str(row.id)
            scores[rid] = scores.get(rid, 0.0) + 1.0 / (_RRF_K + rank_pos + 1)
            rows[rid] = row
    except Exception as fts_err:
        logger.warning("KB FTS failed for source=%s: %s", source_name, fts_err)

    try:
        if query_embedding:
            vec_q = db.query(model_cls).filter(model_cls.embedding.isnot(None))
            if project_name:
                vec_q = vec_q.filter(model_cls.project_name == project_name)
            vec_rows = (
                vec_q
                .order_by(model_cls.embedding.l2_distance(query_embedding))
                .limit(candidate_limit)
                .all()
            )
            for rank_pos, row in enumerate(vec_rows):
                rid = str(row.id)
                scores[rid] = scores.get(rid, 0.0) + 1.0 / (_RRF_K + rank_pos + 1)
                rows[rid] = row
    except Exception as vec_err:
        logger.warning("KB vector search failed for source=%s: %s", source_name, vec_err)

    results = []
    try:
        for rid, score in scores.items():
            row = rows[rid]
            title, content, metadata = extractor(row)
            results.append((rid, score, row, source_name, title, content, metadata))
    except Exception as extract_err:
        logger.error("KB extraction failed for source=%s: %s", source_name, extract_err)
        return []

    return results


@router.post("/search", response_model=KBSearchResponse)
async def kb_search(
    body: KBSearchRequest,
    db: Session = Depends(get_db),
) -> KBSearchResponse:
    """Unified hybrid search across doc_pages, insights, decision_logs, and ship_sessions.

    Generates one query embedding, iterates over each requested source sequentially,
    then merges all results with Reciprocal Rank Fusion (k=60) and returns the top
    `limit`. Individual source failures are logged and skipped — degrades gracefully.
    """
    start = time.time()

    raw_sources: list[str] = body.sources if body.sources else list(_SOURCE_CONFIG.keys())
    invalid = [s for s in raw_sources if s not in VALID_SOURCES]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sources: {invalid}. Valid: {sorted(VALID_SOURCES)}",
        )
    # Dedupe while preserving order — duplicate sources would inflate RRF scores
    requested_sources = list(dict.fromkeys(raw_sources))

    query_embedding: Optional[list[float]] = None
    try:
        query_embedding = await get_embedding(body.query)
    except Exception as embed_err:
        logger.warning("KB search embedding failed, falling back to FTS only: %s", embed_err)

    # Per-source candidate pool — floor of 50 ensures small `limit` queries still
    # have enough material for cross-source RRF merging
    candidate_limit = max(body.limit * 5, 50)

    all_candidates: list[tuple[str, float, Any, str, str, str, dict[str, Any]]] = []
    searched_sources: list[str] = []
    failed_sources: list[str] = []

    for source_name in requested_sources:
        try:
            candidates = _search_source(
                source_name=source_name,
                db=db,
                query=body.query,
                query_embedding=query_embedding,
                project_name=body.project_name,
                candidate_limit=candidate_limit,
            )
            all_candidates.extend(candidates)
            searched_sources.append(source_name)
        except Exception as source_err:
            logger.error("KB search failed for source=%s: %s", source_name, source_err)
            registry_errors.labels(error_type=f"kb_search_{source_name}_failed").inc()
            failed_sources.append(source_name)

    if failed_sources:
        logger.warning("KB search: sources with complete failure: %s", failed_sources)

    all_candidates.sort(key=lambda c: c[1], reverse=True)
    top = all_candidates[: body.limit]

    results = [
        KBSearchResult(
            source=source_name,
            source_id=row.id,
            title=title,
            content=content,
            score=round(score, 8),
            project_name=row.project_name,
            metadata=metadata,
        )
        for (_, score, row, source_name, title, content, metadata) in top
    ]

    registry_read_operations.labels(operation="kb_search").inc()
    registry_read_latency.observe((time.time() - start) * 1000)

    return KBSearchResponse(
        query=body.query,
        results=results,
        total=len(results),
        searched_sources=searched_sources,
    )
