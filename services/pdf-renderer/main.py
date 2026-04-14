from __future__ import annotations

from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from renderer import RenderRequest, render_pdf

app = FastAPI(title="dhg-pdf-renderer", version="0.1.0")


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
