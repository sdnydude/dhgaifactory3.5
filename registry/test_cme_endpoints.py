"""
CME Endpoints Tests
===================
Tests for CME project CRUD, agent output storage, and execution control.

Run with: pytest registry/test_cme_endpoints.py -v
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestCMEProjectCreate:
    def test_create_project_requires_body(self, client):
        response = client.post("/api/cme/projects")
        assert response.status_code == 422

    def test_create_project_invalid_payload_rejected(self, client):
        """Sending a flat dict instead of the IntakeSubmission schema returns 422."""
        response = client.post(
            "/api/cme/projects",
            json={"name": "Test", "therapeutic_area": "Cardiology"},
        )
        assert response.status_code == 422


class TestCMEProjectList:
    def test_list_projects_returns_list(self, client, mock_db):
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        response = client.get("/api/cme/projects")
        assert response.status_code == 200

    def test_list_projects_with_valid_status_filter(self, client, mock_db):
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        response = client.get("/api/cme/projects?status=intake")
        assert response.status_code == 200

    def test_list_projects_invalid_status_rejected(self, client):
        """Invalid status enum value returns 422."""
        response = client.get("/api/cme/projects?status=invalid_status")
        assert response.status_code == 422


class TestCMEProjectDetail:
    def test_get_nonexistent_project(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = client.get(f"/api/cme/projects/{fake_id}")
        assert response.status_code == 404


class TestCMEProjectUpdate:
    """Tests for PUT /api/cme/projects/{id}."""

    VALID_INTAKE = {
        "section_a": {
            "project_name": "HFrEF GDMT Update 2026",
            "therapeutic_area": ["cardiology"],
            "disease_state": ["heart failure"],
            "target_audience_primary": ["cardiologists"],
        },
        "section_b": {"supporter_name": "Acme Pharma"},
        "section_c": {"learning_format": "webinar", "include_post_test": False, "include_pre_test": False},
        "section_d": {"clinical_topics": ["SGLT2 inhibitors"]},
        "section_e": {},
        "section_f": {},
        "section_g": {},
        "section_h": {},
        "section_i": {
            "accme_compliant": True,
            "financial_disclosure_required": True,
            "off_label_discussion": False,
            "commercial_support_acknowledgment": True,
        },
        "section_j": {},
    }

    def test_update_nonexistent_returns_404(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = client.put(f"/api/cme/projects/{fake_id}", json=self.VALID_INTAKE)
        assert response.status_code == 404

    def test_update_non_intake_returns_409(self, client, mock_db):
        """Cannot edit a project that has already started processing."""
        fake_id = str(uuid.uuid4())
        mock_project = MagicMock()
        mock_project.status = "processing"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project
        response = client.put(f"/api/cme/projects/{fake_id}", json=self.VALID_INTAKE)
        assert response.status_code == 409

    def test_update_requires_valid_body(self, client):
        fake_id = str(uuid.uuid4())
        response = client.put(f"/api/cme/projects/{fake_id}", json={"bad": "data"})
        assert response.status_code == 422


class TestCMEProjectArchive:
    """Tests for POST /api/cme/projects/{id}/archive."""

    def test_archive_nonexistent_returns_404(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = client.post(f"/api/cme/projects/{fake_id}/archive")
        assert response.status_code == 404

    def test_archive_already_archived_returns_400(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        mock_project = MagicMock()
        mock_project.status = "archived"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project
        response = client.post(f"/api/cme/projects/{fake_id}/archive")
        assert response.status_code == 400

    def test_archive_intake_project_succeeds(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        mock_project = MagicMock()
        mock_project.id = fake_id
        mock_project.status = "intake"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project
        response = client.post(f"/api/cme/projects/{fake_id}/archive")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "archived"

    def test_archive_complete_project_succeeds(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        mock_project = MagicMock()
        mock_project.id = fake_id
        mock_project.status = "complete"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project
        response = client.post(f"/api/cme/projects/{fake_id}/archive")
        assert response.status_code == 200


class TestCMEProjectExecution:
    def test_start_project_requires_valid_id(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = client.post(f"/api/cme/projects/{fake_id}/start")
        assert response.status_code == 404

    def test_pause_project_nonexistent(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = client.post(f"/api/cme/projects/{fake_id}/pause")
        assert response.status_code == 404

    def test_cancel_project_nonexistent(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = client.post(f"/api/cme/projects/{fake_id}/cancel")
        assert response.status_code == 404


class TestCMEProjectOutputs:
    def test_get_outputs_for_nonexistent_project(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = client.get(f"/api/cme/projects/{fake_id}/outputs")
        assert response.status_code in (200, 404)

    def test_get_output_by_agent_name(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = client.get(f"/api/cme/projects/{fake_id}/outputs/research")
        assert response.status_code == 404


class TestCMEWebhooks:
    def test_agent_complete_webhook_requires_body(self, client):
        response = client.post("/api/cme/webhook/agent-complete")
        assert response.status_code == 422

    def test_pipeline_status_webhook_requires_body(self, client):
        response = client.post("/api/cme/webhook/pipeline-status")
        assert response.status_code == 422


class TestCMEReviewers:
    def test_list_reviewers(self, client, mock_db):
        mock_db.query.return_value.filter.return_value.all.return_value = []
        response = client.get("/api/cme/reviewers")
        assert response.status_code == 200

    def test_create_reviewer_requires_body(self, client):
        response = client.post("/api/cme/reviewers")
        assert response.status_code == 422

    def test_delete_nonexistent_reviewer(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = client.delete(f"/api/cme/reviewers/{fake_id}")
        assert response.status_code in (204, 404)


class TestCMESearch:
    def test_search_requires_query(self, client):
        response = client.get("/api/cme/search")
        assert response.status_code in (200, 422)

    def test_search_with_query(self, client, mock_db):
        mock_db.execute.return_value.fetchall.return_value = []
        response = client.get("/api/cme/search?q=cardiology")
        assert response.status_code == 200


class TestIntakePrefill:
    """Tests for POST /api/cme/intake/prefill."""

    def test_prefill_requires_body(self, client):
        response = client.post("/api/cme/intake/prefill")
        assert response.status_code == 422

    def test_prefill_rejects_incomplete_section_a(self, client):
        """Missing required fields in Section A returns 422."""
        response = client.post(
            "/api/cme/intake/prefill",
            json={"project_name": "Test"},
        )
        assert response.status_code == 422

    def test_prefill_rejects_short_project_name(self, client):
        """Project name under 5 chars returns 422."""
        response = client.post(
            "/api/cme/intake/prefill",
            json={
                "project_name": "Hi",
                "therapeutic_area": ["cardiology"],
                "disease_state": ["heart failure"],
                "target_audience_primary": ["cardiologists"],
            },
        )
        assert response.status_code == 422

    @patch("cme_endpoints.trigger_intake_prefill")
    def test_prefill_success(self, mock_trigger, client):
        """Valid Section A payload invokes the prefill agent and returns 200."""
        mock_trigger.return_value = {
            "prefill_sections": {
                "section_b": {"supporter_name": ""},
                "section_c": {"learning_format": "webinar"},
            },
            "research_summary": "Reviewed 10 articles on heart failure.",
            "confidence": {"section_b": "low", "section_c": "medium"},
        }
        response = client.post(
            "/api/cme/intake/prefill",
            json={
                "project_name": "HFrEF GDMT Update",
                "therapeutic_area": ["cardiology"],
                "disease_state": ["heart failure"],
                "target_audience_primary": ["cardiologists"],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "prefill_sections" in body
        assert "research_summary" in body
        assert "confidence" in body
        mock_trigger.assert_called_once()

    @patch("cme_endpoints.trigger_intake_prefill")
    def test_prefill_agent_failure_returns_502(self, mock_trigger, client):
        """Agent failure returns 502 with error message."""
        mock_trigger.side_effect = Exception("LangGraph Cloud timeout")
        response = client.post(
            "/api/cme/intake/prefill",
            json={
                "project_name": "HFrEF GDMT Update",
                "therapeutic_area": ["cardiology"],
                "disease_state": ["heart failure"],
                "target_audience_primary": ["cardiologists"],
            },
        )
        assert response.status_code == 502
        assert "prefill" in response.json()["detail"].lower() or \
               "unavailable" in response.json()["detail"].lower()
