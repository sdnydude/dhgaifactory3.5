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
from unittest.mock import AsyncMock, MagicMock, patch

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

    @patch("deferred_items_endpoints.get_embedding", new_callable=AsyncMock, create=True)
    @patch("deferred_items_endpoints._upsert_deferred_item")
    def test_create_success_returns_201(self, mock_upsert, mock_embed, client):
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
        mock_upsert.return_value = (row, True)
        mock_embed.return_value = [0.0] * 768

        r = client.post("/api/deferred-items", json=VALID_PAYLOAD)

        assert r.status_code == 201
        body = r.json()
        assert body["title"] == VALID_PAYLOAD["title"]
        assert body["project_name"] == "test-project"
        assert body["priority"] == "medium"
        assert body["category"] == "api"
        assert body["status"] == "open"

    @patch("deferred_items_endpoints.get_embedding", new_callable=AsyncMock, create=True)
    @patch("deferred_items_endpoints._upsert_deferred_item")
    def test_create_upsert_existing_returns_200(self, mock_upsert, mock_embed, client):
        row = _mock_row(
            title=VALID_PAYLOAD["title"],
            project_name=VALID_PAYLOAD["project_name"],
        )
        mock_upsert.return_value = (row, False)
        mock_embed.return_value = [0.0] * 768

        r = client.post("/api/deferred-items", json=VALID_PAYLOAD)

        assert r.status_code == 200
        body = r.json()
        assert body["title"] == VALID_PAYLOAD["title"]


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------


class TestDeferredItemList:
    def test_list_empty_returns_200(self, client, mock_db):
        mock_db.query.return_value.count.return_value = 0
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        r = client.get("/api/deferred-items")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["deferred_items"] == []

    def test_list_with_project_filter(self, client, mock_db):
        rows = [_mock_row(project_name="my-proj")]
        filtered_q = mock_db.query.return_value.filter.return_value
        filtered_q.count.return_value = 1
        filtered_q.order_by.return_value.offset.return_value.limit.return_value.all.return_value = rows

        r = client.get("/api/deferred-items?project_name=my-proj")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["deferred_items"][0]["project_name"] == "my-proj"

    def test_list_with_priority_filter(self, client, mock_db):
        rows = [_mock_row(priority="critical")]
        filtered_q = mock_db.query.return_value.filter.return_value
        filtered_q.count.return_value = 1
        filtered_q.order_by.return_value.offset.return_value.limit.return_value.all.return_value = rows

        r = client.get("/api/deferred-items?priority=critical")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["deferred_items"][0]["priority"] == "critical"

    def test_list_with_status_filter(self, client, mock_db):
        rows = [_mock_row(status="resolved")]
        filtered_q = mock_db.query.return_value.filter.return_value
        filtered_q.count.return_value = 1
        filtered_q.order_by.return_value.offset.return_value.limit.return_value.all.return_value = rows

        r = client.get("/api/deferred-items?status=resolved")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["deferred_items"][0]["status"] == "resolved"

    def test_list_pagination(self, client, mock_db):
        rows = [_mock_row(title=f"Item {i}") for i in range(5)]
        filtered_q = mock_db.query.return_value
        filtered_q.count.return_value = 50
        filtered_q.order_by.return_value.offset.return_value.limit.return_value.all.return_value = rows

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

    def test_search_returns_results(self, client, mock_db):
        rows = [_mock_row(title="Frobnicator validation missing")]
        search_q = mock_db.query.return_value.filter.return_value
        search_q.count.return_value = 1
        search_q.order_by.return_value.limit.return_value.all.return_value = rows

        r = client.post("/api/deferred-items/search", json={"query": "frobnicator"})

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["deferred_items"][0]["title"] == "Frobnicator validation missing"

    def test_search_with_status_filter(self, client, mock_db):
        rows = [_mock_row(status="in_progress")]
        search_q = mock_db.query.return_value.filter.return_value
        filtered_q = search_q.filter.return_value
        filtered_q.count.return_value = 1
        filtered_q.order_by.return_value.limit.return_value.all.return_value = rows

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
    def test_delete_success_returns_204(self, client, mock_db):
        row = _mock_row()
        mock_db.query.return_value.filter.return_value.first.return_value = row

        r = client.delete(f"/api/deferred-items/{row.id}")

        assert r.status_code == 204
        mock_db.delete.assert_called_once_with(row)
        mock_db.commit.assert_called_once()

    def test_delete_not_found_returns_404(self, client, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        fake_id = uuid.uuid4()

        r = client.delete(f"/api/deferred-items/{fake_id}")

        assert r.status_code == 404


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
