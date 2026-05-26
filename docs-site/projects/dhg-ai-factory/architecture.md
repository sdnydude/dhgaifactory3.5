---
sidebar_position: 2
title: Architecture
---

# Architecture

## Agent Systems

### LangGraph Agent System (Current — Production)

17 graphs registered in `langgraph_workflows/dhg-agents-cloud/langgraph.json`. Production runs on LangGraph Cloud; local dev instance on port 2026.

**13 Individual Agent Graphs:**

| Agent | File | Key Pattern |
|-------|------|-------------|
| Needs Assessment | `needs_assessment_agent.py` | 10-node sequential, cold open framework, 3100+ word validation |
| Research | `research_agent.py` | Literature/PubMed queries, 30+ sources |
| Clinical Practice | `clinical_practice_agent.py` | Barrier identification, standard-of-care analysis |
| Gap Analysis | `gap_analysis_agent.py` | 5+ evidence-based gaps, quantification |
| Learning Objectives | `learning_objectives_agent.py` | Moore's Expanded Framework mapping |
| Curriculum Design | `curriculum_design_agent.py` | Educational design + innovation section |
| Research Protocol | `research_protocol_agent.py` | IRB-ready outcomes protocol |
| Marketing Plan | `marketing_plan_agent.py` | Audience strategy + channel budget |
| Grant Writer | `grant_writer_agent.py` | Full package assembly |
| Prose Quality | `prose_quality_agent.py` | De-AI-ification scoring, banned pattern detection |
| Compliance Review | `compliance_review_agent.py` | ACCME verification |
| Citation Checker | `citation_checker_agent.py` | PubMed verification |
| Registry | `registry_agent.py` | Gateway for all agent writes, idempotency, dead letter queue |

All agents have dual tracing: LangSmith (`@traceable`) + OpenTelemetry (`@traced_node`) on every graph node (85 total).

**3 Orchestrator Composition Graphs:**

| Recipe | Pattern |
|--------|---------|
| `needs_package` | Research + Clinical parallel -> Gap -> LO -> Needs -> Prose QA -> Human Review |
| `curriculum_package` | Needs Package + Curriculum + Protocol + Marketing parallel -> Human Review |
| `grant_package` | Full 11 agents, Prose QA 2 passes, Compliance gate, Human Review |

### Legacy Agent System (Decommissioned)

9 Docker-based FastAPI agents (ports 2024, 8002-8008, 3005) — all stopped with `restart: "no"`. Source in `agents/` for reference. Do not build new features on these.

## Infrastructure Services

| Service | Port | Purpose |
|---------|------|---------|
| dhg-registry-db | 5432 | PostgreSQL 15 + pgvector (64 tables) |
| dhg-registry-api | 8011 | FastAPI data registry, Prometheus /metrics, CME endpoints |
| dhg-frontend | 3000 | Next.js production frontend (shadcn/ui + assistant-ui + CopilotKit) |
| dhg-vs-engine | 8013 | Verbalized Sampling engine |
| dhg-ollama | 11434 | Ollama (llama3.1:8b, nomic-embed-text, qwen3:14b) |
| dhg-session-logger | 8009 | Session tracking with Ollama embeddings |
| dhg-logo-maker | 8012 | Logo generation |
| dhg-audio-agent | 8101 | Audio processing |
| dhg-pdf-renderer | internal | Playwright PDF renderer + project bundler + Google Drive sync |
| dhg-medkb-db | 5435 | PostgreSQL 15 + pgvector (medkb knowledge store) |
| dhg-medkb-cache | 6381 | Redis 7 (query + embedding cache, 4GB LRU) |
| dhg-medkb-api | 8015 | FastAPI RAG service with LangGraph |

## Observability Stack

| Service | Port | Purpose |
|---------|------|---------|
| dhg-prometheus | 9090 | 6 scrape targets |
| dhg-grafana | 3001 | Dashboards: golden signals, Docker overview |
| dhg-loki | 3100 | Log aggregation via Promtail |
| dhg-tempo | 3200 | Distributed tracing (OTel gRPC :4317, HTTP :4318) |
| dhg-alertmanager | 9093 | Alert routing (webhook to registry-api) |
| dhg-cadvisor | 8080 | Container metrics |
| dhg-node-exporter | 9100 | Host metrics |
| dhg-postgres-exporter | 9187 | Registry-db metrics |

## Auth and RBAC

4-layer defense-in-depth:

1. **Cloudflare Access WAF** — JWT from `Cf-Access-Jwt-Assertion` header
2. **Next.js middleware** — JWT cookie check, route guard
3. **FastAPI middleware** — JWT signature validation, permission enforcement
4. **PostgreSQL RBAC** — 5 roles (admin, operations, finance, editor, viewer), 5 security tables

Dev mode: `SECURITY_DEV_MODE=true` bypasses all auth.

## Docker Networks

| Network | Members |
|---------|---------|
| dhgaifactory35_dhg-network | Main stack (registry, agents, frontend, observability) |
| dhg-agents-cloud_default | LangGraph dev server (port 2026) |
| dhg-transcribe_default | Transcribe pipeline |

## Frontend Stack

Decided Feb 2026, implemented March-April 2026:

- **shadcn/ui** — unified design system
- **assistant-ui** — composable chat interface with LangGraph starter
- **CopilotKit** — AG-UI protocol for agent-to-frontend communication
- **Refine** — headless admin console with FastAPI data providers
- **React Flow** — visual LangGraph workflow editor
- **Tremor** — monitoring dashboards
- **Agent Inbox** — human-in-the-loop CME review workflows
