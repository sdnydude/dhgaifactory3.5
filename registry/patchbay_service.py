"""Patchbay status service — TCP liveness probes for the docs-hub launchpad.

The homepage LEDs ask "is this service reachable right now?". We answer with
plain async TCP connects against the known port map, cached briefly so a page
load (or several) doesn't storm every port on every request.
"""
import asyncio
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Host the registry probes against. Services publish on the LAN IP.
PROBE_HOST = os.getenv("PATCHBAY_PROBE_HOST", "10.0.0.251")
PROBE_TIMEOUT = 1.0
CACHE_TTL = 10.0

# service key → port. Keys are shared with the frontend's services.ts.
SERVICES: dict[str, int] = {
    "frontend": 3000,
    "open-webui": 3080,
    "portage": 3002,
    "promptmaster": 8020,
    "grafana": 3001,
    "prometheus": 9090,
    "alertmanager": 9093,
    "cadvisor": 8080,
    "pgadmin": 5050,
    "minio": 9001,
    "qdrant": 6333,
    "terminal": 8022,
    "medkb": 8015,
    "agui-poc": 8104,
    "langgraph-dev": 2026,
    "logo-maker": 8012,
    "portage-dev": 3003,
    "registry": 8011,
    "vs-engine": 8013,
}

_cache: dict[str, Optional[object]] = {"data": None, "at": 0.0}


def _now() -> float:
    """Monotonic clock wrapper — patch point for tests (avoids clobbering the
    global time.monotonic that asyncio's event loop relies on)."""
    return time.monotonic()


async def _probe(host: str, port: int) -> bool:
    """True if a TCP connection to host:port opens within the timeout."""
    try:
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=PROBE_TIMEOUT)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


async def probe_services(services: dict[str, int]) -> dict[str, str]:
    """Probe all services concurrently; return {key: "up"|"down"}."""
    keys = list(services)
    results = await asyncio.gather(*(_probe(PROBE_HOST, services[k]) for k in keys))
    return {k: ("up" if ok else "down") for k, ok in zip(keys, results)}


async def get_status() -> dict:
    """Return cached status when fresh, else re-probe. {services, checked_at}."""
    now = _now()
    cached = _cache["data"]
    if cached is not None and (now - float(_cache["at"])) < CACHE_TTL:
        return cached

    services = await probe_services(SERVICES)
    result = {"services": services, "checked_at": int(time.time())}
    _cache["data"] = result
    _cache["at"] = now
    return result
