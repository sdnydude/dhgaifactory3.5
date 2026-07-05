"""Tests for the feedback-loop API at /api/feedback-loop.

Run with: pytest registry/test_feedback_loop.py -v

Routes tested:
  GET /api/feedback-loop/health   pipeline health + per-type counts (7d)
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestFeedbackLoopHealth:
    """Real-DB integration tests for feedback_loop_health endpoint.

    Skipped if the registry DB is not reachable.
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
            yield c
        app.dependency_overrides.clear()

    def test_health_returns_200_with_schema(self, real_client):
        r = real_client.get("/api/feedback-loop/health")
        assert r.status_code == 200
        body = r.json()

        assert body["status"] in ("healthy", "degraded", "dead")
        assert isinstance(body["healthy_types"], int)
        assert isinstance(body["total_types"], int)
        assert body["total_types"] == 7

        assert isinstance(body["types"], list)
        assert len(body["types"]) == 7

        expected_types = {
            "corrections", "bug_fixes", "insights", "decision_logs",
            "deferred_items", "test_coverage", "ship_sessions",
        }
        actual_types = {t["type"] for t in body["types"]}
        assert actual_types == expected_types

    def test_health_type_stat_shape(self, real_client):
        r = real_client.get("/api/feedback-loop/health")
        assert r.status_code == 200

        for ts in r.json()["types"]:
            assert "type" in ts
            assert isinstance(ts["count_7d"], int)
            assert isinstance(ts["count_total"], int)
            assert ts["count_7d"] >= 0
            assert ts["count_total"] >= ts["count_7d"]
            assert "last_capture" in ts

    def test_health_with_project_filter(self, real_client):
        r = real_client.get(
            "/api/feedback-loop/health?project_name=nonexistent-project-xyz"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "dead"
        assert body["healthy_types"] == 0
        for ts in body["types"]:
            assert ts["count_7d"] == 0
            assert ts["count_total"] == 0

    def test_health_status_consistency(self, real_client):
        r = real_client.get("/api/feedback-loop/health")
        assert r.status_code == 200
        body = r.json()

        healthy_count = sum(1 for t in body["types"] if t["count_7d"] > 0)
        assert body["healthy_types"] == healthy_count

        if healthy_count == body["total_types"]:
            assert body["status"] == "healthy"
        elif healthy_count == 0:
            assert body["status"] == "dead"
        else:
            assert body["status"] == "degraded"
