"""Tests for the CME stats endpoints at /api/cme/stats.

Run with:
    pytest registry/test_cme_stats_endpoints.py -v
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


MOCK_PIPELINE_STATS = {
    "projects_by_status": {"draft": 3, "processing": 1, "complete": 2},
    "total_projects": 6,
    "total_runs": 12,
    "total_documents": 45,
    "total_references": 120,
    "agent_completion": [
        {"agent": "research", "count": 6, "avg_quality": 0.85},
    ],
    "document_throughput": [
        {"type": "needs_assessment", "count": 6, "avg_words": 3100, "avg_quality": 0.82},
    ],
    "avg_run_duration_sec": 42.5,
    "active_pipelines": [],
}

MOCK_SERVICE_HEALTH = {
    "service_count": 29,
    "services": [{"name": "incident_service", "domain": "Incident Management"}],
    "db_active_connections": 5,
    "table_counts": {"cme_projects": 6, "cme_documents": 45},
}


class TestPipelineStats:
    @patch("cme_stats_endpoints.svc")
    def test_returns_200_with_data(self, mock_svc, client):
        mock_svc.get_pipeline_stats.return_value = MOCK_PIPELINE_STATS
        r = client.get("/api/cme/stats/pipeline")
        assert r.status_code == 200
        data = r.json()
        assert data["total_projects"] == 6
        assert data["total_runs"] == 12
        assert data["total_documents"] == 45
        mock_svc.get_pipeline_stats.assert_called_once()

    @patch("cme_stats_endpoints.svc")
    def test_returns_all_expected_keys(self, mock_svc, client):
        mock_svc.get_pipeline_stats.return_value = MOCK_PIPELINE_STATS
        r = client.get("/api/cme/stats/pipeline")
        data = r.json()
        expected_keys = {
            "projects_by_status", "total_projects", "total_runs",
            "total_documents", "total_references", "agent_completion",
            "document_throughput", "avg_run_duration_sec", "active_pipelines",
        }
        assert set(data.keys()) == expected_keys

    @patch("cme_stats_endpoints.svc")
    def test_service_error_returns_500(self, mock_svc, client):
        mock_svc.get_pipeline_stats.side_effect = RuntimeError("DB connection lost")
        r = client.get("/api/cme/stats/pipeline")
        assert r.status_code == 500
        assert r.json()["detail"] == "Internal server error"

    @patch("cme_stats_endpoints.svc")
    def test_empty_data_returns_200(self, mock_svc, client):
        empty = {
            "projects_by_status": {},
            "total_projects": 0,
            "total_runs": 0,
            "total_documents": 0,
            "total_references": 0,
            "agent_completion": [],
            "document_throughput": [],
            "avg_run_duration_sec": None,
            "active_pipelines": [],
        }
        mock_svc.get_pipeline_stats.return_value = empty
        r = client.get("/api/cme/stats/pipeline")
        assert r.status_code == 200
        data = r.json()
        assert data["total_projects"] == 0
        assert data["avg_run_duration_sec"] is None


class TestHelpers:
    def test_float_or_none_with_value(self):
        from cme_stats_service import _float_or_none
        assert _float_or_none(3.14) == 3.14

    def test_float_or_none_with_none(self):
        from cme_stats_service import _float_or_none
        assert _float_or_none(None) is None

    def test_float_or_none_with_decimal(self):
        from decimal import Decimal
        from cme_stats_service import _float_or_none
        assert _float_or_none(Decimal("0.85")) == 0.85

    def test_int_or_zero_with_value(self):
        from cme_stats_service import _int_or_zero
        assert _int_or_zero(42) == 42

    def test_int_or_zero_with_none(self):
        from cme_stats_service import _int_or_zero
        assert _int_or_zero(None) == 0


class TestServiceHealth:
    @patch("cme_stats_endpoints.svc")
    def test_returns_200_with_data(self, mock_svc, client):
        mock_svc.get_service_health.return_value = MOCK_SERVICE_HEALTH
        r = client.get("/api/cme/stats/services")
        assert r.status_code == 200
        data = r.json()
        assert data["service_count"] == 29
        assert data["db_active_connections"] == 5
        mock_svc.get_service_health.assert_called_once()

    @patch("cme_stats_endpoints.svc")
    def test_returns_all_expected_keys(self, mock_svc, client):
        mock_svc.get_service_health.return_value = MOCK_SERVICE_HEALTH
        r = client.get("/api/cme/stats/services")
        data = r.json()
        expected_keys = {"service_count", "services", "db_active_connections", "table_counts"}
        assert set(data.keys()) == expected_keys

    @patch("cme_stats_endpoints.svc")
    def test_service_error_returns_500(self, mock_svc, client):
        mock_svc.get_service_health.side_effect = RuntimeError("pg_stat_activity denied")
        r = client.get("/api/cme/stats/services")
        assert r.status_code == 500
        assert r.json()["detail"] == "Internal server error"

    @patch("cme_stats_endpoints.svc")
    def test_table_counts_structure(self, mock_svc, client):
        mock_svc.get_service_health.return_value = MOCK_SERVICE_HEALTH
        r = client.get("/api/cme/stats/services")
        data = r.json()
        assert isinstance(data["table_counts"], dict)
        assert "cme_projects" in data["table_counts"]
