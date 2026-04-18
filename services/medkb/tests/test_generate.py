import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from medkb.graph.nodes.generate import generate_node
from medkb.graph.state import RAGConfig, make_initial_state
from medkb.retriever.protocol import RetrievedChunk


@pytest.mark.asyncio
async def test_generate_produces_answer():
    config = RAGConfig(
        strategy="regular", corpora=["test"], k=8,
        generate_answer=True, generation_model="claude-sonnet-4-6",
        max_total_tokens=50000,
    )
    state = make_initial_state(
        query="What are the outcomes for pembrolizumab in NSCLC?",
        config=config, run_id="run-1", caller_id="test",
    )
    state["retrieved_chunks"] = [
        RetrievedChunk(
            chunk_id="c1", document_id="d1", corpus_id="corp1",
            text="KEYNOTE-024 demonstrated superior PFS of 10.3 months.",
            section="results", metadata={"title": "Pemb Review"},
            retriever_source="pgvector", raw_score=0.9, fusion_rank=1,
        ),
    ]

    mock_response = MagicMock()
    mock_response.content = "Pembrolizumab showed superior progression-free survival in NSCLC per KEYNOTE-024."
    mock_response.usage_metadata = {"input_tokens": 500, "output_tokens": 50}

    with patch("medkb.graph.nodes.generate.get_llm") as mock_get:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_llm

        result = await generate_node(state)
        assert "Pembrolizumab" in result["answer"]
        assert result["tokens_used"] > 0


@pytest.mark.asyncio
async def test_generate_skips_when_disabled():
    config = RAGConfig(
        strategy="regular", corpora=["test"], k=8,
        generate_answer=False,
    )
    state = make_initial_state(
        query="test", config=config, run_id="run-1", caller_id="test",
    )
    state["retrieved_chunks"] = []

    result = await generate_node(state)
    assert result.get("answer", "") == ""
