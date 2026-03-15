# Task Plan: CME Database Schema & Compliance Storage

**Date:** 2026-03-12
**Branch:** `feature/langgraph-migration`
**Goal:** Build production database schema that stores every intake field, every agent output field, source references, and document links — with 7-year ACCME compliance retention, full-text search, and RAG-ready vector embeddings.

---

## Phase 1: Database Schema Migration (CURRENT)

**Status:** IN PROGRESS
**Objective:** Create all tables, columns, indexes, and triggers needed for structured CME data storage.

### 1.1 Expand `cme_agent_outputs` table
- [x] Add `document_text TEXT` column (extracted prose for search)
- [x] Add `embedding vector(768)` column (nomic-embed-text via Ollama)
- [x] Add `search_vector tsvector` column (PostgreSQL full-text search)
- [ ] Add `pg_trgm` extension for fuzzy search
- [ ] Create GIN index on `search_vector`
- [ ] Create HNSW index on `embedding`
- [ ] Create trigram index on `document_text`
- [ ] Create unique index on `(project_id, agent_name)`
- [ ] Create auto-update trigger for `search_vector`

### 1.2 Create `cme_documents` table (compliance, 7-year retention)
- [ ] `id`, `project_id` (RESTRICT delete, not CASCADE)
- [ ] `agent_output_id` FK to `cme_agent_outputs`
- [ ] `document_type` (needs_assessment, research, gap_analysis, etc.)
- [ ] `version` (integer, for revision tracking)
- [ ] `is_current` (boolean, only one current per type per project)
- [ ] `title`, `content_text`, `content_html`, `content_json`
- [ ] `word_count`, `quality_score`, `quality_passed`, `quality_details`
- [ ] `embedding vector(768)`, `search_vector tsvector`
- [ ] `source_references JSONB` (PubMed IDs, URLs)
- [ ] `created_by`, `retention_until` (NOW + 7 years), `is_archived`
- [ ] Immutable — no `updated_at`, versions create new rows
- [ ] Indexes: project, type, current, search, embedding, retention, content_json

### 1.3 Create `cme_intake_fields` table (structured intake, not JSONB blob)
- [ ] `id`, `project_id` (RESTRICT delete)
- [ ] `section` (section_a through section_j)
- [ ] `field_name`, `field_label`
- [ ] `value_text`, `value_json` (complex values like arrays)
- [ ] `search_vector tsvector`
- [ ] Unique constraint on `(project_id, section, field_name)`
- [ ] Indexes: project, section, search

### 1.4 Create `cme_source_references` table (literature tracking)
- [ ] `id`, `project_id` (RESTRICT), `document_id` FK
- [ ] `ref_type` (pubmed, url, journal, guideline)
- [ ] `ref_id` (PubMed ID, DOI)
- [ ] `title`, `authors`, `journal`, `publication_date`, `url`, `abstract`
- [ ] `embedding vector(768)`, `search_vector tsvector`
- [ ] `accessed_at`, `cached_content JSONB` (full reference data for compliance)
- [ ] Indexes: project, type, ref_id, search, embedding

### 1.5 Update SQLAlchemy models in `registry/models.py`
- [ ] Add `CMEDocument` model matching `cme_documents` table
- [ ] Add `CMEIntakeField` model matching `cme_intake_fields` table
- [ ] Add `CMESourceReference` model matching `cme_source_references` table
- [ ] Add new columns to `CMEAgentOutput` model (document_text, embedding, search_vector)
- [ ] Add relationships on `CMEProject` to new models

---

## Phase 2: Sync & Extraction Logic

**Status:** NOT STARTED
**Objective:** When agents complete, extract structured data from JSONB into proper columns/tables.

### 2.1 Expand `AGENT_OUTPUT_KEYS` in `cme_endpoints.py`
- [ ] Add `prose_quality_pass_1`, `prose_quality_pass_2`, `compliance_result`
- [ ] Map each key to proper `document_type` for `cme_documents`

### 2.2 Build text extraction functions
- [ ] `_extract_document_text(agent_name, content_jsonb)` — pulls prose document from each agent's output
  - research: `content["research_document"]`
  - clinical: `content["clinical_practice_document"]`
  - gap_analysis: `content["gap_analysis_document"]`
  - needs_assessment: `content["complete_document"]`
  - learning_objectives: `content["learning_objectives_document"]`
  - curriculum: `content["curriculum_document"]`
  - protocol: `content["protocol_document"]`
  - marketing: `content["marketing_document"]`
  - grant_package: `content["complete_document_markdown"]`
  - prose_quality: `content["summary"]`
  - compliance: build from `content["compliance_report"]`

### 2.3 Build quality score extraction
- [ ] `_extract_quality_score(agent_name, content_jsonb)` — finds quality score at correct path
  - needs_assessment: `quality_passed` (bool) + `word_count`
  - prose_quality: `overall_score` (0-100)
  - compliance: `compliance_report.overall_verdict`

