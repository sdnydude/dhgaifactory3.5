from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import quote

import httpx

from export_signing import PrintTokenPayload, sign_print_token


def _secret() -> str:
    secret = os.environ.get("EXPORT_SIGNING_SECRET")
    if not secret:
        raise RuntimeError("EXPORT_SIGNING_SECRET not set")
    return secret


def _frontend_internal_url() -> str:
    return os.environ.get("FRONTEND_INTERNAL_URL", "http://dhg-frontend:3000")


def _renderer_url() -> str:
    return os.environ.get("PDF_RENDERER_URL", "http://dhg-pdf-renderer:8014")


def build_print_url(
    subject: str,
    resource_id: str,
    path_prefix: str,
    ttl_seconds: int = 300,
) -> str:
    token = sign_print_token(
        PrintTokenPayload(
            subject=subject,
            resource_id=resource_id,
            expires_at=int(time.time()) + ttl_seconds,
        ),
        secret=_secret(),
    )
    return f"{_frontend_internal_url()}{path_prefix}{quote(resource_id)}?t={token}"


async def load_document_for_thread(thread_id: str) -> dict[str, Any] | None:
    """Fetch the data the print route needs for a single document.

    Thin wrapper so tests can monkey-patch. Real impl reads the latest
    CMEDocument row joined to CMEProject via pipeline_thread_id.
    """
    from cme_endpoints import fetch_latest_document_for_thread

    return await fetch_latest_document_for_thread(thread_id)


async def render_via_renderer(
    url: str,
    wait_for_selectors: list[str] | None = None,
) -> bytes:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{_renderer_url()}/render-sync",
            json={
                "url": url,
                "wait_for_selectors": wait_for_selectors or ["[data-print-ready=true]"],
            },
        )
        resp.raise_for_status()
        return resp.content
