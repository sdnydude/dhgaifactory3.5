# DHG AI Factory - Master To-Do List
**Last Updated:** Mar 14, 2026

## System Status
- **DHG Containers:** 39 running (18 healthy, others no-healthcheck configured)
- **LangGraph Server:** Cloud production at `dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app` (15 graphs)
- **GPU:** RTX 5080 (0% utilization, 4.5GB/16GB VRAM — transcribe pipeline idle)
- **Disk:** 12% used (197GB / 1.9TB)
- **Frontend:** Next.js on :3002 (shadcn/ui + assistant-ui + CopilotKit)
- **Ollama Models:** llama3.1:8b, nomic-embed-text, qwen3:14b
- **Observability:** Prometheus :9090, Grafana :3001, Loki :3100, Tempo :3200, Alertmanager :9093, Promtail, cAdvisor :8080, Node Exporter, Postgres Exporter :9187

### Container Groups
| Stack | Count | Status |
|---|---|---|
| DHG AI Factory | 24 | 18 healthy, 6 no-healthcheck |
| Transcribe Pipeline | 10 | All running |
| Infisical | 5 | All stable (2 healthy, 3 no-healthcheck) |
| RAGFlow | 1 | Running (:8585) |
| pgAdmin | 1 | Running (:5050) |
| Dify | 0 | **Removed** (port 3000 freed for Next.js frontend) |
| LibreChat | 0 | **Removed** (deprecated) |

---

## P0: Blockers

None.

---

## P1: Active Sprint

### `/ship` Command — Custom Shipping Workflow
- [x] Researched all superpowers skills (brainstorming, writing-plans, executing-plans, etc.)
- [x] Identified 9 custom additions not in any existing skill
- [x] Designed 7-phase workflow (Brainstorm → Explore → Plan → Build → Verify → Review → Ship)
- [x] Created task_plan.md with full phase design
- [ ] Write the `/ship` command file (`.claude/commands/ship.md`)
- [ ] Write explorer agent prompt template
- [ ] Write reviewer agent prompt template
- [ ] Test with a real feature

### Monitoring Dashboard — Frontend
- [x] Session-logger stats endpoints (overview, daily, concepts)
- [x] Session-logger Prometheus instrumentation
- [x] Session-logger connection pooling (ThreadedConnectionPool)
- [x] 14 tests for stats + metrics endpoints
- [x] Frontend monitoring API client and Zustand store
- [x] Frontend stats cards, tab navigation, polling
- [x] API proxy routes for session-logger and Alertmanager
- [x] Review findings addressed
- [ ] Session-logger data visualization — graphs, tables, and copy for the 42 ingested sessions (462 chunks, 642 concepts, 3604 edges) on the monitoring page
- [ ] Additional dashboard tabs (logs, traces, alerts — wired to Loki/Tempo/Alertmanager)
- [ ] Grafana dashboard curation

### Observability Stack — Remaining Gaps
- [x] Prometheus + Docker service discovery
- [x] Grafana dashboards provisioned (Prometheus, Loki, Tempo datasources)
- [x] Promtail deployed (Docker log scraping → Loki)
- [x] Tempo deployed (OTel trace collection)
- [x] Alertmanager deployed with webhook to registry-api
- [x] cAdvisor, Node Exporter, Postgres Exporter
- [ ] Expand Grafana dashboards (LangGraph agent performance, session-logger metrics)
- [ ] Alert rules for critical services (container down, high error rate, disk usage)
- [ ] Verify Tempo trace ingestion from LangGraph agents end-to-end

---

## P2: Next Up

### Frontend — Feature Completion
- [x] Chat page (assistant-ui + CopilotKit AG-UI bridge)
- [x] Agent Inbox / review UI components
- [x] Studio route
- [x] Search page + search API client
- [x] Monitoring page (stats cards, tab navigation)
- [ ] Generative UI — domain panels (leads, projects, CMS) rendered inline in chat
- [ ] MCP Integration — connect agents to external tools
- [ ] Memory — persistent context via LangGraph checkpointing
- [ ] LLManager — approval workflow with reflection for CME review

### CME Workflow
- [x] PostgreSQL database schema (003_add_cme_projects.sql)
- [x] Compliance-ready CME database schema with RAG embeddings
- [x] CME endpoints integrated with database
- [x] JSONB datetime serialization fix
- [x] Search & RAG endpoints for CME knowledge base
- [x] CME intake template (CSV)
- [ ] Human Review Requirements implementation (interrupt()-based, wired to frontend inbox)
- [ ] End-to-end CME pipeline test (intake → agents → review → output)

### LangGraph Agents — Hardening
- [x] Topic extraction, PubMed citations, and references added to all 9 content agents
- [x] PubMed keyword extraction, PMID dedup, shared build_references_section
- [x] interrupt()-based human review in needs_package recipe
- [x] interrupt() replicated to all 4 orchestrator recipes
- [x] Graceful degradation when OTel not installed
- [x] importlib file-based loading for Cloud runtime
- [ ] Agent-level unit tests (currently only session-logger has tests)
- [ ] Performance benchmarks for full pipeline run

