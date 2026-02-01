# Research Findings

## Key Discoveries

### LibreChat Architecture
- Side panel uses `useSideNavLinks.ts` hook to define navigation items
- Each NavLink has: title (i18n key), icon, Component, id
- Translation keys defined in `/client/src/locales/en/translation.json`
- Uses TypeScript with strict type checking on translation keys

### Docker Setup
- LibreChat runs via docker-compose on port 3010
- Image: `ghcr.io/danny-avila/librechat-dev:latest` (now custom `librechat-cme:latest`)
- Full rebuild takes ~17 minutes
- Container name: LibreChat

### Planning-with-Files Skill
- Located at `.agent/skills/planning-with-files/skills/planning-with-files/SKILL.md`
- Version 2.10.0 with hooks for PreToolUse, PostToolUse, Stop
- Includes session-catchup.py for recovery
- Manus-style "working memory on disk" approach

### 12-Agent CME Pipeline
- 12 specialized agents for CME grant generation
- Outputs: research, clinical, gap analysis, needs assessment, learning objectives, curriculum, protocol, marketing, grant package, prose quality, compliance
- Final deliverable: Complete grant package for pharma submission

## Technical Notes

### CME Panel Component Structure
- 10 sections (A-J) matching intake form schema
- React state for form data and navigation
- Progress bar showing completion
- Tailwind CSS for styling
- handleSubmit placeholder for API integration

### API Architecture (from docs)
**Existing:**
- Registry API on port 8011 (`dhg-registry-api`)
- FastAPI framework
- `/api/v1/projects` — Generic Claude project storage
- `/api/v1/agents` — Agent registry

**Per 12-Agent ARCHITECTURE.md (to implement):**
- `POST /api/v2/projects` — Create CME project (submit intake)
- `POST /api/v2/projects/{id}/start` — Trigger LangGraph pipeline
- `GET /api/v2/projects/{id}/status` — Execution status
- `GET /api/v2/projects/{id}/outputs` — Get agent outputs

**Implementation approach:**
1. Create `cme_endpoints.py` in registry/
2. Use `/api/v2/` prefix to separate from generic v1
3. Define Pydantic schemas for IntakeSubmission (10 sections)
4. Connect to LangGraph for pipeline execution

### Database Sync Architecture
- planning_documents table stores file content + metadata
- Content hashing prevents redundant syncs
- needs_embedding flag triggers embedding generation
- planning_embeddings table stores vectors for RAG

### Database Connection
- Registry DB runs in Docker as `dhg-registry-db`
- Exposed on localhost:5432
- .env uses `POSTGRES_HOST=registry-db` (Docker internal)
- Scripts must use `DB_HOST=localhost` when run from server host
- Credentials in .env: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB

### Embedding Pipeline
- Uses Ollama with nomic-embed-text model (768 dimensions)
- Chunks documents at ~500 chars with 50 char overlap
- Breaks at paragraph/sentence boundaries when possible
- Adds project/file context to chunks for better retrieval
- pgvector with IVFFlat index for similarity search

### System Architecture (Decided)
- **UI**: LibreChat (CME form, chat interface)
- **Agent Runtime**: LangGraph Cloud (12 CME agents — **need to build**)
- **Observability**: LangSmith (tracing)
- **Knowledge**: CR (pgvector) for structured, RAGFlow for research
- **Dify**: Not used for agents (LangGraph handles this)

**Agent Build Order:** Start with Needs Assessment, then add incrementally

### Prompt Library Systems
- LibreChat: Presets/system prompts
- Dify: Workflow prompts
- RAGFlow: Query prompts (if any)
- LangSmith: Agent prompts

**Decision**: CR (PostgreSQL) as single master, sync to all systems

### Prompt Sync Architecture
```
CR (prompts table) ──push──> LibreChat
                   ──push──> Dify
                   ──push──> LangSmith
```
- CR is source of truth
- One-way sync (not bidirectional)
- Version tracking in CR

## References
- LibreChat repo: `/home/swebber64/DHG/aifactory3.5/librechat/`
- CME Docs: `/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/DHG-CME-12-Agent-Docs/`
- Intake schema: `technical/intake-form-schema.yaml`
- Planning scripts: `scripts/sync_planning_files.py`, `generate_planning_embeddings.py`, `search_planning_docs.py`
- Dify: https://dify.digitalharmonyai.com/


