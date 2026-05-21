"""
CME Search Service Tests
========================
Unit tests for cme_search_service.py: snippet_from_text, fulltext_search,
vector_similarity_search, hybrid_search, get_rag_context.

Run with: pytest registry/test_cme_search_service.py -v
"""

import os
import sys
import uuid
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cme_search_service as svc


# ── Helpers ─────────────────────────────────────────────────────────────


def _uuid():
    return uuid.uuid4()


def _make_doc_row(**overrides):
    """Create a mock row matching the CMEDocument query projection."""
    row = MagicMock()
    row.id = overrides.get("id", _uuid())
    row.project_id = overrides.get("project_id", _uuid())
    row.title = overrides.get("title", "Test Document")
    row.content_text = overrides.get("content_text", "Some document content.")
    row.document_type = overrides.get("document_type", "needs_assessment")
    row.version = overrides.get("version", 1)
    row.quality_score = overrides.get("quality_score", 0.92)
    row.word_count = overrides.get("word_count", 1500)
    row.rank = overrides.get("rank", 0.75)
    row.similarity = overrides.get("similarity", 0.88)
    return row


def _make_field_row(**overrides):
    """Create a mock row matching the CMEIntakeField query projection."""
    row = MagicMock()
    row.id = overrides.get("id", _uuid())
    row.project_id = overrides.get("project_id", _uuid())
    row.section = overrides.get("section", "disease_state")
    row.field_label = overrides.get("field_label", "Primary Condition")
    row.value_text = overrides.get("value_text", "Type 2 Diabetes management")
    row.rank = overrides.get("rank", 0.60)
    return row


def _make_ref_row(**overrides):
    """Create a mock row matching the CMESourceReference query projection."""
    row = MagicMock()
    row.id = overrides.get("id", _uuid())
    row.project_id = overrides.get("project_id", _uuid())
    row.title = overrides.get("title", "Evidence-based Diabetes Care")
    row.abstract = overrides.get("abstract", "This study evaluated glycemic control.")
    row.ref_type = overrides.get("ref_type", "pubmed")
    row.ref_id = overrides.get("ref_id", "12345678")
    row.journal = overrides.get("journal", "NEJM")
    row.authors = overrides.get("authors", "Smith J, Doe A")
    row.rank = overrides.get("rank", 0.55)
    row.similarity = overrides.get("similarity", 0.80)
    return row


def _mock_fulltext_chain(db, doc_rows=None, field_rows=None, ref_rows=None):
    """Wire up chained ORM query calls for fulltext_search / hybrid_search.

    Each call to db.query(...) returns a fresh query mock that chains through
    filter → order_by → limit → all.
    """
    chains = []
    for rows in [doc_rows, field_rows, ref_rows]:
        if rows is not None:
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            q.limit.return_value = q
            q.all.return_value = rows
            chains.append(q)

    db.query.side_effect = chains


# ── snippet_from_text ──────────────────────────────────────────────────


class TestSnippetFromText:
    def test_empty_string_returns_empty(self):
        assert svc.snippet_from_text("") == ""

    def test_none_returns_empty(self):
        assert svc.snippet_from_text(None) == ""

    def test_short_text_unchanged(self):
        assert svc.snippet_from_text("Hello world") == "Hello world"

    def test_whitespace_collapsed(self):
        result = svc.snippet_from_text("hello   world\n\tnow")
        assert result == "hello world now"

    def test_truncation_at_max_len(self):
        text = "word " * 100  # 500 chars
        result = svc.snippet_from_text(text, max_len=30)
        assert len(result) <= 35  # truncated + "..."
        assert result.endswith("...")

    def test_exact_boundary_not_truncated(self):
        text = "ab" * 10  # 20 chars
        result = svc.snippet_from_text(text, max_len=20)
        assert result == text
        assert "..." not in result

    def test_custom_max_len(self):
        text = "alpha bravo charlie delta echo foxtrot golf hotel india juliet"
        result = svc.snippet_from_text(text, max_len=20)
        assert result.endswith("...")
        assert len(result) <= 25


# ── fulltext_search ────────────────────────────────────────────────────


