---
id: overview
title: Tools Overview
sidebar_position: 1
---

# Custom Tools Overview

Three DHG custom tools (verified 2026-06-05) let the models query the live platform. They expose **7 functions** in total.

| Tool | Functions | Backend |
|------|-----------|---------|
| [DHG System Health](./system-health) | `get_container_health`, `get_system_health` | Registry API (`:8011`) |
| [DHG Knowledge Search](./knowledge-search) | `search_knowledge`, `get_recent_bug_fixes`, `get_recent_decisions` | Registry API (`:8011`, `POST /api/kb/search`) |
| [DHG Log Query](./log-query) | `query_logs`, `search_errors` | Loki (`:3100`) |

## Attachment policy

| Model type | Tools attached |
|------------|----------------|
| 6 text models (DeepSeek Flash/Pro, Gemma 4 12B, GLM-4.7, Devstral, Qwen3 14B) | all 3 |
| 2 vision models (Qwen3-VL, Llama 3.2 Vision) | `dhg_system_health` only |

Vision models are scoped to health only — they exist for image analysis, not log/KB agentic work.

## How a tool call works

See [Architecture → Integrations](../architecture/integrations) and the [request-flow diagram](/open-webui/img/request-flow.svg). In short: the model emits a tool call → Open WebUI executes it inside the container → the tool hits a DHG backend over `dhgaifactory35_dhg-network` → JSON returns to the model → the model produces a grounded answer.
