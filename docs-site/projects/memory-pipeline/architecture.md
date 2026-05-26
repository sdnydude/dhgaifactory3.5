---
sidebar_position: 5
title: Architecture
---

# Architecture

The Memory Pipeline connects Claude Code sessions to a persistent knowledge base through three phases: Capture, Store, and Recall.

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Claude Code Session                          │
│                                                                     │
│  auto-rules ──► post-*.sh scripts ──► Registry API ──► PostgreSQL  │
│                                            │                        │
│  SessionStart hook ◄── session-briefing.sh ◄── KB Search           │
│                                                                     │
│  .claude/memory/ ◄──► MEMORY.md index ◄──► Claude context          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DHG Registry (port 8011)                     │
│                                                                     │
│  FastAPI endpoints ──► Pydantic validation ──► SQLAlchemy ORM      │
│                                                      │              │
│  Alembic migrations ◄── PostgreSQL 15 + pgvector ◄───┘              │
│                              │                                      │
│  Ollama nomic-embed-text ◄───┤ (embeddings for semantic search)    │
│                              │                                      │
│  /api/kb/search ◄────────────┤ (hybrid RRF: semantic + FTS)       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Documentation Pipeline                       │
│                                                                     │
│  website/docs/ ──► Docusaurus build ──► nginx (port 8017)          │
│       │                                                             │
│       └──► doc_ingest.py ──► doc_pages table ──► /api/doc-pages    │
└─────────────────────────────────────────────────────────────────────┘
```

## Design Principles

### Fire-and-Forget Capture

Capture scripts never block sessions. Every script exits 0 regardless of API response. This ensures:
- No session interruption if the registry is down
- No context pollution from capture errors
- Millisecond overhead per capture event

### Idempotent Upserts

All endpoints use content-hash deduplication. Re-syncing, re-capturing, or re-running scripts produces no duplicates. This makes the system crash-safe — partial captures can be retried without cleanup.

### Hybrid Search (RRF)

The unified KB search combines:
1. **Semantic search** — pgvector cosine similarity on `nomic-embed-text` embeddings
2. **Full-text search** — PostgreSQL `tsvector` with `ts_rank`
3. **Reciprocal Rank Fusion** — merges both ranked lists with `k=60`

This handles both exact-match queries ("what was the bcrypt decision?") and conceptual queries ("how do we handle auth?").

### Source Separation

Each data type has its own table, endpoint module, and Pydantic schema. This means:
- Schema changes to one type don't affect others
- Each type can have custom validation and dedup logic
- Search can filter by source type
- Alembic migrations are independent per table

## Key Files

| Layer | File | Purpose |
|-------|------|---------|
| Capture | `~/.claude/scripts/post-*.sh` | 7 fire-and-forget POST scripts |
| Rules | `.claude/rules/auto-*.md` | Trigger conditions per capture type |
| Registry | `registry/*_endpoints.py` | FastAPI route handlers |
| Registry | `registry/*_schemas.py` | Pydantic request/response models |
| Registry | `registry/database.py` | SQLAlchemy engine + session |
| Registry | `registry/api.py` | FastAPI app + router registration |
| Search | `registry/kb_search_endpoints.py` | Unified hybrid search |
| Docs | `registry/doc_ingest.py` | Markdown chunking + embedding ingest |
| Docs | `registry/doc_pages_endpoints.py` | Doc page CRUD + search |
| Hooks | `~/.claude/scripts/session-briefing.sh` | 7-source SessionStart injection |
| Memory | `.claude/projects/*/memory/` | File-based persistent memory |
