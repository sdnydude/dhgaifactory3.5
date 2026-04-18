import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from medkb.retriever.pgvector import PgVectorRetriever
from medkb.retriever.protocol import Retriever


def test_pgvector_implements_protocol():
    retriever = PgVectorRetriever(
        session_factory=MagicMock(),
        embed_fn=AsyncMock(),
    )
    assert isinstance(retriever, Retriever)
    assert retriever.name == "pgvector"


@pytest.mark.asyncio
async def test_pgvector_retrieve_returns_chunks():
    mock_session = AsyncMock()
    corpus_id = str(uuid.uuid4())
    chunk_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    mock_row = MagicMock()
    mock_row.id = uuid.UUID(chunk_id)
    mock_row.document_id = uuid.UUID(doc_id)
    mock_row.corpus_id = uuid.UUID(corpus_id)
    mock_row.chunk_text = "Pembrolizumab shows efficacy in NSCLC."
    mock_row.section = "abstract"
    mock_row.metadata_ = {"year": 2024}
    mock_row.distance = 0.15

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]
    mock_session.execute = AsyncMock(return_value=mock_result)

    session_ctx = AsyncMock()
    session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    session_ctx.__aexit__ = AsyncMock(return_value=False)

    async def fake_session_factory():
        return session_ctx

    embed_fn = AsyncMock(return_value=[0.1] * 768)

    retriever = PgVectorRetriever(
        session_factory=fake_session_factory,
        embed_fn=embed_fn,
    )
    results = await retriever.retrieve(
        "pembrolizumab NSCLC",
        k=5,
        corpus_ids=[corpus_id],
    )
    assert len(results) == 1
    assert results[0].text == "Pembrolizumab shows efficacy in NSCLC."
    assert results[0].retriever_source == "pgvector"
    embed_fn.assert_awaited_once()
