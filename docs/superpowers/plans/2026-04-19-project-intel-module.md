# Project Intelligence Module — Plan 1 (Foundation + Burndown)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a new admin module that ingests all project documentation into the existing Registry, surveils development activity (commits, PRs, CI, LangSmith traces, registry writes), keeps item status current in near-real-time, and exposes four synchronized views (Burndown, Kanban, Table, List) plus a Reports surface at `/admin/project-intel`. Phase 1 delivers the **Burndown view** end-to-end; later phases expand views, reports, and agent sophistication.

**Initial scope (Phase 1 focus):** Burndown view + a scheduled **Burndown Agent** that runs at 03:00 daily, reconciles the install-time TODO list against current repo activity, writes daily snapshots, and flags items as `new | in-progress | stalled | blocker | done` with evidence links and confidence scores.

---

## Architecture

A new admin surface under the existing Next.js frontend at `/admin/project-intel`, backed by new endpoints under the Registry API (`registry/project_intel_endpoints.py`) and a new LangGraph agent (`langgraph_workflows/dhg-agents-cloud/src/burndown_agent.py`). **No new containers, no new databases, no new auth layer.** All state lives in the existing `dhg-registry-db` (Postgres 15 + pgvector), reusing the medkb chunk/embedding patterns for doc search and the Registry's RBAC tables for access control.

**Ingestion & surveillance surface:**
- Documentation sources: `docs/`, `CLAUDE.md`, plan files under `docs/superpowers/plans/`, PR descriptions, commit messages, LangGraph agent READMEs
- Activity sources: git log (via GitPython), GitHub webhooks (PRs, issues, releases), CI results (GitHub Actions API), LangSmith traces (existing client), registry API audit log
- Chunking + embedding: reuse medkb's `text-embedding-nomic-embed-text` via Ollama, store in a new `project_doc_chunks` table with `vector(768)` column and GIN index on `tsvector` for hybrid search
- Matching inference: LLM-assisted heuristic that correlates commits/PRs/trace IDs to item IDs, emits a confidence score

**Why no new infra:**
1. Registry DB already has pgvector and FTS — no Meilisearch needed (see design discussion 2026-04-19)
2. Registry API already has Cloudflare JWT + RBAC — reuse `security_users` / `security_project_access`
3. medkb already implements hybrid retrieval — reuse the `retriever/hybrid.py` pattern for corpus-wide search
4. dhg-pdf-renderer already handles exports — reuse for report PDFs

**Tech stack (everything already installed):**
- Backend: FastAPI 0.115, SQLAlchemy 2.0, Alembic, GitPython, PyGithub
- Agent: LangGraph 0.3, ChatAnthropic, Ollama embeddings
- Frontend: Next.js 16, shadcn/ui, Tremor, TanStack Table, TanStack Query, dnd-kit, cmdk, react-pdf
- DB: existing dhg-registry-db with pgvector + Postgres FTS
- Observability: existing OTel/Tempo + Prometheus + LangSmith

---

## Phase Map

| Phase | Scope | Est. |
|-------|-------|------|
| **0** | Schema migration, core endpoints skeleton, auth wiring, install-time TODO seed | 3-4 days |
| **1** | Burndown Agent (cron 03:00), daily snapshots, stalled/blocker detection with evidence + confidence | 1 week |
| **2** | Burndown UI (Tremor chart + KPI cards + stalled drill-down), detail drawer with evidence links | 1 week |
| **3** | Kanban + Table + List views sharing the same Zustand store; inline cell editing via TanStack Table | 1 week |
| **4** | Doc ingestion pipeline + hybrid search, ⌘K command palette, react-pdf preview pane | 1-1.5 weeks |
| **5** | Reports surface: 4 build-first reports (Burndown, Stalled, Dev Activity, Agent Cost) rendered as Tremor dashboards, xlsx export via openpyxl, scheduled email digest | 1 week |
| **6** | Real-time event stream (SSE from registry-api) for near-real-time status updates; webhook receivers for GitHub | 3-4 days |

**Phase 1 is the MVP.** Phases 2+ should only start after Phase 1 is verified working against real project activity.

---

## Open Research Questions (blocking Phase 0 start)

Before any code, complete the **OSS adoption memo** — evaluate these candidates and recommend adopt/fork/build-fresh:

