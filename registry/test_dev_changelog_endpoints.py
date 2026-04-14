"""Tests for the dev_changelog admin/reporting API.

Six cases matching the Build 1 spec (§9):
  1. GET list returns all seeded entries
  2. GET list with status=shipped filter
  3. GET {slug} returns detail with commits array
  4. PATCH {slug} with declared_status updates and bumps last_human_edit_at
  5. PATCH {slug} with agent-owned field is rejected (extra='forbid' → 422)
  6. PATCH nonexistent slug returns 404
"""
import os
import sys
from datetime import date, datetime, timezone
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import DevChangelog


def _fake_entry(**overrides):
    """Build a real DevChangelog instance (unattached to any session) for mock returns."""
    defaults = dict(
        id=uuid4(),
        slug="telemetry-pipeline",
        epic="LangGraph Telemetry Pipeline (OTel/Tempo)",
        category="debt",
        detected_status="in_progress",
        declared_status=None,
        window_start=date(2026, 3, 6),
        window_end=None,
        commit_count=14,
        commits=[
            {"sha": "c7b46e6", "date": "2026-04-12", "subject": "fix(tracing): swap OTLP gRPC for HTTP"},
            {"sha": "f236196", "date": "2026-04-12", "subject": "fix(tracing): attach BatchSpanProcessor to langsmith"},
        ],
        sessions=[],
        key_insight="DEBT not feature",
        notes=None,
        priority=None,
        locked=False,
        source="manual",
        detected_at=datetime.now(timezone.utc),
        last_agent_run_at=None,
        last_human_edit_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return DevChangelog(**defaults)


class TestDevChangelogList:
    def test_list_returns_all_seeded(self, client, mock_db):
        rows = [_fake_entry(slug=f"entry-{i}") for i in range(16)]
        mock_db.query.return_value.count.return_value = 16
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = rows

        r = client.get("/api/dev-changelog")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 16
        assert len(body["entries"]) == 16

    def test_list_with_status_shipped_filter(self, client, mock_db):
        shipped = [_fake_entry(slug=f"shipped-{i}", detected_status="shipped") for i in range(12)]
        filtered_q = mock_db.query.return_value.filter.return_value
        filtered_q.count.return_value = 12
        filtered_q.order_by.return_value.offset.return_value.limit.return_value.all.return_value = shipped

        r = client.get("/api/dev-changelog?status=shipped")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 12
        assert all(e["detected_status"] == "shipped" for e in body["entries"])


class TestDevChangelogDetail:
    def test_detail_returns_commits_array(self, client, mock_db):
        entry = _fake_entry(slug="telemetry-pipeline", commit_count=14)
        mock_db.query.return_value.filter.return_value.first.return_value = entry

        r = client.get("/api/dev-changelog/telemetry-pipeline")

        assert r.status_code == 200
        body = r.json()
        assert body["slug"] == "telemetry-pipeline"
        assert body["commit_count"] == 14
        assert len(body["commits"]) >= 1
        assert body["commits"][0]["sha"] == "c7b46e6"


class TestDevChangelogPatch:
    def test_patch_human_field_bumps_timestamp(self, client, mock_db):
        row = _fake_entry()
        before = row.last_human_edit_at
        mock_db.query.return_value.filter.return_value.first.return_value = row

        r = client.patch(
            "/api/dev-changelog/telemetry-pipeline",
            json={"declared_status": "backlog"},
        )

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["declared_status"] == "backlog"
        assert row.last_human_edit_at is not None
        assert row.last_human_edit_at != before

    def test_patch_agent_owned_field_rejected(self, client):
        r = client.patch(
            "/api/dev-changelog/anything",
            json={"commits": [{"sha": "evil"}]},
        )
        assert r.status_code == 422

    def test_patch_missing_slug_returns_404(self, client, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        r = client.patch(
            "/api/dev-changelog/nonexistent",
            json={"notes": "hi"},
        )

        assert r.status_code == 404
