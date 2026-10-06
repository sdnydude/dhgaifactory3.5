# DHG AI Factory — Master Task List
**Last Updated:** Apr 20, 2026 (v19)

## System Status
- **Containers:** 22 running (21 healthy, 1 expected-unhealthy: `dhg-medkb-ingestor` stub activates Phase 5)
- **LangGraph Server:** Cloud production at `dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app` (17 graphs)
- **VS Engine:** Running, healthy, Prometheus metrics active
- **Frontend:** Next.js on :3000 (shadcn/ui + assistant-ui + CopilotKit)
- **GPU:** RTX 5080 (16GB VRAM, 26% used by Ollama)
- **Disk:** Root 12% (1.9TB), Data 6% (3.6TB)
- **Observability:** Full stack operational — Prometheus (7/7 targets UP, +medkb), Grafana, Loki+Promtail, Tempo+OTel, Alertmanager, cAdvisor, Node/Postgres exporters
- **CI/CD:** GitHub Actions (lint, test, compose validation, doc drift checker)
- **Tests:** 273 tests across 33 files — registry: 227 tests (12 files), medkb: 46 tests (21 files)
- **Branch state:** Master at `5a915a4` (55 commits ahead of v17 base `f7f85b2`). medkb Plan 1 Phases 0-3 landed. Agent Observatory Phase 1 in progress on `claude/agent-observatory-phase1` worktree (19 commits). Several auto-worktrees from parallel sessions.

---

## Phase 1: Immediate (Fix / Unblock)

1. [x] ~~Fix gh auth and push commits~~ — DONE (7 commits pushed)
2. [x] ~~Fix 16 DB-dependent test failures~~ — DONE (61/61 passing, conftest.py rewritten with `app.dependency_overrides`)
3. [x] ~~Investigate Dify worker instability~~ — DONE (decommissioned Dify + RAGFlow, zero usage)

## Phase 2: VS Wave 1 Verification

4. [x] ~~End-to-end VS pipeline test~~ — DONE (generate + select + metrics all verified)
5. [x] ~~Confirm VS metrics visible in Grafana VS dashboard~~ — DONE (Prometheus scraping, dashboard JSON provisioned)

## Phase 3: Frontend Features

