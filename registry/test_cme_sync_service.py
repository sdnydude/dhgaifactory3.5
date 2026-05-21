"""Tests for cme_sync_service -- direct service-layer coverage.

Covers all 5 extractors, calculate_progress, generate_embedding,
extract_intake_fields, and sync_project_from_thread orchestration.

Run with: pytest registry/test_cme_sync_service.py -v
"""
import os
import sys
import uuid
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cme_sync_service as svc


# ── Helpers ─────────────────────────────────────────────────────────────


def mock_query_chain(db, results):
    """Wire up db.query(...).filter(...).first()/.all()/.count() chains."""
    q = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.all.return_value = results
    q.first.return_value = results[0] if results else None
    q.count.return_value = len(results)
    return q


# ── extract_document_text ───────────────────────────────────────────────


class TestExtractDocumentText:
    def test_research_returns_research_document(self):
        content = {"research_document": "This is the full research document text."}
        assert svc.extract_document_text("research", content) == content["research_document"]

    def test_needs_assessment_returns_complete_document(self):
        content = {"complete_document": "Full needs assessment document content here."}
        assert svc.extract_document_text("needs_assessment", content) == content["complete_document"]

    def test_grant_package_returns_complete_document_markdown(self):
        content = {"complete_document_markdown": "# Grant Package\n\nFull markdown document."}
        assert svc.extract_document_text("grant_package", content) == content["complete_document_markdown"]

    def test_prose_quality_returns_summary(self):
        content = {"summary": "Prose quality assessment summary with details."}
        assert svc.extract_document_text("prose_quality_1", content) == content["summary"]

    def test_clinical_returns_clinical_practice_document(self):
        content = {"clinical_practice_document": "Clinical practice analysis document text."}
        assert svc.extract_document_text("clinical", content) == content["clinical_practice_document"]

    def test_compliance_builds_text_from_report(self):
        content = {
            "compliance_report": {
                "overall_verdict": "APPROVED",
                "standard_checks": {
                    "SCS1": {"status": "pass", "findings": "All clear"},
                    "SCS2": {"status": "pass", "findings": "Compliant"},
                },
            }
        }
        result = svc.extract_document_text("compliance", content)
        assert result is not None
        assert "Compliance Verdict: APPROVED" in result
        assert "SCS1: pass" in result
        assert "All clear" in result

    def test_compliance_returns_verdict_text_when_report_key_absent(self):
        # When compliance_report key is absent, .get returns {} which still
        # produces the verdict line (empty verdict string).
        result = svc.extract_document_text("compliance", {})
        assert result == "Compliance Verdict: "

    def test_compliance_returns_none_when_report_is_not_dict(self):
        assert svc.extract_document_text("compliance", {"compliance_report": "string"}) is None

    def test_learning_objectives_extracts_text(self):
        content = {"learning_objectives_document": "Objective 1: Identify key barriers to treatment adherence in oncology patients."}
        result = svc.extract_document_text("learning_objectives", content)
        assert result is not None
        assert "Identify key barriers" in result

    def test_protocol_extracts_text(self):
        content = {"protocol_document": "Study Protocol: Randomized controlled trial measuring knowledge retention across cohorts."}
        result = svc.extract_document_text("protocol", content)
        assert result is not None
        assert "Randomized controlled trial" in result

    def test_marketing_extracts_text(self):
        content = {"marketing_document": "Marketing Plan: Multi-channel outreach strategy targeting oncology specialists nationwide."}
        result = svc.extract_document_text("marketing", content)
        assert result is not None
        assert "Multi-channel outreach" in result

    def test_prose_quality_2_extracts_summary(self):
        content = {"summary": "Second pass prose quality review with improved density scoring and fewer AI patterns detected."}
        result = svc.extract_document_text("prose_quality_2", content)
        assert result is not None
        assert "Second pass prose quality" in result

    def test_returns_none_for_non_dict_content(self):
        assert svc.extract_document_text("research", "not a dict") is None
        assert svc.extract_document_text("research", None) is None

    def test_returns_none_when_text_too_short(self):
        content = {"research_document": "short"}
        assert svc.extract_document_text("research", content) is None

    def test_returns_none_when_key_missing(self):
        assert svc.extract_document_text("research", {"other_key": "value"}) is None

    def test_curriculum_returns_curriculum_document(self):
        content = {"curriculum_document": "Curriculum design document with full content."}
        assert svc.extract_document_text("curriculum", content) == content["curriculum_document"]

    def test_gap_analysis_returns_gap_analysis_document(self):
        content = {"gap_analysis_document": "Gap analysis document with identified gaps."}
        assert svc.extract_document_text("gap_analysis", content) == content["gap_analysis_document"]


