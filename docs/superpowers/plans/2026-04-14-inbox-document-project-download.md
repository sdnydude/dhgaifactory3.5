# Inbox Document & Project Download Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship CME-compliance-grade document and full-project downloads from the `/inbox` page, delivered across 5 phases so each phase ships working, testable value.

**Architecture:** A new sibling service `dhg-pdf-renderer` runs Playwright/Chromium against Next.js print routes so PDFs are rendered from the same React components we ship to users (single source of styling truth). The Registry API exposes a synchronous single-document endpoint and an asynchronous project-bundle endpoint backed by a new `download_jobs` table with a `FOR UPDATE SKIP LOCKED` worker queue running inside the API's async lifespan. Artifacts land on a shared Docker volume (`dhg_exports`) mounted read-write by the renderer and read-only by the API, served back through signed URLs. Print routes are protected by HMAC-signed short-lived tokens rather than the Cloudflare Access JWT so the renderer can fetch them without user credentials.

**Tech Stack:**
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 15, asyncpg/psycopg
- Rendering: Playwright + Chromium in a dedicated Python sibling service
- Frontend: Next.js 16 (print routes), shadcn/ui, Zustand (`persist` + `partialize`), Tailwind
- Auth: HMAC-SHA256 signed tokens (print routes), Cloudflare Access JWT (user-facing endpoints)
- Tests: pytest + httpx AsyncClient (backend), Playwright test runner + Vitest (frontend), Docker Compose for integration

**Spec:** `docs/superpowers/specs/2026-04-14-inbox-download-design.md`

**Important corrections to the spec (apply during implementation):**
- The spec says alembic migration `008`. That slot is taken by `008_add_pipeline_runs.py`. Use **`009_add_download_jobs.py`** throughout.

**Phase map:**

| Phase | Scope | Est. |
|-------|-------|------|
| 1 | Single document download (sync), renderer service scaffold, print infra, signing, Download button | 3–4d |
| 2 | Full project download (async), `download_jobs` table + worker, bundler v1, downloads tray, audit log | 5–7d |
| 3 | Quality/review/citation print routes + expanded bundle, chart-ready wait, Tremor chart in print | 4–5d |
| 4 | Revision history with semantic paragraph-level diff across checkpoints | 4–6d |
| 5 | Hardening: TTL cleanup, rate limiting, retry UX, Grafana/Alertmanager, key rotation, compliance stamp | 3–4d |

---

## Phase 1 — Single Document Download (sync path)

Goal: User on `/inbox` clicks **Download Document** in the review panel header. Within ~5 seconds the browser streams a PDF rendered from the same React component they see on screen. No job queue yet — strictly synchronous.

**Build order inside the phase:**
1. Scaffold sibling service `dhg-pdf-renderer`
2. Shared signing module (HMAC) — TDD
3. Renderer FastAPI `/render-sync` + Playwright helper
4. Dockerfile + compose wiring + shared volume
5. Next.js print route + layout + middleware bypass — TDD
6. Registry `export_endpoints` — `GET /document/{thread_id}` — TDD
7. Frontend Download button in review panel header
8. End-to-end smoke test through Playwright

---

### Task 1.1: Scaffold `dhg-pdf-renderer` service directory

**Files:**
- Create: `services/pdf-renderer/requirements.txt`
- Create: `services/pdf-renderer/main.py`
- Create: `services/pdf-renderer/README.md`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
playwright==1.48.0
pydantic==2.9.2
httpx==0.27.2
structlog==24.4.0
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Create minimal main.py that boots uvicorn with /health**

```python
from fastapi import FastAPI

app = FastAPI(title="dhg-pdf-renderer", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8014, reload=False)
```

- [ ] **Step 3: Create README.md**

```markdown
# dhg-pdf-renderer

Sibling service that renders Next.js print routes to PDF via Playwright/Chromium.
Only the Registry API should call this service; it is not exposed to users.

Endpoints:
- GET /health — liveness
- POST /render-sync — render a print URL to PDF and return the bytes
```

- [ ] **Step 4: Commit**

```bash
git add services/pdf-renderer/
git commit -m "feat(pdf-renderer): scaffold sibling service"
```

---

### Task 1.2: Shared HMAC signing module (TDD)

Print routes are reachable by any network client inside the docker network, so they must require a short-lived HMAC signature. We will mirror the exact same signing logic on the Python side (registry API → generates tokens) and the TypeScript side (Next.js middleware → verifies tokens).

**Files:**
- Create: `registry/export_signing.py`
- Create: `registry/test_export_signing.py`
- Create: `frontend/src/lib/printTokens.ts`
- Modify: `.env.example`

- [ ] **Step 1: Write the failing Python test**

```python
# registry/test_export_signing.py
import time

import pytest

from registry.export_signing import (
    PrintTokenPayload,
    sign_print_token,
    verify_print_token,
    PrintTokenInvalid,
    PrintTokenExpired,
)

SECRET = "a" * 64


def test_roundtrip_verifies() -> None:
    token = sign_print_token(
        PrintTokenPayload(
            subject="cme_document",
            resource_id="thread-abc",
            expires_at=int(time.time()) + 60,
        ),
        secret=SECRET,
    )
    payload = verify_print_token(token, secret=SECRET)
    assert payload.subject == "cme_document"
    assert payload.resource_id == "thread-abc"


def test_tampered_signature_rejected() -> None:
    token = sign_print_token(
        PrintTokenPayload(
            subject="cme_document",
            resource_id="thread-abc",
            expires_at=int(time.time()) + 60,
        ),
        secret=SECRET,
    )
    head, _, sig = token.rpartition(".")
    tampered = f"{head}.{'0' * len(sig)}"
    with pytest.raises(PrintTokenInvalid):
        verify_print_token(tampered, secret=SECRET)


def test_expired_rejected() -> None:
    token = sign_print_token(
        PrintTokenPayload(
            subject="cme_document",
            resource_id="thread-abc",
            expires_at=int(time.time()) - 1,
        ),
        secret=SECRET,
    )
    with pytest.raises(PrintTokenExpired):
        verify_print_token(token, secret=SECRET)


def test_wrong_secret_rejected() -> None:
    token = sign_print_token(
        PrintTokenPayload(
            subject="cme_document",
            resource_id="thread-abc",
            expires_at=int(time.time()) + 60,
        ),
        secret=SECRET,
    )
    with pytest.raises(PrintTokenInvalid):
        verify_print_token(token, secret="b" * 64)
```

- [ ] **Step 2: Run the test — expect ImportError**

```bash
docker exec dhg-registry-api pytest registry/test_export_signing.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'registry.export_signing'`

- [ ] **Step 3: Implement the signing module**

```python
# registry/export_signing.py
from __future__ import annotations

import base64
import hmac
import json
import time
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Literal


Subject = Literal["cme_document", "cme_project_intake", "cme_quality", "cme_review_history"]


class PrintTokenInvalid(Exception):
    """Token signature did not verify or payload was malformed."""


class PrintTokenExpired(Exception):
    """Token was well-formed but past its expiry."""


@dataclass(frozen=True)
class PrintTokenPayload:
    subject: Subject
    resource_id: str
    expires_at: int  # unix seconds


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign_print_token(payload: PrintTokenPayload, *, secret: str) -> str:
    body = _b64url_encode(json.dumps(asdict(payload), separators=(",", ":")).encode("utf-8"))
    mac = hmac.new(secret.encode("utf-8"), body.encode("ascii"), sha256).digest()
    return f"{body}.{_b64url_encode(mac)}"


def verify_print_token(token: str, *, secret: str) -> PrintTokenPayload:
    try:
        body, sig = token.split(".", 1)
    except ValueError as exc:
        raise PrintTokenInvalid("malformed token") from exc

    expected = _b64url_encode(
        hmac.new(secret.encode("utf-8"), body.encode("ascii"), sha256).digest()
    )
    if not hmac.compare_digest(expected, sig):
        raise PrintTokenInvalid("bad signature")

    try:
        raw = json.loads(_b64url_decode(body).decode("utf-8"))
        payload = PrintTokenPayload(**raw)
    except Exception as exc:
        raise PrintTokenInvalid("bad payload") from exc

    if payload.expires_at <= int(time.time()):
        raise PrintTokenExpired("token expired")
    return payload
```

- [ ] **Step 4: Run the test — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_signing.py -v
```

Expected: 4 passed

- [ ] **Step 5: Add `EXPORT_SIGNING_SECRET` to `.env.example`**

```bash
# .env.example
EXPORT_SIGNING_SECRET=change-me-to-a-64-char-random-hex-string
```

- [ ] **Step 6: Write the TypeScript verifier**

```typescript
// frontend/src/lib/printTokens.ts
import { createHmac, timingSafeEqual } from "node:crypto";

export class PrintTokenInvalid extends Error {}
export class PrintTokenExpired extends Error {}

export type Subject =
  | "cme_document"
  | "cme_project_intake"
  | "cme_quality"
  | "cme_review_history";

export interface PrintTokenPayload {
  subject: Subject;
  resource_id: string;
  expires_at: number;
}

function b64urlDecode(input: string): Buffer {
  const pad = "=".repeat((4 - (input.length % 4)) % 4);
  return Buffer.from(input + pad, "base64url");
}

function b64urlEncode(buf: Buffer): string {
  return buf.toString("base64url");
}

export function verifyPrintToken(token: string, secret: string): PrintTokenPayload {
  const dot = token.lastIndexOf(".");
  if (dot < 0) throw new PrintTokenInvalid("malformed token");
  const body = token.slice(0, dot);
  const sig = token.slice(dot + 1);

  const expected = b64urlEncode(createHmac("sha256", secret).update(body).digest());
  const a = Buffer.from(expected);
  const b = Buffer.from(sig);
  if (a.length !== b.length || !timingSafeEqual(a, b)) {
    throw new PrintTokenInvalid("bad signature");
  }

  let payload: PrintTokenPayload;
  try {
    payload = JSON.parse(b64urlDecode(body).toString("utf-8"));
  } catch {
    throw new PrintTokenInvalid("bad payload");
  }
  if (payload.expires_at <= Math.floor(Date.now() / 1000)) {
    throw new PrintTokenExpired("token expired");
  }
  return payload;
}
```

- [ ] **Step 7: Commit**

```bash
git add registry/export_signing.py registry/test_export_signing.py \
        frontend/src/lib/printTokens.ts .env.example
git commit -m "feat(export): add HMAC-signed print token module"
```

---

### Task 1.3: Playwright render helper in pdf-renderer service

**Files:**
- Create: `services/pdf-renderer/renderer.py`
- Create: `services/pdf-renderer/test_renderer.py`

- [ ] **Step 1: Write the failing test**

```python
# services/pdf-renderer/test_renderer.py
import asyncio

import pytest

from renderer import RenderRequest, render_pdf


@pytest.mark.asyncio
async def test_render_about_blank_returns_pdf_bytes() -> None:
    request = RenderRequest(
        url="about:blank",
        wait_for_selectors=[],
        timeout_ms=10_000,
    )
    pdf = await render_pdf(request)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1024
```

- [ ] **Step 2: Run test — expect ImportError**

Run: `cd services/pdf-renderer && pytest test_renderer.py -v`
Expected: FAIL (`No module named 'renderer'`)

- [ ] **Step 3: Implement the helper**

```python
# services/pdf-renderer/renderer.py
from __future__ import annotations

from dataclasses import dataclass, field

from playwright.async_api import async_playwright


@dataclass(frozen=True)
class RenderRequest:
    url: str
    wait_for_selectors: list[str] = field(default_factory=list)
    timeout_ms: int = 30_000
    extra_http_headers: dict[str, str] = field(default_factory=dict)


async def render_pdf(request: RenderRequest) -> bytes:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        try:
            context = await browser.new_context(
                extra_http_headers=request.extra_http_headers
            )
            page = await context.new_page()
            await page.goto(request.url, wait_until="networkidle", timeout=request.timeout_ms)
            for selector in request.wait_for_selectors:
                await page.wait_for_selector(selector, timeout=request.timeout_ms)
            # Wait for any element declaring it is still loading to finish
            await page.wait_for_function(
                "() => document.querySelectorAll('[data-loading=\"true\"]').length === 0",
                timeout=request.timeout_ms,
            )
            return await page.pdf(
                format="Letter",
                margin={"top": "0.75in", "bottom": "0.75in", "left": "0.75in", "right": "0.75in"},
                print_background=True,
            )
        finally:
            await browser.close()
```

- [ ] **Step 4: Run test — expect PASS**

Run: `cd services/pdf-renderer && pytest test_renderer.py -v`
Expected: 1 passed. (Chromium download is one-time.)

- [ ] **Step 5: Commit**

```bash
git add services/pdf-renderer/renderer.py services/pdf-renderer/test_renderer.py
git commit -m "feat(pdf-renderer): add Playwright render helper with data-loading wait"
```

---

### Task 1.4: `/render-sync` endpoint on pdf-renderer

**Files:**
- Modify: `services/pdf-renderer/main.py`
- Create: `services/pdf-renderer/test_main.py`

- [ ] **Step 1: Write the failing test**

```python
# services/pdf-renderer/test_main.py
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_render_sync_returns_pdf() -> None:
    fake_pdf = b"%PDF-1.7\nfake"
    with patch("main.render_pdf", new=AsyncMock(return_value=fake_pdf)):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/render-sync",
                json={
                    "url": "http://frontend:3000/print/cme/document/abc?t=xxx",
                    "wait_for_selectors": ["[data-print-ready=true]"],
                    "extra_http_headers": {},
                },
            )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == fake_pdf


@pytest.mark.asyncio
async def test_render_sync_rejects_non_http_url() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/render-sync",
            json={"url": "file:///etc/passwd", "wait_for_selectors": []},
        )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run test — expect FAIL**

`cd services/pdf-renderer && pytest test_main.py -v`
Expected: 404 on POST /render-sync

- [ ] **Step 3: Implement the endpoint**

```python
# services/pdf-renderer/main.py
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
```

- [ ] **Step 4: Run test — expect PASS**

`cd services/pdf-renderer && pytest test_main.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add services/pdf-renderer/main.py services/pdf-renderer/test_main.py
git commit -m "feat(pdf-renderer): add /render-sync endpoint with url validation"
```

---

### Task 1.5: Dockerfile + compose wiring for pdf-renderer

**Files:**
- Create: `services/pdf-renderer/Dockerfile`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# services/pdf-renderer/Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8014

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8014/health').status == 200 else 1)"

CMD ["python", "main.py"]
```

- [ ] **Step 2: Add service to `docker-compose.yml`**

```yaml
  dhg-pdf-renderer:
    build:
      context: ./services/pdf-renderer
      dockerfile: Dockerfile
    container_name: dhg-pdf-renderer
    restart: unless-stopped
    shm_size: 2gb
    environment:
      FRONTEND_INTERNAL_URL: http://dhg-frontend:3000
    networks:
      - dhg-network
    volumes:
      - dhg_exports:/exports
    # no external port — only reachable from registry-api over the internal network
```

And under the top-level `volumes:` block:

```yaml
volumes:
  dhg_exports:
    driver: local
```

- [ ] **Step 3: Build and start**

```bash
docker compose build dhg-pdf-renderer
docker compose up -d dhg-pdf-renderer
```

- [ ] **Step 4: Verify health**

```bash
docker exec dhg-pdf-renderer curl -fsS http://localhost:8014/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 5: Mount `dhg_exports` (read-only) on the registry-api service**

In `docker-compose.yml` under `dhg-registry-api`:

```yaml
    volumes:
      - ./registry:/app
      - dhg_exports:/exports:ro
    environment:
      # ... existing env vars ...
      EXPORT_SIGNING_SECRET: ${EXPORT_SIGNING_SECRET}
      PDF_RENDERER_URL: http://dhg-pdf-renderer:8014
      FRONTEND_INTERNAL_URL: http://dhg-frontend:3000
      EXPORTS_DIR: /exports
```

Then restart the API:

```bash
docker compose up -d dhg-registry-api
```

- [ ] **Step 6: Commit**

```bash
git add services/pdf-renderer/Dockerfile docker-compose.yml
git commit -m "feat(compose): wire dhg-pdf-renderer service and dhg_exports volume"
```

---

### Task 1.6: Next.js print layout + document print route

**Files:**
- Create: `frontend/src/app/print/layout.tsx`
- Create: `frontend/src/app/print/cme/document/[threadId]/page.tsx`
- Create: `frontend/src/components/print/print-shell.tsx`
- Create: `frontend/src/components/print/document-print.tsx`

- [ ] **Step 1: Create the print layout that strips chrome**

