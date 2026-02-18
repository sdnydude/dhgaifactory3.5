# DHG AI Factory - Master To-Do List
**Last Updated:** Feb 18, 2026 (10:55 EST)

## System Status
- **Running Containers:** 54 total across all stacks
- **DHG Stack:** 25 containers (22 healthy, 3 no healthcheck: dhg-ollama, dhg-transcribe-qdrant, dhg-worker)
- **LangGraph Server:** Running on :2026 (v0.7.16, 15 graphs)
- **GPU:** RTX 5080 (0% utilization, 4.0GB/16GB VRAM)
- **Disk:** 11% used (183GB / 1.9TB)
- **LibreChat:** Running on :3010 — **BEING DEPRECATED**
- **Ollama Models:** llama3.1:8b, nomic-embed-text, qwen3:14b
- **Observability:** Prometheus ✓ (:9090), Grafana ✓ (:3001), Loki ✓ (:3100)

### Container Groups
| Stack | Count | Status |
|---|---|---|
| DHG AI Factory | 25 | 22 healthy |
| Transcribe Pipeline | 9 | All running |
| Dify | 8 | All running |
| Infisical | 6 | 5 healthy, 1 crash-looping (Exit 255) |
| LibreChat | 3 | Running (being deprecated) |
| RAGFlow | 1 | Running (:8585) |
| pgAdmin | 1 | Running (:5050) |

---

## P0: Blockers

- [ ] **`infisical` container crash-looping** (Exit 255) — investigate logs, may affect secret sync

---

## P1: Active Sprint

### Frontend Migration — LibreChat → LangGraph Native
- [ ] Deploy Open Agent Platform (agent management, intake forms, multi-agent)
- [ ] Deploy Agent Inbox (CME human review queue)
- [ ] Deploy Open Canvas (writer document editing)
- [ ] Wire all three to LangGraph Cloud (prod) and :2026 (dev)
- [ ] Update agents to emit HumanInterrupt schema for Agent Inbox
- [ ] Remove LibreChat from active use

### CME Workflow
- [x] PostgreSQL database schema (003_add_cme_projects.sql)
- [x] CME endpoints integrated with database
- [x] JSONB datetime serialization fix
- [ ] Human Review Requirements implementation (via Agent Inbox)

### Observability Stack
- [x] Deploy Prometheus/Grafana/Loki stack
- [x] Healthchecks on all monitorable containers (22/25 healthy)
- [ ] Configure database exporters
- [ ] Set up Grafana dashboards
- [ ] Configure Alertmanager

---

## P2: Next Up

### Antigravity Session Sync
- [x] Build sync agent using local API (port 58575)
- [x] Created generate_embeddings.py script
- [x] Export via GetCascadeTrajectory endpoint working
- [x] Deduplication fixed (delete before re-insert)
- [ ] Run embedding generation (4974 messages, 0 with embeddings)
- [ ] Automate daily sync

### RAGFlow Setup
- [x] RAGFlow running at ragflow.digitalharmonyai.com
- [x] Google OAuth configured
- [ ] Configure LLM connection
- [ ] Create first knowledge base

### Dify Setup
- [x] Dify running at dify.digitalharmonyai.com
- [x] Google OAuth configured (shared with RAGFlow)
- [ ] Configure as documentation platform

---

## P3: LangGraph Frontend Features

- [ ] **Generative UI** - Domain panels (leads, projects, CMS) rendered inline in chat
- [ ] **MCP Integration** - Connect agents to external tools via Open Agent Platform
- [ ] **Memory** - Persistent context via LangGraph checkpointing
- [ ] **LLManager** - Approval workflow with reflection for CME review
- [ ] **Healthchecks** - Add to dhg-ollama, dhg-transcribe-qdrant, dhg-worker

---

## P4: Security & Media

### Security
- [ ] **Build DHG Security Agent** (2 hrs)
  - Manage Cloudflare Access
  - Fetch analytics via GraphQL API

### Video Content Pipeline
- [ ] Vimeo API Integration
- [ ] YouTube API Integration
- [ ] Video Ingestion Pipeline
- [ ] AI Clip Generation

---

## P5: Backlog

- [ ] Code Interpreter
- [ ] Claude Files API
- [ ] XMP Metadata (Visuals Agent)
- [ ] LibreChat to Registry Sync
- [ ] Upgrade Infisical CLI

---

## Completed (Feb 18, 2026)

- [x] Full agent-check: 54 containers inventoried across all stacks
- [x] LangGraph frontend strategy decided: LibreChat → Open Agent Platform + Agent Inbox + Open Canvas
- [x] 17-option LangGraph frontend comparative table researched and documented
- [x] TODO.md updated with accurate system status

## Completed (Feb 3 - Feb 17, 2026)

- [x] Audio agent added to LangGraph (647b3dd)
- [x] Recipe-Based Orchestrator implemented (92d0d2f)
- [x] Marketing Plan agent created
- [x] Docker healthchecks added for Grafana, Loki, Prometheus, registry-api
- [x] Registry-API Docker image rebuilt (fixed missing Alembic migration 003)
- [x] LangGraph proxy and docker override (4c45b69)
- [x] Research protocol + curriculum design: disease_state/therapeutic_area fields

## Completed (Jan 29 - Feb 2, 2026)

- [x] CME intake form PostgreSQL integration (b9b53df)
- [x] CME JSONB datetime serialization fix (c82233c)
- [x] Planning-with-files skill research-first requirement (e71559f)
- [x] Infisical workflow DB role fix (a819922)
- [x] CME intake form improvements (8f5f91b)
- [x] Teammate onboarding guide for Antigravity (5d85535)
- [x] Agent planning and progress tracking files (a769507)
- [x] Planning-with-files skill installed (0cb0757)
- [x] Antigravity deduplication fixed (21acaa9)
- [x] Antigravity export HTTPS/cascadeId fixes (e7f744b)
- [x] Antigravity session sync scripts and workflow (b1c4e61)
- [x] All workflows updated for Remote-SSH (d9f04af)

## Completed (Jan 27-28, 2026)

- [x] RAGFlow OAuth configured
- [x] Redis connected to RAGFlow network
- [x] Observability implementation plan created
- [x] All files committed to git (274c175)
- [x] .agent folder synced to .251
- [x] pre-response workflow updated
- [x] Ingest scripts created (ingest_conversations.py, generate_embeddings.py)

## Completed (Jan 18-26, 2026)

- [x] Tavily Web Search configured
- [x] LibreChat Google OAuth
- [x] qwen2.5:14b → qwen3:14b as default Ollama model
- [x] Infisical CLI working
- [x] All DHG agents configured in LibreChat
- [x] Perplexity configured
- [x] pgAdmin running on :5050
- [x] 34 Antigravity sessions ingested to CR
