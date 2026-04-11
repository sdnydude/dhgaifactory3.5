"""
Tests for the Recipe-Based Orchestrator (orchestrator.py).

Covers:
- Recipe graph construction (needs_graph, curriculum_graph, grant_graph, full_graph)
- Routing functions (route_after_prose_quality_1/2, route_after_compliance, route_after_human_review)
- Helper functions (create_error_record, create_initial_state, should_retry)
- PipelineStatus and ErrorCategory enums
- Human review interrupt and process_review_feedback nodes
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

import orchestrator as orch


# ============================================================================
# Enum tests
# ============================================================================


class TestPipelineStatus:
    """Tests for PipelineStatus enum."""

    def test_all_statuses_defined(self):
        expected = {"pending", "in_progress", "awaiting_review",
                    "revision_required", "approved", "complete", "failed"}
        actual = {s.value for s in orch.PipelineStatus}
        assert expected == actual

    def test_pending_value(self):
        assert orch.PipelineStatus.PENDING.value == "pending"

    def test_complete_value(self):
        assert orch.PipelineStatus.COMPLETE.value == "complete"


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_all_categories_defined(self):
        expected = {"agent_failure", "validation_failure", "quality_failure",
                    "timeout", "external_failure"}
        actual = {c.value for c in orch.ErrorCategory}
        assert expected == actual


# ============================================================================
# create_error_record tests
# ============================================================================


class TestCreateErrorRecord:
    """Tests for create_error_record helper."""

    def test_returns_dict_with_required_fields(self):
        record = orch.create_error_record("agent_failure", "Something broke", "research")
        assert record["error_type"] == "agent_failure"
        assert record["message"] == "Something broke"
        assert record["agent"] == "research"
        assert "timestamp" in record
        assert record["context"] == {}

    def test_includes_context_when_provided(self):
        ctx = {"input_size": 1024, "attempt": 2}
        record = orch.create_error_record("timeout", "Timed out", "gap_analysis", context=ctx)
        assert record["context"] == ctx

    def test_truncates_long_messages(self):
        long_msg = "x" * 1000
        record = orch.create_error_record("agent_failure", long_msg, "research")
        assert len(record["message"]) <= 500

    def test_timestamp_is_iso_format(self):
        record = orch.create_error_record("agent_failure", "err", "research")
        # Should parse without error
        datetime.fromisoformat(record["timestamp"])

    def test_converts_non_string_message(self):
        record = orch.create_error_record("agent_failure", RuntimeError("boom"), "research")
        assert isinstance(record["message"], str)
        assert "boom" in record["message"]


# ============================================================================
# should_retry tests
# ============================================================================


class TestShouldRetry:
    """Tests for should_retry logic."""

    def test_allows_retry_when_no_previous_errors(self, sample_pipeline_state):
        assert orch.should_retry(sample_pipeline_state, "agent_failure", "research") is True

    def test_allows_retry_when_below_max(self, sample_pipeline_state):
        sample_pipeline_state["errors"] = [
            {"agent": "research", "error_type": "agent_failure", "message": "err1", "timestamp": ""},
            {"agent": "research", "error_type": "agent_failure", "message": "err2", "timestamp": ""},
        ]
        # MAX_RETRIES["agent_failure"] is 3, so 2 errors should still allow retry
        assert orch.should_retry(sample_pipeline_state, "agent_failure", "research") is True

    def test_denies_retry_at_max(self, sample_pipeline_state):
        sample_pipeline_state["errors"] = [
            {"agent": "research", "error_type": "agent_failure", "message": f"err{i}", "timestamp": ""}
            for i in range(3)
        ]
        assert orch.should_retry(sample_pipeline_state, "agent_failure", "research") is False

    def test_counts_only_matching_agent_and_type(self, sample_pipeline_state):
        sample_pipeline_state["errors"] = [
            {"agent": "research", "error_type": "agent_failure", "message": "err", "timestamp": ""},
            {"agent": "clinical", "error_type": "agent_failure", "message": "err", "timestamp": ""},
            {"agent": "research", "error_type": "timeout", "message": "err", "timestamp": ""},
        ]
        # Only 1 error matches (research + agent_failure), max is 3
        assert orch.should_retry(sample_pipeline_state, "agent_failure", "research") is True

    def test_timeout_allows_only_one_retry(self, sample_pipeline_state):
        sample_pipeline_state["errors"] = [
            {"agent": "research", "error_type": "timeout", "message": "err", "timestamp": ""},
        ]
        assert orch.should_retry(sample_pipeline_state, "timeout", "research") is False


# ============================================================================
# create_initial_state tests
# ============================================================================


class TestCreateInitialState:
    """Tests for create_initial_state factory function."""

    def test_returns_valid_state(self):
        intake = {"therapeutic_area": "oncology", "target_audience": "oncologists"}
        state = orch.create_initial_state("proj-123", "Test Project", intake)

        assert state["project_id"] == "proj-123"
        assert state["project_name"] == "Test Project"
        assert state["status"] == "pending"
        assert state["intake_data"] == intake
        assert state["intake_validated"] is True

    def test_agent_outputs_start_as_none(self):
        state = orch.create_initial_state("p1", "P1", {})
        output_keys = [
            "research_output", "clinical_output", "gap_analysis_output",
            "needs_assessment_output", "learning_objectives_output",
            "curriculum_output", "protocol_output", "marketing_output",
            "grant_package_output", "prose_quality_pass_1",
            "prose_quality_pass_2", "compliance_result",
        ]
        for key in output_keys:
            assert state[key] is None, f"{key} should be None initially"

    def test_control_fields_initialized(self):
        state = orch.create_initial_state("p1", "P1", {})
        assert state["current_step"] == "started"
        assert state["retry_count"] == 0
        assert state["messages"] == []
        assert state["errors"] == []
        assert state["checkpoint_agent"] == "init"

    def test_timestamps_are_iso_format(self):
        state = orch.create_initial_state("p1", "P1", {})
        datetime.fromisoformat(state["created_at"])
        datetime.fromisoformat(state["updated_at"])
        datetime.fromisoformat(state["last_checkpoint"])

    def test_human_review_fields_start_none(self):
        state = orch.create_initial_state("p1", "P1", {})
        assert state["human_review_status"] is None
        assert state["human_review_notes"] is None
        assert state["human_reviewer"] is None


class TestReviewStateFields:
    """Tests for review-related state fields."""

    def test_initial_state_has_review_comments(self):
        state = orch.create_initial_state("p1", "P1", {})
        assert state["review_comments"] == []

    def test_initial_state_has_review_round(self):
        state = orch.create_initial_state("p1", "P1", {})
        assert state["review_round"] == 0


# ============================================================================
# Routing function tests
# ============================================================================


class TestRouteAfterProseQuality1:
    """Tests for route_after_prose_quality_1 routing function."""

    def test_continue_when_passed(self, sample_pipeline_state):
        sample_pipeline_state["prose_quality_pass_1"] = {"overall_passed": True}
        assert orch.route_after_prose_quality_1(sample_pipeline_state) == "continue"

    def test_retry_needs_when_failed_and_retries_remain(self, sample_pipeline_state):
        sample_pipeline_state["prose_quality_pass_1"] = {"overall_passed": False}
        sample_pipeline_state["retry_count"] = 1
        assert orch.route_after_prose_quality_1(sample_pipeline_state) == "retry_needs"

    def test_human_intervention_when_retries_exhausted(self, sample_pipeline_state):
        sample_pipeline_state["prose_quality_pass_1"] = {"overall_passed": False}
        sample_pipeline_state["retry_count"] = 3  # equals MAX_RETRIES["quality_failure"]
        assert orch.route_after_prose_quality_1(sample_pipeline_state) == "human_intervention"

    def test_retry_needs_when_result_missing(self, sample_pipeline_state):
        """When prose_quality_pass_1 is None, overall_passed defaults to False."""
        sample_pipeline_state["prose_quality_pass_1"] = None
        sample_pipeline_state["retry_count"] = 0
        assert orch.route_after_prose_quality_1(sample_pipeline_state) == "retry_needs"


class TestRouteAfterProseQuality2:
    """Tests for route_after_prose_quality_2 routing function."""

    def test_continue_when_passed(self, sample_pipeline_state):
        sample_pipeline_state["prose_quality_pass_2"] = {"overall_passed": True}
        assert orch.route_after_prose_quality_2(sample_pipeline_state) == "continue"

    def test_retry_grant_when_failed_and_retries_remain(self, sample_pipeline_state):
        sample_pipeline_state["prose_quality_pass_2"] = {"overall_passed": False}
        sample_pipeline_state["retry_count"] = 0
        assert orch.route_after_prose_quality_2(sample_pipeline_state) == "retry_grant"

    def test_human_intervention_when_retries_exhausted(self, sample_pipeline_state):
        sample_pipeline_state["prose_quality_pass_2"] = {"overall_passed": False}
        sample_pipeline_state["retry_count"] = 3
        assert orch.route_after_prose_quality_2(sample_pipeline_state) == "human_intervention"


class TestRouteAfterCompliance:
    """Tests for route_after_compliance routing function."""

    def test_continue_when_passed(self, sample_pipeline_state):
        sample_pipeline_state["compliance_result"] = {"overall_passed": True}
        assert orch.route_after_compliance(sample_pipeline_state) == "continue"

    def test_revision_required_when_failed(self, sample_pipeline_state):
        sample_pipeline_state["compliance_result"] = {"overall_passed": False}
        assert orch.route_after_compliance(sample_pipeline_state) == "revision_required"

    def test_revision_required_when_result_missing(self, sample_pipeline_state):
        sample_pipeline_state["compliance_result"] = None
        assert orch.route_after_compliance(sample_pipeline_state) == "revision_required"


class TestRouteAfterHumanReviewInterrupt:
    """Tests for route_after_human_review_interrupt routing function."""

    def test_approved(self, sample_pipeline_state):
        sample_pipeline_state["human_review_status"] = "approved"
        assert orch.route_after_human_review_interrupt(sample_pipeline_state) == "approved"

    def test_revision(self, sample_pipeline_state):
        sample_pipeline_state["human_review_status"] = "revision"
        assert orch.route_after_human_review_interrupt(sample_pipeline_state) == "revision"

    def test_rejected_default(self, sample_pipeline_state):
        sample_pipeline_state["human_review_status"] = "pending"
        assert orch.route_after_human_review_interrupt(sample_pipeline_state) == "rejected"

    def test_rejected_when_none(self, sample_pipeline_state):
        sample_pipeline_state["human_review_status"] = None
        assert orch.route_after_human_review_interrupt(sample_pipeline_state) == "rejected"


# ============================================================================
# Recipe graph construction tests
# ============================================================================


class TestNeedsPackageGraph:
    """Tests for create_needs_package_graph / needs_graph."""

    def test_compiles_without_error(self):
        graph = orch.create_needs_package_graph()
        assert graph is not None

    def test_module_level_needs_graph_exists(self):
        assert orch.needs_graph is not None

    def test_has_expected_nodes(self):
        nodes = set(orch.needs_graph.get_graph().nodes.keys())
        expected = {
            "early_research", "gap_analysis", "learning_objectives",
            "needs_assessment", "prose_quality", "human_review",
            "process_feedback", "complete", "failed",
            "__start__", "__end__",
        }
        assert expected.issubset(nodes)

    def test_entry_point_is_early_research(self):
        graph_repr = orch.needs_graph.get_graph()
        start_edges = [e for e in graph_repr.edges if e[0] == "__start__"]
        assert any(e[1] == "early_research" for e in start_edges)

    def test_human_review_has_three_way_routing(self):
        """Human review should route to complete, needs_assessment (revision), or failed."""
        graph_repr = orch.needs_graph.get_graph()
        hr_targets = sorted([e[1] for e in graph_repr.edges if e[0] == "human_review"])
        assert "complete" in hr_targets
        assert "process_feedback" in hr_targets
        assert "failed" in hr_targets


class TestCurriculumPackageGraph:
    """Tests for create_curriculum_package_graph / curriculum_graph."""

    def test_compiles_without_error(self):
        graph = orch.create_curriculum_package_graph()
        assert graph is not None

    def test_module_level_curriculum_graph_exists(self):
        assert orch.curriculum_graph is not None

    def test_has_design_phase_node(self):
        nodes = set(orch.curriculum_graph.get_graph().nodes.keys())
        assert "design_phase" in nodes

    def test_has_expected_nodes(self):
        nodes = set(orch.curriculum_graph.get_graph().nodes.keys())
        expected = {
            "early_research", "gap_analysis", "learning_objectives",
            "needs_assessment", "prose_quality_1", "design_phase",
            "human_review", "process_feedback", "complete", "failed",
            "__start__", "__end__",
        }
        assert expected.issubset(nodes)


class TestGrantPackageGraph:
    """Tests for create_grant_package_graph / grant_graph."""

    def test_compiles_without_error(self):
        graph = orch.create_grant_package_graph()
        assert graph is not None

    def test_module_level_grant_graph_exists(self):
        assert orch.grant_graph is not None

    def test_has_all_phase_nodes(self):
        nodes = set(orch.grant_graph.get_graph().nodes.keys())
        expected = {
            "early_research", "gap_analysis", "learning_objectives",
            "needs_assessment", "prose_quality_1", "design_phase",
            "grant_writer", "prose_quality_2", "compliance",
            "human_review", "process_feedback", "complete", "failed",
            "__start__", "__end__",
        }
        assert expected.issubset(nodes)

    def test_grant_graph_node_count(self):
        nodes = set(orch.grant_graph.get_graph().nodes.keys())
        agent_nodes = nodes - {"__start__", "__end__"}
        assert len(agent_nodes) == 13


class TestFullPipelineGraph:
    """Tests for create_full_pipeline_graph / full_graph."""

    def test_compiles_without_error(self):
        graph = orch.create_full_pipeline_graph()
        assert graph is not None

    def test_module_level_full_graph_exists(self):
        assert orch.full_graph is not None

    def test_has_same_nodes_as_grant_graph(self):
        """Full pipeline has the same nodes as grant pipeline."""
        full_nodes = set(orch.full_graph.get_graph().nodes.keys())
        grant_nodes = set(orch.grant_graph.get_graph().nodes.keys())
        assert full_nodes == grant_nodes

    def test_full_graph_has_human_review_routing(self):
        """Full graph should have 3-way routing from human_review."""
        graph_repr = orch.full_graph.get_graph()
        hr_targets = sorted([e[1] for e in graph_repr.edges if e[0] == "human_review"])
        assert "complete" in hr_targets
        assert "process_feedback" in hr_targets
        assert "failed" in hr_targets


# ============================================================================
# Configuration constants tests
# ============================================================================


class TestConfiguration:
    """Tests for orchestrator configuration values."""

    def test_max_retries_defined(self):
        assert "agent_failure" in orch.MAX_RETRIES
        assert "quality_failure" in orch.MAX_RETRIES
        assert "timeout" in orch.MAX_RETRIES

    def test_agent_timeout_is_reasonable(self):
        assert orch.AGENT_TIMEOUT == 300  # 5 minutes

    def test_timeout_retry_is_minimal(self):
        assert orch.MAX_RETRIES["timeout"] == 1

    def test_quality_failure_allows_three_retries(self):
        assert orch.MAX_RETRIES["quality_failure"] == 3


# ============================================================================
# Async gate node tests
# ============================================================================


class TestGateNodes:
    """Tests for human_review_node, mark_complete, mark_failed nodes."""

    @pytest.mark.asyncio
    async def test_mark_complete_sets_status(self, sample_pipeline_state):
        result = await orch.mark_complete(sample_pipeline_state)
        assert result["status"] == "complete"
        assert result["current_step"] == "complete"

    @pytest.mark.asyncio
    async def test_mark_failed_sets_status(self, sample_pipeline_state):
        result = await orch.mark_failed(sample_pipeline_state)
        assert result["status"] == "failed"
        assert result["current_step"] == "failed_human_intervention_required"

    @pytest.mark.asyncio
    async def test_gate_nodes_include_timestamp(self, sample_pipeline_state):
        result = await orch.mark_complete(sample_pipeline_state)
        datetime.fromisoformat(result["updated_at"])

        result = await orch.mark_failed(sample_pipeline_state)
        datetime.fromisoformat(result["updated_at"])


class TestHumanReviewInterrupt:
    """Tests for interrupt-based human review."""

    def test_human_review_node_calls_interrupt(self, sample_pipeline_state):
        """The human_review node should call interrupt() with a review payload."""
        sample_pipeline_state["needs_assessment_output"] = {
            "complete_document": "Test document content",
            "word_count": 3200,
            "prose_density": 0.85,
            "quality_passed": True,
            "banned_patterns_found": [],
        }
        sample_pipeline_state["prose_quality_pass_1"] = {
            "overall_passed": True,
            "feedback": "",
        }

        from unittest.mock import patch as mock_patch

        with mock_patch("orchestrator.interrupt") as mock_interrupt:
            mock_interrupt.side_effect = lambda payload: {"decision": "approved", "comments": []}
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                orch.human_review_node(sample_pipeline_state)
            )
            mock_interrupt.assert_called_once()
            call_payload = mock_interrupt.call_args[0][0]
            assert "document" in call_payload
            assert "metrics" in call_payload
            assert call_payload["recipe"] == "needs_package"

    def test_route_after_interrupt_approved(self):
        """When interrupt resumes with approved, route to complete/END."""
        state = {"human_review_status": "approved"}
        assert orch.route_after_human_review_interrupt(state) == "approved"

    def test_route_after_interrupt_revision(self):
        """When interrupt resumes with revision, route to revision agent."""
        state = {"human_review_status": "revision"}
        assert orch.route_after_human_review_interrupt(state) == "revision"

    def test_route_after_interrupt_rejected(self):
        """When interrupt resumes with rejected, route to failed."""
        state = {"human_review_status": "rejected"}
        assert orch.route_after_human_review_interrupt(state) == "rejected"


class TestProcessReviewFeedback:
    """Tests for process_review_feedback node."""

    @pytest.mark.asyncio
    async def test_formats_comments_into_message(self, sample_pipeline_state):
        sample_pipeline_state["review_comments"] = [
            {"selectedText": "The prevalence", "comment": "Add CDC data", "startOffset": 0, "endOffset": 14},
            {"selectedText": "guidelines recommend", "comment": "Wrong area", "startOffset": 100, "endOffset": 120},
        ]
        result = await orch.process_review_feedback(sample_pipeline_state)
        assert len(result["messages"]) == 1
        msg_content = result["messages"][0].content
        assert "The prevalence" in msg_content
        assert "Add CDC data" in msg_content
        assert "guidelines recommend" in msg_content

    @pytest.mark.asyncio
    async def test_increments_review_round(self, sample_pipeline_state):
        sample_pipeline_state["review_comments"] = [
            {"selectedText": "text", "comment": "fix", "startOffset": 0, "endOffset": 4},
        ]
        sample_pipeline_state["review_round"] = 1
        result = await orch.process_review_feedback(sample_pipeline_state)
        assert result["review_round"] == 2

    @pytest.mark.asyncio
    async def test_empty_comments_still_works(self, sample_pipeline_state):
        sample_pipeline_state["review_comments"] = []
        result = await orch.process_review_feedback(sample_pipeline_state)
        assert result["review_round"] == 1
        assert "General revision requested" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_max_revisions_routes_to_failed(self, sample_pipeline_state):
        sample_pipeline_state["review_round"] = 3
        sample_pipeline_state["review_comments"] = []
        result = await orch.process_review_feedback(sample_pipeline_state)
        assert result["status"] == "failed"
        assert "maximum" in result["current_step"]


# ============================================================================
# flatten_intake tests
# ============================================================================


class TestFlattenIntake:
    """Tests for flatten_intake helper — especially new alias keys."""

    SAMPLE_SECTIONED_INTAKE = {
        "section_a": {
            "project_name": "PMR Management Update",
            "therapeutic_area": ["rheumatology"],
            "disease_state": ["polymyalgia rheumatica"],
            "target_audience_primary": ["rheumatologists", "internists"],
        },
        "section_b": {"supporter_name": "Acme Pharma"},
        "section_c": {"learning_format": "webinar", "include_post_test": False, "include_pre_test": False},
        "section_d": {
            "clinical_topics": ["glucocorticoid tapering", "IL-6 inhibitors"],
            "treatment_modalities": ["pharmacologic"],
            "patient_population": "adults over 50",
        },
        "section_e": {
            "knowledge_gaps": ["Optimal tapering protocols"],
            "competence_gaps": ["Distinguishing PMR from RA"],
            "performance_gaps": ["Monitoring for relapse"],
        },
        "section_f": {
            "primary_outcomes": ["Reduced relapse rate"],
            "moore_levels_target": ["Level 5", "Level 4"],
        },
        "section_g": {
            "competitor_products_to_mention": ["tocilizumab", "sarilumab"],
        },
        "section_h": {"geo_restrictions": ["US", "EU"]},
        "section_i": {"accme_compliant": True, "financial_disclosure_required": True,
                      "off_label_discussion": False, "commercial_support_acknowledgment": True},
        "section_j": {},
    }

    def test_disease_state_extracted(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["disease_state"] == ["polymyalgia rheumatica"]

    def test_known_gaps_combines_three_gap_types(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["known_gaps"] == [
            "Optimal tapering protocols",
            "Distinguishing PMR from RA",
            "Monitoring for relapse",
        ]

    def test_outcome_goals_aliases_primary_outcomes(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["outcome_goals"] == ["Reduced relapse rate"]

    def test_moore_level_target_takes_first(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["moore_level_target"] == "Level 5"

    def test_moore_level_target_empty_when_none(self):
        intake = {**self.SAMPLE_SECTIONED_INTAKE, "section_f": {}}
        flat = orch.flatten_intake(intake)
        assert flat["moore_level_target"] == ""

    def test_educational_format_aliases_learning_format(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["educational_format"] == "webinar"

    def test_competitor_products_aliases(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["competitor_products"] == ["tocilizumab", "sarilumab"]

    def test_geographic_focus_joins_list(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["geographic_focus"] == "US, EU"

    def test_already_flat_returns_as_is(self):
        flat_input = {"therapeutic_area": "oncology", "disease_state": "NSCLC"}
        result = orch.flatten_intake(flat_input)
        assert result == flat_input

    def test_supporter_company_maps_from_supporter_name(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["supporter_company"] == "Acme Pharma"


# ============================================================================
# Wrapper agent_input passthrough tests
# ============================================================================


class TestWrapperPassthrough:
    """Verify that run_*_agent wrappers pass disease-critical intake fields."""

    @pytest.mark.asyncio
    async def test_research_agent_receives_disease_state(self, sample_pipeline_state):
        """run_research_agent must pass disease_state to the agent."""
        captured_input = {}

        async def fake_invoke(agent_input):
            captured_input.update(agent_input)
            return {"research_report": "mocked"}

        mock_graph = MagicMock()
        mock_graph.ainvoke = fake_invoke

        with patch("orchestrator.get_agent_graph", return_value=mock_graph):
            await orch.run_research_agent(sample_pipeline_state)

        assert captured_input["disease_state"] == "heart failure with reduced ejection fraction"
        assert captured_input["therapeutic_area"] == "cardiology"
        assert captured_input["supporter_company"] == "Test Pharma"
        assert captured_input["supporter_products"] == ["sacubitril/valsartan"]
        assert captured_input["known_gaps"] == ["Underutilization of GDMT"]
        assert captured_input["competitor_products"] == ["dapagliflozin"]
        assert captured_input["geographic_focus"] == "United States"

    @pytest.mark.asyncio
    async def test_clinical_agent_receives_disease_state(self, sample_pipeline_state):
        """run_clinical_agent must pass disease_state to the agent."""
        captured_input = {}

        async def fake_invoke(agent_input):
            captured_input.update(agent_input)
            return {"clinical_report": "mocked"}

        mock_graph = MagicMock()
        mock_graph.ainvoke = fake_invoke

        with patch("orchestrator.get_agent_graph", return_value=mock_graph):
            await orch.run_clinical_agent(sample_pipeline_state)

        assert captured_input["disease_state"] == "heart failure with reduced ejection fraction"
        assert captured_input["therapeutic_area"] == "cardiology"
        assert captured_input["geographic_focus"] == "United States"
        assert captured_input["known_gaps"] == ["Underutilization of GDMT"]

    @pytest.mark.asyncio
    async def test_gap_analysis_agent_receives_disease_state(self, sample_pipeline_state):
        """run_gap_analysis_agent must pass disease_state to the agent."""
        captured_input = {}

        async def fake_invoke(agent_input):
            captured_input.update(agent_input)
            return {"gap_report": "mocked"}

        mock_graph = MagicMock()
        mock_graph.ainvoke = fake_invoke

        with patch("orchestrator.get_agent_graph", return_value=mock_graph):
            await orch.run_gap_analysis_agent(sample_pipeline_state)

        assert captured_input["disease_state"] == "heart failure with reduced ejection fraction"
        assert captured_input["target_audience"] == "primary care physicians"
        assert captured_input["known_gaps"] == ["Underutilization of GDMT"]
        assert captured_input["outcome_goals"] == ["Improved GDMT adherence"]

    @pytest.mark.asyncio
    async def test_learning_objectives_agent_receives_disease_state(self, sample_pipeline_state):
        """run_learning_objectives_agent must pass disease_state to the agent."""
        captured_input = {}

        async def fake_invoke(agent_input):
            captured_input.update(agent_input)
            return {"lo_report": "mocked"}

        mock_graph = MagicMock()
        mock_graph.ainvoke = fake_invoke

        with patch("orchestrator.get_agent_graph", return_value=mock_graph):
            await orch.run_learning_objectives_agent(sample_pipeline_state)

        assert captured_input["disease_state"] == "heart failure with reduced ejection fraction"
        assert captured_input["therapeutic_area"] == "cardiology"
        assert captured_input["educational_format"] == "webinar"
        assert captured_input["moore_level_target"] == "Level 5"
        assert captured_input["outcome_goals"] == ["Improved GDMT adherence"]

    @pytest.mark.asyncio
    async def test_compliance_agent_receives_full_context(self, sample_pipeline_state):
        """run_compliance_agent must pass supporter_products and accreditation_types."""
        captured_input = {}
        sample_pipeline_state["grant_package_output"] = {"document": "mocked grant"}

        async def fake_invoke(agent_input):
            captured_input.update(agent_input)
            return {"compliance_report": "mocked"}

        mock_graph = MagicMock()
        mock_graph.ainvoke = fake_invoke

        with patch("orchestrator.get_agent_graph", return_value=mock_graph):
            await orch.run_compliance_agent(sample_pipeline_state)

        assert captured_input["supporter_company"] == "Test Pharma"
        assert captured_input["supporter_products"] == ["sacubitril/valsartan"]
        assert captured_input["competitor_products"] == ["dapagliflozin"]
        assert captured_input["accreditation_types"] == ["ACCME"]