```typescript
// frontend/src/app/print/layout.tsx
import type { ReactNode } from "react";
import "@/app/globals.css";
import "./print.css";

export const dynamic = "force-dynamic";

export default function PrintLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-white text-[#32374A] antialiased">
        <main className="mx-auto max-w-[7.5in] px-[0.75in] py-[0.5in]">{children}</main>
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Create print stylesheet**

```css
/* frontend/src/app/print/print.css */
@media print {
  html, body { background: #ffffff !important; }
  .no-print { display: none !important; }
  a { color: #32374A; text-decoration: none; }
}

:root { --dhg-background: #ffffff; }
```

- [ ] **Step 3: Create shared print shell component**

```typescript
// frontend/src/components/print/print-shell.tsx
import type { ReactNode } from "react";

export interface PrintShellProps {
  title: string;
  subtitle?: string;
  generatedAt: string;
  children: ReactNode;
}

export function PrintShell({ title, subtitle, generatedAt, children }: PrintShellProps) {
  return (
    <article data-print-ready="true">
      <header className="mb-8 border-b border-[#E4E4E7] pb-4">
        <p className="text-[11px] uppercase tracking-[0.18em] text-[#71717A]">
          Digital Harmony Group · CME
        </p>
        <h1 className="mt-2 font-[Inter] text-2xl font-semibold text-[#32374A]">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-[#52525B]">{subtitle}</p>}
        <p className="mt-4 text-[10px] text-[#A1A1AA]">Generated {generatedAt}</p>
      </header>
      {children}
      <footer className="mt-12 border-t border-[#E4E4E7] pt-3 text-[10px] text-[#A1A1AA]">
        AI-assisted output · verify against source material · not legal or medical advice
      </footer>
    </article>
  );
}
```

- [ ] **Step 4: Create document print component**

```typescript
// frontend/src/components/print/document-print.tsx
import { PrintShell } from "./print-shell";

export interface DocumentPrintProps {
  title: string;
  graphLabel: string;
  reviewRound: number;
  documentText: string;
  generatedAt: string;
}

export function DocumentPrint({
  title,
  graphLabel,
  reviewRound,
  documentText,
  generatedAt,
}: DocumentPrintProps) {
  return (
    <PrintShell
      title={title}
      subtitle={`${graphLabel} · Round ${reviewRound + 1}`}
      generatedAt={generatedAt}
    >
      <div className="prose prose-sm max-w-none text-[#32374A]">
        {documentText.split(/\n{2,}/).map((para, i) => (
          <p key={i}>{para}</p>
        ))}
      </div>
    </PrintShell>
  );
}
```

- [ ] **Step 5: Create the print route**

```typescript
// frontend/src/app/print/cme/document/[threadId]/page.tsx
import { notFound } from "next/navigation";

import { DocumentPrint } from "@/components/print/document-print";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ threadId: string }>;
  searchParams: Promise<{ t?: string }>;
}

async function fetchDocument(threadId: string, token: string) {
  const registry = process.env.REGISTRY_INTERNAL_URL ?? "http://dhg-registry-api:8000";
  const res = await fetch(
    `${registry}/api/cme/export/internal/document/${threadId}`,
    {
      headers: { "X-Print-Token": token },
      cache: "no-store",
    },
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`registry fetch failed: ${res.status}`);
  return res.json() as Promise<{
    title: string;
    graph_label: string;
    review_round: number;
    document_text: string;
  }>;
}

export default async function Page({ params, searchParams }: Props) {
  const { threadId } = await params;
  const { t } = await searchParams;
  if (!t) notFound();
  const data = await fetchDocument(threadId, t);
  if (!data) notFound();
  return (
    <DocumentPrint
      title={data.title}
      graphLabel={data.graph_label}
      reviewRound={data.review_round}
      documentText={data.document_text}
      generatedAt={new Date().toISOString()}
    />
  );
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/print/ frontend/src/components/print/
git commit -m "feat(frontend): add /print/cme/document print route and shell"
```

---

### Task 1.7: Middleware bypass for `/print/*` with HMAC verify (TDD)

**Files:**
- Create: `frontend/src/lib/printTokens.test.ts`
- Modify: `frontend/src/middleware.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/lib/printTokens.test.ts
import { describe, expect, it } from "vitest";
import { createHmac } from "node:crypto";

import { PrintTokenInvalid, PrintTokenExpired, verifyPrintToken } from "./printTokens";

const SECRET = "a".repeat(64);

function sign(payload: object): string {
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const sig = createHmac("sha256", SECRET).update(body).digest().toString("base64url");
  return `${body}.${sig}`;
}

describe("verifyPrintToken", () => {
  it("accepts a valid token", () => {
    const token = sign({
      subject: "cme_document",
      resource_id: "thread-abc",
      expires_at: Math.floor(Date.now() / 1000) + 60,
    });
    const payload = verifyPrintToken(token, SECRET);
    expect(payload.resource_id).toBe("thread-abc");
  });

  it("rejects tampered signature", () => {
    const token = sign({
      subject: "cme_document",
      resource_id: "thread-abc",
      expires_at: Math.floor(Date.now() / 1000) + 60,
    });
    const [body] = token.split(".");
    expect(() => verifyPrintToken(`${body}.${"A".repeat(43)}`, SECRET)).toThrow(
      PrintTokenInvalid,
    );
  });

  it("rejects expired token", () => {
    const token = sign({
      subject: "cme_document",
      resource_id: "thread-abc",
      expires_at: Math.floor(Date.now() / 1000) - 1,
    });
    expect(() => verifyPrintToken(token, SECRET)).toThrow(PrintTokenExpired);
  });
});
```

- [ ] **Step 2: Run test — expect PASS (the verifier already exists from Task 1.2)**

```bash
cd frontend && pnpm vitest run src/lib/printTokens.test.ts
```

Expected: 3 passed

- [ ] **Step 3: Add `/print/*` bypass to middleware**

Replace the top of the existing middleware body so that print routes are checked **before** the Cloudflare Access logic:

```typescript
// frontend/src/middleware.ts (add inside the middleware function, near the top)
import { verifyPrintToken, PrintTokenInvalid, PrintTokenExpired } from "@/lib/printTokens";

// ... existing imports ...

const PRINT_SUBJECT_BY_PREFIX: Array<{ prefix: string; subject: string }> = [
  { prefix: "/print/cme/document/", subject: "cme_document" },
  { prefix: "/print/cme/project/", subject: "cme_project_intake" },
  { prefix: "/print/cme/quality/", subject: "cme_quality" },
  { prefix: "/print/cme/review-history/", subject: "cme_review_history" },
];

// Inside the middleware function, before the existing auth logic:
if (pathname.startsWith("/print/")) {
  const secret = process.env.EXPORT_SIGNING_SECRET;
  if (!secret) {
    return new NextResponse("print disabled", { status: 503 });
  }
  const token = request.nextUrl.searchParams.get("t");
  if (!token) {
    return new NextResponse("missing token", { status: 401 });
  }
  try {
    const payload = verifyPrintToken(token, secret);
    const match = PRINT_SUBJECT_BY_PREFIX.find((m) => pathname.startsWith(m.prefix));
    if (!match || match.subject !== payload.subject) {
      return new NextResponse("subject mismatch", { status: 403 });
    }
    const tail = pathname.slice(match.prefix.length).split("/")[0];
    if (tail !== payload.resource_id) {
      return new NextResponse("resource mismatch", { status: 403 });
    }
    return NextResponse.next();
  } catch (err) {
    if (err instanceof PrintTokenExpired) {
      return new NextResponse("expired", { status: 401 });
    }
    if (err instanceof PrintTokenInvalid) {
      return new NextResponse("invalid", { status: 401 });
    }
    throw err;
  }
}
```

And update the `config.matcher` so `/print/*` is actually evaluated (the existing matcher already matches any non-API path; verify no exclusion is needed).

- [ ] **Step 4: Manual check — token round-trip through middleware**

```bash
# Mint a token by hand inside the registry container
docker exec dhg-registry-api python -c "
import time, os
from registry.export_signing import sign_print_token, PrintTokenPayload
print(sign_print_token(PrintTokenPayload('cme_document','demo-thread', int(time.time())+60), secret=os.environ['EXPORT_SIGNING_SECRET']))
"
# Then hit the print route directly (will 404 on data, but 200 on auth)
docker exec dhg-pdf-renderer curl -sI "http://dhg-frontend:3000/print/cme/document/demo-thread?t=<paste-token>"
```

Expected: HTTP status ≠ 401/403. 404 is acceptable here — it means auth passed and the data lookup ran.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/middleware.ts frontend/src/lib/printTokens.test.ts
git commit -m "feat(frontend): bypass auth for /print/* behind HMAC token"
```

---

### Task 1.8: Registry `export_schemas.py`

**Files:**
- Create: `registry/export_schemas.py`

- [ ] **Step 1: Write schemas**

```python
# registry/export_schemas.py
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentPrintPayload(BaseModel):
    """Returned to the pdf-renderer via the frontend print route fetch."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    title: str
    graph_label: str
    review_round: int
    document_text: str


JobScope = Literal["document", "project"]
JobStatus = Literal["pending", "running", "succeeded", "failed"]


class DownloadJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    graph_id: str


class DownloadJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    thread_id: str
    graph_id: str
    scope: JobScope
    status: JobStatus
    artifact_bytes: int | None = None
    artifact_sha256: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


class DownloadJobListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: list[DownloadJobResponse] = Field(default_factory=list)
```

- [ ] **Step 2: Commit**

```bash
git add registry/export_schemas.py
git commit -m "feat(export): add pydantic schemas for export payloads and jobs"
```

---

### Task 1.9: Registry endpoints — `/document` sync + internal fetch (TDD)

**Files:**
- Create: `registry/export_endpoints.py`
- Create: `registry/test_export_endpoints.py`
- Create: `registry/export_service.py`
- Modify: `registry/api.py`

- [ ] **Step 1: Write the failing test**

```python
# registry/test_export_endpoints.py
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api import app


@pytest.mark.asyncio
async def test_internal_document_requires_print_token() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/cme/export/internal/document/thread-abc")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_document_sync_returns_pdf() -> None:
    fake_pdf = b"%PDF-1.7\nfake"
    fake_doc = {
        "title": "Diabetes Management",
        "graph_label": "Grant Package",
        "review_round": 1,
        "document_text": "para 1\n\npara 2",
    }
    with patch("export_service.load_document_for_thread", new=AsyncMock(return_value=fake_doc)), \
         patch("export_service.render_via_renderer", new=AsyncMock(return_value=fake_pdf)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(
                "/api/cme/export/document/thread-abc",
                headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
            )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.headers["content-disposition"].startswith("attachment;")
    assert resp.content == fake_pdf
```

- [ ] **Step 2: Run test — expect FAIL (404)**

```bash
docker exec dhg-registry-api pytest registry/test_export_endpoints.py -v
```

- [ ] **Step 3: Implement `export_service.py`**

```python
# registry/export_service.py
from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import quote

import httpx

from registry.export_signing import PrintTokenPayload, sign_print_token


def _secret() -> str:
    secret = os.environ.get("EXPORT_SIGNING_SECRET")
    if not secret:
        raise RuntimeError("EXPORT_SIGNING_SECRET not set")
    return secret


def _frontend_internal_url() -> str:
    return os.environ.get("FRONTEND_INTERNAL_URL", "http://dhg-frontend:3000")


def _renderer_url() -> str:
    return os.environ.get("PDF_RENDERER_URL", "http://dhg-pdf-renderer:8014")


def build_print_url(subject: str, resource_id: str, path_prefix: str, ttl_seconds: int = 300) -> str:
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

    Real implementation reads the latest checkpoint payload via the LangGraph SDK
    and the CMEDocument row for this thread. Kept as a thin module function so
    tests can monkey-patch it.
    """
    from registry.cme_endpoints import fetch_latest_document_for_thread  # lazy import

    return await fetch_latest_document_for_thread(thread_id)


async def render_via_renderer(url: str, wait_for_selectors: list[str] | None = None) -> bytes:
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
```

- [ ] **Step 4: Implement `export_endpoints.py`**

```python
# registry/export_endpoints.py
from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from registry.export_signing import (
    PrintTokenExpired,
    PrintTokenInvalid,
    verify_print_token,
)
from registry.export_schemas import DocumentPrintPayload
from registry.export_service import (
    build_print_url,
    load_document_for_thread,
    render_via_renderer,
)

router = APIRouter(prefix="/api/cme/export", tags=["cme-export"])


def _sanitize_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in s)[:80]


@router.get("/internal/document/{thread_id}", response_model=DocumentPrintPayload)
async def internal_document(
    thread_id: str,
    x_print_token: str | None = Header(default=None, alias="X-Print-Token"),
) -> DocumentPrintPayload:
    """Called by Next.js print route to hydrate the page.

    Protected by the same HMAC token the route was signed with, so it is
    never reachable from user traffic.
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
    """User-facing sync download. Auth handled by the Cloudflare Access layer."""
    data = await load_document_for_thread(thread_id)
    if not data:
        raise HTTPException(status_code=404, detail="document not found")
    url = build_print_url(
        subject="cme_document",
        resource_id=thread_id,
        path_prefix="/print/cme/document/",
    )
    pdf = await render_via_renderer(url)
    safe_title = _sanitize_filename(data["title"])
    stamp = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{safe_title}_{stamp}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "content-disposition": f'attachment; filename="{filename}"',
            "cache-control": "no-store",
        },
    )
```

- [ ] **Step 5: Stub `fetch_latest_document_for_thread` in `cme_endpoints.py`**

Add a function that the service layer calls. For Phase 1 it can pull from the most recent `CMEDocument` row joined to `CMEProject` by `pipeline_thread_id`.

```python
# registry/cme_endpoints.py — add at end of file
async def fetch_latest_document_for_thread(thread_id: str) -> dict | None:
    from sqlalchemy import select
    from database import async_session
    from models import CMEDocument, CMEProject

    async with async_session() as session:
        stmt = (
            select(CMEDocument, CMEProject)
            .join(CMEProject, CMEDocument.project_id == CMEProject.id)
            .where(CMEProject.pipeline_thread_id == thread_id)
            .order_by(CMEDocument.created_at.desc())
            .limit(1)
        )
        row = (await session.execute(stmt)).first()
        if not row:
            return None
        doc, project = row
        return {
            "title": project.name,
            "graph_label": doc.agent_source or "CME Document",
            "review_round": int(doc.meta.get("review_round", 0)) if doc.meta else 0,
            "document_text": doc.content or "",
        }
```

- [ ] **Step 6: Wire router into `api.py`**

```python
# registry/api.py — near existing app.include_router(dev_changelog_router)
from registry.export_endpoints import router as export_router
app.include_router(export_router)
```

- [ ] **Step 7: Run test — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_endpoints.py -v
```

Expected: 2 passed

- [ ] **Step 8: Commit**

```bash
git add registry/export_endpoints.py registry/export_service.py \
        registry/test_export_endpoints.py registry/cme_endpoints.py registry/api.py
git commit -m "feat(registry): add /api/cme/export sync document endpoint"
```

---

### Task 1.10: Frontend `exportApi.ts` client

**Files:**
- Create: `frontend/src/lib/exportApi.ts`

- [ ] **Step 1: Write the module**

```typescript
// frontend/src/lib/exportApi.ts
"use client";

const BASE = "/api/registry/api/cme/export";

export async function downloadDocument(threadId: string, suggestedName: string): Promise<void> {
  const res = await fetch(`${BASE}/document/${encodeURIComponent(threadId)}`, {
    method: "GET",
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(`download failed: ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${suggestedName}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/exportApi.ts
git commit -m "feat(frontend): add exportApi client for document download"
```

---

### Task 1.11: Download button in review panel header

**Files:**
- Modify: `frontend/src/components/review/review-panel.tsx`

- [ ] **Step 1: Import and add button in the masthead row**

Locate the `<div className="flex items-baseline justify-between gap-4 border-b border-border pb-2 mb-5">` block in `review-panel.tsx`. Keep the existing title/round on the left; add the Download button on the right-hand side of the same row.

```typescript
// frontend/src/components/review/review-panel.tsx — inside the masthead row
import { Download } from "lucide-react";
import { useState } from "react";
import { downloadDocument } from "@/lib/exportApi";
// ... existing imports ...

// inside the component:
const [downloading, setDownloading] = useState(false);
const handleDownload = async () => {
  try {
    setDownloading(true);
    await downloadDocument(payload.thread_id, payload.title ?? "document");
  } catch (err) {
    console.error(err);
  } finally {
    setDownloading(false);
  }
};

// inside the masthead row, after the round label:
<button
  type="button"
  onClick={handleDownload}
  disabled={downloading}
  aria-label="Download document"
  className="no-print inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1 text-xs text-foreground hover:bg-muted transition-colors disabled:opacity-50"
>
  <Download className="h-3.5 w-3.5" />
  {downloading ? "Preparing…" : "Document"}
</button>
```

- [ ] **Step 2: Build and smoke test through the UI**

```bash
docker compose up -d dhg-frontend dhg-registry-api dhg-pdf-renderer
# open http://localhost:3000/inbox, select a review, click Download
```

Expected: browser downloads `<title>.pdf` and opening it shows the same headline/body that's visible in the review panel.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/review/review-panel.tsx
git commit -m "feat(inbox): add document download button to review panel header"
```

---

### Task 1.12: Phase 1 end-to-end smoke test

**Files:**
- Create: `frontend/e2e/inbox-document-download.spec.ts`

- [ ] **Step 1: Write the Playwright spec**

```typescript
// frontend/e2e/inbox-document-download.spec.ts
import { test, expect } from "@playwright/test";

test("inbox document download produces a PDF", async ({ page }) => {
  await page.goto("/inbox");
  await page.getByRole("button", { name: /grant package|needs package/i }).first().click();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /document/i }).click();
  const download = await downloadPromise;

  const path = await download.path();
  expect(path).toBeTruthy();
  const fs = await import("node:fs");
  const buf = fs.readFileSync(path!);
  expect(buf.subarray(0, 5).toString()).toBe("%PDF-");
  expect(buf.length).toBeGreaterThan(2048);
});
```

- [ ] **Step 2: Run it**

```bash
cd frontend && pnpm playwright test inbox-document-download.spec.ts
```

Expected: 1 passed

- [ ] **Step 3: Commit Phase 1**

```bash
git add frontend/e2e/inbox-document-download.spec.ts
git commit -m "test(inbox): e2e smoke test for document download"
git tag phase1-complete
```

---

## Phase 2 — Full Project Download (async with jobs table)

Goal: Second button on `/inbox` labeled **Download full project**. Enqueues a job, returns immediately with a job id. The registry's async worker picks up the job, assembles a zip bundle containing the intake PDF, every document PDF, and a JSON manifest, writes it to `/exports/`, and records a SHA-256 + byte count. The frontend polls via a downloads tray and offers the finished artifact.

**Build order inside the phase:**
1. Alembic migration `009_add_download_jobs.py` + SQLAlchemy model
2. Job enqueue + dedup + audit log
3. Job status, artifact stream, list endpoints
4. Worker loop in FastAPI lifespan with `SKIP LOCKED`
5. Project intake print route + bundler v1 + atomic zip writer
6. Frontend downloads store + polling hook + tray
7. "Download full project" button wired into inbox page header
8. Integration test

---

### Task 2.1: Alembic migration `009_add_download_jobs`

**Files:**
- Create: `registry/alembic/versions/009_add_download_jobs.py`

- [ ] **Step 1: Find the current head revision**

```bash
docker exec dhg-registry-api alembic heads
```

Expected: `008_add_pipeline_runs (head)`

- [ ] **Step 2: Write the migration**

```python
# registry/alembic/versions/009_add_download_jobs.py
"""add download_jobs table

Revision ID: 009_add_download_jobs
Revises: 008_add_pipeline_runs
Create Date: 2026-04-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "009_add_download_jobs"
down_revision = "008_add_pipeline_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "download_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("thread_id", sa.Text(), nullable=False),
        sa.Column("graph_id", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("artifact_sha256", sa.Text(), nullable=True),
        sa.Column("artifact_bytes", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint("scope IN ('document','project')", name="download_jobs_scope_check"),
        sa.CheckConstraint(
            "status IN ('pending','running','succeeded','failed')",
            name="download_jobs_status_check",
        ),
    )
    op.create_index(
        "ix_download_jobs_status_created_at",
        "download_jobs",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_download_jobs_thread_scope_status",
        "download_jobs",
        ["thread_id", "scope", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_download_jobs_thread_scope_status", table_name="download_jobs")
    op.drop_index("ix_download_jobs_status_created_at", table_name="download_jobs")
    op.drop_table("download_jobs")
```

- [ ] **Step 3: Run the migration**

```bash
docker exec dhg-registry-api alembic upgrade head
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade 008_add_pipeline_runs -> 009_add_download_jobs`

- [ ] **Step 4: Verify table exists**

```bash
docker exec dhg-registry-db psql -U dhg -d dhg_registry -c "\d download_jobs"
```

Expected: table listing with 13 columns + 2 indexes + 2 check constraints.

- [ ] **Step 5: Commit**

```bash
git add registry/alembic/versions/009_add_download_jobs.py
git commit -m "feat(registry): add 009 alembic migration for download_jobs"
```

---

### Task 2.2: SQLAlchemy `DownloadJob` model

**Files:**
- Modify: `registry/models.py`

- [ ] **Step 1: Add the model at the bottom of `models.py`**

```python
class DownloadJob(Base):
    __tablename__ = "download_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(Text, nullable=False)
    graph_id = Column(Text, nullable=False)
    scope = Column(Text, nullable=False)  # 'document' | 'project'
    status = Column(Text, nullable=False, default="pending")
    artifact_path = Column(Text, nullable=True)
    artifact_sha256 = Column(Text, nullable=True)
    artifact_bytes = Column(BigInteger, nullable=True)
    created_by = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<DownloadJob id={self.id} scope={self.scope} status={self.status}>"
```

Ensure `BigInteger` and `Text` and `text` are in the existing `sqlalchemy` import block at the top of the file.

- [ ] **Step 2: Commit**

```bash
git add registry/models.py
git commit -m "feat(registry): add DownloadJob model"
```

---

### Task 2.3: Alembic migration `010_download_feature_v2`

**Files:**
- Create: `registry/alembic/versions/010_download_feature_v2.py`

v2 adds `project_id` + `selected_document_ids` to `download_jobs`, widens the `scope` CHECK to `('document','project_bundle','drive_sync')`, and adds Drive tracking columns to `cme_projects` and `cme_documents`. Follow repo convention: short numeric revision ID (`"010"`), not long-form.

- [ ] **Step 1: Write the migration**

```python
"""download feature v2

Revision ID: 010
Revises: 009
Create Date: 2026-04-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # download_jobs: add project_id + selected_document_ids
    op.add_column(
        "download_jobs",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "download_jobs",
        sa.Column("selected_document_ids", postgresql.JSONB, nullable=True),
    )
    op.create_foreign_key(
        "fk_download_jobs_project",
        "download_jobs",
        "cme_projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_download_jobs_project_status",
        "download_jobs",
        ["project_id", "status"],
    )

    # Widen scope CHECK
    op.drop_constraint(
        "download_jobs_scope_check", "download_jobs", type_="check"
    )
    op.create_check_constraint(
        "download_jobs_scope_check",
        "download_jobs",
        "scope IN ('document','project_bundle','drive_sync')",
    )

    # cme_projects: Drive tracking
    op.add_column(
        "cme_projects",
        sa.Column("drive_folder_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "cme_projects",
        sa.Column(
            "drive_last_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "cme_projects",
        sa.Column("drive_sync_status", sa.Text(), nullable=True),
    )

    # cme_documents: Drive tracking
    op.add_column(
        "cme_documents",
        sa.Column("drive_file_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "cme_documents",
        sa.Column(
            "drive_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "cme_documents",
        sa.Column("drive_md5", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cme_documents", "drive_md5")
    op.drop_column("cme_documents", "drive_synced_at")
    op.drop_column("cme_documents", "drive_file_id")
    op.drop_column("cme_projects", "drive_sync_status")
    op.drop_column("cme_projects", "drive_last_synced_at")
    op.drop_column("cme_projects", "drive_folder_id")

    op.drop_constraint(
        "download_jobs_scope_check", "download_jobs", type_="check"
    )
    op.create_check_constraint(
        "download_jobs_scope_check",
        "download_jobs",
        "scope IN ('document','project')",
    )

    op.drop_index(
        "ix_download_jobs_project_status", table_name="download_jobs"
    )
    op.drop_constraint(
        "fk_download_jobs_project", "download_jobs", type_="foreignkey"
    )
    op.drop_column("download_jobs", "selected_document_ids")
    op.drop_column("download_jobs", "project_id")
```

- [ ] **Step 2: Rebuild registry-api and run the migration**

```bash
docker compose build registry-api
docker compose up -d registry-api
docker logs dhg-registry-api 2>&1 | grep -E "alembic|Running upgrade" | tail -20
```

Expected: log contains `Running upgrade 009 -> 010, download feature v2`.

- [ ] **Step 3: Verify schema**

```bash
docker exec dhg-registry-db psql -U dhg -d dhg_registry -c "\d download_jobs" | grep -E "project_id|selected_document_ids|scope_check"
docker exec dhg-registry-db psql -U dhg -d dhg_registry -c "\d cme_projects" | grep drive_
docker exec dhg-registry-db psql -U dhg -d dhg_registry -c "\d cme_documents" | grep drive_
```

Expected: all new columns present; scope check allows `project_bundle` and `drive_sync`.

- [ ] **Step 4: Commit**

```bash
git add registry/alembic/versions/010_download_feature_v2.py
git commit -m "feat(registry): migration 010 — download_jobs v2 + Drive tracking columns"
```

---

### Task 2.4: SQLAlchemy model updates for v2 schema

**Files:**
- Modify: `registry/models.py`

Adds the new columns to `DownloadJob`, `CMEProject`, `CMEDocument`. Follow existing conventions (`func.now()`, `Index` in `__table_args__`, `JSONB` import from `sqlalchemy.dialects.postgresql`).

- [ ] **Step 1: Extend `DownloadJob`**

In `registry/models.py`, modify the existing `DownloadJob` class (added in Task 2.2) to add two columns and one index. Add after the existing `error` column:

```python
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cme_projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    selected_document_ids = Column(JSONB, nullable=True)
```

And extend `__table_args__`:

```python
    __table_args__ = (
        Index("ix_download_jobs_status_created_at", "status", "created_at"),
        Index(
            "ix_download_jobs_thread_scope_status",
            "thread_id", "scope", "status",
        ),
        Index(
            "ix_download_jobs_project_status",
            "project_id", "status",
        ),
    )
```

If `JSONB` is not already imported in `models.py`, add:

```python
from sqlalchemy.dialects.postgresql import JSONB
```

- [ ] **Step 2: Extend `CMEProject`**

In the existing `CMEProject` class, add three Drive columns (location: next to other metadata columns, before `relationships`):

```python
    drive_folder_id = Column(Text, nullable=True)
    drive_last_synced_at = Column(DateTime(timezone=True), nullable=True)
    drive_sync_status = Column(Text, nullable=True)
```

- [ ] **Step 3: Extend `CMEDocument`**

In the existing `CMEDocument` class, add three Drive columns:

```python
    drive_file_id = Column(Text, nullable=True)
    drive_synced_at = Column(DateTime(timezone=True), nullable=True)
    drive_md5 = Column(Text, nullable=True)
```

- [ ] **Step 4: Syntax check on host**

```bash
python3 -c "import ast; ast.parse(open('registry/models.py').read()); print('OK')"
```

Expected: `OK`.

- [ ] **Step 5: Rebuild + import check**

```bash
docker compose build registry-api
docker compose up -d registry-api
docker exec dhg-registry-api python -c "from models import DownloadJob, CMEProject, CMEDocument; print(DownloadJob.project_id, CMEProject.drive_folder_id, CMEDocument.drive_file_id)"
```

Expected: three Column references print with no ImportError.

- [ ] **Step 6: Commit**

```bash
git add registry/models.py
git commit -m "feat(registry): extend DownloadJob/CMEProject/CMEDocument for v2 (project_id, Drive fields)"
```

---

### Task 2.5: Pydantic schemas for v2 endpoints

**Files:**
- Modify: `registry/export_schemas.py`
- Create: `registry/project_schemas.py`

Adds bundle job request/response, project list + project documents response schemas. All use `ConfigDict(extra="forbid")` per the serializer-drift rule.

- [ ] **Step 1: Extend `registry/export_schemas.py`**

Add these classes near the existing `DownloadJobCreate`:

```python
from uuid import UUID

class BundleJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    document_ids: list[UUID] | None = None  # None = all current docs
    include_manifest: bool = True
    include_intake: bool = False


class BundleJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    project_id: UUID | None
    scope: Literal["document", "project_bundle", "drive_sync"]
    status: Literal["pending", "running", "succeeded", "failed"]
    selected_document_ids: list[UUID] | None
    created_at: datetime
    completed_at: datetime | None
    artifact_bytes: int | None
    error: str | None
```

- [ ] **Step 2: Create `registry/project_schemas.py`**

```python
"""Pydantic schemas for project list + project documents endpoints.

Serializer-drift rule: every field is enumerated explicitly; extra fields
rejected at parse time. Response constructors in projects_endpoints.py
must pass each field by name — never `**model.__dict__`.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    status: str
    kind: str | None
    document_count: int
    last_activity_at: datetime | None
    drive_folder_id: str | None


class ProjectListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    projects: list[ProjectListItem]
    total: int
    limit: int
    offset: int


class ProjectDocumentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    document_type: str
    title: str | None
    word_count: int | None
    version: int
    is_current: bool
    created_at: datetime
    drive_file_id: str | None


class ProjectDocumentsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    documents: list[ProjectDocumentItem]
```

- [ ] **Step 3: Syntax check**

```bash
python3 -c "import ast; ast.parse(open('registry/export_schemas.py').read()); ast.parse(open('registry/project_schemas.py').read()); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add registry/export_schemas.py registry/project_schemas.py
git commit -m "feat(registry): Pydantic schemas for bundle jobs + project list/documents"
```

---

### Task 2.6: Project list + project documents endpoints (TDD)

**Files:**
- Create: `registry/projects_endpoints.py`
- Create: `registry/test_projects_endpoints.py`
- Modify: `registry/api.py` (wire the router)

Adds `GET /api/cme/export/projects` and `GET /api/cme/export/projects/{project_id}/documents`. Read-only. Requires authenticated user (existing `require_user` dependency).

**Route namespace note:** `/api/cme/projects` already exists in `cme_endpoints.py` (CME admin projects list, returning `List[CMEProjectDetail]`, consumed by the frontend CME admin page and `use-badge-polling`). The Files tab needs a different schema shape (paginated `{projects, total, limit, offset}` with aggregates), so it slots under the existing Phase 1 `/api/cme/export/*` namespace alongside `POST /api/cme/export/bundle`. The Files tab is semantically the "export browser." Do NOT mount this router at `/api/cme/projects` — that would shadow the existing admin endpoint and break the frontend.

- [ ] **Step 1: Write the failing tests**

```python
# registry/test_projects_endpoints.py
import pytest
from httpx import ASGITransport, AsyncClient

from registry.api import app


@pytest.mark.asyncio
async def test_list_projects_returns_real_rows() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.get(
            "/api/cme/export/projects?limit=5",
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "projects" in body
    assert isinstance(body["projects"], list)
    assert body["limit"] == 5
    if body["projects"]:
        item = body["projects"][0]
        for k in ("id", "name", "status", "document_count"):
            assert k in item


@pytest.mark.asyncio
async def test_list_projects_search_filter() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.get(
            "/api/cme/export/projects?search=zzz_not_a_real_project",
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
    assert resp.status_code == 200
    assert resp.json()["projects"] == []


@pytest.mark.asyncio
async def test_project_documents_returns_current_versions() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        # Pick a project with known documents
        list_resp = await c.get(
            "/api/cme/export/projects?limit=1",
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
        projects = list_resp.json()["projects"]
        if not projects:
            pytest.skip("no projects in DB to exercise the endpoint")
        pid = projects[0]["id"]

        docs_resp = await c.get(
            f"/api/cme/export/projects/{pid}/documents",
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
    assert docs_resp.status_code == 200
    body = docs_resp.json()
    assert body["project_id"] == pid
    assert isinstance(body["documents"], list)
    for d in body["documents"]:
        assert d["is_current"] is True
```

- [ ] **Step 2: Run the tests — verify they fail**

```bash
docker exec dhg-registry-api python -m pytest registry/test_projects_endpoints.py -v
```

Expected: 404 for both endpoints (router not mounted yet).

- [ ] **Step 3: Implement the endpoints**

```python
# registry/projects_endpoints.py
"""Project list + project documents endpoints for the inbox Files tab."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from registry.auth import require_user
from registry.database import get_db
from registry.models import CMEDocument, CMEProject
from registry.project_schemas import (
    ProjectDocumentItem,
    ProjectDocumentsResponse,
    ProjectListItem,
    ProjectListResponse,
)

router = APIRouter(prefix="/api/cme/export/projects", tags=["cme-export"])


@router.get("", response_model=ProjectListResponse)
def list_projects(
    search: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user=Depends(require_user),
) -> ProjectListResponse:
    doc_count_sq = (
        db.query(
            CMEDocument.project_id.label("pid"),
            func.count(CMEDocument.id).label("cnt"),
            func.max(CMEDocument.created_at).label("last_activity"),
        )
        .filter(CMEDocument.is_current.is_(True))
        .group_by(CMEDocument.project_id)
        .subquery()
    )

    q = db.query(
        CMEProject,
        func.coalesce(doc_count_sq.c.cnt, 0).label("cnt"),
        doc_count_sq.c.last_activity,
    ).outerjoin(doc_count_sq, CMEProject.id == doc_count_sq.c.pid)

    if search:
        term = f"%{search.strip()}%"
        q = q.filter(CMEProject.name.ilike(term))
    if status:
        q = q.filter(CMEProject.status == status)

    total = q.count()
    rows = (
        q.order_by(CMEProject.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    projects = [
        ProjectListItem(
            id=row[0].id,
            name=row[0].name,
            status=row[0].status,
            kind=getattr(row[0], "kind", None),
            document_count=int(row[1]),
            last_activity_at=row[2],
            drive_folder_id=row[0].drive_folder_id,
        )
        for row in rows
    ]
    return ProjectListResponse(
        projects=projects, total=total, limit=limit, offset=offset
    )


@router.get("/{project_id}/documents", response_model=ProjectDocumentsResponse)
def list_project_documents(
    project_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_user),
) -> ProjectDocumentsResponse:
    project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    docs = (
        db.query(CMEDocument)
        .filter(
            CMEDocument.project_id == project_id,
            CMEDocument.is_current.is_(True),
        )
        .order_by(CMEDocument.document_type, CMEDocument.version.desc())
        .all()
    )

    items = [
        ProjectDocumentItem(
            id=d.id,
            document_type=d.document_type,
            title=d.title,
            word_count=d.word_count,
            version=d.version,
            is_current=d.is_current,
            created_at=d.created_at,
            drive_file_id=d.drive_file_id,
        )
        for d in docs
    ]
    return ProjectDocumentsResponse(project_id=project_id, documents=items)
```

- [ ] **Step 4: Mount the router in `registry/api.py`**

```python
# near the other router imports
from registry.projects_endpoints import router as projects_router

# near other include_router calls
app.include_router(projects_router)
```

- [ ] **Step 5: Rebuild + run tests**

```bash
docker compose build registry-api
docker compose up -d registry-api
docker exec dhg-registry-api python -m pytest registry/test_projects_endpoints.py -v
```

Expected: 3/3 pass.

- [ ] **Step 6: Commit**

```bash
git add registry/projects_endpoints.py registry/test_projects_endpoints.py registry/api.py
git commit -m "feat(registry): project list + project documents endpoints for Files tab"
```

---

### Task 2.7: Bundle enqueue endpoint + amended job/artifact endpoints (TDD)

**Files:**
- Modify: `registry/export_endpoints.py`
- Modify: `registry/test_export_endpoints.py`

Adds `POST /api/cme/export/bundle`, `GET /api/cme/export/job/{id}`, `GET /api/cme/export/artifact/{id}`, `GET /api/cme/export/jobs`. Bundle creation validates that every selected document_id belongs to the given project_id before inserting the row.

- [ ] **Step 1: Write failing tests**

```python
# append to registry/test_export_endpoints.py
import pytest
from httpx import ASGITransport, AsyncClient

from registry.api import app


@pytest.mark.asyncio
async def test_bundle_enqueue_returns_job_id() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        projects = (
            await c.get(
                "/api/cme/export/projects?limit=1",
                headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
            )
        ).json()["projects"]
        if not projects:
            pytest.skip("no projects available")
        pid = projects[0]["id"]

        resp = await c.post(
            "/api/cme/export/bundle",
            json={
                "project_id": pid,
                "document_ids": None,
                "include_manifest": True,
                "include_intake": False,
            },
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
    assert resp.status_code == 202
    body = resp.json()
    assert body["scope"] == "project_bundle"
    assert body["status"] == "pending"
    assert body["project_id"] == pid


@pytest.mark.asyncio
async def test_bundle_rejects_doc_ids_outside_project() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        projects = (
            await c.get(
                "/api/cme/export/projects?limit=2",
                headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
            )
        ).json()["projects"]
        if len(projects) < 2:
            pytest.skip("need two projects")
        pid_a = projects[0]["id"]
        pid_b = projects[1]["id"]

        docs_b = (
            await c.get(
                f"/api/cme/export/projects/{pid_b}/documents",
                headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
            )
        ).json()["documents"]
        if not docs_b:
            pytest.skip("project B has no documents")

        resp = await c.post(
            "/api/cme/export/bundle",
            json={
                "project_id": pid_a,
                "document_ids": [docs_b[0]["id"]],
                "include_manifest": True,
                "include_intake": False,
            },
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
    assert resp.status_code == 400
    assert "document_ids" in resp.json()["detail"].lower()
```

- [ ] **Step 2: Run tests — should fail 404/405**

```bash
docker exec dhg-registry-api python -m pytest registry/test_export_endpoints.py::test_bundle_enqueue_returns_job_id registry/test_export_endpoints.py::test_bundle_rejects_doc_ids_outside_project -v
```

- [ ] **Step 3: Implement endpoints**

Append to `registry/export_endpoints.py`:

```python
from uuid import UUID
from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from registry.export_schemas import BundleJobCreate, BundleJobResponse
from registry.models import CMEDocument, CMEProject, DownloadJob


def _serialize_job(job: DownloadJob) -> BundleJobResponse:
    return BundleJobResponse(
        id=job.id,
        project_id=job.project_id,
        scope=job.scope,
        status=job.status,
        selected_document_ids=job.selected_document_ids,
        created_at=job.created_at,
        completed_at=job.completed_at,
        artifact_bytes=job.artifact_bytes,
        error=job.error,
    )


@router.post("/bundle", response_model=BundleJobResponse, status_code=202)
def create_bundle_job(
    body: BundleJobCreate,
    db: Session = Depends(get_db),
    user=Depends(require_user),
) -> BundleJobResponse:
    project = (
        db.query(CMEProject).filter(CMEProject.id == body.project_id).first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    if body.document_ids is not None:
        if not body.document_ids:
            raise HTTPException(
                status_code=400, detail="document_ids may not be empty list"
            )
        count = (
            db.query(CMEDocument)
            .filter(
                CMEDocument.id.in_(body.document_ids),
                CMEDocument.project_id == body.project_id,
                CMEDocument.is_current.is_(True),
            )
            .count()
        )
        if count != len(body.document_ids):
            raise HTTPException(
                status_code=400,
                detail="one or more document_ids do not belong to this project",
            )

    job = DownloadJob(
        thread_id=project.pipeline_thread_id or "",
        graph_id="bundle",
        scope="project_bundle",
        status="pending",
        project_id=project.id,
        selected_document_ids=(
            [str(x) for x in body.document_ids] if body.document_ids else None
        ),
        created_by=getattr(user, "email", None),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _serialize_job(job)


@router.get("/job/{job_id}", response_model=BundleJobResponse)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_user),
) -> BundleJobResponse:
    job = db.query(DownloadJob).filter(DownloadJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.created_by and job.created_by != getattr(user, "email", None):
        if not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="forbidden")
    return _serialize_job(job)


@router.get("/artifact/{job_id}")
def stream_artifact(
    job_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_user),
) -> FileResponse:
    job = db.query(DownloadJob).filter(DownloadJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.created_by and job.created_by != getattr(user, "email", None):
        if not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="forbidden")
    if job.status != "succeeded" or not job.artifact_path:
        raise HTTPException(status_code=409, detail="artifact not ready")
    return FileResponse(
        path=job.artifact_path,
        media_type="application/zip",
        filename=f"bundle-{job.id}.zip",
    )


@router.get("/jobs", response_model=list[BundleJobResponse])
def list_jobs(
    limit: int = 20,
    db: Session = Depends(get_db),
    user=Depends(require_user),
) -> list[BundleJobResponse]:
    email = getattr(user, "email", None)
    q = db.query(DownloadJob)
    if email:
        q = q.filter(DownloadJob.created_by == email)
    rows = q.order_by(DownloadJob.created_at.desc()).limit(limit).all()
    return [_serialize_job(j) for j in rows]
```

- [ ] **Step 4: Rebuild + run tests**

```bash
docker compose build registry-api && docker compose up -d registry-api
docker exec dhg-registry-api python -m pytest registry/test_export_endpoints.py -v
```

Expected: new tests pass; existing Phase 1 tests still pass.

- [ ] **Step 5: Commit**

```bash
git add registry/export_endpoints.py registry/test_export_endpoints.py
git commit -m "feat(registry): bundle enqueue endpoint + job/artifact/jobs routes"
```

---

### Task 2.8: Bundler reading from `cme_documents` (TDD)

**Files:**
- Create: `services/pdf-renderer/src/bundler.py`
- Create: `services/pdf-renderer/tests/test_bundler.py`

`assemble_bundle(job)` reads the selected documents from `cme_documents` (already-authoritative store; Phase 1 proved this works). Renders MD from `content_text`, PDF via Playwright against the existing `/print/document/{id}` route. Atomic zip: write to `.tmp`, `os.replace` to final.

- [ ] **Step 1: Write failing test with mocked render**

```python
# services/pdf-renderer/tests/test_bundler.py
import hashlib
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bundler import assemble_bundle


@pytest.mark.asyncio
async def test_assemble_bundle_writes_expected_structure(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("EXPORTS_DIR", str(tmp_path))

    fake_docs = [
        MagicMock(
            id="doc-1",
            document_type="needs_assessment",
            title="Needs",
            content_text="# Needs\n\nBody.",
        ),
        MagicMock(
            id="doc-2",
            document_type="research",
            title="Research",
            content_text="# Research\n\nBody.",
        ),
    ]
    fake_project = MagicMock(
        id="proj-1", name="Test Project", pipeline_thread_id="t-1"
    )
    fake_job = MagicMock(
        id="job-1",
        project_id="proj-1",
        selected_document_ids=None,
        include_manifest=True,
        include_intake=False,
    )

    import src.bundler as bundler_mod

    monkeypatch.setattr(
        bundler_mod, "load_project", MagicMock(return_value=fake_project)
    )
    monkeypatch.setattr(
        bundler_mod, "load_current_docs", MagicMock(return_value=fake_docs)
    )
    monkeypatch.setattr(
        bundler_mod,
        "render_document_pdf",
        AsyncMock(return_value=b"%PDF-1.4 fake\n%%EOF"),
    )
    monkeypatch.setattr(
        bundler_mod, "update_job_artifact", MagicMock()
    )

    await assemble_bundle(fake_job)

    final = tmp_path / "job-1.zip"
    assert final.exists()
    with zipfile.ZipFile(final) as zf:
        names = set(zf.namelist())
        assert "README.md" in names
        assert "04-metadata/project.json" in names
        assert "01-documents/01-needs_assessment.md" in names
        assert "01-documents/01-needs_assessment.pdf" in names
        assert "01-documents/02-research.md" in names
        assert "01-documents/02-research.pdf" in names

        meta = json.loads(zf.read("04-metadata/project.json"))
        assert meta["project_id"] == "proj-1"
        assert meta["selection_mode"] == "all"
```

- [ ] **Step 2: Run test — verify failure**

```bash
cd services/pdf-renderer && python -m pytest tests/test_bundler.py -v
```

- [ ] **Step 3: Implement `bundler.py`**

```python
"""Project bundle assembler.

Reads from cme_documents (authoritative store; Phase 1 already uses this
path via registry's fetch_latest_document_for_thread). Writes zip to a
.tmp file then atomically renames. Uses EXPORTS_DIR env var for the base
path (admin-configurable storage is deferred per spec §11).
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .renderer import RenderRequest, render_pdf
from .signing import sign_token

logger = logging.getLogger(__name__)


def _exports_dir() -> Path:
    base = os.getenv("EXPORTS_DIR", "/var/exports")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_project(project_id: Any) -> Any:
    from .db import session_scope
    from registry.models import CMEProject

    with session_scope() as db:
        return db.query(CMEProject).filter(CMEProject.id == project_id).first()


def load_current_docs(
    project_id: Any, selected_ids: list[str] | None
) -> list[Any]:
    from .db import session_scope
    from registry.models import CMEDocument

    with session_scope() as db:
        q = db.query(CMEDocument).filter(
            CMEDocument.project_id == project_id,
            CMEDocument.is_current.is_(True),
        )
        if selected_ids:
            q = q.filter(CMEDocument.id.in_(selected_ids))
        return (
            q.order_by(CMEDocument.document_type, CMEDocument.version.desc())
            .all()
        )


async def render_document_pdf(document_id: Any) -> bytes:
    frontend = os.getenv("FRONTEND_INTERNAL_URL", "http://dhg-frontend:3000")
    token = sign_token(f"document:{document_id}")
    url = f"{frontend}/print/document/{document_id}?token={token}"
    return await render_pdf(
        RenderRequest(
            url=url,
            wait_for_selectors=["[data-print-ready='true']"],
            timeout_ms=30_000,
        )
    )


def update_job_artifact(job_id: Any, path: Path, size: int, sha: str) -> None:
    from .db import session_scope
    from registry.models import DownloadJob

    with session_scope() as db:
        job = db.query(DownloadJob).filter(DownloadJob.id == job_id).first()
        if job is None:
            return
        job.artifact_path = str(path)
        job.artifact_bytes = size
        job.artifact_sha256 = sha
        db.commit()


def _manifest_text(
    project: Any,
    entries: list[tuple[str, str]],
    selection_mode: str,
) -> str:
    lines = [
        f"# Bundle: {project.name}",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Selection mode: {selection_mode}",
        "",
        "## Files",
        "",
    ]
    for name, sha in entries:
        lines.append(f"- `{name}` — sha256 `{sha}`")
    lines.append("")
    return "\n".join(lines)


async def assemble_bundle(job: Any) -> None:
    exports = _exports_dir()
    tmp = exports / f"{job.id}.zip.tmp"
    final = exports / f"{job.id}.zip"

    project = load_project(job.project_id)
    if project is None:
        raise RuntimeError(f"project {job.project_id} not found")

    selected = (
        list(job.selected_document_ids) if job.selected_document_ids else None
    )
    docs = load_current_docs(job.project_id, selected)
    if not docs:
        raise RuntimeError("no documents matched the selection")

    entries: list[tuple[str, str]] = []

    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, doc in enumerate(docs, start=1):
            prefix = f"{i:02d}-{doc.document_type}"
            md_name = f"01-documents/{prefix}.md"
            pdf_name = f"01-documents/{prefix}.pdf"

            md_bytes = (doc.content_text or "").encode("utf-8")
            zf.writestr(md_name, md_bytes)
            entries.append(
                (md_name, hashlib.sha256(md_bytes).hexdigest())
            )

            pdf_bytes = await render_document_pdf(doc.id)
            zf.writestr(pdf_name, pdf_bytes)
            entries.append(
                (pdf_name, hashlib.sha256(pdf_bytes).hexdigest())
            )

        metadata = {
            "project_id": str(project.id),
            "project_name": project.name,
            "selection_mode": "subset" if selected else "all",
            "selected_document_ids": [str(x) for x in (selected or [])],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "document_count": len(docs),
        }
        meta_bytes = json.dumps(metadata, indent=2).encode("utf-8")
        zf.writestr("04-metadata/project.json", meta_bytes)
        entries.append(
            (
                "04-metadata/project.json",
                hashlib.sha256(meta_bytes).hexdigest(),
            )
        )

        readme = _manifest_text(project, entries, metadata["selection_mode"])
        zf.writestr("README.md", readme.encode("utf-8"))

    os.replace(tmp, final)

    size = final.stat().st_size
    h = hashlib.sha256()
    with final.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    update_job_artifact(job.id, final, size, h.hexdigest())
    logger.info("bundle written", extra={"job_id": str(job.id), "size": size})
```

- [ ] **Step 4: Create `src/db.py` session_scope helper**

```python
# services/pdf-renderer/src/db.py
"""Sync SQLAlchemy session scope for the renderer worker.

Uses registry's sync SessionLocal. Worker call sites must wrap these in
asyncio.to_thread when invoked from the async worker loop.
"""
from __future__ import annotations

from contextlib import contextmanager

from registry.database import SessionLocal


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Run test**

```bash
cd services/pdf-renderer && python -m pytest tests/test_bundler.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add services/pdf-renderer/src/bundler.py services/pdf-renderer/src/db.py services/pdf-renderer/tests/test_bundler.py
git commit -m "feat(pdf-renderer): bundler reads from cme_documents + atomic zip writer"
```

---

### Task 2.9: Google Drive client factory + requirements

**Files:**
- Modify: `services/pdf-renderer/requirements.txt`
- Modify: `services/pdf-renderer/Dockerfile`
- Create: `services/pdf-renderer/src/drive_client.py`

Adds Google Drive SDK dependency, mounts the service account credentials file into the container, and provides a `build_drive_client()` factory.

- [ ] **Step 1: Add dependency**

Append to `services/pdf-renderer/requirements.txt`:

```
google-api-python-client==2.141.0
google-auth==2.34.0
```

- [ ] **Step 2: Dockerfile credentials mount point**

No Dockerfile change needed — credentials are mounted as a volume at runtime. Document the expected env var in a comment near the top:

```dockerfile
# Expects GOOGLE_APPLICATION_CREDENTIALS to point at a JSON keyfile mounted
# via docker-compose volume (read-only). Service account must have Drive
# write access to GOOGLE_DRIVE_ROOT_FOLDER_ID.
```

- [ ] **Step 3: Write `drive_client.py`**

```python
"""Google Drive service account client factory."""
from __future__ import annotations

import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive"]


def build_drive_client():
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS not set — Drive sync unavailable"
        )
    creds = service_account.Credentials.from_service_account_file(
        creds_path, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)
```

- [ ] **Step 4: Compose volume mount**

In `docker-compose.override.yml` `dhg-pdf-renderer` service, add:

```yaml
    volumes:
      - dhg_exports:/var/exports:rw
      - ./secrets/drive-service-account.json:/run/secrets/drive-sa.json:ro
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/drive-sa.json
      - GOOGLE_DRIVE_ROOT_FOLDER_ID=${GOOGLE_DRIVE_ROOT_FOLDER_ID}
```

Add `secrets/drive-service-account.json` to `.gitignore` (create if missing) — the real key never enters git.

- [ ] **Step 5: Rebuild and import check**

```bash
docker compose build dhg-pdf-renderer
docker compose up -d dhg-pdf-renderer
docker exec dhg-pdf-renderer python -c "from src.drive_client import SCOPES; print(SCOPES)"
```

Expected: `['https://www.googleapis.com/auth/drive']`.

- [ ] **Step 6: Commit**

```bash
git add services/pdf-renderer/requirements.txt services/pdf-renderer/Dockerfile services/pdf-renderer/src/drive_client.py docker-compose.override.yml .gitignore
git commit -m "feat(pdf-renderer): Google Drive service account client + creds mount"
```

---

### Task 2.10: Drive sync worker action (TDD with mocked Drive)

**Files:**
- Create: `services/pdf-renderer/src/drive_sync.py`
- Create: `services/pdf-renderer/tests/test_drive_sync.py`

`sync_project_to_drive(job)` ensures a project folder exists, renders PDFs for each current document, diffs by MD5, uploads changed files via the service account, and writes `manifest.json`. All Drive calls wrapped in `asyncio.to_thread` because the Google SDK is sync-only.

- [ ] **Step 1: Failing test**

```python
# services/pdf-renderer/tests/test_drive_sync.py
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.drive_sync import sync_project_to_drive


@pytest.mark.asyncio
async def test_drive_sync_creates_folder_and_uploads_changed_docs(
    monkeypatch,
):
    monkeypatch.setenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "root-folder")

    fake_project = MagicMock(
        id="proj-1",
        name="Test Project",
        drive_folder_id=None,
    )
    fake_doc_unchanged = MagicMock(
        id="d-1",
        document_type="needs_assessment",
        drive_file_id="existing-file-id",
        drive_md5=hashlib.md5(b"pdf-A").hexdigest(),
    )
    fake_doc_new = MagicMock(
        id="d-2",
        document_type="research",
        drive_file_id=None,
        drive_md5=None,
    )

    mock_drive = MagicMock()
    mock_drive.files().create().execute.side_effect = [
        {"id": "folder-123"},  # project folder create
        {"id": "file-new-id"},  # doc create
        {"id": "manifest-file-id"},  # manifest create
    ]
    mock_drive.files().list().execute.return_value = {"files": []}

    pdf_calls = iter([b"pdf-A", b"pdf-B"])

    async def fake_render(_doc_id):
        return next(pdf_calls)

    import src.drive_sync as ds

    monkeypatch.setattr(ds, "build_drive_client", lambda: mock_drive)
    monkeypatch.setattr(
        ds, "load_project", MagicMock(return_value=fake_project)
    )
    monkeypatch.setattr(
        ds,
        "load_current_docs",
        MagicMock(return_value=[fake_doc_unchanged, fake_doc_new]),
    )
    monkeypatch.setattr(ds, "render_document_pdf", fake_render)
    monkeypatch.setattr(ds, "persist_project_updates", MagicMock())
    monkeypatch.setattr(ds, "persist_document_sync", MagicMock())

    job = MagicMock(id="job-1", project_id="proj-1")

    await sync_project_to_drive(job)

    # Unchanged doc should not have been re-uploaded
    ds.persist_document_sync.assert_called_once()
    args = ds.persist_document_sync.call_args[0]
    assert args[0] == "d-2"
```

- [ ] **Step 2: Run — verify failure**

```bash
cd services/pdf-renderer && python -m pytest tests/test_drive_sync.py -v
```

- [ ] **Step 3: Implement `drive_sync.py`**

```python
"""Google Drive sync for project documents.

Reconciliation model: manifest.json in the Drive project folder holds the
desired state; we diff against it on each run and only upload documents
whose MD5 has changed. All Google SDK calls are sync — wrapped with
asyncio.to_thread.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from googleapiclient.http import MediaIoBaseUpload

from .bundler import load_current_docs, load_project, render_document_pdf
from .drive_client import build_drive_client

logger = logging.getLogger(__name__)

MANIFEST_NAME = "manifest.json"
FOLDER_MIME = "application/vnd.google-apps.folder"


def persist_project_updates(
    project_id: Any, drive_folder_id: str, status: str
) -> None:
    from .db import session_scope
    from registry.models import CMEProject

    with session_scope() as db:
        p = db.query(CMEProject).filter(CMEProject.id == project_id).first()
        if p is None:
            return
        p.drive_folder_id = drive_folder_id
        p.drive_last_synced_at = datetime.now(timezone.utc)
        p.drive_sync_status = status
        db.commit()


def persist_document_sync(
    document_id: Any, drive_file_id: str, md5: str
) -> None:
    from .db import session_scope
    from registry.models import CMEDocument

    with session_scope() as db:
        d = (
            db.query(CMEDocument)
            .filter(CMEDocument.id == document_id)
            .first()
        )
        if d is None:
            return
        d.drive_file_id = drive_file_id
        d.drive_md5 = md5
        d.drive_synced_at = datetime.now(timezone.utc)
        db.commit()


async def sync_project_to_drive(job: Any) -> None:
    root_folder_id = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID")
    if not root_folder_id:
        raise RuntimeError("GOOGLE_DRIVE_ROOT_FOLDER_ID not configured")

    drive = build_drive_client()
    project = load_project(job.project_id)
    if project is None:
        raise RuntimeError(f"project {job.project_id} not found")

    folder_id = project.drive_folder_id
    if not folder_id:
        meta = await asyncio.to_thread(
            lambda: drive.files()
            .create(
                body={
                    "name": f"{project.name} ({project.id})",
                    "mimeType": FOLDER_MIME,
                    "parents": [root_folder_id],
                },
                fields="id",
            )
            .execute()
        )
        folder_id = meta["id"]

    existing = await asyncio.to_thread(
        lambda: drive.files()
        .list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, md5Checksum)",
        )
        .execute()
    )
    existing_by_name = {
        f["name"]: f for f in existing.get("files", [])
    }

    docs = load_current_docs(job.project_id, None)
    manifest_entries = []

    for i, doc in enumerate(docs, start=1):
        pdf_name = f"{i:02d}-{doc.document_type}.pdf"
        pdf_bytes = await render_document_pdf(doc.id)
        pdf_md5 = hashlib.md5(pdf_bytes).hexdigest()

        manifest_entries.append(
            {
                "document_id": str(doc.id),
                "name": pdf_name,
                "md5": pdf_md5,
            }
        )

        if doc.drive_md5 == pdf_md5 and doc.drive_file_id:
            continue

        media = MediaIoBaseUpload(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            resumable=False,
        )
        if pdf_name in existing_by_name:
            file_id = existing_by_name[pdf_name]["id"]
            await asyncio.to_thread(
                lambda: drive.files()
                .update(fileId=file_id, media_body=media)
                .execute()
            )
        else:
            res = await asyncio.to_thread(
                lambda: drive.files()
                .create(
                    body={"name": pdf_name, "parents": [folder_id]},
                    media_body=media,
                    fields="id",
                )
                .execute()
            )
            file_id = res["id"]
        persist_document_sync(doc.id, file_id, pdf_md5)

    manifest = {
        "project_id": str(project.id),
        "project_name": project.name,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "documents": manifest_entries,
    }
    manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
    manifest_media = MediaIoBaseUpload(
        io.BytesIO(manifest_bytes),
        mimetype="application/json",
        resumable=False,
    )
    if MANIFEST_NAME in existing_by_name:
        await asyncio.to_thread(
            lambda: drive.files()
            .update(
                fileId=existing_by_name[MANIFEST_NAME]["id"],
                media_body=manifest_media,
            )
            .execute()
        )
    else:
        await asyncio.to_thread(
            lambda: drive.files()
            .create(
                body={"name": MANIFEST_NAME, "parents": [folder_id]},
                media_body=manifest_media,
                fields="id",
            )
            .execute()
        )

    persist_project_updates(project.id, folder_id, "ok")
    logger.info(
        "drive sync done",
        extra={
            "project_id": str(project.id),
            "document_count": len(docs),
            "folder_id": folder_id,
        },
    )
```

- [ ] **Step 4: Run test — expect pass**

```bash
cd services/pdf-renderer && python -m pytest tests/test_drive_sync.py -v
```

- [ ] **Step 5: Commit**

```bash
git add services/pdf-renderer/src/drive_sync.py services/pdf-renderer/tests/test_drive_sync.py
git commit -m "feat(pdf-renderer): Drive sync with manifest.json reconciliation"
```

---

### Task 2.11: Worker loop with `FOR UPDATE` + three scopes

**Files:**
- Create: `services/pdf-renderer/src/worker.py`
- Modify: `services/pdf-renderer/src/main.py` (lifespan hook)
- Create: `services/pdf-renderer/tests/test_worker_claim.py`

Plain `FOR UPDATE` (no SKIP LOCKED — single-replica deployment). Dispatches based on `job.scope`.

- [ ] **Step 1: Claim test**

```python
# services/pdf-renderer/tests/test_worker_claim.py
from unittest.mock import MagicMock

import pytest

from src.worker import claim_next_job_sync


def test_claim_ignores_non_pending(monkeypatch):
    fake_db = MagicMock()
    fake_result = MagicMock()
    fake_result.fetchone.return_value = None
    fake_db.execute.return_value = fake_result
    job = claim_next_job_sync(fake_db)
    assert job is None
    # Verify SQL uses FOR UPDATE (not SKIP LOCKED)
    sql = fake_db.execute.call_args[0][0].text
    assert "FOR UPDATE" in sql
    assert "SKIP LOCKED" not in sql
```

- [ ] **Step 2: Implement**

```python
"""Worker loop: claims pending download_jobs and dispatches by scope.

Single-replica deployment — plain FOR UPDATE. If we ever run multiple
renderer replicas, swap in SKIP LOCKED.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from .bundler import assemble_bundle
from .db import session_scope
from .drive_sync import sync_project_to_drive

logger = logging.getLogger(__name__)

_CLAIM_SQL = text(
    """
    SELECT id, scope, project_id, thread_id, graph_id,
           selected_document_ids, created_by
      FROM download_jobs
     WHERE status = 'pending'
       AND scope IN ('project_bundle', 'drive_sync')
     ORDER BY created_at
     LIMIT 1
     FOR UPDATE
    """
)


def claim_next_job_sync(db) -> Any | None:
    result = db.execute(_CLAIM_SQL)
    row = result.fetchone()
    if row is None:
        return None
    db.execute(
        text(
            "UPDATE download_jobs SET status='running', started_at=now() "
            "WHERE id=:id"
        ),
        {"id": row.id},
    )
    db.commit()
    return row


def mark_completed_sync(db, job_id: Any) -> None:
    db.execute(
        text(
            "UPDATE download_jobs SET status='succeeded', completed_at=now() "
            "WHERE id=:id"
        ),
        {"id": job_id},
    )
    db.commit()


def mark_failed_sync(db, job_id: Any, error: str) -> None:
    db.execute(
        text(
            "UPDATE download_jobs "
            "SET status='failed', completed_at=now(), error=:error "
            "WHERE id=:id"
        ),
        {"id": job_id, "error": error[:2000]},
    )
    db.commit()


async def _claim() -> Any | None:
    def _inner():
        with session_scope() as db:
            return claim_next_job_sync(db)

    return await asyncio.to_thread(_inner)


async def run_worker(stop_event: asyncio.Event) -> None:
    logger.info("worker loop started")
    while not stop_event.is_set():
        job = await _claim()
        if job is None:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                pass
            continue

        logger.info(
            "claimed job",
            extra={"job_id": str(job.id), "scope": job.scope},
        )
        try:
            if job.scope == "project_bundle":
                await assemble_bundle(job)
            elif job.scope == "drive_sync":
                await sync_project_to_drive(job)
            else:
                raise RuntimeError(f"unsupported scope {job.scope}")

            def _ok():
                with session_scope() as db:
                    mark_completed_sync(db, job.id)

            await asyncio.to_thread(_ok)
        except Exception as exc:
            logger.exception("job failed", extra={"job_id": str(job.id)})

            def _fail():
                with session_scope() as db:
                    mark_failed_sync(db, job.id, str(exc))

            await asyncio.to_thread(_fail)
```

- [ ] **Step 3: Wire into FastAPI lifespan**

In `services/pdf-renderer/src/main.py`:

```python
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from .worker import run_worker

_worker_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_task, _stop_event
    _stop_event = asyncio.Event()
    _worker_task = asyncio.create_task(run_worker(_stop_event))
    try:
        yield
    finally:
        _stop_event.set()
        if _worker_task:
            try:
                await asyncio.wait_for(_worker_task, timeout=10.0)
            except asyncio.TimeoutError:
                _worker_task.cancel()


app = FastAPI(lifespan=lifespan)
# ... existing route registrations ...
```

- [ ] **Step 4: Run tests**

```bash
cd services/pdf-renderer && python -m pytest tests/test_worker_claim.py -v
```

- [ ] **Step 5: Rebuild + smoke**

```bash
docker compose build dhg-pdf-renderer
docker compose up -d dhg-pdf-renderer
docker logs dhg-pdf-renderer 2>&1 | grep "worker loop started"
```

Expected: log contains `worker loop started`.

- [ ] **Step 6: Commit**

```bash
git add services/pdf-renderer/src/worker.py services/pdf-renderer/src/main.py services/pdf-renderer/tests/test_worker_claim.py
git commit -m "feat(pdf-renderer): worker loop with FOR UPDATE + bundle/drive_sync dispatch"
```

---

### Task 2.12: Orchestrator `enqueue_drive_sync` + milestone call sites

**Files:**
- Create: `langgraph_workflows/dhg-agents-cloud/src/drive_sync_hook.py`
- Modify: `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py`

Provides a helper that inserts a `drive_sync` row into `download_jobs`, with dedup (skip if an existing `pending`/`running` row for the same `project_id` exists). Wired to three milestone points: after each content-agent pass, after a human review decision resumes, after compliance passes.

- [ ] **Step 1: Write the helper**

```python
"""Enqueue drive_sync jobs at pipeline milestones.

Dedup: if a pending or running drive_sync job already exists for the
project, do not insert another. This absorbs bursts of near-simultaneous
milestones (e.g. parallel research + clinical finishing within ms of
each other) into a single sync.
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _db_session() -> Session:
    from registry.database import SessionLocal

    return SessionLocal()


@contextmanager
def _session():
    db = _db_session()
    try:
        yield db
    finally:
        db.close()


def enqueue_drive_sync(project_id: str) -> bool:
    """Insert a drive_sync job row unless one is already pending/running.

    Returns True if a new row was inserted.
    """
    if os.getenv("DRIVE_SYNC_DISABLED") == "1":
        return False
    with _session() as db:
        existing = db.execute(
            text(
                "SELECT id FROM download_jobs "
                "WHERE project_id = :pid AND scope = 'drive_sync' "
                "  AND status IN ('pending', 'running') "
                "LIMIT 1"
            ),
            {"pid": project_id},
        ).first()
        if existing:
            logger.debug(
                "drive_sync dedup",
                extra={"project_id": project_id, "existing_id": str(existing.id)},
            )
            return False

        db.execute(
            text(
                "INSERT INTO download_jobs "
                "  (thread_id, graph_id, scope, status, project_id) "
                "VALUES ('', 'drive_sync', 'drive_sync', 'pending', :pid)"
            ),
            {"pid": project_id},
        )
        db.commit()
        logger.info(
            "drive_sync enqueued", extra={"project_id": project_id}
        )
        return True
```

- [ ] **Step 2: Call sites in `orchestrator.py`**

Identify the three milestone points. For each, import and call the helper with the project_id resolved from thread state. Example pattern:

```python
from .drive_sync_hook import enqueue_drive_sync

# After a content agent node finishes:
def _on_content_agent_complete(state):
    project_id = state.get("project_id")
    if project_id:
        try:
            enqueue_drive_sync(project_id)
        except Exception:
            logger.exception("drive_sync enqueue failed (non-fatal)")
    return state
```

The exact insertion points are: the end of each agent sub-graph in `orchestrator.py`, the human-review resume handler, and the compliance-review finalization. Resolve `project_id` from `state["project_id"]` — orchestrator state already carries it.

- [ ] **Step 3: Smoke test — manual enqueue via psql**

```bash
docker exec dhg-registry-db psql -U dhg -d dhg_registry -c \
  "INSERT INTO download_jobs (thread_id, graph_id, scope, status, project_id) \
   VALUES ('', 'drive_sync', 'drive_sync', 'pending', (SELECT id FROM cme_projects LIMIT 1));"
sleep 3
docker exec dhg-registry-db psql -U dhg -d dhg_registry -c \
  "SELECT id, status, error FROM download_jobs WHERE scope='drive_sync' ORDER BY created_at DESC LIMIT 1;"
```

Expected: job transitions to `succeeded` (or `failed` with a clear error if Drive credentials aren't wired yet — acceptable at this checkpoint).

- [ ] **Step 4: Commit**

```bash
git add langgraph_workflows/dhg-agents-cloud/src/drive_sync_hook.py langgraph_workflows/dhg-agents-cloud/src/orchestrator.py
git commit -m "feat(orchestrator): enqueue_drive_sync helper + milestone call sites"
```

---

### Task 2.13: Frontend `filesApi.ts` client

**Files:**
- Create: `frontend/src/lib/filesApi.ts`

Typed fetch wrappers for the new project + bundle endpoints. Uses the existing `/api/registry` proxy route which forwards Cloudflare JWT.

- [ ] **Step 1: Write the client**

```typescript
// frontend/src/lib/filesApi.ts
export interface ProjectListItem {
  id: string;
  name: string;
  status: string;
  kind: string | null;
  document_count: number;
  last_activity_at: string | null;
  drive_folder_id: string | null;
}

export interface ProjectListResponse {
  projects: ProjectListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProjectDocumentItem {
  id: string;
  document_type: string;
  title: string | null;
  word_count: number | null;
  version: number;
  is_current: boolean;
  created_at: string;
  drive_file_id: string | null;
}

export interface ProjectDocumentsResponse {
  project_id: string;
  documents: ProjectDocumentItem[];
}

export interface BundleJobResponse {
  id: string;
  project_id: string | null;
  scope: "document" | "project_bundle" | "drive_sync";
  status: "pending" | "running" | "succeeded" | "failed";
  selected_document_ids: string[] | null;
  created_at: string;
  completed_at: string | null;
  artifact_bytes: number | null;
  error: string | null;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export async function listProjects(params: {
  search?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<ProjectListResponse> {
  const qs = new URLSearchParams();
  if (params.search) qs.set("search", params.search);
  if (params.status) qs.set("status", params.status);
  qs.set("limit", String(params.limit ?? 50));
  qs.set("offset", String(params.offset ?? 0));
  return json<ProjectListResponse>(
    await fetch(`/api/registry/api/cme/export/projects?${qs.toString()}`),
  );
}

export async function listProjectDocuments(
  projectId: string,
): Promise<ProjectDocumentsResponse> {
  return json<ProjectDocumentsResponse>(
    await fetch(`/api/registry/api/cme/export/projects/${projectId}/documents`),
  );
}

export async function createBundleJob(body: {
  project_id: string;
  document_ids: string[] | null;
  include_manifest: boolean;
  include_intake: boolean;
}): Promise<BundleJobResponse> {
  return json<BundleJobResponse>(
    await fetch(`/api/registry/api/cme/export/bundle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function getJob(jobId: string): Promise<BundleJobResponse> {
  return json<BundleJobResponse>(
    await fetch(`/api/registry/api/cme/export/job/${jobId}`),
  );
}

export async function listJobs(limit = 20): Promise<BundleJobResponse[]> {
  return json<BundleJobResponse[]>(
    await fetch(`/api/registry/api/cme/export/jobs?limit=${limit}`),
  );
}

export function artifactUrl(jobId: string): string {
  return `/api/registry/api/cme/export/artifact/${jobId}`;
}
```

- [ ] **Step 2: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/filesApi.ts
git commit -m "feat(frontend): filesApi client for projects + bundle jobs"
```

---

### Task 2.14: Files tab Zustand store

**Files:**
- Create: `frontend/src/stores/files-tab-store.ts`

Holds project list, expanded-project set, selection set, search query, preview doc id. Persists only `expandedProjectIds` (selection + preview are ephemeral).

- [ ] **Step 1: Write the store**

```typescript
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type {
  ProjectDocumentItem,
  ProjectListItem,
} from "@/lib/filesApi";

interface FilesTabState {
  projects: ProjectListItem[];
  documentsByProject: Record<string, ProjectDocumentItem[]>;
  expandedProjectIds: string[];
  selectedDocumentIds: string[];
  selectedProjectId: string | null;
  searchQuery: string;
  previewDocumentId: string | null;

  setProjects: (projects: ProjectListItem[]) => void;
  setDocuments: (projectId: string, docs: ProjectDocumentItem[]) => void;
  toggleProjectExpanded: (id: string) => void;
  toggleDocumentSelected: (projectId: string, documentId: string) => void;
  clearSelection: () => void;
  setPreview: (documentId: string | null) => void;
  setSearch: (q: string) => void;
}

export const useFilesTabStore = create<FilesTabState>()(
  persist(
    (set, get) => ({
      projects: [],
      documentsByProject: {},
      expandedProjectIds: [],
      selectedDocumentIds: [],
      selectedProjectId: null,
      searchQuery: "",
      previewDocumentId: null,

      setProjects: (projects) => set({ projects }),
      setDocuments: (projectId, docs) =>
        set((s) => ({
          documentsByProject: { ...s.documentsByProject, [projectId]: docs },
        })),
      toggleProjectExpanded: (id) =>
        set((s) => ({
          expandedProjectIds: s.expandedProjectIds.includes(id)
            ? s.expandedProjectIds.filter((x) => x !== id)
            : [...s.expandedProjectIds, id],
        })),
      toggleDocumentSelected: (projectId, documentId) => {
        const s = get();
        const currentProject = s.selectedProjectId;
        if (currentProject && currentProject !== projectId) {
          set({
            selectedDocumentIds: [documentId],
            selectedProjectId: projectId,
          });
          return;
        }
        const selected = s.selectedDocumentIds.includes(documentId)
          ? s.selectedDocumentIds.filter((x) => x !== documentId)
          : [...s.selectedDocumentIds, documentId];
        set({
          selectedDocumentIds: selected,
          selectedProjectId: selected.length ? projectId : null,
        });
      },
      clearSelection: () =>
        set({ selectedDocumentIds: [], selectedProjectId: null }),
      setPreview: (documentId) => set({ previewDocumentId: documentId }),
      setSearch: (q) => set({ searchQuery: q }),
    }),
    {
      name: "files-tab-store",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ expandedProjectIds: s.expandedProjectIds }),
    },
  ),
);
```

- [ ] **Step 2: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/files-tab-store.ts
git commit -m "feat(frontend): files-tab-store with selection + expansion state"
```

---

### Task 2.15: Files tab UI components

**Files:**
- Create: `frontend/src/components/inbox/files-tab.tsx`
- Create: `frontend/src/components/inbox/files-tree.tsx`
- Create: `frontend/src/components/inbox/files-selection-bar.tsx`

Two-click interaction: row click previews, checkbox toggles selection. Selection bar at bottom shows count + Download button. Selection across projects is prevented.

- [ ] **Step 1: `files-selection-bar.tsx`**

```tsx
"use client";

import { useFilesTabStore } from "@/stores/files-tab-store";
import { Button } from "@/components/ui/button";
import { createBundleJob } from "@/lib/filesApi";
import { useDownloadsStore } from "@/stores/downloads-store";

export function FilesSelectionBar() {
  const { selectedDocumentIds, selectedProjectId, clearSelection } =
    useFilesTabStore();
  const upsertJob = useDownloadsStore((s) => s.upsertJob);

  async function onDownload() {
    if (!selectedProjectId || selectedDocumentIds.length === 0) return;
    const job = await createBundleJob({
      project_id: selectedProjectId,
      document_ids: selectedDocumentIds,
      include_manifest: true,
      include_intake: false,
    });
    upsertJob(job);
    clearSelection();
  }

  if (selectedDocumentIds.length === 0) return null;

  return (
    <div className="flex items-center justify-between border-t border-border bg-surface px-4 py-2">
      <span className="text-sm text-text-secondary">
        {selectedDocumentIds.length} selected
      </span>
      <Button size="sm" onClick={onDownload}>
        Download zip
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: `files-tree.tsx`**

```tsx
"use client";

import { useEffect } from "react";
import { ChevronRight, ChevronDown } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { useFilesTabStore } from "@/stores/files-tab-store";
import { listProjectDocuments } from "@/lib/filesApi";

export function FilesTree() {
  const {
    projects,
    documentsByProject,
    expandedProjectIds,
    selectedDocumentIds,
    toggleProjectExpanded,
    toggleDocumentSelected,
    setDocuments,
    setPreview,
  } = useFilesTabStore();

  useEffect(() => {
    expandedProjectIds.forEach(async (pid) => {
      if (!documentsByProject[pid]) {
        const res = await listProjectDocuments(pid);
        setDocuments(pid, res.documents);
      }
    });
  }, [expandedProjectIds, documentsByProject, setDocuments]);

  return (
    <ul className="flex-1 overflow-y-auto">
      {projects.map((project) => {
        const expanded = expandedProjectIds.includes(project.id);
        const docs = documentsByProject[project.id] ?? [];
        return (
          <li key={project.id} className="border-b border-border">
            <button
              type="button"
              onClick={() => toggleProjectExpanded(project.id)}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted"
            >
              {expanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              <span className="flex-1 truncate">{project.name}</span>
              <span className="text-xs text-text-secondary">
                {project.document_count} docs
              </span>
            </button>
            {expanded && (
              <ul className="bg-background">
                {docs.map((doc, i) => {
                  const checked = selectedDocumentIds.includes(doc.id);
                  return (
                    <li
                      key={doc.id}
                      className="flex items-center gap-2 px-6 py-1.5 text-xs hover:bg-muted"
                    >
                      <Checkbox
                        checked={checked}
                        onCheckedChange={() =>
                          toggleDocumentSelected(project.id, doc.id)
                        }
                      />
                      <button
                        type="button"
                        onClick={() => setPreview(doc.id)}
                        className="flex-1 truncate text-left"
                      >
                        <span className="mr-2 text-text-secondary">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        {doc.title ?? doc.document_type}
                      </button>
                      <span className="text-text-secondary">
                        {doc.word_count ?? "—"}w
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </li>
        );
      })}
    </ul>
  );
}
```

- [ ] **Step 3: `files-tab.tsx`**

```tsx
"use client";

import { useEffect } from "react";
import { Input } from "@/components/ui/input";
import { listProjects } from "@/lib/filesApi";
import { useFilesTabStore } from "@/stores/files-tab-store";
import { FilesTree } from "./files-tree";
import { FilesSelectionBar } from "./files-selection-bar";

export function FilesTab() {
  const { searchQuery, setSearch, setProjects } = useFilesTabStore();

  useEffect(() => {
    const t = setTimeout(async () => {
      const res = await listProjects({
        search: searchQuery || undefined,
        limit: 50,
      });
      setProjects(res.projects);
    }, 200);
    return () => clearTimeout(t);
  }, [searchQuery, setProjects]);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border p-2">
        <Input
          placeholder="Search projects..."
          value={searchQuery}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <FilesTree />
      <FilesSelectionBar />
    </div>
  );
}
```

- [ ] **Step 4: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/inbox/files-tab.tsx frontend/src/components/inbox/files-tree.tsx frontend/src/components/inbox/files-selection-bar.tsx
git commit -m "feat(frontend): Files tab UI with project tree + multi-select + download bar"
```

---

### Task 2.16: Wire Files tab into inbox left sidebar

**Files:**
- Modify: `frontend/src/components/review/inbox-master-detail.tsx`

Adds shadcn `Tabs` (underline variant) above the existing review list. `Reviews` tab = existing content; `Files` tab = `<FilesTab />`.

- [ ] **Step 1: Add tabs wrapper**

Locate the left sidebar JSX in `inbox-master-detail.tsx`. Wrap its existing contents in a `Tabs` component:

```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FilesTab } from "@/components/inbox/files-tab";

// ...inside the left panel JSX:
<Tabs defaultValue="reviews" className="flex h-full flex-col">
  <TabsList className="rounded-none border-b border-border bg-transparent p-0">
    <TabsTrigger
      value="reviews"
      className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary"
    >
      Reviews
    </TabsTrigger>
    <TabsTrigger
      value="files"
      className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary"
    >
      Files
    </TabsTrigger>
  </TabsList>
  <TabsContent value="reviews" className="flex-1 overflow-hidden">
    {/* existing reviews list content */}
  </TabsContent>
  <TabsContent value="files" className="flex-1 overflow-hidden">
    <FilesTab />
  </TabsContent>
</Tabs>
```

- [ ] **Step 2: Verify shadcn `tabs` is installed**

```bash
cd frontend && ls src/components/ui/tabs.tsx 2>&1
```

If missing: `npx shadcn@latest add tabs`.

- [ ] **Step 3: Typecheck + dev server smoke**

```bash
cd frontend && npx tsc --noEmit
```

Then open `/inbox` in the browser, verify the tabs render, click Files → tree loads projects from the real DB.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/review/inbox-master-detail.tsx frontend/src/components/ui/tabs.tsx
git commit -m "feat(inbox): add Files tab to left sidebar with Reviews | Files underline tabs"
```

---

### Task 2.17: Downloads store + polling hook + tray

**Files:**
- Create: `frontend/src/stores/downloads-store.ts`
- Create: `frontend/src/hooks/use-download-polling.ts`
- Create: `frontend/src/components/downloads/downloads-tray.tsx`
- Modify: `frontend/src/components/layout/app-shell.tsx` (mount tray)

Zustand store holds recent jobs, polling hook polls `GET /jobs` every 3s only while at least one job is `pending`/`running`, tray is a shadcn `Sheet` listing rows with an appropriate action per scope.

- [ ] **Step 1: Store**

```typescript
// frontend/src/stores/downloads-store.ts
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { BundleJobResponse } from "@/lib/filesApi";

interface DownloadsState {
  jobs: BundleJobResponse[];
  trayOpen: boolean;
  setJobs: (jobs: BundleJobResponse[]) => void;
  upsertJob: (job: BundleJobResponse) => void;
  openTray: () => void;
  closeTray: () => void;
  toggleTray: () => void;
}

export const useDownloadsStore = create<DownloadsState>()(
  persist(
    (set) => ({
      jobs: [],
      trayOpen: false,
      setJobs: (jobs) => set({ jobs }),
      upsertJob: (job) =>
        set((s) => {
          const idx = s.jobs.findIndex((j) => j.id === job.id);
          if (idx === -1) return { jobs: [job, ...s.jobs] };
          const next = [...s.jobs];
          next[idx] = job;
          return { jobs: next };
        }),
      openTray: () => set({ trayOpen: true }),
      closeTray: () => set({ trayOpen: false }),
      toggleTray: () => set((s) => ({ trayOpen: !s.trayOpen })),
    }),
    {
      name: "downloads-store",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ jobs: s.jobs }),
    },
  ),
);
```

- [ ] **Step 2: Polling hook**

```typescript
// frontend/src/hooks/use-download-polling.ts
"use client";
import { useEffect } from "react";
import { listJobs } from "@/lib/filesApi";
import { useDownloadsStore } from "@/stores/downloads-store";

export function useDownloadPolling() {
  const { jobs, setJobs } = useDownloadsStore();
  useEffect(() => {
    const hasActive = jobs.some(
      (j) => j.status === "pending" || j.status === "running",
    );
    if (!hasActive) return;
    const id = window.setInterval(async () => {
      const fresh = await listJobs(20);
      setJobs(fresh);
    }, 3000);
    return () => window.clearInterval(id);
  }, [jobs, setJobs]);
}
```

- [ ] **Step 3: Tray component**

```tsx
// frontend/src/components/downloads/downloads-tray.tsx
"use client";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Download, Cloud, FileArchive, AlertTriangle } from "lucide-react";
import { useDownloadsStore } from "@/stores/downloads-store";
import { useDownloadPolling } from "@/hooks/use-download-polling";
import { artifactUrl, type BundleJobResponse } from "@/lib/filesApi";

function Row({ job }: { job: BundleJobResponse }) {
  const icon =
    job.scope === "drive_sync" ? (
      <Cloud className="h-4 w-4" />
    ) : (
      <FileArchive className="h-4 w-4" />
    );
  const statusLabel =
    job.status === "succeeded" ? "Done" : job.status === "failed" ? "Failed" : job.status;

  return (
    <li className="flex items-center gap-3 border-b border-border px-4 py-3">
      {icon}
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm">
          {job.scope === "drive_sync" ? "Drive sync" : "Project bundle"}
        </div>
        <div className="text-xs text-text-secondary">
          {statusLabel}
          {job.error ? ` — ${job.error}` : ""}
        </div>
      </div>
      {job.scope !== "drive_sync" && job.status === "succeeded" && (
        <a
          href={artifactUrl(job.id)}
          className="text-xs text-primary hover:underline"
          download
        >
          <Download className="mr-1 inline h-3 w-3" />
          Download
        </a>
      )}
      {job.status === "failed" && <AlertTriangle className="h-4 w-4 text-destructive" />}
    </li>
  );
}

export function DownloadsTray() {
  const { trayOpen, closeTray, jobs } = useDownloadsStore();
  useDownloadPolling();

  return (
    <Sheet open={trayOpen} onOpenChange={(o) => !o && closeTray()}>
      <SheetContent side="right" className="w-96 p-0">
        <SheetHeader className="border-b border-border px-4 py-3">
          <SheetTitle>Downloads</SheetTitle>
        </SheetHeader>
        <ul className="divide-y divide-border">
          {jobs.map((j) => (
            <Row key={j.id} job={j} />
          ))}
          {jobs.length === 0 && (
            <li className="px-4 py-6 text-center text-sm text-text-secondary">
              No recent downloads
            </li>
          )}
        </ul>
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 4: Mount tray + trigger in `app-shell.tsx`**

Add a `<DownloadsTray />` render at the top level of the shell, plus a button in the header that calls `toggleTray()`.

- [ ] **Step 5: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/stores/downloads-store.ts frontend/src/hooks/use-download-polling.ts frontend/src/components/downloads/downloads-tray.tsx frontend/src/components/layout/app-shell.tsx
git commit -m "feat(frontend): downloads tray with polling + bundle/drive_sync rows"
```

---

### Task 2.18: End-to-end integration test

**Files:**
- Create: `frontend/e2e/inbox-files-tab-download.spec.ts`

Playwright e2e: open `/inbox`, click Files tab, expand a project, check 2 documents, click Download zip, wait for job to complete via tray polling, download the artifact, assert it's a valid zip with the expected files.

- [ ] **Step 1: Write the test**

```typescript
import { test, expect } from "@playwright/test";

const REGISTRY_URL = process.env.REGISTRY_URL ?? "http://localhost:8011";

test("files tab can select and download a project bundle", async ({
  page,
  request,
}) => {
  // Preflight: ensure the API has at least one project with documents
  const listRes = await request.get(
    `${REGISTRY_URL}/api/cme/export/projects?limit=1`,
    { timeout: 15_000 },
  );
  expect(listRes.status()).toBe(200);
  const projects = (await listRes.json()).projects;
  test.skip(projects.length === 0, "no projects in DB");

  await page.goto("/inbox");
  await page.getByRole("tab", { name: /files/i }).click();

  const firstProject = page.locator("button", { hasText: projects[0].name }).first();
  await expect(firstProject).toBeVisible({ timeout: 10_000 });
  await firstProject.click();

  const checkboxes = page.getByRole("checkbox");
  await expect(checkboxes.first()).toBeVisible();
  const count = await checkboxes.count();
  const picks = Math.min(2, count);
  for (let i = 0; i < picks; i++) {
    await checkboxes.nth(i).click();
  }

  await page.getByRole("button", { name: /download zip/i }).click();

  // Tray should show a running then succeeded row
  await expect(page.getByText(/project bundle/i).first()).toBeVisible({
    timeout: 15_000,
  });

  const downloadLink = page.locator("a", { hasText: /download/i }).first();
  await expect(downloadLink).toBeVisible({ timeout: 120_000 });

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    downloadLink.click(),
  ]);
  const path = await download.path();
  expect(path).toBeTruthy();

  const fs = await import("node:fs");
  const buf = fs.readFileSync(path!);
  // Zip magic number
  expect(buf.subarray(0, 2).toString()).toBe("PK");
  expect(buf.length).toBeGreaterThan(2048);
});
```

- [ ] **Step 2: Run**

```bash
cd frontend && npx playwright test e2e/inbox-files-tab-download.spec.ts
```

Expected: pass end-to-end (or skipped if DB has no projects — acceptable at this checkpoint).

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/inbox-files-tab-download.spec.ts
git commit -m "test(e2e): inbox Files tab selection + bundle download round-trip"
```

---

### Task 2.19: Phase 2 v2 smoke + tag

**Files:** none (bookkeeping)

- [ ] **Step 1: Drive-sync smoke (manual trigger)**

```bash
docker exec dhg-registry-db psql -U dhg -d dhg_registry -c \
  "INSERT INTO download_jobs (thread_id, graph_id, scope, status, project_id) \
   VALUES ('', 'drive_sync', 'drive_sync', 'pending', (SELECT id FROM cme_projects LIMIT 1));"
sleep 10
docker exec dhg-registry-db psql -U dhg -d dhg_registry -c \
  "SELECT id, status, completed_at, error FROM download_jobs \
   WHERE scope='drive_sync' ORDER BY created_at DESC LIMIT 1;"
```

Expected: status=`succeeded`. If Drive creds aren't yet provisioned on the host, expected: status=`failed` with a clear credentials error — this is acceptable only if credentials are scheduled for the next deploy window.

- [ ] **Step 2: Bundle smoke (via UI)**

Open `/inbox`, click Files tab, expand a project, select 1+ docs, click Download zip, wait for tray, download the zip, unzip it locally:

```bash
unzip -l /tmp/bundle.zip
```

Expected output: README.md, 01-documents/*.md + *.pdf, 04-metadata/project.json.

- [ ] **Step 3: Tag**

```bash
git tag phase2-v2-complete
git log --oneline phase1-complete..phase2-v2-complete | head -30
```

- [ ] **Step 4: Commit (if any bookkeeping files changed)**

Usually nothing to commit here — the tag is the artifact.

---

## Phase 3 — Quality / Review History / Citations + chart-ready wait

Goal: Extend the bundle so auditors can see WHY a document was approved. Adds three new source readers, three print routes, and one Tremor chart rendered inside headless Chromium. Also introduces the `data-loading` attribute convention so future chart wrappers integrate cleanly.

---

### Task 3.1: Source reader — `quality.py`

**Files:**
- Create: `registry/export_sources/__init__.py`
- Create: `registry/export_sources/quality.py`
- Create: `registry/test_export_sources_quality.py`

- [ ] **Step 1: Write the failing test**

```python
# registry/test_export_sources_quality.py
from unittest.mock import AsyncMock, patch

import pytest

from registry.export_sources.quality import load_quality_for_thread


@pytest.mark.asyncio
async def test_load_quality_shape() -> None:
    fake = {
        "prose_quality_agent": {
            "score": 87,
            "banned_patterns": [{"pattern": "leverage", "count": 2}],
            "history": [{"round": 0, "score": 72}, {"round": 1, "score": 87}],
        }
    }
    with patch(
        "registry.export_sources.quality._fetch_latest_outputs",
        new=AsyncMock(return_value=fake),
    ):
        q = await load_quality_for_thread("t-1")
    assert q is not None
    assert q["score"] == 87
    assert q["history"][-1]["score"] == 87
    assert q["banned_patterns"][0]["pattern"] == "leverage"
```

- [ ] **Step 2: Implement**

```python
# registry/export_sources/__init__.py
"""Data readers used by the export bundler."""
```

```python
# registry/export_sources/quality.py
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from database import async_session
from models import CMEProject


async def _fetch_latest_outputs(thread_id: str) -> dict[str, Any] | None:
    async with async_session() as session:
        row = (
            await session.execute(
                select(CMEProject).where(CMEProject.pipeline_thread_id == thread_id).limit(1)
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return row.outputs or {}


async def load_quality_for_thread(thread_id: str) -> dict[str, Any] | None:
    outputs = await _fetch_latest_outputs(thread_id)
    if not outputs:
        return None
    prose = outputs.get("prose_quality_agent") or {}
    return {
        "score": prose.get("score"),
        "banned_patterns": prose.get("banned_patterns", []),
        "history": prose.get("history", []),
    }
```

- [ ] **Step 3: Run — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_sources_quality.py -v
```

- [ ] **Step 4: Commit**

```bash
git add registry/export_sources/__init__.py registry/export_sources/quality.py \
        registry/test_export_sources_quality.py
git commit -m "feat(export): quality source reader"
```

---

### Task 3.2: Source reader — `review_history.py`

**Files:**
- Create: `registry/export_sources/review_history.py`

- [ ] **Step 1: Implement**

```python
# registry/export_sources/review_history.py
from __future__ import annotations

from typing import Any

from registry.export_sources.quality import _fetch_latest_outputs


async def load_review_history_for_thread(thread_id: str) -> list[dict[str, Any]]:
    outputs = await _fetch_latest_outputs(thread_id)
    if not outputs:
        return []
    rounds = outputs.get("review_rounds") or []
    history: list[dict[str, Any]] = []
    for i, rnd in enumerate(rounds):
        history.append(
            {
                "round": i,
                "decision": rnd.get("decision"),
                "decided_at": rnd.get("decided_at"),
                "reviewer": rnd.get("reviewer"),
                "notes": rnd.get("notes", ""),
            }
        )
    return history
```

- [ ] **Step 2: Commit**

```bash
git add registry/export_sources/review_history.py
git commit -m "feat(export): review history source reader"
```

---

### Task 3.3: Source reader — `citations.py`

**Files:**
- Create: `registry/export_sources/citations.py`

- [ ] **Step 1: Implement**

```python
# registry/export_sources/citations.py
from __future__ import annotations

from typing import Any

from registry.export_sources.quality import _fetch_latest_outputs


async def load_citations_for_thread(thread_id: str) -> list[dict[str, Any]]:
    outputs = await _fetch_latest_outputs(thread_id)
    if not outputs:
        return []
    checker = outputs.get("citation_checker_agent") or {}
    return list(checker.get("citations", []))
```

- [ ] **Step 2: Commit**

```bash
git add registry/export_sources/citations.py
git commit -m "feat(export): citations source reader"
```

---

### Task 3.4: Chart-ready wait attribute on `daily-chart.tsx`

**Files:**
- Modify: `frontend/src/components/monitoring/daily-chart.tsx`

- [ ] **Step 1: Add `data-loading` to the wrapper**

```typescript
// frontend/src/components/monitoring/daily-chart.tsx
// Wrap both the skeleton path and the loaded path in a div that emits the attribute:
<div data-loading={loading ? "true" : "false"}>
  {/* existing conditional body */}
</div>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/monitoring/daily-chart.tsx
git commit -m "feat(frontend): emit data-loading attribute on daily chart"
```

---

### Task 3.5: `QualityPrint` component with Tremor chart

**Files:**
- Create: `frontend/src/components/print/quality-print.tsx`

- [ ] **Step 1: Write the component**

```typescript
// frontend/src/components/print/quality-print.tsx
import { AreaChart, Area, CartesianGrid, XAxis, YAxis, ResponsiveContainer } from "recharts";

import { PrintShell } from "./print-shell";

export interface QualityPrintProps {
  projectName: string;
  generatedAt: string;
  score: number;
  bannedPatterns: Array<{ pattern: string; count: number }>;
  history: Array<{ round: number; score: number }>;
}

export function QualityPrint({
  projectName,
  generatedAt,
  score,
  bannedPatterns,
  history,
}: QualityPrintProps) {
  return (
    <PrintShell title={projectName} subtitle="Prose Quality Report" generatedAt={generatedAt}>
      <section className="mb-6">
        <p className="text-sm text-[#52525B]">Final prose quality score</p>
        <p className="mt-1 text-4xl font-semibold text-[#32374A]">{score}</p>
      </section>

      <section className="mb-6" data-loading="false">
        <h2 className="mb-2 text-sm font-semibold">Score across review rounds</h2>
        <div style={{ width: "100%", height: 180 }}>
          <ResponsiveContainer>
            <AreaChart data={history}>
              <CartesianGrid stroke="#E4E4E7" strokeDasharray="3 3" />
              <XAxis dataKey="round" stroke="#71717A" fontSize={10} />
              <YAxis stroke="#71717A" fontSize={10} domain={[0, 100]} />
              <Area
                type="monotone"
                dataKey="score"
                stroke="#663399"
                fill="#663399"
                fillOpacity={0.2}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold">Banned patterns detected</h2>
        {bannedPatterns.length === 0 ? (
          <p className="text-xs text-[#71717A]">No banned patterns found.</p>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[#E4E4E7] text-left">
                <th className="py-1 font-semibold">Pattern</th>
                <th className="py-1 font-semibold">Count</th>
              </tr>
            </thead>
            <tbody>
              {bannedPatterns.map((p) => (
                <tr key={p.pattern} className="border-b border-[#F4F4F5]">
                  <td className="py-1 font-mono">{p.pattern}</td>
                  <td className="py-1 tabular-nums">{p.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </PrintShell>
  );
}
```

The outer chart section sets `data-loading="false"` because the Recharts tree has no loading state. The Playwright helper already waits for all `[data-loading="true"]` to clear, so static `"false"` is a safe signal.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/print/quality-print.tsx
git commit -m "feat(frontend): QualityPrint component with Tremor chart"
```

---

### Task 3.6: `ReviewHistoryPrint` component

**Files:**
- Create: `frontend/src/components/print/review-history-print.tsx`

- [ ] **Step 1: Write the component**

```typescript
// frontend/src/components/print/review-history-print.tsx
import { PrintShell } from "./print-shell";

export interface ReviewHistoryEntry {
  round: number;
  decision: string;
  decided_at?: string | null;
  reviewer?: string | null;
  notes?: string;
}

export interface ReviewHistoryPrintProps {
  projectName: string;
  generatedAt: string;
  entries: ReviewHistoryEntry[];
}

export function ReviewHistoryPrint({
  projectName,
  generatedAt,
  entries,
}: ReviewHistoryPrintProps) {
  return (
    <PrintShell
      title={projectName}
      subtitle="Review History"
      generatedAt={generatedAt}
    >
      {entries.length === 0 ? (
        <p className="text-sm text-[#71717A]">No review history on record.</p>
      ) : (
        <ol className="space-y-4">
          {entries.map((e) => (
            <li
              key={e.round}
              className="rounded-md border border-[#E4E4E7] bg-[#FAF9F7] p-3"
            >
              <div className="flex items-baseline justify-between">
                <h3 className="text-sm font-semibold">
                  Round {e.round + 1} — {e.decision}
                </h3>
                <span className="text-[10px] text-[#A1A1AA]">
                  {e.decided_at ?? "—"}
                </span>
              </div>
              {e.reviewer && (
                <p className="text-xs text-[#71717A]">Reviewer: {e.reviewer}</p>
              )}
              {e.notes && (
                <p className="mt-2 whitespace-pre-wrap text-xs text-[#52525B]">
                  {e.notes}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </PrintShell>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/print/review-history-print.tsx
git commit -m "feat(frontend): ReviewHistoryPrint component"
```

---

### Task 3.7: Print routes for quality + review history

**Files:**
- Create: `frontend/src/app/print/cme/quality/[threadId]/page.tsx`
- Create: `frontend/src/app/print/cme/review-history/[threadId]/page.tsx`

- [ ] **Step 1: Create the quality route**

```typescript
// frontend/src/app/print/cme/quality/[threadId]/page.tsx
import { notFound } from "next/navigation";

import { QualityPrint } from "@/components/print/quality-print";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ threadId: string }>;
  searchParams: Promise<{ t?: string }>;
}

async function fetchQuality(threadId: string, token: string) {
  const registry = process.env.REGISTRY_INTERNAL_URL ?? "http://dhg-registry-api:8000";
  const res = await fetch(
    `${registry}/api/cme/export/internal/quality/${threadId}`,
    { headers: { "X-Print-Token": token }, cache: "no-store" },
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`registry fetch failed: ${res.status}`);
  return res.json() as Promise<{
    project_name: string;
    score: number;
    banned_patterns: Array<{ pattern: string; count: number }>;
    history: Array<{ round: number; score: number }>;
  }>;
}

export default async function Page({ params, searchParams }: Props) {
  const { threadId } = await params;
  const { t } = await searchParams;
  if (!t) notFound();
  const data = await fetchQuality(threadId, t);
  if (!data) notFound();
  return (
    <QualityPrint
      projectName={data.project_name}
      generatedAt={new Date().toISOString()}
      score={data.score}
      bannedPatterns={data.banned_patterns}
      history={data.history}
    />
  );
}
```

- [ ] **Step 2: Create the review-history route**

```typescript
// frontend/src/app/print/cme/review-history/[threadId]/page.tsx
import { notFound } from "next/navigation";

import { ReviewHistoryPrint } from "@/components/print/review-history-print";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ threadId: string }>;
  searchParams: Promise<{ t?: string }>;
}

async function fetchHistory(threadId: string, token: string) {
  const registry = process.env.REGISTRY_INTERNAL_URL ?? "http://dhg-registry-api:8000";
  const res = await fetch(
    `${registry}/api/cme/export/internal/review-history/${threadId}`,
    { headers: { "X-Print-Token": token }, cache: "no-store" },
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`registry fetch failed: ${res.status}`);
  return res.json() as Promise<{
    project_name: string;
    entries: Array<{
      round: number;
      decision: string;
      decided_at?: string | null;
      reviewer?: string | null;
      notes?: string;
    }>;
  }>;
}

export default async function Page({ params, searchParams }: Props) {
  const { threadId } = await params;
  const { t } = await searchParams;
  if (!t) notFound();
  const data = await fetchHistory(threadId, t);
  if (!data) notFound();
  return (
    <ReviewHistoryPrint
      projectName={data.project_name}
      generatedAt={new Date().toISOString()}
      entries={data.entries}
    />
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/print/cme/quality frontend/src/app/print/cme/review-history
git commit -m "feat(frontend): quality + review-history print routes"
```

---

### Task 3.8: Internal endpoints hydrating the new print routes

**Files:**
- Modify: `registry/export_endpoints.py`

- [ ] **Step 1: Add the endpoints**

```python
# registry/export_endpoints.py — append
from registry.export_sources.quality import load_quality_for_thread
from registry.export_sources.review_history import load_review_history_for_thread
from models import CMEProject as _CMEProject


async def _project_name_for_thread(session: AsyncSession, thread_id: str) -> str | None:
    row = (
        await session.execute(
            select(_CMEProject).where(_CMEProject.pipeline_thread_id == thread_id).limit(1)
        )
    ).scalar_one_or_none()
    return row.name if row else None


def _require_token(subject: str, thread_id: str, token: str | None) -> None:
    secret = os.environ.get("EXPORT_SIGNING_SECRET")
    if not secret or not token:
        raise HTTPException(status_code=401, detail="missing token")
    try:
        payload = verify_print_token(token, secret=secret)
    except PrintTokenExpired:
        raise HTTPException(status_code=401, detail="token expired")
    except PrintTokenInvalid:
        raise HTTPException(status_code=401, detail="invalid token")
    if payload.subject != subject or payload.resource_id != thread_id:
        raise HTTPException(status_code=403, detail="scope mismatch")


@router.get("/internal/quality/{thread_id}")
async def internal_quality(
    thread_id: str,
    x_print_token: str | None = Header(default=None, alias="X-Print-Token"),
    session: AsyncSession = Depends(get_async_db),
) -> dict:
    _require_token("cme_quality", thread_id, x_print_token)
    name = await _project_name_for_thread(session, thread_id)
    quality = await load_quality_for_thread(thread_id)
    if name is None or quality is None:
        raise HTTPException(status_code=404, detail="quality data not found")
    return {"project_name": name, **quality}


@router.get("/internal/review-history/{thread_id}")
async def internal_review_history(
    thread_id: str,
    x_print_token: str | None = Header(default=None, alias="X-Print-Token"),
    session: AsyncSession = Depends(get_async_db),
) -> dict:
    _require_token("cme_review_history", thread_id, x_print_token)
    name = await _project_name_for_thread(session, thread_id)
    entries = await load_review_history_for_thread(thread_id)
    if name is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {"project_name": name, "entries": entries}
```

- [ ] **Step 2: Commit**

```bash
git add registry/export_endpoints.py
git commit -m "feat(export): internal endpoints for quality + review-history print routes"
```

---

### Task 3.9: Extend the bundler to include quality, review history, citations

**Files:**
- Modify: `registry/export_bundler.py`

- [ ] **Step 1: Pull the new sources and add them to the zip**

In `assemble_project_bundle`, after the document rendering block:

```python
# Optional extras — only included when the source returns data
from registry.export_sources.quality import load_quality_for_thread
from registry.export_sources.review_history import load_review_history_for_thread
from registry.export_sources.citations import load_citations_for_thread

quality_pdf: bytes | None = None
quality = await load_quality_for_thread(thread_id)
if quality:
    url = build_print_url(
        subject="cme_quality",
        resource_id=thread_id,
        path_prefix="/print/cme/quality/",
    )
    quality_pdf = await render_via_renderer(url)

review_pdf: bytes | None = None
review = await load_review_history_for_thread(thread_id)
if review:
    url = build_print_url(
        subject="cme_review_history",
        resource_id=thread_id,
        path_prefix="/print/cme/review-history/",
    )
    review_pdf = await render_via_renderer(url)

citations = await load_citations_for_thread(thread_id)
```

Then, inside the `with zipfile.ZipFile(...)` block, add:

```python
if quality_pdf is not None:
    zf.writestr("quality.pdf", quality_pdf)
if review_pdf is not None:
    zf.writestr("review-history.pdf", review_pdf)
if citations:
    zf.writestr("citations.json", json.dumps(citations, indent=2))
```

- [ ] **Step 2: Commit**

```bash
git add registry/export_bundler.py
git commit -m "feat(export): bundler includes quality, review-history, citations"
```

---

### Task 3.10: Round-trip integration test with quality + review history

**Files:**
- Create: `registry/test_export_integration_extras.py`

- [ ] **Step 1: Write the test**

```python
# registry/test_export_integration_extras.py
import zipfile
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api import app
from registry.export_worker import _claim_next_job, _process


@pytest.mark.asyncio
async def test_bundle_contains_quality_and_review(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EXPORTS_DIR", str(tmp_path))

    fake_project = {
        "name": "Extras Project",
        "intake": {"audience": {"specialty": "Nephrology"}},
        "documents": [{"slug": "needs-assessment", "thread_id": "t-extra"}],
    }
    fake_quality = {"score": 91, "banned_patterns": [], "history": [{"round": 0, "score": 91}]}
    fake_review = [{"round": 0, "decision": "approved", "decided_at": "2026-04-14", "notes": "ok"}]
    fake_citations = [{"id": "10.1001/jama.2024.12345", "status": "verified"}]

    with patch("registry.export_bundler.load_project_for_thread",
               new=AsyncMock(return_value=fake_project)), \
         patch("registry.export_bundler.render_via_renderer",
               new=AsyncMock(return_value=b"%PDF-1.7\nfake")), \
         patch("registry.export_sources.quality.load_quality_for_thread",
               new=AsyncMock(return_value=fake_quality)), \
         patch("registry.export_sources.review_history.load_review_history_for_thread",
               new=AsyncMock(return_value=fake_review)), \
         patch("registry.export_sources.citations.load_citations_for_thread",
               new=AsyncMock(return_value=fake_citations)):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            enqueue = await c.post(
                "/api/cme/export/project/t-extra",
                json={"thread_id": "t-extra", "graph_id": "grant_package"},
                headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
            )
            job_id = enqueue.json()["id"]
            job = await _claim_next_job()
            await _process(job)

    with zipfile.ZipFile(tmp_path / f"{job_id}.zip") as zf:
        names = set(zf.namelist())
    assert "quality.pdf" in names
    assert "review-history.pdf" in names
    assert "citations.json" in names
```

- [ ] **Step 2: Run — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_integration_extras.py -v
```

- [ ] **Step 3: Tag Phase 3 complete**

```bash
git add registry/test_export_integration_extras.py
git commit -m "test(export): integration coverage for quality/review/citation extras"
git tag phase3-complete
```

---

## Phase 4 — Revision history with paragraph-level semantic diff

Goal: Auditors can see exactly how a document changed between review rounds. Walks LangGraph checkpoints for the thread, extracts document text after each round, aligns paragraphs across rounds using a similarity metric, and renders a colored diff into a new `revision-history.pdf`. Guarded by a feature flag so we can tune it before making it default.

---

### Task 4.1: Checkpoint history fetcher

**Files:**
- Create: `registry/export_sources/revisions.py`
- Create: `registry/test_export_sources_revisions.py`

- [ ] **Step 1: Write the failing test**

```python
# registry/test_export_sources_revisions.py
from unittest.mock import AsyncMock, patch

import pytest

from registry.export_sources.revisions import fetch_document_versions


@pytest.mark.asyncio
async def test_versions_are_ordered_oldest_first() -> None:
    fake_checkpoints = [
        {"created_at": "2026-04-10T10:00:00Z", "document_text": "A\n\nB"},
        {"created_at": "2026-04-11T10:00:00Z", "document_text": "A prime\n\nB"},
        {"created_at": "2026-04-12T10:00:00Z", "document_text": "A prime\n\nB\n\nC"},
    ]
    with patch(
        "registry.export_sources.revisions._fetch_checkpoints",
        new=AsyncMock(return_value=fake_checkpoints),
    ):
        versions = await fetch_document_versions("t-1")
    assert len(versions) == 3
    assert versions[0].round == 0
    assert versions[-1].round == 2
    assert versions[0].document_text.startswith("A")
```

- [ ] **Step 2: Implement**

```python
# registry/export_sources/revisions.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DocumentVersion:
    round: int
    created_at: str
    document_text: str


async def _fetch_checkpoints(thread_id: str) -> list[dict[str, Any]]:
    """Fetch LangGraph checkpoints for the given thread, oldest first.

    Real implementation uses the LangGraph SDK against LangGraph Cloud. Kept as
    a module-level function so tests can patch it.
    """
    import os

    import httpx

    base_url = os.environ.get("LANGGRAPH_CLOUD_URL")
    api_key = os.environ.get("LANGCHAIN_API_KEY")
    if not base_url or not api_key:
        return []

    async with httpx.AsyncClient(
        base_url=base_url,
        headers={"x-api-key": api_key},
        timeout=60.0,
    ) as client:
        resp = await client.get(f"/threads/{thread_id}/history")
        resp.raise_for_status()
        raw = resp.json() or []

    out: list[dict[str, Any]] = []
    for entry in sorted(raw, key=lambda x: x.get("created_at", "")):
        values = entry.get("values") or {}
        text = values.get("document_text") or values.get("final_document") or ""
        if not text:
            continue
        out.append({"created_at": entry.get("created_at", ""), "document_text": text})
    return out


async def fetch_document_versions(thread_id: str) -> list[DocumentVersion]:
    checkpoints = await _fetch_checkpoints(thread_id)
    versions: list[DocumentVersion] = []
    for i, c in enumerate(checkpoints):
        versions.append(
            DocumentVersion(
                round=i,
                created_at=c["created_at"],
                document_text=c["document_text"],
            )
        )
    return versions
```

- [ ] **Step 3: Run — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_sources_revisions.py -v
```

- [ ] **Step 4: Commit**

```bash
git add registry/export_sources/revisions.py registry/test_export_sources_revisions.py
git commit -m "feat(export): checkpoint history fetcher"
```

---

### Task 4.2: Paragraph-level semantic diff algorithm (TDD)

**Files:**
- Create: `registry/export_diff.py`
- Create: `registry/test_export_diff.py`

- [ ] **Step 1: Write the failing tests**

```python
# registry/test_export_diff.py
import pytest

from registry.export_diff import (
    DiffEntry,
    align_paragraphs,
    classify_round,
    tokenize_paragraphs,
)


def test_tokenize_splits_on_blank_lines() -> None:
    text = "para one\nline two\n\npara two\n\n\npara three"
    paras = tokenize_paragraphs(text)
    assert len(paras) == 3
    assert paras[0].startswith("para one")


def test_align_unchanged_paragraphs() -> None:
    a = ["The sky is blue.", "Water is wet."]
    b = ["The sky is blue.", "Water is wet."]
    pairs = align_paragraphs(a, b, threshold=0.85)
    assert all(p.classification == "unchanged" for p in pairs)


def test_detects_add_modify_remove() -> None:
    a = ["Keep this sentence.", "Remove this one.", "Edit me slightly."]
    b = ["Keep this sentence.", "Edit me a little.", "A brand new paragraph."]
    pairs = align_paragraphs(a, b, threshold=0.55)
    kinds = {p.classification for p in pairs}
    assert "unchanged" in kinds
    assert "modified" in kinds
    assert "added" in kinds
    assert "removed" in kinds


def test_classify_round_returns_diff_entries() -> None:
    previous = "keep\n\nold"
    current = "keep\n\nnew"
    entries: list[DiffEntry] = classify_round(previous, current, threshold=0.55)
    assert any(e.classification == "unchanged" for e in entries)
    assert any(e.classification == "modified" for e in entries)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
docker exec dhg-registry-api pytest registry/test_export_diff.py -v
```

- [ ] **Step 3: Implement the diff module**

```python
# registry/export_diff.py
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

Classification = Literal["unchanged", "modified", "added", "removed"]


@dataclass(frozen=True)
class DiffEntry:
    classification: Classification
    previous: str | None
    current: str | None
    similarity: float


def tokenize_paragraphs(text: str) -> list[str]:
    blocks = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n")]
    return [b for b in blocks if b]


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def align_paragraphs(
    previous: list[str],
    current: list[str],
    *,
    threshold: float = 0.85,
) -> list[DiffEntry]:
    """Greedy alignment: for each previous paragraph, find its best match in current.

    Previous paragraphs without a match above threshold are marked 'removed'.
    Current paragraphs never claimed are marked 'added'.
    """
    used_current: set[int] = set()
    entries: list[DiffEntry] = []

    for p in previous:
        best_idx = -1
        best_score = 0.0
        for j, c in enumerate(current):
            if j in used_current:
                continue
            score = _similarity(p, c)
            if score > best_score:
                best_score = score
                best_idx = j
        if best_idx >= 0 and best_score >= threshold:
            used_current.add(best_idx)
            classification: Classification = "unchanged" if best_score >= 0.995 else "modified"
            entries.append(
                DiffEntry(
                    classification=classification,
                    previous=p,
                    current=current[best_idx],
                    similarity=best_score,
                )
            )
        else:
            entries.append(
                DiffEntry(
                    classification="removed",
                    previous=p,
                    current=None,
                    similarity=best_score,
                )
            )

    for j, c in enumerate(current):
        if j in used_current:
            continue
        entries.append(
            DiffEntry(
                classification="added",
                previous=None,
                current=c,
                similarity=0.0,
            )
        )

    return entries


def classify_round(
    previous_text: str,
    current_text: str,
    *,
    threshold: float = 0.85,
) -> list[DiffEntry]:
    return align_paragraphs(
        tokenize_paragraphs(previous_text),
        tokenize_paragraphs(current_text),
        threshold=threshold,
    )
```

- [ ] **Step 4: Run — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_diff.py -v
```

- [ ] **Step 5: Commit**

```bash
git add registry/export_diff.py registry/test_export_diff.py
git commit -m "feat(export): paragraph-level semantic diff algorithm"
```

---

### Task 4.3: Three-round golden file test

**Files:**
- Create: `registry/test_export_diff_golden.py`
- Create: `registry/fixtures/diff/round_0.txt`
- Create: `registry/fixtures/diff/round_1.txt`
- Create: `registry/fixtures/diff/round_2.txt`

- [ ] **Step 1: Create fixture files**

```
# registry/fixtures/diff/round_0.txt
The CME activity addresses type 2 diabetes management in primary care.

Current practice patterns show underuse of GLP-1 receptor agonists.

Learners will identify barriers to intensification.
```

```
# registry/fixtures/diff/round_1.txt
The CME activity addresses type 2 diabetes management in primary care.

Current practice patterns show underuse of GLP-1 receptor agonists and SGLT2 inhibitors.

Learners will identify barriers to intensification.

A new section on shared decision-making was added.
```

```
# registry/fixtures/diff/round_2.txt
The CME activity addresses type 2 diabetes management in primary care settings across the U.S.

Current practice patterns show underuse of GLP-1 receptor agonists and SGLT2 inhibitors.

A new section on shared decision-making was added.
```

- [ ] **Step 2: Write the golden test**

```python
# registry/test_export_diff_golden.py
from pathlib import Path

from registry.export_diff import classify_round

FIXTURES = Path(__file__).parent / "fixtures" / "diff"


def read(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_round_0_to_1() -> None:
    entries = classify_round(read("round_0.txt"), read("round_1.txt"), threshold=0.6)
    kinds = [e.classification for e in entries]
    assert "unchanged" in kinds  # first paragraph
    assert "modified" in kinds  # GLP-1 sentence got SGLT2 added
    assert kinds.count("added") == 1  # new section paragraph
    assert "removed" not in kinds


def test_round_1_to_2() -> None:
    entries = classify_round(read("round_1.txt"), read("round_2.txt"), threshold=0.6)
    kinds = [e.classification for e in entries]
    assert "modified" in kinds  # first sentence grew
    assert "removed" in kinds  # 'Learners will identify barriers...' was dropped
```

- [ ] **Step 3: Run — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_diff_golden.py -v
```

- [ ] **Step 4: Commit**

```bash
git add registry/fixtures/diff/ registry/test_export_diff_golden.py
git commit -m "test(export): golden fixtures for three-round diff"
```

---

### Task 4.4: `RevisionHistoryPrint` component

**Files:**
- Create: `frontend/src/components/print/revision-history-print.tsx`

- [ ] **Step 1: Write the component**

```typescript
// frontend/src/components/print/revision-history-print.tsx
import { PrintShell } from "./print-shell";

export interface DiffEntry {
  classification: "unchanged" | "modified" | "added" | "removed";
  previous: string | null;
  current: string | null;
  similarity: number;
}

export interface RevisionRound {
  from_round: number;
  to_round: number;
  entries: DiffEntry[];
}

export interface RevisionHistoryPrintProps {
  projectName: string;
  generatedAt: string;
  rounds: RevisionRound[];
}

const STYLE: Record<DiffEntry["classification"], string> = {
  unchanged: "text-[#52525B]",
  modified: "bg-[#FFF7E6] text-[#32374A] border-l-2 border-[#F77E2D] pl-2",
  added: "bg-[#ECFDF5] text-[#065F46] border-l-2 border-[#10B981] pl-2",
  removed: "text-[#9F1239] line-through decoration-[#9F1239]/60",
};

export function RevisionHistoryPrint({
  projectName,
  generatedAt,
  rounds,
}: RevisionHistoryPrintProps) {
  return (
    <PrintShell title={projectName} subtitle="Revision History" generatedAt={generatedAt}>
      {rounds.length === 0 ? (
        <p className="text-sm text-[#71717A]">Only a single draft on file — no diffs to show.</p>
      ) : (
        rounds.map((round) => (
          <section key={`${round.from_round}-${round.to_round}`} className="mb-8">
            <h2 className="mb-3 border-b border-[#E4E4E7] pb-1 text-sm font-semibold">
              Round {round.from_round + 1} → Round {round.to_round + 1}
            </h2>
            <div className="space-y-3 text-xs">
              {round.entries.map((entry, i) => {
                const text =
                  entry.classification === "removed"
                    ? entry.previous ?? ""
                    : entry.current ?? entry.previous ?? "";
                return (
                  <p key={i} className={`whitespace-pre-wrap ${STYLE[entry.classification]}`}>
                    {text}
                  </p>
                );
              })}
            </div>
          </section>
        ))
      )}
    </PrintShell>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/print/revision-history-print.tsx
git commit -m "feat(frontend): RevisionHistoryPrint component"
```

---

### Task 4.5: Print route + internal endpoint for revision history

**Files:**
- Create: `frontend/src/app/print/cme/revision-history/[threadId]/page.tsx`
- Modify: `registry/export_signing.py`
- Modify: `frontend/src/middleware.ts`
- Modify: `registry/export_endpoints.py`

- [ ] **Step 1: Add the new subject to the signing union**

```python
# registry/export_signing.py — extend the Subject Literal
Subject = Literal[
    "cme_document",
    "cme_project_intake",
    "cme_quality",
    "cme_review_history",
    "cme_revision_history",
]
```

And in `frontend/src/lib/printTokens.ts`:

```typescript
export type Subject =
  | "cme_document"
  | "cme_project_intake"
  | "cme_quality"
  | "cme_review_history"
  | "cme_revision_history";
```

- [ ] **Step 2: Extend middleware prefix map**

```typescript
// frontend/src/middleware.ts — add to PRINT_SUBJECT_BY_PREFIX
{ prefix: "/print/cme/revision-history/", subject: "cme_revision_history" },
```

- [ ] **Step 3: Create the print route**

```typescript
// frontend/src/app/print/cme/revision-history/[threadId]/page.tsx
import { notFound } from "next/navigation";

import {
  RevisionHistoryPrint,
  type RevisionRound,
} from "@/components/print/revision-history-print";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ threadId: string }>;
  searchParams: Promise<{ t?: string }>;
}

async function fetchRevisions(threadId: string, token: string) {
  const registry = process.env.REGISTRY_INTERNAL_URL ?? "http://dhg-registry-api:8000";
  const res = await fetch(
    `${registry}/api/cme/export/internal/revision-history/${threadId}`,
    { headers: { "X-Print-Token": token }, cache: "no-store" },
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`registry fetch failed: ${res.status}`);
  return res.json() as Promise<{ project_name: string; rounds: RevisionRound[] }>;
}

export default async function Page({ params, searchParams }: Props) {
  const { threadId } = await params;
  const { t } = await searchParams;
  if (!t) notFound();
  const data = await fetchRevisions(threadId, t);
  if (!data) notFound();
  return (
    <RevisionHistoryPrint
      projectName={data.project_name}
      generatedAt={new Date().toISOString()}
      rounds={data.rounds}
    />
  );
}
```

- [ ] **Step 4: Add the internal endpoint**

```python
# registry/export_endpoints.py — append
from dataclasses import asdict

from registry.export_diff import classify_round
from registry.export_sources.revisions import fetch_document_versions


@router.get("/internal/revision-history/{thread_id}")
async def internal_revision_history(
    thread_id: str,
    x_print_token: str | None = Header(default=None, alias="X-Print-Token"),
    session: AsyncSession = Depends(get_async_db),
) -> dict:
    _require_token("cme_revision_history", thread_id, x_print_token)
    name = await _project_name_for_thread(session, thread_id)
    if name is None:
        raise HTTPException(status_code=404, detail="project not found")

    versions = await fetch_document_versions(thread_id)
    rounds: list[dict] = []
    for i in range(1, len(versions)):
        entries = classify_round(
            versions[i - 1].document_text,
            versions[i].document_text,
            threshold=0.75,
        )
        rounds.append(
            {
                "from_round": versions[i - 1].round,
                "to_round": versions[i].round,
                "entries": [asdict(e) for e in entries],
            }
        )
    return {"project_name": name, "rounds": rounds}
```

- [ ] **Step 5: Commit**

```bash
git add registry/export_signing.py registry/export_endpoints.py \
        frontend/src/lib/printTokens.ts frontend/src/middleware.ts \
        frontend/src/app/print/cme/revision-history
git commit -m "feat(export): revision-history print route and diff endpoint"
```

---

### Task 4.6: Bundler integration behind `EXPORT_INCLUDE_REVISIONS` flag

**Files:**
- Modify: `registry/export_bundler.py`
- Modify: `.env.example`

- [ ] **Step 1: Read the flag and render the PDF only when enabled**

In `assemble_project_bundle`, after the review history block:

```python
revision_pdf: bytes | None = None
if os.environ.get("EXPORT_INCLUDE_REVISIONS", "false").lower() == "true":
    from registry.export_sources.revisions import fetch_document_versions

    versions = await fetch_document_versions(thread_id)
    if len(versions) >= 2:
        url = build_print_url(
            subject="cme_revision_history",
            resource_id=thread_id,
            path_prefix="/print/cme/revision-history/",
        )
        revision_pdf = await render_via_renderer(url)
```

Inside the zip block:

```python
if revision_pdf is not None:
    zf.writestr("revision-history.pdf", revision_pdf)
```

- [ ] **Step 2: Add the flag to `.env.example`**

```bash
# Include revision-history.pdf in project downloads (experimental)
EXPORT_INCLUDE_REVISIONS=false
```

- [ ] **Step 3: Commit**

```bash
git add registry/export_bundler.py .env.example
git commit -m "feat(export): include revision history in bundle behind flag"
```

---

### Task 4.7: Bundler flag test

**Files:**
- Create: `registry/test_export_revisions_flag.py`

- [ ] **Step 1: Write the test**

```python
# registry/test_export_revisions_flag.py
import zipfile
from unittest.mock import AsyncMock, patch

import pytest

from registry.export_bundler import assemble_project_bundle


@pytest.mark.asyncio
async def test_revisions_included_when_flag_set(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EXPORTS_DIR", str(tmp_path))
    monkeypatch.setenv("EXPORT_INCLUDE_REVISIONS", "true")

    fake_project = {
        "name": "Revisions Project",
        "intake": {},
        "documents": [],
    }
    fake_versions = [
        type("V", (), {"round": 0, "document_text": "A"})(),
        type("V", (), {"round": 1, "document_text": "B"})(),
    ]

    with patch("registry.export_bundler.load_project_for_thread",
               new=AsyncMock(return_value=fake_project)), \
         patch("registry.export_bundler.render_via_renderer",
               new=AsyncMock(return_value=b"%PDF-1.7\nfake")), \
         patch("registry.export_sources.revisions.fetch_document_versions",
               new=AsyncMock(return_value=fake_versions)):
        result = await assemble_project_bundle("t-rev")

    with zipfile.ZipFile(result.path) as zf:
        assert "revision-history.pdf" in zf.namelist()


@pytest.mark.asyncio
async def test_revisions_excluded_by_default(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EXPORTS_DIR", str(tmp_path))
    monkeypatch.delenv("EXPORT_INCLUDE_REVISIONS", raising=False)

    fake_project = {"name": "No Rev", "intake": {}, "documents": []}
    with patch("registry.export_bundler.load_project_for_thread",
               new=AsyncMock(return_value=fake_project)), \
         patch("registry.export_bundler.render_via_renderer",
               new=AsyncMock(return_value=b"%PDF-1.7\nfake")):
        result = await assemble_project_bundle("t-norev")

    with zipfile.ZipFile(result.path) as zf:
        assert "revision-history.pdf" not in zf.namelist()
```

- [ ] **Step 2: Run — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_revisions_flag.py -v
```

- [ ] **Step 3: Commit and tag**

```bash
git add registry/test_export_revisions_flag.py
git commit -m "test(export): feature flag controls revision history inclusion"
git tag phase4-complete
```

---

### Task 4.8: Manual review of a real two-round fixture

- [ ] **Step 1: Enable the flag against a dev project**

```bash
docker exec dhg-registry-api sh -c "EXPORT_INCLUDE_REVISIONS=true python -m registry.cli debug-bundle <real-thread-id>"
```

(The debug CLI is an existing helper in the repo; if it does not exist yet, this step can be skipped and revisited during execution.)

- [ ] **Step 2: Open `revision-history.pdf` and visually verify**
- Modified paragraphs appear orange-highlighted
- Added paragraphs appear green
- Removed paragraphs appear strikethrough red
- Unchanged paragraphs appear plain gray

- [ ] **Step 3: If the threshold feels wrong, tune it in `internal_revision_history` and rerun — do not commit threshold changes until they beat the golden fixtures.**

---

## Phase 5 — Hardening (TTL, rate limiting, retry, observability)

Goal: Make the feature production-durable. TTL cleanup so `/exports` doesn't grow unbounded, rate limiting so one user can't saturate the queue, retry UX for failed jobs, signing key rotation, Chromium memory watchdog, Grafana panel, Alertmanager rule, and a compliance-mode stamp in the README.

---

### Task 5.1: TTL cleanup task

**Files:**
- Create: `registry/export_cleanup.py`
- Modify: `registry/api.py`

- [ ] **Step 1: Write the cleanup loop**

```python
# registry/export_cleanup.py
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from database import async_session
from models import DownloadJob

log = logging.getLogger("dhg.export.cleanup")

CLEANUP_INTERVAL_SECONDS = 3600.0  # run hourly
DEFAULT_TTL_DAYS = 30


def _ttl_days() -> int:
    raw = os.environ.get("EXPORT_ARTIFACT_TTL_DAYS")
    if not raw:
        return DEFAULT_TTL_DAYS
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_TTL_DAYS


async def _cleanup_once() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=_ttl_days())
    async with async_session() as session:
        async with session.begin():
            rows = (
                await session.execute(
                    select(DownloadJob).where(
                        DownloadJob.status == "succeeded",
                        DownloadJob.completed_at < cutoff,
                        DownloadJob.artifact_path.is_not(None),
                    )
                )
            ).scalars().all()
            for row in rows:
                if row.artifact_path:
                    try:
                        Path(row.artifact_path).unlink(missing_ok=True)
                    except OSError:
                        log.exception("failed to unlink %s", row.artifact_path)
                row.artifact_path = None  # keep row for audit, drop file reference


async def run_cleanup(stop_event: asyncio.Event) -> None:
    log.info("export cleanup started")
    while not stop_event.is_set():
        try:
            await _cleanup_once()
        except Exception:
            log.exception("cleanup loop error")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=CLEANUP_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass
    log.info("export cleanup stopped")
```

- [ ] **Step 2: Start it in the FastAPI lifespan alongside the worker**

```python
# registry/api.py — lifespan additions
from registry.export_cleanup import run_cleanup

_cleanup_task: asyncio.Task | None = None

# inside lifespan() setup:
_cleanup_task = asyncio.create_task(run_cleanup(_worker_stop))

# inside teardown, after worker task awaited:
if _cleanup_task is not None:
    await _cleanup_task
```

- [ ] **Step 3: Commit**

```bash
git add registry/export_cleanup.py registry/api.py
git commit -m "feat(export): hourly TTL cleanup of expired artifacts"
```

---

### Task 5.2: Rate limiting on project enqueue

**Files:**
- Modify: `registry/export_endpoints.py`
- Modify: `registry/test_export_endpoints.py`

- [ ] **Step 1: Write the failing test**

```python
# append to registry/test_export_endpoints.py
@pytest.mark.asyncio
async def test_enqueue_rate_limit(monkeypatch) -> None:
    monkeypatch.setenv("EXPORT_MAX_IN_FLIGHT_PER_USER", "2")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = {"Cf-Access-Jwt-Assertion": "dev-bypass"}
        for i in range(2):
            resp = await c.post(
                f"/api/cme/export/project/thread-rl-{i}",
                json={"thread_id": f"thread-rl-{i}", "graph_id": "grant_package"},
                headers=headers,
            )
            assert resp.status_code == 202
        third = await c.post(
            "/api/cme/export/project/thread-rl-2",
            json={"thread_id": "thread-rl-2", "graph_id": "grant_package"},
            headers=headers,
        )
    assert third.status_code == 429
```

- [ ] **Step 2: Implement the rate check**

```python
# registry/export_endpoints.py — inside enqueue_project_download, after dedup block:
from sqlalchemy import func

max_in_flight = int(os.environ.get("EXPORT_MAX_IN_FLIGHT_PER_USER", "5"))
in_flight = (
    await session.execute(
        select(func.count(DownloadJob.id)).where(
            DownloadJob.status.in_(("pending", "running")),
        )
    )
).scalar_one()
if in_flight >= max_in_flight:
    raise HTTPException(
        status_code=429,
        detail=f"rate limit: {in_flight} jobs in flight (max {max_in_flight})",
    )
```

(In Phase 5 this counts across all users; per-user limiting lands when `created_by` is populated from the Cloudflare JWT subject, which is a tiny follow-up inside the enqueue handler. Do both at once:)

```python
# when constructing the DownloadJob above:
job = DownloadJob(
    thread_id=thread_id,
    graph_id=body.graph_id,
    scope="project",
    status="pending",
    created_by=request.state.user_email if hasattr(request.state, "user_email") else None,
)
```

And adjust the `in_flight` query to filter on `created_by` when present.

- [ ] **Step 3: Run — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_endpoints.py::test_enqueue_rate_limit -v
```

- [ ] **Step 4: Commit**

```bash
git add registry/export_endpoints.py registry/test_export_endpoints.py
git commit -m "feat(export): per-user rate limit on project enqueues"
```

---

### Task 5.3: Retry UX — button on failed jobs

**Files:**
- Modify: `frontend/src/components/review/downloads-tray.tsx`
- Modify: `frontend/src/lib/exportApi.ts`

- [ ] **Step 1: Add a retry helper**

```typescript
// frontend/src/lib/exportApi.ts — append
export async function retryJob(threadId: string, graphId: string): Promise<DownloadJobResponse> {
  return enqueueProject(threadId, graphId);
}
```

- [ ] **Step 2: Add the retry button in the tray's failed branch**

```typescript
// frontend/src/components/review/downloads-tray.tsx — near the "Save zip" branch
{r.status === "failed" && (
  <button
    type="button"
    onClick={async () => {
      try {
        const job = await retryJob(r.threadId, /* graphId unknown here — store it */);
        upsert({
          jobId: job.id,
          threadId: r.threadId,
          projectName: r.projectName,
          status: job.status,
          createdAt: job.created_at,
        });
      } catch (err) {
        console.error(err);
      }
    }}
    className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-2.5 py-1 text-xs text-foreground hover:bg-muted"
  >
    Retry
  </button>
)}
```

This requires the store record to carry `graphId`. Extend `DownloadRecord` with `graphId: string` and plumb it through the inbox `handleDownloadProject` handler.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/review/downloads-tray.tsx \
        frontend/src/lib/exportApi.ts frontend/src/stores/downloads-store.ts \
        frontend/src/components/review/inbox-master-detail.tsx
git commit -m "feat(inbox): retry button for failed downloads"
```

---

### Task 5.4: Tray filters (all / running / succeeded / failed)

**Files:**
- Modify: `frontend/src/components/review/downloads-tray.tsx`

- [ ] **Step 1: Add a filter state and chip row**

```typescript
// frontend/src/components/review/downloads-tray.tsx
import { useState } from "react";

type Filter = "all" | "running" | "succeeded" | "failed";

const FILTERS: Array<{ value: Filter; label: string }> = [
  { value: "all", label: "All" },
  { value: "running", label: "Running" },
  { value: "succeeded", label: "Done" },
  { value: "failed", label: "Failed" },
];

// inside DownloadsTray component:
const [filter, setFilter] = useState<Filter>("all");

const visible = records.filter((r) => {
  if (filter === "all") return true;
  if (filter === "running") return r.status === "pending" || r.status === "running";
  return r.status === filter;
});
```

Render the chips above the list and switch the list source from `records` to `visible`.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/review/downloads-tray.tsx
git commit -m "feat(inbox): filter chips on downloads tray"
```

---

### Task 5.5: Compliance stamp in `README.txt`

**Files:**
- Modify: `registry/export_bundler.py`

- [ ] **Step 1: Expand the `_readme` builder**

```python
# registry/export_bundler.py
import subprocess


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def _readme(
    project_name: str,
    generated_at: str,
    doc_count: int,
    thread_id: str,
    *,
    cme_mode: bool,
) -> str:
    lines = [
        "DHG AI Factory — CME Project Archive",
        "====================================",
        "",
        f"Project:       {project_name}",
        f"Thread:        {thread_id}",
        f"Generated:     {generated_at}",
        f"Documents:     {doc_count}",
        f"Generator:     dhg-registry-api / export_bundler v1",
        f"Code revision: {_git_sha()}",
        "",
        "Contents:",
        "  - intake.pdf           — Project intake sections",
        "  - documents/*.pdf      — Each CME document",
        "  - quality.pdf          — Prose quality report (when available)",
        "  - review-history.pdf   — Human review decisions (when available)",
        "  - revision-history.pdf — Paragraph diffs across rounds (when enabled)",
        "  - citations.json       — Verified citation list (when available)",
        "  - project.json         — Canonical intake + metadata",
        "",
        "AI-assisted output — verify against source material.",
    ]
    if cme_mode:
        lines += [
            "",
            "CME Compliance Mode:",
            "  This archive was generated with CME compliance mode enabled.",
            "  It is intended as supporting documentation for an ACCME-accredited activity.",
            "  This archive is not itself an ACCME submission and does not constitute legal,",
            "  medical, or accreditation advice.",
        ]
    return "\n".join(lines) + "\n"
```

And thread a `cme_mode` flag through `assemble_project_bundle`, reading from `os.environ.get("CME_COMPLIANCE_MODE", "false").lower() == "true"`.

- [ ] **Step 2: Commit**

```bash
git add registry/export_bundler.py
git commit -m "feat(export): compliance-mode README with git sha and thread id"
```

---

### Task 5.6: Chromium memory watchdog in pdf-renderer

**Files:**
- Modify: `services/pdf-renderer/main.py`
- Modify: `services/pdf-renderer/renderer.py`

- [ ] **Step 1: Switch `render_pdf` to a long-lived browser + per-request context**

```python
# services/pdf-renderer/renderer.py — rewrite
from __future__ import annotations

import asyncio
import os
import resource
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Browser, async_playwright

_MAX_RSS_MB = int(os.environ.get("RENDERER_MAX_RSS_MB", "1500"))
_lock = asyncio.Lock()
_browser: Browser | None = None
_playwright: Any | None = None


async def _ensure_browser() -> Browser:
    global _browser, _playwright
    if _browser is not None:
        return _browser
    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    return _browser


async def _maybe_restart() -> None:
    rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if rss_kb / 1024 > _MAX_RSS_MB:
        await _shutdown_browser()


async def _shutdown_browser() -> None:
    global _browser, _playwright
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright is not None:
        await _playwright.stop()
        _playwright = None


@dataclass(frozen=True)
class RenderRequest:
    url: str
    wait_for_selectors: list[str] = field(default_factory=list)
    timeout_ms: int = 30_000
    extra_http_headers: dict[str, str] = field(default_factory=dict)


async def render_pdf(request: RenderRequest) -> bytes:
    async with _lock:
        browser = await _ensure_browser()
        context = await browser.new_context(extra_http_headers=request.extra_http_headers)
        try:
            page = await context.new_page()
            await page.goto(request.url, wait_until="networkidle", timeout=request.timeout_ms)
            for selector in request.wait_for_selectors:
                await page.wait_for_selector(selector, timeout=request.timeout_ms)
            await page.wait_for_function(
                "() => document.querySelectorAll('[data-loading=\"true\"]').length === 0",
                timeout=request.timeout_ms,
            )
            pdf = await page.pdf(
                format="Letter",
                margin={"top": "0.75in", "bottom": "0.75in", "left": "0.75in", "right": "0.75in"},
                print_background=True,
            )
        finally:
            await context.close()
        await _maybe_restart()
        return pdf


async def shutdown_renderer() -> None:
    await _shutdown_browser()
```

- [ ] **Step 2: Call `shutdown_renderer` on FastAPI shutdown**

```python
# services/pdf-renderer/main.py — add shutdown handler
from contextlib import asynccontextmanager

from renderer import shutdown_renderer

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await shutdown_renderer()

app = FastAPI(title="dhg-pdf-renderer", version="0.1.0", lifespan=lifespan)
```

- [ ] **Step 3: Commit**

```bash
git add services/pdf-renderer/main.py services/pdf-renderer/renderer.py
git commit -m "feat(pdf-renderer): long-lived browser with RSS watchdog"
```

---

### Task 5.7: Signing key rotation support

**Files:**
- Modify: `registry/export_signing.py`
- Modify: `frontend/src/lib/printTokens.ts`
- Modify: `frontend/src/middleware.ts`
- Modify: `.env.example`

- [ ] **Step 1: Accept two secrets on verify in Python**

```python
# registry/export_signing.py — verify function
def verify_print_token(token: str, *, secret: str, previous_secret: str | None = None) -> PrintTokenPayload:
    try:
        return _verify_with(token, secret)
    except PrintTokenInvalid:
        if previous_secret:
            return _verify_with(token, previous_secret)
        raise


def _verify_with(token: str, secret: str) -> PrintTokenPayload:
    # existing body
    ...
```

- [ ] **Step 2: Mirror in TypeScript verifier**

```typescript
// frontend/src/lib/printTokens.ts
export function verifyPrintToken(
  token: string,
  secret: string,
  previousSecret?: string,
): PrintTokenPayload {
  try {
    return verifyWith(token, secret);
  } catch (err) {
    if (err instanceof PrintTokenInvalid && previousSecret) {
      return verifyWith(token, previousSecret);
    }
    throw err;
  }
}
```

And factor the existing body into `verifyWith`.

- [ ] **Step 3: Middleware reads both env vars**

```typescript
// frontend/src/middleware.ts — in the /print/* block
const secret = process.env.EXPORT_SIGNING_SECRET;
const previous = process.env.EXPORT_SIGNING_SECRET_PREVIOUS;
// ...
verifyPrintToken(token, secret, previous);
```

- [ ] **Step 4: Document the flag in `.env.example`**

```bash
# Previous signing secret for rotation windows (optional)
EXPORT_SIGNING_SECRET_PREVIOUS=
```

- [ ] **Step 5: Commit**

```bash
git add registry/export_signing.py frontend/src/lib/printTokens.ts \
        frontend/src/middleware.ts .env.example
git commit -m "feat(export): support signing key rotation with previous-secret fallback"
```

---

### Task 5.8: Prometheus metrics on the registry

**Files:**
- Modify: `registry/export_endpoints.py`
- Modify: `registry/export_worker.py`
- Modify: `registry/api.py`

- [ ] **Step 1: Define counters + histogram at module scope**

```python
# registry/export_endpoints.py — top of file
from prometheus_client import Counter, Histogram

EXPORT_ENQUEUED = Counter(
    "dhg_export_jobs_enqueued_total",
    "Number of export jobs enqueued",
    ["scope"],
)
EXPORT_COMPLETED = Counter(
    "dhg_export_jobs_completed_total",
    "Number of export jobs completed",
    ["scope", "outcome"],
)
EXPORT_DURATION = Histogram(
    "dhg_export_job_duration_seconds",
    "Time from pending to terminal state",
    ["scope"],
    buckets=(1, 5, 15, 30, 60, 120, 300, 600, 1200),
)
```

- [ ] **Step 2: Increment them in the handlers**

```python
# after successful enqueue:
EXPORT_ENQUEUED.labels(scope="project").inc()

# in export_worker._process:
from registry.export_endpoints import EXPORT_COMPLETED, EXPORT_DURATION
import time

start = time.monotonic()
try:
    ...
    EXPORT_COMPLETED.labels(scope=job.scope, outcome="succeeded").inc()
except Exception:
    EXPORT_COMPLETED.labels(scope=job.scope, outcome="failed").inc()
    raise
finally:
    EXPORT_DURATION.labels(scope=job.scope).observe(time.monotonic() - start)
```

- [ ] **Step 3: Verify `/metrics` scrape target**

```bash
curl -s http://localhost:8011/metrics | grep dhg_export_
```

Expected: all three metric names present.

- [ ] **Step 4: Commit**

```bash
git add registry/export_endpoints.py registry/export_worker.py
git commit -m "feat(export): Prometheus counters + duration histogram"
```

---

### Task 5.9: Grafana panel and Alertmanager rule

**Files:**
- Modify: `observability/grafana/dashboards/core-golden-signals.json`
- Modify: `observability/prometheus/alerts.yml`

- [ ] **Step 1: Add panel JSON**

Add three panels to the existing dashboard:
- Enqueue rate: `rate(dhg_export_jobs_enqueued_total[5m])`
- Failure rate: `rate(dhg_export_jobs_completed_total{outcome="failed"}[5m]) / clamp_min(rate(dhg_export_jobs_completed_total[5m]), 0.001)`
- p90 duration: `histogram_quantile(0.9, sum by (le) (rate(dhg_export_job_duration_seconds_bucket[5m])))`

- [ ] **Step 2: Add alert rules**

```yaml
# observability/prometheus/alerts.yml — append under groups:
- name: dhg-export
  rules:
    - alert: DHGExportFailureRateHigh
      expr: |
        (
          rate(dhg_export_jobs_completed_total{outcome="failed"}[15m])
          / clamp_min(rate(dhg_export_jobs_completed_total[15m]), 0.001)
        ) > 0.10
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: "CME export failure rate > 10% for 15m"
        description: "Investigate dhg-pdf-renderer and registry-api logs."

    - alert: DHGExportQueueDepthHigh
      expr: |
        sum(dhg_export_jobs_enqueued_total)
          - sum(dhg_export_jobs_completed_total) > 20
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "CME export queue depth > 20"
        description: "Worker may be stalled or renderer unresponsive."
```

- [ ] **Step 3: Reload Prometheus**

```bash
docker compose kill -s HUP dhg-prometheus
```

Verify in the Prometheus UI that both rules appear under Alerts.

- [ ] **Step 4: Commit**

```bash
git add observability/grafana/dashboards/core-golden-signals.json \
        observability/prometheus/alerts.yml
git commit -m "feat(observability): export dashboards and alert rules"
```

---

### Task 5.10: Load test + phase closeout

**Files:**
- Create: `registry/test_export_load.py`

- [ ] **Step 1: Write a contention test**

```python
# registry/test_export_load.py
import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from api import app


@pytest.mark.asyncio
async def test_twenty_concurrent_enqueues_do_not_deadlock() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async def enqueue(i: int):
            return await c.post(
                f"/api/cme/export/project/thread-load-{i}",
                json={"thread_id": f"thread-load-{i}", "graph_id": "grant_package"},
                headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
            )
        responses = await asyncio.gather(*(enqueue(i) for i in range(20)))
    assert all(r.status_code in (202, 429) for r in responses)
    assert sum(1 for r in responses if r.status_code == 202) >= 1
```

- [ ] **Step 2: Run — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_load.py -v
```

- [ ] **Step 3: Commit and tag**

```bash
git add registry/test_export_load.py
git commit -m "test(export): concurrent enqueue load test"
git tag phase5-complete
```

- [ ] **Step 4: Final close-out**

```bash
git push --tags
```

Announce to Stephen that all 5 phases are complete, all tagged, and point him at the Grafana dashboard for the first week of production traffic.

---

## Phase dependency map

| Phase | Depends on | Produces |
|-------|-----------|----------|
| 1 | — | pdf-renderer service, print layout/route, signing, document sync endpoint, download button |
| 2 | Phase 1 | `download_jobs` table, worker, bundler v1, intake print, tray, full-project button |
| 3 | Phase 2 | Quality/review/citations sources + print routes, bundler extras, chart wait convention |
| 4 | Phase 3 | Paragraph-level diff module, revision-history print, flagged bundler inclusion |
| 5 | Phase 4 | TTL, rate limit, retry UX, watchdog, key rotation, metrics, Grafana, alert rules |

Each phase is independently releasable and independently tagged (`phase1-complete` … `phase5-complete`). Do not merge phases.

## Self-review notes (for the executing engineer)

Before you start executing this plan:

1. **Migration number**: the spec says `008`, this plan uses **`009`**. This is not a typo — `008_add_pipeline_runs.py` is already in the repo. If you regenerate the migration later, do not reuse `008`.
2. **Middleware prefix map**: the `PRINT_SUBJECT_BY_PREFIX` list grows twice — once in Phase 1 (4 entries) and once in Phase 4 (revision history). Keep it sorted and alphabetized.
3. **Signing subjects**: the `Subject` Literal appears in two places (Python + TypeScript). Both must extend in lockstep in Phase 4. A mismatch is a 403 at runtime.
4. **Atomic writes**: every artifact file is written via `<name>.tmp` + `os.replace`. Never skip the rename — an interrupted write would leave a half-zipped file that passes existence checks but fails SHA-256 verification.
5. **Chart-ready attribute**: `data-loading` must appear on the outermost wrapper of any element that is not yet ready to capture. If a future chart wrapper forgets it, Playwright will not wait and the PDF will be blank.
6. **No Redis**: the worker uses `SELECT … FOR UPDATE SKIP LOCKED`. Do not reach for a queue service. If throughput becomes a problem, raise worker concurrency inside the lifespan task, do not change transport.
7. **Environment variables added**: `EXPORT_SIGNING_SECRET`, `EXPORT_SIGNING_SECRET_PREVIOUS`, `EXPORTS_DIR`, `PDF_RENDERER_URL`, `FRONTEND_INTERNAL_URL`, `REGISTRY_INTERNAL_URL`, `EXPORT_INCLUDE_REVISIONS`, `EXPORT_ARTIFACT_TTL_DAYS`, `EXPORT_MAX_IN_FLIGHT_PER_USER`, `CME_COMPLIANCE_MODE`, `RENDERER_MAX_RSS_MB`. Every one of these must be in `.env.example` and `docker-compose.yml` by the end of Phase 5.

