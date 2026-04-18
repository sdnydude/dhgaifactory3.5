from __future__ import annotations

import logging

from medkb.graph.state import RAGState
from medkb.tracing import traced_node

logger = logging.getLogger(__name__)


@traced_node("medkb.graph", "format_cite")
async def format_cite_node(state: RAGState) -> dict:
    state["nodes_visited"].append("format_cite")
    if not state["config"].get("include_citations", True):
        return {"citations": []}

    citations = []
    for chunk in state.get("retrieved_chunks", []):
        citations.append({
            "title": chunk.metadata.get("title"),
            "source": chunk.retriever_source,
            "url": chunk.metadata.get("url"),
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "similarity": chunk.raw_score,
        })
    return {"citations": citations}
