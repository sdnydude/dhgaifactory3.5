# DHG AI Factory — Master Task List
**Last Updated:** Apr 13, 2026 (v12)

## System Status
- **Containers:** 37 running, all healthy (0 unhealthy)
- **LangGraph Server:** Cloud production at `dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app` (17 graphs)
- **VS Engine:** Running, healthy, Prometheus metrics active
- **Frontend:** Next.js on :3000 (shadcn/ui + assistant-ui + CopilotKit)
- **GPU:** RTX 5080 (16GB VRAM, 26% used by Ollama)
- **Disk:** Root 12% (1.9TB), Data 4% (3.6TB)
- **Observability:** Full stack operational — Prometheus (6/6 targets UP), Grafana, Loki+Promtail, Tempo+OTel, Alertmanager, cAdvisor, Node/Postgres exporters
- **CI/CD:** GitHub Actions (lint, test, compose validation, doc drift checker)
- **Tests:** 119 tests across 8 files (119 passing) — +3 real-DB integration tests for /outputs document_text passthrough

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
17a. [~] Dev Changelog (Admin/Reporting section) — editable agent-assisted development log at `/admin/reporting/dev-changelog`. Schema + 16-entry seed DONE (migration 007, verified). Design spec DONE (`docs/superpowers/specs/2026-04-13-dev-changelog-design.md`). First TanStack deployment in the product.
    - **Build 1 IN PROGRESS** — 13 subtasks tracked via `TaskList` (IDs 1-13), dependency DAG wired. Execution waves:
      - Wave 1 (parallel, no blockers): #1 install TanStack + shadcn table, #3 SQLAlchemy model, #7 route permissions, #10 editorial masthead component
      - Wave 2: #2 DataTable wrapper (needs #1), #4 Pydantic schemas (needs #3), #8 page shell (needs #7)
      - Wave 3: #5 backend endpoints (needs #4), #11 table with column defs (needs #2, #4)
      - Wave 4: #6 backend tests (needs #5), #9 API client + Zustand store (needs #5)
      - Wave 5: #12 view container (needs #8, #9, #10, #11)
      - Wave 6: #13 e2e Playwright verify (needs #6, #12)
    - Builds 2-5 queued: (2) detail slide-over + commit links, (3) inline edit + server-side ownership enforcement, (4) filters + saved views + timeline/kanban, (5) 3am nightly agent (BLOCKED on #21 Phase 1 Gate B so traces are visible before unattended runs).

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

## Backlog

31. [ ] VS Wave 2: Team Roster UI
32. [ ] Video Content Pipeline (Vimeo, YouTube, AI clip generation)
33. [ ] Code Interpreter
34. [ ] Claude Files API
35. [ ] XMP Metadata (Visuals Agent)
36. [x] ~~RAGFlow configuration~~ — DECOMMISSIONED (zero usage, removed)
37. [ ] `/ship` command implementation and testing

---

## Completed (April 2026)

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
- v12: Apr 13, 2026 — current (code review of #52 caught that wire-fix alone was operationally a no-op — `step-content.tsx` extracts prose via per-agent `DOCUMENT_KEYS` map and never read `output.document_text`. Frontend wiring landed: `extractDocument()` now prefers `output.document_text` with `>10` char guard, falls back to existing key map. `tsc --noEmit` clean. Commit `1ec1cb3` pushed to origin/master alongside `0cecce0` intake-edit feature and `d601018` observability fix. Three Phase 4 tickets closed in this session: #19, #51, #52. Phase 4 now down to a single open item — #20 Human review feedback loop. GitHub flagged 21 Dependabot alerts on default branch — standing, not from this push.)
