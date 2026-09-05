"""Integration tests for the Claude AI data endpoints (registry/claude_endpoints.py).

Regression guard: the ``projects`` table created by alembic 002_claude_data was
missing from the live registry database, so GET /api/v1/projects returned 500
(``relation "projects" does not exist``). These tests run against the real
Postgres and are skipped when it is not reachable.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))


@pytest.fixture
def real_client():
    """TestClient bound to the real registry database."""
    import sqlalchemy

    try:
        from database import SessionLocal, get_db
        from api import app
    except Exception as e:  # pragma: no cover - environment guard
        pytest.skip(f"registry api import failed: {e}")

    try:
        probe = SessionLocal()
        probe.execute(sqlalchemy.text("SELECT 1"))
        probe.close()
    except Exception as e:  # pragma: no cover - environment guard
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


def test_list_projects_returns_empty_list(real_client):
    """GET /api/v1/projects must return 200 and a list, not a 500."""
    resp = real_client.get("/api/v1/projects")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []
