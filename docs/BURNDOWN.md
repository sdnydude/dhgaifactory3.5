# DHG AI Factory — Master Burndown

**Last Updated:** Apr 19, 2026
**Coverage:** Feb 1 – Apr 19, 2026 (78 days, 395 commits on master)

---

## Summary

| Metric | Value |
|--------|-------|
| Total commits | 395 |
| Phases completed | 11 of 11 numbered phases (Phases 1-7, 9-11); Phase 8 is ongoing streams |
| Open items (planned/in-progress) | 27 |
| Completed items | 63+ |
| Containers | 22 running (21 healthy) |
| Tests | 273 (registry 227 + medkb 46) |

---

## Phase 1: Immediate Fix / Unblock (Feb–Apr 2026)

- [x] Fix gh auth and push commits (7 commits pushed)
- [x] Fix 16 DB-dependent test failures (61/61 passing, conftest.py rewritten)
- [x] Investigate Dify worker instability → decommissioned Dify + RAGFlow (zero usage)

**Status: COMPLETE**

---

## Phase 2: VS Engine Wave 1 (Mar 13–15, 2026)

- [x] Design spec + implementation plan (`docs/superpowers/specs/2026-03-14-verbalized-sampling-engine-design.md`)
- [x] Build VS Engine service (`services/vs-engine/`)
- [x] `/vs/evaluate` endpoint with DiversityEvaluator + TTCTEvaluator
- [x] Prometheus metrics (spread, selection_delta)
- [x] Grafana VS dashboard deployed
- [x] Integrate VS into all 8 content agents (36 generation nodes)
- [x] Orchestrator collects VS distributions from all 9 agents
- [x] Frontend VS alternatives panel in inbox
- [x] Migrate gap_analysis_agent from vs_distribution to vs_distributions dict
- [x] End-to-end VS pipeline test (generate + select + metrics verified)
- [x] Confirm VS metrics visible in Grafana

**Status: COMPLETE**

---

## Phase 3: Frontend Features (Mar–Apr 2026)

### Foundation (Mar 3–9)
- [x] Next.js + shadcn/ui + assistant-ui + CopilotKit frontend rebuild
- [x] Cloud-rewire: server-side proxy, polling sync, full frontend rebuild
- [x] Search page + search API client + registry search/RAG endpoints
- [x] Studio route, real alerts, webhook endpoint
- [x] Review UI components wired into Agent Inbox
- [x] interrupt()-based human review in all 4 orchestrator recipes

### Agents & Content Pipeline (Mar 10–15)
- [x] Session Capture Pipeline v2 (session-logger, Ollama embeddings 768d, PDF export, knowledge graph)
- [x] Switched all embeddings from OpenAI to Ollama (nomic-embed-text)
- [x] Monitoring dashboard frontend (stats cards, API proxies, Zustand store)
- [x] Topic extraction, PubMed citations, references in all 9 content agents
- [x] Graceful OTel degradation, importlib Cloud runtime fix

### Agents Page Enhancements (Mar 15)
- [x] Design spec + implementation plan
- [x] Tabbed container with auto-selection
- [x] Stream events, token tracking, retry to Zustand store
- [x] Streaming API with SDK joinStream and event batching
- [x] VS distribution tab, outputs tab, timeline tab, detail tab
- [x] Docker networking fixes (eliminate localhost refs, registry proxy, LangGraph SDK URL)

### Feature Buildout (Apr 6–13)
- [x] Auth & RBAC foundation (Cloudflare JWT, 5-role RBAC, audit logging, 44 tests)
- [x] LLManager inbox — master-detail layout with review list and detail panel
- [x] AI reflection panel with quality signals and recommendations
- [x] Grouped sidebar sections with role-based filtering
- [x] Inbox editorial redesign (Apr 8)
- [x] Agents Library — grid/list/table views, filtering, search, detail slide-over for 17 graphs (Apr 9)
- [x] Inbox Demo Mode — sample review data for empty-state visibility (Apr 9)
- [x] Intake Prefill Agent — PubMed-backed Section B–H draft generation (Apr 10)
- [x] CME Project edit + archive workflow (PUT/POST endpoints, edit route, archive dialog, +7 tests) (Apr 13)
- [x] Mission Control dashboards redesign + readability pass (Apr 12-13)
- [~] LLManager — deeper CME-specific review logic (PARTIAL — core inbox done, feedback loop pending)
- [ ] React Flow — visual LangGraph workflow editor
- [ ] Tremor — token usage and agent performance dashboards
- [ ] Refine — admin console with FastAPI data providers

### Dev Changelog (Apr 13-14)
- [x] Build 1: backend API + migration 007 + 16-row seed + 6 tests
- [x] Build 2: detail slide-over with agent-detected metadata + commit links
- [x] Build 3: inline edit with editorial form + server-side ownership enforcement
- [~] Build 4: filter rail DONE; timeline/kanban view modes + saved views NOT DONE
- [ ] Build 5: nightly 3am agent (blocked on #21 Phase 1 Gate B)
- [ ] Editorial masthead (hybridize with inbox editorial aesthetic)
- [ ] Real-DB tests replacing mocks
- [ ] Playwright E2E spec
- [ ] Endpoint prefix normalization (`/api/dev-changelog` vs `/api/v1/...`)

**Status: MOSTLY COMPLETE — 3 major features open (React Flow, Tremor, Refine), Dev Changelog Build 4/5 partial**

---

## Phase 4: CME Pipeline End-to-End (Apr 11–16, 2026)

- [x] Orchestrator intake data passthrough fix (`flatten_intake` aliases + 5 wrapper expansions)
- [x] End-to-end CME pipeline test — NSCLC project verified topic-correct (research 26K chars, clinical 13K chars, zero contamination)
- [x] Playwright E2E intake journey (project 66c96439 created via real form, prefill returned 20 publications)
- [x] Auto-sync observability fix (guard + silent logger root-caused, module logger → `uvicorn.error`)
- [x] `/outputs` endpoint document_text passthrough + frontend wiring (3 real-DB tests)
- [x] Intake-edit-after-submit feature (version-bump rerun, stale-intake amber banner)
- [x] Cardiology contamination scrub from prompts and dev test states
- [x] Pipeline rerun, cancel, and run history (Phase 1)
- [x] Guided character mode + CharacterConfig intake schema
- [x] Learning objectives agent crash fix (int moore_level_target + key mismatch)
- [x] Multi-review routing + resume bug + UI cleanup
- [x] 5 agent wrapper input mapping corrections + live status sync
- [x] Default recipe switch from needs_package to grant_package
- [ ] Human review implementation wired to frontend inbox with full feedback loop

**Status: NEARLY COMPLETE — 1 item open (#20, human review feedback loop)**

---

## Phase 5: Hardening (Apr 6–ongoing)

### LangGraph Telemetry Pipeline Repair
- [x] Tasks 1–5: Cloudflare tunnel route, tracing.py OTLP/HTTP swap, CF Access headers, deps, LangSmith TracerProvider fix
- [x] Task 6 / Phase 1 Gate A: CF_ACCESS secrets + Prometheus remote-write-receiver root-caused and fixed; dashboards panel D1 live
- [ ] Tasks 7–13 (Phase 2): `dhg-langgraph-exporter` service (TDD scaffold, impl, Dockerfile), compose wiring, Prometheus scrape job, 6 alert rules, Phase 1 Gate B

### Other Hardening
- [ ] Agent-level integration tests (beyond registry API tests)
- [ ] Performance benchmarks for full pipeline
- [x] Verify Tempo trace ingestion end-to-end (via Phase 1 Gate A)
- [ ] CD — automated deploy on merge to master

**Status: PARTIAL — telemetry Phase 1 done, Phase 2 + CD open**

---

## Phase 6: Security & Infrastructure (Feb–Apr 2026)

- [x] RBAC system: Cloudflare JWT auth, 5-role RBAC, audit logging, admin endpoints, 44 tests
- [x] Decommission legacy Docker agents (ports 8002-8008, restart: "no")
- [x] Decommission LibreChat stack (5 containers, 1 volume, 2.4 GB removed)
- [x] Decommission Dify + RAGFlow (18 containers, zero usage)
- [x] Docker disk cleanup (34.6 GB reclaimed)
- [x] Local LLM Inference Platform API (DB tables, models, schemas, endpoints, LLMRouter integration)
- [x] Remove dead asr/ directory
- [x] Remove decommissioned web-ui and dhg-ai-factory-ui
- [x] Security bumps: next 16.1.6→16.2.3, cryptography 41.0.7→46.0.6→46.0.7, PyJWT 2.8.0→2.12.0, python-multipart 0.0.22→0.0.26

**Status: COMPLETE**

---

## Phase 7: Inbox Document & Project Download (Apr 14–16, 2026)

### Phase 1 — Single Document Download (sync path)
- [x] Scaffold `services/pdf-renderer/` (Dockerfile, main.py, /health)
- [x] HMAC signing module with TDD (`export_signing.py` + Edge-Runtime TS verifier)
- [x] Playwright render helper with `[data-chart-ready]` wait
- [x] `/render-sync` endpoint with URL validation
- [x] Dockerfile + compose wiring (`shm_size: 2gb`, `dhg_exports` volume)
- [x] Next.js print layout + print route (`/print/cme/document`)
- [x] Middleware bypass for `/print/*` with HMAC verify
- [x] `/api/cme/export/document` sync endpoint + export_service.py
- [x] `exportApi.ts` frontend client + download button
- [x] Playwright E2E test
- [x] Registry proxy binary body fix (arrayBuffer() for PDF/zip)

### Phase 2 v2 — Project Bundles + Google Drive Sync (md-only)
- [x] Migrations 009 + 010 (download_jobs v2 schema)
- [x] SQLAlchemy model extensions (DownloadJob, CMEProject Drive fields)
- [x] Pydantic v2 schemas (BundleJobCreate/Response, ProjectList/Documents)
- [x] Project list + project documents endpoints
- [x] Bundle enqueue + job/artifact/jobs endpoints
- [x] md-only project bundler with atomic zip writer
- [x] Google Drive service-account client + Drive sync with manifest.json reconciliation
- [x] Worker loop (FOR UPDATE SKIP LOCKED, 3-scope dispatch)
- [x] Orchestrator `enqueue_drive_sync` hook + recipe milestone call sites
- [x] `filesApi.ts` frontend client
- [x] Files-tab Zustand store + Downloads store + polling hook
- [x] Files tab + Downloads tray wired into inbox tab switcher
- [x] 5-test E2E bundle round-trip (enqueue → poll → download → verify zip manifest)
- [x] Tagged `phase2v2` at `bf711ca`

### Phases 3-5 — Remaining
- [ ] Phase 3: Quality/Review History/Citations + chart-ready wait (10 tasks)
- [ ] Phase 4: Revision history with paragraph-level semantic diff (8 tasks)
- [ ] Phase 5: Hardening — TTL, rate limiting, retry, observability (10 tasks)

**Status: Phases 1-2 COMPLETE (31/31 tasks), Phases 3-5 NOT STARTED (28 tasks)**

---

## Phase 8: Active Worktree Streams (Apr 17–ongoing)

### In Progress
- [~] **Agent Observatory Phase 1** (`claude/agent-observatory-phase1`, 19 commits) — React Flow graph canvas, custom node components, 4 scenarios × 5 architectures, timeline playback engine, metrics bar, compare view, detail panel, Playwright E2E. NOT MERGED.

### Planned (backlog, not started)
- [ ] **Legacy port cleanup** — Remove orphan orchestrator on port 2024, retire `agents/` code
- [ ] **Agent SLO alerts** — Alertmanager rules (p95 latency, error rate, timeout) for 13 agents + Grafana panel
- [ ] **Audit log viewer** — Read-only `/manage/audit-log` route, paginated + filtered, admin-gated

### Reference
- [x] **Master code review** (`claude/master-review`) — P0:11, P1:58, P2:45 issues catalogued
- [x] **Docs-check routine** (`priceless-hoover-c8e359`) — doc-update check at `/ship` close (3 commits, not merged)

**Status: 1 in-progress, 3 planned, 2 reference artifacts**

---

## Phase 9: medkb RAG-as-a-Service (Apr 17–19, 2026)

### Phase 0 — Skeleton
- [x] Service directory scaffold + requirements
- [x] Config module with env-driven Pydantic Settings
- [x] Async database engine + session factory
- [x] SQLAlchemy ORM models (Corpus, Document, Chunk, IngestionJob, EmbeddingCache, QueryAudit)
- [x] Initial SQL schema with pgvector + tsvector
- [x] OTel tracing module with `@traced_node` decorator
- [x] Prometheus metrics registry
- [x] Pydantic request/response schemas
- [x] Token budget tracking with BudgetExceeded
- [x] FastAPI scaffold with `/v1/healthz`, `/v1/readyz`, `/metrics`
- [x] Dockerfile with healthcheck
- [x] 4 containers in docker-compose (db :5435, cache :6381, api :8015, ingestor stub)
- [x] Prometheus scrape target added (7/7 UP)

### Phase 1 — Dense Retrieval
- [x] Retriever Protocol + RetrievedChunk dataclass
- [x] PgVectorRetriever with dual-embedding support (Ollama nomic-embed-text)
- [x] LLM factory via `init_chat_model`
- [x] RAGState + RAGConfig TypedDicts
- [x] Graph nodes: redact, analyze_query, retrieve_fan, rerank, format_cite, emit_feedback
- [x] Conditional edge functions for graph routing
- [x] Graph builder with `strategy=regular` flow
- [x] Seed corpus with 3 CME sample documents
- [x] Corpora CRUD endpoints (`/v1/corpora`)
- [x] `/v1/query` endpoint with graph invocation
- [x] PgVectorRetriever wired into query flow

### Phase 2 — Generation + Citations
- [x] `generate` node with LLM answer generation (Claude/Ollama)
- [x] `format_cite` node with citation assembly
- [x] Ollama base_url fix for Docker networking

### Phase 3 — Hybrid + CRAG
- [x] BM25Retriever (tsvector + ts_rank_cd)
- [x] HybridRetriever (RRF fusion)
- [x] Retriever registry (corpus → retriever mapping)
- [x] `grade_docs` node (LLM relevance grading)
- [x] `rewrite_query` node (LLM query rewriting)
- [x] CRAG conditional edges in graph builder
- [x] `/v1/retrieve` endpoint
- [x] Cloudflare JWT auth module
- [x] `readyz` dependency checks (DB + Redis + Ollama)
- [x] Shared test conftest + CLAUDE.md architecture updates

### Phases 4-5 — Remaining
- [ ] Phase 4: Ingestor Pipeline — `SourceIngestor` base, MeSH/RxNorm/PubMed/PMC OA ingestors, concept reconciliation, golden test set, Recall@5 quality gate
- [ ] Phase 5: Production Hardening — Activate ingestor worker, `medkb_client.py` LangGraph integration, exit-gate verification

**Status: Phases 0-3 COMPLETE (51 commits, 46 tests, 4 containers), Phases 4-5 NOT STARTED**

---

## Phase 10: Incident Record Library (Apr 16, 2026)

- [x] Migration 011 (5 tables: incidents, events, actions, runbooks, postmortems)
- [x] `incident_service.py` (529 lines) + `incident_endpoints.py` + `incident_schemas.py`
- [x] 10 seeded runbooks (`seed_runbooks.py`)
- [x] 58 tests across 2 files (35 endpoint + 23 service)
- [x] Frontend: `/monitoring/incidents` route with list + filters + stats + detail panel
- [x] `incidentsApi.ts` client + Zustand store
- [x] Prometheus alert rule expansion (+97 lines)
- [x] Remediation sidecar (`services/remediator/`) — auto/approval/none modes, safety controls
- [x] Postmortem creation form + snapshot dashboard (264 lines)

**Status: COMPLETE**

---

## Phase 11: Pipeline Improvements (Apr 16, 2026)

- [x] Guided character mode — `CharacterConfig` intake schema, persona-driven content
- [x] Learning objectives agent crash fix — int cast + orchestrator key mismatch

**Status: COMPLETE**

---

## Infrastructure & Observability (Feb–Apr 2026)

- [x] Observability exporters deployed (node-exporter, cAdvisor v0.51.0, postgres-exporter)
- [x] Promtail → Loki log pipeline fixed (Docker Root Dir volume mount)
- [x] OTel → Tempo tracing added to all 11 LangGraph agents (85 @traced_node decorators)
- [x] Prometheus 7/7 targets UP, Alertmanager webhook to registry-api
- [x] Grafana dashboards: core golden signals, Docker overview, VS engine, LangGraph telemetry
- [x] Healthchecks added to 6 containers (bash /dev/tcp pattern)
- [x] Cloudflare tunnel configured (app.digitalharmonyai.com, vs.digitalharmonyai.com)
- [x] Cloudflare tunnel cleanup (removed unused c2l + secrets routes)
- [x] LangGraph Cloud production deployment (17 graphs)
- [x] GitHub Actions CI pipeline (lint, test, compose validation, doc drift checker)
- [x] Documentation consolidated (42 docs archived, CLAUDE.md canonical)
- [x] LSP setup (pyright + typescript-language-server) with pyrightconfig.json
- [x] CodeGraph semantic index initialized

**Status: COMPLETE**

---

## Design Specs Written (Not Yet Implemented)

- [ ] Ansible fleet bootstrap (`docs/superpowers/specs/2026-04-18-ansible-fleet-bootstrap-design.md`) — SSH key bootstrap across 4-machine fleet
- [ ] Agent Observatory (`docs/superpowers/specs/2026-04-17-agent-observatory-design.md`) — Phase 1 IN PROGRESS on branch
- [ ] Market intelligence agent (window_start Apr 13, 0 commits)
- [ ] CME templates and opportunities (`docs/superpowers/specs/2026-03-12-cme-templates-and-opportunities-design.md`)

---

## Backlog (Not Started)

- [ ] VS Wave 2: Team Roster UI
- [ ] Video Content Pipeline (Vimeo, YouTube, AI clip generation)
- [ ] Code Interpreter
- [ ] Claude Files API
- [ ] XMP Metadata (Visuals Agent)
- [ ] `/ship` command implementation and testing
- [ ] pdf-renderer: fix `test_renderer.py::test_render_about_blank_returns_pdf_bytes`
- [ ] pdf-renderer: wire application logger output through uvicorn
- [ ] pdf-renderer: upgrade base image to Python 3.11+

---

## Burndown by Week

| Week | Dates | Key Deliverables | Commits |
|------|-------|-----------------|---------|
| 1 | Feb 1-7 | Agent builds (LO, Curriculum, Research Protocol, Marketing, Grant Writer, Compliance) | ~30 |
| 2 | Feb 8-14 | Recipe orchestrator, human review workflow, deployment integration | ~20 |
| 3 | Feb 15-21 | Observability exporters, cAdvisor upgrade, TODO/doc updates | ~10 |
| 4 | Feb 22-28 | Port conflict fix, Prometheus discovery, Promtail→Loki, registry-db fixes | ~15 |
| 5 | Mar 1-7 | Next.js frontend rebuild, cloud-rewire, search page, CME schema | ~25 |
| 6 | Mar 8-14 | Session Capture Pipeline v2, VS Engine build + integration, Grafana dashboards | ~40 |
| 7 | Mar 15-21 | Agents page enhancements (tabbed container, streaming, timeline), Docker networking fixes | ~20 |
| 8 | Mar 22-Apr 5 | Orchestrator fixes (human review gates, SKIP_HUMAN_REVIEW toggle) | ~5 |
| 9 | Apr 6-8 | Decommissions (Dify, RAGFlow, LibreChat), test fixes (61/61), CI pipeline, RBAC/auth, LLManager inbox | ~30 |
| 10 | Apr 9-11 | Agents Library, Intake Prefill Agent, inference platform API, orchestrator passthrough fix | ~35 |
| 11 | Apr 12-13 | Dashboards redesign, Dev Changelog Builds 1-4, telemetry Gate A, CME edit/archive, intake-edit, auto-sync fix, /outputs passthrough | ~40 |
| 12 | Apr 14-16 | Inbox download Phase 1+2 (31 tasks), LSP setup, medkb design spec, Incident Record Library, remediator, pipeline improvements | ~80 |
| 13 | Apr 17-19 | medkb Phases 0-3 (51 commits), Agent Observatory design, TODO/doc updates | ~55 |

---

## Version History
- v2: Apr 19, 2026 — Full rebuild covering Feb 1 – Apr 19 (78 days, 395 commits, 11 phases). Added all completed, in-progress, and planned work with checkbox task lists.
- v1: Apr 6, 2026 — Original 10-day burndown (not preserved in repo).