# ── extract_quality_score ───────────────────────────────────────────────


class TestExtractQualityScore:
    def test_prose_quality_normalizes_to_fraction(self):
        content = {"overall_score": 85}
        assert svc.extract_quality_score("prose_quality_1", content) == 0.85

    def test_prose_quality_2_normalizes_to_fraction(self):
        content = {"overall_score": 100}
        assert svc.extract_quality_score("prose_quality_2", content) == 1.0

    def test_prose_quality_returns_none_when_score_missing(self):
        assert svc.extract_quality_score("prose_quality_1", {}) is None

    def test_prose_quality_returns_none_when_score_is_string(self):
        assert svc.extract_quality_score("prose_quality_1", {"overall_score": "high"}) is None

    def test_needs_assessment_quality_passed_returns_1(self):
        content = {"quality_passed": True}
        assert svc.extract_quality_score("needs_assessment", content) == 1.0

    def test_needs_assessment_word_count_ratio(self):
        content = {"quality_passed": False, "word_count": 1550}
        assert svc.extract_quality_score("needs_assessment", content) == 0.5

    def test_needs_assessment_word_count_capped_at_1(self):
        content = {"quality_passed": False, "word_count": 6200}
        assert svc.extract_quality_score("needs_assessment", content) == 1.0

    def test_needs_assessment_returns_none_when_no_data(self):
        assert svc.extract_quality_score("needs_assessment", {}) is None

    def test_compliance_approved(self):
        content = {"compliance_report": {"overall_verdict": "APPROVED"}}
        assert svc.extract_quality_score("compliance", content) == 1.0

    def test_compliance_requires_revision(self):
        content = {"compliance_report": {"overall_verdict": "REQUIRES_REVISION"}}
        assert svc.extract_quality_score("compliance", content) == 0.5

    def test_compliance_rejected(self):
        content = {"compliance_report": {"overall_verdict": "REJECTED"}}
        assert svc.extract_quality_score("compliance", content) == 0.0

    def test_compliance_unknown_verdict_returns_none(self):
        content = {"compliance_report": {"overall_verdict": "UNKNOWN"}}
        assert svc.extract_quality_score("compliance", content) is None

    def test_returns_none_for_non_dict(self):
        assert svc.extract_quality_score("prose_quality_1", "bad") is None

    def test_returns_none_for_unknown_agent(self):
        assert svc.extract_quality_score("research", {"some_data": 42}) is None


# ── extract_quality_details ─────────────────────────────────────────────


class TestExtractQualityDetails:
    def test_prose_quality_returns_detail_keys(self):
        content = {
            "overall_score": 88,
            "overall_passed": True,
            "prose_density_score": 0.92,
            "ai_patterns_count": 3,
            "word_count_total": 4200,
            "revision_instructions": None,
        }
        details = svc.extract_quality_details("prose_quality_1", content)
        assert details is not None
        assert details["overall_score"] == 88
        assert details["overall_passed"] is True
        assert details["prose_density_score"] == 0.92
        assert details["ai_patterns_count"] == 3
        assert details["word_count_total"] == 4200
        assert details["revision_instructions"] is None

    def test_needs_assessment_returns_detail_keys(self):
        content = {
            "word_count": 3200,
            "meets_word_count": True,
            "prose_density": 0.88,
            "quality_passed": True,
            "section_word_counts": {"intro": 500, "body": 2700},
            "character_appearances": {"Dr. Smith": 3},
        }
        details = svc.extract_quality_details("needs_assessment", content)
        assert details is not None
        assert details["word_count"] == 3200
        assert details["quality_passed"] is True
        assert details["section_word_counts"] == {"intro": 500, "body": 2700}

    def test_compliance_returns_report_details(self):
        content = {
            "compliance_report": {
                "overall_verdict": "APPROVED",
                "remediation_required": False,
                "standard_checks": {"SCS1": {"status": "pass"}},
                "bias_issues": [],
            }
        }
        details = svc.extract_quality_details("compliance", content)
        assert details is not None
        assert details["overall_verdict"] == "APPROVED"
        assert details["remediation_required"] is False
        assert "SCS1" in details["standard_checks"]

    def test_compliance_returns_none_when_report_not_dict(self):
        assert svc.extract_quality_details("compliance", {"compliance_report": "bad"}) is None

    def test_returns_none_for_unknown_agent(self):
        assert svc.extract_quality_details("research", {"data": True}) is None

    def test_returns_none_for_non_dict(self):
        assert svc.extract_quality_details("prose_quality_1", [1, 2, 3]) is None


