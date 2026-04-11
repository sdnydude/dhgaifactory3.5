# DHG AI Factory v3.5

## Identity

You are the sole AI development partner for Digital Harmony Group's AI Factory. This is a multi-agent platform built on LangGraph that generates pharmaceutical-grade CME (Continuing Medical Education) grant documentation. The platform is also a general-purpose modular enterprise AI system — CME is approximately 10% of DHG's revenue. CME compliance mode activates only when Stephen explicitly toggles it.

**Owner:** Stephen Webber — CEO/Founder, 35+ years in business development, medical education, and broadcast production. Producer/Director of broadcast livestreams, architect of efficient livestream and recording studios (NDI, Dante, TCP/IP VLANs). Bills at $600/hour. Expects Fortune 500 execution quality.

**Server:** g700data1 (10.0.0.251), Ubuntu 24.04, Docker 29.1.5, NVIDIA RTX 5080 (16GB VRAM), 64GB RAM, 1.9TB root disk (12% used), 3.6TB data disk at /mnt/4tb (4% used). Docker Root Dir: /mnt/4tb/docker.

**Repo:** https://github.com/sdnydude/dhgaifactory3.5.git — Branch: master (current).

---

## Architecture (Current State — April 2026)

There are TWO agent systems. The CURRENT system is LangGraph. The LEGACY system is Docker-based FastAPI agents that are being decommissioned.

### LangGraph Agent System (CURRENT — Production)

17 graphs registered in `langgraph_workflows/dhg-agents-cloud/langgraph.json`. Production runs on LangGraph Cloud; local dev instance on port 2026:

**13 Individual Agent Graphs:**

| Agent | File | Lines | Key Pattern |
|-------|------|-------|-------------|
| Needs Assessment | needs_assessment_agent.py | 1110 | 10-node sequential, cold open framework, 3100+ word validation |
| Research | research_agent.py | 1160 | Literature/PubMed queries, 30+ sources |
| Clinical Practice | clinical_practice_agent.py | 864 | Barrier identification, standard-of-care analysis |
| Gap Analysis | gap_analysis_agent.py | 775 | 5+ evidence-based gaps, quantification |
| Learning Objectives | learning_objectives_agent.py | 894 | Moore's Expanded Framework mapping |
| Curriculum Design | curriculum_design_agent.py | 1045 | Educational design + innovation section |
| Research Protocol | research_protocol_agent.py | 977 | IRB-ready outcomes protocol |
| Marketing Plan | marketing_plan_agent.py | 867 | Audience strategy + channel budget |
| Grant Writer | grant_writer_agent.py | 926 | Full package assembly |
| Prose Quality | prose_quality_agent.py | 672 | De-AI-ification scoring, banned pattern detection |
| Compliance Review | compliance_review_agent.py | 436 | ACCME verification |
| Citation Checker | citation_checker_agent.py | ~450 | PubMed verification, outputs registry_request for gateway |
| Registry | registry_agent.py | ~290 | Gateway for all agent writes to Registry API, idempotency, dead letter queue |

All agents have dual tracing: LangSmith (@traceable) + OpenTelemetry (@traced_node) decorators on every graph node (85 total across 9 content agents + orchestrator).

**4 Orchestrator Composition Graphs (in orchestrator.py, 1889 lines):**

| Recipe | Export | Pattern |
|--------|--------|---------|
| needs_package | needs_graph | Research + Clinical parallel → Gap → LO → Needs → Prose QA Pass 1 → Human Review |
| curriculum_package | curriculum_graph | Needs Package + Curriculum + Protocol + Marketing parallel → Human Review |
| grant_package | grant_graph | Full 11 agents, Prose QA 2 passes, Compliance gate, Human Review |
| full_pipeline | full_graph | Same as grant but with 3-way human review routing (approved/revision/rejected) |

**Architecture patterns across all agents:** Each agent has its own TypedDict state, ChatAnthropic (Claude Sonnet) with @traceable LangSmith decorators on every node, asyncio.wait_for with 5-minute timeout, standardized error records. Parallel execution via asyncio.gather with return_exceptions=True. Quality gates use conditional edges with retry loops (up to 3 iterations before human escalation).

### Legacy Agent System (DECOMMISSIONED)

9 Docker-based FastAPI agents (ports 2024, 8002-8008, 3005) — all stopped with `restart: "no"`, will not restart on reboot. Source code retained in `agents/` for reference. Do not build new features on these.

### Infrastructure Services

| Service | Port | Purpose |
|---------|------|---------|
| dhg-registry-db | 5432 | PostgreSQL 15 + pgvector (64 tables) |
| dhg-registry-api | 8011 | FastAPI data registry, Prometheus /metrics, CME endpoints |
| dhg-frontend | 3000 | Next.js production frontend (shadcn/ui + assistant-ui + CopilotKit). Role-aware sidebar (Work/Observe/Manage sections). |
| dhg-vs-engine | 8013 | Verbalized Sampling engine, Prometheus metrics |
| dhg-ollama | 11434 | Ollama (llama3.1:8b, nomic-embed-text, qwen3:14b) |
| dhg-session-logger | 8009 | Session tracking with Ollama embeddings |
| dhg-logo-maker | 8012 | Logo generation |
| dhg-audio-agent | 8101 | Audio processing agent |

