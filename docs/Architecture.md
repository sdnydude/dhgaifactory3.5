# System Architecture

> **Canonical source of truth:** See `CLAUDE.md` in the project root for the current architecture, known issues, and technology stack. This file provides supplementary diagrams.

## High-Level Overview

```mermaid
graph TD
    User[User / Browser] -->|HTTPS| CF[Cloudflare Tunnel]
    CF -->|HTTP| Frontend[Next.js Frontend :3000]
    
    Frontend -->|langgraph-sdk| LGCloud[LangGraph Cloud]
    Frontend -->|REST| Registry[Registry API :8011]
    
    subgraph "LangGraph Agent Layer"
        LGCloud -->|invoke| Agents[11 Agent Graphs]
        LGCloud -->|compose| Orchestrators[4 Orchestrator Recipes]
        Agents -->|Claude Sonnet| Anthropic[Anthropic API]
        Agents -->|@traceable| LangSmith[LangSmith]
        Agents -->|@traced_node| Tempo[Tempo :3200]
    end
    
    subgraph "Data Layer"
        Registry -->|SQLAlchemy| DB[(PostgreSQL 15 + pgvector)]
        VSEngine[VS Engine :8013] -->|Anthropic| Anthropic
        SessionLogger[Session Logger :8009] -->|embeddings| Ollama[Ollama :11434]
    end
    
    subgraph "Observability Layer"
        Prometheus[Prometheus :9090] -->|scrape| Registry
        Prometheus -->|scrape| VSEngine
        Promtail[Promtail] -->|ship logs| Loki[Loki :3100]
        Prometheus -->|alert| Alertmanager[Alertmanager :9093]
        Grafana[Grafana :3001] -->|query| Prometheus
        Grafana -->|query| Loki
        Grafana -->|query| Tempo
    end
```

## Components

### 1. LangGraph Agent System (Production)
The core content generation engine. 17 graphs running in LangGraph Cloud (production) or localhost:2026 (development).
- **13 Individual Agents:** 11 content agents + Citation Checker (PubMed verification) + Registry Agent (gateway for all writes). Each with TypedDict state, Claude Sonnet LLM, dual tracing (LangSmith + OTel), async timeouts, quality gates.
- **4 Orchestrator Recipes:** Compose agents into pipelines with parallel execution, quality gates, and human-in-the-loop review via `interrupt()`.
- **Config:** `langgraph_workflows/dhg-agents-cloud/langgraph.json`

### 2. Registry API (Data Hub)
Central data management service. FastAPI with SQLAlchemy 2.0.
- **64 tables** in PostgreSQL 15 + pgvector
- **Endpoints:** Agent registry, CME project CRUD, session tracking, media/transcription, search/RAG
- **Metrics:** Prometheus histograms for read/write latency, operation counts, errors
- **Container:** dhg-registry-api on port 8011

### 3. Next.js Frontend
Production frontend connecting to LangGraph Cloud via langgraph-sdk.
- **Stack:** Next.js 16 + shadcn/ui + assistant-ui + CopilotKit
- **Features:** Chat interface, graph selector (17 graphs), Agent Inbox (human review), generative UI panels
- **Container:** dhg-frontend on port 3000
- **External:** app.digitalharmonyai.com via Cloudflare Tunnel

### 4. VS Engine (Verbalized Sampling)
Divergent-convergent mechanism for content generation diversity.
- **Container:** dhg-vs-engine on port 8013
- **External:** vs.digitalharmonyai.com via Cloudflare Tunnel
- **Metrics:** Prometheus (spread, selection_delta)

### 5. Observability Stack
Full monitoring, logging, and tracing.
- **Metrics:** Prometheus -> Alertmanager -> Grafana (6 scrape targets)
- **Logs:** Promtail -> Loki -> Grafana (Docker container logs)
- **Traces:** OTel SDK -> Tempo -> Grafana (agent execution traces)
- **APM:** LangSmith (@traceable on every agent node)
- **Configs:** `observability/` directory

### 6. Ollama (Local LLM)
Local inference for embeddings and summarization.
- **Models:** qwen3:14b, llama3.1:8b, nomic-embed-text
- **GPU:** NVIDIA RTX 5080 (16GB VRAM)
- **Container:** dhg-ollama on port 11434

## Data Flow

### CME Content Generation
```
User (Frontend) -> LangGraph Cloud -> Orchestrator Recipe
  -> [Parallel] Research + Clinical Practice agents
  -> Gap Analysis agent
  -> Learning Objectives agent  
  -> Needs Assessment agent
  -> Prose Quality agent (de-AI-ification pass)
  -> [Human Review Gate via interrupt()]
  -> Compliance Review agent
  -> Grant Writer agent (final assembly)
  -> Response to User
```

### Observability
```
Agent Node Execution
  -> @traceable decorator -> LangSmith (LLM traces)
  -> @traced_node decorator -> OTel SDK -> Tempo (infrastructure traces)
  -> Container stdout -> Promtail -> Loki (logs)
  -> /metrics endpoint -> Prometheus (metrics)
  -> All queryable in Grafana
```

## Docker Network Topology

| Network | Services |
|---------|----------|
| dhgaifactory35_dhg-network | Registry, legacy agents, frontend, VS engine, observability |
| dhg-agents-cloud_default | LangGraph dev server (port 2026) |
| dhg-transcribe_default | Transcribe pipeline (12 containers) |
| Host network | Node Exporter (pid: host, network_mode: host) |