# ── extract_word_count ──────────────────────────────────────────────────


class TestExtractWordCount:
    def test_needs_assessment_uses_explicit_word_count(self):
        content = {"word_count": 3100}
        assert svc.extract_word_count("needs_assessment", content) == 3100

    def test_prose_quality_uses_word_count_total(self):
        content = {"word_count_total": 4500}
        assert svc.extract_word_count("prose_quality_1", content) == 4500

    def test_falls_back_to_splitting_document_text(self):
        content = {"research_document": "This is a test document with several words in it."}
        assert svc.extract_word_count("research", content) == 10

    def test_returns_none_for_non_dict(self):
        assert svc.extract_word_count("research", None) is None

    def test_returns_none_when_no_text_and_no_explicit_count(self):
        assert svc.extract_word_count("research", {}) is None

    def test_needs_assessment_ignores_non_int_word_count(self):
        content = {"word_count": "many", "complete_document": "One two three four five six seven eight nine ten eleven."}
        result = svc.extract_word_count("needs_assessment", content)
        assert result == 11


# ── extract_citations ───────────────────────────────────────────────────


class TestExtractCitations:
    def test_research_extracts_citations(self):
        content = {
            "research_report": {
                "citations": [
                    {"pmid": "12345", "title": "Study A"},
                    {"doi": "10.1000/xyz", "title": "Study B"},
                ]
            }
        }
        result = svc.extract_citations("research", content)
        assert len(result) == 2
        assert result[0]["pmid"] == "12345"

    def test_clinical_extracts_citations(self):
        content = {
            "clinical_practice_report": {
                "citations": [{"pmid": "99999", "title": "Clinical Study"}]
            }
        }
        result = svc.extract_citations("clinical", content)
        assert len(result) == 1

    def test_returns_empty_for_non_citation_agent(self):
        assert svc.extract_citations("gap_analysis", {"data": True}) == []
        assert svc.extract_citations("needs_assessment", {"data": True}) == []

    def test_returns_empty_when_report_missing(self):
        assert svc.extract_citations("research", {}) == []

    def test_returns_empty_when_report_not_dict(self):
        assert svc.extract_citations("research", {"research_report": "bad"}) == []

    def test_returns_empty_when_citations_not_list(self):
        content = {"research_report": {"citations": "not a list"}}
        assert svc.extract_citations("research", content) == []

    def test_returns_empty_for_non_dict_content(self):
        assert svc.extract_citations("research", None) == []


# ── extract_intake_fields ───────────────────────────────────────────────


