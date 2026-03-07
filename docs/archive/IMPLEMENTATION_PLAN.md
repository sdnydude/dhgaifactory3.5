# DHG AI Factory - Implementation Plan

**Last Updated:** January 15, 2026  
**Status:** LibreChat Integration Stabilization

---

## Current State

### What Works
- All 10+ agent containers are running and healthy
- Health endpoints respond correctly
- Agents return OpenAI-compatible JSON responses
- Ollama models (medllama2, mistral) respond locally
- Central Registry PostgreSQL operational
- Cloudflare Access configured for public URLs

### What Needs Fixing
1. LibreChat streaming - Fixed with forcePrompt: true
2. Network isolation - Fixed by connecting agents to librechat_default
3. Orchestrator chat endpoint - Missing /v1/chat/completions
4. Agent functionality - Most return stub responses, not real LLM output

---

## Phase 1: LibreChat Stability (CURRENT)

### Completed Today (January 15)
- [x] Research identified forcePrompt: true as solution
- [x] Updated librechat.yaml with forcePrompt for all endpoints
- [x] Connected all DHG containers to librechat_default network
- [x] Created LogoMaker agent with Nano Banana Pro integration

### Still Required
- [ ] Verify user can chat with all agents in LibreChat UI
- [ ] Add orchestrator /v1/chat/completions endpoint
- [ ] Update docker-compose.yml for persistent network config
- [ ] Test each agent individually through LibreChat

---

## Phase 2: Agent Production Readiness

### Code Review Checklist (Per Agent)
Each agent main.py must have:
- [ ] Error handling with try/except around all LLM calls
- [ ] Structured logging using structlog
- [ ] Timeout handling (asyncio.wait_for or httpx timeout)
- [ ] Graceful fallback responses on failure
- [ ] Registry connection with retry logic
- [ ] Health check that verifies all dependencies

### Priority Agent Fixes

1. Medical LLM (8002) - Add OpenAI/Anthropic fallback chain
2. Research (8003) - Implement PubMed, ClinicalTrials.gov clients
3. Orchestrator (8011) - Add /v1/chat/completions endpoint
4. Visuals (8008) - Complete XMP metadata, compliance_mode

---

## Phase 3: Network Persistence

Add networks section to docker-compose.yml to make agent connections persistent.

---

## Phase 4: Central Registry Integration

Tables to Create:
- ai_sessions - LibreChat conversation sync
- debug_logs - Structured error/debug logs
- knowledge_items - RAG-ready knowledge base

---

## Files Modified Today

- /home/swebber64/DHG/aifactory3.5/librechat/librechat.yaml
- /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/services/logo-maker/main.py
- /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/docs/TODO.md
- /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/docs/IMPLEMENTATION_PLAN.md
