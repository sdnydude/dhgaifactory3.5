"""
Session Logger Stats Endpoint Tests
====================================
Tests for /sessions/stats/overview, /sessions/stats/daily, /sessions/stats/concepts.

Run with: cd services/session-logger && python -m pytest test_stats.py -v
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, date, timezone

# Mock the connection pool before importing main (pool initializes at import time)
mock_pool = MagicMock()
mock_pool.closed = False

with patch.dict(os.environ, {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_USER": "test",
    "POSTGRES_PASSWORD": "test",
    "POSTGRES_DB": "test",
}):
    with patch("psycopg2.pool.ThreadedConnectionPool", return_value=mock_pool):
        sys.path.insert(0, os.path.dirname(__file__))
        from main import app

from fastapi.testclient import TestClient


@pytest.fixture
def mock_cursor():
    """Create a fresh mock psycopg2 cursor for each test."""
    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = cursor
    mock_pool.getconn.return_value = conn
    return cursor


@pytest.fixture
def client():
    """Create a test client."""
    with TestClient(app) as c:
        yield c


class TestStatsOverview:
    def test_returns_valid_json(self, client, mock_cursor):
        mock_cursor.fetchone.return_value = (
            5, 20, 12, 36, 18,
            datetime(2026, 3, 10, tzinfo=timezone.utc),
            datetime(2026, 3, 14, tzinfo=timezone.utc),
        )
        response = client.get("/sessions/stats/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 5
        assert data["total_chunks"] == 20
        assert data["total_concepts"] == 12
        assert data["total_edges"] == 36
        assert data["avg_chunks_per_session"] == 4.0
        assert data["embedding_coverage_pct"] == 90.0
        assert data["earliest_session"] is not None
        assert data["latest_session"] is not None

    def test_empty_db_returns_zeroes(self, client, mock_cursor):
        mock_cursor.fetchone.return_value = (0, 0, 0, 0, 0, None, None)
        response = client.get("/sessions/stats/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 0
        assert data["total_chunks"] == 0
        assert data["avg_chunks_per_session"] == 0.0
        assert data["embedding_coverage_pct"] == 0.0
        assert data["earliest_session"] is None
        assert data["latest_session"] is None

    def test_db_error_returns_sanitized_500(self, client, mock_cursor):
        mock_cursor.execute.side_effect = Exception("connection refused host=db.internal")
        response = client.get("/sessions/stats/overview")
        assert response.status_code == 500
        assert "connection refused" not in response.json()["detail"]
        assert response.json()["detail"] == "Failed to fetch stats overview"


class TestStatsDaily:
    def test_returns_7_days(self, client, mock_cursor):
        rows = [(date(2026, 3, d), 0) for d in range(8, 15)]
        rows[5] = (date(2026, 3, 13), 2)
        mock_cursor.fetchall.return_value = rows
        response = client.get("/sessions/stats/daily")
        assert response.status_code == 200
        data = response.json()
        assert len(data["days"]) == 7
        assert data["period_start"] == "2026-03-08"
        assert data["period_end"] == "2026-03-14"

    def test_zero_fill_days_included(self, client, mock_cursor):
        rows = [(date(2026, 3, d), 0) for d in range(8, 15)]
        rows[5] = (date(2026, 3, 13), 3)
        mock_cursor.fetchall.return_value = rows
        response = client.get("/sessions/stats/daily")
        data = response.json()
        zero_days = [d for d in data["days"] if d["session_count"] == 0]
        assert len(zero_days) == 6

    def test_empty_db_returns_empty_days(self, client, mock_cursor):
        mock_cursor.fetchall.return_value = []
        response = client.get("/sessions/stats/daily")
        assert response.status_code == 200
        data = response.json()
        assert data["days"] == []

    def test_db_error_returns_sanitized_500(self, client, mock_cursor):
        mock_cursor.execute.side_effect = Exception("relation session_logs does not exist")
        response = client.get("/sessions/stats/daily")
        assert response.status_code == 500
        assert "session_logs" not in response.json()["detail"]
        assert response.json()["detail"] == "Failed to fetch daily stats"


class TestStatsConcepts:
    def test_returns_ranked_concepts(self, client, mock_cursor):
        mock_cursor.fetchall.side_effect = [
            [("docker", "command", 8), ("curl", "command", 5)],
            [("command", 9), ("file_path", 2)],
        ]
        mock_cursor.fetchone.side_effect = [(12,), (36,)]
        response = client.get("/sessions/stats/concepts")
        assert response.status_code == 200
        data = response.json()
        assert len(data["top_concepts"]) == 2
        assert data["top_concepts"][0]["name"] == "docker"
        assert data["top_concepts"][0]["edge_count"] >= data["top_concepts"][1]["edge_count"]
        assert data["total_nodes"] == 12
        assert data["total_edges"] == 36

    def test_node_type_breakdown(self, client, mock_cursor):
        mock_cursor.fetchall.side_effect = [
            [("exit", "command", 10)],
            [("command", 9), ("file_path", 2), ("error", 1)],
        ]
        mock_cursor.fetchone.side_effect = [(12,), (36,)]
        response = client.get("/sessions/stats/concepts")
        data = response.json()
        assert len(data["node_type_breakdown"]) == 3
        types = [t["node_type"] for t in data["node_type_breakdown"]]
        assert "command" in types

    def test_custom_limit_parameter(self, client, mock_cursor):
        mock_cursor.fetchall.side_effect = [
            [("docker", "command", 8)],
            [("command", 1)],
        ]
        mock_cursor.fetchone.side_effect = [(1,), (1,)]
        response = client.get("/sessions/stats/concepts?limit=5")
        assert response.status_code == 200

    def test_empty_db_returns_empty_arrays(self, client, mock_cursor):
        mock_cursor.fetchall.side_effect = [[], []]
        mock_cursor.fetchone.side_effect = [(0,), (0,)]
        response = client.get("/sessions/stats/concepts")
        assert response.status_code == 200
        data = response.json()
        assert data["top_concepts"] == []
        assert data["node_type_breakdown"] == []
        assert data["total_nodes"] == 0
        assert data["total_edges"] == 0

    def test_db_error_returns_sanitized_500(self, client, mock_cursor):
        mock_cursor.execute.side_effect = Exception("permission denied for table concept_nodes")
        response = client.get("/sessions/stats/concepts")
        assert response.status_code == 500
        assert "concept_nodes" not in response.json()["detail"]
        assert response.json()["detail"] == "Failed to fetch concept stats"


class TestMetrics:
    def test_metrics_endpoint_exists(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_returns_prometheus_format(self, client):
        response = client.get("/metrics")
        assert "session_logger_read_operations" in response.text or "python_info" in response.text
