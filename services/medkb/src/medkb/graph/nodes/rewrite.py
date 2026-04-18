from __future__ import annotations

import logging
import time

from langchain_core.messages import HumanMessage, SystemMessage

from medkb.graph.state import RAGState
from medkb.llm_factory import get_llm
from medkb.metrics import LLM_CALL_LATENCY, LLM_TOKENS
from medkb.tracing import traced_node

logger = logging.getLogger(__name__)

REWRITE_PROMPT = """You are a search query optimizer. The user's query did not retrieve relevant documents.
Rewrite the query to be more specific and likely to match relevant medical literature.
Return ONLY the rewritten query, nothing else."""


@traced_node("medkb.graph", "rewrite_query")
async def rewrite_query_node(state: RAGState) -> dict:
    state["nodes_visited"].append("rewrite_query")
    model_spec = state["config"].get("rewriter_model", "ollama:llama3.1:8b")
    llm = get_llm(model_spec)

    start = time.monotonic()
    messages = [
        SystemMessage(content=REWRITE_PROMPT),
        HumanMessage(content=f"Original query: {state['query']}"),
    ]
    response = await llm.ainvoke(messages)
    elapsed = time.monotonic() - start

    usage = getattr(response, "usage_metadata", {}) or {}
    tokens_in = usage.get("input_tokens", 0)
    tokens_out = usage.get("output_tokens", 0)
    total_tokens = state.get("tokens_used", 0) + tokens_in + tokens_out

    LLM_TOKENS.labels(model=model_spec, node="rewrite_query", direction="in").inc(tokens_in)
    LLM_TOKENS.labels(model=model_spec, node="rewrite_query", direction="out").inc(tokens_out)
    LLM_CALL_LATENCY.labels(model=model_spec, node="rewrite_query").observe(elapsed)

    rewritten = response.content.strip()
    rewrite_count = state.get("rewrite_count", 0) + 1

    logger.info("rewrite_query: attempt %d, new query: %s", rewrite_count, rewritten[:100])
    return {
        "query": rewritten,
        "rewrite_count": rewrite_count,
        "tokens_used": total_tokens,
    }
