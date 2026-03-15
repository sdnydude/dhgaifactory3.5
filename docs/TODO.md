# DHG AI Factory — Master Task List
**Last Updated:** Mar 15, 2026

## System Status
- **Containers:** 63 running (1 unhealthy: dhg-frontend)
- **LangGraph Server:** Cloud production at `dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app` (15 graphs)
- **VS Engine:** Running, healthy, Prometheus metrics active
- **Frontend:** Next.js on :3000 (shadcn/ui + assistant-ui + CopilotKit)
- **GPU:** RTX 5080 (transcribe pipeline idle)
- **Disk:** ~12% used (1.9TB)
- **Observability:** Prometheus :9090, Grafana :3001, Loki :3100, Tempo :3200, Alertmanager :9093, Promtail, cAdvisor :8080, Node Exporter, Postgres Exporter :9187

---

## Phase 0: Close Out VS Branch (do first)

1. [ ] Commit 4 uncommitted changes on `feature/vs-agent-integration` (mem_limit, alert fix, alerts-panel, ship-state)
2. [ ] Merge `feature/vs-agent-integration` → `master`

## Phase 1: Fix Broken Things

3. [ ] Fix `dhg-frontend` unhealthy healthcheck (wget not available in container)
4. [ ] Commit alert rule fix (ContainerHighMemory divide-by-zero guard)

## Phase 2: VS Wave 1 Verification

5. [ ] End-to-end VS pipeline test (agent → VS engine → frontend inbox)
6. [ ] Confirm VS metrics visible in Grafana VS dashboard

## Phase 3: `/ship` Command

7. [ ] Write `.claude/commands/ship.md` (7-phase workflow)
8. [ ] Write explorer agent prompt `.claude/commands/ship-agents/explore.md`
9. [ ] Write reviewer agent prompt `.claude/commands/ship-agents/review.md`
10. [ ] Test `/ship` on a real feature

## Phase 4: Monitoring Dashboard

11. [ ] Session-logger data visualization (graphs/tables for 42 sessions, 462 chunks, 642 concepts)
12. [ ] Wire Loki/Tempo/Alertmanager tabs on monitoring page
13. [ ] Expand Grafana dashboards (LangGraph agent performance, session-logger metrics)
14. [ ] Alert rules for critical services (container down, high error rate, disk usage)

## Phase 5: Frontend Features

15. [ ] Generative UI — domain panels (leads, projects, CMS) in chat
16. [ ] MCP integration — agents to external tools
17. [ ] Memory — persistent context via LangGraph checkpointing
18. [ ] LLManager — approval workflow with reflection for CME review

## Phase 6: CME Pipeline

19. [ ] Human review implementation (interrupt()-based, wired to frontend inbox)
20. [ ] End-to-end CME pipeline test (intake → agents → review → output)

## Phase 7: Hardening

21. [ ] Agent-level unit tests (currently only session-logger has tests)
22. [ ] Performance benchmarks for full pipeline
23. [ ] Verify Tempo trace ingestion from LangGraph agents end-to-end
24. [ ] Healthchecks on remaining containers (ollama, promtail, node-exporter)

## Phase 8: CI/CD & Security

25. [ ] Expand CI (test suite, lint, type-check, Docker build validation)
26. [ ] CD — automated deploy on merge to master
27. [ ] Build DHG Security Agent (Cloudflare Access, GraphQL analytics)

## Phase 9: RAGFlow

28. [ ] Configure LLM connection
29. [ ] Create first knowledge base

## Backlog

30. [ ] VS Wave 2: Team Roster UI
31. [ ] Video Content Pipeline (Vimeo, YouTube, AI clip generation)
32. [ ] Code Interpreter
33. [ ] Claude Files API
34. [ ] XMP Metadata (Visuals Agent)

---

## Completed (Mar 14–15, 2026)

- [x] VS Engine built and deployed (healthy, Prometheus metrics: spread, selection_delta)
- [x] VS integrated into all 8 content agents (36 generation nodes)
- [x] Orchestrator collects VS distributions from all 9 agents
- [x] VS Grafana dashboard deployed
- [x] VS alternatives panel in frontend inbox
- [x] Migrated gap_analysis_agent from vs_distribution to vs_distributions dict

## Completed (Mar 10–14, 2026)

- [x] Session Capture Pipeline fully built (session-logger v2.0.0, Ollama embeddings 768d, summarization, PDF export, knowledge graph)
- [x] Switched all embeddings from OpenAI to Ollama (nomic-embed-text 768d)
- [x] Backfill endpoint added and run (all rows embedded)
- [x] Session-logger stats endpoints, Prometheus metrics, connection pooling, 14 tests
- [x] Monitoring dashboard frontend (stats cards, API proxies, tab navigation, Zustand store)
- [x] `/ship` command 7-phase design completed
- [x] CME intake template created
- [x] Market intelligence design spec documented

## Completed (Mar 3–9, 2026)

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

## Completed (Feb 27 – Mar 2, 2026)

- [x] Resolved C1 port conflict, C3 network isolation, C5 hardcoded IPs, C6 stale files
- [x] Security fix: python-multipart CVE
- [x] Prometheus Docker service discovery, GitHub Actions CI
- [x] Promtail → Loki, Tempo tracing, registry-db fixes
- [x] Infisical orphan removed, Dify removed, LibreChat removed
- [x] Cloudflare tunnel updated, LangGraph Cloud configured

## Completed (Feb 18–26, 2026)

- [x] 54 containers inventoried, LangGraph frontend strategy decided
- [x] Observability exporters deployed, cAdvisor upgraded
- [x] Migrated to Claude Code

## Completed (Feb 3–17, 2026)

- [x] Audio agent, Recipe-Based Orchestrator, Marketing Plan agent
- [x] Docker healthchecks, Registry-API rebuild, LangGraph proxy

## Completed (Jan 18 – Feb 2, 2026)

- [x] CME intake PostgreSQL, RAGFlow OAuth, Infisical CLI
- [x] Antigravity sessions ingested, pgAdmin deployed

---

## Version History
- v1: Feb 26, 2026 — saved as TODO_v1.md
- v2: Mar 14, 2026 — saved as TODO_v2.md
- v3: Mar 15, 2026 — current (phased execution order, VS completion, status corrections)
