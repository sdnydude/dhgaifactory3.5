import pytest
from unittest.mock import AsyncMock

from medkb.graph.builder import build_rag_graph
from medkb.graph.state import RAGConfig, make_initial_state
from medkb.retriever.protocol import RetrievedChunk


@pytest.mark.asyncio
async def test_regular_strategy_visits_expected_nodes():
    chunk = RetrievedChunk(
        chunk_id="c1", document_id="d1", corpus_id="corp1",
        text="Test chunk text", section=None, metadata={},
        retriever_source="pgvector", raw_score=0.9,
    )
    mock_retriever = AsyncMock()
    mock_retriever.name = "pgvector"
    mock_retriever.retrieve = AsyncMock(return_value=[chunk])

    graph = build_rag_graph()
    config = RAGConfig(
        strategy="regular", corpora=["test"], k=8,
        generate_answer=False, include_citations=True,
    )
    state = make_initial_state(
        query="test query", config=config,
        run_id="run-1", caller_id="test",
    )
    state["_retrievers"] = [mock_retriever]

    result = await graph.ainvoke(state)
    visited = result["nodes_visited"]
    assert "redact" in visited
    assert "analyze_query" in visited
    assert "retrieve_fan" in visited
    assert "rerank_results" in visited
    assert "format_cite" in visited
    assert "emit_feedback" in visited
    assert len(result["retrieved_chunks"]) == 1
