from __future__ import annotations

import logging
import time

from langchain_core.messages import HumanMessage, SystemMessage

from medkb.graph.state import RAGState
from medkb.llm_factory import get_llm
from medkb.metrics import LLM_CALL_LATENCY, LLM_TOKENS
from medkb.tracing import traced_node

logger = logging.getLogger(__name__)

GRADING_PROMPT = """You are a document relevance grader. Given a user query and a retrieved document chunk,
determine if the chunk is relevant to answering the query.
Respond with exactly one word: "relevant" or "not_relevant"."""


@traced_node("medkb.graph", "grade_docs")
async def grade_docs_node(state: RAGState) -> dict:
    state["nodes_visited"].append("grade_docs")
    chunks = state.get("retrieved_chunks", [])
    model_spec = state["config"].get("grader_model", "ollama:qwen3:14b")
    llm = get_llm(model_spec)

    graded = []
    total_tokens = state.get("tokens_used", 0)

    for chunk in chunks:
        start = time.monotonic()
        messages = [
            SystemMessage(content=GRADING_PROMPT),
            HumanMessage(content=f"Query: {state['query']}\n\nDocument:\n{chunk.text}"),
        ]
        response = await llm.ainvoke(messages)
        elapsed = time.monotonic() - start

        usage = getattr(response, "usage_metadata", {}) or {}
        tokens_in = usage.get("input_tokens", 0)
        tokens_out = usage.get("output_tokens", 0)
        total_tokens += tokens_in + tokens_out

        LLM_TOKENS.labels(model=model_spec, node="grade_docs", direction="in").inc(tokens_in)
        LLM_TOKENS.labels(model=model_spec, node="grade_docs", direction="out").inc(tokens_out)
        LLM_CALL_LATENCY.labels(model=model_spec, node="grade_docs").observe(elapsed)

        verdict = response.content.strip().lower()
        if "relevant" in verdict and "not_relevant" not in verdict:
            graded.append(chunk)

    doc_grade = "good" if graded else "bad"
    logger.info(
        "grade_docs: %d/%d chunks relevant (grade=%s)",
        len(graded), len(chunks), doc_grade,
    )
    return {
        "graded_chunks": graded,
        "doc_grade": doc_grade,
        "tokens_used": total_tokens,
    }
