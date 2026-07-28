---
id: knowledge-search
title: DHG Knowledge Search
sidebar_position: 3
---

# DHG Knowledge Search

> Search the DHG registry knowledge base across all 9 KB tables for past decisions, bug fixes, insights, and deferred work.

| Property | Value |
|----------|-------|
| Tool id | `dhg_knowledge_search` |
| Backend | Registry API — `POST /api/kb/search` |
| Attached to | 6 text models |

This tool queries the **Registry** knowledge base (9 PostgreSQL tables), which is fully populated — it is **independent of the empty in-app Open WebUI KBs**. See [Architecture → RAG Pipeline](../architecture/rag-pipeline).

## Functions

### `search_knowledge`

Searches the DHG registry KB across all 9 tables. Under the hood this is the hybrid RRF pipeline: query embedding via `nomic-embed-text`, per-table FTS + vector search, Reciprocal Rank Fusion (k=60), TOP_K=5.

### `get_recent_bug_fixes`

Returns the most recent bug fixes logged in the registry.

### `get_recent_decisions`

Returns the most recent architectural and implementation decisions logged in the registry.

## Request shape (`POST /api/kb/search`)

```json
{
  "query": "string (1–2000 chars)",
  "project_name": "dhg-ai-factory (optional)",
  "sources": ["docs", "insights", "decisions", "ship_sessions",
              "corrections", "agent_sessions", "dev_changelog",
              "bug_fixes", "deferred_items"],
  "limit": 10
}
```

Each result carries `source`, `source_id`, `title`, `content`, `score`, `project_name`, and `metadata`. Source of truth: `registry/kb_endpoints.py`, `registry/kb_service.py`, `registry/kb_schemas.py`.

## Example prompts

- *"What did we decide about pyright errors?"*
- *"Find recent bug fixes related to the registry proxy."*
- *"Search the KB for anything about the memreg daemon."*
