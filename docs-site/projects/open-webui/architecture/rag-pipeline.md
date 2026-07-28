---
id: rag-pipeline
title: RAG Pipeline
sidebar_position: 2
---

# RAG Pipeline

The Knowledge Search tool turns a natural-language question into a hybrid retrieval over the DHG Registry's nine knowledge tables and returns ranked, grounded context.

<img src="/open-webui/img/rag-pipeline.svg" alt="RAG pipeline: query, embed, hybrid search across 9 tables, RRF fusion, top-K context" />

## Flow

1. **User query** — a workspace model decides to call `search_knowledge()`, which issues `POST /api/kb/search` to the Registry API.
2. **Embed query** — the Registry generates a single query embedding via Ollama `nomic-embed-text` (768-dim). If embedding fails, the pipeline **degrades gracefully to FTS-only** rather than erroring.
3. **Hybrid search** — each of the 9 KB tables is searched with both full-text search (Postgres `tsvector`) and vector similarity. Sources are searched independently and fault-isolated: a failing source is logged and skipped.
4. **RRF fusion** — results are merged with **Reciprocal Rank Fusion (k=60)** and re-ranked.
5. **TOP_K = 5** — the top 5 results are injected as context for the answering model.

## The 9 knowledge tables

| Table | Contents |
|-------|----------|
| `doc_pages` | Documentation chunks with heading paths |
| `insights` | TLDR + insight statements, categorized |
| `decision_logs` | Decisions: choice, rationale, alternatives rejected |
| `ship_sessions` | Shipped features: approach, complexity, PR |
| `agent_sessions` | Agent run records |
| `corrections` | User feedback / corrections, categorized |
| `dev_changelog` | Development changelog notes |
| `bug_fixes` | Bug fix records |
| `deferred_items` | Deferred / backlog work |

The `sources` request parameter can restrict the search to a subset (e.g. `["docs"]`).

## Open WebUI RAG settings

These govern Open WebUI's *own* document RAG (the in-app KBs), distinct from the tool path above:

| Parameter | Value |
|-----------|-------|
| Embedding model | `nomic-embed-text` (Ollama) |
| Hybrid search | enabled |
| TOP_K | 5 |
| Chunk size | 1500 |
| Chunk overlap | 200 |

:::warning Empty in-app KBs
The three in-app knowledge bases (DHG Reference, Debug Protocols, DHG Architecture) currently contain **0 documents** (verified 2026-06-05). Until they are re-populated, attaching them to a model adds no retrievable context. The Registry-backed Knowledge Search **tool** is unaffected and works normally. See [Knowledge Bases](../knowledge-bases).
:::

## Source of truth

The retrieval logic lives in the Registry, not in Open WebUI:

- Endpoint: `registry/kb_endpoints.py` — `POST /api/kb/search`
- Service: `registry/kb_service.py` — RRF hybrid implementation
- Schemas: `registry/kb_schemas.py` — `KBSearchRequest` / `KBSearchResponse` / `KBSearchResult`