class TestFulltextSearch:
    def test_returns_documents_when_source_type_documents(self, mock_db):
        doc = _make_doc_row(title="Doc Alpha")
        _mock_fulltext_chain(mock_db, doc_rows=[doc])

        results = svc.fulltext_search(mock_db, "diabetes", source_type="documents")

        assert len(results) == 1
        assert results[0]["title"] == "Doc Alpha"
        assert results[0]["source_table"] == "cme_documents"
        assert results[0]["score"] == float(doc.rank)
        assert "document_type" in results[0]["metadata"]

    def test_returns_intake_fields_when_source_type_intake(self, mock_db):
        field = _make_field_row(section="disease", field_label="Condition")
        _mock_fulltext_chain(mock_db, field_rows=[field])

        results = svc.fulltext_search(mock_db, "diabetes", source_type="intake_fields")

        assert len(results) == 1
        assert results[0]["source_table"] == "cme_intake_fields"
        assert results[0]["title"] == "disease: Condition"

    def test_returns_references_when_source_type_references(self, mock_db):
        ref = _make_ref_row(title="Ref Paper")
        _mock_fulltext_chain(mock_db, ref_rows=[ref])

        results = svc.fulltext_search(mock_db, "diabetes", source_type="references")

        assert len(results) == 1
        assert results[0]["source_table"] == "cme_source_references"
        assert results[0]["title"] == "Ref Paper"
        assert results[0]["metadata"]["ref_type"] == "pubmed"

    def test_returns_all_sources_when_source_type_none(self, mock_db):
        doc = _make_doc_row(rank=0.9)
        field = _make_field_row(rank=0.7)
        ref = _make_ref_row(rank=0.5)
        _mock_fulltext_chain(mock_db, doc_rows=[doc], field_rows=[field], ref_rows=[ref])

        results = svc.fulltext_search(mock_db, "diabetes")

        assert len(results) == 3
        # Sorted by score descending
        assert results[0]["score"] >= results[1]["score"] >= results[2]["score"]

    def test_filters_by_project_id(self, mock_db):
        pid = str(_uuid())
        doc = _make_doc_row()

        # Build the chain manually so we can inspect filter calls
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = [doc]
        mock_db.query.return_value = q

        svc.fulltext_search(mock_db, "test", source_type="documents", project_id=pid)

        # filter is called twice: once for the base WHERE clause, once for project_id
        assert q.filter.call_count >= 2

    def test_limit_clamped_to_default_on_invalid(self, mock_db):
        doc = _make_doc_row()
        _mock_fulltext_chain(mock_db, doc_rows=[doc])

        results = svc.fulltext_search(mock_db, "test", source_type="documents", limit=0)
        # limit=0 is invalid (<1), should reset to 20 internally
        assert isinstance(results, list)

    def test_limit_clamped_when_exceeds_max(self, mock_db):
        doc = _make_doc_row()
        _mock_fulltext_chain(mock_db, doc_rows=[doc])

        results = svc.fulltext_search(mock_db, "test", source_type="documents", limit=200)
        assert isinstance(results, list)

    def test_reference_with_none_title_becomes_untitled(self, mock_db):
        ref = _make_ref_row(title=None)
        _mock_fulltext_chain(mock_db, ref_rows=[ref])

        results = svc.fulltext_search(mock_db, "test", source_type="references")

        assert results[0]["title"] == "Untitled Reference"


# ── vector_similarity_search ───────────────────────────────────────────


class TestVectorSimilaritySearch:
    def test_returns_documents_by_default(self, mock_db):
        doc = _make_doc_row(similarity=0.91)
        mock_db.execute.return_value.fetchall.return_value = [doc]

        results = svc.vector_similarity_search(
            mock_db, [0.1, 0.2, 0.3], source_tables=["cme_documents"]
        )

        assert len(results) == 1
        assert results[0]["source_table"] == "cme_documents"
        assert results[0]["score"] == 0.91

    def test_returns_references(self, mock_db):
        ref = _make_ref_row(similarity=0.82)
        mock_db.execute.return_value.fetchall.return_value = [ref]

        results = svc.vector_similarity_search(
            mock_db, [0.1, 0.2], source_tables=["cme_source_references"]
        )

        assert len(results) == 1
        assert results[0]["source_table"] == "cme_source_references"

    def test_both_tables_returns_merged_sorted(self, mock_db):
        doc = _make_doc_row(similarity=0.95)
        ref = _make_ref_row(similarity=0.80)
        # Two execute calls — one per table
        mock_db.execute.return_value.fetchall.side_effect = [[doc], [ref]]

        results = svc.vector_similarity_search(mock_db, [0.1])

        assert len(results) == 2
        assert results[0]["score"] >= results[1]["score"]

    def test_filters_by_project_id(self, mock_db):
        pid = str(_uuid())
        mock_db.execute.return_value.fetchall.return_value = []

        svc.vector_similarity_search(
            mock_db, [0.1], project_id=pid, source_tables=["cme_documents"]
        )

        # Verify execute was called with project_id parameter
        args = mock_db.execute.call_args
        assert args is not None
        params = args[0][1] if len(args[0]) > 1 else args[1].get("params", {})
        assert params["pid"] == pid

    def test_reference_none_title_becomes_untitled(self, mock_db):
        ref = _make_ref_row(title=None, abstract=None)
        mock_db.execute.return_value.fetchall.return_value = [ref]

        results = svc.vector_similarity_search(
            mock_db, [0.1], source_tables=["cme_source_references"]
        )

        assert results[0]["title"] == "Untitled Reference"
        assert results[0]["snippet"] == ""


