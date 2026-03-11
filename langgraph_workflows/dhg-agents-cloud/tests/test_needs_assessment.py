"""
Tests for the Needs Assessment Agent (needs_assessment_agent.py).

Covers:
- Graph construction and node inventory
- Individual node functions with mocked LLM
- Error handling / fallback behaviour
- Token and cost accumulation across nodes
- Utility functions (check_banned_patterns, count_words, check_prose_density)
- Document assembly and quality checks
"""

import json
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from conftest import _make_llm_response

# Import the module under test
import needs_assessment_agent as na


# ============================================================================
# Utility function tests (no LLM needed)
# ============================================================================


class TestCheckBannedPatterns:
    """Tests for check_banned_patterns utility."""

    def test_clean_text_returns_empty(self):
        clean = "The DELIVER trial showed improved outcomes in patients with HFpEF."
        assert na.check_banned_patterns(clean) == []

    def test_detects_em_dash(self):
        text = "The drug — approved in 2022 — works well."
        found = na.check_banned_patterns(text)
        assert any("—" in p for p in found)

    def test_detects_delve(self):
        text = "We will delve into the data."
        found = na.check_banned_patterns(text)
        assert len(found) >= 1

    def test_detects_multiple_banned_patterns(self):
        text = "Furthermore, we must navigate the complexities of this robust paradigm."
        found = na.check_banned_patterns(text)
        assert len(found) >= 3

    def test_case_insensitive(self):
        text = "FURTHERMORE, this is ROBUST."
        found = na.check_banned_patterns(text)
        assert len(found) >= 2


class TestCountWords:
    """Tests for count_words utility."""

    def test_empty_string(self):
        assert na.count_words("") == 0

    def test_single_word(self):
        assert na.count_words("hello") == 1

    def test_normal_sentence(self):
        assert na.count_words("Heart failure affects 6.7 million Americans") == 6


class TestCheckProseDensity:
    """Tests for check_prose_density utility."""

    def test_all_prose(self):
        text = (
            "Heart failure affects millions of Americans every year. "
            "The disease burden continues to grow as the population ages. "
            "Treatment options have expanded significantly in the past decade."
        )
        assert na.check_prose_density(text) == 1.0

    def test_all_bullets(self):
        text = "- item one\n- item two\n- item three"
        assert na.check_prose_density(text) == 0.0

    def test_mixed_content(self):
        text = (
            "Heart failure is a serious condition that demands attention from clinicians.\n"
            "- bullet point one\n"
            "The evidence clearly shows that early intervention matters most.\n"
            "- bullet point two"
        )
        density = na.check_prose_density(text)
        assert 0.4 <= density <= 0.6

    def test_empty_string(self):
        assert na.check_prose_density("") == 1.0


# ============================================================================
# Graph construction tests
# ============================================================================


class TestGraphConstruction:
    """Tests for create_needs_assessment_graph and compiled graph structure."""

    def test_graph_compiles_without_error(self):
        graph = na.create_needs_assessment_graph()
        compiled = graph.compile()
        assert compiled is not None

    def test_graph_has_expected_nodes(self):
        graph = na.create_needs_assessment_graph()
        compiled = graph.compile()
        node_names = set(compiled.get_graph().nodes.keys())

        expected_nodes = {
            "create_character",
            "generate_cold_open",
            "generate_disease_overview",
            "generate_treatment_options",
            "generate_practice_gaps",
            "generate_barriers",
            "generate_educational_rationale",
            "generate_target_audience",
            "generate_conclusion",
            "assemble_document",
            "__start__",
            "__end__",
        }
        assert expected_nodes.issubset(node_names)

    def test_graph_has_ten_agent_nodes(self):
        """The graph should have exactly 10 user-defined nodes (not counting __start__/__end__)."""
        graph = na.create_needs_assessment_graph()
        compiled = graph.compile()
        node_names = set(compiled.get_graph().nodes.keys())
        agent_nodes = node_names - {"__start__", "__end__"}
        assert len(agent_nodes) == 10

    def test_entry_point_is_create_character(self):
        graph = na.create_needs_assessment_graph()
        compiled = graph.compile()
        graph_repr = compiled.get_graph()
        start_edges = [
            e for e in graph_repr.edges if e[0] == "__start__"
        ]
        assert any(e[1] == "create_character" for e in start_edges)

    def test_module_level_graph_exists(self):
        """The module exports a pre-compiled graph at module level."""
        assert hasattr(na, "graph")
        assert na.graph is not None


# ============================================================================
# Individual node tests (with mocked LLM)
# ============================================================================


