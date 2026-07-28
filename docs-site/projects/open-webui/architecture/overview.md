---
id: overview
title: Architecture Overview
sidebar_position: 1
---

# Architecture Overview

Open WebUI sits at the centre of four layers: the Cloudflare **access** edge, the Open WebUI **core** container, the **model backends** (local and cloud), and the **DHG integrations** it can reach over the Docker network.

<img src="/open-webui/img/system-overview.svg" alt="Open WebUI system architecture across access, core, model, and integration layers" />

## Layers

### 1. Access — Cloudflare edge

All external traffic enters through the **aifactory** Cloudflare tunnel. Cloudflare terminates SSL and enforces **Access** (Google OAuth) before any request reaches `dhg-open-webui` on port 3080. There is no anonymous entry point; `enable_signup` is off and login is required.

### 2. Core — `dhg-open-webui`

The container hosts four functional blocks:

- **Chat & workspace** — the 8 DHG workspace models, the default model (`deepseek-v4-flash-dhg`), 11 slash commands, DuckDuckGo web search, and two global filters (`automemory`, `download_code_blocks`).
- **RAG pipeline** — embeds with `nomic-embed-text`, hybrid search, `TOP_K=5`, 1500/200 chunking. See [RAG Pipeline](./rag-pipeline).
- **Custom tools** — `dhg_system_health`, `dhg_knowledge_search`, `dhg_log_query`. See [Integrations](./integrations) and [Tools](../tools/overview).
- **Terminal integration** — a sandboxed shell/file browser backed by `dhg-open-terminal`.

### 3. Model backends

| Tier | Backend | Models |
|------|---------|--------|
| Local (free) | `dhg-ollama` (:11434, GPU) | Gemma 4 12B, GLM-4.7 Flash, Devstral Small 2 24B, Qwen3 14B, Qwen3-VL, Llama 3.2 Vision, plus `nomic-embed-text` for RAG |
| Cloud (fee) | DeepSeek API | DeepSeek V4 Flash (default), DeepSeek V4 Pro |

See the [escalation ladder](../models/overview#escalation-ladder) for when each tier is used.

### 4. DHG integrations

Over `dhgaifactory35_dhg-network`, the tools reach:

- **Registry API** (`:8011`) — `GET /healthz` and `POST /api/kb/search`.
- **Loki** (`:3100`) — LogQL queries over container logs.
- **Registry DB** (`:5432`) — PostgreSQL 15 + pgvector backing the 9-table knowledge base.

## Two separate knowledge stores — don't confuse them

This is the single most important architectural nuance:

| Store | Where | State (2026-06-05) | Used by |
|-------|-------|--------------------|---------|
| **Registry KB** | PostgreSQL, 9 tables | **populated** | `dhg_knowledge_search` tool → `POST /api/kb/search` |
| **Open WebUI in-app KBs** | Open WebUI's own store | **3 KBs, 0 documents** | RAG attachment on the 6 text models |

The Knowledge Search *tool* is fully functional because it queries the **Registry** KB. The in-app RAG KBs are currently empty (see [Knowledge Bases](../knowledge-bases)) — so RAG retrieval from them returns nothing until documents are re-ingested. Both paths are documented separately so the distinction is never lost.

## Component map

| Component | Identifier | Reference |
|-----------|-----------|-----------|
| Chat UI | `dhg-open-webui:3080` | [Installation](../installation) |
| Terminal | `dhg-open-terminal:8000` (host :8022) | [Integrations](./integrations) |
| Local inference | `dhg-ollama:11434` | [Models](../models/overview) |
| Knowledge search backend | `dhg-registry-api:8011` | [Tools → Knowledge Search](../tools/knowledge-search) |
| Log backend | `dhg-loki:3100` | [Tools → Log Query](../tools/log-query) |
