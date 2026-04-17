from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

QUERY_REQUESTS = Counter(
    "medkb_query_requests",
    "Total query requests",
    ["strategy", "corpus", "caller", "outcome"],
)

QUERY_LATENCY = Histogram(
    "medkb_query_latency_seconds",
    "Query latency",
    ["strategy", "corpus", "cache_hit"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

QUERY_ERRORS = Counter(
    "medkb_query_errors",
    "Query errors",
    ["strategy", "corpus", "error_type"],
)

GROUNDEDNESS_SCORE = Histogram(
    "medkb_groundedness_score",
    "Groundedness score distribution",
    ["corpus", "strategy"],
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

LLM_TOKENS = Counter(
    "medkb_llm_tokens",
    "LLM token usage",
    ["model", "node", "direction"],
)

LLM_CALL_LATENCY = Histogram(
    "medkb_llm_call_latency_seconds",
    "LLM call latency per node",
    ["model", "node"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)

RETRIEVER_LATENCY = Histogram(
    "medkb_retriever_latency_seconds",
    "Retriever latency",
    ["retriever", "operation"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

RETRIEVER_ERRORS = Counter(
    "medkb_retriever_errors",
    "Retriever errors",
    ["retriever", "error_type"],
)

CACHE_OPS = Counter(
    "medkb_cache_operations",
    "Cache operations",
    ["cache", "operation", "outcome"],
)

CHUNKS_TOTAL = Gauge(
    "medkb_chunks_total",
    "Total chunks per corpus",
    ["corpus"],
)

REDACTION_EVENTS = Counter(
    "medkb_redaction_events",
    "PII/PHI redaction events",
    ["pii_type", "corpus", "action"],
)

BUDGET_EXCEEDED = Counter(
    "medkb_budget_exceeded",
    "Token budget exceeded events",
    ["caller", "reason"],
)
