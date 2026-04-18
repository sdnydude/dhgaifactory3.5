# services/medkb/src/medkb/schemas.py
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    corpora: list[str]
    strategy: Literal["regular", "crag", "srag", "agentic", "auto"] = "auto"
    k: int = Field(default=8, ge=1, le=100)
    rerank: bool = False
    hybrid_weight_dense: float = Field(default=0.7, ge=0.0, le=1.0)
    classifier_model: str | None = None
    generation_model: str | None = None
    grader_model: str | None = None
    groundedness_model: str | None = None
    rewriter_model: str | None = None
    generate_answer: bool = True
    include_citations: bool = True
    max_retries: int = Field(default=2, ge=0, le=5)
    groundedness_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    max_total_tokens: int = Field(default=50_000, ge=1_000, le=500_000)
    metadata_filters: dict | None = None
    trace_tags: list[str] = Field(default_factory=list)


class CitationOut(BaseModel):
    title: str | None
    source: str
    url: str | None
    chunk_id: str
    document_id: str
    similarity: float


class QueryDebug(BaseModel):
    loops: int = 0
    rewrites: int = 0
    nodes_visited: list[str] = Field(default_factory=list)
    redaction_count: int = 0
    truncated_at_node: str | None = None


class QueryResponse(BaseModel):
    run_id: str
    answer: str | None = None
    citations: list[CitationOut] = Field(default_factory=list)
    retrieved_chunks: list[dict] = Field(default_factory=list)
    strategy_used: str
    groundedness_score: float | None = None
    retrieval_score: float | None = None
    latency_ms: int
    tokens_used: int
    budget_exceeded: bool = False
    trace_url: str | None = None
    debug: QueryDebug = Field(default_factory=QueryDebug)


class RetrieveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    corpora: list[str]
    k: int = Field(default=8, ge=1, le=100)
    hybrid_weight_dense: float = Field(default=0.7, ge=0.0, le=1.0)
    metadata_filters: dict | None = None


class RetrieveResponse(BaseModel):
    run_id: str
    chunks: list[dict]
    latency_ms: int


class CorpusOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    owner: str
    visibility: str
    contains_phi: bool
    default_chunker: str


class CorpusCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    owner: str
    visibility: Literal["public", "dhg_internal", "division_only"] = "dhg_internal"
    contains_phi: bool = False
    default_chunker: str = "markdown"


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    hint: str | None = None
