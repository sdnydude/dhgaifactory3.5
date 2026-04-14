from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_render_sync_returns_pdf() -> None:
    fake_pdf = b"%PDF-1.7\nfake"
    with patch("main.render_pdf", new=AsyncMock(return_value=fake_pdf)):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/render-sync",
                json={
                    "url": "http://frontend:3000/print/cme/document/abc?t=xxx",
                    "wait_for_selectors": ["[data-print-ready=true]"],
                    "extra_http_headers": {},
                },
            )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == fake_pdf


@pytest.mark.asyncio
async def test_render_sync_rejects_non_http_url() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/render-sync",
            json={"url": "file:///etc/passwd", "wait_for_selectors": []},
        )
    assert resp.status_code == 400
