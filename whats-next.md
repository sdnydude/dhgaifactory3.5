# Session Handoff — 2026-03-12 (Session 5: Database Schema & Compliance Storage)

**Date:** 2026-03-12 ~14:00 UTC
**Branch:** `feature/langgraph-migration`
**Last Commit:** `5aeb0aa` (no new commit yet — all changes are uncommitted)

---

<original_task>
Continue from Session 4 handoff: monitor running pipeline, fix P1 UI bugs, then proceed with
audit/review/debug/refactor cycle. User pivoted mid-session to building a comprehensive database
schema for storing all CME pipeline outputs, intake fields, source references, and compliance
materials — with 7-year ACCME retention, full-text search, vector embeddings for RAG, and
structured extraction from JSONB blobs.
</original_task>

<work_completed>

## 1. Pipeline Monitoring & Quick Fixes

### Pipeline Status
- Thread `146808b7-0359-4971-ad5d-4b7b76361254` completed 6 agents: research, clinical, gap_analysis, learning_objectives, needs_assessment, prose_quality_pass_1
- **Failed at prose quality gate** — score 85/100, needs_assessment word count 1696 (below 3100 threshold). Retried 3 times then escalated to `failed_human_intervention_required`. This is correct behavior — quality gate is working.

### Badge Polling 422 Fix
- **File:** `frontend/src/hooks/use-badge-polling.ts` line 18
- **Change:** `limit: 0` → `limit: 100` (Cloud API rejects limit:0)

### Agent Name Mismatch Fix
- **File:** `frontend/src/app/projects/[id]/page.tsx` line 76-78
- **Change:** Output matching now checks both `o.agent_name === selectedStep` (short name) and `o.agent_name === selectedStepDef?.agent` (full name)
- **File:** `frontend/src/components/projects/document-card.tsx` lines 7-30
- **Change:** `AGENT_LABELS` map now includes both short names (`research`) and full names (`research_agent`) as keys

### Auto-Sync in Pipeline Status Endpoint
- **File:** `registry/cme_endpoints.py` — `get_cme_pipeline_status()` endpoint
- **Change:** When project is processing/review and has a pipeline_thread_id, auto-syncs from Cloud on each poll. Frontend polls every 10s, so registry stays current automatically.

## 2. Database Schema (Phase 1 — COMPLETE)

### New Tables Created in PostgreSQL

**`cme_documents`** (21 columns, 8 indexes)
- Immutable, versioned compliance documents with 7-year retention
- `ON DELETE RESTRICT` on project_id (prevents accidental deletion)
- Columns: id, project_id, agent_output_id, document_type, version, is_current, title, content_text, content_html, content_json, word_count, quality_score, quality_passed, quality_details, embedding vector(768), search_vector tsvector, source_references, created_by, retention_until, is_archived, created_at
- Indexes: project, type, current (partial), search (GIN), embedding (HNSW), retention (partial), content_json (GIN)
- Auto-update trigger on search_vector

**`cme_intake_fields`** (10 columns, 6 indexes)
- Structured extraction of 47 intake fields across 10 sections
- Columns: id, project_id, section, field_name, field_label, value_text, value_json, search_vector, created_at, updated_at
- Unique constraint: (project_id, section, field_name)
- Auto-update trigger on search_vector

**`cme_source_references`** (16 columns, 6 indexes)
- PubMed citations with cached content for compliance
- Columns: id, project_id, document_id, ref_type, ref_id, title, authors, journal, publication_date, url, abstract, embedding vector(768), search_vector tsvector, accessed_at, cached_content JSONB, created_at
- Auto-update trigger on search_vector

### Existing Table Updates

**`cme_agent_outputs`** — 3 new columns added:
- `document_text TEXT` — extracted prose from agent output JSONB
- `embedding vector(768)` — nomic-embed-text via Ollama
- `search_vector tsvector` — auto-updated by trigger
- New indexes: GIN on search_vector, HNSW on embedding, trigram on document_text, unique on (project_id, agent_name)

### Extensions Enabled
- `pg_trgm` — fuzzy text search (was already: `vector` 0.8.1)

## 3. SQLAlchemy Models (Phase 1 — COMPLETE)

**File:** `registry/models.py`
- Added `from pgvector.sqlalchemy import Vector` and `TSVECTOR` imports
- Added `pgvector==0.3.6` to `registry/requirements.txt`
- New model: `CMEDocument` — full column mapping including Vector(768), TSVECTOR
- New model: `CMEIntakeField` — with UniqueConstraint
- New model: `CMESourceReference` — full column mapping including Vector(768)
- Updated `CMEAgentOutput` — added `document_text`, `embedding`, `search_vector` columns
- Updated `CMEProject` — added relationships to `documents`, `intake_fields`, `source_references`

## 4. Sync & Extraction Logic (Phase 2 — COMPLETE)

**File:** `registry/cme_endpoints.py` — major rewrite of sync section (~543 lines added)