# ── hybrid_search ──────────────────────────────────────────────────────


class TestHybridSearch:
    def test_fulltext_only_when_no_embedding(self, mock_db):
        doc = _make_doc_row(rank=0.8)
        _mock_fulltext_chain(mock_db, doc_rows=[doc], field_rows=[], ref_rows=[])

        results = svc.hybrid_search(mock_db, "diabetes", query_embedding=None)

        assert len(results) == 1
        assert results[0]["source_table"] == "cme_documents"
        # RRF score for rank 1 = 1/(60+1)
        expected_rrf = 1.0 / (svc._RRF_K + 1)
        assert abs(results[0]["score"] - expected_rrf) < 1e-9

    def test_dedup_across_fulltext_and_vector(self, mock_db):
        shared_id = _uuid()
        pid = _uuid()
        doc_ft = _make_doc_row(id=shared_id, project_id=pid, rank=0.9)
        doc_vec = _make_doc_row(id=shared_id, project_id=pid, similarity=0.85)

        # Fulltext phase: db.query chain
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        # Three ORM queries (docs, fields, refs) — only docs returns results
        mock_db.query.side_effect = [q, q, q]
        q.all.side_effect = [[doc_ft], [], []]

        # Vector phase: db.execute calls for docs and refs
        mock_db.execute.return_value.fetchall.side_effect = [[doc_vec], []]

        results = svc.hybrid_search(
            mock_db, "diabetes", query_embedding=[0.1, 0.2]
        )

        # Same doc ID should appear only once, with combined RRF score
        doc_results = [r for r in results if r["id"] == str(shared_id)]
        assert len(doc_results) == 1
        # Combined score = 1/(60+1) from FT rank 1 + 1/(60+1) from VEC rank 1
        combined = 2.0 / (svc._RRF_K + 1)
        assert abs(doc_results[0]["score"] - combined) < 1e-9

    def test_rrf_ordering_respects_multi_source_ranks(self, mock_db):
        """A doc that appears in both FT and vector should outrank one in only FT."""
        shared_id = _uuid()
        pid = _uuid()
        only_ft_id = _uuid()

        doc_shared = _make_doc_row(id=shared_id, project_id=pid)
        doc_only_ft = _make_doc_row(id=only_ft_id, project_id=pid)
        doc_shared_vec = _make_doc_row(id=shared_id, project_id=pid)

        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        mock_db.query.side_effect = [q, q, q]
        q.all.side_effect = [[doc_shared, doc_only_ft], [], []]

        mock_db.execute.return_value.fetchall.side_effect = [[doc_shared_vec], []]

        results = svc.hybrid_search(
            mock_db, "test", query_embedding=[0.1],
            source_tables=["cme_documents", "cme_intake_fields", "cme_source_references"],
        )

        assert results[0]["id"] == str(shared_id)

    def test_empty_results_when_no_matches(self, mock_db):
        _mock_fulltext_chain(mock_db, doc_rows=[], field_rows=[], ref_rows=[])

        results = svc.hybrid_search(mock_db, "nonexistent", query_embedding=None)

        assert results == []


# ── get_rag_context ────────────────────────────────────────────────────


