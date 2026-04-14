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

### Task 2.3: Enqueue endpoint with dedup + audit log (TDD)

**Files:**
- Modify: `registry/export_endpoints.py`
- Modify: `registry/test_export_endpoints.py`

- [ ] **Step 1: Write the failing test**

```python
# append to registry/test_export_endpoints.py
@pytest.mark.asyncio
async def test_enqueue_project_returns_job_id() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(
            "/api/cme/export/project/thread-abc",
            json={"thread_id": "thread-abc", "graph_id": "grant_package"},
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
    assert resp.status_code == 202
    body = resp.json()
    assert "id" in body
    assert body["scope"] == "project"
    assert body["status"] in ("pending", "running")


@pytest.mark.asyncio
async def test_enqueue_project_is_idempotent() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        first = await c.post(
            "/api/cme/export/project/thread-dedup",
            json={"thread_id": "thread-dedup", "graph_id": "grant_package"},
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
        second = await c.post(
            "/api/cme/export/project/thread-dedup",
            json={"thread_id": "thread-dedup", "graph_id": "grant_package"},
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
```

- [ ] **Step 2: Run — expect FAIL (404)**

```bash
docker exec dhg-registry-api pytest registry/test_export_endpoints.py -v
```

- [ ] **Step 3: Implement the endpoint**

```python
# append to registry/export_endpoints.py
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from database import get_async_db
from models import DownloadJob
from registry.export_schemas import DownloadJobCreate, DownloadJobResponse
from registry.security_audit import record_audit_event  # existing helper


@router.post(
    "/project/{thread_id}",
    response_model=DownloadJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_project_download(
    thread_id: str,
    body: DownloadJobCreate,
    session: AsyncSession = Depends(get_async_db),
) -> DownloadJobResponse:
    if body.thread_id != thread_id:
        raise HTTPException(status_code=400, detail="thread_id mismatch")

    # Dedup: return existing pending/running job if present
    existing = await session.execute(
        select(DownloadJob)
        .where(
            and_(
                DownloadJob.thread_id == thread_id,
                DownloadJob.scope == "project",
                DownloadJob.status.in_(("pending", "running")),
            )
        )
        .order_by(DownloadJob.created_at.desc())
        .limit(1)
    )
    row = existing.scalar_one_or_none()
    if row is not None:
        return DownloadJobResponse.model_validate(row)

    job = DownloadJob(
        thread_id=thread_id,
        graph_id=body.graph_id,
        scope="project",
        status="pending",
    )
    session.add(job)
    await session.flush()
    await record_audit_event(
        session,
        action="cme_export_enqueue",
        resource_type="download_job",
        resource_id=str(job.id),
        metadata={"thread_id": thread_id, "graph_id": body.graph_id},
    )
    await session.commit()
    await session.refresh(job)
    return DownloadJobResponse.model_validate(job)
```