### Observability Stack

| Service | Port | Status |
|---------|------|--------|
| dhg-prometheus | 9090 | 6 scrape targets, all UP |
| dhg-grafana | 3001 | Dashboards: core golden signals, Docker overview |
| dhg-loki | 3100 | Log aggregation via Promtail |
| dhg-tempo | 3200 | Distributed tracing (OTel gRPC :4317, HTTP :4318) |
| dhg-promtail | — | Docker container log shipping to Loki |
| dhg-alertmanager | 9093 | Alert routing (webhook to registry-api) |
| dhg-cadvisor | 8080 | Container metrics (v0.51.0) |
| dhg-node-exporter | 9100 | Host metrics |
| dhg-postgres-exporter | 9187 | Registry-db metrics |

### Auth & RBAC (Added April 2026)

4-layer defense-in-depth: Cloudflare Access WAF → Next.js middleware (JWT cookie check, route guard) → FastAPI middleware (JWT signature validation, permission enforcement) → PostgreSQL RBAC tables.

- Cloudflare JWT from `Cf-Access-Jwt-Assertion` header, validated against JWKS
- 5 roles seeded: admin, operations, finance, editor, viewer
- 5 DB tables: security_users, security_roles, security_user_roles, security_project_access, security_audit_log
- Backend: registry/auth.py (validation + dependencies), registry/security_endpoints.py (API at /api/v1/security)
- Frontend: middleware.ts (route guard), stores/session-store.ts (Zustand), hooks/use-session.ts, lib/permissions.ts
- Dev mode: SECURITY_DEV_MODE=true bypasses all auth (backend + frontend)
- Registry proxy: frontend/src/app/api/registry/[...path]/route.ts forwards Cloudflare JWT to registry API

### LLManager Review Inbox (Added April 2026)

Human-in-the-loop review workflow at /inbox. Master-detail layout: left sidebar lists pending LangGraph interrupted threads, right panel shows document with AI quality assessment.

- Components: frontend/src/components/review/ (inbox-master-detail, review-panel, reflection-panel, metrics-bar, decision-bar, document-viewer, vs-alternatives)
- Store: frontend/src/stores/review-store.ts (Zustand)
- API: frontend/src/lib/inboxApi.ts (queries LangGraph SDK for interrupted threads, resumes with decisions)
- AI Reflection: quality signals (prose score, banned patterns, ACCME compliance) + approve/revise recommendation
- Auto-refreshes every 30s

### Additional Stacks (running independently)

| Stack | Main Port | Containers | Status |
|-------|-----------|------------|--------|
| Transcribe Pipeline | 8200 | 12 containers, GPU-accelerated | Running |
| Infisical | 8089 | 5 containers | Running |

### Docker Networks

| Network | Members |
|---------|---------|
| dhgaifactory35_dhg-network | Main DHG stack (registry, agents, frontend, observability) |
| dhg-agents-cloud_default | LangGraph dev server (port 2026) |
| dhg-transcribe_default | Transcribe pipeline |

**Note:** The LangGraph dev server on port 2026 is on its own network. Production LangGraph runs in LangGraph Cloud (see MEMORY.md for cloud URL). The dev instance uses `host.docker.internal` for cross-container communication.

---

## Known Issues (Updated April 2026)

### Open

**O1: Legacy Orchestrator Port Conflict** — docker-compose.yml maps orchestrator to port 2024. docker-compose.override.yml maps registry-api to 8011. The legacy orchestrator on 2024 is orphaned — nothing connects to it.

**O2: gh Auth Expired** — GitHub CLI token is invalid. 3 commits unpushed. Run `gh auth login -h github.com` to restore.

### Resolved

17 issues resolved Feb–April 2026. Full history: `docs/resolved-issues.md`.

---

## Frontend Migration Strategy (Decided Feb 18, 2026)

The frontend stack (decided Feb 2026, implemented March–April 2026):

**Approach A — Modular Composition (APPROVED):**
- shadcn/ui — unified design system
- assistant-ui — composable chat interface with LangGraph starter template
- CopilotKit — AG-UI protocol for agent-to-frontend communication, Generative UI
- Refine — headless admin console with FastAPI data providers
- React Flow — visual LangGraph workflow editor
- Tremor — monitoring dashboards (token usage, agent performance)
- Agent Inbox patterns — human-in-the-loop CME review workflows

**Connected to LangGraph via:** langgraph-sdk URL pointing to either LangSmith Cloud (production) or localhost:2026 (development). The AG-UI @ag-ui/langgraph package provides the LangGraphHttpAgent bridge.

---

## Key File Locations

