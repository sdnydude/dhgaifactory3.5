import pytest
from medkb.graph.nodes.format_cite import format_cite_node
from medkb.graph.state import RAGConfig, make_initial_state
from medkb.retriever.protocol import RetrievedChunk


@pytest.mark.asyncio
async def test_format_cite_builds_citations():
    config = RAGConfig(strategy="regular", corpora=["pubmed"], k=8, include_citations=True)
    state = make_initial_state(
        query="test", config=config, run_id="run-1", caller_id="test",
    )
    state["retrieved_chunks"] = [
        RetrievedChunk(
            chunk_id="c1", document_id="d1", corpus_id="corp1",
            text="Drug X improves outcomes.", section="abstract",
            metadata={"title": "Drug X Trial", "url": "https://pubmed.ncbi.nlm.nih.gov/12345"},
            retriever_source="pgvector", raw_score=0.91, fusion_rank=1,
        ),
    ]
    state["answer"] = "Drug X shows promise."

    result = await format_cite_node(state)
    assert len(result["citations"]) == 1
    assert result["citations"][0]["chunk_id"] == "c1"
    assert result["citations"][0]["similarity"] == 0.91


@pytest.mark.asyncio
async def test_format_cite_skip_when_no_citations():
    config = RAGConfig(strategy="regular", corpora=["pubmed"], k=8, include_citations=False)
    state = make_initial_state(
        query="test", config=config, run_id="run-1", caller_id="test",
    )
    state["retrieved_chunks"] = []
    result = await format_cite_node(state)
    assert result["citations"] == []
