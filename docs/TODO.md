# DHG AI Factory - Master To-Do List
**Last Updated:** Feb 2, 2026

## System Status
- **Running Containers:** 11 dhg-prefixed (10 healthy, 1 no healthcheck)
- **Healthy Agents:** 7/7 (Orchestrator EOL'd)
- **Key Services:** All healthy
- **GPU:** RTX 5080 (1% utilization, 4.7GB/16GB)
- **Disk:** 9% used (146GB / 1.9TB)
- **LibreChat:** Running on :3010
- **Ollama Models:** nomic-embed-text, qwen3:14b

---

## P0: Blockers - CLEAR

No blockers.

---

## P1: Active Sprint

### CME Intake Form (IN PROGRESS)
- [x] PostgreSQL database schema (003_add_cme_projects.sql)
- [x] CME endpoints integrated with database
- [x] JSONB datetime serialization fix
- [ ] LibreChat CME sidebar integration
- [ ] Human Review Requirements implementation

### LibreChat Agent Features (IN PROGRESS)
- [x] Agents config in librechat.yaml
- [ ] Enable Artifacts for agents
- [ ] Enable Tools selection for agents
- [ ] Test agent tool capabilities

### Observability Stack
- [ ] Deploy Prometheus/Grafana/Loki stack
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

## P3: LibreChat Features

- [x] **Web Search (Tavily)** - Configured Jan 18
- [ ] **Memory** - Persistent context across chats
- [ ] **Artifacts** - Generative UI output (agent feature)
- [ ] **MCP Integration** - Connect to external tools

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
