---
sidebar_position: 3
title: Services
---

# Services Reference

## Registry API (port 8011)

The central data store and API layer. FastAPI + PostgreSQL 15 + pgvector.

- **64 tables** including CME documents, agent sessions, security RBAC, export jobs
- **Alembic migrations** for schema management
- **Prometheus /metrics** endpoint for observability
- **Key modules:** `api.py` (app), `cme_endpoints.py`, `agent_endpoints.py`, `security_endpoints.py`, `export_endpoints.py`

```bash
# DB access
docker exec -it dhg-registry-db psql -U dhg -d dhg_registry

# Health check
curl -s http://localhost:8011/healthz
```

## Frontend (port 3000)

Next.js production frontend with role-aware sidebar (Work/Observe/Manage sections).

- **LLManager Review Inbox** — human-in-the-loop workflow at /inbox
- **Files tab** — document download + project bundles + Google Drive sync
- **Auth** — Cloudflare Access JWT + middleware route guard

## VS Engine (port 8013)

Verbalized Sampling engine with Prometheus metrics. Supports quality assessment of generated content.

## PDF Renderer (internal)

Playwright-based service — no external port, reachable from registry-api over `dhgaifactory35_dhg-network`.

- **Single document PDF** — renders Next.js print routes via Playwright
- **Project bundler** — atomic zip writer with manifest.json
- **Google Drive sync** — service-account client with reconciliation
- **Worker loop** — `FOR UPDATE SKIP LOCKED` job claim, three-scope dispatch

## MedKB (ports 5435, 6381, 8015)

Medical Knowledge Base RAG service:

- **dhg-medkb-db** (5435) — PostgreSQL + pgvector, separate from registry
- **dhg-medkb-cache** (6381) — Redis 7 query + embedding cache (4GB LRU)
- **dhg-medkb-api** (8015) — FastAPI RAG with LangGraph (dense + hybrid + CRAG)

## Ollama (port 11434)

Local LLM inference:

- `llama3.1:8b` — general purpose
- `nomic-embed-text` — embeddings for semantic search
- `qwen3:14b` — alternative model

## Session Logger (port 8009)

Tracks Claude Code sessions with Ollama embeddings. Provides the embedding service for the memory pipeline.

## Additional Stacks

| Stack | Main Port | Containers |
|-------|-----------|------------|
| Transcribe Pipeline | 8200 | 12 containers, GPU-accelerated |
| Infisical | 8089 | 5 containers |
