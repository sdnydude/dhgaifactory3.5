# DHG AI Factory - Master TODO

**Updated:** January 14, 2026  
**Status:** 🟢 LibreChat Running, Distributed GPU Setup Needed

---

## ✅ Completed This Session

- [x] LibreChat deployed on .251 (port 3010)
- [x] Dark theme active
- [x] User registration working (swebber@fafstudios.com)
- [x] Ollama medllama2 connected and working
- [x] Ollama mistral-small3.1:24b connected and working
- [x] DHG Medical LLM OpenAI-compatible endpoint added (`/v1/chat/completions`)
- [x] LibreChat baseURL fix (removed trailing slashes)
- [x] dropParams added for DHG Medical LLM
- [x] Git branch created: `feature/librechat-integration`

---

## 🔴 P0: Complete LibreChat Integration

### Remaining YAML Fixes
- [ ] Fix all DHG endpoint baseURLs (remove trailing `/`)
- [ ] Add dropParams to all DHG endpoints
- [ ] Verify all endpoints connecting

### OpenAI-Compatible Endpoints (for LibreChat)
- [x] DHG Medical LLM — `/v1/chat/completions` added
- [ ] DHG Research — add endpoint
- [ ] DHG Orchestrator — add endpoint
- [ ] DHG Curriculum, Outcomes, Competitor-Intel, QA — add endpoints
- [ ] DHG Visuals — add endpoint

### MCP Tools (Phase 3)
- [ ] Visuals `/mcp` endpoint
- [ ] Transcribe `/mcp` endpoint
- [ ] Prompt Checker `/mcp` endpoint

---

## 🔴 P0.5: Distributed GPU Setup

### Hardware Fleet

| Machine | GPU | VRAM | Role |
|---------|-----|------|------|
| .251 (Ubuntu) | RTX 5080 | 16GB | Main stack, medllama2 |
| ASUS Laptop | RTX 5090 | 24GB | Large models (Mistral 24B) |
| Ubuntu PC | RTX 4080 | 16GB | ComfyUI, image gen |
| ProArt Creator | RTX 5080 | 16GB | Fast NVMe model storage |

### Setup Steps

#### 1. ASUS Laptop (RTX 5090) — For Mistral
- [ ] Install Ollama (WSL2 or Windows native)
- [ ] Configure `OLLAMA_HOST=0.0.0.0`
- [ ] Pull `mistral-small3.1:24b`
- [ ] Add to Tailscale network
- [ ] Get Tailscale IP
- [ ] Update librechat.yaml with remote Ollama URL

#### 2. LibreChat Multi-Ollama Config
```yaml
# librechat.yaml - Multiple Ollama instances
endpoints:
  custom:
    - name: "Ollama-Local"
      baseURL: "http://dhg-ollama:11434/v1"  # .251 - medllama2
    - name: "Ollama-5090"
      baseURL: "http://<5090-tailscale-ip>:11434/v1"  # Laptop - Mistral
```

#### 3. Ubuntu PC (RTX 4080) — For ComfyUI
- [ ] Install ComfyUI
- [ ] Configure SDXL / Flux models
- [ ] Expose API for Visuals agent
- [ ] Update Visuals agent to call remote ComfyUI

---

## 🟠 P1: Database Consolidation

- [ ] Migrate `dhg-transcribe-db` to Central Registry
- [ ] Remove `bakery-db`
- [ ] Evaluate `infisical-*` services
- [ ] Configure LibreChat for PostgreSQL (not MongoDB)

---

## 🟡 P2: Demo Validation

- [ ] Test multi-model switching in LibreChat
- [ ] Test session persistence
- [ ] Test agent invocation via custom endpoints
- [ ] Verify LangSmith traces
- [ ] Record demo video

---

## 🟢 P3: Agent Deployment (9 remaining)

- [ ] Scribe (content generation)
- [ ] Strategy, Discovery, Architect, Implementation, Deployment, QA-Manager

---

## Finalized Decisions

- [x] LibreChat as primary UI
- [x] All agents in code (not Agent Builder)
- [x] MCP integration enabled
- [x] Max 2-level subgraph depth
- [x] Shared central registry
- [x] Distributed GPU across 4 machines
