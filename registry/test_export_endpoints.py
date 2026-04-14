"""Tests for /api/cme/export endpoints."""
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from httpx import ASGITransport, AsyncClient

from api import app


@pytest.mark.asyncio
async def test_internal_document_requires_print_token() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/cme/export/internal/document/thread-abc")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_document_sync_returns_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPORT_SIGNING_SECRET", "a" * 64)
    fake_pdf = b"%PDF-1.7\nfake"
    fake_doc = {
        "title": "Diabetes Management",
        "graph_label": "Grant Package",
        "review_round": 1,
        "document_text": "para 1\n\npara 2",
    }
    with (
        patch("export_endpoints.load_document_for_thread", new=AsyncMock(return_value=fake_doc)),
        patch("export_endpoints.render_via_renderer", new=AsyncMock(return_value=fake_pdf)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/cme/export/document/thread-abc")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.headers["content-disposition"].startswith("attachment;")
    assert resp.content == fake_pdf


@pytest.mark.asyncio
async def test_internal_document_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "a" * 64
    monkeypatch.setenv("EXPORT_SIGNING_SECRET", secret)
    import time as _time
    from export_signing import PrintTokenPayload, sign_print_token

    token = sign_print_token(
        PrintTokenPayload(
            subject="cme_document",
            resource_id="thread-happy",
            expires_at=int(_time.time()) + 60,
        ),
        secret=secret,
    )
    fake_doc = {
        "title": "Diabetes Management",
        "graph_label": "Grant Package",
        "review_round": 2,
        "document_text": "body",
    }
    with patch("export_endpoints.load_document_for_thread", new=AsyncMock(return_value=fake_doc)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(
                "/api/cme/export/internal/document/thread-happy",
                headers={"X-Print-Token": token},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Diabetes Management"
    assert body["review_round"] == 2


@pytest.mark.asyncio
async def test_internal_document_scope_mismatch_is_403(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "a" * 64
    monkeypatch.setenv("EXPORT_SIGNING_SECRET", secret)
    import time as _time
    from export_signing import PrintTokenPayload, sign_print_token

    token = sign_print_token(
        PrintTokenPayload(
            subject="cme_document",
            resource_id="thread-abc",
            expires_at=int(_time.time()) + 60,
        ),
        secret=secret,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(
            "/api/cme/export/internal/document/different-thread",
            headers={"X-Print-Token": token},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sync_download_404_when_document_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPORT_SIGNING_SECRET", "a" * 64)
    with patch("export_endpoints.load_document_for_thread", new=AsyncMock(return_value=None)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/cme/export/document/unknown-thread")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sync_download_renderer_error_is_502(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx as _httpx

    monkeypatch.setenv("EXPORT_SIGNING_SECRET", "a" * 64)
    fake_doc = {
        "title": "Doc",
        "graph_label": "Grant Package",
        "review_round": 0,
        "document_text": "body",
    }
    with (
        patch("export_endpoints.load_document_for_thread", new=AsyncMock(return_value=fake_doc)),
        patch(
            "export_endpoints.render_via_renderer",
            new=AsyncMock(side_effect=_httpx.ConnectError("unreachable")),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/cme/export/document/any-thread")
    assert resp.status_code == 502
