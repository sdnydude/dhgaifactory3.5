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

import pytest

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


class TestDevChangelogRealDB:
    """Real-DB integration tests for dev_changelog endpoints.

    Skipped if the registry DB is not reachable. Seeds rows with a pytest-dc-
    prefixed slug so they never collide with the 16 seed rows from migration
    007, and cleans up in try/finally so aborted runs leave no orphans in
    the shared database.

    These tests exist because the mock tests in TestDevChangelogList /
    TestDevChangelogDetail / TestDevChangelogPatch cannot exercise the
    SQLAlchemy→Pydantic round-trip. They lock to .query().filter().first()
    call chains and would pass falsely if the query shape changed. See
    memory `feedback_serializer_drift.md` for the underlying lesson from
    ticket #52.
    """

    @pytest.fixture
    def real_client(self):
        try:
            from database import SessionLocal, get_db
            from api import app
        except Exception as e:
            pytest.skip(f"registry api import failed: {e}")

        try:
            import sqlalchemy
            probe = SessionLocal()
            probe.execute(sqlalchemy.text("SELECT 1"))
            probe.close()
        except Exception as e:
            pytest.skip(f"registry DB not reachable: {e}")

        def override_get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        from fastapi.testclient import TestClient
        with TestClient(app) as c:
            yield c, SessionLocal
        app.dependency_overrides.clear()

    def _seed_entry(
        self,
        SessionLocal,
        slug=None,
        epic="pytest dev changelog entry",
        category="feature",
        detected_status="shipped",
        declared_status=None,
        window_start=None,
        commit_count=1,
        commits=None,
        key_insight=None,
        notes=None,
        priority=None,
    ):
        from models import DevChangelog
        if slug is None:
            slug = f"pytest-dc-{uuid4().hex[:8]}"
        if window_start is None:
            window_start = date(2026, 4, 14)
        if commits is None:
            commits = [
                {
                    "sha": "abc1234",
                    "date": "2026-04-14",
                    "subject": "test commit subject",
                    "author": "pytest",
                }
            ]
        db = SessionLocal()
        try:
            row = DevChangelog(
                slug=slug,
                epic=epic,
                category=category,
                detected_status=detected_status,
                declared_status=declared_status,
                window_start=window_start,
                commit_count=commit_count,
                commits=commits,
                sessions=[],
                key_insight=key_insight,
                notes=notes,
                priority=priority,
                source="manual",
            )
            db.add(row)
            db.commit()
            return slug
        finally:
            db.close()

    def _cleanup(self, SessionLocal, *slugs):
        from models import DevChangelog
        db = SessionLocal()
        try:
            db.query(DevChangelog).filter(DevChangelog.slug.in_(slugs)).delete(
                synchronize_session=False
            )
            db.commit()
        finally:
            db.close()

    def test_list_real_db_returns_seeded_entries(self, real_client):
        client, SessionLocal = real_client
        slug_a = self._seed_entry(SessionLocal, epic="real-db test A")
        slug_b = self._seed_entry(SessionLocal, epic="real-db test B")
        try:
            r = client.get("/api/dev-changelog?q=real-db test")
            assert r.status_code == 200, r.text
            body = r.json()
            found = {e["slug"] for e in body["entries"]}
            assert slug_a in found
            assert slug_b in found
        finally:
            self._cleanup(SessionLocal, slug_a, slug_b)

    def test_list_real_db_status_filter_uses_coalesce(self, real_client):
        """COALESCE(declared_status, detected_status) must filter on the
        display status, not the raw column. A row with detected=in_progress
        and declared=shipped must be returned for status=shipped, not
        status=in_progress."""
        client, SessionLocal = real_client
        slug_override = self._seed_entry(
            SessionLocal,
            epic="coalesce override test",
            detected_status="in_progress",
            declared_status="shipped",
        )
        slug_raw = self._seed_entry(
            SessionLocal,
            epic="coalesce raw test",
            detected_status="in_progress",
            declared_status=None,
        )
        try:
            r_shipped = client.get("/api/dev-changelog?status=shipped&q=coalesce")
            assert r_shipped.status_code == 200, r_shipped.text
            shipped_slugs = {e["slug"] for e in r_shipped.json()["entries"]}
            assert slug_override in shipped_slugs, "declared_status override should flip display to shipped"
            assert slug_raw not in shipped_slugs

            r_inprog = client.get("/api/dev-changelog?status=in_progress&q=coalesce")
            assert r_inprog.status_code == 200, r_inprog.text
            inprog_slugs = {e["slug"] for e in r_inprog.json()["entries"]}
            assert slug_raw in inprog_slugs
            assert slug_override not in inprog_slugs, "overridden row should not appear under raw detected status"
        finally:
            self._cleanup(SessionLocal, slug_override, slug_raw)

    def test_list_real_db_q_search_ilike_three_columns(self, real_client):
        """Search must match epic, key_insight, AND notes — validates the
        or_(ilike, ilike, ilike) SQL path. Uses three rows, one hit per
        column, with a shared needle that only appears in the target column
        of each row."""
        client, SessionLocal = real_client
        needle = f"ndl{uuid4().hex[:6]}"
        slug_epic = self._seed_entry(
            SessionLocal, epic=f"epic hit {needle}", key_insight="", notes=""
        )
        slug_insight = self._seed_entry(
            SessionLocal, epic="insight row", key_insight=f"insight hit {needle}", notes=""
        )
        slug_notes = self._seed_entry(
            SessionLocal, epic="notes row", key_insight="", notes=f"notes hit {needle}"
        )
        try:
            r = client.get(f"/api/dev-changelog?q={needle}")
            assert r.status_code == 200, r.text
            hits = {e["slug"] for e in r.json()["entries"]}
            assert slug_epic in hits
            assert slug_insight in hits
            assert slug_notes in hits
        finally:
            self._cleanup(SessionLocal, slug_epic, slug_insight, slug_notes)

    def test_get_real_db_returns_entry_with_commits_jsonb(self, real_client):
        """Serializer-drift guard. JSONB commits column must round-trip
        through DevChangelogEntry.model_validate into list[dict] without
        losing fields. Mocks cannot catch this — they return a Python list
        directly, bypassing the Postgres→psycopg2→SQLAlchemy→Pydantic chain."""
        client, SessionLocal = real_client
        commits_fixture = [
            {
                "sha": "deadbeef",
                "date": "2026-04-14",
                "subject": "first commit",
                "author": "alice",
            },
            {
                "sha": "cafebabe",
                "date": "2026-04-14",
                "subject": "second commit with unicode: ψ ☢ 🎯",
                "author": "bob",
            },
        ]
        slug = self._seed_entry(
            SessionLocal,
            epic="jsonb round-trip test",
            commit_count=2,
            commits=commits_fixture,
        )
        try:
            r = client.get(f"/api/dev-changelog/{slug}")
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["slug"] == slug
            assert body["commit_count"] == 2
            assert body["commits"] == commits_fixture, "JSONB commits must survive round-trip byte-identical"
        finally:
            self._cleanup(SessionLocal, slug)

    def test_patch_real_db_bumps_last_human_edit_at_and_persists(self, real_client):
        client, SessionLocal = real_client
        slug = self._seed_entry(
            SessionLocal,
            epic="patch round-trip test",
            declared_status=None,
            priority=None,
        )
        try:
            r_before = client.get(f"/api/dev-changelog/{slug}")
            assert r_before.status_code == 200
            before_last_edit = r_before.json()["last_human_edit_at"]

            r_patch = client.patch(
                f"/api/dev-changelog/{slug}",
                json={"declared_status": "backlog", "priority": 7, "notes": "changed"},
            )
            assert r_patch.status_code == 200, r_patch.text

            r_after = client.get(f"/api/dev-changelog/{slug}")
            assert r_after.status_code == 200
            after = r_after.json()
            assert after["declared_status"] == "backlog"
            assert after["priority"] == 7
            assert after["notes"] == "changed"
            assert after["last_human_edit_at"] is not None
            assert after["last_human_edit_at"] != before_last_edit
        finally:
            self._cleanup(SessionLocal, slug)

    def test_patch_real_db_rejects_agent_owned_field_without_db_write(self, real_client):
        """extra='forbid' must fire at the Pydantic layer before the handler
        touches the DB, so an invalid PATCH neither updates columns nor
        bumps last_human_edit_at."""
        client, SessionLocal = real_client
        slug = self._seed_entry(
            SessionLocal, epic="forbid guard test", declared_status="shipped"
        )
        try:
            before = client.get(f"/api/dev-changelog/{slug}").json()

            r = client.patch(
                f"/api/dev-changelog/{slug}",
                json={"commits": [{"sha": "evil"}]},
            )
            assert r.status_code == 422, r.text

            after = client.get(f"/api/dev-changelog/{slug}").json()
            assert after["commits"] == before["commits"]
            assert after["last_human_edit_at"] == before["last_human_edit_at"]
        finally:
            self._cleanup(SessionLocal, slug)

    def test_patch_real_db_nonexistent_slug_returns_404(self, real_client):
        client, _ = real_client
        r = client.patch(
            "/api/dev-changelog/pytest-dc-does-not-exist",
            json={"notes": "hi"},
        )
        assert r.status_code == 404