6. [x] ~~Generative UI — domain panels in chat~~ — DONE (CopilotKit + 2 domain panels: needs-assessment, gap-analysis; studio page wired to 8 agents)
7. [x] ~~MCP integration — agents to external tools~~ — DONE (3 MCP servers: LangSmith, DHG AI Tracker, Antigravity)
8. [x] ~~Memory — persistent context via LangGraph checkpointing~~ — DONE (AsyncPostgresSaver in orchestrator, fallback to in-memory)
9. [~] LLManager — approval workflow with reflection for CME review — PARTIAL (Apr 7-8: master-detail inbox, reflection panel, decision bar, review store, inboxApi; needs deeper CME-specific review logic)
10. [x] ~~Agents Library — grid/list/table views, filtering, search, detail slide-over for all 17 graphs~~ — DONE (Apr 9, `agent-catalog.ts` + full component suite under `components/agents/`)
11. [x] ~~Intake Prefill Agent — PubMed-backed Section B–H draft generation~~ — DONE (Apr 10, `intake_prefill_agent.py` + store/UI wired with accept/clear controls)
12. [x] ~~CME Project Edit + Archive workflow~~ — DONE (Apr 13, `PUT /api/cme/projects/{id}`, `POST /.../archive`, edit route, archive confirm dialog, archived filter; Section A `therapeutic_area`/`disease_state` narrowed to `List[str]`)
13. [x] ~~Mission Control dashboards redesign + readability pass~~ — DONE (Apr 12-13, HSL→hex token migration, font sizes bumped, contrast tuned)
14. [x] ~~Inbox Demo Mode — sample review data for empty-state visibility~~ — DONE (Apr 9, spec + plan landed)
15. [ ] React Flow — visual LangGraph workflow editor
16. [ ] Tremor — token usage and agent performance dashboards (currently using Recharts for basic monitoring)
17. [ ] Refine — admin console with FastAPI data providers
17a. [~] Dev Changelog (Admin/Reporting section) — editable agent-assisted development log at `/admin/reporting/dev-changelog`. First TanStack deployment in the product. Builds 1-4 functionally landed and committed Apr 14 in `51503b3` (backend + migration + seed + tests), `ef7ae2a` (frontend + TanStack + filter rail + detail slide-over + editorial form), `29ad09e` (design spec).
    - **Build 1 core DONE** — `/api/dev-changelog` live (list + detail + PATCH), 16-row seed verified in DB, TanStack table with 9 column defs (slug, epic, category chip, window, commits, COALESCE display status, override, priority, locked), Zustand store, /admin/reporting/dev-changelog route gated to admin role.
    - **Build 2 DONE de facto** — detail slide-over (`dev-changelog-detail-sheet.tsx`) with agent-detected metadata grid + commits list linking to `github.com/sdnydude/dhgaifactory3.5/commit/{sha}`.
    - **Build 3 DONE de facto** — inline edit via `EditorialForm` component (declared_status / priority / key_insight / notes / locked) with dirty-state + save/discard. Server-side ownership enforcement via `DevChangelogPatch.model_config = ConfigDict(extra='forbid')` — Pydantic rejects agent-owned fields at validation time before the handler runs.
    - **Build 4 PARTIAL** — filter rail (`dev-changelog-filter-rail.tsx`) DONE with faceted status/category/window/debounced-search + live counts. Timeline/kanban view modes declared in store but only table view renders. Saved views NOT implemented.
    - **Build 5 NOT STARTED** — nightly 3am agent, blocked on #21 Phase 1 Gate B per design.
    - **Known gaps to address before calling #17a closed:**
      - [ ] **Editorial masthead** — view header is plain shadcn `<h1>`, not the Fraunces/triple-line border-top editorial treatment the spec calls for (the "hybridize with inbox editorial aesthetic" Build 1 #10). View container is `frontend/src/components/reporting/dev-changelog-view.tsx:51-62`.
      - [ ] **Real-DB tests replacing mocks** — `test_dev_changelog_endpoints.py` uses `mock_db.query.return_value.filter...` chains. Violates the pattern established in #47/#52 after Pydantic 2 rejected MagicMock datetime fields (`feedback_serializer_drift.md`). Pattern to follow: `TestCMEOutputsRealDB` in `test_cme_endpoints.py`.
      - [ ] **Playwright e2e spec** — 9 verification PNGs taken during builds, no committed test file. Verification is not reproducible in CI.
      - [ ] **Build 4 remainder** — timeline view, kanban view, saved views.
      - [ ] **Endpoint prefix normalization** — `/api/dev-changelog` vs `/api/v1/security`, `/api/v1/cme`, etc. elsewhere. Low risk while no external client hardcodes it; growing cost over time.

## Phase 4: CME Pipeline End-to-End

18. [x] ~~Orchestrator intake data passthrough fix~~ — DONE (Apr 11, `flatten_intake` aliases + 5 wrapper expansions; disease_state now reaches all agents)
19. [x] ~~End-to-end CME pipeline test (intake -> agents -> review -> output)~~ — DONE Apr 13: NSCLC project ef4e5b53 verified topic-correct in DB (research 26K chars NSCLC, clinical 13K chars NSCLC, zero cardiology contamination). Playwright UI journey verified end-to-end: project 66c96439 created via real form (Section A → Research & Prefill → Save & Start Pipeline), prefill returned 20 publications with confidence scoring, status flipped intake→processing on detail page, Edit button correctly replaced with Cancel.
20. [ ] Human review implementation wired to frontend inbox with full feedback loop
20a. [x] ~~**Auto-sync observability fix** (#51)~~ — DONE Apr 13: `cme_endpoints.py` guard `if status in (...) and pipeline_thread_id` now logs an explicit `auto-sync skipped for {id}: status={s} thread_id={t}` line on the else branch. Discovered during the fix that the module logger was using `logging.getLogger(__name__)` and uvicorn only configures `uvicorn.*` loggers — every existing logger.info/warning/error in this file had been silently dropped. Switched the module logger to `logging.getLogger("uvicorn.error")` to surface ALL existing log calls. Verified live via Playwright walkthrough: `auto-sync skipped for 66c96439...: status=intake thread_id=None` and `auto-sync skipped for ef4e5b53...: status=complete thread_id=04b36cd2...` both visible in container logs.
20b. [x] ~~**`/outputs` endpoint document_text passthrough** (#52)~~ — DONE Apr 13: added `document_text: Optional[str]` to `AgentOutput` Pydantic schema and threaded `o.document_text` through both `list_cme_outputs` and `get_cme_agent_output` endpoints. Frontend `AgentOutput` interface mirrored. 3 new real-DB integration tests (`TestCMEOutputsRealDB`) cover list, single-agent fetch, and NULL serialization. Verified live against project `ef4e5b53`: all 6 agent outputs now expose `document_text` (research=26,809 chars, clinical=13,803, gap_analysis=16,415, learning_objectives=7,455, needs_assessment=16,532, prose_quality_1=91).

## Phase 5: Hardening

21. [~] LangGraph Telemetry Pipeline Repair (Phase 1) — Tempo→Prometheus span-metrics via `otel.digitalharmonyai.com` Cloudflare tunnel, new `dhg-langgraph-exporter` service, 6 alert rules. Plan dated 2026-04-12.
    - [x] Tasks 1–5: Cloudflare tunnel route, `tracing.py` swapped to OTLP/HTTP, CF Access headers passthrough, `pyproject.toml` deps, LangSmith shared TracerProvider fix (9 commits `c7b46e6..f236196`)
    - [x] Task 6: Phase 1 Gate A — PASSED Apr 13. Root causes: (1) `CF_ACCESS_CLIENT_ID`/`SECRET` missing from LangGraph Cloud deployment — fixed via LangSmith New Revision `7477443f`. (2) Prometheus missing `--web.enable-remote-write-receiver` flag — fixed in `65d21fc`. Dashboards panel D1 wired in `8be7160`. Plan rewritten as v2 diagnostic ladder in `daf230a`.
    - [ ] Tasks 7–13 (Phase 2): `dhg-langgraph-exporter` service (TDD scaffold, impl, Dockerfile), compose wiring, Prometheus scrape job, 6 alert rules, Phase 1 Gate B — see plan v2 §F
22. [ ] Agent-level integration tests (beyond registry API tests)
23. [ ] Performance benchmarks for full pipeline
24. [x] ~~Verify Tempo trace ingestion from LangGraph agents end-to-end~~ — DONE via Phase 1 Gate A (Apr 13, see #21)
25. [ ] CD — automated deploy on merge to master

## Phase 6: Security & Infrastructure

26. [x] ~~Build DHG Security Agent (Cloudflare Access, GraphQL analytics)~~ — DONE (RBAC models, JWT auth, audit logging, admin endpoints, 44 tests)
27. [x] ~~Decommission legacy Docker agents (ports 8002-8008)~~ — DONE (stopped, restart: "no")
28. [x] ~~Decommission LibreChat stack~~ — DONE (5 containers, 1 volume, 2.4 GB removed)
29. [x] ~~Docker disk cleanup~~ — DONE (34.6 GB reclaimed via prune)
30. [x] ~~Local LLM Inference Platform (API scaffolding)~~ — DONE (Apr 11, DB tables + SQLAlchemy models + Pydantic schemas + FastAPI endpoints + LLMRouter registry integration, 7 commits)

## Phase 7: Inbox Document & Project Download

Plan: `docs/superpowers/plans/2026-04-14-inbox-document-project-download.md` (5 phases, ~40 tasks). Active work on branch `lsp-setup`. New sibling service `dhg-pdf-renderer` built from scratch in this feature (see System Status row).

41. [x] ~~**Phase 1 — Single Document Download (sync path)**~~ — DONE Apr 14, Tasks 1.1–1.12 (commit range `e4ec07d..db0d76d`). `services/pdf-renderer/` scaffolded with Playwright render helper (wait-for-`[data-chart-ready]`), `/render-sync` endpoint, Dockerfile, compose wiring, `dhg_exports` volume. HMAC-signed print tokens (`registry/export_signing.py` + Edge-Runtime TS verifier `frontend/src/lib/printTokens.ts`). `/print/cme/document` Next.js print route with middleware bypass for `/print/*`. `/api/cme/export/document` registry endpoint with internal fetch helper. `exportApi.ts` frontend client, download button in review masthead, Playwright E2E `frontend/e2e/inbox-document-download.spec.ts`.

42. [x] ~~**Phase 2 v2 — Full Project Download + Google Drive Sync (md-only)**~~ — DONE Apr 16, 19/19 tasks (commit range `ef5126e..7108b3e`). Migration 009+010, SQLAlchemy model extensions, Pydantic bundle/project schemas, 6 export endpoints, md-only bundler with atomic zip, Google Drive client + sync action, worker loop (`FOR UPDATE SKIP LOCKED`, 3 scopes), orchestrator `enqueue_drive_sync` hook, `filesApi.ts` frontend client, files-tab Zustand store, Files tab UI (tree + multi-select + download bar), sidebar tab switcher (Reviews/Files), downloads store + polling hook, downloads tray UI, 5-test E2E suite (list projects, list docs, full bundle round-trip with zip verification, 404/409 error cases). Tagged `phase2v2`.

43. [ ] **Phase 3 — Quality / Review History / Citations + chart-ready wait** — NOT STARTED. 10 tasks. Source readers (`quality.py`, `review_history.py`, `citations.py`), chart-ready wait attribute on `daily-chart.tsx`, `QualityPrint` + `ReviewHistoryPrint` components with Tremor charts, print routes + internal hydrating endpoints, bundler extension for quality/review/citations, round-trip integration test.

44. [ ] **Phase 4 — Revision history with paragraph-level semantic diff** — NOT STARTED. 8 tasks. Checkpoint history fetcher, paragraph-level semantic diff algorithm (TDD), three-round golden file test, `RevisionHistoryPrint` component, print route + internal endpoint, bundler integration behind `EXPORT_INCLUDE_REVISIONS` flag, manual review of a real two-round fixture.

45. [ ] **Phase 5 — Hardening** (TTL, rate limiting, retry, observability) — NOT STARTED. 10 tasks. TTL cleanup task, rate limiting on project enqueue, retry UX on failed jobs, tray filters (all/running/succeeded/failed), compliance stamp in `README.txt`, Chromium memory watchdog in pdf-renderer, signing key rotation support, Prometheus metrics on the registry, Grafana panel + Alertmanager rule, load test + phase closeout.

## Phase 9: medkb RAG-as-a-Service (Apr 17-19, 2026) — DONE (Phases 0-3)

Plan: `docs/superpowers/plans/2026-04-17-medkb-plan1-foundation.md`. Design spec: `docs/superpowers/specs/2026-04-17-medkb-rag-as-a-service-design.md`.

53. [x] ~~**Phase 0 — Skeleton (Tasks 0.1-0.14)**~~ — DONE. 4 Docker containers (`dhg-medkb-db` :5435, `dhg-medkb-cache` :6381, `dhg-medkb-api` :8015, `dhg-medkb-ingestor` stub), FastAPI scaffold with `/v1/healthz` + `/v1/readyz` + `/metrics`, SQL schema with pgvector + tsvector, SQLAlchemy ORM models, async DB engine, Pydantic Settings config, OTel tracing with `@traced_node`, Prometheus metrics registry, token budget tracker, Dockerfile with healthcheck, Prometheus scrape target added. 32 commits on `feature/medkb-phase0`, merged to master via `47035b3`.

54. [x] ~~**Phase 1 — Dense Retrieval (Tasks 1.1-1.13)**~~ — DONE. `Retriever` Protocol + `RetrievedChunk` dataclass, `PgVectorRetriever` with dual-embedding support (Ollama nomic-embed-text), LLM factory via `init_chat_model`, 9 graph nodes (redact, analyze_query, retrieve_fan, rerank, format_cite, emit_feedback + generate added in Phase 2), conditional edge functions, graph builder with `strategy=regular` flow, seed corpus with 3 CME sample documents, corpora CRUD endpoints, `/v1/query` endpoint with graph invocation, PgVectorRetriever wired into query flow.

55. [x] ~~**Phase 2 — Generation + Citations**~~ — DONE. `generate` node with LLM answer generation via ChatAnthropic/ChatOllama, `format_cite` node with citation assembly, Ollama `base_url` fix for Docker networking.

56. [x] ~~**Phase 3 — Hybrid + CRAG**~~ — DONE. `BM25Retriever` (tsvector + `ts_rank_cd`), `HybridRetriever` (RRF fusion), retriever registry mapping corpus → retriever, `grade_docs` node (LLM relevance grading), `rewrite_query` node (LLM query rewriting), CRAG conditional edges, `/v1/retrieve` endpoint, Cloudflare JWT `auth.py` module, `readyz` dependency checks (DB + Redis + Ollama).

57. [ ] **Phase 4 — Ingestor Pipeline** — NOT STARTED. See #46a.
58. [ ] **Phase 5 — Production Hardening** — NOT STARTED. See #46b.

## Phase 10: Incident Record Library (Apr 16, 2026) — DONE

Full incident management system — backend, frontend, remediation sidecar, 58 tests. Previously undocumented in TODO (predates v17 base but was omitted).

59. [x] ~~**Full Incident Record Library**~~ — DONE (`21d7be1`). Backend: migration 011 (incidents, events, actions, runbooks, postmortems tables), `incident_endpoints.py` + `incident_service.py` + `incident_schemas.py`, 10 seeded runbooks (`seed_runbooks.py`), 35+23=58 tests across 2 files. Frontend: `/monitoring/incidents` route, incident list + filters + stats + detail panel, `incidentsApi.ts` client, Zustand store. Prometheus: 97-line alert rule expansion. 20 files changed, ~4000 lines.
60. [x] ~~**Remediation sidecar**~~ — DONE (`7201da8`). `services/remediator/` — polls registry for active incidents, matches to runbooks, executes remediation steps. Three modes: `auto`, `approval` (diagnostic-only), `none`. Safety: hard-blocked commands, container allowlist, rate limiting, dry-run mode. Postmortem creation form in frontend.
61. [x] ~~**Snapshot dashboard + prefilled postmortem**~~ — DONE (`829e79c`). `snapshot-dashboard.tsx` component (264 lines), prefilled postmortem form from incident data.

## Phase 11: Pipeline Improvements (Apr 16, 2026) — DONE

62. [x] ~~**Guided character mode**~~ — DONE (`efbd9b7`). `CharacterConfig` intake schema, needs_assessment_agent updated with character-driven content generation.
63. [x] ~~**Learning objectives agent crash fix**~~ — DONE (`1b1f1e5`). `int` cast for `moore_level_target` + key mismatch fix in orchestrator.

## Phase 8: Active Worktree Streams (Updated Apr 19, 2026)

Active worktrees in `.claude/worktrees/`:

51. [~] **agent-observatory-phase1** (`claude/agent-observatory-phase1`) — React Flow-based Agent Observatory with timeline playback, scenario comparison, and architecture visualization. 19 commits ahead of master. Design spec at `docs/superpowers/specs/2026-04-17-agent-observatory-design.md`. Components: graph canvas, custom node components, 4 example scenarios × 5 architectures, playback engine, metrics bar, compare view, detail panel, Playwright E2E suite. Uses `@xyflow/react`. **Not merged — needs review.**
52. [ ] **master-review** (`claude/master-review`) — Full code review of master at `f7f85b2` (P0:11, P1:58, P2:45 issues). Reference artifact for prioritizing tech debt.

**Retired streams:** `claude/medkb-phase1` (scope merged to master Apr 17-19, 51 commits), `claude/inbox-files-tab` (shipped in `phase2v2` tag Apr 16), `claude/legacy-port-cleanup`, `claude/agent-slo-alerts`, `claude/audit-log-viewer` (worktrees removed, scope remains in backlog as #48, #49, #50).

**Auto-worktrees from parallel sessions:** 6 `claude-branch/*` worktrees exist — most are at or behind master HEAD with 0-3 commits. `priceless-hoover-c8e359` has a docs-check routine + `/ship` close rule (3 commits, not merged).

48. [ ] **legacy-port-cleanup** — Resolve Issue O1: remove orphan legacy orchestrator on port 2024, retire `agents/` code.
49. [ ] **agent-slo-alerts** — Alertmanager SLO rules for 13 LangGraph agents + Grafana panel.
50. [ ] **audit-log-viewer** — Read-only `/manage/audit-log` route, paginated + filtered, admin-RBAC gated.

Merge order: `git merge --no-ff` always; serialize streams that touch `frontend/src/` sidebar.

---

## Backlog

31. [ ] VS Wave 2: Team Roster UI
32. [ ] Video Content Pipeline (Vimeo, YouTube, AI clip generation)
33. [ ] Code Interpreter
34. [ ] Claude Files API
35. [ ] XMP Metadata (Visuals Agent)
36. [x] ~~RAGFlow configuration~~ — DECOMMISSIONED (zero usage, removed)
37. [ ] `/ship` command implementation and testing
38. [ ] **pdf-renderer: fix `test_renderer.py::test_render_about_blank_returns_pdf_bytes`** — pre-existing failure. AsyncMock chain returns an AsyncMock instead of bytes because `playwright.async_api` is stubbed in conftest; the test asserts `len(pdf) > 1024` which fails. Either stub the full `page.pdf()` chain to return real bytes, or gate the test on Playwright actually being installed.
39. [ ] **pdf-renderer: wire application logger output through uvicorn** — worker/bundler/drive_sync use `logging.getLogger(__name__)` at INFO level but uvicorn's default log config suppresses non-uvicorn loggers, so `worker loop started` and `drive sync done` never appear in `docker logs`. Add a logging config dict in `main.py` or a LOG_LEVEL env-driven setup so live debugging of the worker loop is possible.
40. [ ] **pdf-renderer: upgrade base image to Python 3.11+** — `mcr.microsoft.com/playwright/python:v1.48.0-jammy` ships Python 3.10.12. `google-api-core` fires a FutureWarning on every boot about 3.10 EOL (2026-10-04). Upgrade when Playwright publishes a 3.11+ image, or pin an alternate base.

41. [ ] **Network architecture / VLAN planning for PostHog's isolation** — separate brainstorm. Referenced by PostHog self-host spec (`docs/superpowers/specs/2026-04-18-posthog-self-host-design.md`). Scope: where PostHog's mini-PC sits in the existing VLAN topology (TCP/IP, Dante, NDI), LAN addressing, ingest traffic isolation from production DHG services. Not a blocker for PostHog spec review, but blocks PostHog deployment prerequisites.

42. [ ] **Sonos VLAN, TV/Apple TV VLAN, mDNS server, NDI discovery server** — separate brainstorm. Home/studio network infrastructure extension. Adds two new VLANs (Sonos, TVs/Apple TVs) to the existing TCP/IP + Dante + NDI scheme. Ryzen 6900 mini-PC earmarked as potential DNS/mDNS/NDI-discovery host. Parked — not blocking any active DHG work.

43. [ ] **Visual agent editor evaluation** — parked brainstorm. User-facing drag-and-drop agent builder (Flowise/Langflow/similar) as an install-only addition, not a UI replacement. Goal: let users build their own agents alongside the curated DHG agent library. Gated on #44 — the original Dify-decommission premise that Onyx + Pixeltable + RAGFlow covered Dify's capabilities must be re-verified before picking a tool.

44. [ ] **Revisit Onyx / Pixeltable capability claims** — separate task. Dify decommissioning (Apr 6) was based on a claim that we "could do anything Dify could" via Onyx, Pixeltable, and RAGFlow. RAGFlow has since also been decommissioned. The claim's current validity with only Onyx + Pixeltable remaining is unverified. Concrete deliverable: a capability matrix of Dify vs. (Onyx + Pixeltable) covering drag-and-drop agent building, pre-built agent marketplace, user self-service, and integration with LangGraph. Blocks #43.

46. [x] ~~**medkb Plan 1 — Phases 0-3 (Foundation + Hybrid Retrieval)**~~ — DONE Apr 17-19. 51 commits (`518cd1e..5a915a4`), 46 tests across 21 files, all 4 containers running. Full RAG-as-a-Service with dense + BM25 + hybrid RRF retrieval, LLM generation via init_chat_model, CRAG quality loop (grade_docs + rewrite_query), Cloudflare JWT auth, corpora CRUD, Prometheus metrics. See Phase 9 below for details.
46a. [ ] **medkb Plan 1 — Phase 4 (Ingestor Pipeline)** — NOT STARTED. `SourceIngestor` base, MeSH/RxNorm/PubMed/PMC OA ingestors, concept reconciliation, golden test set + Recall@5 quality gate.
46b. [ ] **medkb Plan 1 — Phase 5 (Production Hardening)** — NOT STARTED. Activate `dhg-medkb-ingestor` worker, `medkb_client.py` LangGraph integration, exit-gate verification script.

---

## Completed (April 2026)

- [x] **medkb Plan 1 Phases 0-3 — RAG-as-a-Service foundation** (Apr 17-19, 51 commits `518cd1e..5a915a4`) — Complete RAG service from scratch in `services/medkb/`. Phase 0: 4 Docker containers (medkb-db :5435, medkb-cache :6381, medkb-api :8015, medkb-ingestor stub), PostgreSQL 15 + pgvector schema, FastAPI scaffold, OTel tracing, Prometheus metrics. Phase 1: Retriever Protocol + RetrievedChunk, PgVectorRetriever with dual-embedding, LLM factory via init_chat_model, 9-node LangGraph StateGraph (redact → analyze → retrieve_fan → rerank → generate → format_cite → emit_feedback + grade/rewrite for CRAG), seed corpus, corpora CRUD, `/v1/query` endpoint. Phase 2: generate node with Claude/Ollama LLM, format_cite citation assembly. Phase 3: BM25Retriever (tsvector), HybridRetriever (RRF fusion), retriever registry, grade_docs + rewrite_query CRAG nodes, `/v1/retrieve` endpoint, Cloudflare JWT auth module, readyz dependency checks. 46 tests across 21 files. Plan reconciled with 6 implementation drifts (port remapping, network declaration, pin relaxation, runtime retriever injection, metrics import, ORM event listener).

- [x] **Incident Record Library + Remediation Sidecar** (Apr 16, commits `21d7be1..829e79c`) — Full incident management system. Backend: migration 011 (5 tables: incidents, events, actions, runbooks, postmortems), `incident_service.py` (529 lines), `incident_endpoints.py`, `incident_schemas.py`, 10 seeded runbooks, 58 tests across 2 files. Frontend: `/monitoring/incidents` route with list + filters + stats + detail panel + postmortem form + snapshot dashboard, `incidentsApi.ts`, Zustand store. Remediation sidecar (`services/remediator/`): polls for active incidents, matches to runbooks, executes steps in auto/approval/none modes with safety controls (hard-blocked commands, container allowlist, rate limiting, dry-run). Prometheus alert rules expanded (+97 lines). Previously undocumented — predates v17 base.

- [x] **Guided character mode + LO crash fix** (Apr 16, `efbd9b7` + `1b1f1e5`) — `CharacterConfig` intake schema for persona-driven content generation in needs_assessment_agent. Learning objectives agent crash fixed: `int` cast for `moore_level_target` + orchestrator key mismatch.

- [x] **Cleanup & dependency bumps** (Apr 17-18) — Removed dead `asr/` directory (`8f6f9cb`). Bumped `python-multipart` 0.0.22→0.0.26, `cryptography` 46.0.6→46.0.7 in registry (`56fa2df`). Bumped `pytest` 8.3.3→9.0.3 in pdf-renderer dev deps (`c207957`).

- [x] **medkb documentation suite** (Apr 17-18) — RAG-as-a-Service design spec (`docs/superpowers/specs/2026-04-17-medkb-rag-as-a-service-design.md`), architecture overview with registry + DHG service integration addendum (`docs/architecture/MEDKB_ARCHITECTURE.md`), Claude Design brief + Nano Banana diagram prompts (`docs/architecture/MEDKB_CLAUDE_DESIGN_BRIEF.md`, `MEDKB_DIAGRAM_PROMPTS.md`), Agent Observatory design spec (`docs/superpowers/specs/2026-04-17-agent-observatory-design.md`), Ansible fleet bootstrap design spec (`docs/superpowers/specs/2026-04-18-ansible-fleet-bootstrap-design.md`).

- [x] **Inbox Document & Project Download Phase 1 — Single-document sync path** (Apr 14, Tasks 1.1–1.12, commit range `e4ec07d..db0d76d`) — New sibling service `dhg-pdf-renderer` scaffolded from scratch. Build order: (1) service directory + requirements.txt + minimal main.py + /health, (2) HMAC signing module with failing-test-first TDD (`registry/test_export_signing.py` → `registry/export_signing.py` → Edge-Runtime TS verifier `frontend/src/lib/printTokens.ts`, `EXPORT_SIGNING_SECRET` wired to frontend compose env), (3) Playwright render helper with wait-for-`[data-chart-ready]` attribute (TDD, `services/pdf-renderer/renderer.py`), (4) `/render-sync` endpoint with URL validation (TDD, `services/pdf-renderer/main.py`), (5) Dockerfile + compose wiring with `shm_size: 2gb` and `dhg_exports` volume mount (read-only on registry-api side), (6) Next.js print layout + print stylesheet + print shell component + `/print/cme/document` route, (7) middleware bypass for `/print/*` with HMAC verify TDD, (8) `registry/export_schemas.py` Pydantic bundle, (9) `/api/cme/export/document` sync endpoint + `export_service.py` + `fetch_latest_document_for_thread` stub + router wired in `api.py`, (10) `exportApi.ts` frontend client, (11) download button in review panel masthead, (12) Playwright E2E `frontend/e2e/inbox-document-download.spec.ts` + `playwright.config.ts` + `playwright test` npm script. Also `7db05d8` fix: TS token verifier rewritten for Edge Runtime (original used Node `crypto` which Edge blocks). Also `eaf9a63` fix: filter zombie interrupted threads from review count and list (pre-existing bug surfaced while testing download button). Also `18bf5e3` refactor: replaced editorial masthead with standard page header (per design review). Also `775ea66` compose: `dhg-pdf-renderer` service + `dhg_exports` volume.

- [x] **Inbox Document & Project Download Phase 2 v2 — Full project download + Google Drive sync (md-only)** (Apr 14–16, Tasks 2.1–2.19, commit range `ef5126e..bf711ca`, tagged `phase2v2`) — all 19 tasks complete. Tasks 2.14–2.19 closeout: `1bb841d` files-tab Zustand store, `7607bbb` downloads store + `use-download-polling` hook, `f68aaca` Files tab + Downloads tray wired into inbox tab switcher, `7108b3e` 5-test E2E round-trip (enqueue → poll → download → verify zip manifest), `bf711ca` docs close-out. Build order: (1) migration 009 `009_add_download_jobs` + (2) `DownloadJob` SQLAlchemy model, (3) migration 010 `010_download_feature_v2` schema extension with `project_id` FK + `scope` CHECK constraint narrowed to `{document, project_bundle, drive_sync}` + `drive_file_id`/`drive_folder_id`/`drive_mime_type`/`selected_document_ids` — downgrade path drains incompatible scope rows before narrowing CHECK (`569e0cd`), (4) SQLAlchemy model updates extending `DownloadJob` + `CMEProject` (Drive folder fields) + `CMEDocument` (Drive file fields), (5) Pydantic v2 schemas — `BundleJobCreate`/`BundleJobResponse` in `export_schemas.py` + `ProjectListItem`/`ProjectListResponse`/`ProjectDocumentItem`/`ProjectDocumentsResponse` in `project_schemas.py`, (6) project list + project documents endpoints under `/api/cme/export/projects` TDD — initial commit `f5dbedc` later amended to `18f937c` after path-prefix reconciliation, (7) bundle enqueue endpoint + amended `/job/{id}` + `/artifact/{id}` + `/jobs` routes TDD, (8) md-only project bundler with atomic zip writer TDD (`services/pdf-renderer/bundler.py`), (9) Google Drive service-account client factory + `google-api-python-client`/`google-auth` deps (`services/pdf-renderer/drive_client.py`), (10) Drive sync worker action with `manifest.json` reconciliation TDD (`services/pdf-renderer/drive_sync.py`), (11) worker loop with `FOR UPDATE SKIP LOCKED` + three-scope dispatch (`services/pdf-renderer/worker.py`, `test_worker_claim.py`) — worker lifespan made optional until runtime deps land (`70cdb66`) then registry package + DB deps wired (`eed1f72`), (12) orchestrator `enqueue_drive_sync` helper + milestone call sites (`langgraph_workflows/dhg-agents-cloud/src/drive_sync.py`, wired into needs/curriculum/grant recipes), (13) `frontend/src/lib/filesApi.ts` frontend client with `credentials: "include"` cookie forwarding + `encodeURIComponent` on IDs + unified `request<T>()` helper. Phase 2 v2 also required `bed50ea` plan amendment to switch bundler + drive sync to md-only (PDF-in-bundle deferred) — rationale: unblocks Phase 2 ship on md-only output, PDF fan-out becomes Phase 3 concern.

- [x] **Registry proxy binary body fix** (Apr 15, `b736357` → merged via `bc9cfd5` inbox-repair) — Next.js `/api/registry/[...path]/route.ts` was text-decoding the upstream response body via `await upstream.text()` + `new Response(text, ...)`, which corrupts PDF/zip binaries on roundtrip. Fix: detect binary content types (`application/pdf`, `application/zip`, `application/octet-stream`) and preserve `arrayBuffer()` + pass through unchanged. Unblocked Phase 1 downloads through the Next.js proxy — without this fix, the download button returned corrupted PDFs.

- [x] **Delete `full_pipeline` orchestrator recipe** (Apr 15, `a1f85f0` → merged via `bc9cfd5` inbox-repair) — Dead code from an earlier orchestration experiment. Only 3 active recipes remain (`needs_package`, `curriculum_package`, `grant_package`) as documented in CLAUDE.md. `full_pipeline` was an 11-agent linear chain predating the milestone-review pattern.

- [x] **medkb v2 unified design spec + Phase 1 plan draft** (Apr 15, `67abc4d`) — Medical knowledge-base service design covering Phases 1–5 with addendum. Parallel design work surfaced during this burst. Phase 1 implementation plan drafted at `docs/superpowers/plans/2026-04-15-medkb-phase1.md` (23 tasks, 4302 lines, 47k tokens) — scaffold, compose services (`dhg-medkb-db` + `dhg-medkb-api`), Alembic schema, OllamaEmbeddingClient TDD, DB session wiring, `/healthz` integration test, `/v1/concept/{source}/{source_id}` + `/v1/graph/neighbors/{concept_id}` + `/v1/search/semantic` + `/v1/search/literature` endpoints (all TDD), `SourceIngestor` base + chunking + concept reconciliation helper, MeSH + RxNorm + PubMed + PMC OA ingestors (TDD with recorded fixtures), golden test set authorship, Recall@5 measurement harness as Phase 1 quality gate, Prometheus metrics + Grafana scrape target, `medkb_client.py` helper + LangGraph smoke test, Phase 1 exit-gate verification script. Tracked as backlog #46.

- [x] **LSP setup (pyright + typescript-language-server) — Task 6 live verification complete** (Apr 14, branch `lsp-setup`, commits `bcd5a2a` → `c626a62`) — `pyrightconfig.json` at repo root with language-subtree-specific `executionEnvironments` (langgraph uses its existing venv, registry uses SQLAlchemy-1.x-aware cascade mutes). Both language servers operational via Claude Code's LSP tool after a `~/.local/bin` symlink workaround for a non-interactive-shell PATH gotcha (`.bashrc` doesn't get sourced by CC's launch context, so the `~/.npm-global/bin` export never fired — durable fix deferred). Task 6 live verification ran 5 probes end-to-end: `hover` on `FastAPI`/`StateGraph` imports (library symbols — full class docs returned), `goToDefinition` on `CMEPipelineState` (project Python — → orchestrator.py:115), `findReferences` on `get_db` (136 refs across 19 files), `goToDefinition` on `ReviewPayloadWithVS` through the `@/` tsconfig path alias (→ types.ts:62). Key operational rule captured in CLAUDE.md + memory: **pyright's `goToDefinition` does NOT navigate into third-party packages by design — use `hover` for library symbols, `goToDefinition`/`findReferences` for workspace code.** Original Task 6 acceptance had this wrong; spec rewritten with a Pyright LSP Behavior Notes section and a post-mortem so future readers don't re-hit it. Also surfaces a latent bug at `orchestrator.py:1795` (`await AsyncPostgresSaver.from_conn_string(...)` — `from_conn_string` returns an async context manager, not an awaitable) which has been logged for a separate debug task. Branch left unmerged (carries unrelated inbox-download feature work in parallel — merge gated on that feature's readiness, not LSP).
- [x] **Playwright E2E intake journey** (Apr 13, #53) — full UI walkthrough verified: project 66c96439 created via `/projects/new` form (Section A → Research & Prefill → Accept All → Save & Start Pipeline), Intake Prefill Agent returned 20 PubMed publications with mixed Low/Med/High confidence per section, detail page transitioned `intake → processing` on reload, Edit button correctly swapped for Cancel by `canEdit` gate. End-to-end journey from #19 closed.
- [x] **`/outputs` endpoint document_text passthrough + frontend wiring** (Apr 13, #52, commit `1ec1cb3`) — Wire-fix only would have been a no-op: `step-content.tsx` extracts prose from `output.content` via per-agent `DOCUMENT_KEYS` map and never read `output.document_text`. Code review (superpowers:code-reviewer) caught this — the prose body would still be missing in the document viewer for any agent whose content JSON doesn't include the agent-specific `*_document` key. Backend: added `document_text: Optional[str] = None` to `AgentOutput` Pydantic + threaded through both list and single-fetch endpoint constructors + 3 real-DB tests in `TestCMEOutputsRealDB`. Frontend: mirrored `document_text: string | null` on TS interface + made `extractDocument()` prefer `output.document_text` (with `>10` char guard matching backend convention) before falling back to existing key map. Verified live against ef4e5b53: 6 outputs populated (research=26,809 chars, clinical=13,803, gap_analysis=16,415, learning_objectives=7,455, needs_assessment=16,532, prose_quality_1=91). `npx tsc --noEmit` clean across frontend. Reviewer-flagged followups deferred: list endpoint payload size (will balloon to ~150-200KB at full pipeline), `/webhook/agent-complete` writer never sets `document_text`, search endpoints don't query `cme_agent_outputs.document_text` despite column being designed for it. Memory saved as `feedback_serializer_drift.md` — when DB has data but API doesn't, suspect serializer drift before migration.
- [x] **Auto-sync observability + silent logger fix** (Apr 13, #51) — guard `if status in (...) and pipeline_thread_id` now logs an explicit `auto-sync skipped for {id}: status={s} thread_id={t}` line on the else branch. Discovered during the fix that `cme_endpoints.py` was using `logging.getLogger(__name__)` and uvicorn only configures `uvicorn.*` loggers — every existing logger.info/warning/error in the file had been silently dropped for the file's entire history. One-symbol fix to `logging.getLogger("uvicorn.error")` surfaced 12 previously-invisible log calls. Verified live via Playwright walkthrough.
- [x] **Intake-edit-after-submit feature** (Apr 13) — backend PUT loosened to allow editing terminal/review states with `intake_version` bump (#46); 4 real-DB integration tests in `TestCMEProjectUpdateIntegration` replacing mock success-path tests after Pydantic 2 rejected MagicMock datetime fields (#47); frontend Edit button + edit page guards loosened to non-processing/non-archived (#48); stale-intake amber banner in `run-status-banner.tsx` triggered when `project.intake_version > run.intake_version_used` with rerun CTA (#49)
- [x] **NSCLC fingerprint test** (Apr 13) — fresh project ef4e5b53 ran end-to-end through LangGraph Cloud, both research and clinical agents produced topic-correct NSCLC content (#28, #45). Confirms cardiology-scrub commit 627f1df + intake-drop fix 3a4e30d both working in production.
- [x] CME Project edit + archive workflow (PUT/POST endpoints, edit route, archive dialog, archived filter, +7 tests)
- [x] Section A schema narrowing: `therapeutic_area`, `disease_state` → `List[str]` (DB verified already in target shape)
- [x] Intake form `useState`→`useEffect` bug fix (edit-mode seeding was running as lazy initializer)
- [x] Agents Library (Apr 9) — grid/list/table/toolbar/slide-over components, static catalog for 17 graphs
- [x] Intake Prefill Agent (Apr 10) — 4-node LangGraph agent with PubMed research + structured LLM prefill
- [x] Inbox Demo Mode (Apr 9) — sample review data for empty-state visibility
- [x] Orchestrator intake passthrough fix (Apr 11) — `flatten_intake` aliases + wrapper expansions
- [x] Local LLM Inference Platform API (Apr 11) — DB tables, models, schemas, endpoints, LLMRouter integration
- [x] Mission Control dashboards redesign (Apr 12-13) — HSL→hex token migration, chart color repair, font/contrast tuning
- [x] Inbox redesign as editorial print journal (Apr 8)
- [x] Security bumps: `next` 16.1.6→16.2.3, `cryptography` 41.0.7→46.0.6, `PyJWT` 2.8.0→2.12.0
- [x] Registry Agent gateway — mediates all agent writes to Registry API (idempotency, dead letter queue, batch citations)
- [x] 3 new CME POST endpoints (source-references, agent-outputs, documents) with idempotency + background Ollama embeddings
- [x] Citation Checker refactored — embedded registry save replaced with prepare_registry_request output pattern
- [x] DB migrations 004 (RBAC) + 005 (verification_status) applied
- [x] Agent Creation SOP updated with deployment steps + admin approval gates
- [x] TypedDict fix across 11 agent files for LangGraph Cloud Python < 3.12 compatibility
- [x] All 17 graphs deployed to LangGraph Cloud (2 new: registry, citation_checker)
- [x] Security/RBAC system: Cloudflare JWT auth, 5-role RBAC, audit logging, admin endpoints, CORS lockdown, Alembic migration, 44 tests (105 total)
- [x] Infrastructure audit re-run (March vs April comparison)
- [x] Promtail -> Loki log pipeline fixed (Docker Root Dir volume mount)
- [x] Cloudflare tunnel cleanup (removed unused c2l route)
- [x] OTel tracing added to all 11 LangGraph agents (85 @traced_node decorators)
- [x] Documentation consolidated (42 docs archived, CLAUDE.md canonical)
- [x] Healthchecks added to 6 containers (Promtail, Ollama, Tempo, Node Exporter, Postgres Exporter, LangGraph)
- [x] Healthcheck commands fixed (Promtail wget->bash, Ollama curl->bash)
- [x] API tests: 23 new tests (CME endpoints + agent endpoints + conftest Prometheus cleanup)
- [x] GitHub Actions CI pipeline with lint, test, compose validation
- [x] Full documentation review and update (CLAUDE.md, README.md, TODO.md, operational docs)
- [x] Documentation drift checker (scripts/generate-docs.py + CI job)
- [x] Fixed 16 DB-dependent test failures (conftest.py dependency_overrides, schema fixes) — 61/61 passing
- [x] Decommissioned Dify (13 containers, 80 restarts, zero usage) and RAGFlow (5 containers, zero usage)

## Completed (Mar 14-15, 2026)

- [x] VS Engine built and deployed (healthy, Prometheus metrics: spread, selection_delta)
- [x] VS integrated into all 8 content agents (36 generation nodes)
- [x] Orchestrator collects VS distributions from all 9 agents
- [x] VS Grafana dashboard deployed
- [x] VS alternatives panel in frontend inbox
- [x] Migrated gap_analysis_agent from vs_distribution to vs_distributions dict

## Completed (Mar 10-14, 2026)

- [x] Session Capture Pipeline fully built (session-logger v2.0.0, Ollama embeddings 768d, summarization, PDF export, knowledge graph)
- [x] Switched all embeddings from OpenAI to Ollama (nomic-embed-text 768d)
- [x] Backfill endpoint added and run (all rows embedded)
- [x] Session-logger stats endpoints, Prometheus metrics, connection pooling, 14 tests
- [x] Monitoring dashboard frontend (stats cards, API proxies, tab navigation, Zustand store)
- [x] `/ship` command 7-phase design completed
- [x] CME intake template created
- [x] Market intelligence design spec documented

## Completed (Mar 3-9, 2026)

- [x] Antigravity-to-Claude Code migration COMPLETE (10/10 criteria met)
- [x] Frontend rebuilt on Next.js + shadcn/ui + assistant-ui + CopilotKit
- [x] Cloud-rewire: server-side proxy, polling sync, full frontend rebuild
- [x] Search page + search API client + registry search/RAG endpoints
- [x] Compliance-ready CME database schema with RAG embeddings
- [x] Studio route, real alerts, webhook endpoint
- [x] Review UI components wired into Agent Inbox
- [x] interrupt()-based human review in all 4 orchestrator recipes
- [x] Topic extraction, PubMed citations, references added to all 9 content agents
- [x] Graceful OTel degradation, importlib Cloud runtime fix

## Completed (Feb 27 - Mar 2, 2026)

- [x] Resolved C1 port conflict, C3 network isolation, C5 hardcoded IPs, C6 stale files
- [x] Security fix: python-multipart CVE
- [x] Prometheus Docker service discovery, GitHub Actions CI
- [x] Promtail -> Loki, Tempo tracing, registry-db fixes
- [x] Infisical orphan removed, Dify port moved, LibreChat deprecated
- [x] Cloudflare tunnel configured, LangGraph Cloud production deployment

## Completed (Feb 18-26, 2026)

- [x] 54 containers inventoried, LangGraph frontend strategy decided
- [x] Observability exporters deployed, cAdvisor upgraded
- [x] Migrated to Claude Code

## Completed (Earlier)

- [x] Audio agent, Recipe-Based Orchestrator, Marketing Plan agent
- [x] Docker healthchecks, Registry-API rebuild, LangGraph proxy
- [x] CME intake PostgreSQL, RAGFlow OAuth, Infisical CLI
- [x] Antigravity sessions ingested, pgAdmin deployed

---

## Version History
- v18: Apr 19, 2026 — current (medkb Plan 1 Phases 0-3 DONE — 51 commits, 46 tests, 4 containers, full RAG-as-a-Service with dense + BM25 + hybrid retrieval, LLM generation, CRAG quality loop. Added Phases 9-11 documenting medkb, Incident Record Library + remediator sidecar, and pipeline improvements that had been implemented but undocumented. Incident Library was undocumented since v17 despite being on master — 58 tests, 5 new DB tables, full frontend. Agent Observatory Phase 1 in progress on worktree branch (19 commits, not merged). Worktree landscape changed: 4 original Phase 8 streams retired/completed, replaced with observatory + master-review + 6 auto-worktrees. Test count jumped from 119→273 (registry 227 + medkb 46). Container count corrected to 22 running. New design specs: Agent Observatory, Ansible fleet bootstrap, medkb Claude Design brief. Cleanup: asr/ removed, deps bumped. Saved v17 as docs/archive/TODO_v17.md.)
- v17: Apr 17, 2026 — (Worktree stream audit session. Verified on master that Phase 2 v2 is DONE 19/19 / tagged `phase2v2` Apr 16; discovered CLAUDE.md "Inbox Document & Project Download" block was stale claiming 13/19. Five worktrees created off master @ `f7f85b2` for parallel development streams, then #1 `inbox-files-tab` retired because its scope was already shipped — verified via commit range `1bb841d..bf711ca` and tag. Added Phase 8 section listing active streams (medkb-phase1, legacy-port-cleanup, agent-slo-alerts, audit-log-viewer) + retired-stream note. Renumbered from Phase 6 during audit — Phases 6 and 7 already claimed (Security & Infrastructure, Inbox Document & Project Download). Fixed stale 13-of-19 line in Apr-2026 Completed section. Removed orphan `docs/TODO_v15.md` (superseded by v16 tracked file, never committed). Related: CLAUDE.md Phase 2 v2 block corrected in separate commit.)
- v16: Apr 16, 2026 — Phase 2 v2 closeout landed: `1bb841d` files-tab store + selection/expansion state, `7607bbb` downloads store + polling hook, `f68aaca` Files tab + Downloads tray wired into inbox tab switcher (Tasks 2.16 + 2.17b), `7108b3e` 5-test E2E round-trip with zip manifest verification, `bf711ca` docs close-out. Tag `phase2v2` at `bf711ca`. 19/19 tasks complete; `lsp-setup` ancestry merged through to master.
- v15: Apr 15, 2026 (Inbox Document & Project Download feature landed in massive burst across 3 parallel sessions 2026-04-14 evening into 2026-04-15 early AM. Phase 1 (12 tasks) single-document download path complete `e4ec07d..db0d76d`. Phase 2 v2 (13 of 19 tasks) async project bundle + Google Drive sync in progress on branch `lsp-setup` — commit range `ef5126e..ef6a70b`. New sibling service `dhg-pdf-renderer` scaffolded from scratch — Playwright renderer with `[data-chart-ready]` wait helper, md-only project bundler with atomic zip writer, Google Drive service-account client, Drive sync with `manifest.json` reconciliation, worker loop with `FOR UPDATE SKIP LOCKED` + three-scope dispatch (document/project_bundle/drive_sync). Migrations 009+010 extended `download_jobs` to v2 schema with Drive tracking. Inbox-repair branch merged in `bc9cfd5` carrying registry proxy binary body fix (`b736357` — critical: proxy was text-decoding PDF bodies) and `full_pipeline` orchestrator recipe deletion (`a1f85f0`). medkb v2 design spec parallel-landed `67abc4d` with Phase 1 plan draft at `docs/superpowers/plans/2026-04-15-medkb-phase1.md` (23 tasks, 4302 lines). Branch `lsp-setup` now +40 commits / +14865/-1180 across 55 files vs master, zero pushed — merge-to-master decision pending. Added Phase 7 (items 41-45) to the phase list covering all 5 phases of the inbox-download plan. Backlog #46: medkb v2. Saved current as `docs/archive/TODO_v14.md` per planning-file-versioning rule. Task 2.13 `filesApi.ts` committed in this session as `ef6a70b` — next is Task 2.14 (Files tab Zustand store).)
- v1: Feb 26, 2026 — saved as docs/archive/TODO_v1.md
- v2: Mar 14, 2026 — saved as docs/archive/TODO_v2.md
- v3: Mar 15, 2026 — phased execution order, VS completion
- v4: Apr 6, 2026 — post-audit update, stale items resolved, reprioritized
- v5: Apr 6, 2026 — test fixes complete, 61/61 passing, doc drift CI
- v6: Apr 7, 2026 — saved as docs/archive/TODO_v6.md
- v7: Apr 8, 2026 — saved as docs/archive/TODO_v7.md (Registry Agent, citation checker refactor, 17 graphs deployed to cloud)
- v8: Apr 13, 2026 — saved as docs/archive/TODO_v8.md (Agents Library, Intake Prefill Agent, Edit/Archive workflow, dashboards redesign, orchestrator passthrough, inference platform API, 112 tests)
- v9: Apr 13, 2026 — saved as docs/archive/TODO_v9.md (Dev Changelog Build 1 task DAG wired via TaskCreate, 13 subtasks IDs 1-13, Build 5 dependency on #21 Gate B made explicit; Phase 1 Gate A PASSED — CF_ACCESS secrets + Prometheus remote-write flag root-caused and fixed, plan v2 diagnostic ladder committed `daf230a`, dashboards panel D1 live)
- v10: Apr 13, 2026 — saved as docs/archive/TODO_v10.md (intake-edit-after-submit feature complete: backend PUT loosened with intake_version bump, 4 real-DB integration tests replacing mocks, frontend gates loosened, stale-intake amber banner; NSCLC fingerprint test ef4e5b53 verified topic-correct end-to-end; auto-sync silent guard skip observability bug logged as #51; /outputs document_text passthrough bug logged as #52; Playwright journey verification queued as #53)
- v11: Apr 13, 2026 — saved as docs/archive/TODO_v11.md (#51 auto-sync observability + silent logger root-caused and fixed — switched module logger to `uvicorn.error` to surface 12 previously-invisible log calls; #52 /outputs document_text passthrough fixed in 3 places — Pydantic schema, both endpoint constructors, frontend interface — with 3 new real-DB tests, verified live; #53 Playwright E2E intake journey walked end-to-end through real UI, project 66c96439 created via Save & Start with prefill returning 20 PubMed publications, status flipped intake→processing; serializer-drift heuristic saved to memory as `feedback_serializer_drift.md`; tests now 119/119 across 8 files)
- v12: Apr 13, 2026 — saved as docs/archive/TODO_v12.md (code review of #52 caught that wire-fix alone was operationally a no-op — `step-content.tsx` extracts prose via per-agent `DOCUMENT_KEYS` map and never read `output.document_text`. Frontend wiring landed: `extractDocument()` now prefers `output.document_text` with `>10` char guard. Commit `1ec1cb3` pushed to origin/master alongside `0cecce0` intake-edit feature and `d601018` observability fix. Phase 4 down to a single open item — #20 Human review feedback loop.)
- v14: Apr 14, 2026 — current (LSP setup Task 6 live verification on branch `lsp-setup`, 5 probes passed end-to-end, pyright library-symbol quirk documented in spec + CLAUDE.md + memory, PATH workaround via `~/.local/bin` symlinks, durable PATH fix deferred. Spec and plan both snapshotted as `_v1.md` before edit per planning-file-versioning rule. Commit `c626a62 docs(lsp-setup): reconcile Task 6 to pyright's actual LSP behavior`. Branch left unmerged — carries unrelated inbox-download feature work; merge gated on that feature's readiness, not LSP. CLAUDE.md gained a pyrightconfig.json key-file row, a Type checking / LSP tech-stack row, and a Claude Code LSP tool usage notes block under Build & Run Commands.)
- v13: Apr 14, 2026 — (Dev Changelog Builds 1-4 functionally landed in 3 commits: `51503b3` backend API + migration 007 + 16-row seed + 6 tests, `ef7ae2a` frontend view with first-in-product TanStack deployment + filter rail + detail slide-over + editorial form + Zustand store, `29ad09e` design spec. `@tanstack/react-table@8.21.3` added. Dev Changelog work surfaced during status-update review after a session disconnect — full code review confirmed functionally working but short of declared spec in 5 specific ways (editorial masthead, real-DB tests, Playwright e2e spec, timeline/kanban/saved-views, prefix normalization) — all logged as gaps under #17a. Also this session: `31f259d` chore gitignore adds `.claude/` `.superpowers/` `.playwright-mcp/` and root `*.png` after 20 items of untracked noise had been accumulating; `dba1f11` fix dashboards mission-control scroll on short viewports. Five commits local, nothing pushed — waiting on explicit approval for the push.)
