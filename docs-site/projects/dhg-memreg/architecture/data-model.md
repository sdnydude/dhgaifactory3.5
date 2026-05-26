---
title: Data Model
sidebar_position: 2
---

# Data Model

dhg-memreg writes to 7 registry tables and reads from 4 endpoints. All tables live in the DHG Registry's PostgreSQL database (`dhg-registry-db` on port 5432).

## Write Targets

### Capture Scripts → Registry Tables

| Capture Script | Registry Endpoint | Target Table | Primary Key |
|----------------|------------------|--------------|-------------|
| `post-bug-fixes` | `POST /api/bug-fixes` | `bug_fixes` | `id` (UUID) |
| `post-correction` | `POST /api/corrections` | `corrections` | `id` (UUID) |
| `post-decision-logs` | `POST /api/decision-logs` | `decisions` | `id` (UUID) |
| `post-deferred-items` | `POST /api/deferred-items` | `deferred_items` | `id` (UUID) |
| `post-insight` | `POST /api/insights` | `insights` | `id` (UUID) |
| `post-ship-session` | `POST /api/ship-sessions` | `ship_sessions` | `id` (UUID) |
| `post-test-coverage` | `POST /api/test-coverage` | `test_coverage` | `id` (UUID) |

### Ingestion Scripts → Registry Tables

| Ingestion Script | Registry Endpoint | Target Table | Upsert Key |
|-----------------|------------------|--------------|------------|
| `ingest-memory-files` (type=decision) | `POST /api/decision-logs` | `decisions` | Duplicate check by title |
| `ingest-memory-files` (other types) | `POST /api/doc-pages/bulk` | `doc_pages` | `source_file` |
| `ingest-claude-md` | `POST /api/doc-pages/bulk` | `doc_pages` | `source_file` |

## Read Sources

### KB Search

The `POST /api/kb/search` endpoint performs hybrid full-text + vector search across multiple tables:

| Source | Table | What's Searched |
|--------|-------|----------------|
| `decisions` | `decisions` | Architecture and implementation decisions |
| `insights` | `insights` | Technical discoveries and observations |
| `deferred_items` | `deferred_items` | Work identified but not yet done |
| `ship_sessions` | `ship_sessions` | Completed shipping workflows |
| `corrections` | `corrections` | User corrections to Claude behavior |

Search returns results ranked by relevance score, combining keyword matching and semantic similarity.

### Direct Queries (Used by Hooks)

| Endpoint | Used By | What It Returns |
|----------|---------|----------------|
| `GET /api/ship-sessions?project_name=X&limit=3` | SessionStart hook | Recent ship sessions for the project |
| `GET /api/deferred-items?project_name=X&status=open&priority=high&limit=5` | SessionStart hook | Open high-priority deferred items |
| `GET /api/corrections/stats` | UserPromptSubmit, SubagentStart hooks | Correction category counts (7-day window) |

## Common Fields

All captured records share these fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Auto-generated primary key |
| `project_name` | string | DHG project identifier (e.g., `dhg-ai-factory`) |
| `created_at` | timestamp | When the record was created |
| `model_name` | string | Claude model that generated the capture (e.g., `claude-opus-4-6`) |
| `tags` | string[] | Semantic search tags for discoverability |

## Data Lifecycle

Captured data is **append-only** — records are never updated or deleted by the capture pipeline. The registry API provides update/delete endpoints for manual management, but the memreg toolchain only writes.

Deferred items are the exception: their `status` field can be updated to `resolved` or `wont_fix` when the work is completed or abandoned, but this happens through the registry API directly, not through memreg.
