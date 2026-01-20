# DHG AI Factory - Task Tracking

**Last Updated:** January 13, 2026  
**Status:** 🟢 **Production Running** (25+ containers healthy on .251)  
**Tailscale IP:** 100.107.14.51 (g700data1)

---

## ✅ Completed

### Infrastructure
- [x] PostgreSQL + pgvector (14 tables)
- [x] LangGraph checkpoint table + AsyncPostgresSaver
- [x] Image storage (BYTEA)
- [x] Onyx RAG connector
- [x] Transcription pipeline (8 services)
- [x] All 7 CME agents deployed and healthy
- [x] Web UI at port 3005
- [x] Tailscale tunnel configured (g700data1, dh40801, stephens-macbook-pro connected)

### LangSmith + LangGraph (IN ORCHESTRATOR CONTAINER)
- [x] LangSmith Plus account (DHG org, workspace ID: bad71132-9f05-443d-9a04-1f923632024c)
- [x] LangSmith SDK v0.6.2 in orchestrator
- [x] LangGraph CLI v0.4.11 in orchestrator
- [x] LangGraph API v0.6.35 in orchestrator
- [x] LangGraph checkpoint-postgres v3.0.3
- [x] langgraph.json configured for dhg_workflow graph
- [x] Port 2024 exposed for LangGraph dev server
- [x] Port 8011 exposed for Orchestrator API
- [x] Traces appearing in LangSmith Cloud
- [x] PostgreSQL checkpointer with AsyncPostgresSaver
- [x] LangGraph workflows executing end-to-end

### Agent Communication
- [x] Medical-LLM generates content via Ollama
- [x] QA-Compliance validation (fixed 422 error)
- [x] Orchestrator WebSocket routing
- [x] End-to-end workflow completes without errors
- [x] All 6 specialized agents healthy (medical-llm, research, curriculum, outcomes, competitor-intel, qa-compliance)

### UI
- [x] Multi-panel layout with tabs
- [x] Visuals Tool Panel
- [x] IDE Gallery with lightbox
- [x] Glassmorphism theme

---

## 🎯 LangSmith Studio Access (via Tailscale)

> Access LangGraph Studio using Tailscale tunnel (no Cloudflare needed)

**Studio URL:**
```
https://smith.langchain.com/studio/?baseUrl=http://100.107.14.51:2024
```

**Direct API:**
- LangGraph API: http://100.107.14.51:2024
- Orchestrator API: http://100.107.14.51:8011
- Web UI: http://100.107.14.51:3005

---

## 🔴 Priority 1: Agent Enhancements (Core Value)

> Make agents more capable with real data sources and improved reliability

- [ ] **Research Agent** - Connect PubMed, ClinicalTrials.gov, CDC APIs
- [ ] **Competitor-Intel** - Web scrapers for ACCME/Medscape/WebMD
- [ ] **Medical LLM** - Cloud fallbacks (OpenAI, Anthropic)
- [ ] **QA-Compliance** - Registry logging for audit trail
- [ ] **Visuals** - XMP metadata embedding, compliance_mode selector

## 🟠 Priority 2: UI Improvements

> Enhance user experience and developer tools

- [ ] **LangGraph visualization** - Graph view in UI
- [ ] **Registry browser** - Query and view database contents
- [ ] **Prompt Refiner** - Real-time prompt quality analysis
- [ ] **Model selector** - Expose all agent models to UI

## 🟡 Priority 3: LangSmith Plus Features

> Leverage full LangSmith Plus for observability

- [ ] **Agents in LangSmith Studio** - Expose 16 agents in graph view
- [ ] **Evaluations** - Online/offline evaluation workflows
- [ ] **Prompt Hub** - Version prompts centrally
- [ ] **Monitoring & Alerting** - Set up LangSmith alerts

## 🟢 Priority 4: Infrastructure Hardening

> Network security and reliability

- [ ] **Health check dashboard** - Grafana metrics
- [ ] **Backup automation** - Scheduled PostgreSQL backups
- [ ] **SSL/TLS** - HTTPS for all endpoints

## 🔵 Priority 5: Multi-Tenant Scalability

> Future: Multi-tenant deployment

- [ ] **Workspace isolation** - Per-tenant workspaces
- [ ] **API key management** - Per-tenant service keys
- [ ] **Resource quotas** - Trace limits per tenant
- [ ] **LangGraph Cloud** - Evaluate for scalability
