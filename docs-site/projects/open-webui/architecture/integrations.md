---
id: integrations
title: Integrations
sidebar_position: 3
---

# Integrations

Open WebUI is wired to the DHG platform through three custom tools and one terminal integration. This page describes how the wiring works; per-tool function reference lives under [Tools](../tools/overview).

<img src="/open-webui/img/request-flow.svg" alt="Request flow including a tool round-trip from model to Registry/Loki and back" />

## Tool round-trip

When a workspace model emits a tool call, Open WebUI executes the tool inside the container, the tool calls a DHG backend over `dhgaifactory35_dhg-network`, and the JSON result is fed back to the model to produce a grounded answer.

| Tool | Backend | Endpoint(s) |
|------|---------|-------------|
| `dhg_system_health` | Registry API | `GET /healthz`, registry health/incidents |
| `dhg_knowledge_search` | Registry API | `POST /api/kb/search` (9-table RRF) |
| `dhg_log_query` | Loki | LogQL `query_range` |

The six **text** models carry all three tools. The two **vision** models (Qwen3-VL, Llama 3.2 Vision) carry only `dhg_system_health` — they are intended for image analysis, not log/KB agentic work.

## Terminal integration

`dhg-open-terminal` provides a sandboxed shell and file browser, registered under **Admin → Settings → Integrations**. The server address is the Docker service name `dhg-open-terminal:8000` (resolved on the shared network), exposed on the host at port 8022.

This is distinct from **Tool Servers** (generic OpenAPI tool providers) — Open Terminal uses the dedicated Terminal integration, and Tool Servers is intentionally left unused.

## Web search

DuckDuckGo web search is enabled globally, giving every model an out-of-the-box web lookup capability without an API key.

## Filters

Two filters are active and global:

| Filter | Effect |
|--------|--------|
| `automemory` | Persists salient facts from a conversation for later turns |
| `download_code_blocks` | Adds a one-click download affordance to emitted code blocks |

## Network

All integration traffic stays on `dhgaifactory35_dhg-network`; nothing crosses the public internet except the DeepSeek cloud API calls and DuckDuckGo searches. Container-to-container calls use Docker service names, never `localhost`.