---

## P3: Infrastructure & Security

### Security
- [ ] Build DHG Security Agent (Cloudflare Access management, GraphQL analytics)
- [ ] Healthchecks on remaining containers (ollama, promtail, node-exporter, etc.)

### CI/CD
- [x] GitHub Actions CI pipeline created
- [ ] Expand CI — test suite, lint, type-check, Docker build validation
- [ ] CD — automated deployment on merge to master

### RAGFlow
- [x] Running at ragflow.digitalharmonyai.com
- [x] Google OAuth configured
- [ ] Configure LLM connection
- [ ] Create first knowledge base

---

## P4: Backlog

- [ ] Video Content Pipeline (Vimeo API, YouTube API, ingestion, AI clip generation)
- [ ] Code Interpreter
- [ ] Claude Files API
- [ ] XMP Metadata (Visuals Agent)

---

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

- [x] Antigravity-to-Claude Code migration **COMPLETE** (10/10 criteria met)
- [x] `.agent/` directory removed (all value extracted)
- [x] Frontend rebuilt on Next.js + shadcn/ui + assistant-ui + CopilotKit
- [x] Cloud-rewire: server-side proxy, polling sync, full frontend rebuild
- [x] Search page + search API client + registry search/RAG endpoints
- [x] Compliance-ready CME database schema with RAG embeddings
- [x] Studio route, real alerts, webhook endpoint
- [x] Review UI components wired into Agent Inbox
- [x] interrupt()-based human review in all 4 orchestrator recipes
- [x] Topic extraction, PubMed citations, references added to all 9 content agents
- [x] Fix frontend: pipeline failure feedback, agent document JSONB extraction
- [x] Graceful OTel degradation, importlib Cloud runtime fix

## Completed (Feb 27 – Mar 2, 2026)

- [x] Resolved C1 port conflict (orchestrator vs registry-api on 8011)
- [x] Resolved C3 LangGraph network isolation + wrong registry URL
- [x] Resolved C5 hardcoded IPs in web-ui (replaced with Vite env vars)
- [x] Resolved C6 stale files at project root
- [x] Security fix: python-multipart 0.0.6 → 0.0.22 (CVE arbitrary file write)
- [x] Prometheus Docker service discovery
- [x] GitHub Actions CI pipeline
- [x] Docs consolidation
- [x] Promtail log shipping to Loki
- [x] Tempo tracing deployment + API tests
- [x] Registry-db healthcheck fix, restart policy, interval increase
- [x] Infisical orphan container removed (was crash-looping Exit 255)
- [x] Dify moved off port 3000, set to restart=no, later fully removed
- [x] LibreChat deprecated and removed
- [x] Cloudflare tunnel updated (app.digitalharmonyai.com → localhost:3000)
- [x] LangGraph Cloud deployment configured (local :2026 = dev only)

## Completed (Feb 18–26, 2026)

- [x] Full agent-check: 54 containers inventoried across all stacks
- [x] LangGraph frontend strategy decided (LibreChat → Next.js + shadcn/ui + assistant-ui + CopilotKit)
- [x] 17-option LangGraph frontend comparative table researched
- [x] Observability: node-exporter, cAdvisor, postgres-exporter deployed
- [x] cAdvisor v0.49.1 → v0.51.0 for Docker API 1.44+ compat
- [x] Loki datasource for Grafana, dashboard mount fix
- [x] Fixed registry-db down (exited 5 days) — restarted, registry-api recovered
- [x] Migrated to Claude Code — restored CLAUDE.md, added rules and 10 ported skills

## Completed (Feb 3–17, 2026)

- [x] Audio agent added to LangGraph
- [x] Recipe-Based Orchestrator implemented
- [x] Marketing Plan agent created
- [x] Docker healthchecks for Grafana, Loki, Prometheus, registry-api
- [x] Registry-API Docker image rebuilt (fixed missing Alembic migration 003)
- [x] LangGraph proxy and docker override
- [x] Research protocol + curriculum design: disease_state/therapeutic_area fields

## Completed (Jan 18 – Feb 2, 2026)

- [x] CME intake form PostgreSQL integration
- [x] CME JSONB datetime serialization fix
- [x] Planning-with-files skill installed
- [x] Infisical workflow DB role fix
- [x] CME intake form improvements
- [x] Antigravity session sync scripts and workflow
- [x] Antigravity deduplication fixed
- [x] Antigravity export HTTPS/cascadeId fixes
- [x] RAGFlow OAuth configured, Redis connected
- [x] Observability implementation plan created
- [x] Tavily Web Search configured
- [x] LibreChat Google OAuth
- [x] qwen2.5:14b → qwen3:14b as default Ollama model
- [x] Infisical CLI working
- [x] All DHG agents configured in LibreChat
- [x] pgAdmin running on :5050
- [x] 34 Antigravity sessions ingested

---

## Version History
- v1: Feb 26, 2026 — saved as TODO_v1.md
- v2: Mar 14, 2026 — current (full reconciliation with git history and running state)
