---
id: knowledge-bases
title: Knowledge Bases
sidebar_position: 6
---

# Knowledge Bases

Open WebUI has **three in-app knowledge bases** defined and attached to the six text workspace models (verified 2026-06-05).

| KB | Description | Documents |
|----|-------------|:---------:|
| **DHG Reference** | Glossary of terms and acronyms, operations runbook, team directory, brand guidelines. | **0** |
| **Debug Protocols** | Systematic debug protocol, production standards, honesty protocol, quality-first principles, incident response. | **0** |
| **DHG Architecture** | Services, ports, networks, Docker infrastructure, LangGraph agents, observability, auth, known issues. | **0** |

:::warning Current state: all three KBs are empty
Every in-app KB currently holds **0 documents**. The 11 source documents created during the 2026-06-05 setup session did not persist (consistent with the `ENABLE_KB_EXEC` / container-recreate sequence). Until they are re-ingested, attaching these KBs adds no retrievable RAG context to a model's answers.

This is tracked as a deferred work item in the registry. It does **not** affect the [Knowledge Search tool](./tools/knowledge-search), which queries the separate, fully-populated **Registry** knowledge base.
:::

## Two stores, one more time

| | In-app KBs (this page) | Registry KB (tool) |
|--|------------------------|--------------------|
| Where | Open WebUI's own store | PostgreSQL, 9 tables |
| State | 3 KBs, 0 docs | populated |
| Reached via | RAG attachment on a model | `dhg_knowledge_search` → `POST /api/kb/search` |
| Works today? | No (empty) | Yes |

## Attachment

The three KBs are attached to: DeepSeek V4 Flash, DeepSeek V4 Pro, Gemma 4 12B, GLM-4.7 Flash, Devstral Small 2, Qwen3 14B. The two vision models carry a single reference attachment. (Attachment is by collection id; the references are valid — the KBs are simply empty.)

## Re-populating (when ready)

Upload the source documents to each KB via **Workspace → Knowledge** in the UI, or via the Open WebUI knowledge API. RAG settings that will apply: `nomic-embed-text` embeddings, hybrid search, TOP_K=5, 1500/200 chunking (see [RAG Pipeline](./architecture/rag-pipeline)).
