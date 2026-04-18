import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from medkb.graph.nodes.rewrite import rewrite_query_node
from medkb.graph.state import RAGConfig, make_initial_state


@pytest.mark.asyncio
async def test_rewrite_produces_new_query():
    config = RAGConfig(
        strategy="crag", corpora=["test"], k=8,
        rewriter_model="ollama:llama3.1:8b", max_total_tokens=50000,
    )
    state = make_initial_state(
        query="pemb nsclc outcomes", config=config,
        run_id="run-1", caller_id="test",
    )
    state["rewrite_count"] = 0

    mock_response = MagicMock()
    mock_response.content = "What are the clinical outcomes of pembrolizumab treatment in non-small cell lung cancer?"
    mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 20}

    with patch("medkb.graph.nodes.rewrite.get_llm") as mock_get:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_llm

        result = await rewrite_query_node(state)
        assert "pembrolizumab" in result["query"].lower()
        assert result["rewrite_count"] == 1
