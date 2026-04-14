# DHG AI Factory — Master Task List
**Last Updated:** Apr 13, 2026

## System Status
- **Containers:** 37 running, all healthy (0 unhealthy)
- **LangGraph Server:** Cloud production at `dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app` (17 graphs)
- **VS Engine:** Running, healthy, Prometheus metrics active
- **Frontend:** Next.js on :3000 (shadcn/ui + assistant-ui + CopilotKit)
- **GPU:** RTX 5080 (16GB VRAM, 26% used by Ollama)
- **Disk:** Root 12% (1.9TB), Data 4% (3.6TB)
- **Observability:** Full stack operational — Prometheus (6/6 targets UP), Grafana, Loki+Promtail, Tempo+OTel, Alertmanager, cAdvisor, Node/Postgres exporters
- **CI/CD:** GitHub Actions (lint, test, compose validation, doc drift checker)
- **Tests:** 112 tests across 8 files (112 passing) — +7 from archive/update coverage

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
17a. [~] Dev Changelog (Admin/Reporting section) — editable agent-assisted development log at `/admin/reporting/dev-changelog`. Schema + 16-entry seed DONE (migration 007, verified). Design spec DONE (`docs/superpowers/specs/2026-04-13-dev-changelog-design.md`). Builds 1-5: (1) TanStack DataTable wrapper + backend endpoints + read-only view, (2) detail slide-over + commit links, (3) inline edit + ownership enforcement, (4) filters + timeline + kanban views, (5) 3am agent for nightly upserts. First TanStack deployment in the product.

## Phase 4: CME Pipeline End-to-End

18. [x] ~~Orchestrator intake data passthrough fix~~ — DONE (Apr 11, `flatten_intake` aliases + 5 wrapper expansions; disease_state now reaches all agents)
19. [ ] End-to-end CME pipeline test (intake -> agents -> review -> output)
20. [ ] Human review implementation wired to frontend inbox with full feedback loop

## Phase 5: Hardening

21. [~] LangGraph Telemetry Pipeline Repair (Phase 1) — Tempo→Prometheus span-metrics via `otel.digitalharmonyai.com` Cloudflare tunnel, new `dhg-langgraph-exporter` service, 6 alert rules. Plan dated 2026-04-12.
    - [x] Tasks 1–5: Cloudflare tunnel route, `tracing.py` swapped to OTLP/HTTP, CF Access headers passthrough, `pyproject.toml` deps, LangSmith shared TracerProvider fix (9 commits `c7b46e6..f236196`)
    - [ ] Task 6: Phase 1 Gate A — explicit end-to-end span flow verification
    - [ ] Tasks 7–13: `dhg-langgraph-exporter` service (TDD scaffold, impl, Dockerfile), compose wiring, Prometheus scrape job, 6 alert rules, Phase 1 Gate B
22. [ ] Agent-level integration tests (beyond registry API tests)
23. [ ] Performance benchmarks for full pipeline
24. [ ] Verify Tempo trace ingestion from LangGraph agents end-to-end
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
- v8: Apr 13, 2026 — current (Agents Library, Intake Prefill Agent, Edit/Archive workflow, dashboards redesign, orchestrator passthrough, inference platform API, 112 tests)
