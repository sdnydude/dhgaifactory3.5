import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from medkb.graph.nodes.grade import grade_docs_node
from medkb.graph.state import RAGConfig, make_initial_state
from medkb.retriever.protocol import RetrievedChunk


@pytest.mark.asyncio
async def test_grade_returns_good_for_relevant_chunks():
    config = RAGConfig(
        strategy="crag", corpora=["test"], k=8,
        grader_model="ollama:qwen3:14b", max_total_tokens=50000,
    )
    state = make_initial_state(
        query="pembrolizumab outcomes", config=config,
        run_id="run-1", caller_id="test",
    )
    state["retrieved_chunks"] = [
        RetrievedChunk(chunk_id="c1", document_id="d1", corpus_id="corp1",
                       text="KEYNOTE-024 showed superior PFS for pembrolizumab.",
                       section="results", metadata={},
                       retriever_source="pgvector", raw_score=0.9, fusion_rank=1),
    ]

    mock_response = MagicMock()
    mock_response.content = "relevant"
    mock_response.usage_metadata = {"input_tokens": 200, "output_tokens": 5}

    with patch("medkb.graph.nodes.grade.get_llm") as mock_get:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_llm

        result = await grade_docs_node(state)
        assert result["doc_grade"] == "good"
        assert len(result["retrieved_chunks"]) == 1


@pytest.mark.asyncio
async def test_grade_returns_bad_for_irrelevant_chunks():
    config = RAGConfig(
        strategy="crag", corpora=["test"], k=8,
        grader_model="ollama:qwen3:14b", max_total_tokens=50000,
    )
    state = make_initial_state(
        query="pembrolizumab outcomes", config=config,
        run_id="run-1", caller_id="test",
    )
    state["retrieved_chunks"] = [
        RetrievedChunk(chunk_id="c1", document_id="d1", corpus_id="corp1",
                       text="Marketing strategies for healthcare events.",
                       section=None, metadata={},
                       retriever_source="pgvector", raw_score=0.5, fusion_rank=1),
    ]

    mock_response = MagicMock()
    mock_response.content = "not_relevant"
    mock_response.usage_metadata = {"input_tokens": 200, "output_tokens": 5}

    with patch("medkb.graph.nodes.grade.get_llm") as mock_get:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_llm

        result = await grade_docs_node(state)
        assert result["doc_grade"] == "bad"
        assert len(result["retrieved_chunks"]) == 0
