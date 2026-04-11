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


# ---------------------------------------------------------------------------
# generate_prefill node tests
# ---------------------------------------------------------------------------

MOCK_LLM_JSON_RESPONSE = json.dumps({
    "section_b": {
        "supporter_name": "",
        "supporter_contact_name": None,
        "supporter_contact_email": None,
        "grant_amount_requested": 75000,
        "grant_submission_deadline": None,
    },
    "section_c": {
        "learning_format": "live-symposium",
        "duration_minutes": 90,
        "include_post_test": True,
        "include_pre_test": True,
        "faculty_count": 3,
    },
    "section_d": {
        "clinical_topics": ["GDMT optimization", "SGLT2 inhibitors", "Device therapy"],
        "treatment_modalities": ["Pharmacologic", "Device"],
        "patient_population": "Adults with HFrEF (EF <= 40%)",
        "stage_of_disease": "Chronic, stable",
        "comorbidities": ["Diabetes", "CKD", "Hypertension"],
    },
    "section_e": {
        "knowledge_gaps": ["Underutilization of ARNI therapy", "Delayed SGLT2i initiation"],
        "competence_gaps": ["Risk stratification for device therapy"],
        "performance_gaps": ["Failure to titrate to target doses"],
        "gap_evidence_sources": ["ACC/AHA 2022 Guidelines", "CHAMP-HF Registry"],
        "gap_priority": "high",
    },
    "section_f": {
        "primary_outcomes": ["Increase in GDMT prescription rates"],
        "secondary_outcomes": ["Improvement in dose titration to target"],
        "measurement_approach": "Pre/post knowledge assessment with 60-day practice survey",
        "moore_levels_target": [3, 4, 5],
        "follow_up_timeline": "60 days post-activity",
    },
    "section_g": {
        "key_messages": ["GDMT should be initiated early", "SGLT2i benefit is class-wide"],
        "required_references": ["PMID:12345 - DAPA-HF trial", "PMID:67890 - EMPEROR-Reduced"],
        "excluded_topics": None,
        "competitor_products_to_mention": None,
        "regulatory_considerations": "Off-label discussion of combination therapy",
    },
    "section_h": {
        "distribution_channels": ["Medical society meetings", "Online CME platforms"],
        "geo_restrictions": None,
        "language_requirements": ["English"],
        "target_launch_date": None,
        "expiration_date": None,
    },
    "confidence": {
        "section_b": "low",
        "section_c": "medium",
        "section_d": "high",
        "section_e": "high",
        "section_f": "high",
        "section_g": "high",
        "section_h": "medium",
    },
})


def _mock_llm_generate(content: str):
    """Build a mock for LLMClient.generate that returns given content."""
    return AsyncMock(return_value={
        "content": content,
        "input_tokens": 500,
        "output_tokens": 800,
        "total_tokens": 1300,
        "cost": 0.0135,
    })


class TestGeneratePrefill:
    """Tests for generate_prefill node (mocked LLM)."""

    @pytest.mark.asyncio
    async def test_parses_valid_json_response(self):
        """Valid JSON from LLM is parsed into prefill_sections and confidence."""
        state = _make_sample_state(
            research_context="LITERATURE REVIEW (5 articles): ...",
        )

        with patch.object(ipa.llm, "generate", _mock_llm_generate(MOCK_LLM_JSON_RESPONSE)):
            result = await ipa.generate_prefill(state)

        assert "prefill_sections" in result
        assert "section_d" in result["prefill_sections"]
        assert result["prefill_sections"]["section_d"]["clinical_topics"][0] == "GDMT optimization"
        assert "confidence" in result
        assert result["confidence"]["section_d"] == "high"

    @pytest.mark.asyncio
    async def test_accumulates_token_counts(self):
        """Token counts are added to running totals."""
        state = _make_sample_state(
            research_context="...",
            total_tokens=100,
            total_cost=0.001,
        )

        with patch.object(ipa.llm, "generate", _mock_llm_generate(MOCK_LLM_JSON_RESPONSE)):
            result = await ipa.generate_prefill(state)

        assert result["total_tokens"] == 100 + 1300
        assert result["total_cost"] > 0.001

    @pytest.mark.asyncio
    async def test_handles_markdown_fenced_json(self):
        """LLM wrapping JSON in ```json fences is handled."""
        fenced = "```json\n" + MOCK_LLM_JSON_RESPONSE + "\n```"
        state = _make_sample_state(research_context="...")

        with patch.object(ipa.llm, "generate", _mock_llm_generate(fenced)):
            result = await ipa.generate_prefill(state)

        assert "section_d" in result["prefill_sections"]

    @pytest.mark.asyncio
    async def test_llm_failure_returns_error(self):
        """LLM call failure returns empty sections + error record."""
        state = _make_sample_state(research_context="...")
        mock_gen = AsyncMock(side_effect=Exception("LLM timeout"))

        with patch.object(ipa.llm, "generate", mock_gen):
            result = await ipa.generate_prefill(state)

        assert result["prefill_sections"] == {}
        assert len(result["errors"]) == 1
        assert "LLM" in result["errors"][0]["error"] or "timeout" in result["errors"][0]["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_json_returns_error(self):
        """Unparseable LLM output returns empty sections + error record."""
        state = _make_sample_state(research_context="...")

        with patch.object(ipa.llm, "generate", _mock_llm_generate("This is not JSON at all")):
            result = await ipa.generate_prefill(state)

        assert result["prefill_sections"] == {}
        assert len(result["errors"]) >= 1
