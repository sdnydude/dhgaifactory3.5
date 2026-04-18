import pytest
from medkb.graph.nodes.rerank import rerank_results_node
from medkb.graph.state import RAGConfig, make_initial_state
from medkb.retriever.protocol import RetrievedChunk


@pytest.mark.asyncio
async def test_rerank_deduplicates_by_chunk_id():
    config = RAGConfig(strategy="regular", corpora=["test"], k=2)
    state = make_initial_state(
        query="test", config=config, run_id="run-1", caller_id="test",
    )
    state["retrieved_chunks"] = [
        RetrievedChunk(chunk_id="c1", document_id="d1", corpus_id="corp1",
                       text="Hit 1", section=None, metadata={},
                       retriever_source="pgvector", raw_score=0.9),
        RetrievedChunk(chunk_id="c1", document_id="d1", corpus_id="corp1",
                       text="Hit 1", section=None, metadata={},
                       retriever_source="bm25", raw_score=0.85),
        RetrievedChunk(chunk_id="c2", document_id="d1", corpus_id="corp1",
                       text="Hit 2", section=None, metadata={},
                       retriever_source="pgvector", raw_score=0.8),
    ]

    result = await rerank_results_node(state)
    ids = [c.chunk_id for c in result["retrieved_chunks"]]
    assert len(ids) == 2
    assert len(set(ids)) == 2
