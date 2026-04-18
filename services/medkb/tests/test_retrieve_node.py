import pytest
from unittest.mock import AsyncMock

from medkb.graph.nodes.retrieve import retrieve_fan_node
from medkb.graph.state import RAGConfig, make_initial_state
from medkb.retriever.protocol import RetrievedChunk


@pytest.mark.asyncio
async def test_retrieve_fan_calls_retrievers():
    chunk = RetrievedChunk(
        chunk_id="c1", document_id="d1", corpus_id="corp1",
        text="test", section=None, metadata={},
        retriever_source="pgvector", raw_score=0.9,
    )
    mock_retriever = AsyncMock()
    mock_retriever.name = "pgvector"
    mock_retriever.retrieve = AsyncMock(return_value=[chunk])

    config = RAGConfig(strategy="regular", corpora=["dhg_internal"], k=8)
    state = make_initial_state(
        query="test query", config=config,
        run_id="run-1", caller_id="test",
    )
    state["_retrievers"] = [mock_retriever]

    result = await retrieve_fan_node(state)
    assert len(result["retrieved_chunks"]) == 1
    assert result["retrieved_chunks"][0].text == "test"
    mock_retriever.retrieve.assert_awaited_once()
