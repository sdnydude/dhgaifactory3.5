---
id: specifications
title: Specifications Report
sidebar_position: 10
---

# Specifications Report

The exhaustive reference for the DHG Open WebUI installation. Every value below was verified against the live instance or its repo-defined dependencies on **2026-06-05**. Values that could not be re-verified via API are labelled.

## 1. Platform

| Property | Value | Verification |
|----------|-------|-------------|
| Product | Open WebUI | live |
| Version | 0.9.6 | live (`/api/config`) |
| Container | `dhg-open-webui` | live (`docker ps`) |
| Host port | 3080 | live |
| Uptime at audit | up 10h, healthy | live (2026-06-05) |
| Auth required | yes (`enable_signup` off, login form on) | live (`/api/config`) |
| OAuth providers (in-app) | none (auth handled at Cloudflare edge) | live |

## 2. Network & access

| Property | Value |
|----------|-------|
| Public URL | `chat.digitalharmonyai.com` |
| LAN URL | `http://10.0.0.251:3080` |
| Tunnel | aifactory (`cloudflared.service`, `/etc/cloudflared/config.yml`) |
| Route | `chat.digitalharmonyai.com → localhost:3080` |
| Edge auth | Cloudflare Access + Google OAuth |
| Docker network | `dhgaifactory35_dhg-network` |

## 3. Companion services

| Service | Container | Port | Source |
|---------|-----------|------|--------|
| Terminal | `dhg-open-terminal` | 8022 (API :8000) | host-managed |
| Local inference | `dhg-ollama` | 11434 | repo `docker-compose.yml` |
| Registry API | `dhg-registry-api` | 8011 | repo `docker-compose.override.yml` |
| Registry DB | `dhg-registry-db` | 5432 | repo |
| Loki | `dhg-loki` | 3100 | repo `docker-compose.override.yml` |

## 4. Models (8 workspace)

Default: `deepseek-v4-flash-dhg`. Picker order matches this table.

| # | Workspace id | Base model | Backend | Cost | Vision | Tools | KBs |
|---|--------------|-----------|---------|------|:---:|:---:|:---:|
| 1 | `deepseek-v4-flash-dhg` | `deepseek-v4-flash` | DeepSeek cloud | fee | — | 3 | 3 |
| 2 | `deepseek-v4-pro-dhg` | `deepseek-v4-pro` | DeepSeek cloud | fee | — | 3 | 3 |
| 3 | `gemma4-12b-dhg` | `gemma4:12b` | Ollama | free | — | 3 | 3 |
| 4 | `glm-4.7-flash-dhg` | `glm-4.7-flash:latest` | Ollama | free | — | 3 | 3 |
| 5 | `devstral-dhg` | `devstral-small-2:24b` | Ollama | free | — | 3 | 3 |
| 6 | `qwen3-14b-dhg` | `qwen3:14b` | Ollama | free | — | 3 | 3 |
| 7 | `qwen3-vl-dhg` | `qwen3-vl:latest` | Ollama | free | ✅ | 1 | 1 |
| 8 | `llama-vision-dhg` | `llama3.2-vision:latest` | Ollama | free | ✅ | 1 | 1 |

System prompts: all share the DHG senior-engineer scaffold (server facts; Registry `:8011`, Loki `:3100`, Grafana `:3001` URLs; "be direct, one recommendation" style) with a per-model closing paragraph. Lengths range 366–852 chars. Full per-model summaries on each [model page](./models/overview).

## 5. Tools (3, 7 functions)

| Tool | Functions | Backend |
|------|-----------|---------|
| `dhg_system_health` | `get_container_health`, `get_system_health` | Registry `:8011` (`/healthz` + health) |
| `dhg_knowledge_search` | `search_knowledge`, `get_recent_bug_fixes`, `get_recent_decisions` | Registry `POST /api/kb/search` |
| `dhg_log_query` | `query_logs`, `search_errors` | Loki `:3100` |

## 6. Knowledge bases (3 in-app)

| KB | id | Documents |
|----|----|:---------:|
| DHG Reference | `e41508e3-…ca095` | 0 |
| Debug Protocols | `416c4457-…91404` | 0 |
| DHG Architecture | `7053ee51-…d8a0be` | 0 |

**All empty** (see [Knowledge Bases](./knowledge-bases)). Separate from the populated Registry KB used by the Knowledge Search tool.

## 7. RAG configuration

| Parameter | Value |
|-----------|-------|
| Embedding model | `nomic-embed-text` (Ollama) |
| Embedding dimensions | 768 |
| Hybrid search | enabled |
| TOP_K | 5 |
| Chunk size | 1500 |
| Chunk overlap | 200 |
| `ENABLE_KB_EXEC` | true |
| Registry retrieval | RRF (k=60) across 9 tables |

## 8. Features & filters

| Feature | State | Verification |
|---------|-------|-------------|
| Default model | `deepseek-v4-flash-dhg` | live (`/api/v1/configs/models`) |
| Web search | DuckDuckGo enabled | session config (not re-verified via public API) |
| Filter: `automemory` | active + global | session config |
| Filter: `download_code_blocks` | active + global | session config |
| Slash commands | 11 | live (`/api/v1/prompts/`) |
| Terminal integration | enabled (`dhg-open-terminal:8000`) | session config |

## 9. Slash commands (11)

`/health`, `/search` `{{query}}`, `/logs` `{{container}}`, `/backlog`, `/debug` `{{issue}}`, `/rca` `{{PROBLEM}}`, `/hypothesis` `{{BUG}}`, `/trace` `{{TARGET}}`, `/postmortem` `{{INCIDENT}}`, `/explain`, `/security-review`. Detail: [Slash Commands](./slash-commands).

## 10. Secrets (Doppler `dhg-infra/dev`)

| Key | Purpose |
|-----|---------|
| `OPEN_WEBUI_API_KEY` | Open WebUI API access |
| DeepSeek API key | Cloud model access |

No secret values appear in this documentation or the repo.

## 11. Source-of-truth files (repo)

| Concern | File |
|---------|------|
| Knowledge search endpoint | `registry/kb_endpoints.py` |
| Knowledge search service (RRF) | `registry/kb_service.py` |
| Knowledge search schemas | `registry/kb_schemas.py` |
| Health endpoint | `registry/api.py` (`/healthz`) |
| Loki config | `observability/loki/loki-config.yml` |
| Ollama service | `docker-compose.yml` |

## 12. Known gaps (honest)

1. **In-app KBs empty** — 3 KBs, 0 docs; re-ingest pending (tracked as a deferred item).
2. **Qwen3-VL local size unverified** — `qwen3-vl:latest` tag's parameter size/quant not confirmed against `ollama list`.
3. **Web search / filters** — confirmed from session config, not re-readable via the API key used for this audit.
4. **`dhg-open-webui` / `dhg-open-terminal` not in repo compose** — host-managed; no single-command reproduce.