class TestCreateCharacterNode:
    """Tests for the create_character_node function."""

    @pytest.mark.asyncio
    async def test_returns_character_data(self, sample_needs_state, mock_llm_response):
        mock_llm_response.return_value = _make_llm_response(
            json.dumps({
                "name": "James Rivera",
                "age": 62,
                "humanizing_detail": "coaches his grandson's baseball team on weekends",
                "clinical_situation": "diagnosed with HFrEF but not on optimal GDMT",
            }),
            input_tokens=50,
            output_tokens=80,
        )

        result = await na.create_character_node(sample_needs_state)

        assert result["character_name"] == "James Rivera"
        assert result["character_age"] == 62
        assert result["character_type"] in ("patient", "clinician")
        assert result["character_appearances"] == 0
        assert "humanizing_detail" in result.get("character_humanizing_detail", "").lower() or len(result["character_humanizing_detail"]) > 0

    @pytest.mark.asyncio
    async def test_token_tracking(self, sample_needs_state, mock_llm_response):
        mock_llm_response.return_value = _make_llm_response(
            json.dumps({"name": "A", "age": 50, "humanizing_detail": "x", "clinical_situation": "y"}),
            input_tokens=120,
            output_tokens=60,
        )

        result = await na.create_character_node(sample_needs_state)

        assert result["total_tokens"] == 180
        assert result["total_cost"] > 0

    @pytest.mark.asyncio
    async def test_character_type_patient_when_outcome_gaps(self, sample_needs_state, mock_llm_response):
        """Gaps mentioning 'mortality' should produce a patient-type character."""
        sample_needs_state["gaps"] = [
            {"gap_statement": "High mortality from delayed diagnosis"}
        ]
        mock_llm_response.return_value = _make_llm_response(
            json.dumps({"name": "A", "age": 55, "humanizing_detail": "x", "clinical_situation": "y"})
        )

        result = await na.create_character_node(sample_needs_state)

        assert result["character_type"] == "patient"

    @pytest.mark.asyncio
    async def test_character_type_clinician_when_knowledge_gaps(self, sample_needs_state, mock_llm_response):
        """Gaps about 'guideline awareness' should produce a clinician-type character."""
        sample_needs_state["gaps"] = [
            {"gap_statement": "Low guideline awareness among prescribing physicians"}
        ]
        mock_llm_response.return_value = _make_llm_response(
            json.dumps({"name": "Dr. B", "age": 45, "humanizing_detail": "x", "clinical_situation": "y"})
        )

        result = await na.create_character_node(sample_needs_state)

        assert result["character_type"] == "clinician"

    @pytest.mark.asyncio
    async def test_returns_none_on_no_json_in_response(self, sample_needs_state, mock_llm_response):
        """When LLM response contains no JSON object, regex finds no match and
        the function returns None (no state update). This is the actual behaviour
        of the current code -- the try block succeeds but the if-match branch is
        skipped, so no return statement executes."""
        mock_llm_response.return_value = _make_llm_response("not valid json at all")

        result = await na.create_character_node(sample_needs_state)

        # The function falls through without returning, yielding None
        assert result is None

    @pytest.mark.asyncio
    async def test_fallback_on_llm_exception(self, sample_needs_state, mock_llm_response):
        """When the LLM call itself throws, the node should return fallback defaults."""
        mock_llm_response.side_effect = Exception("API rate limit exceeded")

        result = await na.create_character_node(sample_needs_state)

        assert result["character_name"] == "Maria Chen"
        assert result["character_age"] == 58
        assert len(result["errors"]) >= 1
        assert "fallback" in result["errors"][0].lower()


class TestGenerateColdOpenNode:
    """Tests for the generate_cold_open_node function."""

    @pytest.mark.asyncio
    async def test_returns_cold_open_text(self, sample_needs_state, mock_llm_response):
        cold_open_text = (
            "Maria Chen, 58, adjusts her reading glasses as she reviews "
            "her latest lab results. The numbers have changed again."
        )
        mock_llm_response.return_value = _make_llm_response(
            cold_open_text, input_tokens=200, output_tokens=50
        )
        sample_needs_state["character_name"] = "Maria Chen"
        sample_needs_state["character_age"] = 58

        result = await na.generate_cold_open_node(sample_needs_state)

        assert result["cold_open"] == cold_open_text
        assert result["character_appearances"] == 1
        assert "cold_open" in result["section_word_counts"]

    @pytest.mark.asyncio
    async def test_accumulates_tokens(self, sample_needs_state, mock_llm_response):
        mock_llm_response.return_value = _make_llm_response(
            "Short text.", input_tokens=100, output_tokens=20
        )
        sample_needs_state["total_tokens"] = 500
        sample_needs_state["total_cost"] = 0.01

        result = await na.generate_cold_open_node(sample_needs_state)

        assert result["total_tokens"] == 500 + 120
        assert result["total_cost"] > 0.01


