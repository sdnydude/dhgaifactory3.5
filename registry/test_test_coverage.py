"""Tests for the test-coverage API endpoints.

Covers CRUD + search for /api/test-coverage.

Run: pytest registry/test_test_coverage.py -v
"""
import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


VALID_PAYLOAD = {
    "title": "Test coverage event for memreg tests",
    "test_count_before": 227,
    "test_count_after": 240,
    "delta": 13,
    "tests_added": ["test_bug_fixes::test_create", "test_bug_fixes::test_list"],
    "tests_removed": [],
    "tests_modified": [],
    "files_affected": ["registry/test_bug_fixes.py"],
    "category": "api",
    "trigger": "Ship B: memreg knowledge-generating tests",
    "project_name": "test-project",
    "tags": ["test", "memreg"],
}


def _mock_row(**overrides):
    """Build a MagicMock with all response fields populated."""
    defaults = dict(
        id=uuid.uuid4(),
        title="Test coverage event",
        test_count_before=100,
        test_count_after=110,
        delta=10,
        tests_added=["test_new"],
        tests_removed=[],
        tests_modified=[],
        files_affected=["test.py"],
        category="api",
        trigger="memreg ship",
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


class TestTestCoverageCreate:
    def test_create_empty_body_returns_422(self, client):
        r = client.post("/api/test-coverage", json={})
        assert r.status_code == 422

    def test_create_invalid_category_returns_422(self, client):
        payload = {**VALID_PAYLOAD, "category": "banana"}
        r = client.post("/api/test-coverage", json=payload)
        assert r.status_code == 422

    @patch("test_coverage_endpoints.get_embedding", new_callable=AsyncMock, create=True)
    @patch("test_coverage_endpoints._upsert_test_coverage")
    def test_create_success_returns_201(self, mock_upsert, mock_embed, client, mock_db):
        row = _mock_row()
        mock_upsert.return_value = (row, True)
        mock_embed.return_value = [0.1] * 768
        mock_db.refresh = MagicMock()

        r = client.post("/api/test-coverage", json=VALID_PAYLOAD)

        assert r.status_code == 201
        body = r.json()
        assert body["title"] == "Test coverage event"
        assert body["category"] == "api"
        assert body["project_name"] == "test-project"

    @patch("test_coverage_endpoints.get_embedding", new_callable=AsyncMock, create=True)
    @patch("test_coverage_endpoints._upsert_test_coverage")
    def test_create_upsert_existing_returns_200(self, mock_upsert, mock_embed, client, mock_db):
        row = _mock_row()
        mock_upsert.return_value = (row, False)
        mock_embed.return_value = [0.1] * 768
        mock_db.refresh = MagicMock()

        r = client.post("/api/test-coverage", json=VALID_PAYLOAD)

        assert r.status_code == 200
        body = r.json()
        assert body["title"] == "Test coverage event"


class TestTestCoverageList:
    def test_list_empty_returns_200(self, client, mock_db):
        mock_db.query.return_value.count.return_value = 0
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        r = client.get("/api/test-coverage")

        assert r.status_code == 200
        body = r.json()
        assert body["test_coverage_events"] == []
        assert body["total"] == 0

    def test_list_with_project_filter(self, client, mock_db):
        rows = [_mock_row(project_name="proj-a")]
        filtered_q = mock_db.query.return_value.filter.return_value
        filtered_q.count.return_value = 1
        filtered_q.order_by.return_value.offset.return_value.limit.return_value.all.return_value = rows

        r = client.get("/api/test-coverage?project_name=proj-a")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["test_coverage_events"][0]["project_name"] == "proj-a"

    def test_list_with_category_filter(self, client, mock_db):
        rows = [_mock_row(category="e2e")]
        filtered_q = mock_db.query.return_value.filter.return_value
        filtered_q.count.return_value = 1
        filtered_q.order_by.return_value.offset.return_value.limit.return_value.all.return_value = rows

        r = client.get("/api/test-coverage?category=e2e")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["test_coverage_events"][0]["category"] == "e2e"

    def test_list_pagination(self, client, mock_db):
        rows = [_mock_row(title=f"Event {i}") for i in range(5)]
        mock_db.query.return_value.count.return_value = 50
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = rows

        r = client.get("/api/test-coverage?limit=5&offset=10")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 50
        assert len(body["test_coverage_events"]) == 5


class TestTestCoverageSearch:
    def test_search_empty_query_returns_422(self, client):
        r = client.post("/api/test-coverage/search", json={"query": ""})
        assert r.status_code == 422

    def test_search_returns_results(self, client, mock_db):
        rows = [_mock_row(title="Coverage for auth tests")]
        search_q = mock_db.query.return_value.filter.return_value
        search_q.count.return_value = 1
        search_q.order_by.return_value.limit.return_value.all.return_value = rows

        r = client.post("/api/test-coverage/search", json={"query": "auth tests"})

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["test_coverage_events"][0]["title"] == "Coverage for auth tests"


class TestTestCoverageDelete:
    def test_delete_success_returns_204(self, client, mock_db):
        row = _mock_row()
        mock_db.query.return_value.filter.return_value.first.return_value = row

        r = client.delete(f"/api/test-coverage/{row.id}")

        assert r.status_code == 204

    def test_delete_not_found_returns_404(self, client, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        r = client.delete(f"/api/test-coverage/{uuid.uuid4()}")

        assert r.status_code == 404


class TestTestCoverageIntegration:
    """Real-DB integration tests for test-coverage endpoints.

    Skipped if the registry DB is not reachable. Seeds rows with a pytest-tc-
    prefixed title so they never collide with production data, and cleans up
    in try/finally so aborted runs leave no orphans.
    """

    @pytest.fixture
    def real_client(self):
        import sys, os
        sys.path.insert(0, os.path.dirname(__file__))
        try:
            from database import SessionLocal, get_db
            from api import app
        except Exception as e:
            pytest.skip(f"registry api import failed: {e}")
        try:
            probe = SessionLocal()
            probe.execute(__import__("sqlalchemy").text("SELECT 1"))
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
        from models import TestCoverage
        db = SessionLocal()
        try:
            db.query(TestCoverage).filter(
                TestCoverage.title.in_(titles)
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

    def test_roundtrip_create_list_search_delete(self, real_client):
        client, SessionLocal = real_client
        title = f"pytest-tc-{uuid.uuid4().hex[:8]}"
        payload = {
            **VALID_PAYLOAD,
            "title": title,
            "project_name": "pytest-integration",
        }
        try:
            # Create
            r_create = client.post("/api/test-coverage", json=payload)
            assert r_create.status_code == 201, r_create.text
            created_id = r_create.json()["id"]
            assert r_create.json()["title"] == title
            assert r_create.json()["delta"] == 13

            # List — filter by project
            r_list = client.get("/api/test-coverage?project_name=pytest-integration")
            assert r_list.status_code == 200, r_list.text
            found_ids = {e["id"] for e in r_list.json()["test_coverage_events"]}
            assert created_id in found_ids

            # Search
            r_search = client.post(
                "/api/test-coverage/search",
                json={"query": title, "project_name": "pytest-integration"},
            )
            assert r_search.status_code == 200, r_search.text
            search_ids = {e["id"] for e in r_search.json()["test_coverage_events"]}
            assert created_id in search_ids

            # Delete
            r_delete = client.delete(f"/api/test-coverage/{created_id}")
            assert r_delete.status_code == 204

            # Confirm gone
            r_after = client.get("/api/test-coverage?project_name=pytest-integration")
            remaining_ids = {e["id"] for e in r_after.json()["test_coverage_events"]}
            assert created_id not in remaining_ids
        finally:
            self._cleanup(SessionLocal, title)
