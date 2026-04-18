from __future__ import annotations

from langgraph.graph import END, StateGraph

from medkb.graph.edges import (
    should_check_grounded,
    should_grade,
    should_regenerate,
    should_rewrite,
)
from medkb.graph.nodes.analyze import analyze_query_node
from medkb.graph.nodes.emit_feedback import emit_feedback_node
from medkb.graph.nodes.format_cite import format_cite_node
from medkb.graph.nodes.generate import generate_node
from medkb.graph.nodes.grade import grade_docs_node
from medkb.graph.nodes.redact import redact_node
from medkb.graph.nodes.rerank import rerank_results_node
from medkb.graph.nodes.retrieve import retrieve_fan_node
from medkb.graph.nodes.rewrite import rewrite_query_node
from medkb.graph.state import RAGState


def build_rag_graph():
    graph = StateGraph(RAGState)

    graph.add_node("redact", redact_node)
    graph.add_node("analyze_query", analyze_query_node)
    graph.add_node("retrieve_fan", retrieve_fan_node)
    graph.add_node("rerank_results", rerank_results_node)
    graph.add_node("grade_docs", grade_docs_node)
    graph.add_node("rewrite_query", rewrite_query_node)
    graph.add_node("generate", generate_node)
    graph.add_node("format_cite", format_cite_node)
    graph.add_node("emit_feedback", emit_feedback_node)

    graph.set_entry_point("redact")
    graph.add_edge("redact", "analyze_query")
    graph.add_edge("analyze_query", "retrieve_fan")
    graph.add_edge("retrieve_fan", "rerank_results")

    graph.add_conditional_edges(
        "rerank_results",
        should_grade,
        {"grade_docs": "grade_docs", "generate": "generate"},
    )

    graph.add_conditional_edges(
        "grade_docs",
        should_rewrite,
        {"rewrite_query": "rewrite_query", "generate": "generate"},
    )

    graph.add_edge("rewrite_query", "retrieve_fan")

    graph.add_edge("generate", "format_cite")
    graph.add_edge("format_cite", "emit_feedback")
    graph.add_edge("emit_feedback", END)

    return graph.compile()
