"""
Capture-write bearer-token middleware (item 14).

Machine-to-machine auth for the KB/capture write paths — distinct from the
human-facing Cloudflare Access layer in auth.py. Mutating methods (POST/PUT/
PATCH/DELETE) on the capture route families require
`Authorization: Bearer <REGISTRY_WRITE_TOKEN>`. Reads stay LAN-open, and
POST <prefix>/search routes are exempt (read-via-POST — ship.md, inject
hooks, and briefings depend on them).

Modes (REGISTRY_WRITE_AUTH_MODE):
  off      — middleware inert (default; safe first deploy)
  log      — validate and log misses, but allow (48h observation window)
  enforce  — 401 on missing/invalid token

Fail-closed detail: in enforce mode with REGISTRY_WRITE_TOKEN unset, all
covered writes 401 (loudly logged) rather than silently passing.

Client side: dhg-memreg's memreg_capture.py sends the token from
REGISTRY_WRITE_TOKEN env or ~/.claude/secrets/registry-write-token.
"""
import hmac
import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("dhg.write_auth")

WRITE_PREFIXES = (
    "/api/insights",
    "/api/corrections",
    "/api/decision-logs",
    "/api/deferred-items",
    "/api/bug-fixes",
    "/api/ship-sessions",
    "/api/test-coverage",
    "/api/agent-sessions",
    "/api/kb",
)

# Read-via-POST endpoints stay open: every covered family exposes
# POST <prefix>/search (used by ship.md, the inject hooks, and briefings).
EXEMPT_SUFFIXES = ("/search",)

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _covered(method: str, path: str) -> bool:
    if method not in MUTATING_METHODS:
        return False
    path = path.rstrip("/") or "/"
    if not any(path == p or path.startswith(p + "/") for p in WRITE_PREFIXES):
        return False
    return not path.endswith(EXEMPT_SUFFIXES)


def _token_valid(request) -> bool:
    expected = os.getenv("REGISTRY_WRITE_TOKEN", "")
    if not expected:
        return False
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    supplied = auth[len("Bearer "):].strip()
    return hmac.compare_digest(supplied, expected)


class WriteAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        mode = os.getenv("REGISTRY_WRITE_AUTH_MODE", "off").lower()
        if mode == "off" or not _covered(request.method, request.url.path):
            return await call_next(request)

        if _token_valid(request):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        if mode == "log":
            logger.warning(
                "write-auth MISS (log-only, allowed): %s %s from %s",
                request.method, request.url.path, client,
            )
            return await call_next(request)

        if not os.getenv("REGISTRY_WRITE_TOKEN", ""):
            logger.error(
                "write-auth MISCONFIG: enforce mode with no REGISTRY_WRITE_TOKEN set "
                "— failing closed for %s %s", request.method, request.url.path,
            )
        else:
            logger.warning(
                "write-auth DENY: %s %s from %s",
                request.method, request.url.path, client,
            )
        return JSONResponse(
            status_code=401,
            content={"detail": "write authentication required"},
        )
