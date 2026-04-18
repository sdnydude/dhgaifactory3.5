import pytest
from unittest.mock import AsyncMock

from medkb.retriever.hybrid import HybridRetriever
from medkb.retriever.protocol import Retriever, RetrievedChunk


def test_hybrid_implements_protocol():
    retriever = HybridRetriever(
        dense=AsyncMock(),
        sparse=AsyncMock(),
    )
    assert isinstance(retriever, Retriever)
    assert retriever.name == "hybrid"


@pytest.mark.asyncio
async def test_rrf_fusion_merges_and_ranks():
    dense_chunks = [
        RetrievedChunk(chunk_id="c1", document_id="d1", corpus_id="corp1",
                       text="Dense hit 1", section=None, metadata={},
                       retriever_source="pgvector", raw_score=0.9),
        RetrievedChunk(chunk_id="c2", document_id="d1", corpus_id="corp1",
                       text="Dense hit 2", section=None, metadata={},
                       retriever_source="pgvector", raw_score=0.8),
    ]
    sparse_chunks = [
        RetrievedChunk(chunk_id="c2", document_id="d1", corpus_id="corp1",
                       text="Dense hit 2", section=None, metadata={},
                       retriever_source="bm25", raw_score=0.85),
        RetrievedChunk(chunk_id="c3", document_id="d1", corpus_id="corp1",
                       text="Sparse only hit", section=None, metadata={},
                       retriever_source="bm25", raw_score=0.7),
    ]

    mock_dense = AsyncMock()
    mock_dense.name = "pgvector"
    mock_dense.retrieve = AsyncMock(return_value=dense_chunks)

    mock_sparse = AsyncMock()
    mock_sparse.name = "bm25"
    mock_sparse.retrieve = AsyncMock(return_value=sparse_chunks)

    retriever = HybridRetriever(dense=mock_dense, sparse=mock_sparse, weight_dense=0.7)
    results = await retriever.retrieve("test query", k=3)

    assert len(results) == 3
    assert results[0].chunk_id == "c2"
    assert results[0].retriever_source == "hybrid"
    for i, chunk in enumerate(results):
        assert chunk.fusion_rank == i + 1
