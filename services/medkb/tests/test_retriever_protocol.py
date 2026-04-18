from medkb.retriever.protocol import Retriever, RetrievedChunk


def test_retrieved_chunk_fields():
    chunk = RetrievedChunk(
        chunk_id="abc",
        document_id="def",
        corpus_id="ghi",
        text="sample text",
        section="abstract",
        metadata={"year": 2024},
        retriever_source="pgvector",
        raw_score=0.95,
    )
    assert chunk.fusion_rank is None
    assert chunk.retriever_source == "pgvector"


def test_retriever_is_runtime_checkable():
    assert isinstance(Retriever, type)

    class FakeRetriever:
        name = "fake"
        async def retrieve(self, query, *, k, filters=None, corpus_ids=None):
            return []

    assert isinstance(FakeRetriever(), Retriever)