- [ ] **Step 4: Run — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_endpoints.py -v
```

Expected: 4 passed (2 from Task 1.9, 2 new)

- [ ] **Step 5: Commit**

```bash
git add registry/export_endpoints.py registry/test_export_endpoints.py
git commit -m "feat(export): enqueue project download with dedup + audit log"
```

---

### Task 2.4: Status, artifact stream, and list endpoints

**Files:**
- Modify: `registry/export_endpoints.py`
- Modify: `registry/test_export_endpoints.py`

- [ ] **Step 1: Write tests**

```python
# append to registry/test_export_endpoints.py
@pytest.mark.asyncio
async def test_get_job_status() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        created = await c.post(
            "/api/cme/export/project/thread-status",
            json={"thread_id": "thread-status", "graph_id": "grant_package"},
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
        job_id = created.json()["id"]
        resp = await c.get(
            f"/api/cme/export/job/{job_id}",
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


@pytest.mark.asyncio
async def test_artifact_404_while_pending() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        created = await c.post(
            "/api/cme/export/project/thread-pending",
            json={"thread_id": "thread-pending", "graph_id": "grant_package"},
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
        job_id = created.json()["id"]
        resp = await c.get(
            f"/api/cme/export/artifact/{job_id}",
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_jobs_returns_recent() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(
            "/api/cme/export/jobs",
            headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
        )
    assert resp.status_code == 200
    assert "jobs" in resp.json()
```

- [ ] **Step 2: Implement the endpoints**

```python
# append to registry/export_endpoints.py
import hashlib
from pathlib import Path
from uuid import UUID

from fastapi.responses import StreamingResponse
from registry.export_schemas import DownloadJobListResponse


@router.get("/job/{job_id}", response_model=DownloadJobResponse)
async def get_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_async_db),
) -> DownloadJobResponse:
    row = await session.get(DownloadJob, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="job not found")
    return DownloadJobResponse.model_validate(row)


@router.get("/artifact/{job_id}")
async def get_artifact(
    job_id: UUID,
    session: AsyncSession = Depends(get_async_db),
) -> StreamingResponse:
    row = await session.get(DownloadJob, job_id)
    if row is None or row.status != "succeeded" or not row.artifact_path:
        raise HTTPException(status_code=404, detail="artifact not ready")

    path = Path(row.artifact_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="artifact expired")

    # Re-validate SHA-256 before streaming
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            hasher.update(chunk)
    if hasher.hexdigest() != row.artifact_sha256:
        raise HTTPException(status_code=500, detail="artifact checksum mismatch")

    safe_name = _sanitize_filename(f"project_{row.thread_id}")
    stamp = row.completed_at.strftime("%Y-%m-%d") if row.completed_at else "undated"
    filename = f"{safe_name}_{stamp}.zip"

    def iterfile():
        with path.open("rb") as fh:
            yield from iter(lambda: fh.read(1024 * 1024), b"")

    return StreamingResponse(
        iterfile(),
        media_type="application/zip",
        headers={
            "content-disposition": f'attachment; filename="{filename}"',
            "content-length": str(row.artifact_bytes or path.stat().st_size),
            "cache-control": "no-store",
        },
    )


@router.get("/jobs", response_model=DownloadJobListResponse)
async def list_jobs(
    limit: int = 50,
    session: AsyncSession = Depends(get_async_db),
) -> DownloadJobListResponse:
    limit = max(1, min(limit, 200))
    rows = (
        await session.execute(
            select(DownloadJob).order_by(DownloadJob.created_at.desc()).limit(limit)
        )
    ).scalars().all()
    return DownloadJobListResponse(
        jobs=[DownloadJobResponse.model_validate(r) for r in rows]
    )
```

- [ ] **Step 3: Run — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_endpoints.py -v
```

Expected: 7 passed

- [ ] **Step 4: Commit**

```bash
git add registry/export_endpoints.py registry/test_export_endpoints.py
git commit -m "feat(export): add job status, artifact stream, and list endpoints"
```

---

### Task 2.5: Worker loop in FastAPI lifespan (`SKIP LOCKED`)

**Files:**
- Create: `registry/export_worker.py`
- Modify: `registry/api.py`

- [ ] **Step 1: Write the worker**

```python
# registry/export_worker.py
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import text

from database import async_session
from models import DownloadJob

log = logging.getLogger("dhg.export.worker")

POLL_INTERVAL_SECONDS = 2.0


async def _claim_next_job() -> DownloadJob | None:
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                text(
                    """
                    SELECT id FROM download_jobs
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                    """
                )
            )
            row = result.first()
            if row is None:
                return None
            job = await session.get(DownloadJob, row[0])
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            return job


async def _complete(job_id, *, status: str, **fields: object) -> None:
    async with async_session() as session:
        async with session.begin():
            row = await session.get(DownloadJob, job_id)
            if row is None:
                return
            row.status = status
            row.completed_at = datetime.now(timezone.utc)
            for k, v in fields.items():
                setattr(row, k, v)


async def _process(job: DownloadJob) -> None:
    from registry.export_bundler import assemble_project_bundle

    try:
        result = await assemble_project_bundle(job.thread_id)
        await _complete(
            job.id,
            status="succeeded",
            artifact_path=str(result.path),
            artifact_sha256=result.sha256,
            artifact_bytes=result.bytes,
        )
    except Exception as exc:  # pragma: no cover - exercised in integration
        log.exception("bundle failed for job %s", job.id)
        await _complete(job.id, status="failed", error=str(exc)[:1000])


async def run_worker(stop_event: asyncio.Event) -> None:
    log.info("export worker started")
    while not stop_event.is_set():
        try:
            job = await _claim_next_job()
        except Exception:
            log.exception("worker claim loop error")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            continue
        if job is None:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=POLL_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass
            continue
        await _process(job)
    log.info("export worker stopped")
```

- [ ] **Step 2: Wire into the FastAPI `lifespan` in `api.py`**

```python
# registry/api.py — inside the existing lifespan context manager
import asyncio
from contextlib import asynccontextmanager

from registry.export_worker import run_worker

_worker_stop = asyncio.Event()
_worker_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_task
    _worker_stop.clear()
    _worker_task = asyncio.create_task(run_worker(_worker_stop))
    try:
        yield
    finally:
        _worker_stop.set()
        if _worker_task is not None:
            await _worker_task
```

If a `lifespan` already exists, merge: start the task in the setup block and await it in the teardown block; do not replace existing lifespan logic.

- [ ] **Step 3: Restart the API and tail logs**

```bash
docker compose up -d dhg-registry-api
docker logs -f dhg-registry-api | grep "export worker"
```

Expected: `export worker started` on boot, `export worker stopped` on shutdown.

- [ ] **Step 4: Commit**

```bash
git add registry/export_worker.py registry/api.py
git commit -m "feat(export): background worker with SKIP LOCKED claim"
```

---

### Task 2.6: Intake print route + IntakePrint component

**Files:**
- Create: `frontend/src/app/print/cme/project/[threadId]/intake/page.tsx`
- Create: `frontend/src/components/print/intake-print.tsx`
- Modify: `registry/export_service.py`
- Modify: `registry/cme_endpoints.py`

- [ ] **Step 1: Create the IntakePrint component**

```typescript
// frontend/src/components/print/intake-print.tsx
import { PrintShell } from "./print-shell";

export interface IntakePrintProps {
  projectName: string;
  generatedAt: string;
  intake: Record<string, unknown>;
}

function renderValue(value: unknown): string {
  if (value == null) return "—";
  if (Array.isArray(value)) return value.map((v) => String(v)).join(", ");
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

export function IntakePrint({ projectName, generatedAt, intake }: IntakePrintProps) {
  const sections = Object.entries(intake);
  return (
    <PrintShell title={projectName} subtitle="Project Intake" generatedAt={generatedAt}>
      <div className="space-y-6 text-[#32374A]">
        {sections.map(([section, fields]) => (
          <section key={section}>
            <h2 className="mb-2 border-b border-[#E4E4E7] pb-1 text-base font-semibold">
              {section}
            </h2>
            <dl className="grid grid-cols-[180px_1fr] gap-x-4 gap-y-1 text-sm">
              {Object.entries(fields as Record<string, unknown>).map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="text-[#71717A]">{k}</dt>
                  <dd className="whitespace-pre-wrap">{renderValue(v)}</dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
      </div>
    </PrintShell>
  );
}
```

- [ ] **Step 2: Create the route**

```typescript
// frontend/src/app/print/cme/project/[threadId]/intake/page.tsx
import { notFound } from "next/navigation";

import { IntakePrint } from "@/components/print/intake-print";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ threadId: string }>;
  searchParams: Promise<{ t?: string }>;
}

async function fetchIntake(threadId: string, token: string) {
  const registry = process.env.REGISTRY_INTERNAL_URL ?? "http://dhg-registry-api:8000";
  const res = await fetch(
    `${registry}/api/cme/export/internal/project/${threadId}/intake`,
    { headers: { "X-Print-Token": token }, cache: "no-store" },
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`registry fetch failed: ${res.status}`);
  return res.json() as Promise<{
    project_name: string;
    intake: Record<string, unknown>;
  }>;
}

export default async function Page({ params, searchParams }: Props) {
  const { threadId } = await params;
  const { t } = await searchParams;
  if (!t) notFound();
  const data = await fetchIntake(threadId, t);
  if (!data) notFound();
  return (
    <IntakePrint
      projectName={data.project_name}
      generatedAt={new Date().toISOString()}
      intake={data.intake}
    />
  );
}
```

- [ ] **Step 3: Add the internal endpoint on the registry**

```python
# registry/export_endpoints.py — append
@router.get("/internal/project/{thread_id}/intake")
async def internal_project_intake(
    thread_id: str,
    x_print_token: str | None = Header(default=None, alias="X-Print-Token"),
    session: AsyncSession = Depends(get_async_db),
) -> dict:
    secret = os.environ.get("EXPORT_SIGNING_SECRET")
    if not secret or not x_print_token:
        raise HTTPException(status_code=401, detail="missing token")
    try:
        payload = verify_print_token(x_print_token, secret=secret)
    except PrintTokenExpired:
        raise HTTPException(status_code=401, detail="token expired")
    except PrintTokenInvalid:
        raise HTTPException(status_code=401, detail="invalid token")
    if payload.subject != "cme_project_intake" or payload.resource_id != thread_id:
        raise HTTPException(status_code=403, detail="scope mismatch")

    from models import CMEProject
    row = (
        await session.execute(
            select(CMEProject).where(CMEProject.pipeline_thread_id == thread_id).limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {"project_name": row.name, "intake": row.intake or {}}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/print/cme/project frontend/src/components/print/intake-print.tsx \
        registry/export_endpoints.py
git commit -m "feat(export): project intake print route + internal endpoint"
```

---

### Task 2.7: Bundler v1 + atomic zip writer

**Files:**
- Create: `registry/export_bundler.py`
- Create: `registry/test_export_bundler.py`

- [ ] **Step 1: Write the failing test**

```python
# registry/test_export_bundler.py
import hashlib
import os
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from registry.export_bundler import BundleResult, assemble_project_bundle


@pytest.mark.asyncio
async def test_bundle_contains_required_members(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EXPORTS_DIR", str(tmp_path))

    fake_project = {
        "name": "Diabetes Management",
        "intake": {"audience": {"specialty": "Endocrinology"}},
        "documents": [
            {"slug": "needs-assessment", "thread_id": "t-1"},
            {"slug": "grant-writer", "thread_id": "t-1"},
        ],
    }
    with patch("registry.export_bundler.load_project_for_thread",
               new=AsyncMock(return_value=fake_project)), \
         patch("registry.export_bundler.render_via_renderer",
               new=AsyncMock(return_value=b"%PDF-1.7\nfake")):
        result: BundleResult = await assemble_project_bundle("t-1")

    assert result.path.exists()
    assert result.bytes > 0
    assert hashlib.sha256(result.path.read_bytes()).hexdigest() == result.sha256

    with zipfile.ZipFile(result.path) as zf:
        names = set(zf.namelist())
    assert "README.txt" in names
    assert "intake.pdf" in names
    assert "project.json" in names
    assert any(n.startswith("documents/") and n.endswith(".pdf") for n in names)

    # Ensure no .tmp artifact left behind
    assert not any(p.suffix == ".tmp" for p in Path(tmp_path).iterdir())
```

- [ ] **Step 2: Run — expect FAIL**

```bash
docker exec dhg-registry-api pytest registry/test_export_bundler.py -v
```

- [ ] **Step 3: Implement the bundler**

```python
# registry/export_bundler.py
from __future__ import annotations

import hashlib
import json
import logging
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from registry.export_service import build_print_url, render_via_renderer

log = logging.getLogger("dhg.export.bundler")


@dataclass(frozen=True)
class BundleResult:
    path: Path
    sha256: str
    bytes: int


def _exports_dir() -> Path:
    path = Path(os.environ.get("EXPORTS_DIR", "/exports"))
    path.mkdir(parents=True, exist_ok=True)
    return path


async def load_project_for_thread(thread_id: str) -> dict | None:
    """Thin shim so tests can patch it."""
    from sqlalchemy import select

    from database import async_session
    from models import CMEProject, CMEDocument

    async with async_session() as session:
        project_row = (
            await session.execute(
                select(CMEProject).where(CMEProject.pipeline_thread_id == thread_id).limit(1)
            )
        ).scalar_one_or_none()
        if project_row is None:
            return None
        document_rows = (
            await session.execute(
                select(CMEDocument)
                .where(CMEDocument.project_id == project_row.id)
                .order_by(CMEDocument.created_at.asc())
            )
        ).scalars().all()
        return {
            "name": project_row.name,
            "intake": project_row.intake or {},
            "documents": [
                {
                    "slug": (d.agent_source or "document").lower().replace("_", "-"),
                    "thread_id": thread_id,
                }
                for d in document_rows
            ],
        }


def _readme(project_name: str, generated_at: str, doc_count: int) -> str:
    return (
        "DHG AI Factory — CME Project Archive\n"
        "====================================\n\n"
        f"Project:       {project_name}\n"
        f"Generated:     {generated_at}\n"
        f"Documents:     {doc_count}\n"
        f"Generator:     dhg-registry-api / export_bundler v1\n\n"
        "Contents:\n"
        "  - intake.pdf          — Project intake sections\n"
        "  - documents/*.pdf     — Each CME document\n"
        "  - project.json        — Canonical intake + metadata\n\n"
        "AI-assisted output — verify against source material.\n"
    )


async def assemble_project_bundle(thread_id: str) -> BundleResult:
    project = await load_project_for_thread(thread_id)
    if project is None:
        raise ValueError(f"project not found for thread {thread_id}")

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    job_uid = uuid4().hex

    # Render intake PDF
    intake_url = build_print_url(
        subject="cme_project_intake",
        resource_id=thread_id,
        path_prefix="/print/cme/project/",
    ).replace(f"/print/cme/project/{thread_id}?", f"/print/cme/project/{thread_id}/intake?")
    intake_pdf = await render_via_renderer(intake_url)

    # Render each document PDF
    document_pdfs: list[tuple[str, bytes]] = []
    for i, doc in enumerate(project["documents"]):
        url = build_print_url(
            subject="cme_document",
            resource_id=thread_id,
            path_prefix="/print/cme/document/",
        )
        pdf = await render_via_renderer(url)
        name = f"documents/{i:02d}_{doc['slug']}.pdf"
        document_pdfs.append((name, pdf))

    exports_dir = _exports_dir()
    tmp_path = exports_dir / f"{job_uid}.zip.tmp"
    final_path = exports_dir / f"{job_uid}.zip"

    with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "README.txt",
            _readme(project["name"], generated_at, len(document_pdfs)),
        )
        zf.writestr("intake.pdf", intake_pdf)
        for name, pdf in document_pdfs:
            zf.writestr(name, pdf)
        zf.writestr(
            "project.json",
            json.dumps(
                {
                    "name": project["name"],
                    "thread_id": thread_id,
                    "generated_at": generated_at,
                    "intake": project["intake"],
                    "document_count": len(document_pdfs),
                },
                indent=2,
            ),
        )

    hasher = hashlib.sha256()
    with tmp_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            hasher.update(chunk)
    size = tmp_path.stat().st_size

    os.replace(tmp_path, final_path)  # atomic rename
    log.info("bundle written path=%s bytes=%d", final_path, size)

    return BundleResult(path=final_path, sha256=hasher.hexdigest(), bytes=size)
```

- [ ] **Step 4: Run — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_bundler.py -v
```

Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add registry/export_bundler.py registry/test_export_bundler.py
git commit -m "feat(export): bundler v1 with atomic zip writer"
```

---

### Task 2.8: Frontend downloads Zustand store

**Files:**
- Create: `frontend/src/stores/downloads-store.ts`

- [ ] **Step 1: Write the store**

```typescript
// frontend/src/stores/downloads-store.ts
"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type DownloadStatus = "pending" | "running" | "succeeded" | "failed";

export interface DownloadRecord {
  jobId: string;
  threadId: string;
  projectName: string;
  status: DownloadStatus;
  createdAt: string;
  completedAt?: string;
  error?: string;
}

interface DownloadsState {
  records: DownloadRecord[];
  trayOpen: boolean;
  upsert: (record: DownloadRecord) => void;
  remove: (jobId: string) => void;
  setStatus: (jobId: string, status: DownloadStatus, fields?: Partial<DownloadRecord>) => void;
  openTray: () => void;
  closeTray: () => void;
  toggleTray: () => void;
}

export const useDownloadsStore = create<DownloadsState>()(
  persist(
    (set) => ({
      records: [],
      trayOpen: false,
      upsert: (record) =>
        set((s) => {
          const existing = s.records.find((r) => r.jobId === record.jobId);
          if (existing) {
            return {
              records: s.records.map((r) =>
                r.jobId === record.jobId ? { ...r, ...record } : r,
              ),
            };
          }
          return { records: [record, ...s.records].slice(0, 50) };
        }),
      remove: (jobId) =>
        set((s) => ({ records: s.records.filter((r) => r.jobId !== jobId) })),
      setStatus: (jobId, status, fields) =>
        set((s) => ({
          records: s.records.map((r) =>
            r.jobId === jobId ? { ...r, status, ...(fields ?? {}) } : r,
          ),
        })),
      openTray: () => set({ trayOpen: true }),
      closeTray: () => set({ trayOpen: false }),
      toggleTray: () => set((s) => ({ trayOpen: !s.trayOpen })),
    }),
    {
      name: "dhg.inbox.downloads",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ records: state.records }),
    },
  ),
);
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/downloads-store.ts
git commit -m "feat(frontend): persistent downloads store"
```

---

### Task 2.9: Polling hook `useDownloadPolling`

**Files:**
- Create: `frontend/src/hooks/use-download-polling.ts`
- Modify: `frontend/src/lib/exportApi.ts`

- [ ] **Step 1: Extend `exportApi.ts`**

```typescript
// frontend/src/lib/exportApi.ts — append
export interface DownloadJobResponse {
  id: string;
  thread_id: string;
  graph_id: string;
  scope: "document" | "project";
  status: "pending" | "running" | "succeeded" | "failed";
  artifact_bytes: number | null;
  artifact_sha256: string | null;
  created_at: string;
  completed_at: string | null;
  error: string | null;
}

export async function enqueueProject(threadId: string, graphId: string): Promise<DownloadJobResponse> {
  const res = await fetch(`${BASE}/project/${encodeURIComponent(threadId)}`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, graph_id: graphId }),
  });
  if (!res.ok) throw new Error(`enqueue failed: ${res.status}`);
  return res.json();
}

export async function getJob(jobId: string): Promise<DownloadJobResponse> {
  const res = await fetch(`${BASE}/job/${encodeURIComponent(jobId)}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`job fetch failed: ${res.status}`);
  return res.json();
}

