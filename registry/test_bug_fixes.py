"""Tests for the bug_fixes API endpoints at /api/bug-fixes.

Run with:
    pytest registry/test_bug_fixes.py -v
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import BugFix


VALID_PAYLOAD = {
    "tldr": "Test bug fix for memreg tests",
    "symptom": "Widget fails to render when data is null",
    "root_cause": "Missing null check in render function",
    "fix_applied": "Added null guard before accessing data.items",
    "files_affected": ["src/components/widget.tsx"],
    "severity": "medium",
    "category": "frontend",
    "project_name": "test-project",
    "tags": ["test", "memreg"],
}


def _mock_bug_fix_row(**overrides):
    """Build a MagicMock that looks like a BugFix ORM row."""
    defaults = dict(
        id=uuid.uuid4(),
        tldr="Test bug fix",
        symptom="Test symptom",
        root_cause="Test root cause",
        fix_applied="Test fix",
        files_affected=["test.py"],
        severity="medium",
        category="frontend",
        project_name="test-project",
        source_file=None,
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


class TestBugFixCreate:
    def test_create_empty_body_returns_422(self, client):
        r = client.post("/api/bug-fixes", json={})
        assert r.status_code == 422

    def test_create_invalid_severity_returns_422(self, client):
        payload = {**VALID_PAYLOAD, "severity": "apocalyptic"}
        r = client.post("/api/bug-fixes", json=payload)
        assert r.status_code == 422

    def test_create_invalid_category_returns_422(self, client):
        payload = {**VALID_PAYLOAD, "category": "banana"}
        r = client.post("/api/bug-fixes", json=payload)
        assert r.status_code == 422

    @patch("bug_fixes_endpoints.svc")
    def test_create_success_returns_201(self, mock_svc, client):
        row = _mock_bug_fix_row()
        mock_svc.upsert_bug_fix.return_value = (row, True)

        r = client.post("/api/bug-fixes", json=VALID_PAYLOAD)

        assert r.status_code == 201
        body = r.json()
        assert body["tldr"] == "Test bug fix"
        assert body["severity"] == "medium"
        assert body["category"] == "frontend"
        mock_svc.upsert_bug_fix.assert_called_once()

    @patch("bug_fixes_endpoints.svc")
    def test_create_upsert_existing_returns_200(self, mock_svc, client):
        row = _mock_bug_fix_row()
        mock_svc.upsert_bug_fix.return_value = (row, False)

        r = client.post("/api/bug-fixes", json=VALID_PAYLOAD)

        assert r.status_code == 200
        body = r.json()
        assert body["tldr"] == "Test bug fix"


class TestBugFixList:
    @patch("bug_fixes_endpoints.svc")
    def test_list_empty_returns_200(self, mock_svc, client):
        mock_svc.list_bug_fixes.return_value = ([], 0)

        r = client.get("/api/bug-fixes")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["bug_fixes"] == []

    @patch("bug_fixes_endpoints.svc")
    def test_list_with_project_filter(self, mock_svc, client):
        row = _mock_bug_fix_row(project_name="filtered-project")
        mock_svc.list_bug_fixes.return_value = ([row], 1)

        r = client.get("/api/bug-fixes?project_name=filtered-project")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["bug_fixes"][0]["project_name"] == "filtered-project"

    @patch("bug_fixes_endpoints.svc")
    def test_list_with_severity_filter(self, mock_svc, client):
        row = _mock_bug_fix_row(severity="critical")
        mock_svc.list_bug_fixes.return_value = ([row], 1)

        r = client.get("/api/bug-fixes?severity=critical")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["bug_fixes"][0]["severity"] == "critical"

    @patch("bug_fixes_endpoints.svc")
    def test_list_pagination(self, mock_svc, client):
        rows = [_mock_bug_fix_row(tldr=f"Bug {i}") for i in range(5)]
        mock_svc.list_bug_fixes.return_value = (rows, 50)

        r = client.get("/api/bug-fixes?limit=5&offset=10")

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 50
        assert len(body["bug_fixes"]) == 5


class TestBugFixSearch:
    def test_search_empty_query_returns_422(self, client):
        r = client.post("/api/bug-fixes/search", json={"query": ""})
        assert r.status_code == 422

    @patch("bug_fixes_endpoints.svc")
    def test_search_returns_results(self, mock_svc, client):
        row = _mock_bug_fix_row(tldr="null pointer fix")
        mock_svc.search_bug_fixes.return_value = ([row], 1)

        r = client.post(
            "/api/bug-fixes/search",
            json={"query": "null pointer", "limit": 10},
        )

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["bug_fixes"][0]["tldr"] == "null pointer fix"


class TestBugFixDelete:
    @patch("bug_fixes_endpoints.svc")
    def test_delete_success_returns_204(self, mock_svc, client):
        row = _mock_bug_fix_row()
        mock_svc.delete_bug_fix.return_value = row

        r = client.delete(f"/api/bug-fixes/{row.id}")

        assert r.status_code == 204
        mock_svc.delete_bug_fix.assert_called_once()

    @patch("bug_fixes_endpoints.svc")
    def test_delete_not_found_returns_404(self, mock_svc, client):
        mock_svc.delete_bug_fix.return_value = None

        r = client.delete(f"/api/bug-fixes/{uuid.uuid4()}")

        assert r.status_code == 404


class TestBugFixIntegration:
    """Real-DB integration tests for bug_fixes endpoints.

    Skipped if the registry DB is not reachable. Seeds rows with a
    pytest-bf- prefixed project_name so they never collide with real data,
    and cleans up in try/finally so aborted runs leave no orphans.
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
            yield c
        app.dependency_overrides.clear()

    def _cleanup_by_project(self, project_name):
        """Remove all bug_fixes rows matching a project_name."""
        from database import SessionLocal
        db = SessionLocal()
        try:
            db.query(BugFix).filter(
                BugFix.project_name == project_name
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

    def test_roundtrip_create_list_search_delete(self, real_client):
        project = f"pytest-bf-{uuid.uuid4().hex[:8]}"
        payload = {
            **VALID_PAYLOAD,
            "project_name": project,
            "tldr": "Integration test null guard bug fix",
        }
        try:
            # Create
            r_create = real_client.post("/api/bug-fixes", json=payload)
            assert r_create.status_code == 201, r_create.text
            created = r_create.json()
            item_id = created["id"]
            assert created["project_name"] == project
            assert created["severity"] == "medium"
            assert created["category"] == "frontend"

            # Upsert same record returns 200
            r_upsert = real_client.post("/api/bug-fixes", json=payload)
            assert r_upsert.status_code == 200, r_upsert.text
            assert r_upsert.json()["id"] == item_id

            # List with project filter
            r_list = real_client.get(f"/api/bug-fixes?project_name={project}")
            assert r_list.status_code == 200, r_list.text
            list_body = r_list.json()
            assert list_body["total"] >= 1
            found_ids = {bf["id"] for bf in list_body["bug_fixes"]}
            assert item_id in found_ids

            # Search (FTS — may return 0 if tsvector trigger hasn't fired;
            # we still assert the endpoint returns 200 with valid structure)
            r_search = real_client.post(
                "/api/bug-fixes/search",
                json={"query": "null guard", "project_name": project},
            )
            assert r_search.status_code == 200, r_search.text
            assert "bug_fixes" in r_search.json()
            assert "total" in r_search.json()

            # Delete
            r_delete = real_client.delete(f"/api/bug-fixes/{item_id}")
            assert r_delete.status_code == 204, r_delete.text

            # Confirm deletion
            r_gone = real_client.delete(f"/api/bug-fixes/{item_id}")
            assert r_gone.status_code == 404
        finally:
            self._cleanup_by_project(project)