| Candidate | License | Self-hostable | Agent/webhook extensibility | Embedding-friendly |
|-----------|---------|---------------|------------------------------|-------------------|
| Plane | AGPL-3.0 | Yes | Webhooks, REST API | No native |
| Focalboard | MIT (archived by Mattermost 2024) | Yes | Limited | No |
| Huly | MIT | Yes | Plugin SDK | No |
| OpenProject | GPL-3.0 | Yes | REST API, webhooks | No |
| Leantime | AGPL-3.0 | Yes | Plugins | No |
| Taiga | MPL-2.0 | Yes | Webhooks | No |
| Vikunja | AGPL-3.0 | Yes | Webhooks | No |

Memo deliverable: ranked recommendation with integration cost vs. DHG stack (Registry API, LangGraph, pgvector, shadcn/Tremor, Cloudflare Access). If any candidate scores well, this plan pivots to "fork + integrate" rather than "build fresh."

**Current recommendation (pre-research):** build-fresh on existing DHG stack. The candidates above are monolithic apps with their own DBs and auth; integrating any of them means either running a parallel stack or doing deep surgery. Our requirements (agent-driven status updates, evidence linking, embedded doc search, DHG brand, Cloudflare Access + RBAC integration) are already 70% infrastructure we own. Net: forking is likely more expensive than the 4-6 week build.

---

## File Structure (new files only)

```
registry/
├── project_intel_endpoints.py           # FastAPI router: CRUD + query endpoints
├── project_intel_service.py             # Business logic (item matching, burndown calc)
├── project_intel_schemas.py             # Pydantic request/response models
├── project_intel_ingest.py              # Doc ingestion pipeline (git scan, chunk, embed)
├── project_intel_surveillance.py        # Git/GitHub/LangSmith/audit log correlators
└── alembic/versions/
    └── 012_add_project_intel.py         # Schema migration

langgraph_workflows/dhg-agents-cloud/src/
├── burndown_agent.py                    # StateGraph: scan → match → flag → snapshot
└── burndown_agent_tests.py              # pytest against fixture repo

frontend/src/
├── app/admin/project-intel/
│   ├── layout.tsx                       # Sidebar + top bar + tab nav
│   ├── page.tsx                         # Default = Burndown view
│   ├── burndown/page.tsx
│   ├── kanban/page.tsx
│   ├── table/page.tsx
│   ├── list/page.tsx
│   ├── docs/page.tsx                    # Doc search + PDF preview
│   └── reports/[slug]/page.tsx          # Report runner
├── components/project-intel/
│   ├── burndown-chart.tsx               # Tremor AreaChart
│   ├── kpi-cards.tsx                    # Tremor Card grid
│   ├── stalled-list.tsx
│   ├── item-detail-drawer.tsx           # shadcn Sheet
│   ├── evidence-links.tsx
│   ├── kanban-board.tsx                 # dnd-kit
│   ├── items-table.tsx                  # TanStack DataTable + inline edit
│   ├── items-list.tsx                   # shadcn Command list
│   ├── doc-preview.tsx                  # react-pdf lazy-loaded
│   └── command-palette.tsx              # cmdk global ⌘K
├── stores/project-intel-store.ts        # Zustand shared across views
├── lib/projectIntelApi.ts               # Typed fetcher
└── hooks/use-project-intel-stream.ts    # SSE subscription (Phase 6)

docs/
├── superpowers/plans/
│   └── 2026-04-19-project-intel-module.md          # this file
└── superpowers/specs/
    └── 2026-04-19-project-intel-design.md          # detailed design doc (write in Phase 0)
```

---

## Database Schema (migration 012)

