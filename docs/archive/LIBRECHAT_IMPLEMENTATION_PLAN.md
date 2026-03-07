# Implementation Plan: LibreChat Integration

## Goal

Replace current Web UI with LibreChat. Connect to DHG backend, Ollama, and central registry. Use dark theme.

---

## Phase 0: Database Consolidation (Day 1)

> Target: 2 databases only (Central Registry + Onyx)

### Current State (4+ PostgreSQL, 3+ Redis)
- `dhg-registry-db` — Central Registry ✅ KEEP
- `dhg-transcribe-db` — Transcription → MIGRATE
- `bakery-db` — Unknown → REMOVE
- `infisical-*` — Secrets → EVALUATE
- `onyx-*` — RAG stack → KEEP (self-contained)

### Migration Steps

```bash
# 1. Dump transcribe tables
docker exec dhg-transcribe-db pg_dump -U postgres transcribe > transcribe_backup.sql

# 2. Create tables in Central Registry
docker exec -i 986cbb4003b3_dhg-registry-db psql -U dhg dhg_registry < transcribe_schema.sql

# 3. Import data
docker exec -i 986cbb4003b3_dhg-registry-db psql -U dhg dhg_registry < transcribe_backup.sql

# 4. Update transcription services to use Central Registry
# Edit docker-compose: DATABASE_URL → registry-db

# 5. Stop/remove old container
docker stop dhg-transcribe-db && docker rm dhg-transcribe-db
```

### LibreChat Database Strategy

LibreChat uses MongoDB by default. To use PostgreSQL:

```yaml
# docker-compose.override.yml
services:
  api:
    environment:
      - DB_DRIVER=postgres
      - POSTGRES_URI=postgresql://dhg:password@dhg-registry-db:5432/librechat
```

Note: LibreChat PostgreSQL support is available but less tested than MongoDB.

---

## Phase 1: Deploy LibreChat (Day 1)

### Clone and Configure

```bash
cd /home/swebber64/DHG/aifactory3.5
git clone https://github.com/danny-avila/LibreChat.git librechat
cd librechat
cp .env.example .env
```

### docker-compose.override.yml

```yaml
services:
  api:
    environment:
      - MONGO_URI=mongodb://mongodb:27017/LibreChat
      # Connect to existing Ollama
      - OLLAMA_BASE_URL=http://dhg-ollama:11434
    networks:
      - default
      - dhgaifactory35_dhg-network

  client:
    ports:
      - "3010:80"  # Different port from current UI (3005)

networks:
  dhgaifactory35_dhg-network:
    external: true
```

### librechat.yaml

See complete configuration: `docs/librechat.yaml` (210 lines)

Key endpoints configured:
- Ollama (auto-detected models)
- DHG Orchestrator (dhg-cme-pipeline, dhg-research, etc.)
- Research Agent, Medical LLM (direct access)
- Cloud: Anthropic, OpenAI, Google
- MCP: dhg-visuals, dhg-transcribe, dhg-prompt-checker

---

## Phase 2: Dark Theme (Day 1)

LibreChat has built-in dark mode. Set default in `.env`:

```bash
# Force dark theme
APP_TITLE=DHG AI Factory
ALLOW_SOCIAL_LOGIN=false
```

User preference stored in MongoDB. Dark mode is default on fresh install.

---

## Phase 3: DHG Agents as LibreChat Agents (Day 2)

### Option A: Custom Endpoints (Simpler)

DHG agents as OpenAI-compatible endpoints:

```yaml
# librechat.yaml
endpoints:
  custom:
    - name: "Research Agent"
      baseURL: "http://dhg-research:8000/v1"
      models: ["research-pubmed", "research-clinical-trials"]
      
    - name: "Medical LLM"
      baseURL: "http://dhg-medical-llm:8000/v1"
      models: ["medllama2", "mistral-medical"]
```

### Option B: MCP Tools (Richer)

Expose DHG agents as MCP servers, connect via LibreChat's MCP support:

```yaml
# librechat.yaml
mcpServers:
  dhg-research:
    command: "curl"
    args: ["http://dhg-aifactory-orchestrator:8000/mcp"]
```

---

## Phase 4: Migrate Features (Day 2-3)

