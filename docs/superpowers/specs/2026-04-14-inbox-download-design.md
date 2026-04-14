# Inbox Document & Project Download Feature — Design

**Date:** 2026-04-14
**Status:** Approved (brainstorming phase)
**Owner:** Stephen Webber
**Next step:** Writing-plans skill → implementation plan

---

## 1. Problem

The inbox at `/inbox` lets a reviewer approve, revise, or reject in-flight LangGraph review threads, but offers no way to export the document under review or the full project archive.

For CME compliance, reviewers need a durable record of what was reviewed, when, by whom, and with what quality signals. "Downloaded from browser" is not a good enough archive — the bundle must be reproducible, auditable, and self-contained.

The feature ships two download actions on the inbox:

1. **Download current document** — the manuscript currently in the review panel, as Markdown + PDF in a zip.
2. **Download full project** — the entire audit-trail bundle for the selected review thread, as a structured zip containing documents, intake metadata, quality signals, review history, and machine-readable metadata.

## 2. Decisions (locked during brainstorming)

| # | Question | Decision | Rationale |
|---|---|---|---|
| Q1 | Scope | Both buttons (document + full project) | Each serves a different reviewer workflow |
| Q2 | File format | Markdown + PDF, bundled in a zip | MD is source-of-truth, PDF is print-ready, both cost nothing to keep |
| Q3 | Full-project bundle contents | Full audit trail (docs + intake + quality + review history + metadata) | CME compliance requires a reproducible archive |
| Q4 | Button placement | Split: doc button on the manuscript header, project button in the page header | Each button sits next to its scope — affordance matches mental model |
| Q5 | Frontend vs backend export | Backend (new registry endpoint + sibling service) | PDF rendering belongs server-side; one place for auth, audit, rate limits |
| Q6 | PDF rendering stack | Playwright + Next.js print routes (sibling `dhg-pdf-renderer` service) | Charts + dynamic layouts require Chromium; print routes reuse real React components |
| Q7 | Sync vs async | Document sync, project async (jobs table) | Full-project bundle is 15–30s of work; needs durable record, stampede control, retries, and share links |
| Q8 | Permissions | Any user with page access can download | No extra role gate |
| Q9 | Bundle shape | MD+PDF pairs, numeric prefixes, README with checksums, `project.json` metadata; round-by-round diffs deferred to Phase 4; citations as separate JSON | Deterministic structure for compliance tooling |

## 3. Architecture

```
┌─────────────────┐                    ┌────────────────────┐
│  dhg-frontend   │                    │  dhg-registry-api  │
│  (Next.js)      │   1. POST export   │  (FastAPI)         │
│                 │ ─────────────────▶ │                    │
│  [Download]     │                    │  creates job row   │
│  [Full project] │ ◀──── 202 job_id ──│  in download_jobs  │
│                 │                    │                    │
│  Downloads tray │   2. GET job/:id   │                    │
│  (polls every   │ ─────────────────▶ │  returns status +  │
│   3s)           │ ◀── status/artifact│  artifact URL      │
│                 │                    │                    │
│  /print/*       │                    └─────────┬──────────┘
│  routes         │                              │
│       ▲         │                              │ 3. enqueue
│       │         │                              ▼
│       │         │                    ┌────────────────────┐
│       │         │  4. Playwright     │ dhg-pdf-renderer   │
│       └─────────┼──── GET /print/… ──│  (new service)     │
│                 │                    │                    │
│                 │                    │  worker loop polls │
│                 │                    │  download_jobs     │
│                 │                    │  launches Chromium │
│                 │                    │  writes artifact   │
│                 │                    │  to /var/exports   │
│                 │                    │  updates job row   │
│                 │                    └─────────┬──────────┘
│                 │                              │
│                 │                              │ 5. artifact URL
│                 │ ◀────────────────────────────┘
│                 │   6. GET /api/cme/export/artifact/:id
│                 │ ──────────────────▶  streams zip to browser
└─────────────────┘
```

### 3.1 Components