```sql
-- Projects the module tracks (seeded from docs/TODO.md initiatives)
CREATE TABLE project_intel_projects (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug          TEXT NOT NULL UNIQUE,        -- 'medkb', 'inbox-download', 'auth-rbac'
  name          TEXT NOT NULL,
  description   TEXT,
  status        TEXT NOT NULL DEFAULT 'active',   -- active | archived | paused
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Individual trackable items (tasks, features, fixes)
CREATE TABLE project_items (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id        UUID NOT NULL REFERENCES project_intel_projects(id) ON DELETE CASCADE,
  title             TEXT NOT NULL,
  description       TEXT,
  status            TEXT NOT NULL DEFAULT 'new',   -- new | in-progress | stalled | blocker | done
  priority          INT DEFAULT 3,                  -- 1 (highest) to 5
  owner             TEXT,                           -- user email or 'unassigned'
  source            TEXT NOT NULL,                  -- 'todo_seed' | 'manual' | 'agent_inferred'
  source_ref        TEXT,                           -- line ref into docs/TODO.md, PR #, etc.
  confidence        REAL DEFAULT 1.0,               -- 0.0-1.0 for agent-inferred items
  stalled_since     TIMESTAMPTZ,                    -- NULL unless status='stalled'
  stalled_reason    TEXT,                           -- agent narrative
  blocker_reason    TEXT,
  opened_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  closed_at         TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('new','in-progress','stalled','blocker','done'))
);
CREATE INDEX idx_project_items_project_status ON project_items(project_id, status);
CREATE INDEX idx_project_items_stalled_since ON project_items(stalled_since) WHERE stalled_since IS NOT NULL;

-- Evidence trail — every status change points back to a commit/PR/trace
CREATE TABLE project_item_evidence (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id       UUID NOT NULL REFERENCES project_items(id) ON DELETE CASCADE,
  kind          TEXT NOT NULL,                    -- 'commit' | 'pr' | 'trace' | 'ci' | 'manual'
  ref           TEXT NOT NULL,                    -- SHA / PR# / trace_id / run_id
  url           TEXT,                             -- direct link if available
  summary       TEXT,
  observed_at   TIMESTAMPTZ NOT NULL,
  confidence    REAL DEFAULT 1.0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_evidence_item ON project_item_evidence(item_id);
CREATE INDEX idx_evidence_ref ON project_item_evidence(kind, ref);

-- Daily burndown snapshots — the 3am agent writes one row per project per day
CREATE TABLE burndown_snapshots (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      UUID NOT NULL REFERENCES project_intel_projects(id) ON DELETE CASCADE,
  snapshot_date   DATE NOT NULL,
  open_count      INT NOT NULL,
  in_progress_count INT NOT NULL,
  stalled_count   INT NOT NULL,
  blocker_count   INT NOT NULL,
  done_count      INT NOT NULL,
  velocity_7d     REAL,                           -- items closed per day (7-day avg)
  projected_done  DATE,                           -- projected completion date
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (project_id, snapshot_date)
);

-- Ingested project documentation
CREATE TABLE project_docs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id    UUID REFERENCES project_intel_projects(id) ON DELETE SET NULL,
  path          TEXT NOT NULL,                    -- relative repo path
  commit_sha    TEXT NOT NULL,                    -- sha at ingestion time
  content_hash  TEXT NOT NULL,                    -- sha256 of body, for dedup
  title         TEXT,
  chunk_count   INT NOT NULL DEFAULT 0,
  ingested_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (path, content_hash)
);

CREATE TABLE project_doc_chunks (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doc_id        UUID NOT NULL REFERENCES project_docs(id) ON DELETE CASCADE,
  chunk_index   INT NOT NULL,
  text          TEXT NOT NULL,
  tsv           TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
  embedding     VECTOR(768),                      -- nomic-embed-text via Ollama
  span_start    INT,
  span_end      INT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_doc_chunks_tsv ON project_doc_chunks USING GIN(tsv);
CREATE INDEX idx_doc_chunks_embedding ON project_doc_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Decisions log — separate from items, captures why choices were made
CREATE TABLE project_decisions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id    UUID REFERENCES project_intel_projects(id) ON DELETE SET NULL,
  title         TEXT NOT NULL,
  rationale     TEXT NOT NULL,
  captured_from TEXT,                             -- 'plan_file' | 'pr' | 'claude_md' | 'manual'
  source_ref    TEXT,
  decided_at    TIMESTAMPTZ NOT NULL,
  linked_item_ids UUID[] DEFAULT '{}',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tags for both items and docs
CREATE TABLE project_tags (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL UNIQUE,
  color       TEXT
);
CREATE TABLE project_item_tags (
  item_id UUID REFERENCES project_items(id) ON DELETE CASCADE,
  tag_id  UUID REFERENCES project_tags(id) ON DELETE CASCADE,
  PRIMARY KEY (item_id, tag_id)
);
```

