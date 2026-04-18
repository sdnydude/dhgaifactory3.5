from __future__ import annotations

import logging

from medkb.graph.state import RAGState
from medkb.tracing import traced_node

logger = logging.getLogger(__name__)


@traced_node("medkb.graph", "emit_feedback")
async def emit_feedback_node(state: RAGState) -> dict:
    state["nodes_visited"].append("emit_feedback")
    logger.info(
        "emit_feedback stub: run_id=%s strategy=%s",
        state.get("run_id"),
        state["config"].get("strategy"),
    )
    return {}