### 2.4 Build intake field extraction
- [ ] On project create/update, explode `intake` JSONB into `cme_intake_fields` rows
- [ ] 47 fields across 10 sections (see findings.md for full field list)

### 2.5 Build source reference extraction
- [ ] Parse `citations` arrays from research_agent and clinical_practice_agent outputs
- [ ] Extract PubMed IDs, titles, authors, journals
- [ ] Store in `cme_source_references` with `cached_content` for compliance

### 2.6 Update `_sync_project_from_thread()` to populate all new tables
- [ ] Store documents in `cme_documents` (versioned, immutable)
- [ ] Store extracted text in `cme_agent_outputs.document_text`
- [ ] Store intake fields in `cme_intake_fields`
- [ ] Store references in `cme_source_references`

---

## Phase 3: Embedding Generation

**Status:** NOT STARTED
**Objective:** Generate vector embeddings for all stored content using Ollama nomic-embed-text.

### 3.1 Build embedding utility
- [ ] `_generate_embedding(text: str) -> List[float]` — calls Ollama at localhost:11434
- [ ] Chunking strategy for long documents (nomic-embed-text context: 8192 tokens)
- [ ] Batch processing for multiple documents

### 3.2 Integrate into sync pipeline
- [ ] Generate embeddings for `cme_documents.embedding`
- [ ] Generate embeddings for `cme_agent_outputs.embedding`
- [ ] Generate embeddings for `cme_source_references.embedding`
- [ ] Run async to not block sync response

### 3.3 Backfill existing data
- [ ] Embed the 5 outputs already in the database for project 861ce1b2

---

## Phase 4: Search & RAG Endpoints

**Status:** NOT STARTED
**Objective:** Add API endpoints for full-text search, vector similarity, and hybrid search.

### 4.1 Full-text search endpoint
- [ ] `GET /api/cme/search?q=...&type=...` — PostgreSQL `ts_query` across all CME tables
- [ ] Returns ranked results from documents, intake fields, and references

### 4.2 Vector similarity endpoint
- [ ] `POST /api/cme/search/similar` — cosine similarity on embeddings
- [ ] Input: text query → embed → search
- [ ] Returns top-k similar documents/references

### 4.3 Hybrid search endpoint
- [ ] `POST /api/cme/search/hybrid` — combines full-text + vector + metadata filters
- [ ] Reciprocal rank fusion for score blending

### 4.4 RAG context endpoint
- [ ] `POST /api/cme/rag/context` — returns relevant chunks for LLM context window
- [ ] Supports project scoping (within-project vs. cross-project)

---

## Phase 5: Frontend Integration

**Status:** NOT STARTED
**Objective:** Wire search/document access into the Next.js frontend.

### 5.1 Update project detail page
- [ ] Show documents from `cme_documents` table (versioned)
- [ ] Show source references from `cme_source_references`
- [ ] Show quality metrics from extracted scores

### 5.2 Add search page
- [ ] Global search across all CME data
- [ ] Filters by project, document type, date range
- [ ] Preview snippets with highlighted matches

---

## Phase 6: Verification & Compliance

**Status:** NOT STARTED
**Objective:** Verify 7-year retention, search accuracy, and data completeness.

### 6.1 Retention verification
- [ ] Confirm `ON DELETE RESTRICT` prevents accidental project deletion
- [ ] Confirm `retention_until` is set correctly (NOW + 7 years)
- [ ] Verify immutable documents (no UPDATE trigger)

### 6.2 Data completeness check
- [ ] All 47 intake fields extracted for test project
- [ ] All 11 agent outputs stored with extracted text
- [ ] All citations stored as source references
- [ ] All documents have embeddings

### 6.3 Search quality check
- [ ] Full-text search returns relevant results
- [ ] Vector search returns semantically similar results
- [ ] Hybrid search outperforms either alone

---

## Decisions Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| D1 | Use `ON DELETE RESTRICT` for compliance tables | 7-year retention means we cannot cascade-delete CME materials when a project is removed | 2026-03-12 |
| D2 | Immutable `cme_documents` (version, no update) | Compliance requires audit trail of all document versions | 2026-03-12 |
| D3 | nomic-embed-text (768 dims) via Ollama | Already running on server, good balance of quality/speed | 2026-03-12 |
| D4 | HNSW index (not IVFFlat) | Better for small datasets, no training data needed | 2026-03-12 |
| D5 | Keep JSONB in `cme_agent_outputs.content` alongside structured extraction | Belt and suspenders — structured for queries, JSONB as source of truth | 2026-03-12 |
| D6 | Separate `cme_documents` from `cme_agent_outputs` | Documents are compliance artifacts with retention rules; agent outputs are pipeline state | 2026-03-12 |
