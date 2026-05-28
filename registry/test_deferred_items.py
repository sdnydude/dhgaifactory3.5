"""Tests for the deferred_items API endpoints at /api/deferred-items.

Run with: pytest registry/test_deferred_items.py -v

Routes tested:
  POST   /api/deferred-items              create / upsert a deferred item
  GET    /api/deferred-items              list with filters (project/category/priority/status/limit/offset)
  POST   /api/deferred-items/search       full-text search across deferred items
  DELETE /api/deferred-items/{item_id}    delete a deferred item record
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


VALID_PAYLOAD = {
    "title": "Test deferred item for memreg tests",
    "description": "Missing validation on the frobnicator endpoint",
    "reason": "Out of scope for current ship, will address in next sprint",
    "source_context": "registry/frobnicator_endpoints.py:42",
    "priority": "medium",
    "category": "api",
    "status": "open",
    "affected_files": ["registry/frobnicator_endpoints.py"],
    "project_name": "test-project",
    "tags": ["test", "memreg"],
}


def _mock_row(**overrides):
    """Build a MagicMock with all DeferredItemResponse fields."""
    defaults = dict(
        id=uuid.uuid4(),
        title="Test deferred item",
        description="Test description",
        reason="Test reason",
        source_context=None,
        priority="medium",
        category="api",
        status="open",
        affected_files=["test.py"],
        project_name="test-project",
        tags=["test"],
        session_id=None,
        model_name=None,
        meta_data=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        last_surfaced_at=None,
    )
    defaults.update(overrides)
    row = MagicMock()
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------


class TestDeferredItemCreate:
    def test_create_empty_body_returns_422(self, client):
        r = client.post("/api/deferred-items", json={})
        assert r.status_code == 422

    def test_create_invalid_priority_returns_422(self, client):
        payload = {**VALID_PAYLOAD, "priority": "urgent"}
        r = client.post("/api/deferred-items", json=payload)
        assert r.status_code == 422
        assert "priority" in r.json()["detail"].lower()

    def test_create_invalid_category_returns_422(self, client):
        payload = {**VALID_PAYLOAD, "category": "banana"}
        r = client.post("/api/deferred-items", json=payload)
        assert r.status_code == 422
        assert "category" in r.json()["detail"].lower()

    def test_create_invalid_status_returns_422(self, client):
        payload = {**VALID_PAYLOAD, "status": "maybe"}
        r = client.post("/api/deferred-items", json=payload)
        assert r.status_code == 422
        assert "status" in r.json()["detail"].lower()

    @patch("deferred_items_endpoints.svc")
    def test_create_success_returns_201(self, mock_svc, client):
        row = _mock_row(
            title=VALID_PAYLOAD["title"],
            description=VALID_PAYLOAD["description"],
            reason=VALID_PAYLOAD["reason"],
            source_context=VALID_PAYLOAD["source_context"],
            priority=VALID_PAYLOAD["priority"],
            category=VALID_PAYLOAD["category"],
            status=VALID_PAYLOAD["status"],
            affected_files=VALID_PAYLOAD["affected_files"],
            project_name=VALID_PAYLOAD["project_name"],
            tags=VALID_PAYLOAD["tags"],
        )
        mock_svc.upsert_deferred_item.return_value = (row, True)

        r = client.post("/api/deferred-items", json=VALID_PAYLOAD)

        assert r.status_code == 201
        body = r.json()
        assert body["title"] == VALID_PAYLOAD["title"]
        assert body["project_name"] == "test-project"
        assert body["priority"] == "medium"
        assert body["category"] == "api"
        assert body["status"] == "open"

    @patch("deferred_items_endpoints.svc")
    def test_create_upsert_existing_returns_200(self, mock_svc, client):
        row = _mock_row(
            title=VALID_PAYLOAD["title"],
            project_name=VALID_PAYLOAD["project_name"],
        )
        mock_svc.upsert_deferred_item.return_value = (row, False)

        r = client.post("/api/deferred-items", json=VALID_PAYLOAD)

        assert r.status_code == 200
        body = r.json()
        assert body["title"] == VALID_PAYLOAD["title"]


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------


class TestDeferredItemList:
    @patch("deferred_items_endpoints.svc")
    def test_list_empty_returns_200(self, mock_svc, client):
        mock_svc.list_deferred_items.return_value = ([], 0)

        r = client.get("/api/deferred-items")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["deferred_items"] == []

    @patch("deferred_items_endpoints.svc")
    def test_list_with_project_filter(self, mock_svc, client):
        rows = [_mock_row(project_name="my-proj")]
        mock_svc.list_deferred_items.return_value = (rows, 1)

        r = client.get("/api/deferred-items?project_name=my-proj")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["deferred_items"][0]["project_name"] == "my-proj"

    @patch("deferred_items_endpoints.svc")
    def test_list_with_priority_filter(self, mock_svc, client):
        rows = [_mock_row(priority="critical")]
        mock_svc.list_deferred_items.return_value = (rows, 1)

        r = client.get("/api/deferred-items?priority=critical")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["deferred_items"][0]["priority"] == "critical"

    @patch("deferred_items_endpoints.svc")
    def test_list_with_status_filter(self, mock_svc, client):
        rows = [_mock_row(status="resolved")]
        mock_svc.list_deferred_items.return_value = (rows, 1)

        r = client.get("/api/deferred-items?status=resolved")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["deferred_items"][0]["status"] == "resolved"

    @patch("deferred_items_endpoints.svc")
    def test_list_pagination(self, mock_svc, client):
        rows = [_mock_row(title=f"Item {i}") for i in range(5)]
        mock_svc.list_deferred_items.return_value = (rows, 50)

        r = client.get("/api/deferred-items?limit=5&offset=10")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 50
        assert len(body["deferred_items"]) == 5


# ---------------------------------------------------------------------------
# SEARCH
# ---------------------------------------------------------------------------


class TestDeferredItemSearch:
    def test_search_empty_query_returns_422(self, client):
        r = client.post("/api/deferred-items/search", json={"query": ""})
        assert r.status_code == 422

    @patch("deferred_items_endpoints.svc")
    def test_search_returns_results(self, mock_svc, client):
        rows = [_mock_row(title="Frobnicator validation missing")]
        mock_svc.search_deferred_items.return_value = (rows, 1)

        r = client.post("/api/deferred-items/search", json={"query": "frobnicator"})

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["deferred_items"][0]["title"] == "Frobnicator validation missing"

    @patch("deferred_items_endpoints.svc")
    def test_search_with_status_filter(self, mock_svc, client):
        rows = [_mock_row(status="in_progress")]
        mock_svc.search_deferred_items.return_value = (rows, 1)

        r = client.post(
            "/api/deferred-items/search",
            json={"query": "validation", "status": "in_progress"},
        )

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["deferred_items"][0]["status"] == "in_progress"


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


class TestDeferredItemDelete:
    @patch("deferred_items_endpoints.svc")
    def test_delete_success_returns_204(self, mock_svc, client):
        row = _mock_row()
        mock_svc.delete_deferred_item.return_value = row

        r = client.delete(f"/api/deferred-items/{row.id}")

        assert r.status_code == 204
        mock_svc.delete_deferred_item.assert_called_once()

    @patch("deferred_items_endpoints.svc")
    def test_delete_not_found_returns_404(self, mock_svc, client):
        mock_svc.delete_deferred_item.return_value = None
        fake_id = uuid.uuid4()

        r = client.delete(f"/api/deferred-items/{fake_id}")

        assert r.status_code == 404


# ---------------------------------------------------------------------------
# REQUEST VALIDATION (parameter validation — no service stubbing needed)
# ---------------------------------------------------------------------------


class TestDeferredItemRequestValidation:
    """422 cases for the new query params (Task 0 of memreg-daemon plan).

    These only exercise FastAPI's request validation — no service or DB call.
    Real sort/staleness behavior is in TestDeferredItemIntegration below.
    """

    def test_invalid_sort_value_returns_422(self, client):
        r = client.get("/api/deferred-items?sort=random_order")
        assert r.status_code == 422

    def test_min_age_days_must_be_non_negative(self, client):
        r = client.get("/api/deferred-items?min_age_days=-1")
        assert r.status_code == 422

    def test_last_surfaced_before_hours_must_be_non_negative(self, client):
        r = client.get("/api/deferred-items?last_surfaced_before_hours=-1")
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# INTEGRATION (real DB, skipped when unreachable)
# ---------------------------------------------------------------------------


class TestDeferredItemIntegration:
    """Real-DB integration tests for deferred_items endpoints.

    Skipped if the registry DB is not reachable. Seeds rows with a
    pytest-di- prefixed title/project_name so they never collide with
    production data, and cleans up in try/finally so aborted runs leave
    no orphans in the shared database.
    """

    @pytest.fixture
    def real_client(self):
        import sys as _sys
        import os as _os
        _sys.path.insert(0, _os.path.dirname(__file__))
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

    def _cleanup(self, SessionLocal, *titles):
        """Remove test rows by title to keep the DB clean."""
        from models import DeferredItem
        db = SessionLocal()
        try:
            db.query(DeferredItem).filter(
                DeferredItem.title.in_(titles)
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

    def test_roundtrip_create_list_search_delete(self, real_client):
        client, SessionLocal = real_client
        unique_suffix = uuid.uuid4().hex[:8]
        title = f"pytest-di-roundtrip-{unique_suffix}"
        project_name = f"pytest-di-proj-{unique_suffix}"

        payload = {
            "title": title,
            "description": "Integration test deferred item",
            "reason": "Testing the full CRUD round-trip",
            "source_context": "registry/test_deferred_items.py:999",
            "priority": "high",
            "category": "testing",
            "status": "open",
            "affected_files": ["registry/test_deferred_items.py"],
            "project_name": project_name,
            "tags": ["pytest", "integration"],
        }

        try:
            # --- CREATE ---
            r_create = client.post("/api/deferred-items", json=payload)
            assert r_create.status_code == 201, r_create.text
            created = r_create.json()
            item_id = created["id"]
            assert created["title"] == title
            assert created["priority"] == "high"
            assert created["category"] == "testing"
            assert created["status"] == "open"
            assert created["project_name"] == project_name

            # --- UPSERT (same project_name+title, change status) ---
            upsert_payload = {**payload, "status": "in_progress", "priority": "critical"}
            r_upsert = client.post("/api/deferred-items", json=upsert_payload)
            assert r_upsert.status_code == 200, r_upsert.text
            upserted = r_upsert.json()
            assert upserted["id"] == item_id, "upsert must return the same row ID"
            assert upserted["status"] == "in_progress"
            assert upserted["priority"] == "critical"

            # --- LIST with project filter ---
            r_list = client.get(f"/api/deferred-items?project_name={project_name}")
            assert r_list.status_code == 200, r_list.text
            list_body = r_list.json()
            assert list_body["total"] >= 1
            found_titles = {di["title"] for di in list_body["deferred_items"]}
            assert title in found_titles

            # --- LIST with status filter (aliased query param) ---
            r_status = client.get(
                f"/api/deferred-items?project_name={project_name}&status=in_progress"
            )
            assert r_status.status_code == 200, r_status.text
            status_body = r_status.json()
            assert status_body["total"] >= 1
            assert all(
                di["status"] == "in_progress"
                for di in status_body["deferred_items"]
            )

            # --- SEARCH ---
            r_search = client.post(
                "/api/deferred-items/search",
                json={"query": "round-trip", "project_name": project_name},
            )
            assert r_search.status_code == 200, r_search.text
            search_body = r_search.json()
            search_titles = {di["title"] for di in search_body["deferred_items"]}
            assert title in search_titles, (
                f"full-text search should find the seeded row; got {search_titles}"
            )

            # --- DELETE ---
            r_delete = client.delete(f"/api/deferred-items/{item_id}")
            assert r_delete.status_code == 204, r_delete.text

            # --- VERIFY GONE ---
            r_gone = client.delete(f"/api/deferred-items/{item_id}")
            assert r_gone.status_code == 404

        finally:
            self._cleanup(SessionLocal, title)

    def test_capture_script_payload_format(self, real_client):
        """Verify the exact JSON shape used by post-deferred-items.sh works."""
        client, SessionLocal = real_client
        unique_suffix = uuid.uuid4().hex[:8]
        title = f"pytest-di-capture-{unique_suffix}"
        project_name = f"pytest-di-capture-proj-{unique_suffix}"

        capture_payload = {
            "title": title,
            "description": "Capture script E2E test",
            "reason": "Verifying memreg pipeline end-to-end",
            "source_context": "/ship advisor fix",
            "priority": "medium",
            "category": "testing",
            "project_name": project_name,
            "affected_files": ["registry/test_deferred_items.py"],
            "tags": ["memreg", "e2e", "capture-script"],
            "model_name": "claude-opus-4-6",
        }

        try:
            r = client.post("/api/deferred-items", json=capture_payload)
            assert r.status_code == 201, r.text
            body = r.json()
            assert body["title"] == title
            assert body["project_name"] == project_name
            assert body["tags"] == ["memreg", "e2e", "capture-script"]
            assert body["category"] == "testing"
            assert "id" in body
            assert "created_at" in body

            r_verify = client.get(
                f"/api/deferred-items?project_name={project_name}"
            )
            assert r_verify.status_code == 200
            items = r_verify.json()["deferred_items"]
            assert len(items) == 1
            assert items[0]["title"] == title

            client.delete(f"/api/deferred-items/{body['id']}")
        finally:
            self._cleanup(SessionLocal, title)

    def test_stats_age_histogram_counts_open_only(self, real_client):
        """Age histogram buckets must count only open items, not resolved."""
        client, SessionLocal = real_client
        unique_suffix = uuid.uuid4().hex[:8]
        project_name = f"pytest-di-stats-{unique_suffix}"
        title_open = f"pytest-di-stats-open-{unique_suffix}"
        title_resolved = f"pytest-di-stats-resolved-{unique_suffix}"

        try:
            for title, status in [
                (title_open, "open"),
                (title_resolved, "resolved"),
            ]:
                r = client.post("/api/deferred-items", json={
                    "title": title,
                    "description": "Stats test item",
                    "reason": "Testing age histogram filter",
                    "priority": "medium",
                    "category": "testing",
                    "status": status,
                    "project_name": project_name,
                    "tags": ["pytest", "stats"],
                })
                assert r.status_code == 201, r.text

            r_stats = client.get(
                f"/api/deferred-items/stats?project_name={project_name}"
            )
            assert r_stats.status_code == 200
            stats = r_stats.json()

            assert stats["total"] == 2
            assert stats["by_status"]["open"] == 1
            assert stats["by_status"]["resolved"] == 1

            histogram_total = sum(stats["age_histogram"].values())
            assert histogram_total == 1, (
                f"Age histogram should count only open items (1), got {histogram_total}"
            )
        finally:
            self._cleanup(SessionLocal, title_open, title_resolved)

    # -----------------------------------------------------------------------
    # Task 0 (memreg-daemon): sort + last_surfaced_at behavior against real DB
    # -----------------------------------------------------------------------

    def _seed_with_created_at(self, SessionLocal, *, title, project_name, age_days):
        """Insert a deferred item with a backdated created_at."""
        from datetime import datetime, timezone, timedelta
        from models import DeferredItem
        import uuid as _uuid
        db = SessionLocal()
        try:
            row = DeferredItem(
                id=_uuid.uuid4(),
                title=title,
                description="Sort/staleness integration test",
                reason="Testing Task 0",
                priority="high",
                category="testing",
                status="open",
                project_name=project_name,
                tags=["pytest", "task-0"],
                created_at=datetime.now(timezone.utc) - timedelta(days=age_days),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return str(row.id)
        finally:
            db.close()

    def test_sort_created_at_asc_returns_oldest_first(self, real_client):
        """The whole point of Task 0: oldest open items must come first when sort=asc."""
        client, SessionLocal = real_client
        suffix = uuid.uuid4().hex[:8]
        project = f"pytest-di-sort-{suffix}"
        titles = [
            f"pytest-di-sort-old-{suffix}",
            f"pytest-di-sort-mid-{suffix}",
            f"pytest-di-sort-new-{suffix}",
        ]
        try:
            self._seed_with_created_at(SessionLocal, title=titles[0], project_name=project, age_days=30)
            self._seed_with_created_at(SessionLocal, title=titles[1], project_name=project, age_days=15)
            self._seed_with_created_at(SessionLocal, title=titles[2], project_name=project, age_days=1)

            r = client.get(
                f"/api/deferred-items?project_name={project}"
                "&status=open&priority=high&sort=created_at_asc&limit=5"
            )
            assert r.status_code == 200, r.text
            returned = [item["title"] for item in r.json()["deferred_items"]]
            assert returned == titles, (
                f"sort=created_at_asc must return oldest-first; got {returned}"
            )
        finally:
            self._cleanup(SessionLocal, *titles)

    def test_default_sort_is_created_at_desc(self, real_client):
        """Backward compatibility: default sort must remain newest-first."""
        client, SessionLocal = real_client
        suffix = uuid.uuid4().hex[:8]
        project = f"pytest-di-default-{suffix}"
        titles = [
            f"pytest-di-default-old-{suffix}",
            f"pytest-di-default-new-{suffix}",
        ]
        try:
            self._seed_with_created_at(SessionLocal, title=titles[0], project_name=project, age_days=30)
            self._seed_with_created_at(SessionLocal, title=titles[1], project_name=project, age_days=1)

            r = client.get(
                f"/api/deferred-items?project_name={project}&status=open&priority=high&limit=5"
            )
            assert r.status_code == 200, r.text
            returned = [item["title"] for item in r.json()["deferred_items"]]
            assert returned[0] == titles[1], (
                f"default sort must remain DESC (newest-first); got {returned}"
            )
        finally:
            self._cleanup(SessionLocal, *titles)

    def test_min_age_days_filter_excludes_recent(self, real_client):
        client, SessionLocal = real_client
        suffix = uuid.uuid4().hex[:8]
        project = f"pytest-di-age-{suffix}"
        old_title = f"pytest-di-age-old-{suffix}"
        new_title = f"pytest-di-age-new-{suffix}"
        try:
            self._seed_with_created_at(SessionLocal, title=old_title, project_name=project, age_days=30)
            self._seed_with_created_at(SessionLocal, title=new_title, project_name=project, age_days=1)

            r = client.get(
                f"/api/deferred-items?project_name={project}&status=open&min_age_days=7&limit=10"
            )
            assert r.status_code == 200, r.text
            titles = {item["title"] for item in r.json()["deferred_items"]}
            assert old_title in titles
            assert new_title not in titles
        finally:
            self._cleanup(SessionLocal, old_title, new_title)

    def test_last_surfaced_at_starts_null(self, real_client):
        client, SessionLocal = real_client
        suffix = uuid.uuid4().hex[:8]
        title = f"pytest-di-surf-init-{suffix}"
        project = f"pytest-di-surf-{suffix}"
        try:
            r_create = client.post("/api/deferred-items", json={
                "title": title, "description": "test", "reason": "test",
                "priority": "high", "category": "testing", "status": "open",
                "project_name": project, "tags": ["pytest"],
            })
            assert r_create.status_code == 201
            assert r_create.json()["last_surfaced_at"] is None
        finally:
            self._cleanup(SessionLocal, title)

    def test_mark_surfaced_bumps_timestamp(self, real_client):
        """POST /api/deferred-items/{id}/surfaced sets last_surfaced_at = now()."""
        client, SessionLocal = real_client
        suffix = uuid.uuid4().hex[:8]
        title = f"pytest-di-bump-{suffix}"
        project = f"pytest-di-bump-{suffix}"
        try:
            r_create = client.post("/api/deferred-items", json={
                "title": title, "description": "test", "reason": "test",
                "priority": "high", "category": "testing", "status": "open",
                "project_name": project, "tags": ["pytest"],
            })
            assert r_create.status_code == 201
            item_id = r_create.json()["id"]
            assert r_create.json()["last_surfaced_at"] is None

            r_surf = client.post(f"/api/deferred-items/{item_id}/surfaced")
            assert r_surf.status_code == 200, r_surf.text
            assert r_surf.json()["last_surfaced_at"] is not None
        finally:
            self._cleanup(SessionLocal, title)

    def test_mark_surfaced_unknown_id_returns_404(self, real_client):
        client, _ = real_client
        fake_id = uuid.uuid4()
        r = client.post(f"/api/deferred-items/{fake_id}/surfaced")
        assert r.status_code == 404

    def test_last_surfaced_before_hours_filter_excludes_recently_surfaced(self, real_client):
        """The exact daemon Step 6/8 filter: only surface items not seen in the last N hours."""
        client, SessionLocal = real_client
        suffix = uuid.uuid4().hex[:8]
        project = f"pytest-di-lsb-{suffix}"
        surfaced_title = f"pytest-di-lsb-surfaced-{suffix}"
        unsurfaced_title = f"pytest-di-lsb-unsurfaced-{suffix}"
        try:
            sid = self._seed_with_created_at(
                SessionLocal, title=surfaced_title, project_name=project, age_days=10,
            )
            self._seed_with_created_at(
                SessionLocal, title=unsurfaced_title, project_name=project, age_days=10,
            )

            # Mark one as just-surfaced
            r_surf = client.post(f"/api/deferred-items/{sid}/surfaced")
            assert r_surf.status_code == 200

            # Query for items not surfaced in last 1 hour — should exclude the one we just bumped
            r = client.get(
                f"/api/deferred-items?project_name={project}&status=open"
                "&sort=created_at_asc&last_surfaced_before_hours=1&limit=10"
            )
            assert r.status_code == 200, r.text
            titles = {item["title"] for item in r.json()["deferred_items"]}
            assert unsurfaced_title in titles  # never surfaced (NULL passes filter)
            assert surfaced_title not in titles  # just-surfaced is filtered out
        finally:
            self._cleanup(SessionLocal, surfaced_title, unsurfaced_title)