### New Constants
- `AGENT_OUTPUT_KEYS` expanded: added `prose_quality_pass_1`, `prose_quality_pass_2`, `compliance_result`
- `AGENT_OUTPUT_META` — maps state key → (short name, document title)
- `DOCUMENT_TEXT_PATHS` — maps agent name → JSONB path to prose document
- `REPORT_PATHS` — maps agent name → JSONB path to structured report
- `CITATION_PATHS` — maps agent name → JSONB path to citations list

### New Functions
- `_extract_document_text(agent_name, content)` — pulls prose from each agent's specific JSONB path
- `_extract_quality_score(agent_name, content)` — normalizes to 0-1 scale per agent type
- `_extract_quality_details(agent_name, content)` — structured quality metrics
- `_extract_word_count(agent_name, content)` — from metadata or counted from text
- `_extract_citations(agent_name, content)` — PubMed citations from research/clinical agents
- `_extract_intake_fields(project_id, intake_jsonb, db)` — explodes 10-section JSONB into 47 individual rows with proper labels
- `_generate_embedding(text)` — calls Ollama nomic-embed-text via `http://dhg-ollama:11434/api/embeddings`

### Rewritten `_sync_project_from_thread()` (now async)
Now populates ALL tables on each sync:
1. `cme_agent_outputs` — with document_text and quality_score
2. `cme_documents` — versioned, immutable, with word_count and quality_details
3. `cme_source_references` — PubMed citations with cached_content
4. `cme_intake_fields` — extracted once per project
5. Generates embeddings for all three vector-enabled tables
All callers updated to `await` the now-async function.

## 5. Backfill Verification (Phase 2 — COMPLETE)

Test project `861ce1b2-a88c-4cfa-9d05-4d4591c39724` ("Advances in Immunotherapy for NSCLC"):

| Table | Rows | Embeddings | Text Extracted |
|-------|------|------------|----------------|
| cme_agent_outputs | 6 | 6/6 | 6/6 |
| cme_documents | 6 | 6/6 | 6/6 |
| cme_intake_fields | 48 | N/A | 45/48 |
| cme_source_references | 89 | 89/89 | 89/89 |

Documents stored with 7-year retention (retention_until = 2033-03-12).

## 6. Planning Files Created
- `task_plan.md` — 6-phase plan with decision log
- `findings.md` — intake field structure (47 fields), agent output schemas (11 agents), extraction paths
- `progress.md` — session log with completed/in-progress/blocked items

</work_completed>

<work_remaining>

## Immediate: Commit This Work
1. **Git commit** all changes (7 files, ~920 lines added)
2. **Push to `feature/langgraph-migration`** for Cloud deployment

## Phase 4: Search & RAG Endpoints (NOT STARTED)
3. **Full-text search endpoint** — `GET /api/cme/search?q=...&type=...` using PostgreSQL ts_query across cme_documents, cme_intake_fields, cme_source_references
4. **Vector similarity endpoint** — `POST /api/cme/search/similar` — embed query → cosine similarity on pgvector columns
5. **Hybrid search endpoint** — `POST /api/cme/search/hybrid` — combines full-text + vector + metadata filters with reciprocal rank fusion
6. **RAG context endpoint** — `POST /api/cme/rag/context` — returns relevant chunks for LLM context, supports project scoping

## Phase 5: Frontend Integration (NOT STARTED)
7. **Update project detail page** — show documents from cme_documents (versioned), source references, quality metrics
8. **Add search page** — global search across all CME data with filters and preview snippets
9. **Wire review functions** — `submitForReview()` and `submitReview()` exist in registryApi.ts but no UI components call them yet

## Phase 6: Verification & Compliance (NOT STARTED)
10. **Retention verification** — confirm ON DELETE RESTRICT works, retention_until is correct
11. **Data completeness** — verify all 47 intake fields, all agent outputs, all citations
12. **Search quality** — test full-text and vector search accuracy

## From Session 4 (Still Outstanding)
13. **Fix `submitForReview()` UI wiring** — needs component to call it
14. **Fix `submitReview()` UI wiring** — needs reviewer_email param
15. **Error feedback for pipeline failures** — frontend should show failure reason, not just "processing"
16. **Verify app.digitalharmonyai.com** — proxy through Cloudflare tunnel
17. **Audit cycle** — /code-health → /debt-analysis → /review → /audit → /deploy-validate

</work_remaining>

<attempted_approaches>

### Docker exec heredoc doesn't work
- Multiple attempts to run multi-statement SQL via `docker exec psql` with heredocs failed silently
- **Fix:** Run each SQL statement as a separate `docker exec psql -c "..."` command
- This is a shell escaping issue with heredocs inside docker exec

### Ollama localhost:11434 unreachable from container
- First attempt at embedding generation used `http://localhost:11434/api/embeddings`
- Registry container can't reach localhost — Ollama is `dhg-ollama` on Docker network
- **Fix:** Changed to `os.getenv('OLLAMA_URL', 'http://dhg-ollama:11434')`

### SQLAlchemy model missing pgvector Vector type
- First sync attempt after adding embedding logic failed: `type object 'CMEAgentOutput' has no attribute 'embedding'`
- The `embedding` column existed in DB but not in the ORM model
- **Fix:** Added `pgvector==0.3.6` to requirements.txt, imported `from pgvector.sqlalchemy import Vector`, mapped all embedding columns as `Column(Vector(768))`