| Component | New/Changed | Purpose |
|---|---|---|
| `dhg-pdf-renderer` | **NEW service** | Playwright worker container. Polls `download_jobs`, renders Next.js print routes to PDF, assembles zips, writes artifacts to shared volume. |
| `download_jobs` table | **NEW alembic migration** | Tracks each export job: status, scope, thread, artifact path, checksum, requester. |
| `/api/cme/export/*` | **NEW registry endpoints** | POST to enqueue, GET for status, GET to stream artifact, GET to list recent jobs. |
| `/print/document/[id]`, `/print/project/[id]`, `/print/intake/[id]`, `/print/quality/[id]`, `/print/review-history/[id]` | **NEW Next.js routes** | Print-optimized React pages reusing existing review components. Auth via signed short-lived token in query string. |
| Review panel "Download" button | **NEW UI** | Top-right of manuscript header in `review-panel.tsx`. Sync fetch → streams zip. |
| Inbox page "Full project" button | **NEW UI** | In the standard page header in `inbox-master-detail.tsx`. POST → tray row. |
| Downloads tray | **NEW component** | Slide-out drawer (shadcn `Sheet`). Lists recent jobs, polls active ones, click-through to artifact. Mounted in `app-shell.tsx` for cross-page visibility. |
| `dhg_exports` Docker volume | **NEW** | Mounted on `dhg-registry-api` (ro) and `dhg-pdf-renderer` (rw). Holds zip artifacts until TTL cleanup. |

### 3.2 Data flow — document scope (sync)

1. User clicks "Download" in review panel.
2. Frontend hits `GET /api/cme/export/document/{thread_id}?format=zip`.
3. Registry calls `dhg-pdf-renderer`'s `POST /render-sync { url, token }`, streams the response body zip back to the browser.
4. No job row — logged only. Document downloads are small (< 2s) and don't need a durable record.

### 3.3 Data flow — project scope (async)

1. User clicks "Full project" in page header.
2. Frontend: `POST /api/cme/export/project/{thread_id}` → 202 `{ job_id, status: "queued" }`.
3. Registry inserts `download_jobs` row (`status=queued`), returns job_id.
4. `dhg-pdf-renderer` worker loop sees the queued row via `SELECT … FOR UPDATE SKIP LOCKED`, flips to `running`, pulls data from registry + LangGraph state, renders N print routes through headless Chromium, assembles zip into `/var/exports/{job_id}.zip`, updates row to `done` with `artifact_path`, `artifact_sha256`, `artifact_bytes`.
5. Frontend tray polls `GET /api/cme/export/job/{job_id}` every 3s, sees `done`, shows download link.
6. User clicks link → `GET /api/cme/export/artifact/{job_id}` → registry streams from shared volume.
7. Audit row: `security_audit_log` gets `action='export.download'` with user, job_id, artifact sha256.

### 3.4 Key design choices

- **Document scope sync, project scope async.** Two code paths, justified by the 30-second render delta. Document downloads never need a tray row; project downloads always need one.
- **Standalone `dhg-pdf-renderer` service.** Chromium is isolated from the data layer. Can be scaled or restarted without touching registry-api.
- **Print routes reuse real React components.** `DocumentViewer`, `ReflectionPanel`, brand tokens, shadcn — one source of truth for styling. No template drift.
- **Signed short-lived HMAC tokens for print route auth.** The renderer doesn't need user JWTs or Cloudflare Access cookies. Token is `HMAC-SHA256(PDF_RENDER_SIGNING_KEY, "{thread_id}:{scope}:{exp}")` with 60-second expiry.
- **Shared Docker volume for artifacts.** No object storage dependency. TTL cleanup (Phase 5) deletes rows + files older than 30 days.
- **`FOR UPDATE SKIP LOCKED`** is the worker queue primitive. Postgres-specific; relies on staying on Postgres, which is our standing decision.

## 4. Backend detail

### 4.1 `download_jobs` table (alembic migration 008)

