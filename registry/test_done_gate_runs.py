"""Tests for the done_gate_runs API endpoints at /api/done-gate-runs.

Run with:
    POSTGRES_PASSWORD=test pytest registry/test_done_gate_runs.py -v
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from done_gate_runs_schemas import VALID_ADJUDICATIONS


VALID_PAYLOAD = {
    "session_id": "sess-abc123",
    "project": "dhg-memreg",
    "verdict": "fail",
    "claim": {"terms": ["done"], "snippet": "All tests pass, we're done."},
    "evidence": [],
    "gate_mode": "observe",
    "check_version": 3,
}


def _mock_run_row(**overrides):
    """Build a MagicMock that looks like a DoneGateRun ORM row."""
    defaults = dict(
        id=uuid.uuid4(),
        session_id="sess-abc123",
        project="dhg-memreg",
        verdict="fail",
        claim={"terms": ["done"], "snippet": "All tests pass, we're done."},
        evidence=[],
        gate_mode="observe",
        check_version=3,
        adjudication=None,
        sampled=False,
        meta_data=None,
        created_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    row = MagicMock()
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


class TestDoneGateSchemas:
    def test_false_negative_is_valid_adjudication(self):
        assert "false_negative" in VALID_ADJUDICATIONS

    def test_create_sampled_flag_defaults_false(self):
        from done_gate_runs_schemas import DoneGateRunCreate

        base = DoneGateRunCreate(session_id="s1", project="p1", verdict="pass")
        assert base.sampled is False
        flagged = DoneGateRunCreate(
            session_id="s1", project="p1", verdict="no_claim", sampled=True,
        )
        assert flagged.sampled is True


class TestDoneGateCreate:
    @patch("done_gate_runs_endpoints.svc")
    def test_create_success_returns_201(self, mock_svc, client):
        row = _mock_run_row()
        mock_svc.create_run.return_value = row

        r = client.post("/api/done-gate-runs", json=VALID_PAYLOAD)

        assert r.status_code == 201, r.text
        body = r.json()
        assert body["id"] == str(row.id)
        assert body["verdict"] == "fail"
        assert body["check_version"] == 3
        assert body["sampled"] is False
        mock_svc.create_run.assert_called_once()

    def test_create_invalid_verdict_returns_422(self, client):
        payload = {**VALID_PAYLOAD, "verdict": "maybe"}
        r = client.post("/api/done-gate-runs", json=payload)
        assert r.status_code == 422


class TestDoneGateList:
    @patch("done_gate_runs_endpoints.svc")
    def test_list_passes_filters_and_returns_runs(self, mock_svc, client):
        rows = [_mock_run_row(), _mock_run_row(verdict="pass")]
        mock_svc.list_runs.return_value = (rows, 2)

        r = client.get(
            "/api/done-gate-runs",
            params={"project": "dhg-memreg", "verdict": "fail",
                    "adjudicated": "false", "check_version": 3,
                    "limit": 5, "offset": 0},
        )

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 2
        assert len(body["runs"]) == 2
        _, kwargs = mock_svc.list_runs.call_args
        assert kwargs["project"] == "dhg-memreg"
        assert kwargs["verdict"] == "fail"
        assert kwargs["adjudicated"] is False
        assert kwargs["check_version"] == 3
        assert kwargs["limit"] == 5


class TestDoneGateAdjudicate:
    @patch("done_gate_runs_endpoints.svc")
    def test_adjudicate_sets_value(self, mock_svc, client):
        row = _mock_run_row(adjudication="true_positive")
        mock_svc.adjudicate_run.return_value = row

        r = client.patch(
            f"/api/done-gate-runs/{row.id}/adjudicate",
            json={"adjudication": "true_positive"},
        )

        assert r.status_code == 200, r.text
        assert r.json()["adjudication"] == "true_positive"
        args, _ = mock_svc.adjudicate_run.call_args
        assert args[2] == "true_positive"

    def test_adjudicate_invalid_value_returns_422(self, client):
        r = client.patch(
            f"/api/done-gate-runs/{uuid.uuid4()}/adjudicate",
            json={"adjudication": "banana"},
        )
        assert r.status_code == 422

    @patch("done_gate_runs_endpoints.svc")
    def test_adjudicate_missing_run_returns_404(self, mock_svc, client):
        mock_svc.adjudicate_run.return_value = None

        r = client.patch(
            f"/api/done-gate-runs/{uuid.uuid4()}/adjudicate",
            json={"adjudication": "false_negative"},
        )

        assert r.status_code == 404


class TestDoneGateStats:
    @patch("done_gate_runs_endpoints.svc")
    def test_stats_returns_per_version_rollup(self, mock_svc, client):
        mock_svc.stats.return_value = [
            {"check_version": 3, "total": 10, "passes": 4, "fails": 6,
             "adjudicated": 5, "true_positives": 4, "false_positives": 1,
             "false_negatives": 0, "sampled_total": 2, "precision": 0.8},
        ]

        r = client.get("/api/done-gate-runs/stats",
                       params={"project": "dhg-memreg"})

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["project"] == "dhg-memreg"
        v3 = body["versions"][0]
        assert v3["check_version"] == 3
        assert v3["precision"] == 0.8
        assert v3["false_negatives"] == 0
        assert v3["sampled_total"] == 2


class TestFalseDoneCategoryAndModel:
    def test_false_done_is_valid_correction_category(self):
        from corrections_schemas import VALID_CATEGORIES

        assert "false-done" in VALID_CATEGORIES

    def test_model_constraint_allows_false_negative_and_sampled_column(self):
        from models import DoneGateRun

        constraints = {
            c.sqltext.text
            for c in DoneGateRun.__table__.constraints
            if hasattr(c, "sqltext")
        }
        assert any("false_negative" in text for text in constraints)
        assert "sampled" in DoneGateRun.__table__.columns
