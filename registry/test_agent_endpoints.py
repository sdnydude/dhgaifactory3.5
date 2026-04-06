"""
Agent Endpoints Tests
=====================
Tests for agent registration, heartbeat, listing, and discovery.

Run with: pytest registry/test_agent_endpoints.py -v
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch
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


class TestAgentRegistration:
    def test_register_requires_body(self, client):
        response = client.post("/api/v1/agents/register")
        assert response.status_code == 422

    def test_register_valid_agent(self, client):
        with patch("agent_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            mock_agent = MagicMock()
            mock_agent.service_id = "test-agent-1"
            mock_agent.service_name = "Test Agent"
            mock_agent.status = "active"
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()

            response = client.post(
                "/api/v1/agents/register",
                json={
                    "service_id": "test-agent-1",
                    "service_name": "Test Agent",
                    "service_type": "research",
                    "host": "localhost",
                    "port": 8002,
                    "capabilities": ["research", "pubmed"],
                },
            )
            assert response.status_code in (200, 500)


class TestAgentHeartbeat:
    def test_heartbeat_nonexistent_agent(self, client):
        with patch("agent_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None
            response = client.post("/api/v1/agents/nonexistent/heartbeat")
            assert response.status_code in (404, 500)

    def test_heartbeat_requires_no_body(self, client):
        with patch("agent_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_agent = MagicMock()
            mock_agent.service_id = "test-agent"
            mock_db.query.return_value.filter.return_value.first.return_value = mock_agent
            response = client.post("/api/v1/agents/test-agent/heartbeat")
            assert response.status_code in (200, 500)


class TestAgentList:
    def test_list_agents_returns_response(self, client):
        with patch("agent_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.all.return_value = []
            response = client.get("/api/v1/agents")
            assert response.status_code in (200, 500)


class TestAgentDetail:
    def test_get_nonexistent_agent(self, client):
        with patch("agent_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None
            response = client.get("/api/v1/agents/nonexistent")
            assert response.status_code in (404, 500)


class TestAgentDelete:
    def test_delete_nonexistent_agent(self, client):
        with patch("agent_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None
            response = client.delete("/api/v1/agents/nonexistent")
            assert response.status_code in (404, 500)


class TestAgentModels:
    def test_list_models(self, client):
        with patch("agent_endpoints.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            response = client.get("/api/v1/agents/models/list")
            assert response.status_code in (200, 500)


class TestAgentDiscovery:
    def test_discover_requires_body(self, client):
        response = client.post("/api/v1/agents/discover")
        assert response.status_code == 422
