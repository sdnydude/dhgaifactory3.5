---
sidebar_position: 3
title: Services
---

# Services Reference

:::info Generated inventory
The authoritative, CI-checked list of every container, port and profile is the generated [Service Inventory](./service-inventory.md) page. This page is the narrative companion.
:::

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

## Ollama (port 11434)

Local LLM inference. **`dhg-ollama` container only** — repo-defined in `docker-compose.yml`, bound `0.0.0.0:11434`, GPU, models on named volume `dhgaifactory35_ollama-data`. Consumers on the LAN (e.g. Portage Porter chat, `LOCAL_LLM_BASE_URL=http://10.0.0.251:11434/v1`) depend on this exact bind.

> **Do not run a host `ollama.service`.** A stray systemd unit (`/etc/systemd/system/ollama.service`, `127.0.0.1:11434`, empty model store) was found enabled on 2026-08-15. It lost the bind race to the container for months (crash-looping every 3s), then won it after a power-outage cold boot: `dhg-ollama` failed to restart (`failed to bind host port 0.0.0.0:11434/tcp: address already in use`), dockerd dropped the container's port endpoint, and Portage Porter silently fell over from granite to Gemini for 5h. Disabled with `systemctl disable --now ollama.service`. If it ever reappears (e.g. an Ollama installer re-adds it), disable it again. Recovery when the container is up but `docker port dhg-ollama` prints nothing: `docker compose up -d --force-recreate --no-deps ollama` (plain `docker start` reuses the broken endpoint). Registry bug-fix `ef492f28`.

- `granite4.1:8b` — Portage Porter chat primary (tools, grounding)
- `qwen3-vl:8b-instruct` — Portage vision/scan primary (`VISION_PROVIDERS=local:qwen3-vl:8b-instruct,gemini,anthropic`, 2026-08-17). Must be the **instruct** tag: `qwen3-vl:latest` is the thinking variant and burns the whole `max_tokens` budget on reasoning (Ollama's OpenAI-compat path ignores `think:false` / `reasoning_effort`), returning empty content. Container runs `OLLAMA_CONTEXT_LENGTH=16384` — default 4096 rejects 3-image scans (~8k prompt tokens).
- `qwen3-vl:latest` (thinking) / `qwen3-vl-nothink` (template hack, avoid) / `llama3.2-vision` — other vision
- `nomic-embed-text` — embeddings for semantic search
- `qwen3:14b`, `qwen3:8b`, `qwen3:4b`, `llama3.1:8b`, `gemma4:12b`/`26b`, `mistral-small3.2:24b`, `devstral-small-2:24b`, `glm-4.7-flash` — general / alternates

## Session Logger (port 8009)

Tracks Claude Code sessions with Ollama embeddings. Provides the embedding service for the memory pipeline.

## Additional Stacks

| Stack | Main Port | Containers |
|-------|-----------|------------|
| Transcribe Pipeline | 8200 | 12 containers, GPU-accelerated |
| Infisical | 8089 | 5 containers |
