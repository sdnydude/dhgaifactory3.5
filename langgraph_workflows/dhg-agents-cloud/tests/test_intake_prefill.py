"""
Tests for the Intake Prefill Agent (intake_prefill_agent.py).

Covers:
- Graph construction and node inventory
- Individual node functions with mocked LLM
- Validation logic
- Error handling / fallback behaviour

Run with: pytest langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py -v
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import intake_prefill_agent as ipa


class TestGraphStructure:
    """Verify the compiled graph has the expected nodes and edges."""

    def test_graph_has_four_nodes(self):
        nodes = list(ipa.graph.nodes)
        expected = {"search_literature", "build_context", "generate_prefill", "validate_output"}
        # LangGraph adds __start__ and __end__ automatically
        agent_nodes = {n for n in nodes if not n.startswith("__")}
        assert agent_nodes == expected

    def test_graph_exports_as_graph(self):
        """The module-level `graph` is a compiled StateGraph."""
        assert hasattr(ipa, "graph")
        assert hasattr(ipa.graph, "invoke")


# ---------------------------------------------------------------------------
# search_literature node tests
# ---------------------------------------------------------------------------

def _make_sample_state(**overrides) -> dict:
    """Build a minimal IntakePrefillState dict for unit tests."""
    base = {
        "therapeutic_area": "cardiology",
        "disease_state": "heart failure with reduced ejection fraction",
        "target_audience_primary": ["cardiologists", "internists"],
        "target_hcp_types": ["MD/DO"],
        "project_name": "HFrEF GDMT Update 2026",
        "messages": [],
        "pubmed_results": [],
        "research_context": "",
        "prefill_sections": {},
        "research_summary": "",
        "confidence": {},
        "errors": [],
        "total_tokens": 0,
        "total_cost": 0.0,
    }
    base.update(overrides)
    return base


class TestSearchLiterature:
    """Tests for search_literature node."""

    @pytest.mark.asyncio
    async def test_returns_pubmed_results(self):
        """Successful PubMed search populates pubmed_results."""
        sample_articles = [
            {"pmid": "12345", "title": "HFrEF GDMT Review", "abstract": "...", "year": 2025},
            {"pmid": "67890", "title": "SGLT2i in Heart Failure", "abstract": "...", "year": 2024},
        ]
        mock_pubmed = MagicMock()
        mock_pubmed.search = AsyncMock(return_value=["12345", "67890"])
        mock_pubmed.fetch_details = AsyncMock(return_value=sample_articles)

        state = _make_sample_state()

        with patch.object(ipa, "PubMedClient", return_value=mock_pubmed):
            result = await ipa.search_literature(state)

        assert "pubmed_results" in result
        assert len(result["pubmed_results"]) == 2
        assert result["pubmed_results"][0]["pmid"] == "12345"

    @pytest.mark.asyncio
    async def test_builds_query_from_disease_and_area(self):
        """The PubMed query includes disease_state and therapeutic_area."""
        mock_pubmed = MagicMock()
        mock_pubmed.search = AsyncMock(return_value=[])
        mock_pubmed.fetch_details = AsyncMock(return_value=[])

        state = _make_sample_state(
            disease_state="atrial fibrillation",
            therapeutic_area="electrophysiology",
        )

        with patch.object(ipa, "PubMedClient", return_value=mock_pubmed):
            await ipa.search_literature(state)

        call_args = mock_pubmed.search.call_args
        query = call_args[0][0] if call_args[0] else call_args[1].get("query", "")
        assert "atrial fibrillation" in query
        assert "electrophysiology" in query

    @pytest.mark.asyncio
    async def test_handles_pubmed_failure_gracefully(self):
        """PubMed failure returns empty results + error record."""
        mock_pubmed = MagicMock()
        mock_pubmed.search = AsyncMock(side_effect=Exception("PubMed API timeout"))

        state = _make_sample_state()

        with patch.object(ipa, "PubMedClient", return_value=mock_pubmed):
            result = await ipa.search_literature(state)

        assert result["pubmed_results"] == []
        assert len(result["errors"]) == 1
        assert "PubMed" in result["errors"][0]["error"]


# ---------------------------------------------------------------------------
# build_context node tests
# ---------------------------------------------------------------------------

class TestBuildContext:
    """Tests for build_context node (no LLM call — pure data transformation)."""

    @pytest.mark.asyncio
    async def test_builds_context_from_articles(self):
        """Articles are formatted into a research context string."""
        articles = [
            {
                "pmid": "11111",
                "title": "SGLT2 Inhibitors in HFrEF",
                "abstract": "SGLT2i showed significant reduction in hospitalization.",
                "year": 2025,
                "journal": "NEJM",
                "journal_abbrev": "N Engl J Med",
            },
        ]
        state = _make_sample_state(pubmed_results=articles)
        result = await ipa.build_context(state)

        assert "research_context" in result
        assert "SGLT2 Inhibitors in HFrEF" in result["research_context"]
        assert "heart failure" in result["research_context"].lower()
        assert "research_summary" in result
        assert "1" in result["research_summary"]  # "Reviewed 1 recent publications"

    @pytest.mark.asyncio
    async def test_empty_articles_returns_fallback_context(self):
        """No PubMed results produces a fallback context string."""
        state = _make_sample_state(pubmed_results=[])
        result = await ipa.build_context(state)

        assert "research_context" in result
        assert "no pubmed results" in result["research_context"].lower() or \
               "general medical knowledge" in result["research_context"].lower()

    @pytest.mark.asyncio
    async def test_context_includes_audience_and_hcp_types(self):
        """Research context includes target audience and HCP types."""
        articles = [{"pmid": "1", "title": "Test", "abstract": "...", "year": 2025, "journal": "", "journal_abbrev": ""}]
        state = _make_sample_state(
            pubmed_results=articles,
            target_audience_primary=["primary care physicians"],
            target_hcp_types=["MD/DO", "NP"],
        )
        result = await ipa.build_context(state)

        assert "primary care physicians" in result["research_context"]
        assert "MD/DO" in result["research_context"]