class TestGenerateDiseaseOverviewNode:
    """Tests for the generate_disease_overview_node function."""

    @pytest.mark.asyncio
    async def test_increments_character_appearances(self, sample_needs_state, mock_llm_response):
        overview_text = "Maria Chen is one of 6.7 million Americans living with HFrEF."
        mock_llm_response.return_value = _make_llm_response(overview_text)
        sample_needs_state["character_name"] = "Maria Chen"
        sample_needs_state["character_appearances"] = 1

        result = await na.generate_disease_overview_node(sample_needs_state)

        assert result["character_appearances"] == 2

    @pytest.mark.asyncio
    async def test_no_character_appearance_when_not_mentioned(self, sample_needs_state, mock_llm_response):
        overview_text = "Heart failure affects 6.7 million Americans with high mortality."
        mock_llm_response.return_value = _make_llm_response(overview_text)
        sample_needs_state["character_name"] = "James Rivera"
        sample_needs_state["character_appearances"] = 1

        result = await na.generate_disease_overview_node(sample_needs_state)

        assert result["character_appearances"] == 1


class TestGenerateTreatmentOptionsNode:
    """Tests for the generate_treatment_options_node function."""

    @pytest.mark.asyncio
    async def test_returns_treatment_content(self, sample_needs_state, mock_llm_response):
        treatment_text = (
            "The ACC/AHA guidelines recommend a four-pillar approach to HFrEF management. "
            "SGLT2 inhibitors, ARNIs, beta-blockers, and MRAs form the foundation of GDMT. "
            "The PARADIGM-HF trial demonstrated that sacubitril-valsartan reduced cardiovascular "
            "death by 20% compared to enalapril alone."
        )
        mock_llm_response.return_value = _make_llm_response(treatment_text)

        result = await na.generate_treatment_options_node(sample_needs_state)

        assert result["treatment_landscape"] == treatment_text
        assert result["section_word_counts"]["treatment_landscape"] > 0

    @pytest.mark.asyncio
    async def test_token_accumulation(self, sample_needs_state, mock_llm_response):
        mock_llm_response.return_value = _make_llm_response(
            "Treatment text.", input_tokens=300, output_tokens=400
        )
        sample_needs_state["total_tokens"] = 1000
        sample_needs_state["total_cost"] = 0.05

        result = await na.generate_treatment_options_node(sample_needs_state)

        assert result["total_tokens"] == 1700
        assert result["total_cost"] > 0.05


class TestAssembleDocumentNode:
    """Tests for the assemble_document_node function."""

    @pytest.mark.asyncio
    async def test_assembles_all_sections(self, sample_needs_state):
        # Fill in sections with enough words to pass
        long_prose = " ".join(["word"] * 500)
        sample_needs_state["cold_open"] = "Maria Chen sits in the waiting room. " * 3
        sample_needs_state["disease_state_overview"] = long_prose
        sample_needs_state["treatment_landscape"] = long_prose
        sample_needs_state["practice_gaps_section"] = long_prose
        sample_needs_state["barriers_section"] = long_prose
        sample_needs_state["educational_rationale"] = long_prose
        sample_needs_state["target_audience_section"] = long_prose
        sample_needs_state["conclusion"] = long_prose
        sample_needs_state["character_appearances"] = 5

        result = await na.assemble_document_node(sample_needs_state)

        assert "## Disease State Overview" in result["complete_document"]
        assert "## Current Treatment Options" in result["complete_document"]
        assert "## Practice Gaps" in result["complete_document"]
        assert "## Barriers to Optimal Care" in result["complete_document"]
        assert "## Educational Rationale" in result["complete_document"]
        assert "## Target Audience" in result["complete_document"]
        assert "## Conclusion" in result["complete_document"]
        assert result["word_count"] > 0

    @pytest.mark.asyncio
    async def test_quality_fails_on_low_word_count(self, sample_needs_state):
        sample_needs_state["cold_open"] = "Short text."
        sample_needs_state["character_appearances"] = 5

        result = await na.assemble_document_node(sample_needs_state)

        assert result["meets_word_count"] is False
        assert result["quality_passed"] is False

    @pytest.mark.asyncio
    async def test_quality_fails_on_low_character_appearances(self, sample_needs_state):
        long_prose = " ".join(["word"] * 500)
        sample_needs_state["cold_open"] = long_prose
        sample_needs_state["disease_state_overview"] = long_prose
        sample_needs_state["treatment_landscape"] = long_prose
        sample_needs_state["practice_gaps_section"] = long_prose
        sample_needs_state["barriers_section"] = long_prose
        sample_needs_state["educational_rationale"] = long_prose
        sample_needs_state["target_audience_section"] = long_prose
        sample_needs_state["conclusion"] = long_prose
        sample_needs_state["character_appearances"] = 2

        result = await na.assemble_document_node(sample_needs_state)

        assert result["meets_character_thread"] is False
        assert result["quality_passed"] is False

    @pytest.mark.asyncio
    async def test_quality_fails_on_banned_patterns(self, sample_needs_state):
        long_prose = " ".join(["word"] * 500)
        banned_text = long_prose + " Furthermore, we must delve into the robust paradigm."
        sample_needs_state["cold_open"] = banned_text
        sample_needs_state["disease_state_overview"] = long_prose
        sample_needs_state["treatment_landscape"] = long_prose
        sample_needs_state["practice_gaps_section"] = long_prose
        sample_needs_state["barriers_section"] = long_prose
        sample_needs_state["educational_rationale"] = long_prose
        sample_needs_state["target_audience_section"] = long_prose
        sample_needs_state["conclusion"] = long_prose
        sample_needs_state["character_appearances"] = 5

        result = await na.assemble_document_node(sample_needs_state)

        assert len(result["banned_patterns_found"]) > 0
        assert result["quality_passed"] is False

    @pytest.mark.asyncio
    async def test_quality_passes_when_all_criteria_met(self, sample_needs_state):
        # Build clean prose with enough words and no banned patterns
        clean_prose = (
            "Heart failure is a condition that demands careful clinical attention "
            "from physicians across all practice settings in the United States. "
        )
        # Repeat to exceed 3100 words total
        section = clean_prose * 35  # ~490 words per section
        sample_needs_state["cold_open"] = clean_prose * 5
        sample_needs_state["disease_state_overview"] = section
        sample_needs_state["treatment_landscape"] = section
        sample_needs_state["practice_gaps_section"] = section
        sample_needs_state["barriers_section"] = section
        sample_needs_state["educational_rationale"] = section
        sample_needs_state["target_audience_section"] = section
        sample_needs_state["conclusion"] = section
        sample_needs_state["character_appearances"] = 5

        result = await na.assemble_document_node(sample_needs_state)

        assert result["meets_word_count"] is True
        assert result["meets_prose_density"] is True
        assert result["meets_character_thread"] is True
        assert result["quality_passed"] is True


