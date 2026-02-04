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
- [x] Update session-start workflow withagent compared t planning check
- [x] Test full pipeline: sync → embeddings → search (15 embeddings generated)

### Phase 3: Backend API (In Progress)
- [x] Refactor api.py - move Claude endpoints to claude_endpoints.py
- [x] Create cme_endpoints.py with /api/v2 prefix
- [x] Define all 47-field intake schemas (10 sections)
- [x] Create project CRUD endpoints
- [x] Create pipeline control endpoints (start/pause/resume/cancel)
- [x] Create webhook for LangGraph callbacks
- [x] Create database migration for cme_projects table (003_add_cme_projects.sql)

#### Phase 3.2: Database Integration ✅
- [x] Add SQLAlchemy ORM models to models.py
  - CMEProject model
  - CMEAgentOutput model
- [x] Remove in-memory store (_cme_projects dict)
- [x] Update 10 endpoints to use database:
  - [x] POST /api/v2/projects (create)
  - [x] GET /api/v2/projects (list)
  - [x] GET /api/v2/projects/{id} (get)
  - [x] POST /api/v2/projects/{id}/start
  - [x] GET /api/v2/projects/{id}/status
  - [x] POST /api/v2/projects/{id}/pause
  - [x] POST /api/v2/projects/{id}/resume
  - [x] POST /api/v2/projects/{id}/cancel
  - [x] GET /api/v2/projects/{id}/outputs
  - [x] GET /api/v2/projects/{id}/outputs/{agent}
  - [x] POST /api/v2/webhook/agent-complete
- [x] Rebuild registry-api container with new code
- [x] Verify data persists in PostgreSQL

#### Phase 3.3: CSV Import (Pending)
- [ ] Create POST /api/v2/projects/import endpoint
- [ ] CSV parsing and validation
- [ ] Column mapping to intake form fields
- [ ] Batch insert with error handling
- [ ] Frontend: File upload component in CME panel
- [ ] Template CSV download

#### Phase 3.4: HTTPS/SSL Setup (Pending)
- [ ] Determine subdomain for registry-api (e.g., api.digitalharmonyai.com)
- [ ] Set up Let's Encrypt/Certbot for SSL certificates
- [ ] Configure nginx reverse proxy with SSL termination
- [ ] Update frontend API URL to use HTTPS
- [ ] Test Mixed Content resolved

### Phase 3.5: LangGraph Agent Development (Complete)
**Approach:** Build and test agents one at a time
**First agent:** Needs Assessment

- [x] Build Needs Assessment agent in LangGraph
- [x] Test Needs Assessment agent standalone
- [x] Connect to pipeline orchestrator
- [x] Build remaining 11 agents incrementally:
  - [x] Research, Clinical, Gap Analysis, Learning Objectives
  - [x] Curriculum, Protocol, Marketing
  - [x] Grant Writer (Partially implemented)
  - [ ] Prose Quality, Compliance, Package Assembly

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

### Phase 6: Reporting & Multimodal (New)
#### Phase 6.1: Pixeltable Implementation (P2)
- [ ] Add `pixeltable` to `scripts/requirements.txt`
- [ ] Create Proof-of-Concept script `scripts/poc_pixeltable_video.py`
  - [ ] Ingest a dummy video from `swincoming/`
  - [ ] Extract frames and store in Postgres
- [ ] Evaluate for replacing current RAG ingestion pipeline

#### Phase 6.2: Observability Stack (P2)
- [ ] Prometheus/Grafana/Loki deployment
- [ ] Database exporters

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