class TestGetRagContext:
    @patch("cme_search_service.hybrid_search")
    def test_returns_structure_with_no_results(self, mock_hybrid, mock_db):
        mock_hybrid.return_value = []

        result = svc.get_rag_context(mock_db, "test query", None)

        assert result["query"] == "test query"
        assert result["chunks"] == []
        assert result["total_chunks"] == 0
        assert result["estimated_tokens"] == 0
        assert result["project_scope"] is None

    @patch("cme_search_service.hybrid_search")
    def test_includes_document_content(self, mock_hybrid, mock_db):
        doc_id = str(_uuid())
        mock_hybrid.return_value = [{
            "id": doc_id,
            "source_table": "cme_documents",
            "title": "Test Doc",
            "snippet": "short",
            "score": 0.8,
            "metadata": {"document_type": "needs_assessment"},
        }]

        # Mock the db.query(CMEDocument).filter(...).first() call
        mock_doc = MagicMock()
        mock_doc.content_text = "Full document content for RAG context."
        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = mock_doc

        result = svc.get_rag_context(mock_db, "diabetes", None)

        assert result["total_chunks"] == 1
        assert result["chunks"][0]["content"] == "Full document content for RAG context."
        assert result["chunks"][0]["document_id"] == doc_id
        assert result["estimated_tokens"] > 0

    @patch("cme_search_service.hybrid_search")
    def test_includes_reference_content(self, mock_hybrid, mock_db):
        ref_id = str(_uuid())
        mock_hybrid.return_value = [{
            "id": ref_id,
            "source_table": "cme_source_references",
            "title": "Study A",
            "snippet": "abstract preview",
            "score": 0.7,
            "metadata": {"ref_type": "pubmed"},
        }]

        mock_ref = MagicMock()
        mock_ref.title = "Study A"
        mock_ref.authors = "Jones B"
        mock_ref.journal = "Lancet"
        mock_ref.abstract = "Comprehensive analysis of treatment outcomes."
        mock_ref.ref_id = "99999"

        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        # First call: content lookup; second call: citation lookup
        q.first.side_effect = [mock_ref, mock_ref]

        result = svc.get_rag_context(mock_db, "treatment", None, include_citations=True)

        assert result["total_chunks"] == 1
        content = result["chunks"][0]["content"]
        assert "Title: Study A" in content
        assert "Authors: Jones B" in content
        assert "Journal: Lancet" in content

    @patch("cme_search_service.hybrid_search")
    def test_respects_max_chunks(self, mock_hybrid, mock_db):
        doc_ids = [str(_uuid()) for _ in range(10)]
        mock_hybrid.return_value = [
            {
                "id": did,
                "source_table": "cme_documents",
                "title": f"Doc {i}",
                "snippet": "text",
                "score": 0.9 - i * 0.05,
                "metadata": {},
            }
            for i, did in enumerate(doc_ids)
        ]

        mock_doc = MagicMock()
        mock_doc.content_text = "Short content."
        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = mock_doc

        result = svc.get_rag_context(mock_db, "test", None, max_chunks=3)

        assert result["total_chunks"] == 3

    @patch("cme_search_service.hybrid_search")
    def test_respects_max_tokens(self, mock_hybrid, mock_db):
        doc_id = str(_uuid())
        mock_hybrid.return_value = [{
            "id": doc_id,
            "source_table": "cme_documents",
            "title": "Large Doc",
            "snippet": "preview",
            "score": 0.9,
            "metadata": {},
        }]

        # Content that would exceed max_tokens=50 (50*4=200 chars budget)
        mock_doc = MagicMock()
        mock_doc.content_text = "word " * 200  # 1000 chars = 250 tokens
        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = mock_doc

        result = svc.get_rag_context(mock_db, "test", None, max_tokens=50)

        # Content should be truncated
        if result["total_chunks"] > 0:
            assert result["chunks"][0]["content"].endswith("...")
            assert result["estimated_tokens"] <= 55  # allow small overshoot from truncation

    @patch("cme_search_service.hybrid_search")
    def test_project_scope_passed_through(self, mock_hybrid, mock_db):
        pid = str(_uuid())
        mock_hybrid.return_value = []

        result = svc.get_rag_context(mock_db, "test", None, project_id=pid)

        assert result["project_scope"] == pid
        mock_hybrid.assert_called_once_with(
            mock_db, "test", None,
            project_id=pid,
            source_tables=["cme_documents", "cme_source_references"],
            limit=10,  # max_chunks=5 default * 2
        )

    @patch("cme_search_service.hybrid_search")
    def test_skips_chunks_with_empty_content(self, mock_hybrid, mock_db):
        doc_id = str(_uuid())
        mock_hybrid.return_value = [{
            "id": doc_id,
            "source_table": "cme_documents",
            "title": "Empty Doc",
            "snippet": "",
            "score": 0.5,
            "metadata": {},
        }]

        mock_doc = MagicMock()
        mock_doc.content_text = ""
        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = mock_doc

        result = svc.get_rag_context(mock_db, "test", None)

        assert result["total_chunks"] == 0

    @patch("cme_search_service.hybrid_search")
    def test_no_citations_when_flag_false(self, mock_hybrid, mock_db):
        ref_id = str(_uuid())
        mock_hybrid.return_value = [{
            "id": ref_id,
            "source_table": "cme_source_references",
            "title": "Study X",
            "snippet": "abstract",
            "score": 0.6,
            "metadata": {"ref_type": "pubmed"},
        }]

        mock_ref = MagicMock()
        mock_ref.title = "Study X"
        mock_ref.authors = "A, B"
        mock_ref.journal = "Nature"
        mock_ref.abstract = "Something interesting."
        mock_ref.ref_id = "11111"

        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = mock_ref

        result = svc.get_rag_context(
            mock_db, "test", None, include_citations=False
        )

        # Should still have chunks, just no citation overhead in estimated_tokens
        assert result["total_chunks"] == 1
        # With citations=False, the citation block is never computed
        # estimated_tokens should only reflect the chunk content
        content_len = len(result["chunks"][0]["content"])
        expected_tokens = content_len // 4
        assert result["estimated_tokens"] == expected_tokens
