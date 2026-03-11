"""
Shared test fixtures for DHG CME LangGraph agent tests.
Provides mocked LLM responses, sample states, and reusable test utilities.
"""

import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest

# Add src/ to path so agent modules resolve without package installs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ---------------------------------------------------------------------------
# LLM mock helpers
# ---------------------------------------------------------------------------

def _make_llm_response(content: str, input_tokens: int = 100, output_tokens: int = 200):
    """Build a fake LangChain AIMessage-like object returned by ChatAnthropic.ainvoke."""
    response = MagicMock()
    response.content = content
    response.usage_metadata = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    return response


@pytest.fixture
def mock_llm_response():
    """
    Patch ChatAnthropic so that every .ainvoke() call returns a canned response.

    Usage in tests:
        def test_something(mock_llm_response):
            mock_llm_response.return_value = _make_llm_response("hello")
            ...

    The fixture yields the AsyncMock bound to ChatAnthropic.ainvoke so callers
    can customise return_value or side_effect per-test.
    """
    with patch("langchain_anthropic.ChatAnthropic") as cls_mock:
        instance = MagicMock()
        cls_mock.return_value = instance

        async_invoke = AsyncMock(
            return_value=_make_llm_response("default mock response")
        )
        instance.ainvoke = async_invoke

        yield async_invoke


# ---------------------------------------------------------------------------
# Needs Assessment sample state
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_needs_state():
    """Minimal valid NeedsAssessmentState dict for unit tests."""
    return {
        "therapeutic_area": "cardiology",
        "disease_state": "heart failure with reduced ejection fraction",
        "target_audience": "primary care physicians",
        "geographic_focus": "United States",
        "activity_title": "Optimizing HFrEF Management in Primary Care",
        "accreditation_types": ["AMA PRA Category 1"],
        "gaps": [
            {
                "gap_statement": "Underutilization of guideline-directed medical therapy",
                "evidence_summary": "Only 25% of eligible patients receive GDMT",
                "patient_impact": "Increased mortality and hospitalizations",
            },
            {
                "gap_statement": "Delayed referral for device therapy",
                "evidence_summary": "Average delay of 18 months for ICD evaluation",
                "patient_impact": "Preventable sudden cardiac death",
            },
        ],
        "research_summary": (
            "Heart failure affects 6.7 million Americans with mortality "
            "remaining high at 50% within 5 years."
        ),
        "clinical_barriers": [
            "Time constraints",
            "Complex guidelines",
            "Competing priorities",
        ],
        "epidemiology": {
            "prevalence": "6.7 million Americans",
            "mortality": "50% 5-year mortality",
            "cost": "$43.6 billion annually",
        },
        "messages": [],
        "errors": [],
        "character_name": "",
        "character_age": 0,
        "character_type": "",
        "character_humanizing_detail": "",
        "character_appearances": 0,
        "cold_open": "",
        "disease_state_overview": "",
        "treatment_landscape": "",
        "practice_gaps_section": "",
        "barriers_section": "",
        "educational_rationale": "",
        "target_audience_section": "",
        "conclusion": "",
        "complete_document": "",
        "word_count": 0,
        "prose_density": 0.0,
        "banned_patterns_found": [],
        "section_word_counts": {},
        "meets_word_count": False,
        "meets_prose_density": False,
        "meets_character_thread": False,
        "quality_passed": False,
        "model_used": "",
        "total_tokens": 0,
        "total_cost": 0.0,
    }


# ---------------------------------------------------------------------------
# Orchestrator sample state
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_pipeline_state():
    """Minimal valid CMEPipelineState dict for orchestrator tests."""
    now = datetime.now().isoformat()
    return {
        "project_id": "test-project-001",
        "project_name": "Test CME Project",
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "intake_data": {
            "therapeutic_area": "cardiology",
            "target_audience": "primary care physicians",
            "research_questions": ["What is current GDMT utilization?"],
            "project_title": "Test Project",
            "activity_title": "Test Activity",
            "supporter_company": "Test Pharma",
            "supporter_contact": "contact@test.com",
            "requested_amount": "$50,000",
            "budget_breakdown": {},
            "organization_info": {},
            "accreditation_statement": "AMA PRA Category 1",
        },
        "intake_validated": True,
        "research_output": None,
        "clinical_output": None,
        "gap_analysis_output": None,
        "needs_assessment_output": None,
        "learning_objectives_output": None,
        "curriculum_output": None,
        "protocol_output": None,
        "marketing_output": None,
        "grant_package_output": None,
        "prose_quality_pass_1": None,
        "prose_quality_pass_2": None,
        "compliance_result": None,
        "human_review_status": None,
        "human_review_notes": None,
        "human_reviewer": None,
        "current_step": "started",
        "retry_count": 0,
        "messages": [],
        "errors": [],
        "last_checkpoint": now,
        "checkpoint_agent": "init",
        "review_comments": [],
        "review_round": 0,
    }