```python
class DownloadJob(Base):
    __tablename__ = "download_jobs"
    id = Column(UUID, primary_key=True, server_default=text("gen_random_uuid()"))
    thread_id = Column(String, nullable=False, index=True)
    graph_id = Column(String, nullable=False)
    scope = Column(String, nullable=False)          # 'document' | 'project'
    status = Column(String, nullable=False, index=True)  # 'queued'|'running'|'done'|'failed'
    artifact_path = Column(String, nullable=True)
    artifact_sha256 = Column(String, nullable=True)
    artifact_bytes = Column(BigInteger, nullable=True)
    created_by = Column(String, nullable=False)     # user email from JWT
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_download_jobs_status_created", "status", "created_at"),
        CheckConstraint("scope IN ('document','project')", name="ck_scope"),
        CheckConstraint("status IN ('queued','running','done','failed')", name="ck_status"),
    )
```

Composite index on `(status, created_at)` makes the worker's claim query index-only.

### 4.2 Registry endpoints (`registry/export_endpoints.py`)

```
# Synchronous — document scope
GET  /api/cme/export/document/{thread_id}
     → 200 application/zip (streams)
     → 404 thread not found
     → 503 renderer unreachable

# Async — project scope
POST /api/cme/export/project/{thread_id}
     → 202 { job_id, status: "queued", poll_url }
     → 200 { job_id, status: "running" } if a job already exists (dedup)

GET  /api/cme/export/job/{job_id}
     → 200 { job_id, status, scope, created_at, completed_at, error, artifact_url? }
     → 403 if job.created_by != current user AND user is not admin

GET  /api/cme/export/artifact/{job_id}
     → 200 application/zip (streams from shared volume)
     → 403 if job.created_by != current user AND user is not admin
     → 404 if artifact_path missing or job not done
     → writes security_audit_log row: action='export.download'

GET  /api/cme/export/jobs?limit=20
     → 200 [ … last 20 jobs for current user … ]
     → powers the Downloads tray
```

Pydantic schemas live in `registry/export_schemas.py`. All use `model_config = ConfigDict(extra='forbid')` per the serializer-drift rule.

**Dedup**: `POST /project` checks for an existing `queued` or `running` job on the same `thread_id` + `scope`; returns that job_id with 200, not a new one. Prevents double-click stampede.

### 4.3 `dhg-pdf-renderer` service layout

```
services/pdf-renderer/
├── Dockerfile           # python:3.12-slim + playwright install chromium
├── requirements.txt     # fastapi, uvicorn, playwright, psycopg2-binary, sqlalchemy, httpx
├── pyproject.toml
├── src/
│   ├── main.py          # FastAPI app + /render-sync + /health
│   ├── worker.py        # asyncio loop polling download_jobs
│   ├── renderer.py      # Playwright browser context manager
│   ├── bundler.py       # assemble_project_bundle(thread_id) -> zip bytes
│   ├── signing.py       # HMAC token sign/verify
│   └── sources/
│       ├── registry.py       # SQLAlchemy queries against shared DB
│       ├── langgraph.py      # httpx → LangGraph Cloud
│       ├── quality.py        # quality signals extraction (Phase 3)
│       ├── review_history.py # audit log + review actions (Phase 3)
│       └── citations.py      # citation_checker outputs (Phase 3)
```

Two things run in the container:
- **FastAPI** on port 8014: `POST /render-sync` (document scope), `GET /health`.
- **Async worker loop** started by `main.py` lifespan: polls `download_jobs` every 2s, claims with `FOR UPDATE SKIP LOCKED`, runs `assemble_project_bundle`, updates row.

One Chromium browser launched at startup, one new `BrowserContext` per render for isolation.

### 4.4 Service-to-service auth on print routes

Shared secret `PDF_RENDER_SIGNING_KEY` in both `dhg-frontend` and `dhg-pdf-renderer` env.

```
token = HMAC-SHA256(secret, "{thread_id}:{scope}:{exp}")  # exp = unix timestamp, 60s out
url   = http://dhg-frontend:3000/print/document/{thread_id}?section={agent}&token={token}&exp={exp}
```

Next.js `middleware.ts` has a bypass clause for `/print/*`:
- Extracts `token` + `exp` from query string.
- Rejects if missing, expired, or signature mismatch.
- Uses `timingSafeEqual` from `node:crypto` to avoid timing attacks.

Print routes are internal-only by network — they resolve via `http://dhg-frontend:3000` (Docker-internal hostname) and have no Cloudflare Access rule pointed at them externally.

### 4.5 Docker compose additions (`docker-compose.override.yml`)

