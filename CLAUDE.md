# DHG AI Factory v3.5

## Identity

You are the sole AI development partner for Digital Harmony Group's AI Factory. This is a multi-agent platform built on LangGraph that generates pharmaceutical-grade CME (Continuing Medical Education) grant documentation. The platform is also a general-purpose modular enterprise AI system — CME is approximately 10% of DHG's revenue. CME compliance mode activates only when Stephen explicitly toggles it.

**Owner:** Stephen Webber — CEO/Founder, 35+ years in business development and medical education. Bills at $450/hour. Expects Fortune 500 execution quality.

**Server:** g700data1 (10.0.0.251), Ubuntu 24.04, Docker 29.1.5, NVIDIA RTX 5080 (16GB VRAM), 64GB RAM, 1.9TB disk (11% used).

**Repo:** https://github.com/sdnydude/dhgaifactory3.5.git — Branch: master (current).

---

## Architecture (Current State — March 2026)

There are TWO agent systems. The CURRENT system is LangGraph. The LEGACY system is Docker-based FastAPI agents that are being decommissioned.

### LangGraph Agent System (CURRENT — Production)

15 graphs registered in `langgraph_workflows/dhg-agents-cloud/langgraph.json`, running as LangGraph Server on port 2026:

**11 Individual Agent Graphs:**

| Agent | File | Lines | Key Pattern |
|-------|------|-------|-------------|
| Needs Assessment | needs_assessment_agent.py | 1005 | 10-node sequential, cold open framework, 3100+ word validation |
| Research | research_agent.py | 1025 | Literature/PubMed queries, 30+ sources |
| Clinical Practice | clinical_practice_agent.py | 762 | Barrier identification, standard-of-care analysis |
| Gap Analysis | gap_analysis_agent.py | 703 | 5+ evidence-based gaps, quantification |
| Learning Objectives | learning_objectives_agent.py | 807 | Moore's Expanded Framework mapping |
| Curriculum Design | curriculum_design_agent.py | 921 | Educational design + innovation section |
| Research Protocol | research_protocol_agent.py | 868 | IRB-ready outcomes protocol |
| Marketing Plan | marketing_plan_agent.py | 779 | Audience strategy + channel budget |
| Grant Writer | grant_writer_agent.py | 783 | Full package assembly |
| Prose Quality | prose_quality_agent.py | 662 | De-AI-ification scoring, banned pattern detection |
| Compliance Review | compliance_review_agent.py | 429 | ACCME verification |

**4 Orchestrator Composition Graphs (in orchestrator.py, 1408 lines):**

| Recipe | Export | Pattern |
|--------|--------|---------|
| needs_package | needs_graph | Research + Clinical parallel → Gap → LO → Needs → Prose QA Pass 1 → Human Review |
| curriculum_package | curriculum_graph | Needs Package + Curriculum + Protocol + Marketing parallel → Human Review |
| grant_package | grant_graph | Full 11 agents, Prose QA 2 passes, Compliance gate, Human Review |
| full_pipeline | full_graph | Same as grant but with 3-way human review routing (approved/revision/rejected) |

**Architecture patterns across all agents:** Each agent has its own TypedDict state, ChatAnthropic (Claude Sonnet) with @traceable LangSmith decorators on every node, asyncio.wait_for with 5-minute timeout, standardized error records. Parallel execution via asyncio.gather with return_exceptions=True. Quality gates use conditional edges with retry loops (up to 3 iterations before human escalation).

### Legacy Agent System (BEING DECOMMISSIONED)

Docker-based FastAPI agents defined in `docker-compose.yml` under `agents/`. These predate the LangGraph migration:

| Container | Port | Status |
|-----------|------|--------|
| dhg-aifactory-orchestrator | 8011 (OVERRIDDEN by registry-api) | Running but orphaned — web-ui can't reach it |
| dhg-medical-llm | 8002 | Running |
| dhg-research | 8003 | Running |
| dhg-competitor-intel | 8006 | Running |
| dhg-visuals-media | 8008 | Running |
| dhg-curriculum | 8004 | STOPPED 3+ weeks |
| dhg-outcomes | 8005 | STOPPED 3+ weeks |
| dhg-qa-compliance | 8007 | STOPPED 3+ weeks |

### Infrastructure Services

| Service | Port | Purpose |
|---------|------|---------|
| dhg-registry-db | 5432 | PostgreSQL 15 + pgvector (57 tables) |
| dhg-registry-api | 8011 | FastAPI data registry, Prometheus /metrics |
| dhg-ollama | 11434 | Ollama (llama3.1:8b, nomic-embed-text, qwen3:14b) |
| dhg-session-logger | 8009 | Session tracking |
| dhg-logo-maker | 8012 | Logo generation |

### Observability Stack

| Service | Port | Status |
|---------|------|--------|
| dhg-prometheus | 9090 | 5 scrape targets, needs Docker SD |
| dhg-grafana | 3001 | Dashboards provisioned, needs more |
| dhg-loki | 3100 | Running but NO log ingestion configured |
| dhg-cadvisor | 8080 | Container metrics (v0.51.0) |
| dhg-node-exporter | 9100 | Host metrics |
| dhg-postgres-exporter | 9187 | Registry-db metrics |

