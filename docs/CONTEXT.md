# DHG AI Factory - Current Context

**Last Updated:** Jan 25, 2026 2:25 PM

## Architecture Direction (from Jan 23-24 sessions)

### The Decision: Docker → LangSmith Cloud

**FROM (Being Deprecated):**
- Docker-based FastAPI agents on .251
- Docker-based orchestrator routing requests
- Self-hosted infrastructure

**TO (Target):**
- All 16 agents on **LangSmith Cloud**
- LibreChat connects **directly to LangSmith Cloud** endpoints
- Registry for metadata/tracking only (not routing)
- Agents deployed via **GitHub → LangSmith UI** (not CLI)

### Key Insights from Previous Sessions

1. **"Workflows run in cloud, not on .251"** - LangSmith Cloud hosts execution
2. **"Deploy from GitHub, not CLI"** -  is for local testing only
3. **No proxies needed** - Use LangServe for OpenAI-compatible endpoints
4. **Studio is web-based** - at smith.langchain.com

### What Stays
- **Registry Database** - for tracking agents, requests, costs
- **LibreChat** - as user interface
- **Local Development** - testing on .251 before pushing to cloud

### What Gets Deprecated
- **Docker Orchestrator** - no longer needed when agents are in cloud
- **FastAPI agent containers** - replaced by LangGraph Cloud agents
- **Proxy endpoints** - LangServe provides OpenAI-compatibility natively

---

## Current State (Jan 25, 2026)

### Running on .251
| Service | Port | Status | Future |
|---------|------|--------|--------|
| CME Research Agent | 2026 | Running (dev) | Deploy to LangSmith Cloud |
| Registry API | 8011 | Running | Keep (metadata only) |
| Docker Orchestrator | 8000 | Unknown | DEPRECATE |
| LibreChat | 3010 | Running | Keep |

### Migration Status
- [x] CME Research Agent created on LangGraph
- [x] Parallel search pattern implemented
- [x] LangSmith Studio connected
- [ ] Deploy to LangSmith Cloud (via GitHub)
- [ ] LibreChat connects to cloud endpoint
- [ ] Deprecate Docker orchestrator

---

## LibreChat Integration (Corrected)

**WRONG approach (what I started doing):**
- Add OpenAI endpoints to Docker orchestrator
- LibreChat → Orchestrator → LangGraph agent

**RIGHT approach:**
- Deploy agent to LangSmith Cloud
- LibreChat → LangSmith Cloud directly (via LangServe)
- No orchestrator in the middle

### librechat.yaml (Target)


---

## Immediate Actions Needed

1. **STOP** adding OpenAI endpoints to orchestrator (wrong direction)
2. **REVERT** changes to orchestrator/main.py if any were made
3. **Deploy CME Research Agent to LangSmith Cloud** via GitHub
4. **Update librechat.yaml** to point to cloud endpoint

---

## Port Reference

| Port | Service | Notes |
|------|---------|-------|
| 2026 | CME Research (dev) | langgraph dev server, for testing |
| 3010 | LibreChat | UI |
| 8011 | Registry API | metadata storage |
| 8500 | Registry (old) | may be deprecated |

---

## Data Storage Strategy (from Jan 24)

### Dual-Write: CR + Onyx

All session context, decisions, and artifacts should be stored in:

1. **Central Registry (CR)**
   - Agent metadata, capabilities
   - Request history
   - Cost tracking
   - Deployment status

2. **Onyx Knowledge Base**
   - Session context (like this CONTEXT.md)
   - Architecture decisions
   - SOPs and templates
   - Searchable via RAG

### What to Store

| Data | CR | Onyx | Notes |
|------|-----|------|-------|
| Agent definitions | ✓ | ✓ | Metadata + docs |
| Research results | ✓ | ✓ | Structured + searchable |
| Session decisions | | ✓ | RAG-searchable context |
| Cost/usage metrics | ✓ | | Structured only |
| SOPs/templates | | ✓ | Documentation |

---

## Outstanding TODOs from Previous Sessions

### From Jan 24 Task.md:
- [ ] Onyx integration (dual-write)
- [ ] LangSmith Assistants setup
- [ ] MCP server deployment

### Architecture Decisions Pending:
- Should new agents be LangGraph-only (no Docker)?
- How do existing Docker agents migrate?
- What's the orchestrator deprecation timeline?
