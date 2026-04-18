from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from medkb.config import Settings

router = APIRouter()

_settings = Settings()


@router.get("/v1/healthz")
async def healthz() -> dict:
    return {"status": "ok", "service": "dhg-medkb"}


@router.get("/v1/readyz")
async def readyz() -> dict:
    checks = {}

    try:
        from medkb.db import get_engine
        from sqlalchemy import text
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["db"] = "up"
    except Exception as e:
        checks["db"] = f"down: {e}"

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(_settings.medkb_redis_url, socket_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "up"
    except Exception as e:
        checks["redis"] = f"down: {e}"

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{_settings.ollama_url}/api/tags", timeout=5)
            resp.raise_for_status()
        checks["ollama"] = "up"
    except Exception as e:
        checks["ollama"] = f"down: {e}"

    all_up = all(v == "up" for v in checks.values())
    status = "ok" if all_up else "degraded"
    return {"status": status, "checks": checks}


@router.get("/metrics")
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
