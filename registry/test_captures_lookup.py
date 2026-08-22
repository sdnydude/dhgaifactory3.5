"""Tests for GET /api/captures/lookup — natural-key landing verification.

The lookup route lets capture clients (capture-guarantee Stop hook) ask
"did this capture land?" by pipeline + project + natural-key value, without
knowing per-table key columns. Read-open, matching registry read posture.
"""
import uuid
from unittest.mock import MagicMock


def _row(row_id=None):
    row = MagicMock()
    row.id = row_id or uuid.uuid4()
    return row


class TestCapturesLookup:
    def test_insights_hit_returns_found_with_id(self, client, mock_db):
        row = _row()
        mock_db.query.return_value.filter.return_value.first.return_value = row
        resp = client.get(
            "/api/captures/lookup",
            params={"pipeline": "insights", "project": "portage", "key": "some tldr"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["found"] is True
        assert body["pipeline"] == "insights"
        assert body["id"] == str(row.id)

    def test_miss_returns_404(self, client, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        resp = client.get(
            "/api/captures/lookup",
            params={"pipeline": "insights", "project": "portage", "key": "absent"},
        )
        assert resp.status_code == 404

    def test_unknown_pipeline_returns_400(self, client, mock_db):
        resp = client.get(
            "/api/captures/lookup",
            params={"pipeline": "nonsense", "project": "portage", "key": "x"},
        )
        assert resp.status_code == 400
        assert "insights" in resp.json()["detail"]
