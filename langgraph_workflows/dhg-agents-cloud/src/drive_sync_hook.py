"""Enqueue drive_sync jobs at pipeline milestones via the registry webhook.

LangGraph Cloud can't reach registry-db directly, so this hook posts to the
public Cloudflare-tunneled endpoint `/api/cme/webhook/drive-sync-enqueue`
authenticated with a shared `X-Webhook-Secret` header. The registry endpoint
dedupes inflight jobs; this helper is fire-and-forget (exceptions logged,
never raised) so pipeline state transitions never fail because Drive sync is
unreachable.

Set `DRIVE_SYNC_DISABLED=1` in the orchestrator env to no-op the hook
(used by local dev and in tests where we don't want to contact the registry).
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)


async def enqueue_drive_sync(project_id: str, milestone: str) -> bool:
    """Post a drive_sync enqueue request to the registry webhook.

    Returns True on a 2xx response, False on any error, missing config, or
    disabled flag. Never raises.
    """
    if os.getenv("DRIVE_SYNC_DISABLED") == "1":
        return False
    if not project_id:
        logger.warning("drive_sync hook: missing project_id; skipping")
        return False

    base_url = os.getenv("AI_FACTORY_REGISTRY_URL")
    secret = os.getenv("REGISTRY_WEBHOOK_SECRET")
    if not base_url or not secret:
        logger.warning(
            "drive_sync hook: AI_FACTORY_REGISTRY_URL or REGISTRY_WEBHOOK_SECRET "
            "unset; skipping enqueue for project=%s",
            project_id,
        )
        return False

    url = f"{base_url.rstrip('/')}/api/cme/webhook/drive-sync-enqueue"
    body = {"project_id": project_id, "milestone": milestone}
    headers = {"X-Webhook-Secret": secret}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code >= 400:
                logger.warning(
                    "drive_sync enqueue returned %s for project=%s: %s",
                    resp.status_code, project_id, resp.text[:200],
                )
                return False
            logger.info(
                "drive_sync enqueued project=%s milestone=%s status=%s",
                project_id, milestone, resp.status_code,
            )
            return True
    except Exception as e:
        logger.warning(
            "drive_sync enqueue error project=%s milestone=%s: %s",
            project_id, milestone, e,
        )
        return False
