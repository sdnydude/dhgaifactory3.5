from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Header, HTTPException, Response

from export_schemas import DocumentPrintPayload
from export_service import (
    build_print_url,
    load_document_for_thread,
    render_via_renderer,
)
from export_signing import (
    PrintTokenExpired,
    PrintTokenInvalid,
    verify_print_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cme/export", tags=["cme-export"])


def _sanitize_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in s)[:80]


@router.get("/internal/document/{thread_id}", response_model=DocumentPrintPayload)
async def internal_document(
    thread_id: str,
    x_print_token: str | None = Header(default=None, alias="X-Print-Token"),
) -> DocumentPrintPayload:
    """Called by the Next.js print route to hydrate the page.

    Guarded by the same HMAC token the print URL was signed with, so the
    endpoint is never reachable from user traffic.
    """
    secret = os.environ.get("EXPORT_SIGNING_SECRET")
    if not secret or not x_print_token:
        raise HTTPException(status_code=401, detail="missing token")
    try:
        payload = verify_print_token(x_print_token, secret=secret)
    except PrintTokenExpired:
        raise HTTPException(status_code=401, detail="token expired")
    except PrintTokenInvalid:
        raise HTTPException(status_code=401, detail="invalid token")
    if payload.subject != "cme_document" or payload.resource_id != thread_id:
        raise HTTPException(status_code=403, detail="scope mismatch")

    data = await load_document_for_thread(thread_id)
    if not data:
        raise HTTPException(status_code=404, detail="document not found")
    return DocumentPrintPayload(**data)


@router.get("/document/{thread_id}")
async def sync_download_document(thread_id: str) -> Response:
    """User-facing sync download. Auth handled by Cloudflare Access layer."""
    data = await load_document_for_thread(thread_id)
    if not data:
        raise HTTPException(status_code=404, detail="document not found")
    url = build_print_url(
        subject="cme_document",
        resource_id=thread_id,
        path_prefix="/print/cme/document/",
    )
    try:
        pdf = await render_via_renderer(url)
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
        logger.warning("pdf renderer unreachable: %s", e)
        raise HTTPException(status_code=502, detail="pdf renderer unavailable")
    except httpx.HTTPStatusError as e:
        logger.warning("pdf renderer returned %s: %s", e.response.status_code, e.response.text[:200])
        raise HTTPException(status_code=502, detail="pdf render failed")
    safe_title = _sanitize_filename(data["title"])
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{safe_title}_{stamp}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "content-disposition": f'attachment; filename="{filename}"',
            "cache-control": "no-store",
        },
    )
