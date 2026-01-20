# DHG AI Factory - Master To-Do List
**Last Updated:** Jan 20, 2026

## System Status
- **Running Containers:** 38
- **Stopped Containers:** 16 (Onyx kept 60 days, Whisper stopped for GPU, web-ui stopped)
- **Key Services:** All healthy
- **Code Audit:** Passed (Jan 20)

---

## P0: Blockers - CLEAR

No blockers.

---

## P1: This Sprint

### CME Pipeline Endpoints (Priority Order Per Workflow)

**Step 1: Research Agent** (first in pipeline)
- [x] /sources/perplexity/query - Perplexity integration ✓ Jan 20
- [ ] /sources/pubmed/query - PubMed integration
- [ ] /sources/status - Check source availability
- [ ] /validate-url - URL validation
- [ ] /cache/stats - Cache statistics
- [ ] /cache/clear - Clear cache

**Step 2: Curriculum Agent** (core CME design)
- [ ] /design - Full curriculum design
- [ ] /objectives/generate - Learning objectives
- [ ] /map - Objective mapping to Moore/ICD-10/QI
- [ ] /outline - Activity outline
- [ ] /faculty-brief - Instructor brief
- [ ] /assessment - Assessment design
- [ ] /templates - Template retrieval

### LibreChat Features
- [x] **Web Search (Tavily)** - Configured Jan 18
- [x] **Memory** - Enabled Jan 20 (Claude backend)
- [x] **MCP Integration** - Enabled Jan 20
- [ ] **Artifacts** - Verify CSP headers

### Security
- [ ] **Build DHG Security Agent** (2 hrs)

### LibreChat Enhancements
- [ ] **Slash Commands** - /security, /dhg-style
- [ ] **Footer Links** - Docs, Status, Admin
- [ ] **Publish Google OAuth App**

### Pending API Keys
- [ ] **Consensus API** - Application submitted, awaiting approval

---

## P2: Support Agent Endpoints

**Competitor Intel Agent** (not in main pipeline, support/optional)
- [ ] /analyze/competitive
- [ ] /extract/activities
- [ ] /analyze/differentiation
- [ ] /intelligence
- [ ] /validate
- [ ] /providers
- [ ] /funders
- [ ] /activities/period
- [ ] /monitoring
- [ ] /search

**Orchestrator**
- [ ] /registry/log

---

## P3: Video Content Pipeline

- [ ] Vimeo API Integration
- [ ] YouTube API Integration
- [ ] Video Ingestion Pipeline
- [ ] AI Clip Generation
- [ ] Install Clapshot
- [ ] Transcript-Based Editing
- [ ] Install Mixpost

---

## P4: Creator Harmony Platform

- [ ] Define Content Production Agents
- [ ] Project Creation Flow
- [ ] Deliverable Generation
- [ ] Creator Harmony Dashboard

---

## P5: Backlog

- [ ] Install LangFlow (Port :7860)
- [ ] Install OpenRAG (Port :8090)
- [ ] Cleanup: Move architect_agentV3.py to /docs/examples/
- [ ] Code Interpreter (waiting for self-hosted option)
- [ ] Claude Files API (beta header)
- [ ] Claude Skills API (beta header)
- [ ] Local Whisper for LibreChat STT
- [ ] XMP Metadata (Visuals Agent)
- [ ] pgvector Embeddings
- [ ] LibreChat to Registry Sync
- [ ] Upgrade Infisical CLI to v0.155.5

---

## Completed (Jan 20, 2026)

- [x] **Perplexity integration** in Research Agent
- [x] **Code Quality Audit** - Passed
- [x] Memory feature enabled (Claude backend)
- [x] MCP Servers enabled
- [x] Session-logger health check fixed (curl added)
- [x] Stopped web-ui containers (redundant with LibreChat)
- [x] Committed all outstanding changes (10 commits pushed)

## Completed (Jan 18-19, 2026)

- [x] Tavily Web Search configured (3 API keys saved)
- [x] LibreChat Google OAuth configured
- [x] qwen2.5:14b set as default Ollama model
- [x] Infisical CLI working (localhost:8089)
- [x] Cloudflare tokens saved to Infisical
- [x] eofranke@gmail.com added to Cloudflare Access
- [x] Stopped Onyx (11 containers, keeping 60 days)
- [x] Deleted UIBakery (8 containers)
- [x] All DHG agents configured in LibreChat (10)
- [x] Perplexity configured
- [x] pgAdmin running on :5050
- [x] Full features review completed

## Previously Completed

- [x] LibreChat custom endpoints
- [x] Anthropic/OpenAI/Google providers
- [x] MCP servers configured
- [x] 7 CME agents running
- [x] Transcription pipeline operational
- [x] Infisical secrets management
- [x] File upload + Speech TTS/STT
- [x] Registry database tables created
- [x] RAG API running
- [x] Meilisearch (conversation search)
