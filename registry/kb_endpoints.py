"""Unified Knowledge Base search endpoint.

Routes:
  POST /api/kb/search  — Hybrid FTS + vector RRF search across 9 tables, searched sequentially.
                         Sources: doc_pages, insights, decision_logs, ship_sessions,
                         agent_sessions, corrections, dev_changelog, bug_fixes, deferred_items.
"""
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from embedding_utils import get_embedding
import kb_service as svc
from kb_schemas import KBSearchRequest, KBSearchResponse, KBSearchResult, VALID_SOURCES

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/kb", tags=["kb"])


@router.post("/search", response_model=KBSearchResponse)
async def kb_search(
    body: KBSearchRequest,
    db: Session = Depends(get_db),
) -> KBSearchResponse:
    """Unified hybrid search across all 9 KB sources.

    Generates one query embedding, delegates to kb_service for per-source hybrid
    FTS + vector search with Reciprocal Rank Fusion (k=60), then constructs the
    response. Individual source failures are logged and skipped — degrades gracefully.
    """
    start = time.time()

    raw_sources: list[str] = body.sources if body.sources else list(svc.SOURCE_CONFIG.keys())
    invalid = [s for s in raw_sources if s not in VALID_SOURCES]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sources: {invalid}. Valid: {sorted(VALID_SOURCES)}",
        )
    requested_sources = list(dict.fromkeys(raw_sources))

    query_embedding: Optional[list[float]] = None
    try:
        query_embedding = await get_embedding(body.query)
    except Exception as embed_err:
        logger.warning("KB search embedding failed, falling back to FTS only: %s", embed_err)

    candidates, searched_sources, failed_sources = svc.kb_search(
        db, body.query, query_embedding,
        sources=requested_sources,
        project_name=body.project_name,
        limit=body.limit,
    )

    for source_name in failed_sources:
        registry_errors.labels(error_type=f"kb_search_{source_name}_failed").inc()

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
        for (_, score, row, source_name, title, content, metadata) in candidates
    ]

    registry_read_operations.labels(operation="kb_search").inc()
    registry_read_latency.observe((time.time() - start) * 1000)

    return KBSearchResponse(
        query=body.query,
        results=results,
        total=len(results),
        searched_sources=searched_sources,
    )