**Stalled detection rule (agent logic, not DB):**
- Item has `status IN ('new','in-progress')` AND no evidence row in last N days (N=7 for in-progress, N=14 for new). N is configurable per project.
- Agent writes `stalled_since` and an LLM-generated `stalled_reason` based on last evidence + surrounding context.

---

## API Endpoints (registry/project_intel_endpoints.py)

All under `/api/v1/project-intel/`, all behind existing `get_current_user` dependency (Cloudflare JWT or API key).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/projects` | List tracked projects |
| POST | `/projects` | Create project (admin only) |
| GET | `/projects/{id}` | Project detail |
| PATCH | `/projects/{id}` | Update project |
| GET | `/projects/{id}/items` | List items with filters (status, owner, tag, since) |
| POST | `/projects/{id}/items` | Manual item create |
| PATCH | `/items/{id}` | Update item (status, owner, tags, notes) |
| GET | `/items/{id}` | Item detail + evidence + linked docs |
| GET | `/items/{id}/evidence` | Evidence trail |
| POST | `/items/{id}/evidence` | Manual evidence add |
| GET | `/projects/{id}/burndown` | Burndown snapshots + KPIs (query: `from`, `to`) |
| POST | `/projects/{id}/burndown/recompute` | Trigger Burndown Agent on-demand (admin only) |
| GET | `/search` | Hybrid search across chunks (query: `q`, `project_id?`, `k=20`) |
| GET | `/decisions` | List decisions with filters |
| POST | `/decisions` | Create decision |
| GET | `/reports/{slug}` | Render report dataset (Burndown, Stalled, DevActivity, AgentCost) |
| GET | `/reports/{slug}/export.xlsx` | xlsx export via openpyxl |
| GET | `/stream` | SSE event stream (Phase 6) |

RBAC: write endpoints require `role IN ('admin','operations','editor')`; read endpoints require any authenticated user. Per-project visibility enforced via `security_project_access`.

---

## Burndown Agent Design (Phase 1 core)

**LangGraph StateGraph** at `langgraph_workflows/dhg-agents-cloud/src/burndown_agent.py`. Runs as a scheduled cron trigger at 03:00 local server time.

**State (TypedDict):**
```python
class BurndownState(TypedDict):
    project_ids: list[UUID]                 # projects to process this run
    current_project_id: UUID | None
    items: list[ProjectItem]                # loaded items for current project
    recent_commits: list[CommitMeta]        # last 30 days
    recent_prs: list[PRMeta]
    recent_traces: list[TraceMeta]
    matched_evidence: list[EvidenceCandidate]
    flagged_stalled: list[UUID]
    flagged_blocker: list[UUID]
    snapshot: BurndownSnapshot | None
    errors: list[ErrorRecord]
