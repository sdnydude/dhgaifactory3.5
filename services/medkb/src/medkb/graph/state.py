from __future__ import annotations

from typing import Any, TypedDict

from medkb.retriever.protocol import RetrievedChunk


class RAGConfig(TypedDict, total=False):
    strategy: str
    corpora: list[str]
    k: int
    rerank: bool
    hybrid_weight_dense: float
    classifier_model: str
    generation_model: str
    grader_model: str
    groundedness_model: str
    rewriter_model: str
    generate_answer: bool
    include_citations: bool
    max_retries: int
    groundedness_threshold: float
    max_total_tokens: int
    metadata_filters: dict
    trace_tags: list[str]
    redaction_mode: str


class RAGState(TypedDict, total=False):
    query: str
    original_query: str
    run_id: str
    caller_id: str
    config: RAGConfig

    retrieved_chunks: list[RetrievedChunk]
    graded_chunks: list[RetrievedChunk]
    doc_grade: str
    rewrite_count: int
    regenerated: bool

    answer: str
    citations: list[dict]
    groundedness_score: float
    retrieval_score: float

    tokens_used: int
    redaction_count: int
    nodes_visited: list[str]
    error: str

    _retrievers: list[Any]


def make_initial_state(
    *,
    query: str,
    config: RAGConfig,
    run_id: str,
    caller_id: str,
) -> RAGState:
    return RAGState(
        query=query,
        original_query=query,
        run_id=run_id,
        caller_id=caller_id,
        config=config,
        retrieved_chunks=[],
        graded_chunks=[],
        doc_grade="",
        rewrite_count=0,
        regenerated=False,
        answer="",
        citations=[],
        groundedness_score=0.0,
        retrieval_score=0.0,
        tokens_used=0,
        redaction_count=0,
        nodes_visited=[],
        error="",
    )
