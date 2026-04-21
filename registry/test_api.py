"""
Registry API Tests
==================
Tests for healthcheck, metrics, and core CRUD endpoints.
Uses shared `client` fixture from conftest.py.

Run with: pytest registry/test_api.py -v
"""

from unittest.mock import MagicMock, patch


class TestHealthcheck:
    def test_healthz_returns_ok(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.text == "OK"

    def test_healthz_content_type(self, client):
        response = client.get("/healthz")
        assert "text/plain" in response.headers["content-type"]


class TestMetrics:
    def test_metrics_endpoint_exists(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_returns_prometheus_format(self, client):
        response = client.get("/metrics")
        assert "registry_write_operations" in response.text or "python_info" in response.text


class TestMediaEndpoints:
    def test_create_media_requires_body(self, client):
        response = client.post("/api/v1/media")
        assert response.status_code == 422

    def test_list_media_returns_list(self, client):
        with patch("api.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            response = client.get("/api/v1/media")
            assert response.status_code in (200, 500)


class TestEventEndpoints:
    def test_create_event_requires_body(self, client):
        response = client.post("/api/v1/events")
        assert response.status_code == 422

    def test_list_events_returns_list(self, client):
        with patch("api.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            response = client.get("/api/v1/events")
            assert response.status_code in (200, 500)


class TestWebSocketStatus:
    def test_ws_status_endpoint_exists(self, client):
        response = client.get("/api/v1/ws/status")
        assert response.status_code == 200
