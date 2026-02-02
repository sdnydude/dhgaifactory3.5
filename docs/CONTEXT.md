# DHG AI Factory - Current Context

**Last Updated:** Feb 2, 2026

## Architecture (Current State)

### What's Running

| Component | Location | Status |
|-----------|----------|--------|
| **9 DHG Agents** | Docker on .251 | ✅ All healthy |
| **LibreChat** | Docker on .251 | ✅ Port 3010 |
| **PostgreSQL** | Docker on .251 | ✅ Registry DB |
| **Ollama** | Docker on .251 | ✅ qwen3:14b, nomic-embed-text |
| **pgAdmin** | Docker on .251 | ✅ Port 5050 |

### LLM Orchestration

Orchestration is handled by **LibreChat** via agent configuration. The old custom orchestrator service (port 8011) was deprecated.

---

## Agent Parallel Processing Patterns

```
┌─────────────────────────────────────────────────────────────────┐
│                     PARALLEL PHASE 1                             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────┐               │
│  │ Research │    │ Competitor   │    │ Visuals  │               │
│  │  (8003)  │    │ Intel (8006) │    │  (8008)  │               │
│  └────┬─────┘    └──────┬───────┘    └────┬─────┘               │
└───────┼─────────────────┼─────────────────┼─────────────────────┘
        │                 │                 │
        ▼                 ▼                 │
┌───────────────────────────────────────────┼─────────────────────┐
│              SEQUENTIAL PHASE                                    │
│  ┌────────────┐                           │                      │
│  │ Medical LLM│ ◄── needs research ───────┘                      │
│  │   (8002)   │                                                  │
│  └─────┬──────┘                                                  │
└────────┼────────────────────────────────────────────────────────┘
         │
┌────────┼────────────────────────────────────────────────────────┐
│        ▼         PARALLEL PHASE 2                                │
│  ┌───────────┐    ┌──────────┐                                   │
│  │ Curriculum│    │ Outcomes │                                   │
│  │   (8004)  │    │  (8005)  │                                   │
│  └─────┬─────┘    └────┬─────┘                                   │
└────────┼───────────────┼────────────────────────────────────────┘
         │               │
         ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FINAL VALIDATION                                │
│  ┌─────────────────────────────────────┐                        │
│  │        QA/Compliance (8007)         │                        │
│  │   Validates all outputs, last step  │                        │
│  └─────────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

### Processing Summary

| Phase | Agents | Notes |
|-------|--------|-------|
| **Parallel 1** | Research, Competitor Intel, Visuals | Independent data gathering |
| **Sequential** | Medical LLM | Depends on research results |
| **Parallel 2** | Curriculum, Outcomes | Can process content simultaneously |
| **Final** | QA/Compliance | Must validate everything at end |

### Support Agents (Always Available)

| Agent | Port | Purpose |
|-------|------|---------|
| Session Logger | 8009 | Audit trail for all requests |
| Logo Maker | 8012 | On-demand brand asset generation |

---

## Active Work Streams

### 1. CME Intake Form (P1)
- ✅ PostgreSQL database schema deployed
- ✅ CME endpoints integrated with database
- ✅ JSONB datetime serialization fixed
- 🔲 LibreChat CME sidebar integration
- 🔲 Human Review Requirements implementation

### 2. LibreChat Agent Features (P1)
- ✅ Agent config in librechat.yaml
- 🔲 Enable Artifacts for agents
- 🔲 Enable Tools selection for agents

### 3. Observability Stack (P2)
- 🔲 Prometheus/Grafana/Loki deployment
- 🔲 Database exporters

---

## Port Reference

| Port | Service | Notes |
|------|---------|-------|
| 3010 | LibreChat | Main UI |
| 5050 | pgAdmin | Database management |
| 5432 | PostgreSQL | Registry database |
| 8002 | Medical LLM Agent | |
| 8003 | Research Agent | |
| 8004 | Curriculum Agent | |
| 8005 | Outcomes Agent | |
| 8006 | Competitor Intel Agent | |
| 8007 | QA/Compliance Agent | |
| 8008 | Visuals/Media Agent | |
| 8009 | Session Logger | |
| 8012 | Logo Maker | |
| 11434 | Ollama | Local LLM |

---

## Data Storage

### PostgreSQL (Registry DB)
- Agent metadata and capabilities
- CME project intake data
- Request/response logs
- Antigravity session history

### Ollama
- **qwen3:14b** - General purpose LLM
- **nomic-embed-text** - Embeddings for RAG

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/TODO.md` | Active task list |
| `docs/PROJECT_TRUTH.md` | System status source of truth |
| `.agent/workflows/` | Automated workflows |
| `registry/models.py` | Database models |
| `registry/migrations/` | SQL migrations |

---

## Git Info

- **Branch:** `feature/langgraph-migration`
- **Remote:** `https://github.com/sdnydude/dhgaifactory3.5.git`
