import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock

from medkb.retriever.bm25 import BM25Retriever
from medkb.retriever.protocol import Retriever


def test_bm25_implements_protocol():
    retriever = BM25Retriever(session_factory=MagicMock())
    assert isinstance(retriever, Retriever)
    assert retriever.name == "bm25"


@pytest.mark.asyncio
async def test_bm25_retrieve_returns_chunks():
    mock_session = AsyncMock()
    corpus_id = str(uuid.uuid4())
    chunk_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    mock_row = MagicMock()
    mock_row.id = uuid.UUID(chunk_id)
    mock_row.document_id = uuid.UUID(doc_id)
    mock_row.corpus_id = uuid.UUID(corpus_id)
    mock_row.chunk_text = "Pembrolizumab efficacy in lung cancer."
    mock_row.section = "abstract"
    mock_row.metadata_ = {}
    mock_row.rank = 0.85

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]
    mock_session.execute = AsyncMock(return_value=mock_result)

    session_ctx = AsyncMock()
    session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    session_ctx.__aexit__ = AsyncMock(return_value=False)

    async def fake_session_factory():
        return session_ctx

    retriever = BM25Retriever(session_factory=fake_session_factory)
    results = await retriever.retrieve(
        "pembrolizumab lung cancer",
        k=5,
        corpus_ids=[corpus_id],
    )
    assert len(results) == 1
    assert results[0].retriever_source == "bm25"
