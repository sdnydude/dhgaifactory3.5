# services/medkb/src/medkb/endpoints/health.py
from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()


@router.get("/v1/healthz")
async def healthz() -> dict:
    return {"status": "ok", "service": "dhg-medkb"}


@router.get("/v1/readyz")
async def readyz() -> dict:
    return {"status": "ok", "checks": {"process": "up"}}


@router.get("/metrics")
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
