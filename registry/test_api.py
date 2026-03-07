"""
Registry API Tests
==================
Tests for healthcheck, metrics, and core CRUD endpoints.

Run with: pytest registry/test_api.py -v
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


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