```yaml
volumes:
  dhg_exports: {}

services:
  dhg-registry-api:
    volumes:
      - dhg_exports:/var/exports:ro
    environment:
      - PDF_RENDERER_URL=http://dhg-pdf-renderer:8014

  dhg-frontend:
    environment:
      - PDF_RENDER_SIGNING_KEY=${PDF_RENDER_SIGNING_KEY}

  dhg-pdf-renderer:
    build: ./services/pdf-renderer
    container_name: dhg-pdf-renderer
    networks: [dhg-network]
    shm_size: 2gb
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - LANGCHAIN_API_KEY=${LANGCHAIN_API_KEY}
      - LANGGRAPH_CLOUD_URL=${LANGGRAPH_CLOUD_URL}
      - FRONTEND_INTERNAL_URL=http://dhg-frontend:3000
      - PDF_RENDER_SIGNING_KEY=${PDF_RENDER_SIGNING_KEY}
    volumes:
      - dhg_exports:/var/exports:rw
    depends_on: [dhg-registry-db, dhg-frontend]
    restart: unless-stopped
```

`shm_size: 2gb` is required for Chromium; without it, renders crash on large documents.

### 4.6 Where each bundle file comes from

| File in bundle | Data source | Rendering |
|---|---|---|
| `README.md` | Worker-generated manifest listing every file + sha256 | Plain text |
| `00-intake/intake.md` | Registry `projects` table (CME metadata) | Jinja template |
| `00-intake/intake.pdf` | — | Playwright → `/print/intake/{thread_id}` |
| `01-documents/{nn}-{agent}.md` | LangGraph thread state `values[document_{agent}]` | From state, straight MD |
| `01-documents/{nn}-{agent}.pdf` | — | Playwright → `/print/document/{thread_id}?section={agent}` |
| `02-quality/quality-signals.md` | Registry quality tables | Jinja template (Phase 3) |
| `02-quality/quality-signals.pdf` | — | Playwright → `/print/quality/{thread_id}` (Phase 3) |
| `03-review-history/review-log.md` | `security_audit_log` + review actions in thread state | Jinja template (Phase 3) |
| `03-review-history/review-log.pdf` | — | Playwright → `/print/review-history/{thread_id}` (Phase 3) |
| `03-review-history/rounds/round-{n}-diff.md` | LangGraph checkpoint history | Semantic paragraph diff (Phase 4) |
| `04-metadata/project.json` | Worker assembles from registry + thread metadata | `json.dumps` |
| `04-metadata/citations.json` | `citation_checker` agent outputs | `json.dumps` (Phase 3) |