class TestExtractIntakeFields:
    def test_creates_fields_from_intake_json(self, mock_db):
        project_id = uuid.uuid4()
        intake = {
            "section_a": {
                "project_name": "Test CME Project",
                "therapeutic_area": "Oncology",
            }
        }
        mock_query_chain(mock_db, [])
        count = svc.extract_intake_fields(project_id, intake, mock_db)
        assert count == 2
        assert mock_db.add.call_count == 2

    def test_updates_existing_field(self, mock_db):
        project_id = uuid.uuid4()
        intake = {"section_a": {"project_name": "Updated Name"}}
        existing = MagicMock()
        mock_query_chain(mock_db, [existing])
        count = svc.extract_intake_fields(project_id, intake, mock_db)
        assert count == 1
        assert existing.value_text == "Updated Name"
        assert existing.field_label == "Project Name"

    def test_boolean_value_converts_to_yes_no(self, mock_db):
        project_id = uuid.uuid4()
        intake = {"section_c": {"include_pre_test": True}}
        mock_query_chain(mock_db, [])
        svc.extract_intake_fields(project_id, intake, mock_db)
        call_args = mock_db.add.call_args
        field_obj = call_args[0][0]
        assert field_obj.value_text == "Yes"
        assert field_obj.value_json is None

    def test_list_value_stored_as_json(self, mock_db):
        project_id = uuid.uuid4()
        intake = {"section_d": {"clinical_topics": ["cardiology", "pulmonology"]}}
        mock_query_chain(mock_db, [])
        svc.extract_intake_fields(project_id, intake, mock_db)
        field_obj = mock_db.add.call_args[0][0]
        assert field_obj.value_json == ["cardiology", "pulmonology"]
        assert field_obj.value_text == str(["cardiology", "pulmonology"])

    def test_none_value_produces_none_text_and_json(self, mock_db):
        project_id = uuid.uuid4()
        intake = {"section_j": {"special_instructions": None}}
        mock_query_chain(mock_db, [])
        svc.extract_intake_fields(project_id, intake, mock_db)
        field_obj = mock_db.add.call_args[0][0]
        assert field_obj.value_text is None
        assert field_obj.value_json is None

    def test_returns_zero_for_non_dict_intake(self, mock_db):
        assert svc.extract_intake_fields(uuid.uuid4(), "bad", mock_db) == 0
        assert svc.extract_intake_fields(uuid.uuid4(), None, mock_db) == 0

    def test_skips_non_dict_sections(self, mock_db):
        intake = {"section_a": "not a dict", "section_b": {"supporter_name": "Pfizer"}}
        mock_query_chain(mock_db, [])
        count = svc.extract_intake_fields(uuid.uuid4(), intake, mock_db)
        assert count == 1

    def test_unknown_field_gets_title_cased_label(self, mock_db):
        intake = {"section_z": {"custom_field_xyz": "value"}}
        mock_query_chain(mock_db, [])
        svc.extract_intake_fields(uuid.uuid4(), intake, mock_db)
        field_obj = mock_db.add.call_args[0][0]
        assert field_obj.field_label == "Custom Field Xyz"


# ── calculate_progress ──────────────────────────────────────────────────


class TestCalculateProgress:
    def test_empty_list_returns_zero(self):
        assert svc.calculate_progress([]) == 0

    def test_all_agents_returns_100(self):
        all_agents = [meta[0] for meta in svc.AGENT_OUTPUT_META.values()]
        assert svc.calculate_progress(all_agents) == 100

    def test_half_agents_returns_approximately_50(self):
        all_agents = [meta[0] for meta in svc.AGENT_OUTPUT_META.values()]
        total = len(all_agents)
        half = total // 2
        agents = all_agents[:half]
        expected = int((half / total) * 100)
        assert svc.calculate_progress(agents) == expected

    def test_single_agent(self):
        total = len(svc.AGENT_OUTPUT_META)
        expected = int((1 / total) * 100)
        assert svc.calculate_progress(["research"]) == expected


# ── generate_embedding ──────────────────────────────────────────────────


class TestGenerateEmbedding:
    @pytest.mark.asyncio
    async def test_returns_embedding_on_success(self):
        fake_embedding = [0.1] * 768
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"embedding": fake_embedding}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("cme_sync_service.httpx.AsyncClient", return_value=mock_client):
            result = await svc.generate_embedding("This is enough text for embedding generation.")
        assert result == fake_embedding

    @pytest.mark.asyncio
    async def test_returns_none_for_short_text(self):
        result = await svc.generate_embedding("short")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_text(self):
        result = await svc.generate_embedding("")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_none(self):
        result = await svc.generate_embedding(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_embedding_wrong_dimension(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"embedding": [0.1] * 512}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("cme_sync_service.httpx.AsyncClient", return_value=mock_client):
            result = await svc.generate_embedding("This text is long enough to be embedded.")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("cme_sync_service.httpx.AsyncClient", return_value=mock_client):
            result = await svc.generate_embedding("This text is long enough for embedding generation.")
        assert result is None

    @pytest.mark.asyncio
    async def test_truncates_long_text(self):
        long_text = "word " * 10000  # 50000 chars
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"embedding": [0.1] * 768}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("cme_sync_service.httpx.AsyncClient", return_value=mock_client):
            result = await svc.generate_embedding(long_text)
        sent_prompt = mock_client.post.call_args[1]["json"]["prompt"]
        assert len(sent_prompt) <= 32000
        assert result is not None