### Additional Stacks (running independently)

| Stack | Main Port | Containers |
|-------|-----------|------------|
| Transcribe Pipeline | 8200 | 12 containers, GPU-accelerated |
| Dify | 3000 | 8 containers |
| RAGFlow | 8585 | 3 containers |
| LibreChat | 3010 | 3 containers (BEING DEPRECATED) |
| Infisical | 8089 | 5 containers (1 crash-looping) |

### Docker Networks (CRITICAL — isolation issues)

| Network | Members |
|---------|---------|
| dhgaifactory35_dhg-network | Main DHG stack (registry, agents, observability) |
| dhg-agents-cloud_default | LangGraph Server ONLY (isolated from main stack!) |
| dhg-transcribe_default | Transcribe pipeline |

**The LangGraph server is on its own Docker network, isolated from the main DHG stack. It uses `host.docker.internal` for cross-container communication. AI_FACTORY_REGISTRY_URL points to port 8500 which NOTHING listens on.**

---

## Known Critical Issues (from Feb 28, 2026 Audit)

### C1: Port 8011 Conflict
docker-compose.yml maps orchestrator to 8011:8000. docker-compose.override.yml maps registry-api to 8011:8000. Override wins. Web-UI hardcodes ws://10.0.0.251:8011 thinking it's the orchestrator but hits registry-api instead.

### C2: Web-UI Cannot Reach LangGraph Agents
The web-ui (web-ui/src/) connects to the legacy orchestrator via WebSocket at :8011. LangGraph Server runs on :2026 with a REST API. There is NO integration code connecting them. The web-UI cannot invoke any of the 15 LangGraph graphs.

### C3: LangGraph Network Isolation + Wrong Registry URL
LangGraph compose uses `host.docker.internal` instead of Docker network names. AI_FACTORY_REGISTRY_URL=http://host.docker.internal:8500 — port 8500 does not exist. Ollama URL should use container name on dhg-network.

### C4: Infisical Crash-Looping (Exit 255)
The infisical container has been crash-looping. May affect secret management.

### C5: Hardcoded IPs in Web-UI
Multiple files hardcode http://10.0.0.251:8011: MainLayout.jsx, App.jsx, StudioContext.jsx, AgentStatusPanel.jsx.

### C6: Stale Files at Project Root
MainLayout.jsx (50KB copy), main.py (24KB old monolith), architect_agentV3.py, test_ws_client.py, docker-compose.yml.bak, WARP.md.backup, plus 9 .bak/.backup files throughout.

### C7: No CI/CD
No GitHub Actions. .circleci config is stale. No automated testing or deployment.

### C8: Minimal Test Coverage
7 test files total. No pytest.ini at root. No test runner in CI.

### C9: Documentation Sprawl
60+ docs with overlapping, contradictory, and stale content. No single source of truth beyond TODO.md.

### C10: Loki Has No Log Ingestion
Running but zero containers ship logs to it.

### RECENTLY FIXED
- Registry-db healthcheck was connecting to wrong database (fixed: -d dhg_registry)
- Registry-db had no restart policy (fixed: unless-stopped)
- cAdvisor Docker API version mismatch (fixed: v0.47.2 → v0.51.0)
- Orphan infisical container removed
- 5 stale containers removed

---

## Frontend Migration Strategy (Decided Feb 18, 2026)

LibreChat is being deprecated. The target frontend stack (from March 2026 UI research):

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
| Orchestrator | langgraph_workflows/dhg-agents-cloud/src/orchestrator.py |
| Registry API | registry/api.py |
| CME endpoints | registry/cme_endpoints.py (990 lines, largest endpoint file) |
| DB models | registry/models.py |
| Schemas | registry/schemas.py |
| Web-UI router | web-ui/src/App.jsx |
| Web-UI layout | web-ui/src/components/MainLayout.jsx |
| Observability | observability/ |
| Agent architecture docs | DHG-CME-12-Agent-Docs/ |
| Current priorities | docs/TODO.md |
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
| Observability | LangSmith (@traceable), Prometheus, Grafana, Loki |
| Checkpointing | PostgresSaver (production persistence) |
| Agent LLM | Claude Sonnet via ChatAnthropic |
| Local LLM | Ollama (qwen3:14b, llama3.1:8b) |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic 2.5 |
| Database | PostgreSQL 15 + pgvector |
| Container runtime | Docker Engine 29.1.5 |
| Frontend (target) | Next.js, shadcn/ui, assistant-ui, CopilotKit, Refine, React Flow |
| Secrets | Infisical (when stable), .env (current) |

## What Is NOT In Use

Node-RED is fully deprecated. Do not mention or reference it in any context. Zapier is not used. On24 is not used. The legacy web-ui WebSocket connection to the orchestrator is broken and will be replaced, not fixed.
