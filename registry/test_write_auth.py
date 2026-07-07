"""Tests for the capture-write bearer-token middleware (item 14).

Scope: mutating methods on the 9 KB/capture route families require
Authorization: Bearer <REGISTRY_WRITE_TOKEN>. Reads stay open.
/api/kb/search is a read-via-POST and stays open. Modes: off | log | enforce.

Run with: pytest registry/test_write_auth.py -v
"""

import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TOKEN = "test-token-abc123"


def load_middleware():
    """Import inside the test path so a missing module fails the test, not collection."""
    try:
        from write_auth import WriteAuthMiddleware
    except ImportError as exc:
        pytest.fail(f"write_auth module not importable: {exc}")
    return WriteAuthMiddleware


def make_client() -> TestClient:
    """Tiny app with the middleware and dummy routes — isolates middleware logic."""
    app = FastAPI()
    app.add_middleware(load_middleware())

    @app.post("/api/insights")
    @app.get("/api/insights")
    @app.post("/api/kb/search")
    @app.post("/api/kb/ingest")
    @app.post("/api/deferred-items/search")
    @app.post("/api/deferred-items/abc123/surfaced")
    @app.post("/api/cme/projects")
    def ok():
        return {"ok": True}

    return TestClient(app)


def test_enforce_mode_rejects_unauthenticated_write(monkeypatch):
    monkeypatch.setenv("REGISTRY_WRITE_AUTH_MODE", "enforce")
    monkeypatch.setenv("REGISTRY_WRITE_TOKEN", TOKEN)
    client = make_client()
    resp = client.post("/api/insights", json={})
    assert resp.status_code == 401


def test_off_mode_is_inert(monkeypatch):
    monkeypatch.setenv("REGISTRY_WRITE_AUTH_MODE", "off")
    monkeypatch.delenv("REGISTRY_WRITE_TOKEN", raising=False)
    client = make_client()
    assert client.post("/api/insights", json={}).status_code == 200


def test_default_mode_is_off(monkeypatch):
    monkeypatch.delenv("REGISTRY_WRITE_AUTH_MODE", raising=False)
    monkeypatch.delenv("REGISTRY_WRITE_TOKEN", raising=False)
    client = make_client()
    assert client.post("/api/insights", json={}).status_code == 200


def test_enforce_mode_rejects_wrong_token(monkeypatch):
    monkeypatch.setenv("REGISTRY_WRITE_AUTH_MODE", "enforce")
    monkeypatch.setenv("REGISTRY_WRITE_TOKEN", TOKEN)
    client = make_client()
    resp = client.post("/api/insights", json={}, headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401


def test_enforce_mode_accepts_valid_token(monkeypatch):
    monkeypatch.setenv("REGISTRY_WRITE_AUTH_MODE", "enforce")
    monkeypatch.setenv("REGISTRY_WRITE_TOKEN", TOKEN)
    client = make_client()
    resp = client.post("/api/insights", json={}, headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status_code == 200


def test_enforce_mode_leaves_reads_open(monkeypatch):
    monkeypatch.setenv("REGISTRY_WRITE_AUTH_MODE", "enforce")
    monkeypatch.setenv("REGISTRY_WRITE_TOKEN", TOKEN)
    client = make_client()
    assert client.get("/api/insights").status_code == 200


def test_enforce_mode_exempts_kb_search(monkeypatch):
    monkeypatch.setenv("REGISTRY_WRITE_AUTH_MODE", "enforce")
    monkeypatch.setenv("REGISTRY_WRITE_TOKEN", TOKEN)
    client = make_client()
    assert client.post("/api/kb/search", json={}).status_code == 200


def test_enforce_mode_covers_kb_ingest(monkeypatch):
    monkeypatch.setenv("REGISTRY_WRITE_AUTH_MODE", "enforce")
    monkeypatch.setenv("REGISTRY_WRITE_TOKEN", TOKEN)
    client = make_client()
    assert client.post("/api/kb/ingest", json={}).status_code == 401


def test_enforce_mode_leaves_uncovered_routes_open(monkeypatch):
    monkeypatch.setenv("REGISTRY_WRITE_AUTH_MODE", "enforce")
    monkeypatch.setenv("REGISTRY_WRITE_TOKEN", TOKEN)
    client = make_client()
    assert client.post("/api/cme/projects", json={}).status_code == 200


def test_log_mode_allows_but_logs(monkeypatch, caplog):
    monkeypatch.setenv("REGISTRY_WRITE_AUTH_MODE", "log")
    monkeypatch.setenv("REGISTRY_WRITE_TOKEN", TOKEN)
    client = make_client()
    import logging as _logging
    with caplog.at_level(_logging.WARNING, logger="dhg.write_auth"):
        resp = client.post("/api/insights", json={})
    assert resp.status_code == 200
    assert any("write-auth MISS" in r.message for r in caplog.records)


def test_enforce_mode_fails_closed_without_configured_token(monkeypatch):
    monkeypatch.setenv("REGISTRY_WRITE_AUTH_MODE", "enforce")
    monkeypatch.delenv("REGISTRY_WRITE_TOKEN", raising=False)
    client = make_client()
    resp = client.post("/api/insights", json={}, headers={"Authorization": "Bearer anything"})
    assert resp.status_code == 401


def test_middleware_is_wired_into_registry_app(monkeypatch):
    monkeypatch.setenv("SECURITY_DEV_MODE", "true")
    # Engine creation is lazy — a dummy URL lets api import without a live DB.
    monkeypatch.setenv("DATABASE_URL", "postgresql://dhg:x@127.0.0.1:59999/dhg_registry")
    from write_auth import WriteAuthMiddleware
    import api
    stack = [m.cls for m in api.app.user_middleware]
    assert WriteAuthMiddleware in stack


def test_enforce_mode_exempts_search_posts_on_all_families(monkeypatch):
    """POST /api/<family>/search is a read (ship.md + hooks depend on it) — stays open."""
    monkeypatch.setenv("REGISTRY_WRITE_AUTH_MODE", "enforce")
    monkeypatch.setenv("REGISTRY_WRITE_TOKEN", TOKEN)
    client = make_client()
    assert client.post("/api/deferred-items/search", json={}).status_code == 200


def test_enforce_mode_still_covers_nested_mutations(monkeypatch):
    """Nested mutating routes like /{id}/surfaced stay covered."""
    monkeypatch.setenv("REGISTRY_WRITE_AUTH_MODE", "enforce")
    monkeypatch.setenv("REGISTRY_WRITE_TOKEN", TOKEN)
    client = make_client()
    assert client.post("/api/deferred-items/abc123/surfaced", json={}).status_code == 401
