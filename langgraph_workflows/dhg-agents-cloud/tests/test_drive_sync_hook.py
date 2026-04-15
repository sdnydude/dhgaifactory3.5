"""Unit tests for drive_sync_hook.enqueue_drive_sync."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_enqueue_posts_to_webhook_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_FACTORY_REGISTRY_URL", "https://registry-webhook.example.com")
    monkeypatch.setenv("REGISTRY_WEBHOOK_SECRET", "s" * 64)
    monkeypatch.delenv("DRIVE_SYNC_DISABLED", raising=False)

    import drive_sync_hook
    import importlib
    importlib.reload(drive_sync_hook)

    fake_response = MagicMock()
    fake_response.status_code = 202
    fake_response.json.return_value = {"job_id": "job-1", "status": "queued"}

    fake_client = AsyncMock()
    fake_client.__aenter__.return_value = fake_client
    fake_client.__aexit__.return_value = False
    fake_client.post = AsyncMock(return_value=fake_response)

    with patch.object(drive_sync_hook.httpx, "AsyncClient", return_value=fake_client):
        result = await drive_sync_hook.enqueue_drive_sync(
            "p-123", milestone="review_ready:grant"
        )

    assert result is True
    fake_client.post.assert_awaited_once()
    call = fake_client.post.await_args
    assert call.args[0] == "https://registry-webhook.example.com/api/cme/webhook/drive-sync-enqueue"
    assert call.kwargs["json"] == {
        "project_id": "p-123",
        "milestone": "review_ready:grant",
    }
    assert call.kwargs["headers"]["X-Webhook-Secret"] == "s" * 64


@pytest.mark.asyncio
async def test_enqueue_returns_false_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRIVE_SYNC_DISABLED", "1")
    import drive_sync_hook
    import importlib
    importlib.reload(drive_sync_hook)
    result = await drive_sync_hook.enqueue_drive_sync("p-123", milestone="complete")
    assert result is False


@pytest.mark.asyncio
async def test_enqueue_swallows_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DRIVE_SYNC_DISABLED", raising=False)
    monkeypatch.setenv("AI_FACTORY_REGISTRY_URL", "https://registry-webhook.example.com")
    monkeypatch.setenv("REGISTRY_WEBHOOK_SECRET", "s" * 64)

    import drive_sync_hook
    import importlib
    importlib.reload(drive_sync_hook)

    fake_client = AsyncMock()
    fake_client.__aenter__.return_value = fake_client
    fake_client.__aexit__.return_value = False
    fake_client.post = AsyncMock(side_effect=RuntimeError("network down"))

    with patch.object(drive_sync_hook.httpx, "AsyncClient", return_value=fake_client):
        result = await drive_sync_hook.enqueue_drive_sync("p-123", milestone="complete")

    assert result is False


@pytest.mark.asyncio
async def test_enqueue_no_project_id_returns_false() -> None:
    import drive_sync_hook
    import importlib
    importlib.reload(drive_sync_hook)
    assert await drive_sync_hook.enqueue_drive_sync("", milestone="complete") is False
