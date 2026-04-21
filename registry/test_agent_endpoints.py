"""
Agent Endpoints Tests
=====================
Tests for agent registration, heartbeat, listing, and discovery.

Run with: pytest registry/test_agent_endpoints.py -v
"""

from unittest.mock import MagicMock


class TestAgentRegistration:
    def test_register_requires_body(self, client):
        response = client.post("/api/v1/agents/register")
        assert response.status_code == 422

    def test_register_valid_agent(self, client, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        response = client.post(
            "/api/v1/agents/register",
            json={
                "service": {
                    "id": "test-agent-1",
                    "name": "Test Agent",
                    "version": "1.0.0",
                    "division": "DHG AI",
                    "type": "research_agent",
                },
                "capabilities": {
                    "primary": ["research", "pubmed"],
                },
            },
        )
        assert response.status_code in (200, 201)


class TestAgentHeartbeat:
    def test_heartbeat_nonexistent_agent(self, client, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = client.post(
            "/api/v1/agents/nonexistent/heartbeat",
            json={"status": "healthy"},
        )
        assert response.status_code == 404

    def test_heartbeat_valid_agent(self, client, mock_db):
        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.status = "active"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_agent
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        response = client.post(
            "/api/v1/agents/test-agent/heartbeat",
            json={"status": "healthy"},
        )
        assert response.status_code == 200


class TestAgentList:
    def test_list_agents_returns_response(self, client, mock_db):
        mock_db.query.return_value.all.return_value = []
        response = client.get("/api/v1/agents")
        assert response.status_code == 200


class TestAgentDetail:
    def test_get_nonexistent_agent(self, client, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = client.get("/api/v1/agents/nonexistent")
        assert response.status_code == 404


class TestAgentDelete:
    def test_delete_nonexistent_agent(self, client, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = client.delete("/api/v1/agents/nonexistent")
        assert response.status_code == 404


class TestAgentModels:
    def test_list_models(self, client, mock_db):
        response = client.get("/api/v1/agents/models/list")
        assert response.status_code == 200


class TestAgentDiscovery:
    def test_discover_requires_body(self, client):
        response = client.post("/api/v1/agents/discover")
        assert response.status_code == 422