# ── sync_project_from_thread ────────────────────────────────────────────


class TestSyncProjectFromThread:
    def _make_project(self, **overrides):
        project = MagicMock()
        project.id = overrides.get("id", uuid.uuid4())
        project.status = overrides.get("status", "processing")
        project.current_agent = overrides.get("current_agent", "research")
        project.human_review_status = overrides.get("human_review_status", None)
        project.human_review_notes = overrides.get("human_review_notes", None)
        project.agents_completed = overrides.get("agents_completed", [])
        project.agents_pending = overrides.get("agents_pending", ["research", "gap_analysis"])
        project.progress_percent = overrides.get("progress_percent", 0)
        project.completed_at = overrides.get("completed_at", None)
        project.intake = overrides.get("intake", None)
        project.errors = overrides.get("errors", None)
        return project

    def _make_thread_data(self, thread_status="idle", next_nodes=None, values=None):
        return {
            "thread": {"status": thread_status, "thread_id": "t-123"},
            "state": {
                "values": values or {},
                "next": next_nodes or [],
            },
        }

    @pytest.mark.asyncio
    async def test_idle_complete_status_mapping(self, mock_db):
        project = self._make_project()
        thread_data = self._make_thread_data(
            thread_status="idle",
            values={"status": "complete"},
        )
        mock_query_chain(mock_db, [])

        with patch("cme_sync_service.generate_embedding", new_callable=AsyncMock, return_value=None):
            result = await svc.sync_project_from_thread(project, thread_data, mock_db)
        assert result["new_status"] == "complete"
        assert project.status == "complete"

    @pytest.mark.asyncio
    async def test_idle_approved_maps_to_complete(self, mock_db):
        project = self._make_project()
        thread_data = self._make_thread_data(
            thread_status="idle",
            values={"status": "approved"},
        )
        mock_query_chain(mock_db, [])

        with patch("cme_sync_service.generate_embedding", new_callable=AsyncMock, return_value=None):
            result = await svc.sync_project_from_thread(project, thread_data, mock_db)
        assert result["new_status"] == "complete"

    @pytest.mark.asyncio
    async def test_idle_failed_maps_to_failed(self, mock_db):
        project = self._make_project()
        thread_data = self._make_thread_data(
            thread_status="idle",
            values={"status": "failed"},
        )
        mock_query_chain(mock_db, [])

        with patch("cme_sync_service.generate_embedding", new_callable=AsyncMock, return_value=None):
            result = await svc.sync_project_from_thread(project, thread_data, mock_db)
        assert result["new_status"] == "failed"

    @pytest.mark.asyncio
    async def test_busy_thread_maps_to_processing(self, mock_db):
        project = self._make_project()
        thread_data = self._make_thread_data(thread_status="busy")
        mock_query_chain(mock_db, [])

        with patch("cme_sync_service.generate_embedding", new_callable=AsyncMock, return_value=None):
            result = await svc.sync_project_from_thread(project, thread_data, mock_db)
        assert result["new_status"] == "processing"

    @pytest.mark.asyncio
    async def test_interrupted_thread_maps_to_review(self, mock_db):
        project = self._make_project()
        thread_data = self._make_thread_data(thread_status="interrupted")
        mock_query_chain(mock_db, [])

        with patch("cme_sync_service.generate_embedding", new_callable=AsyncMock, return_value=None):
            result = await svc.sync_project_from_thread(project, thread_data, mock_db)
        assert result["new_status"] == "review"

    @pytest.mark.asyncio
    async def test_next_nodes_updates_current_agent(self, mock_db):
        project = self._make_project()
        thread_data = self._make_thread_data(
            thread_status="busy",
            next_nodes=["gap_analysis"],
        )
        mock_query_chain(mock_db, [])

        with patch("cme_sync_service.generate_embedding", new_callable=AsyncMock, return_value=None):
            await svc.sync_project_from_thread(project, thread_data, mock_db)
        assert project.current_agent == "gap_analysis"

    @pytest.mark.asyncio
    async def test_agent_output_creates_records(self, mock_db):
        project = self._make_project()
        thread_data = self._make_thread_data(
            thread_status="idle",
            values={
                "status": "complete",
                "research_output": {
                    "research_document": "Full research document text with enough content.",
                    "research_report": {"citations": []},
                },
            },
        )
        mock_query_chain(mock_db, [])

        with patch("cme_sync_service.generate_embedding", new_callable=AsyncMock, return_value=None):
            result = await svc.sync_project_from_thread(project, thread_data, mock_db)
        assert "research" in result["agents_completed"]
        assert mock_db.add.called
        assert mock_db.flush.called

    @pytest.mark.asyncio
    async def test_completed_project_gets_completed_at(self, mock_db):
        project = self._make_project(completed_at=None)
        thread_data = self._make_thread_data(
            thread_status="idle",
            values={"status": "complete"},
        )
        mock_query_chain(mock_db, [])

        with patch("cme_sync_service.generate_embedding", new_callable=AsyncMock, return_value=None):
            await svc.sync_project_from_thread(project, thread_data, mock_db)
        assert project.completed_at is not None

    @pytest.mark.asyncio
    async def test_errors_propagated_to_project(self, mock_db):
        project = self._make_project()
        thread_data = self._make_thread_data(
            thread_status="idle",
            values={
                "status": "failed",
                "errors": [{"agent": "research", "message": "timeout"}],
            },
        )
        mock_query_chain(mock_db, [])

        with patch("cme_sync_service.generate_embedding", new_callable=AsyncMock, return_value=None):
            await svc.sync_project_from_thread(project, thread_data, mock_db)
        assert project.errors == [{"agent": "research", "message": "timeout"}]

    @pytest.mark.asyncio
    async def test_result_dict_structure(self, mock_db):
        project = self._make_project(status="processing")
        thread_data = self._make_thread_data(
            thread_status="idle",
            values={"status": "complete"},
        )
        mock_query_chain(mock_db, [])

        with patch("cme_sync_service.generate_embedding", new_callable=AsyncMock, return_value=None):
            result = await svc.sync_project_from_thread(project, thread_data, mock_db)
        assert "project_id" in result
        assert "old_status" in result
        assert "new_status" in result
        assert "thread_status" in result
        assert "agents_completed" in result
        assert "documents_created" in result
        assert "references_created" in result
        assert "intake_fields_created" in result
        assert "progress_percent" in result
        assert result["old_status"] == "processing"
        assert result["thread_status"] == "idle"


# ── Lookup table coverage ──────────────────────────────────────────────


class TestLookupTables:
    def test_agent_output_meta_has_12_entries(self):
        assert len(svc.AGENT_OUTPUT_META) == 12

    def test_document_text_paths_keys_match_meta_agent_names(self):
        meta_agents = {v[0] for v in svc.AGENT_OUTPUT_META.values()}
        path_agents = set(svc.DOCUMENT_TEXT_PATHS.keys())
        assert meta_agents == path_agents

    def test_node_to_agent_maps_all_pipeline_nodes(self):
        assert svc.NODE_TO_AGENT["initialize"] == "initializing"
        assert svc.NODE_TO_AGENT["human_review"] == "human_review"
        assert svc.NODE_TO_AGENT["complete"] == "complete"

    def test_thread_status_map_covers_active_states(self):
        assert svc.THREAD_STATUS_MAP["busy"] == "processing"
        assert svc.THREAD_STATUS_MAP["interrupted"] == "review"
        assert svc.THREAD_STATUS_MAP["error"] == "failed"
