from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter

from medkb.config import Settings
from medkb.graph.builder import build_rag_graph
from medkb.graph.state import RAGConfig, make_initial_state
from medkb.metrics import QUERY_LATENCY, QUERY_REQUESTS, QUERY_ERRORS
from medkb.schemas import QueryDebug, QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1")

settings = Settings()
_graph = build_rag_graph()


def _get_retrievers(corpora: list[str]) -> list:
    return []


@router.post("/query", response_model=QueryResponse)
async def query(body: QueryRequest):
    run_id = f"medkb-{uuid.uuid4().hex[:12]}"
    start = time.monotonic()

    config = RAGConfig(
        strategy=body.strategy,
        corpora=body.corpora,
        k=body.k,
        rerank=body.rerank,
        hybrid_weight_dense=body.hybrid_weight_dense,
        classifier_model=body.classifier_model or settings.default_classifier_model,
        generation_model=body.generation_model or settings.default_generation_model,
        grader_model=body.grader_model or settings.default_grader_model,
        groundedness_model=body.groundedness_model or settings.default_groundedness_model,
        rewriter_model=body.rewriter_model or settings.default_rewriter_model,
        generate_answer=body.generate_answer,
        include_citations=body.include_citations,
        max_retries=body.max_retries,
        groundedness_threshold=body.groundedness_threshold,
        max_total_tokens=body.max_total_tokens,
        metadata_filters=body.metadata_filters or {},
        trace_tags=body.trace_tags,
    )

    state = make_initial_state(
        query=body.query,
        config=config,
        run_id=run_id,
        caller_id="anonymous",
    )
    state["_retrievers"] = _get_retrievers(body.corpora)

    try:
        result = await _graph.ainvoke(state)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        QUERY_REQUESTS.labels(
            strategy=result["config"]["strategy"],
            corpus=",".join(body.corpora),
            caller="anonymous",
            outcome="success",
        ).inc()
        QUERY_LATENCY.labels(
            strategy=result["config"]["strategy"],
            corpus=",".join(body.corpora),
            cache_hit="false",
        ).observe(elapsed_ms / 1000)

        return QueryResponse(
            run_id=run_id,
            answer=result.get("answer") or None,
            citations=result.get("citations", []),
            retrieved_chunks=[
                {
                    "chunk_id": c.chunk_id,
                    "text": c.text,
                    "section": c.section,
                    "score": c.raw_score,
                    "source": c.retriever_source,
                }
                for c in result.get("retrieved_chunks", [])
            ],
            strategy_used=result["config"]["strategy"],
            groundedness_score=result.get("groundedness_score"),
            latency_ms=elapsed_ms,
            tokens_used=result.get("tokens_used", 0),
            budget_exceeded=False,
            debug=QueryDebug(
                loops=0,
                rewrites=result.get("rewrite_count", 0),
                nodes_visited=result.get("nodes_visited", []),
                redaction_count=result.get("redaction_count", 0),
            ),
        )
    except Exception as exc:
        QUERY_ERRORS.labels(
            strategy=body.strategy,
            corpus=",".join(body.corpora),
            error_type=type(exc).__name__,
        ).inc()
        raise
