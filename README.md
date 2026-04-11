# DHG AI Factory v3.5

**Multi-Agent Platform for Pharmaceutical-Grade CME Grant Documentation**

Digital Harmony Group's AI Factory — a LangGraph-based orchestration platform that generates ACCME-compliant Continuing Medical Education content using 11 specialized AI agents and 4 composition pipelines.

---

## Architecture

```
                          LangGraph Cloud (Production)
                          localhost:2026 (Development)
                                    |
              ┌─────────────────────┼──────────────────────┐
              |                     |                      |
     ┌────────┴─────────┐  ┌───────┴────────┐  ┌─────────┴──────────┐
     | Orchestrator      |  | Content Agents |  | Quality Gates      |
     | Recipes (4)       |  | (9 agents)     |  | (2 agents)         |
     |                   |  |                |  |                    |
     | needs_package     |  | research       |  | prose_quality      |
     | curriculum_package|  | clinical_pract |  | compliance_review  |
     | grant_package     |  | gap_analysis   |  |                    |
     | full_pipeline     |  | learning_obj   |  └────────────────────┘
     └───────────────────┘  | curriculum_des |
                            | research_proto |
                            | marketing_plan |
                            | grant_writer   |
                            | needs_assessmt |
                            └────────────────┘
              |                     |                      |
     ┌────────┴─────────────────────┴──────────────────────┴──┐
     |                    Infrastructure                       |
     |  PostgreSQL 15 + pgvector  |  Ollama (qwen3, llama3.1) |
     |  Registry API (:8011)      |  VS Engine (:8013)         |
     |  Next.js Frontend (:3000)  |  Session Logger (:8009)    |
     └─────────────────────────────────────────────────────────┘
              |
     ┌────────┴──────────────────────────────────────────────┐
     |                   Observability                        |
     |  Prometheus → Alertmanager → Grafana                   |
     |  Promtail → Loki → Grafana                             |
     |  OTel SDK → Tempo → Grafana                            |
     |  LangSmith (@traceable on every node)                  |
     └────────────────────────────────────────────────────────┘
```

## 15 LangGraph Graphs

**11 Individual Agents** — each with TypedDict state, Claude Sonnet LLM, dual tracing (LangSmith + OTel), 5-minute async timeouts, and quality gate retry loops:

| Agent | Purpose |
|-------|---------|
| Needs Assessment | Cold open narrative, 3100+ word validation |
| Research | Literature/PubMed queries, 30+ sources |
| Clinical Practice | Barrier identification, standard-of-care |
| Gap Analysis | 5+ evidence-based gaps, quantification |
| Learning Objectives | Moore's Expanded Framework mapping |
| Curriculum Design | Educational design + innovation section |
| Research Protocol | IRB-ready outcomes protocol |
| Marketing Plan | Audience strategy + channel budget |
| Grant Writer | Full package assembly |
| Prose Quality | De-AI-ification scoring, banned pattern detection |
| Compliance Review | ACCME standards verification |

**4 Orchestrator Composition Graphs** — parallel execution via asyncio.gather, conditional quality gates, human-in-the-loop review:

| Recipe | Pipeline |
|--------|----------|
| needs_package | Research + Clinical parallel -> Gap -> LO -> Needs -> Prose QA -> Human Review |
| curriculum_package | Needs Package + Curriculum + Protocol + Marketing parallel -> Human Review |
| grant_package | Full 11 agents, Prose QA 2 passes, Compliance gate, Human Review |
| full_pipeline | Grant package with 3-way human review routing (approved/revision/rejected) |

---

## Quick Start

### Prerequisites

- Docker Engine 29+ with Docker Compose
- NVIDIA GPU (optional, for Ollama local inference)
- API keys: `ANTHROPIC_API_KEY`, `LANGCHAIN_API_KEY` (required); `GOOGLE_API_KEY`, `PERPLEXITY_API_KEY`, `NCBI_API_KEY` (optional)

### Start Infrastructure

```bash
# Main stack (registry, observability, frontend, legacy agents)
docker compose up -d

# LangGraph dev server (separate compose)
cd langgraph_workflows/dhg-agents-cloud
docker compose up -d
```

### Verify Health

```bash
curl -s http://localhost:2026/ok          # LangGraph server
curl -s http://localhost:8011/healthz     # Registry API
curl -s http://localhost:3000             # Frontend
curl -s http://localhost:9090/-/healthy   # Prometheus
```

### Access Services

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Registry API (Swagger) | http://localhost:8011/docs |
| Grafana | http://localhost:3001 (admin/admin) |
| Prometheus | http://localhost:9090 |
| LangGraph Studio | http://localhost:2026 |

---

## Project Structure

```
dhgaifactory3.5/
  langgraph_workflows/dhg-agents-cloud/
    src/                    # 13 agent graphs + orchestrator + tracing
    langgraph.json          # Graph registry (17 graphs)
    docker-compose.yml      # LangGraph dev server
  registry/                 # FastAPI registry API + CME endpoints
  frontend/                 # Next.js + shadcn/ui + assistant-ui + CopilotKit
  services/
    vs-engine/              # Verbalized Sampling engine
    session-logger/         # Session capture with Ollama embeddings
    logo-maker/             # Logo generation
  agents/                   # Legacy FastAPI agents (being decommissioned)
  observability/            # Prometheus, Grafana, Loki, Tempo, Promtail configs
  DHG-CME-12-Agent-Docs/    # 12-agent system architecture documentation
  docs/                     # Active documentation
  docs/archive/             # Historical/superseded docs
  .github/workflows/ci.yml # GitHub Actions CI (lint, test, compose validation)
  docker-compose.yml        # Main infrastructure compose
  docker-compose.override.yml # Services, observability, frontend
  CLAUDE.md                 # Canonical source of truth for architecture & rules
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | LangGraph (StateGraph, Command pattern) |
| Observability | LangSmith + OTel/Tempo + Prometheus + Grafana + Loki |
| Agent LLM | Claude Sonnet via ChatAnthropic |
| Local LLM | Ollama (qwen3:14b, llama3.1:8b, nomic-embed-text) |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic 2.5 |
| Database | PostgreSQL 15 + pgvector (64 tables) |
| Frontend | Next.js 16, shadcn/ui, assistant-ui, CopilotKit |
| Container Runtime | Docker Engine 29.1.5 |
| CI/CD | GitHub Actions |
| External Access | Cloudflare Tunnel + Cloudflare Access (Google OAuth) |

---

## Documentation

- **CLAUDE.md** — Canonical architecture, rules, and system state
- **docs/TODO.md** — Master task list with phased priorities
- **docs/FRONTEND.md** — Frontend architecture and components
- **docs/REGISTRY_API.md** — Registry API endpoint reference
- **docs/OBSERVABILITY_RUNBOOK.md** — Monitoring operational procedures
- **DHG-CME-12-Agent-Docs/** — Complete 12-agent system specifications

---

## Server

- **Host:** g700data1 (10.0.0.251)
- **OS:** Ubuntu 24.04
- **GPU:** NVIDIA RTX 5080 (16GB VRAM)
- **RAM:** 64GB
- **Disk:** 1.9TB root (12% used), 3.6TB data (4% used)
- **Containers:** ~60 running across 5 stacks
- **External:** app.digitalharmonyai.com (frontend), vs.digitalharmonyai.com (VS Engine)
