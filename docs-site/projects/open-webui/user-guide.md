---
id: user-guide
title: User Guide
sidebar_position: 8
---

# User Guide

Practical, day-to-day usage of the DHG Open WebUI instance.

## Signing in

Go to **[chat.digitalharmonyai.com](https://chat.digitalharmonyai.com)** and authenticate with Google (Cloudflare Access). There is no local account creation — access is gated at the edge.

## Choosing a model

The picker opens on **DeepSeek V4 Flash (DHG)** — the right default for most prompts. Switch based on the task:

| You want to… | Use |
|--------------|-----|
| Ask a quick question / triage | DeepSeek V4 Flash (default) |
| Reason through architecture or a hard bug | DeepSeek V4 Pro |
| Work locally for free, general reasoning | Gemma 4 12B or Qwen3 14B |
| Run an agent loop / tool-heavy task locally | GLM-4.7 Flash |
| Generate or refactor code locally | Devstral Small 2 |
| Analyze a screenshot, diagram, or UI | Qwen3-VL (primary) or Llama 3.2 Vision |

See [Models → Overview](./models/overview) for the full comparison and the escalation ladder.

## Using the DHG tools

The six text models can call three tools automatically when your question implies them:

- **System health** — *"Is the registry healthy?"*, *"any open incidents?"*
- **Knowledge search** — *"what did we decide about X?"*, *"recent bug fixes in the proxy?"*
- **Log query** — *"last 20 errors across all containers"*, *"logs from dhg-registry-api"*

You don't invoke tools manually — describe what you want and the model decides. For deterministic behaviour, use the matching [slash command](./slash-commands) (`/health`, `/search`, `/logs`).

## RAG / knowledge

The **Knowledge Search tool** works today (it hits the Registry KB). The **in-app RAG knowledge bases are currently empty** — don't rely on document RAG until they're re-populated. See [Knowledge Bases](./knowledge-bases).

## Web search

DuckDuckGo web search is enabled for every model — ask about current events or external docs and the model can look them up without any setup.

## Terminal

A sandboxed shell + file browser is available via the Terminal integration (backed by `dhg-open-terminal`). Use it for quick file inspection from within the chat surface.

## Thinking modes (Qwen3 14B)

Qwen3 14B supports `/think` (deep reasoning, slower) and `/no_think` (fast). Prepend the directive to your message. Other models reason by default per their system prompt.

## Slash commands

Type `/` to see all 11 commands — five DHG operations, five Debug Ops engineering prompts, and a security review. See [Slash Commands](./slash-commands).

## Tips

- The models share a "be direct, one recommendation, alternatives below" house style — expect concise answers.
- For visual work, paste or upload an image and the vision models will analyze it directly.
- Generated code blocks have a one-click download (the `download_code_blocks` filter).