### Container code not updating on restart
- `docker compose restart registry-api` doesn't pick up code changes — code is baked into image (no volume mounts)
- **Fix:** Must run `docker compose build --no-cache registry-api && docker compose up -d registry-api`

### _sync_project_from_thread became async
- After adding `_generate_embedding()` (which is async), the sync function needed to become async
- All 3 callers needed `await` added: sync endpoint, sync-active endpoint, auto-sync in get_pipeline_status

</attempted_approaches>

<critical_context>

## Architecture Decisions Made This Session

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | `ON DELETE RESTRICT` for compliance tables | 7-year ACCME retention — can't cascade-delete CME materials |
| D2 | Immutable cme_documents (version, no update) | Compliance audit trail — new version = new row |
| D3 | nomic-embed-text (768 dims) via Ollama | Already running on server at dhg-ollama:11434 |
| D4 | HNSW index (not IVFFlat) | Better for small datasets, no training data needed |
| D5 | JSONB kept alongside structured extraction | Belt and suspenders — structured for queries, JSONB as source of truth |
| D6 | RAG from central registry, NOT RAGFlow | Single source of truth, no sync needed, compliance in one place |
| D7 | Separate cme_documents from cme_agent_outputs | Documents are compliance artifacts; agent outputs are pipeline state |

## Key File Locations (New/Modified This Session)

| File | Purpose |
|------|---------|
| `registry/models.py` | 3 new models: CMEDocument, CMEIntakeField, CMESourceReference |
| `registry/cme_endpoints.py` | Full extraction/sync/embedding pipeline (~543 new lines) |
| `registry/requirements.txt` | Added pgvector==0.3.6 |
| `frontend/src/hooks/use-badge-polling.ts` | Fixed limit:0 → limit:100 |
| `frontend/src/app/projects/[id]/page.tsx` | Fixed output matching for short/full agent names |
| `frontend/src/components/projects/document-card.tsx` | Added short agent name labels |
| `task_plan.md` | 6-phase plan with decision log |
| `findings.md` | All intake fields, agent output schemas, extraction paths |
| `progress.md` | Session progress tracking |

## Document Text Extraction Paths (CRITICAL for sync)

| Agent | State Key | Text Path |
|-------|-----------|-----------|
| Research | research_output | .research_document |
| Clinical | clinical_output | .clinical_practice_document |
| Gap Analysis | gap_analysis_output | .gap_analysis_document |
| Needs Assessment | needs_assessment_output | .complete_document |
| Learning Objectives | learning_objectives_output | .learning_objectives_document |
| Curriculum | curriculum_output | .curriculum_document |
| Protocol | protocol_output | .protocol_document |
| Marketing | marketing_output | .marketing_document |
| Grant Package | grant_package_output | .complete_document_markdown |
| Prose Quality | prose_quality_pass_1/2 | .summary |
| Compliance | compliance_result | built from .compliance_report |

## Embedding Infrastructure
- Model: nomic-embed-text (768 dimensions, 8192 token context)
- Endpoint: `http://dhg-ollama:11434/api/embeddings` (Docker network name)
- Truncation: 32000 chars (~8000 tokens)
- Stored in: vector(768) columns on cme_agent_outputs, cme_documents, cme_source_references
- Index: HNSW with vector_cosine_ops

## Container Rebuild Required
Registry has NO volume mounts — code is baked into Docker image. Any code change to `registry/` requires:
```bash
docker compose build --no-cache registry-api && docker compose up -d registry-api
```

## Database Status
- 9 CME tables total (6 existing + 3 new)
- pg_trgm extension enabled
- pgvector 0.8.1
- All triggers and indexes active
- Test project fully populated across all tables

</critical_context>

<current_state>

## Git State
- Branch: `feature/langgraph-migration`
- **7 files modified, NOT committed** (~920 lines added)
- Last commit: `5aeb0aa`
- mintify/ directory untracked

## What's Working
- Registry API running with full sync pipeline (just rebuilt)
- All 4 CME tables populated for test project (6 outputs, 6 documents, 48 intake fields, 89 references)
- All 101 embeddings generated (6+6+89)
- Auto-sync on pipeline status poll
- Badge polling fixed (no more 422s)
- Agent name matching fixed in frontend

## What's Not Working
- No search/RAG endpoints yet (Phase 4)
- Review UI not wired to API functions
- Pipeline failed at quality gate (expected — needs higher word count in needs_assessment)
- Inbox shows empty (correct — no interrupted threads, pipeline failed not interrupted)

## What Needs Immediate Attention
1. Commit and push these changes
2. Build search/RAG endpoints (Phase 4 of task_plan.md)
3. Wire frontend to show documents and search results

## User's Stated Priorities
- All CME documents stored in central registry with every field
- 7-year ACCME compliance retention
- Search and RAG from registry (NOT RAGFlow)
- Audit/review cycle still pending from Session 4

</current_state>