**Data source heuristic**: because of the serializer-drift rule, each source is fetched through one authoritative query path with matching Pydantic schemas. Agent documents come from LangGraph thread state directly (not registry's `/outputs` endpoint, which was the source of the `document_text` bug in commit `1ec1cb3`).

## 5. Frontend detail

### 5.1 Review panel "Download" button

Added to `review-panel.tsx` in the manuscript header (right side, next to the round indicator).

```tsx
<button
  onClick={() => downloadDocument(threadId)}
  disabled={isDownloading}
  className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
>
  <Download className="h-3.5 w-3.5" />
  {isDownloading ? "Preparing…" : "Download"}
</button>
```

Handler triggers a hidden `<a>` with `download` attribute pointing at `/api/cme/export/document/{threadId}`. Browser handles the zip. No store state, no tray row — sync path only.

### 5.2 Page header "Full project" button

Added to the standard header in `inbox-master-detail.tsx`, between the pending count and the refresh icon.

```tsx
<button
  onClick={() => enqueueProjectExport(selectedReview.threadId)}
  disabled={!selectedReview}
  className="inline-flex items-center gap-1.5 rounded-md border border-input px-2.5 py-1 text-xs hover:bg-muted"
>
  <FileArchive className="h-3.5 w-3.5" />
  Full project
</button>
```

Disabled until a review is selected. Handler POSTs to `/api/cme/export/project/{threadId}`, pushes the returned job into the downloads store, opens the tray.

### 5.3 Downloads store (`frontend/src/stores/downloads-store.ts`)

```ts
interface DownloadJob {
  jobId: string;
  threadId: string;
  scope: "document" | "project";
  status: "queued" | "running" | "done" | "failed";
  createdAt: string;
  completedAt?: string;
  artifactUrl?: string;
  error?: string;
}

interface DownloadsState {
  jobs: DownloadJob[];
  trayOpen: boolean;
  setJobs: (jobs: DownloadJob[]) => void;
  upsertJob: (job: DownloadJob) => void;
  openTray: () => void;
  closeTray: () => void;
  toggleTray: () => void;
}
```

Zustand with `persist` + `partialize` keeping only `jobs` (not `trayOpen`). On mount, hydrates from `GET /api/cme/export/jobs?limit=20` so jobs survive a page refresh.

### 5.4 Polling hook (`frontend/src/hooks/use-download-polling.ts`)

Polls only while at least one job is active (`queued` or `running`). When the last active job transitions to `done`/`failed`, the interval clears itself. No infinite polling on an idle tray. 3-second interval.

### 5.5 Downloads tray component

Slide-out panel (shadcn `Sheet`) from the right edge, triggered by an icon in the standard header with a badge showing count of active jobs. Mounted in `app-shell.tsx` so a download kicked off from `/inbox` is still watchable from `/monitoring`.

Row shape:
```
┌────────────────────────────────────────────┐
│ 📦 Grant Package              14s          │
│    Full project · c7b46e6                  │
│    ● Rendering…                            │
└────────────────────────────────────────────┘
┌────────────────────────────────────────────┐
│ 📄 Needs Assessment          ✓ 2 min ago   │
│    Document · f236196                      │
│    Download (1.2 MB) →                     │
└────────────────────────────────────────────┘
```

Failed rows get a `Retry` link that re-POSTs the same endpoint (new job, not retry in place). Rows auto-purge from the local store after 24 hours (server-side they stick around per the 30-day TTL).

### 5.6 Print routes (`frontend/src/app/print/`)

```
frontend/src/app/print/
├── layout.tsx              # minimal HTML, no sidebar, no chrome, print.css
├── document/[threadId]/page.tsx
├── intake/[threadId]/page.tsx
├── project/[threadId]/page.tsx       # aggregate — optional
├── quality/[threadId]/page.tsx       # Phase 3
└── review-history/[threadId]/page.tsx # Phase 3
```

- `layout.tsx` does NOT wrap children in `AppShell`. Imports `print.css` which sets `@page { size: Letter; margin: 0.75in; }`, hides interactive controls, forces page breaks.
- Page components reuse `DocumentViewer`, `ReflectionPanel`, brand tokens, shadcn components directly.
- Authentication via signed-token middleware bypass (§4.4).
- `timingSafeEqual` from `node:crypto` for signature comparison.

### 5.7 Chart-ready wait convention

The Tremor/Recharts wrapper components get a `data-loading="true|false"` attribute set based on their render state. Playwright waits for `!document.querySelector('[data-loading=true]')` before calling `page.pdf()`. This lands in **Phase 1** even though charts don't ship until Phase 3 — retrofitting the convention later would mean re-auditing every chart component.

## 6. Bundle assembly pipeline

### 6.1 Worker loop

```python
async def run_worker():
    while True:
        job = await claim_next_job()   # FOR UPDATE SKIP LOCKED
        if job is None:
            await asyncio.sleep(2)
            continue
        try:
            await mark_running(job.id)
            artifact_path, sha, size = await assemble_bundle(job)
            await mark_done(job.id, artifact_path, sha, size)
        except Exception as e:
            logger.exception("bundle failed", job_id=job.id)
            await mark_failed(job.id, str(e)[:2000])
```

Single worker per container replica. Horizontal scale is free — `SKIP LOCKED` means two replicas contend safely without Redis or Celery.

### 6.2 `assemble_project_bundle(job)`

- Fetches thread state + project metadata.
- Builds prefix `{project.kind}-{short_id}-{date}` (e.g. `grant-package-c7b46e6-2026-04-14`).
- Opens `AsyncZipBuilder` at `/var/exports/{job.id}.zip.tmp`.
- Adds README placeholder first (replaced at end with actual manifest + checksums).
- Renders intake MD + PDF.
- Iterates `AGENT_ORDER` constant, rendering MD + PDF per agent that actually ran.
- Writes `04-metadata/project.json`.
- (Phase 3+) writes quality, review history, citations, diffs.
- Replaces README placeholder with final manifest (now knows every file's sha256).
- Atomically renames `.tmp` → final path via `os.replace`.

**Agent order constant** lives next to the orchestrator's recipe definitions as a single source of truth:
```python
AGENT_ORDER = [
    "needs_assessment", "research", "clinical_practice", "gap_analysis",
    "learning_objectives", "curriculum_design", "research_protocol",
    "marketing_plan", "grant_writer", "prose_quality", "compliance_review",
]
```
Recipe-specific subsets (needs/curriculum/grant/full) filter this list to what actually ran.

### 6.3 Playwright render helper

```python
_browser: Browser | None = None  # module-scope, shared across renders

async def render_print_route(path: str) -> bytes:
    url = f"{FRONTEND_INTERNAL_URL}{path}"
    token, exp = signing.sign(path)
    url_with_token = f"{url}{'&' if '?' in path else '?'}token={token}&exp={exp}"

    context = await _browser.new_context(viewport={"width": 1056, "height": 1500})
    try:
        page = await context.new_page()
        await page.goto(url_with_token, wait_until="networkidle", timeout=30_000)
        await page.wait_for_function(
            "() => !document.querySelector('[data-loading=true]')",
            timeout=10_000,
        )
        return await page.pdf(
            format="Letter",
            margin={"top": "0.75in", "right": "0.75in", "bottom": "0.75in", "left": "0.75in"},
            print_background=True,
        )
    finally:
        await context.close()
```

Chromium launch flags: `--no-sandbox --disable-dev-shm-usage`. `shm_size: 2gb` set in compose.

### 6.4 Failure model

- **Partial failure ≠ success.** Any print-route failure or data-fetch error fails the whole job. A half-bundle is worse than no bundle for compliance.
- **Retries**: manual in v1. Tray's Retry button re-POSTs, creating a fresh job. Automatic retry goes on the Phase 5 list if logs show flakiness.
- **Timeouts**: 30s per print route, 90s total budget per job via `asyncio.wait_for`. Exceed → `failed` + partial tmp file deleted.
- **Atomic zip**: temp file + `os.replace`. Crash mid-write leaves only the `.tmp`, cleaned on worker startup. Registry never streams a half-written file.

### 6.5 Concurrency

- Worker queue is `FOR UPDATE SKIP LOCKED` on Postgres 15 — two renderer replicas can run side-by-side without additional coordination.
- Dedup on `POST /project` prevents duplicate jobs for the same thread being queued simultaneously.
- Per-thread rate limit (Phase 5) prevents a single user queuing more than N jobs/hour.

## 7. Phase breakdown

Five phases. Each one ships a user-visible improvement and is independently deployable.

### Phase 1 — Document download (sync path only)

**Goal:** reviewer can click "Download" on the manuscript header and get a zip with the current document as MD + PDF.

**Deliverables:**
- New service scaffold: `services/pdf-renderer/` with Dockerfile, FastAPI app, Playwright browser manager, signing helper
- Docker compose entry for `dhg-pdf-renderer` on `dhgaifactory35_dhg-network`
- Print route `/print/document/[threadId]?section={agent}` + `layout.tsx` + `print.css`
- Next.js `middleware.ts` bypass for `/print/*` with signed-token check
- Registry endpoint `GET /api/cme/export/document/{thread_id}` (sync, calls renderer, streams zip)
- `registry/export_endpoints.py` + `registry/export_schemas.py` (forbidden-extras pattern)
- "Download" button in `review-panel.tsx`
- Chart-ready wait convention: `[data-loading=true]` attribute on Tremor/Recharts wrappers

**Acceptance:**
1. `curl -o test.zip https://app.digitalharmonyai.com/api/registry/api/cme/export/document/{id}` returns a valid zip
2. `unzip -l test.zip` shows MD + PDF pair
3. PDF opens cleanly, renders brand tokens (Graphite/Purple/Inter)
4. Token tests: missing token, expired token, wrong-key token all return 401
5. Playwright e2e: click button → zip downloads → unzip → PDF present

**Deferred:** project scope, async, jobs table, tray, quality/history/citations, retries.

**Estimate:** 3–4 engineering days.

### Phase 2 — Full project async scaffolding + v1 bundle

**Goal:** reviewer clicks "Full project", gets a tray row, and eventually downloads a zip with documents + intake + project metadata.

**Deliverables:**
- Alembic migration `008_add_download_jobs.py`
- Registry endpoints: `POST /project`, `GET /job/{id}`, `GET /artifact/{id}`, `GET /jobs`
- Dedup logic on POST
- Worker loop with `FOR UPDATE SKIP LOCKED`
- `assemble_project_bundle()` — README, `00-intake/`, `01-documents/`, `04-metadata/project.json` only
- Print route `/print/intake/[threadId]`
- Atomic zip writer with tmp-file + `os.replace`
- Shared Docker volume `dhg_exports`
- Frontend: downloads store, polling hook, tray component
- Tray mounted in `app-shell.tsx`
- "Full project" button in inbox header
- `security_audit_log` write on each artifact download

**Acceptance:**
1. Two concurrent POSTs for same thread return same job_id
2. Two workers claim disjoint rows (`SKIP LOCKED` test)
3. Real-DB integration: create job → worker processes → zip at expected path → sha256 matches DB row
4. Bundle structure assertion via `zipfile.ZipFile.namelist()`
5. Crash test: kill worker mid-render → no partial zip at final path
6. Tray transitions `queued` → `running` → `done` within one poll tick
7. User A cannot fetch user B's artifact (403)

**Deferred:** quality signals, review history, citations, diffs, retries, TTL cleanup.

**Estimate:** 5–7 engineering days.

### Phase 3 — Quality, review history, citations

**Goal:** bundle becomes a real compliance archive.

**Deliverables:**
- `sources/quality.py`, `sources/review_history.py`, `sources/citations.py`
- Quality signals: prose score, banned pattern hits, ACCME flags per document
- Review history: `security_audit_log` + human review decisions in thread state
- Citations: verified + unverified lists from `citation_checker` outputs
- Print routes: `/print/quality/[threadId]`, `/print/review-history/[threadId]`
- Bundle additions: `02-quality/`, `03-review-history/review-log.{md,pdf}`, `04-metadata/citations.json`
- `render_readme()` updated to include new files in manifest
- Tremor bar chart in quality print route (relies on Phase 1 chart-ready convention)

**Acceptance:**
1. Real-DB fixture: seed quality signals → bundle contains `02-quality/quality-signals.md` with matching numbers
2. Real-DB fixture: three audit rows → review-log.md has three entries in reverse chronological order
3. Citations fixture round-trips byte-identical (serializer-drift rule)
4. Chart test: quality PDF renders Tremor bar chart, not a blank rectangle
5. README manifest includes all new files with correct sha256s

**Deferred:** diffs, retries, TTL, rate limiting.

**Estimate:** 4–5 engineering days.

### Phase 4 — Round-by-round diffs

**Goal:** reviewers see exactly what changed between revision rounds.

**Deliverables:**
- Version source: LangGraph checkpoint history for v1 (migrate to a `document_versions` table only if checkpoint query proves too slow)
- Diff renderer: paragraph-level semantic diff (not line-level, because LLM output reflows whitespace)
- Bundle additions: `03-review-history/rounds/round-{n}-diff.md`
- Integration behind feature flag `INCLUDE_ROUND_DIFFS=true`

**Acceptance:**
1. Two-round fixture: single paragraph change → diff shows that paragraph only
2. Deleted paragraph → marked as removed, not as whole-document rewrite
3. Single-round thread → `rounds/` directory omitted entirely (not an empty folder)
4. Three-round bundle → `rounds/` contains exactly 2 diff files

**Deferred:** three-way merge, in-app HTML diff view.

**Estimate:** 4–6 engineering days.

### Phase 5 — Polish, operations, hardening

**Goal:** fleet-ready.

**Deliverables:**
- **TTL cleanup**: registry-api background task deletes rows + artifact files older than 30 days
- **Rate limiting**: `POST /project` returns 429 if caller created > 5 jobs in last hour
- **Retry UX**: failed tray rows show Retry link
- **Tray improvements**: filter by thread_id, archive view
- **Compliance stamp**: README top section with exporter name, role, ISO timestamp, checksum tree
- **Chromium tuning**: memory leak watchdog (restart browser after 100 renders)
- **Signing key rotation**: `PDF_RENDER_SIGNING_KEY` accepts old + new during rotation
- **Grafana panel**: `dhg-pdf-renderer` — jobs queued, running, avg render time, failure rate
- **Alertmanager**: page on `downloads_failed_total > 5 / 15min` or `queue_depth > 20 / 5min`

**Acceptance:**
1. TTL test: 31-day-old job → cleanup → row + file gone
2. Rate-limit test: 6 POSTs in an hour → 6th returns 429
3. Grafana dashboard loads with live data
4. Alertmanager fires webhook on simulated failure burst

**Deferred:** object storage migration, auto-retry with exponential backoff, WebSocket push instead of polling.

**Estimate:** 3–4 engineering days.

### Summary

| Phase | Ships | Est (days) | Risk |
|---|---|---|---|
| 1 | Download current document as zip | 3–4 | Low |
| 2 | Full project bundle (docs + intake) | 5–7 | Med |
| 3 | Quality + history + citations | 4–5 | Med |
| 4 | Round-by-round diffs | 4–6 | Med-high |
| 5 | Ops + polish | 3–4 | Low |
| **Total** | | **19–26 days** | |

Phases 1–3 give a compliance-grade export. Phase 4 is a differentiator but not a blocker. Phase 5 is the operations tail.

## 8. Open design decisions (to resolve at implementation time)

- **Checkpoint query vs `document_versions` table** for Phase 4 — defer until we can measure checkpoint query latency on real data.
- **Token rotation cadence** for `PDF_RENDER_SIGNING_KEY` — Phase 5 concern; default quarterly.
- **Memory watchdog threshold** for Chromium — start at 100 renders, tune based on observed leak rate.

## 9. Security considerations

- **Print-route middleware bypass** is the most security-sensitive change. Phase 1 test matrix must include: missing token → 401, expired token → 401, wrong-key token → 401, valid token → 200. Unit test on the middleware logic, plus Playwright e2e.
- **Artifact auth**: `GET /artifact/{job_id}` restricted to job creator or admin. Admin exception exists so compliance reviewers can retrieve archives they didn't personally create.
- **Shared volume** is writable only by `dhg-pdf-renderer`. Registry has read-only mount.
- **No external Cloudflare Access rule** exists for `/print/*`. The routes are only reachable over the internal Docker network — a user hitting `app.digitalharmonyai.com/print/...` gets blocked at the middleware token check.
- **Signing key** lives in `.env` and is surfaced to exactly two containers. Rotation procedure ships in Phase 5.

## 10. Testing approach

- **Unit**: middleware token validation, dedup logic, `FOR UPDATE SKIP LOCKED` claim, atomic zip writer, diff renderer (Phase 4).
- **Integration (real DB)**: end-to-end job lifecycle, bundle structure assertions, serializer round-trip for each data source (serializer-drift rule — mock tests cannot catch JSONB drift).
- **Playwright e2e**: click button → zip downloads → unzip → PDF present → assert brand tokens in PDF content.
- **Chaos**: kill worker mid-render, verify partial tmp file cleanup on next startup; kill renderer container mid-job, verify row transitions to `failed` via watchdog (Phase 5).
- **Security**: token test matrix, cross-user artifact access test.

## 11. Out of scope (explicit non-goals)

- **S3 / object storage** for artifacts. Shared Docker volume is sufficient for current scale.
- **Real-time push** of job status. Polling every 3s is adequate — WebSocket migration can happen later if polling load shows up on dashboards.
- **Multi-user collaboration** on exports. One user per job, no sharing of in-progress renders.
- **PDF editing / annotations** inside the exported documents. PDFs are read-only compliance artifacts.
- **Scheduled exports** (nightly bundle snapshots). Users initiate every export explicitly.
- **Export of threads not yet in review** (running, not interrupted). Only threads visible in the inbox can be exported.
