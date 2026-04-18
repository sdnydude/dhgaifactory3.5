import pytest
from unittest.mock import AsyncMock, patch

from medkb.retriever.protocol import RetrievedChunk


@pytest.mark.asyncio
async def test_query_returns_retrieved_chunks(client):
    chunk = RetrievedChunk(
        chunk_id="c1", document_id="d1", corpus_id="corp1",
        text="Test chunk", section="abstract", metadata={"title": "Test"},
        retriever_source="pgvector", raw_score=0.9,
    )

    async def mock_invoke(state):
        state["retrieved_chunks"] = [chunk]
        state["nodes_visited"] = ["redact", "analyze_query", "retrieve_fan", "rerank_results", "format_cite", "emit_feedback"]
        state["citations"] = [{
            "title": "Test", "source": "pgvector", "url": None,
            "chunk_id": "c1", "document_id": "d1", "similarity": 0.9,
        }]
        return state

    with patch("medkb.endpoints.query._graph") as mock_graph, \
         patch("medkb.endpoints.query._get_retrievers", return_value=[AsyncMock()]):
        mock_graph.ainvoke = AsyncMock(side_effect=mock_invoke)

        resp = await client.post("/v1/query", json={
            "query": "pembrolizumab NSCLC",
            "corpora": ["dhg_cme_sample"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["strategy_used"] == "auto"
        assert len(data["citations"]) >= 0
        assert "run_id" in data
