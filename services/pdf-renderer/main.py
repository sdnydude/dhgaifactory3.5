from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from renderer import RenderRequest, render_pdf

logger = logging.getLogger(__name__)

try:
    from worker import run_worker

    _worker_available = True
except ImportError as exc:  # pragma: no cover - environment gate
    logger.warning(
        "worker loop unavailable: %s. /render-sync will still serve. "
        "Wire sqlalchemy/pgvector/psycopg2 + registry package before enabling.",
        exc,
    )
    _worker_available = False
    run_worker = None  # type: ignore[assignment]

_worker_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_task, _stop_event
    if not _worker_available:
        yield
        return
    _stop_event = asyncio.Event()
    assert run_worker is not None
    _worker_task = asyncio.create_task(run_worker(_stop_event))
    try:
        yield
    finally:
        _stop_event.set()
        if _worker_task is not None:
            try:
                await asyncio.wait_for(_worker_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("worker task did not stop within 10s; cancelling")
                _worker_task.cancel()


app = FastAPI(title="dhg-pdf-renderer", version="0.1.0", lifespan=lifespan)


class RenderSyncBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    wait_for_selectors: list[str] = Field(default_factory=list)
    extra_http_headers: dict[str, str] = Field(default_factory=dict)
    timeout_ms: int = 30_000


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/render-sync")
async def render_sync(body: RenderSyncBody) -> Response:
    parsed = urlparse(body.url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="only http(s) urls allowed")
    pdf = await render_pdf(
        RenderRequest(
            url=body.url,
            wait_for_selectors=body.wait_for_selectors,
            extra_http_headers=body.extra_http_headers,
            timeout_ms=body.timeout_ms,
        )
    )
    return Response(content=pdf, media_type="application/pdf")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8014, reload=False)
