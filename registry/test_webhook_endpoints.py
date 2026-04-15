"""Tests for /api/cme/webhook/drive-sync-enqueue."""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient

from api import app
from database import get_db
from models import DownloadJob


SECRET = "a" * 64


@pytest.fixture
def webhook_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("REGISTRY_WEBHOOK_SECRET", SECRET)

    db = MagicMock()
    project = MagicMock()
    project.id = "11111111-1111-1111-1111-111111111111"
    project.pipeline_thread_id = "thread-xyz"
    db.query.return_value.filter.return_value.first.return_value = project

    added: list[DownloadJob] = []

    def fake_add(obj):
        added.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = "22222222-2222-2222-2222-222222222222"

    def fake_refresh(obj):
        if getattr(obj, "status", None) is None:
            obj.status = "pending"
        from datetime import datetime, timezone
        obj.created_at = datetime.now(timezone.utc)

    db.add.side_effect = fake_add
    db.refresh.side_effect = fake_refresh

    # Default: no existing drive_sync job (dedup query returns None).
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c, db, added, project
    app.dependency_overrides.clear()


def test_missing_secret_returns_401(webhook_client) -> None:
    c, *_ = webhook_client
    r = c.post(
        "/api/cme/webhook/drive-sync-enqueue",
        json={"project_id": "11111111-1111-1111-1111-111111111111", "milestone": "needs_complete"},
    )
    assert r.status_code == 401


def test_bad_secret_returns_401(webhook_client) -> None:
    c, *_ = webhook_client
    r = c.post(
        "/api/cme/webhook/drive-sync-enqueue",
        headers={"X-Webhook-Secret": "wrong"},
        json={"project_id": "11111111-1111-1111-1111-111111111111", "milestone": "needs_complete"},
    )
    assert r.status_code == 401


def test_valid_call_enqueues_drive_sync_job(webhook_client) -> None:
    c, db, added, project = webhook_client
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    r = c.post(
        "/api/cme/webhook/drive-sync-enqueue",
        headers={"X-Webhook-Secret": SECRET},
        json={"project_id": str(project.id), "milestone": "grant_complete"},
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "queued"
    assert "job_id" in body
    assert len(added) == 1
    job = added[0]
    assert job.scope == "drive_sync"
    assert job.status == "pending"
    assert str(job.project_id) == str(project.id)
    assert job.thread_id == "thread-xyz"


def test_duplicate_inflight_job_is_deduped(webhook_client) -> None:
    c, db, added, project = webhook_client
    existing = MagicMock()
    existing.id = "33333333-3333-3333-3333-333333333333"
    existing.status = "pending"
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = existing

    r = c.post(
        "/api/cme/webhook/drive-sync-enqueue",
        headers={"X-Webhook-Secret": SECRET},
        json={"project_id": str(project.id), "milestone": "grant_complete"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["job_id"] == str(existing.id)
    assert body["status"] == "pending"
    assert len(added) == 0


def test_missing_project_id_returns_422(webhook_client) -> None:
    c, *_ = webhook_client
    r = c.post(
        "/api/cme/webhook/drive-sync-enqueue",
        headers={"X-Webhook-Secret": SECRET},
        json={"milestone": "needs_complete"},
    )
    assert r.status_code == 422


def test_project_not_found_returns_404(webhook_client) -> None:
    c, db, *_ = webhook_client
    db.query.return_value.filter.return_value.first.return_value = None
    r = c.post(
        "/api/cme/webhook/drive-sync-enqueue",
        headers={"X-Webhook-Secret": SECRET},
        json={"project_id": "99999999-9999-9999-9999-999999999999", "milestone": "needs_complete"},
    )
    assert r.status_code == 404
