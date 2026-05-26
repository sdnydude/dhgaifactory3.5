---
sidebar_position: 1
title: Getting Started
---

# Memory Pipeline

The Memory Pipeline is DHG's full intelligence capture and recall system. It automatically captures decisions, insights, corrections, bug fixes, ship sessions, deferred items, and test coverage changes from Claude Code sessions into the DHG Registry, then makes them searchable via hybrid semantic + full-text search.

## Components

The pipeline spans three layers:

| Layer | Where | Purpose |
|-------|-------|---------|
| **Capture** | `~/.claude/scripts/post-*.sh` | 7 fire-and-forget POST scripts that send structured events to the Registry API |
| **Registry** | `aifactory3.5/registry/*_endpoints.py` | FastAPI endpoints that store, deduplicate, and index captured data in PostgreSQL + pgvector |
| **Recall** | `~/.claude/rules/auto-*.md` + session hooks | Rules that trigger capture automatically; briefing hook that injects context on session start |

## Quick Overview

```
Claude Code session
    │
    ├─ auto-rules fire ─────────► post-insight.sh ──────► /api/insights (upsert)
    ├─ auto-rules fire ─────────► post-decision-logs.sh ► /api/decision-logs (upsert)
    ├─ auto-rules fire ─────────► post-correction.sh ───► /api/corrections (upsert)
    ├─ auto-rules fire ─────────► post-bug-fixes.sh ────► /api/bug-fixes (upsert)
    ├─ auto-rules fire ─────────► post-ship-session.sh ─► /api/ship-sessions (upsert)
    ├─ auto-rules fire ─────────► post-deferred-items.sh► /api/deferred-items (upsert)
    ├─ auto-rules fire ─────────► post-test-coverage.sh ► /api/test-coverage (upsert)
    │
    ├─ SessionStart hook ───────► session-briefing.sh ──► Injects 7-source context
    ├─ Stop hook ───────────────► Sweep for missed captures
    │
    └─ /api/kb/search ◄────────── Unified hybrid search across ALL sources
```

## Prerequisites

- DHG Registry API running on `10.0.0.251:8011`
- Claude Code with hooks configured
- PostgreSQL 15 with pgvector extension
- Ollama with `nomic-embed-text` for embeddings (via session-logger on port 8009)

## Key URLs

| Endpoint | Purpose |
|----------|---------|
| `POST /api/kb/search` | Unified search across all sources |
| `POST /api/insights` | Capture insights |
| `POST /api/decision-logs` | Capture decisions |
| `POST /api/corrections` | Capture corrections |
| `POST /api/bug-fixes` | Capture bug fixes |
| `POST /api/ship-sessions` | Capture ship sessions |
| `POST /api/deferred-items` | Capture deferred items |
| `POST /api/test-coverage-changes` | Capture test changes |
| `GET /api/doc-pages/search` | Search indexed documentation |
