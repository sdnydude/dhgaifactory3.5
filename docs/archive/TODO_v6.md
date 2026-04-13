# DHG AI Factory — Master Task List
**Last Updated:** Apr 7, 2026

## System Status
- **Containers:** 37 running, all healthy (0 unhealthy)
- **LangGraph Server:** Cloud production at `dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app` (15 graphs)
- **VS Engine:** Running, healthy, Prometheus metrics active
- **Frontend:** Next.js on :3000 (shadcn/ui + assistant-ui + CopilotKit)
- **GPU:** RTX 5080 (16GB VRAM, 26% used by Ollama)
- **Disk:** Root 12% (1.9TB), Data 4% (3.6TB)
- **Observability:** Full stack operational — Prometheus (6/6 targets UP), Grafana, Loki+Promtail, Tempo+OTel, Alertmanager, cAdvisor, Node/Postgres exporters
- **CI/CD:** GitHub Actions (lint, test, compose validation, doc drift checker)
- **Tests:** 105 tests across 8 files (105 passing)

---

## Phase 1: Immediate (Fix / Unblock)

1. [x] ~~Fix gh auth and push commits~~ — DONE (7 commits pushed)
2. [x] ~~Fix 16 DB-dependent test failures~~ — DONE (61/61 passing, conftest.py rewritten with `app.dependency_overrides`)
3. [x] ~~Investigate Dify worker instability~~ — DONE (decommissioned Dify + RAGFlow, zero usage)

## Phase 2: VS Wave 1 Verification

4. [x] ~~End-to-end VS pipeline test~~ — DONE (generate + select + metrics all verified)
5. [x] ~~Confirm VS metrics visible in Grafana VS dashboard~~ — DONE (Prometheus scraping, dashboard JSON provisioned)

## Phase 3: Frontend Features

6. [ ] Generative UI — domain panels (leads, projects, CMS) in chat
7. [ ] MCP integration — agents to external tools
8. [ ] Memory — persistent context via LangGraph checkpointing
9. [ ] LLManager — approval workflow with reflection for CME review
10. [ ] React Flow — visual LangGraph workflow editor
11. [ ] Tremor — token usage and agent performance dashboards
12. [ ] Refine — admin console with FastAPI data providers

## Phase 4: CME Pipeline End-to-End

13. [ ] End-to-end CME pipeline test (intake -> agents -> review -> output)
14. [ ] Human review implementation wired to frontend inbox with full feedback loop

## Phase 5: Hardening

15. [ ] Agent-level integration tests (beyond registry API tests)
16. [ ] Performance benchmarks for full pipeline
17. [ ] Verify Tempo trace ingestion from LangGraph agents end-to-end
18. [ ] CD — automated deploy on merge to master

## Phase 6: Security & Infrastructure

19. [x] ~~Build DHG Security Agent (Cloudflare Access, GraphQL analytics)~~ — DONE (RBAC models, JWT auth, audit logging, admin endpoints, 44 tests)
20. [x] ~~Decommission legacy Docker agents (ports 8002-8008)~~ — DONE (stopped, restart: "no")
21. [x] ~~Decommission LibreChat stack~~ — DONE (5 containers, 1 volume, 2.4 GB removed)
22. [x] ~~Docker disk cleanup~~ — DONE (34.6 GB reclaimed via prune)

## Backlog

23. [ ] VS Wave 2: Team Roster UI
24. [ ] Video Content Pipeline (Vimeo, YouTube, AI clip generation)
25. [ ] Code Interpreter
26. [ ] Claude Files API
27. [ ] XMP Metadata (Visuals Agent)
28. [x] ~~RAGFlow configuration~~ — DECOMMISSIONED (zero usage, removed)
29. [ ] `/ship` command implementation and testing

---

## Completed (April 2026)

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
- v6: Apr 7, 2026 — current (security/RBAC complete, 105/105 passing)
