# DHG AI Factory - Master To-Do List
**Last Updated:** Jan 20, 2026

## System Status
- **Running Containers:** 40
- **Stopped Containers:** 14 (Onyx kept 60 days, Whisper stopped for GPU)
- **Key Services:** All healthy

---

## P0: Blockers - CLEAR

No blockers.

---

## P1: This Sprint

### LibreChat Features (In Progress)
- [x] **Web Search (Tavily)** - Configured Jan 18
- [ ] **Memory** - Persistent context across chats
- [ ] **Artifacts** - Generative UI output
- [ ] **MCP Integration** - Connect to external tools

### Security
- [ ] **Build DHG Security Agent** (2 hrs)
  - Manage Cloudflare Access (add/remove users)
  - Fetch analytics via GraphQL API
  - Ingest data into Registry

### LibreChat Enhancements
- [ ] **Slash Commands** - /security, /dhg-style
- [ ] **Footer Links** - Docs, Status, Admin
- [ ] **Publish Google OAuth App** - Allow external users

### RAG Platform
- [ ] **Install LangFlow** - Port :7860
- [ ] **Install OpenRAG** - Port :8090

---

## P2: Video Content Pipeline

- [ ] Vimeo API Integration
- [ ] YouTube API Integration
- [ ] Video Ingestion Pipeline
- [ ] AI Clip Generation
- [ ] Install Clapshot
- [ ] Transcript-Based Editing
- [ ] Install Mixpost

---

## P3: Creator Harmony Platform

- [ ] Define Content Production Agents
- [ ] Project Creation Flow
- [ ] Deliverable Generation
- [ ] Creator Harmony Dashboard

---

## P4: Backlog

- [ ] Code Interpreter (waiting for self-hosted option)
- [ ] Claude Files API (beta header)
- [ ] Claude Skills API (beta header)
- [ ] Local Whisper for LibreChat STT
- [ ] XMP Metadata (Visuals Agent)
- [ ] pgvector Embeddings
- [ ] LibreChat to Registry Sync
- [ ] Upgrade Infisical CLI to v0.155.5

---

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
