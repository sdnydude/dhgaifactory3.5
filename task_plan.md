# DHG AI Factory 3.5 - Task Plan

## Goal
Build CME Grant intake-to-pipeline system with unified knowledge and prompt management across LibreChat, LangGraph, and supporting services.

## Current Phase
Phase 3: Backend API — `pending`

## Phases

### Phase 1: CME Intake Panel Integration ✅
- [x] Analyze LibreChat panel architecture
- [x] Create CMEIntakePanel.tsx component (638 lines)
- [x] Add panel to useSideNavLinks.ts
- [x] Add i18n translation key
- [x] Build Docker image with CME panel
- [x] Update docker-compose.yml to use custom image
- [x] Restart LibreChat container
- [x] Verify panel accessible at http://10.0.0.251:3010

### Phase 2: Planning Infrastructure ✅
- [x] Create planning-with-files rule
- [x] Copy full skill to workflow
- [x] Create sync_planning_files.py script
- [x] Create planning-sync workflow
- [x] Create generate_planning_embeddings.py script
- [x] Create search_planning_docs.py script
- [x] Update session-start workflow with planning check
- [x] Test full pipeline: sync → embeddings → search (15 embeddings generated)

### Phase 3: Backend API (In Progress)
- [x] Refactor api.py - move Claude endpoints to claude_endpoints.py
- [x] Create cme_endpoints.py with /api/v2 prefix
- [x] Define all 47-field intake schemas (10 sections)
- [x] Create project CRUD endpoints
- [x] Create pipeline control endpoints (start/pause/resume/cancel)
- [x] Create webhook for LangGraph callbacks
- [x] Create database migration for cme_projects table (003_add_cme_projects.sql)

#### Phase 3.2: Database Integration (Current)
- [ ] Add SQLAlchemy ORM models to cme_endpoints.py
  - CMEProject model
  - CMEAgentOutput model
- [ ] Remove in-memory store (_cme_projects dict)
- [ ] Update 11 endpoints to use database:
  - [ ] POST /api/v2/projects (create)
  - [ ] GET /api/v2/projects (list)
  - [ ] GET /api/v2/projects/{id} (get)
  - [ ] POST /api/v2/projects/{id}/start
  - [ ] GET /api/v2/projects/{id}/status
  - [ ] POST /api/v2/projects/{id}/pause
  - [ ] POST /api/v2/projects/{id}/resume
  - [ ] POST /api/v2/projects/{id}/cancel
  - [ ] GET /api/v2/projects/{id}/outputs
  - [ ] GET /api/v2/projects/{id}/outputs/{agent}
  - [ ] POST /api/v2/webhook/agent-complete
- [ ] Restart registry-api container
- [ ] Test API endpoints with curl
- [ ] Test form submission from LibreChat
- [ ] Verify data persists in PostgreSQL

### Phase 3.5: LangGraph Agent Development (Pending)
**Approach:** Build and test agents one at a time
**First agent:** Needs Assessment

- [ ] Build Needs Assessment agent in LangGraph
- [ ] Test Needs Assessment agent standalone
- [ ] Connect to pipeline orchestrator
- [ ] Build remaining 11 agents incrementally:
  - Research, Clinical, Gap Analysis, Learning Objectives
  - Curriculum, Protocol, Marketing, Grant Writer
  - Prose Quality, Compliance, Package Assembly

### Phase 4: Prompt Library Sync (Pending)
- [ ] Create prompts table in CR (PostgreSQL)
- [ ] Build prompt sync script for LibreChat
- [ ] Build prompt sync script for Dify
- [ ] Build prompt sync script for LangSmith
- [ ] Create prompt management workflow
- [ ] Test sync: CR → LibreChat → Dify → LangSmith

### Phase 5: Knowledge Architecture (Pending)
- [ ] Define content routing: what goes where
- [ ] Planning files → CR (done)
- [ ] 12-Agent docs → CR or RAGFlow
- [ ] Medical literature → RAGFlow
- [ ] User uploads → LibreChat rag_api
- [ ] Build unified search across knowledge stores

## System Architecture

```
User → LibreChat (CME Form)
         ↓
    /api/v2/intake
         ↓
    LangGraph Cloud (12 agents)
         ↓                    ↓
    CR (pgvector)       RAGFlow
    (planning,          (medical
     prompts)            research)
         ↓
    LangSmith (traces)
         ↓
    Grant Package → LibreChat
```

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| Vite can't find @librechat/client | 1 | Need to build Docker image, not run dev server |
| SSL error on browser | 1 | Use http:// not https:// |
| Duplicate import in useSideNavLinks | 1 | Removed duplicate line |
| DB_HOST=registry-db not resolvable | 1 | Use DB_HOST=localhost from server (Docker exposes 5432) |

## Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| How to add panel to LibreChat | Docker rebuild | Production instance uses Docker |
| Planning workflow approach | Rule + workflow + database sync | Enables knowledge search across projects |
| API versioning | Start at v2 | Pre-launch, no backward compatibility needed |
| Agent runtime | LangGraph (not Dify) | All 12 agents already in LangGraph |
| Prompt library master | CR (PostgreSQL) | Single source, sync to LibreChat/Dify/LangSmith |
| Knowledge architecture | CR + RAGFlow | CR for structured, RAGFlow for research |
