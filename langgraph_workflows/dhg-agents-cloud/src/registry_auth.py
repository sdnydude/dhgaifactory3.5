"""Registry write-auth headers for cloud agents.

The registry's WriteAuthMiddleware covers /api/v1 and /api/cme mutating
routes (P2 T13, 2026-08-21). Agents send the bearer token from
REGISTRY_WRITE_TOKEN env — set in the container/runtime env, no file
fallback here (cloud containers have no ~/.claude). Empty = no header,
matching the middleware's off/log modes.
"""
import os


def registry_write_headers() -> dict:
    token = os.environ.get("REGISTRY_WRITE_TOKEN", "")
    return {"Authorization": f"Bearer {token}"} if token else {}