| Purpose | Path |
|---------|------|
| Main compose | docker-compose.yml |
| Override compose | docker-compose.override.yml |
| LangGraph compose | langgraph_workflows/dhg-agents-cloud/docker-compose.yml |
| LangGraph config | langgraph_workflows/dhg-agents-cloud/langgraph.json |
| LangGraph agents | langgraph_workflows/dhg-agents-cloud/src/*.py |
| OTel tracing | langgraph_workflows/dhg-agents-cloud/src/tracing.py |
| Orchestrator | langgraph_workflows/dhg-agents-cloud/src/orchestrator.py |
| Registry API | registry/api.py |
| CME endpoints | registry/cme_endpoints.py |
| Agent endpoints | registry/agent_endpoints.py |
| DB models | registry/models.py |
| Schemas | registry/schemas.py |
| Registry tests | registry/test_*.py (5 test files, 105 tests) |
| Frontend | frontend/src/ |
| VS Engine | services/vs-engine/ |
| Observability configs | observability/ (prometheus, grafana, loki, tempo, promtail, alertmanager) |
| Agent architecture docs | DHG-CME-12-Agent-Docs/ |
| Current priorities | docs/TODO.md |
| CI/CD | .github/workflows/ci.yml |
| Auth module | registry/auth.py |
| Security API | registry/security_endpoints.py |
| Security schemas | registry/security_schemas.py |
| RBAC migration | registry/alembic/versions/004_add_security_rbac.py |
| Frontend auth | frontend/src/middleware.ts, frontend/src/lib/permissions.ts |
| Review components | frontend/src/components/review/ |
| Inbox API | frontend/src/lib/inboxApi.ts |
| Environment vars | .env (secrets — never expose) |

---

## Build & Run Commands

```bash
# Full system
docker compose up -d
docker compose ps
docker compose logs -f <service>

# LangGraph server (separate compose)
cd langgraph_workflows/dhg-agents-cloud
docker compose up -d

# Registry DB access
docker exec -it dhg-registry-db psql -U dhg -d dhg_registry

# Health checks
curl -s http://localhost:2026/ok          # LangGraph server
curl -s http://localhost:8011/healthz     # Registry API
curl -s http://localhost:9090/-/healthy   # Prometheus

# Single service rebuild
docker compose build --no-cache <service>
docker compose up -d <service>
```

---

## Production Rules

1. **Version control is the sole source of truth.** Sequential phases only. No overlapping or speculative work.
2. **No placeholders, TODOs, or provisional logic.** Every file must work on first deploy.
3. **One fix per hypothesis when debugging.** If it fails, form a new hypothesis.
4. **View files before editing.** State what you're changing and why.
5. **Run verification after any change.** Show proof it works.
6. **No silent refactors.** No behavior changes without operational rationale.
7. **Written change request required.** Map to phase + acceptance criteria.
8. **Make assumptions explicit.** Do not invent requirements.
9. **Definition of done:** Works in real conditions, no data loss on restart/refresh, state is unambiguous, commit history reflects intent.
10. **Overhead IS the quality.** Standards, processes, rigor, and thorough planning are the product clients pay for. Never optimize for speed or convenience; always optimize for best outcome. Quality and accuracy are first priority. Fortune 500 execution.
11. **Planning and building are separate phases.** Do not write files, run commands, or generate code until the design/plan is fully worked through AND Stephen explicitly approves moving to implementation. Jumping to code before planning is complete produces half-finished work, abandoned sessions, and unnecessary refactors. When in doubt, keep planning.

## Principles

Clarity > cleverness. Predictability > novelty. Visibility > completeness. Explicit state > implicit behavior. Recovery > optimism. Determinism + auditability.

## DHG Brand

| Token | Value |
|-------|-------|
| Graphite | #32374A |
| Purple | #663399 |
| Orange | #F77E2D |
| Neutrals | #FFFFFF through #2E3243 |
| Font | Inter |
| Layout rule | 60-30-10 |
| Tagline | "AI Agents In Tune With You" |

Light mode: Background #FAF9F7, Surface #FFFFFF, Text #32374A, Accent #663399.
Dark mode: Background #1A1D24, Surface #27272A, Text #FAF9F7, Accent #A78BFA.

Use semantic tokens, not raw hex values, in code.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | LangGraph (StateGraph, Command pattern) |
| Observability | LangSmith (@traceable), OTel/Tempo (@traced_node), Prometheus, Grafana, Loki, Alertmanager |
| Checkpointing | PostgresSaver (production persistence) |
| Agent LLM | Claude Sonnet via ChatAnthropic |
| Local LLM | Ollama (qwen3:14b, llama3.1:8b) |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic 2.5 |
| Database | PostgreSQL 15 + pgvector |
| Container runtime | Docker Engine 29.1.5 |
| Frontend (target) | Next.js, shadcn/ui, assistant-ui, CopilotKit, Refine, React Flow |
| Secrets | Infisical (when stable), .env (current) |
