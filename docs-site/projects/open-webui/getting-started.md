---
id: getting-started
title: Getting Started
sidebar_position: 1
---

# Open WebUI — DHG AI Factory

Open WebUI is the DHG AI Factory's self-hosted chat and agent surface. It puts a curated stack of eight large language models — some running locally on the RTX 5080, some in the cloud — behind a single authenticated interface at **[chat.digitalharmonyai.com](https://chat.digitalharmonyai.com)**, wired into the DHG Registry, Loki logs, and a sandboxed terminal.

> **Documentation status.** Every fact in this section was verified against the live instance on **2026-06-05** (Open WebUI **v0.9.6**) via the Open WebUI API, not reconstructed from notes. Where the live state differs from earlier session logs, the live state is documented and the discrepancy is called out explicitly.

## What it is

<img src="/open-webui/img/system-overview.svg" alt="Open WebUI system architecture: Cloudflare access, core container, local and cloud model backends, and DHG integrations" />

| Property | Value |
|----------|-------|
| Product | Open WebUI |
| Version | 0.9.6 |
| Container | `dhg-open-webui` |
| Port | 3080 (host) |
| Public URL | `chat.digitalharmonyai.com` (Cloudflare Tunnel + Access) |
| LAN URL | `http://10.0.0.251:3080` |
| Default model | `deepseek-v4-flash-dhg` |
| Workspace models | 8 (see [Models](./models/overview)) |
| Custom tools | 3 (see [Tools](./tools/overview)) |
| Knowledge bases | 3 defined — **0 documents loaded** (see [Knowledge Bases](./knowledge-bases)) |
| Slash commands | 11 (see [Slash Commands](./slash-commands)) |
| Web search | DuckDuckGo (enabled) |
| Companion service | `dhg-open-terminal` (port 8022) |

## Why it exists

Open WebUI is the **Debug Ops** workbench — a place to interrogate the running DHG AI Factory platform conversationally without leaving a browser tab. Through three custom tools the models can:

- check system and container health (Registry `/healthz` + feedback-pipeline status),
- search the DHG knowledge base (decisions, bug fixes, insights, deferred work across 9 registry tables), and
- query container logs from Loki.

The model stack is deliberately tiered for cost: local Ollama models do the routine work for free, DeepSeek's cloud models handle harder reasoning, and Claude Opus 4.8 is reserved for escalation. See the [escalation ladder](./models/overview#escalation-ladder).

## 30-second quick start

1. Open **[chat.digitalharmonyai.com](https://chat.digitalharmonyai.com)** and sign in via Google (Cloudflare Access).
2. The model selector defaults to **DeepSeek V4 Flash (DHG)** — fast and cheap. Leave it for general questions.
3. Ask a system question to see the tools fire, e.g. *"What's the registry health right now?"* or *"Show me the last 10 errors from dhg-registry-api."*
4. For heavy reasoning, switch to **DeepSeek V4 Pro (DHG)**; for local/free, pick **Gemma 4 12B** or **GLM-4.7 Flash**; for screenshots/diagrams, pick a vision model.
5. Type `/` to see the 11 slash commands.

## Where to go next

- **[Installation](./installation)** — containers, ports, Cloudflare, Open Terminal, environment.
- **[Architecture](./architecture/overview)** — how the pieces fit together, the RAG pipeline, and integrations.
- **[Models](./models/overview)** — the 8-model stack, free vs. fee, and per-model deep dives with cited benchmarks.
- **[Benchmarks](./benchmarks)** — consolidated, fully-sourced benchmark comparison.
- **[User Guide](./user-guide)** — practical day-to-day usage.
- **[Specifications](./specifications)** — the exhaustive reference: every config value, port, and setting.
