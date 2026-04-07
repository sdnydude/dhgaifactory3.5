# Progress Log: CME Database Schema & Compliance Storage

---

## Session 5 — 2026-03-12

### Completed
- [x] Checked pipeline status: thread `146808b7` completed 6 agents, failed at prose quality gate (score 85, retry exhausted)
- [x] Synced 5 agent outputs from LangGraph Cloud to registry via `POST /sync`
- [x] Fixed badge polling 422 bug: `limit: 0` → `limit: 100` in `use-badge-polling.ts`
- [x] Fixed agent name mismatch: output matching in `page.tsx` and `document-card.tsx` now handles both short names (`research`) and full names (`research_agent`)
- [x] Added auto-sync to `get_cme_pipeline_status` endpoint — Cloud sync triggers on every poll when project is processing/review
- [x] Added `document_text`, `embedding vector(768)`, `search_vector tsvector` columns to `cme_agent_outputs`
- [x] Enabled `pg_trgm` extension
- [x] Researched all 47 intake form fields across 10 sections
- [x] Researched all 11 agent output schemas (document text paths, quality score paths, metrics)
- [x] Created task_plan.md, findings.md, progress.md

### In Progress
- [ ] Phase 1: Database schema migration (tables, indexes, triggers)
  - `cme_documents` table (compliance, 7-year retention)
  - `cme_intake_fields` table (structured intake)
  - `cme_source_references` table (literature tracking)
  - Indexes and triggers for all tables
  - SQLAlchemy model updates

### Blocked
- Registry needs restart to pick up auto-sync code change in `cme_endpoints.py`

### Decisions Made
- D1: `ON DELETE RESTRICT` for compliance tables (not CASCADE)
- D2: Immutable documents (version, no update)
- D3: nomic-embed-text (768 dims) via Ollama for embeddings
- D4: HNSW index for vector search (better for small datasets)
- D5: Keep JSONB alongside structured extraction (belt and suspenders)
- D6: Separate `cme_documents` from `cme_agent_outputs`
