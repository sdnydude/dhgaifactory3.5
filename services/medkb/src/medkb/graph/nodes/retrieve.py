from __future__ import annotations

import asyncio
import logging
import time

from medkb.graph.state import RAGState
from medkb.metrics import RETRIEVER_LATENCY, RETRIEVER_ERRORS
from medkb.retriever.protocol import RetrievedChunk
from medkb.tracing import traced_node

logger = logging.getLogger(__name__)


@traced_node("medkb.graph", "retrieve_fan")
async def retrieve_fan_node(state: RAGState) -> dict:
    state["nodes_visited"].append("retrieve_fan")
    retrievers = state.get("_retrievers", [])
    query = state["query"]
    k = state["config"].get("k", 8)
    corpus_ids = state["config"].get("corpora", [])
    filters = state["config"].get("metadata_filters")

    async def _call(retriever) -> list[RetrievedChunk]:
        start = time.monotonic()
        try:
            results = await retriever.retrieve(
                query, k=k, corpus_ids=corpus_ids, filters=filters,
            )
            elapsed = time.monotonic() - start
            RETRIEVER_LATENCY.labels(
                retriever=retriever.name, operation="retrieve",
            ).observe(elapsed)
            return results
        except Exception as exc:
            RETRIEVER_ERRORS.labels(
                retriever=retriever.name, error_type=type(exc).__name__,
            ).inc()
            logger.warning("Retriever %s failed: %s", retriever.name, exc)
            return []

    all_results = await asyncio.gather(*[_call(r) for r in retrievers])
    merged: list[RetrievedChunk] = []
    for results in all_results:
        merged.extend(results)

    return {"retrieved_chunks": merged}