export function artifactUrl(jobId: string): string {
  return `${BASE}/artifact/${encodeURIComponent(jobId)}`;
}
```

- [ ] **Step 2: Write the hook**

```typescript
// frontend/src/hooks/use-download-polling.ts
"use client";

import { useEffect } from "react";

import { getJob } from "@/lib/exportApi";
import { useDownloadsStore } from "@/stores/downloads-store";

const POLL_MS = 2000;

export function useDownloadPolling(): void {
  const records = useDownloadsStore((s) => s.records);
  const setStatus = useDownloadsStore((s) => s.setStatus);

  useEffect(() => {
    const active = records.filter((r) => r.status === "pending" || r.status === "running");
    if (active.length === 0) return;

    let cancelled = false;
    let failureCount = 0;

    const tick = async () => {
      for (const record of active) {
        try {
          const job = await getJob(record.jobId);
          if (cancelled) return;
          setStatus(job.id, job.status, {
            completedAt: job.completed_at ?? undefined,
            error: job.error ?? undefined,
          });
          failureCount = 0;
        } catch {
          failureCount += 1;
        }
      }
    };

    const delay = Math.min(POLL_MS * 2 ** failureCount, 30_000);
    const handle = setInterval(tick, delay);
    void tick();
    return () => {
      cancelled = true;
      clearInterval(handle);
    };
  }, [records, setStatus]);
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/use-download-polling.ts frontend/src/lib/exportApi.ts
git commit -m "feat(frontend): polling hook + enqueue/getJob API client"
```

---

### Task 2.10: Downloads tray component

**Files:**
- Create: `frontend/src/components/review/downloads-tray.tsx`

- [ ] **Step 1: Write the component**

```typescript
// frontend/src/components/review/downloads-tray.tsx
"use client";

import { X, Download, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";

import { artifactUrl } from "@/lib/exportApi";
import { useDownloadsStore, type DownloadRecord } from "@/stores/downloads-store";
import { cn } from "@/lib/utils";

function StatusIcon({ status }: { status: DownloadRecord["status"] }) {
  if (status === "succeeded") return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
  if (status === "failed") return <AlertCircle className="h-4 w-4 text-destructive" />;
  return <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />;
}

export function DownloadsTray() {
  const trayOpen = useDownloadsStore((s) => s.trayOpen);
  const records = useDownloadsStore((s) => s.records);
  const closeTray = useDownloadsStore((s) => s.closeTray);
  const remove = useDownloadsStore((s) => s.remove);

  if (!trayOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-40 flex w-96 flex-col border-l border-border bg-background shadow-xl">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">Downloads</h2>
        <button
          type="button"
          onClick={closeTray}
          aria-label="Close downloads tray"
          className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-auto">
        {records.length === 0 ? (
          <div className="p-6 text-center text-xs text-muted-foreground">
            No downloads yet.
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {records.map((r) => (
              <li key={r.jobId} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {r.projectName}
                    </p>
                    <p className="mt-0.5 text-[10px] text-muted-foreground">
                      {new Date(r.createdAt).toLocaleString()}
                    </p>
                    {r.status === "failed" && r.error && (
                      <p className="mt-1 text-[11px] text-destructive">{r.error}</p>
                    )}
                  </div>
                  <StatusIcon status={r.status} />
                </div>

                <div className="mt-2 flex items-center gap-2">
                  {r.status === "succeeded" && (
                    <a
                      href={artifactUrl(r.jobId)}
                      className={cn(
                        "inline-flex items-center gap-1 rounded-md border border-border",
                        "bg-[color:var(--color-dhg-orange)] px-2.5 py-1 text-xs font-medium text-white",
                      )}
                    >
                      <Download className="h-3.5 w-3.5" />
                      Save zip
                    </a>
                  )}
                  <button
                    type="button"
                    onClick={() => remove(r.jobId)}
                    className="text-[11px] text-muted-foreground hover:text-foreground"
                  >
                    Dismiss
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/review/downloads-tray.tsx
git commit -m "feat(inbox): downloads tray component"
```

---

### Task 2.11: Full-project button in inbox header + tray mount

**Files:**
- Modify: `frontend/src/components/review/inbox-master-detail.tsx`

- [ ] **Step 1: Import the tray, hook, store, and button wiring**

```typescript
// frontend/src/components/review/inbox-master-detail.tsx — additions
import { Download } from "lucide-react";

import { DownloadsTray } from "./downloads-tray";
import { useDownloadsStore } from "@/stores/downloads-store";
import { useDownloadPolling } from "@/hooks/use-download-polling";
import { enqueueProject } from "@/lib/exportApi";
```

- [ ] **Step 2: Call the polling hook near the top of the component**

```typescript
// inside InboxMasterDetail()
useDownloadPolling();

const upsertDownload = useDownloadsStore((s) => s.upsert);
const openTray = useDownloadsStore((s) => s.openTray);
const trayOpen = useDownloadsStore((s) => s.trayOpen);
const toggleTray = useDownloadsStore((s) => s.toggleTray);

const handleDownloadProject = async () => {
  if (!selectedReview) return;
  try {
    const job = await enqueueProject(selectedReview.threadId, selectedReview.graphId);
    upsertDownload({
      jobId: job.id,
      threadId: selectedReview.threadId,
      projectName: GRAPH_LABELS[selectedReview.graphId] ?? selectedReview.graphId,
      status: job.status,
      createdAt: job.created_at,
    });
    openTray();
  } catch (err) {
    console.error(err);
  }
};
```

- [ ] **Step 3: Add the button to the page header, next to the pending count**

```typescript
// in the existing header JSX, next to the refresh button:
<button
  type="button"
  onClick={handleDownloadProject}
  disabled={!selectedReview}
  className="inline-flex items-center gap-1.5 rounded-md border border-[color:var(--color-dhg-orange)] bg-background px-2.5 py-1 text-xs text-[color:var(--color-dhg-orange)] hover:bg-[color:var(--color-dhg-orange)]/10 transition-colors disabled:opacity-50"
>
  <Download className="h-3.5 w-3.5" />
  Full project
</button>
<button
  type="button"
  onClick={toggleTray}
  aria-label="Open downloads tray"
  className="h-8 w-8 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
>
  <Download className="h-4 w-4" />
</button>
```

- [ ] **Step 4: Mount the tray at the bottom of the returned JSX**

```typescript
// inside the outer wrapper div, as a sibling of the main flex container:
<DownloadsTray />
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/review/inbox-master-detail.tsx
git commit -m "feat(inbox): add full-project download button, tray mount, polling"
```

---

### Task 2.12: End-to-end integration test (worker round-trip)

**Files:**
- Create: `registry/test_export_integration.py`

- [ ] **Step 1: Write the test**

```python
# registry/test_export_integration.py
import asyncio
import hashlib
import zipfile
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api import app
from registry.export_worker import _claim_next_job, _process


@pytest.mark.asyncio
async def test_enqueue_then_worker_produces_zip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EXPORTS_DIR", str(tmp_path))

    fake_project = {
        "name": "Integration Project",
        "intake": {"audience": {"specialty": "Cardiology"}},
        "documents": [{"slug": "needs-assessment", "thread_id": "t-int"}],
    }
    with patch("registry.export_bundler.load_project_for_thread",
               new=AsyncMock(return_value=fake_project)), \
         patch("registry.export_bundler.render_via_renderer",
               new=AsyncMock(return_value=b"%PDF-1.7\nfake")):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            enqueue = await c.post(
                "/api/cme/export/project/t-int",
                json={"thread_id": "t-int", "graph_id": "grant_package"},
                headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
            )
            assert enqueue.status_code == 202
            job_id = enqueue.json()["id"]

            job = await _claim_next_job()
            assert job is not None
            await _process(job)

            status = await c.get(
                f"/api/cme/export/job/{job_id}",
                headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
            )
            assert status.json()["status"] == "succeeded"

            artifact = await c.get(
                f"/api/cme/export/artifact/{job_id}",
                headers={"Cf-Access-Jwt-Assertion": "dev-bypass"},
            )
            assert artifact.status_code == 200
            assert artifact.headers["content-type"] == "application/zip"

    sha = hashlib.sha256(artifact.content).hexdigest()
    assert sha == status.json()["artifact_sha256"]

    with zipfile.ZipFile(tmp_path / f"{job_id}.zip") as zf:
        assert "README.txt" in zf.namelist()
```

- [ ] **Step 2: Run — expect PASS**

```bash
docker exec dhg-registry-api pytest registry/test_export_integration.py -v
```

Expected: 1 passed

- [ ] **Step 3: Tag Phase 2 complete**

```bash
git add registry/test_export_integration.py
git commit -m "test(export): end-to-end worker round-trip integration test"
git tag phase2-complete
```

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

