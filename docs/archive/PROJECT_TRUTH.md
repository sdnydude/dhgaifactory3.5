# DHG AI Factory - Project Truth Document
**Last Audit:** Feb 2, 2026 07:20 EST  
**Audited by:** Antigravity (Claude)

> [!CAUTION]
> This document is the source of truth. Updated on every `/session-start`, `/agent-check`, and status review.

---

## Status Legend

| Status | Meaning |
|--------|---------|
| ✅ **OPERATIONAL** | Built, deployed, tested, working |
| 🔧 **NEEDS FIX** | Built but broken, needs repair |
| 📦 **BUILT NOT DEPLOYED** | Code exists, not running |
| ❌ **CLAIMED NOT BUILT** | Marked complete but doesn't exist |
| 📋 **PLANNED** | In plan, not started |
| 🚫 **NOT IN PLAN** | Needed but not yet planned |

---

## Infrastructure Components

| Component | Status | Details |
|-----------|--------|---------|
| **dhg-registry-db** | ✅ OPERATIONAL | PostgreSQL running (healthy, 2+ weeks uptime) |
| **dhg-ollama** | ✅ OPERATIONAL | Running (no healthcheck, expected), qwen3:14b + nomic-embed-text |
| **LibreChat** | ✅ OPERATIONAL | Running on port 3010 |
| **pgAdmin** | ✅ OPERATIONAL | Running on port 5050 |
| **vectordb** | ✅ OPERATIONAL | Running |
| **chat-mongodb** | ✅ OPERATIONAL | Running |
| **chat-meilisearch** | ✅ OPERATIONAL | Running |

---

## DHG Agent Services (Docker)

| Agent | Status | Port | Notes |
|-------|--------|------|-------|
| **dhg-medical-llm** | ✅ OPERATIONAL | 8002 | Healthy (11 days) |
| **dhg-research** | ✅ OPERATIONAL | 8003 | Healthy (9 days) |
| **dhg-curriculum** | ✅ OPERATIONAL | 8004 | Healthy (11 days) |
| **dhg-outcomes** | ✅ OPERATIONAL | 8005 | Healthy (11 days) |
| **dhg-competitor-intel** | ✅ OPERATIONAL | 8006 | Healthy (11 days) |
| **dhg-qa-compliance** | ✅ OPERATIONAL | 8007 | Healthy (11 days) |
| **dhg-visuals-media** | ✅ OPERATIONAL | 8008 | Healthy (11 days) |
| **dhg-session-logger** | ✅ OPERATIONAL | 8009 | Healthy (12 days) |
| **dhg-logo-maker** | ✅ OPERATIONAL | 8012 | Healthy (2 weeks) |

### Deprecated Services

| Service | Status | Notes |
|---------|--------|-------|
| **Orchestrator (8011)** | ❌ EOL | Removed from architecture - agents accessed directly or via LibreChat |
| **dhg-registry-api (8500)** | 📦 DEPRECATED | Replaced by per-agent direct access |

---

## Current Architecture (Feb 2026)

```
┌────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                          │
│   LibreChat (3010) │ LangSmith Studio │ Agent APIs (8002-8012)  │
└─────────────────────────────┬──────────────────────────────────┘
                              │
    ┌─────────────┬───────────┼───────────┬─────────────┐
    │             │           │           │             │
┌───▼───┐    ┌───▼───┐   ┌───▼───┐   ┌───▼───┐    ┌───▼───┐
│Medical│    │Research│   │Currclm│   │Outcomes│   │Compet.│
│  LLM  │    │ Agent  │   │ Agent │   │ Agent  │   │ Intel │
│ (8002)│    │ (8003) │   │ (8004)│   │ (8005) │   │ (8006)│
└───────┘    └────────┘   └───────┘   └────────┘   └───────┘
                              │
              ┌───────────────┼───────────────┐
          ┌───▼───┐       ┌───▼───┐       ┌───▼───┐
          │  QA/  │       │Visuals│       │Session│
          │Compli.│       │ Media │       │Logger │
          │(8007) │       │(8008) │       │(8009) │
          └───────┘       └───────┘       └───────┘
                              │
┌─────────────────────────────▼──────────────────────────────────┐
│                      DATA LAYER                                 │
│  PostgreSQL (5432) │ Ollama (11434) │ MongoDB │ Redis          │
└────────────────────────────────────────────────────────────────┘
```

---

## Active Work Streams

### P1: CME Intake Form (IN PROGRESS)
| Component | Status | Details |
|-----------|--------|---------|
| Database schema | ✅ OPERATIONAL | `003_add_cme_projects.sql` deployed |
| CME endpoints | ✅ OPERATIONAL | Integrated with PostgreSQL |
| JSONB serialization | ✅ OPERATIONAL | Fixed datetime handling |
| LibreChat sidebar | 📋 PLANNED | CME panel integration |
| Human Review UI | 📋 PLANNED | Per requirements doc |

### P2: LibreChat Agent Features
| Component | Status | Details |
|-----------|--------|---------|
| Agent config | ✅ OPERATIONAL | In librechat.yaml |
| Artifacts | 📋 PLANNED | Enable generative UI |
| Tools | 📋 PLANNED | Tool selection for agents |

---

## System Health Summary

| Metric | Value |
|--------|-------|
| **Docker Containers** | 10 healthy + 1 no-healthcheck (Ollama) |
| **Agent Endpoints** | 7/7 responding |
| **GPU** | RTX 5080 - 4.7GB/16GB (1% util) |
| **Disk** | 146GB / 1.9TB (9% used) |
| **Branch** | `feature/langgraph-migration` |

---

## Next Steps for Session Start

1. Run `/agent-check` for full status
2. Check `docs/TODO.md` for current priorities
3. Review any `🔧 NEEDS FIX` items above

**This document will be updated automatically on each `/session-start` and `/agent-check` run.**