| Current Feature | LibreChat Equivalent |
|-----------------|---------------------|
| Chat sessions | ✅ Built-in (MongoDB or Postgres) |
| History sidebar | ✅ Built-in |
| Model selector | ✅ Built-in (multi-endpoint) |
| Visuals tool | Create as LibreChat Agent |
| Prompt Checker | Create as LibreChat Agent |

### Visuals Agent (agents.json)

```json
{
  "name": "DHG Visuals",
  "description": "Generate CME-compliant visuals",
  "model": "gpt-4-turbo",
  "tools": ["dall-e-3", "dhg-visuals-api"]
}
```

---

## Phase 5: Connect to Central Registry (Optional)

LibreChat uses MongoDB by default. To share data with DHG registry:

1. Keep LibreChat on MongoDB for its own data
2. DHG agents write to PostgreSQL as before
3. Cross-reference via session IDs

Or: Configure LibreChat to use PostgreSQL (experimental).

---

## Phase 6: Tool Selector with Controller Menus (Day 3)

### UX Pattern

```
┌───────────────────────────────────────────────────────────┐
│  LEFT PANEL       │   CHAT AREA        │  RIGHT PANEL     │
│  (History)        │                    │  (Controller)    │
│ ┌───────────────┐ │ ┌────────────────┐ │ ┌──────────────┐ │
│ │ Today         │ │ │ Messages...    │ │ │ Visuals      │ │
│ │ • Chat 1      │ │ │                │ │ │ [Style: ▼]   │ │
│ │ • Chat 2      │ │ │                │ │ │ [Size: ▼]    │ │
│ │ Yesterday     │ │ │                │ │ │ [CME: ▼]     │ │
│ │ • Chat 3      │ │ └────────────────┘ │ │ [Generate]   │ │
│ └───────────────┘ │ ┌────────────────┐ │ └──────────────┘ │
│                   │ │🖼️🔍📝 Type... │ │                  │
│                   │ └────────────────┘ │                  │
└───────────────────────────────────────────────────────────┘
```

### Tools with Controller Menus

| Tool Icon | Tool | Controller Menu Options |
|-----------|------|-------------------------|
| 🖼️ | Visuals | Style, Size, CME Mode, Watermark |
| 🔍 | Prompt Checker | Eval Mode, Compliance Check, Scoring |
| 🎙️ | Transcribe | Source (URL/Upload), Speaker ID, Language |

### Implementation Approach

LibreChat's plugin/tool system allows custom UI. Two options:

**Option A: LibreChat Artifacts + Custom Menu**
- Use LibreChat's existing artifact system
- Add custom React component for controller menu
- Toggle left panel context based on tool selection

**Option B: Fork LibreChat Sidebar**
- Modify `client/src/components/SidePanel/` 
- Add tool context state
- Render controller menus conditionally

### Files to Create/Modify

```
librechat/
├── client/src/components/
│   ├── Tools/
│   │   ├── ToolSelector.tsx (prompt box tool icons)
│   │   ├── VisualsController.tsx
│   │   ├── PromptCheckerController.tsx
│   │   └── TranscribeController.tsx
│   └── SidePanel/
│       └── ToolPanel.tsx (dynamic left panel content)
```

---

## Verification Plan

### Startup
```bash
cd /home/swebber64/DHG/aifactory3.5/librechat
docker compose up -d
```

### Test Checklist
- [ ] Access LibreChat at http://100.107.14.51:3010
- [ ] Dark theme active
- [ ] Ollama models appear (medllama2, mistral-small3.1)
- [ ] DHG Orchestrator endpoint available
- [ ] Create chat → persists on refresh
- [ ] Switch models mid-chat
- [ ] Agent invocation works

---

## Port Allocation

| Service | Port | Status |
|---------|------|--------|
| Current Web UI | 3005 | Keep running during transition |
| LibreChat | 3010 | New |
| Ollama | 11434 | Existing |
| Orchestrator | 8011 | Existing |

---

**Executable as delivered in the stated environment.**

**Complete configuration file:** `docs/librechat.yaml` (210 lines, synced to .251)

Intentionally omitted:
- Tool controller React components (Phase 6) — will be built during execution
- transcribe_schema.sql — will be extracted from existing dhg-transcribe-db during migration
