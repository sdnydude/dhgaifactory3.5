from __future__ import annotations

import logging

from medkb.graph.state import RAGState
from medkb.tracing import traced_node

logger = logging.getLogger(__name__)


@traced_node("medkb.graph", "rerank_results")
async def rerank_results_node(state: RAGState) -> dict:
    state["nodes_visited"].append("rerank_results")
    chunks = state.get("retrieved_chunks", [])
    k = state["config"].get("k", 8)

    seen: set[str] = set()
    deduped = []
    for chunk in chunks:
        if chunk.chunk_id not in seen:
            seen.add(chunk.chunk_id)
            deduped.append(chunk)

    sorted_chunks = sorted(deduped, key=lambda c: c.raw_score, reverse=True)[:k]
    for i, chunk in enumerate(sorted_chunks):
        chunk.fusion_rank = i + 1
    return {"retrieved_chunks": sorted_chunks}
