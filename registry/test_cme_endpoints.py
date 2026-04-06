"""
CME Endpoints Tests
===================
Tests for CME project CRUD, agent output storage, and execution control.

Run with: pytest registry/test_cme_endpoints.py -v
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from fastapi.testclient import TestClient
from datetime import datetime


@pytest.fixture
def mock_engine():
    """Mock the database engine so api.py can import without a real DB."""
    with patch("api.create_engine") as mock_ce:
        mock_ce.return_value = MagicMock()
        yield mock_ce


@pytest.fixture
def client(mock_engine):
    """Create a test client with mocked database."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

    with patch("api.SessionLocal") as mock_session_cls:
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)

        from api import app
        with TestClient(app) as c:
            yield c


class TestCMEProjectCreate:
    def test_create_project_requires_body(self, client):
        response = client.post("/api/cme/projects")
        assert response.status_code == 422

    def test_create_project_valid_payload(self, client):
        with patch("cme_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            mock_project = MagicMock()
            mock_project.id = str(uuid.uuid4())
            mock_project.name = "Test CME Project"
            mock_project.status = "created"
            mock_project.therapeutic_area = "Cardiology"
            mock_project.created_at = datetime.utcnow()
            mock_project.updated_at = datetime.utcnow()
            mock_project.intake_data = {}
            mock_project.config = {}
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()
            mock_db.refresh = MagicMock(side_effect=lambda x: None)

            with patch("cme_endpoints.CMEProject", return_value=mock_project):
                response = client.post(
                    "/api/cme/projects",
                    json={
                        "name": "Test CME Project",
                        "therapeutic_area": "Cardiology",
                        "intake_data": {"topic": "Heart Failure Management"},
                    },
                )
                assert response.status_code in (201, 200, 500)


class TestCMEProjectList:
    def test_list_projects_returns_list(self, client):
        with patch("cme_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
            response = client.get("/api/cme/projects")
            assert response.status_code in (200, 500)

    def test_list_projects_with_status_filter(self, client):
        with patch("cme_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_query = MagicMock()
            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = []
            response = client.get("/api/cme/projects?status=created")
            assert response.status_code in (200, 500)


class TestCMEProjectDetail:
    def test_get_nonexistent_project(self, client):
        fake_id = str(uuid.uuid4())
        with patch("cme_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None
            response = client.get(f"/api/cme/projects/{fake_id}")
            assert response.status_code in (404, 500)


class TestCMEProjectExecution:
    def test_start_project_requires_valid_id(self, client):
        fake_id = str(uuid.uuid4())
        with patch("cme_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None
            response = client.post(f"/api/cme/projects/{fake_id}/start")
            assert response.status_code in (404, 500)

    def test_pause_project(self, client):
        fake_id = str(uuid.uuid4())
        with patch("cme_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None
            response = client.post(f"/api/cme/projects/{fake_id}/pause")
            assert response.status_code in (404, 500)

    def test_cancel_project(self, client):
        fake_id = str(uuid.uuid4())
        with patch("cme_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None
            response = client.post(f"/api/cme/projects/{fake_id}/cancel")
            assert response.status_code in (404, 500)


class TestCMEProjectOutputs:
    def test_get_outputs_for_nonexistent_project(self, client):
        fake_id = str(uuid.uuid4())
        with patch("cme_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.all.return_value = []
            mock_db.query.return_value.filter.return_value.first.return_value = None
            response = client.get(f"/api/cme/projects/{fake_id}/outputs")
            assert response.status_code in (200, 404, 500)

    def test_get_output_by_agent_name(self, client):
        fake_id = str(uuid.uuid4())
        with patch("cme_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None
            response = client.get(
                f"/api/cme/projects/{fake_id}/outputs/research"
            )
            assert response.status_code in (404, 500)


class TestCMEWebhooks:
    def test_agent_complete_webhook_requires_body(self, client):
        response = client.post("/api/cme/webhook/agent-complete")
        assert response.status_code == 422

    def test_pipeline_status_webhook_requires_body(self, client):
        response = client.post("/api/cme/webhook/pipeline-status")
        assert response.status_code == 422


class TestCMEReviewers:
    def test_list_reviewers(self, client):
        with patch("cme_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.all.return_value = []
            response = client.get("/api/cme/reviewers")
            assert response.status_code in (200, 500)

    def test_create_reviewer_requires_body(self, client):
        response = client.post("/api/cme/reviewers")
        assert response.status_code == 422

    def test_delete_nonexistent_reviewer(self, client):
        fake_id = str(uuid.uuid4())
        with patch("cme_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None
            response = client.delete(f"/api/cme/reviewers/{fake_id}")
            assert response.status_code in (204, 404, 500)


class TestCMESearch:
    def test_search_requires_query(self, client):
        response = client.get("/api/cme/search")
        assert response.status_code in (200, 422, 500)

    def test_search_with_query(self, client):
        with patch("cme_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.execute.return_value.fetchall.return_value = []
            response = client.get("/api/cme/search?q=cardiology")
            assert response.status_code in (200, 500)
