from __future__ import annotations

import logging

from medkb.graph.state import RAGState
from medkb.tracing import traced_node

logger = logging.getLogger(__name__)


@traced_node("medkb.graph", "redact")
async def redact_node(state: RAGState) -> dict:
    state["nodes_visited"].append("redact")
    return {"redaction_count": 0}
