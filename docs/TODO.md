# DHG AI Factory - Master To-Do List
**Last Updated:** Jan 28, 2026

## System Status
- **Running Containers:** 11 dhg-prefixed + supporting services
- **Healthy Agents:** 7/8 (Orchestrator /health returns 404)
- **Key Services:** All healthy
- **GPU:** RTX 5080 (4% utilization)
- **Disk:** 8% used (136GB / 1.9TB)

---

## P0: Blockers - CLEAR

No blockers.

---

## P1: Active Sprint

### Observability Stack (NEW)
- [ ] Deploy Prometheus/Grafana/Loki stack
- [ ] Configure database exporters
- [ ] Set up Grafana dashboards
- [ ] Configure Alertmanager

### Antigravity Session Sync (IN PROGRESS)
- [ ] Build sync agent using local API (port 58575)
- [ ] Convert .pb files via GetCascadeTrajectory endpoint
- [ ] Ingest new sessions to CR with deduplication
- [x] Created generate_embeddings.py script
- [ ] Run embedding generation (4974 messages, 0 with embeddings)

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

## P2: Next Up

### LibreChat Features
- [x] **Web Search (Tavily)** - Configured Jan 18
- [ ] **Memory** - Persistent context across chats
- [ ] **Artifacts** - Generative UI output
- [ ] **MCP Integration** - Connect to external tools

### Security
- [ ] **Build DHG Security Agent** (2 hrs)
  - Manage Cloudflare Access
  - Fetch analytics via GraphQL API

---

## P3: Video Content Pipeline

- [ ] Vimeo API Integration
- [ ] YouTube API Integration
- [ ] Video Ingestion Pipeline
- [ ] AI Clip Generation

---

## P4: Backlog

- [ ] Code Interpreter
- [ ] Claude Files API
- [ ] XMP Metadata (Visuals Agent)
- [ ] LibreChat to Registry Sync
- [ ] Upgrade Infisical CLI

---

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