```

**Graph nodes (all @traceable + @traced_node):**
1. `load_projects` — fetch projects with `status='active'`
2. `scan_activity` — pull git log, GitHub PRs, LangSmith traces for last 30 days (parallel via asyncio.gather)
3. `match_evidence` — for each commit/PR, LLM-classify which item(s) it relates to, emit (item_id, evidence, confidence) tuples; confidence threshold 0.7 for auto-attach, 0.4-0.7 for suggest-only
4. `detect_stalled` — flag items with status in (new, in-progress) and no evidence within threshold
5. `generate_stalled_narrative` — LLM generates "why stalled" for each flagged item
6. `detect_blockers` — scan for phrases like "blocked on", "waiting for", "needs" in item descriptions and recent comments
7. `compute_snapshot` — aggregate counts + 7-day velocity + projected completion date
8. `persist` — write evidence rows, update items, insert burndown_snapshot (one transaction per project)
9. `emit_digest` — produce daily digest payload (newly stalled, newly closed, new blockers) for email/Slack

**Error handling:** per-project try/except; failure on one project must not block others. All errors captured in `errors[]` and logged to `dev_changelog` table.

**Idempotency:** `burndown_snapshots` has `UNIQUE (project_id, snapshot_date)` — re-running same day UPSERTs.

**Cron wiring:** use existing LangGraph Cloud cron trigger (same mechanism as planned for medkb ingestor). Local dev: manual POST to `/projects/{id}/burndown/recompute`.

---

## Frontend Architecture

**Single page route, four tabbed views sharing one Zustand store** to avoid re-fetching when switching views. Tab state persisted in URL query param (`?view=burndown`) for deep-linking.

**Reused primitives from existing codebase:**
- Inbox master-detail layout (`frontend/src/components/review/inbox-master-detail.tsx`) — copy pattern for project list + item detail
- Downloads tray pattern (`frontend/src/components/downloads/downloads-tray.tsx`) — reuse for report PDF generation
- Role-aware sidebar — add "Project Intel" section under Manage

**Performance pattern (the device.report "fast" feel):**
- Burndown page rendered via React Server Components on initial request
- TanStack Query with `staleTime: 30s` + SWR revalidation for client updates
- Skeleton loaders (shadcn) not spinners
- TanStack Virtual for item lists >200 rows
- Tremor charts lazy-loaded below the fold

---

## Reports (Phase 5)

Four build-first reports, all reusing the same query service:

1. **Burndown Report** — `reports/burndown` — velocity, projected completion, items added vs. closed this week
2. **Stalled & Blocker Report** — `reports/stalled` — flagged items with narratives and suggested unblock actions
3. **Dev Activity Digest** — `reports/dev-activity` — commits / PRs / CI / traces / registry writes in last 24h grouped by project
4. **Agent Cost Report** — `reports/agent-cost` — Claude token spend per agent per day, cost per grant package, forecast vs. budget (pulls from LangSmith)

Each renders as a Tremor dashboard, exports to xlsx via openpyxl, and is schedulable for email digest (Phase 5 optional: Slack webhook).

---

## Phase 0 Tasks — Schema + skeleton

- [ ] 0.1 Write detailed design spec at `docs/superpowers/specs/2026-04-19-project-intel-design.md` (tables, endpoints, agent nodes, stalled rules, matching heuristic)
- [ ] 0.2 Complete OSS adoption memo (evaluate Plane, Huly, OpenProject, Leantime) — deliverable: `docs/research/2026-04-19-project-tracker-oss-eval.md`
- [ ] 0.3 Stephen reviews memo + approves build-fresh vs. fork decision
- [ ] 0.4 Create worktree branch `feature/project-intel-phase0`
- [ ] 0.5 Write migration `registry/alembic/versions/012_add_project_intel.py` — all tables + indexes above
- [ ] 0.6 Add SQLAlchemy models to `registry/models.py` (8 new classes)
- [ ] 0.7 Write Pydantic schemas in `registry/project_intel_schemas.py`
- [ ] 0.8 Scaffold `registry/project_intel_endpoints.py` with all routes returning 501 Not Implemented
- [ ] 0.9 Wire router into `registry/api.py` under `/api/v1/project-intel`
- [ ] 0.10 Add RBAC checks to every write endpoint (reuse existing dependencies)
- [ ] 0.11 Write installer script `scripts/seed_project_intel.py` that parses `docs/TODO.md`, creates a project row per top-level initiative, and creates `project_items` with `source='todo_seed'`
- [ ] 0.12 Implement GET /projects, GET /projects/{id}/items, POST /projects/{id}/items, PATCH /items/{id} (read + manual CRUD only in Phase 0)
- [ ] 0.13 Unit tests in `registry/test_project_intel_endpoints.py` — 15+ tests covering CRUD, RBAC, filters
- [ ] 0.14 Run migration against dev DB, verify tables exist and seeds load cleanly
- [ ] 0.15 Run `npx pyright` and `pytest registry/test_project_intel_endpoints.py` — both must pass
- [ ] 0.16 Commit, open PR, Stephen review, merge to master with `--no-ff`

---

## Phase 1 Tasks — Burndown Agent

- [ ] 1.1 Create `langgraph_workflows/dhg-agents-cloud/src/burndown_agent.py` with state + graph skeleton
- [ ] 1.2 Implement `scan_activity` node — GitPython for commits, PyGithub for PRs, LangSmith client for traces (parallel asyncio.gather)
- [ ] 1.3 Implement `match_evidence` node — prompt template + structured output via Claude; unit test with fixture commits
- [ ] 1.4 Implement `detect_stalled` node — pure function, configurable thresholds per project
- [ ] 1.5 Implement `generate_stalled_narrative` node — Claude call per flagged item
- [ ] 1.6 Implement `detect_blockers` node — regex + LLM confirmation
- [ ] 1.7 Implement `compute_snapshot` node — SQL aggregation via SQLAlchemy
- [ ] 1.8 Implement `persist` node — one transaction per project, idempotent
- [ ] 1.9 Implement `emit_digest` node — returns JSON payload; actual email/Slack send deferred to Phase 5
- [ ] 1.10 Error handling: per-project try/except, errors written to `dev_changelog`
- [ ] 1.11 Register `burndown_graph` in `langgraph.json`
- [ ] 1.12 Wire POST `/projects/{id}/burndown/recompute` to invoke agent for a single project
- [ ] 1.13 Integration test: seed fixture project + items + commits, run agent, assert snapshot row + evidence rows written
- [ ] 1.14 Schedule cron trigger at 03:00 in LangGraph Cloud (manual setup, document steps)
- [ ] 1.15 Run agent against real DHG data (medkb, inbox-download, auth-rbac projects), review output with Stephen, tune thresholds
- [ ] 1.16 Implement GET `/projects/{id}/burndown` endpoint — returns snapshots + computed KPIs
- [ ] 1.17 Commit, PR, review, merge with `--no-ff`

---

## Acceptance Criteria — Phase 1 (MVP)

1. Migration 012 applied cleanly against dev and prod registry DB; all tables + indexes present
2. `scripts/seed_project_intel.py` produces a sensible set of starter projects and items from `docs/TODO.md`
3. Burndown Agent runs end-to-end against real repo data without errors and produces:
   - One `burndown_snapshots` row per active project per run
   - Evidence rows linking commits/PRs to items with confidence scores
   - `stalled_since` + `stalled_reason` populated for items matching stalled rules
4. GET `/projects/{id}/burndown` returns structured snapshots + 7-day velocity + projected completion
5. Agent run time < 3 minutes for the full DHG project set
6. All tests pass (pyright + pytest); no TODOs/placeholders in shipped code
7. Stephen reviews a full agent output for at least one project and confirms the matched evidence + stalled narratives are accurate enough to act on

---

## Open Questions for Stephen (answer before Phase 0.4)

1. **OSS evaluation gate:** Should Phase 0.2 (memo) be done as a separate Explore-subagent research task first, or in parallel with Phase 0.1 (design spec)?
2. **Install-time TODO source:** Confirm `docs/TODO.md` is the authoritative seed. Any other files to ingest at install?
3. **Project granularity:** One project per initiative (medkb, inbox-download, auth-rbac) or finer (e.g., per-phase)? Recommendation: initiative-level, with tags for phases.
4. **Stalled thresholds:** Default 7 days for in-progress, 14 days for new — adjust?
5. **Evidence confidence thresholds:** Auto-attach at 0.7, suggest-only at 0.4-0.7 — adjust?
6. **Cloud cron wiring:** LangGraph Cloud scheduled trigger vs. a systemd timer on g700data1 posting to the recompute endpoint? Recommendation: Cloud trigger (reuses existing infra, survives server reboots).
7. **Reports scope for Phase 5:** Is the four-report set sufficient, or add CME-specific (grant status, prose QA trend, citation verification) immediately?
8. **Decision log capture:** Manual only (Phase 1) or agent-extracted from plan files at ingestion (Phase 4)? Recommendation: manual in Phase 1, agent extraction in Phase 4.

---

## Non-Goals (explicit, to prevent scope creep)

- **Not a replacement for GitHub Issues or Linear.** This is an *internal surveillance + burndown* tool, not a ticketing system with full issue workflow, assignments, SLAs, etc.
- **Not a time-tracking tool.** No hours logged against items.
- **Not a public-facing product.** Admin tool only, behind Cloudflare Access.
- **Not a CI/CD dashboard.** Pulls CI signals for evidence but is not a replacement for GitHub Actions UI.
- **No formula-spreadsheet UX in Phase 1-5.** Univer only if a specific Phase 6+ use case requires it.
- **No Meilisearch, no new search service.** Postgres FTS + pgvector covers the corpus size.

---

## Version History

- v1 (2026-04-19) — Initial plan draft. Pending Stephen review + OSS evaluation memo (Phase 0.2) before Phase 0.4 branch cut.
