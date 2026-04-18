import uuid
from medkb.models import Corpus, Document, Chunk


def test_corpus_defaults():
    c = Corpus(name="test_corpus", owner="dhg_cme", visibility="public")
    assert c.contains_phi is False
    assert c.default_chunker == "markdown"


def test_document_requires_corpus():
    d = Document(
        corpus_id=uuid.uuid4(),
        source="pubmed",
        source_id="PMID:12345",
        title="Test Article",
    )
    assert d.audience is None
    assert d.valid_to is None


def test_chunk_active_version_default():
    c = Chunk(
        document_id=uuid.uuid4(),
        corpus_id=uuid.uuid4(),
        chunk_index=0,
        chunk_text="Some text here.",
        chunk_tokens=5,
    )
    assert c.active_version == 1


def test_corpus_visibility_values():
    for vis in ("public", "dhg_internal", "division_only"):
        c = Corpus(name=f"test_{vis}", owner="test", visibility=vis)
        assert c.visibility == vis
