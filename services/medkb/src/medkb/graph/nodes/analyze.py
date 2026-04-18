from __future__ import annotations

import logging

from medkb.graph.state import RAGState
from medkb.tracing import traced_node

logger = logging.getLogger(__name__)


@traced_node("medkb.graph", "analyze_query")
async def analyze_query_node(state: RAGState) -> dict:
    state["nodes_visited"].append("analyze_query")
    strategy = state["config"].get("strategy", "regular")
    if strategy == "auto":
        strategy = "regular"
    return {"config": {**state["config"], "strategy": strategy}}