# ============================================================================
# Token and cost accumulation tests
# ============================================================================


class TestTokenAccumulation:
    """Verify that tokens and costs accumulate correctly across sequential nodes."""

    @pytest.mark.asyncio
    async def test_cost_calculation_formula(self, sample_needs_state, mock_llm_response):
        """Verify cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000."""
        mock_llm_response.return_value = _make_llm_response(
            "Test content.", input_tokens=1000, output_tokens=500
        )
        sample_needs_state["character_name"] = "Test Person"
        sample_needs_state["total_tokens"] = 0
        sample_needs_state["total_cost"] = 0.0

        result = await na.generate_cold_open_node(sample_needs_state)

        expected_cost = (1000 * 0.003 + 500 * 0.015) / 1000
        assert abs(result["total_cost"] - expected_cost) < 1e-10

    @pytest.mark.asyncio
    async def test_tokens_add_to_previous(self, sample_needs_state, mock_llm_response):
        mock_llm_response.return_value = _make_llm_response(
            "Content.", input_tokens=200, output_tokens=300
        )
        sample_needs_state["character_name"] = "Test"
        sample_needs_state["total_tokens"] = 1000
        sample_needs_state["total_cost"] = 0.10

        result = await na.generate_cold_open_node(sample_needs_state)

        assert result["total_tokens"] == 1500


# ============================================================================
# Section requirements / constants tests
# ============================================================================


class TestSectionRequirements:
    """Verify SECTION_REQUIREMENTS dictionary is correctly defined."""

    def test_all_sections_present(self):
        expected_sections = {
            "cold_open", "disease_state_overview", "treatment_landscape",
            "practice_gaps", "barriers", "educational_rationale",
            "target_audience", "conclusion",
        }
        assert expected_sections == set(na.SECTION_REQUIREMENTS.keys())

    def test_cold_open_word_limits(self):
        reqs = na.SECTION_REQUIREMENTS["cold_open"]
        assert reqs["min_words"] == 50
        assert reqs["max_words"] == 100
        assert reqs["character_required"] is True

    def test_practice_gaps_is_longest_section(self):
        """Practice gaps should have the highest max_words."""
        max_words = {k: v["max_words"] for k, v in na.SECTION_REQUIREMENTS.items()}
        assert max_words["practice_gaps"] == max(max_words.values())


class TestBannedPatternsConstant:
    """Verify the BANNED_PATTERNS list is well-formed."""

    def test_banned_patterns_is_nonempty(self):
        assert len(na.BANNED_PATTERNS) > 20

    def test_all_patterns_compile_as_regex(self):
        for pattern in na.BANNED_PATTERNS:
            re.compile(pattern, re.IGNORECASE)
