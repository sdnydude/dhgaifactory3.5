---
id: installation
title: Installation & Deployment
sidebar_position: 2
---

# Installation & Deployment

This page documents how the Open WebUI installation is deployed on **g700data1** and how to reproduce or operate it.

> **Deployment note (verified 2026-06-05).** `dhg-open-webui` and `dhg-open-terminal` are **not defined in the repository's docker-compose files** — they were deployed directly on the host. Every other service they depend on (Ollama, Registry API, Registry DB, Loki) *is* repo-defined. This is captured honestly here rather than implying a single `docker compose up`.

## Topology

<img src="/open-webui/img/deployment-topology.svg" alt="Deployment topology of Open WebUI and its dependencies on g700data1" />

## Host

| Property | Value |
|----------|-------|
| Server | g700data1 (`10.0.0.251`) |
| OS | Ubuntu 24.04 |
| GPU | NVIDIA RTX 5080 (16 GB VRAM) |
| RAM | 64 GB |
| Docker network | `dhgaifactory35_dhg-network` |

## Containers

| Container | Port | Source | Status (2026-06-05) | Role |
|-----------|------|--------|---------------------|------|
| `dhg-open-webui` | 3080 | host-managed | up 10h, healthy | Chat / agent UI |
| `dhg-open-terminal` | 8022 (API :8000) | host-managed | up 12h | Shell + file browser tool |
| `dhg-ollama` | 11434 | repo (`docker-compose.yml`) | running (GPU) | Local model + embedding inference |
| `dhg-registry-api` | 8011 | repo (`docker-compose.override.yml`) | running | Health + knowledge search |
| `dhg-registry-db` | 5432 | repo | running | PostgreSQL 15 + pgvector |
| `dhg-loki` | 3100 | repo (`docker-compose.override.yml`) | running | Log aggregation |

## Network exposure (Cloudflare)

The instance is reachable from the internet through the **aifactory** Cloudflare tunnel (`cloudflared.service`, config `/etc/cloudflared/config.yml`):

```
chat.digitalharmonyai.com  →  localhost:3080
```

- Cloudflare terminates SSL.
- **Cloudflare Access** (Google OAuth, account `Swebber@fafstudios.com`) gates the app — no anonymous access.
- The tunnel config is root-owned; changes require `sudo sed` + `sudo systemctl restart cloudflared`.

## Open Terminal integration

`dhg-open-terminal` is registered inside Open WebUI under **Admin → Settings → Integrations** (not Tool Servers). The terminal server address is configured as:

```
dhg-open-terminal:8000
```

This resolves over `dhgaifactory35_dhg-network` (container-to-container), which is why it uses the Docker service name rather than `localhost`.

## Environment & secrets

Secrets are stored in **Doppler** (`dhg-infra/dev`), never in the repo:

| Key | Purpose |
|-----|---------|
| `OPEN_WEBUI_API_KEY` | Programmatic access to the Open WebUI API (model/tool/KB management) |
| DeepSeek API key | Cloud model access for `deepseek-v4-flash` / `deepseek-v4-pro` |

A relevant RAG-related setting applied at the container level:

| Setting | Value | Notes |
|---------|-------|-------|
| `ENABLE_KB_EXEC` | `true` | Enables knowledge-base execution; required a container recreate |

## RAG configuration

| Parameter | Value |
|-----------|-------|
| Embedding model | `nomic-embed-text` (via Ollama) |
| Embedding dimensions | 768 |
| Hybrid search | enabled |
| TOP_K | 5 |
| Chunk size | 1500 |
| Chunk overlap | 200 |

See [Architecture → RAG Pipeline](./architecture/rag-pipeline) for how retrieval actually flows.

## Operating commands

```bash
# Health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3080/health      # → 200
docker ps --filter name=open-webui --format '{{.Names}} | {{.Status}}'

# Restart (host-managed container)
docker restart dhg-open-webui

# Confirm models are served
curl -s http://localhost:3080/api/models -H "Authorization: Bearer $OPEN_WEBUI_API_KEY"
```
