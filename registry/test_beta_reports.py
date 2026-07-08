"""Tests for the beta_reports API endpoints at /api/beta-reports.

Run with:
    pytest registry/test_beta_reports.py -v
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from beta_reports_schemas import BetaReportUpdate, BetaReportResponse


VALID_PAYLOAD = {
    "project_name": "portage",
    "reporter_email": "tester@example.com",
    "reporter_user_id": "6f1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8",
    "page": "/listings/new",
    "area": "listing-flow",
    "severity": "medium",
    "description": "Publish button stays disabled after all fields are filled",
    "screenshot_url": "https://images.example.com/report-1.png",
}


def _mock_report_row(**overrides):
    """Build a MagicMock that looks like a BetaReport ORM row."""
    defaults = dict(
        id=uuid.uuid4(),
        project_name="portage",
        reporter_email="tester@example.com",
        reporter_user_id=None,
        page="/listings/new",
        area="listing-flow",
        severity="medium",
        description="Publish button stays disabled",
        screenshot_url=None,
        status="open",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    row = MagicMock()
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


class TestBetaReportSchemas:
    def test_update_rejects_unknown_fields(self):
        with pytest.raises(Exception):
            BetaReportUpdate(status="triaged", description="not allowed")

    def test_response_exposes_all_fields(self):
        row = _mock_report_row(status="triaged", severity="high")
        resp = BetaReportResponse.model_validate(row)
        assert resp.status == "triaged"
        assert resp.severity == "high"
        assert resp.page == "/listings/new"


class TestBetaReportCreate:
    def test_create_empty_body_returns_422(self, client):
        r = client.post("/api/beta-reports", json={})
        assert r.status_code == 422

    def test_create_invalid_severity_returns_422(self, client):
        payload = {**VALID_PAYLOAD, "severity": "apocalyptic"}
        r = client.post("/api/beta-reports", json=payload)
        assert r.status_code == 422

    def test_create_unknown_field_returns_422(self, client):
        payload = {**VALID_PAYLOAD, "banana": True}
        r = client.post("/api/beta-reports", json=payload)
        assert r.status_code == 422

    @patch("beta_reports_endpoints.svc")
    def test_create_success_returns_201(self, mock_svc, client):
        row = _mock_report_row()
        mock_svc.create_beta_report.return_value = row

        r = client.post("/api/beta-reports", json=VALID_PAYLOAD)

        assert r.status_code == 201, r.text
        body = r.json()
        assert body["id"] == str(row.id)
        assert body["project_name"] == "portage"
        assert body["status"] == "open"
        mock_svc.create_beta_report.assert_called_once()

    @patch("beta_reports_endpoints.svc")
    def test_create_service_error_returns_500(self, mock_svc, client):
        mock_svc.create_beta_report.side_effect = RuntimeError("db down")

        r = client.post("/api/beta-reports", json=VALID_PAYLOAD)

        assert r.status_code == 500


class TestBetaReportList:
    @patch("beta_reports_endpoints.svc")
    def test_list_returns_reports_and_total(self, mock_svc, client):
        rows = [_mock_report_row(), _mock_report_row(severity="high")]
        mock_svc.list_beta_reports.return_value = (rows, 2)

        r = client.get("/api/beta-reports")

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 2
        assert len(body["beta_reports"]) == 2

    @patch("beta_reports_endpoints.svc")
    def test_list_passes_filters(self, mock_svc, client):
        mock_svc.list_beta_reports.return_value = ([], 0)

        r = client.get(
            "/api/beta-reports",
            params={"project_name": "portage", "status": "open",
                    "severity": "high", "limit": 5, "offset": 10},
        )

        assert r.status_code == 200
        _, kwargs = mock_svc.list_beta_reports.call_args
        assert kwargs["project_name"] == "portage"
        assert kwargs["status"] == "open"
        assert kwargs["severity"] == "high"
        assert kwargs["limit"] == 5
        assert kwargs["offset"] == 10

    def test_list_invalid_limit_returns_422(self, client):
        r = client.get("/api/beta-reports", params={"limit": 0})
        assert r.status_code == 422


class TestBetaReportUpdate:
    @patch("beta_reports_endpoints.svc")
    def test_patch_updates_status(self, mock_svc, client):
        row = _mock_report_row(status="triaged")
        mock_svc.update_beta_report.return_value = row

        r = client.patch(
            f"/api/beta-reports/{row.id}",
            json={"status": "triaged"},
        )

        assert r.status_code == 200, r.text
        assert r.json()["status"] == "triaged"

    @patch("beta_reports_endpoints.svc")
    def test_patch_updates_area_and_severity(self, mock_svc, client):
        row = _mock_report_row(area="photos", severity="critical")
        mock_svc.update_beta_report.return_value = row

        r = client.patch(
            f"/api/beta-reports/{row.id}",
            json={"area": "photos", "severity": "critical"},
        )

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["area"] == "photos"
        assert body["severity"] == "critical"

    def test_patch_invalid_status_returns_422(self, client):
        r = client.patch(
            f"/api/beta-reports/{uuid.uuid4()}",
            json={"status": "banana"},
        )
        assert r.status_code == 422

    def test_patch_invalid_severity_returns_422(self, client):
        r = client.patch(
            f"/api/beta-reports/{uuid.uuid4()}",
            json={"severity": "banana"},
        )
        assert r.status_code == 422

    @patch("beta_reports_endpoints.svc")
    def test_patch_missing_report_returns_404(self, mock_svc, client):
        mock_svc.update_beta_report.return_value = None

        r = client.patch(
            f"/api/beta-reports/{uuid.uuid4()}",
            json={"status": "resolved"},
        )

        assert r.status_code == 404
