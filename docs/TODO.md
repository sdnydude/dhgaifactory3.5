# DHG AI Factory - Master TODO

**Updated:** January 14, 2026
**Status:** 🟢 LibreChat + 11 Agents Running, CR Integration Next

---

## ✅ Completed

### Infrastructure
- [x] LibreChat deployed on .251 (port 3010)
- [x] 11 Docker containers healthy
- [x] PostgreSQL Central Registry (18 tables)
- [x] LangGraph checkpointing working
- [x] Ollama medllama2 + mistral connected
- [x] Git branch: `feature/librechat-integration`

### OpenAI-Compatible Endpoints (All 7 Agents)
- [x] DHG Medical LLM — `/v1/chat/completions`
- [x] DHG Research — `/v1/chat/completions`
- [x] DHG Curriculum — `/v1/chat/completions`
- [x] DHG Outcomes — `/v1/chat/completions`
- [x] DHG Competitor-Intel — `/v1/chat/completions`
- [x] DHG QA-Compliance — `/v1/chat/completions`
- [x] DHG Visuals — `/v1/chat/completions`

### Infisical Secret Vault
- [x] Organization: Digital Harmony Group
- [x] Project: DHG AI Factory
- [x] Environments: Dev, Staging, Production
- [x] Folders: database, llm-providers, research-apis, observability, infrastructure
- [x] Machine Identity: cli-setup (Universal Auth)

---

## 🔴 P0: Central Registry Integration (NEW)

> All session data, debug logs, and knowledge stored in PostgreSQL for RAG

- [ ] Create `ai_sessions` table
- [ ] Create `debug_logs` table
- [ ] Create `session_files` table (with embeddings)
- [ ] Create `knowledge_items` table
- [ ] Build session-logger service
- [ ] Configure Onyx RAG connector to CR
- [ ] Sync LibreChat conversations to CR (MongoDB → PostgreSQL sync)

---

## 🔴 P0.5: Database Consolidation

- [ ] Migrate `dhg-transcribe-db` to Central Registry
- [ ] Remove `bakery-db`
- [ ] Evaluate Infisical DB consolidation
- [ ] Add LibreChat → CR sync service (MongoDB stays, data synced)

---

## 🟠 P1: Distributed GPU Setup

| Machine | GPU | Status |
|---------|-----|--------|
| .251 (Ubuntu) | RTX 5080 | ✓ Running |
| ASUS Laptop | RTX 5090 | [ ] Pending |
| Ubuntu PC | RTX 4080 | [ ] Pending |
| ProArt Creator | RTX 5080 | [ ] Pending |

### Next Steps
- [ ] Install Ollama on ASUS Laptop (WSL2)
- [ ] Add to Tailscale, update librechat.yaml
- [ ] Install ComfyUI on Ubuntu PC
- [ ] Update Visuals agent for remote ComfyUI

---

## 🟡 P2: Agent Enhancements

- [ ] Research Agent — Connect PubMed, ClinicalTrials.gov APIs
- [ ] Competitor-Intel — Web scrapers for ACCME/Medscape
- [ ] Medical LLM — Cloud fallbacks (OpenAI, Anthropic)
- [ ] QA-Compliance — Registry audit trail logging
- [ ] Visuals — XMP metadata, compliance_mode selector

---

## 🟢 P3: MCP Tools

- [ ] Visuals `/mcp` endpoint
- [ ] Transcribe `/mcp` endpoint
- [ ] Prompt Checker `/mcp` endpoint

---

## 🔵 P4: Demo & Validation

- [ ] Test multi-model switching in LibreChat
- [ ] Test agent invocation via custom endpoints
- [ ] Verify LangSmith traces
- [ ] Record demo video

---

## Finalized Decisions

- [x] LibreChat as primary UI
- [x] All agents in code (not Agent Builder)
- [x] MCP integration enabled
- [x] Shared Central Registry (PostgreSQL + pgvector)
- [x] Distributed GPU across 4 machines
- [x] Infisical for secret management
- [x] All sessions/debug data to Central Registry for RAG
