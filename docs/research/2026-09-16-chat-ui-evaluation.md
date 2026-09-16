# Local-model chat UI: what Open WebUI does here, and whether anything on GitHub justifies replacing it

Date: 2026-09-16. Author: Claude (Fable 5.1), for Stephen Webber.
Sources: the running container and its database on g700data1 (read-only), GitHub API numbers pulled 2026-09-16, and a documentation survey with URLs beside every claim (appendix).

## 1. What Open WebUI is used for today

Open WebUI is not the DHG front end. The DHG front end is the Next.js 16 app on port 3000 (app.digitalharmonyai.com) built on assistant-ui and CopilotKit. Open WebUI is a separate container, `dhg-open-webui`, on port 3080, published as chat.digitalharmonyai.com through the Cloudflare tunnel, behind Cloudflare Access.

It was set up on 2026-06-05 during "Debug Ops Phase 1" as a chat surface for the local models on the RTX 5080. What is configured in it right now:

| Thing | Count | Detail |
|---|---|---|
| Users | 1 | admin (Stephen) |
| Chats, ever | 2 | both on 2026-06-05, none since |
| Workspace models | 14 | 8 DHG-branded (DeepSeek V4 Flash/Pro, Gemma 4 12B, GLM-4.7 Flash, Devstral Small 2, Qwen3 14B, Qwen3 VL, Llama 3.2 Vision) plus 6 raw Ollama entries |
| Backends | 2 | Ollama at `dhg-ollama:11434` (15 models pulled); DeepSeek via an OpenAI-compatible endpoint |
| Custom tools | 3 | DHG System Health, DHG Knowledge Search, DHG Log Query |
| Knowledge bases | 3 | DHG Architecture (4 files), Debug Protocols (3), DHG Reference (4) |
| Saved prompts | 11 | |
| Filter functions | 2 | automemory, Download Code Blocks |
| Companion | 1 | `dhg-open-terminal` on port 8022 |
| Version | 0.9.6 | current upstream is 0.11.3; seven releases behind |

Plain reading: a well-configured playground that has not been opened in three months. It is not a production surface, and nothing in the codebase depends on it (the only repo references are the backup manifest).

## 2. The GitHub field, September 2026

Numbers from the GitHub API on 2026-09-16.

| Project | Stars | License | Latest release | Server-deployable |
|---|---|---|---|---|
| open-webui/open-webui | 152,269 | custom (BSD-3 plus branding clause) | v0.11.3, 2026-08-31 | yes |
| lobehub/lobehub (was lobe-chat) | 82,527 | custom (Apache-2 plus commercial terms) | v2.2.17, 2026-09-11 | yes |
| Mintplex-Labs/anything-llm | 66,092 | MIT | v1.16.1, 2026-08-27 | yes |
| janhq/jan | 44,493 | custom | v0.8.4, 2026-07-23 | desktop |
| danny-avila/LibreChat | 44,081 | MIT | v0.8.7 stable 2026-06-23; v0.8.8-rc3 2026-09-15 | yes |
| chatboxai/chatbox | 41,785 | GPL-3.0 | v1.23.2, 2026-09-10 | desktop |
| CopilotKit/CopilotKit | 37,381 | MIT | v1.72.0, 2026-09-15 | library (already in our frontend) |
| onyx-dot-app/onyx | 32,120 | MIT plus enterprise `ee/` dirs | v4.7.6, 2026-09-16 | yes |
| assistant-ui/assistant-ui | 12,163 | MIT | 2026-09-15 | library (already in our frontend) |
| huggingface/chat-ui | 10,952 | Apache-2.0 | v0.10.0, 2026-05-11 | yes |
| enricoros/big-AGI | 7,126 | MIT | v2.1.0, 2026-08-21 | yes, but chats live in the browser |
| fmaclen/hollama | 1,184 | MIT | 0.35.4, 2025-10-12 | stale |

## 3. What each server candidate offers, against what we need

What we need from this surface, if it exists at all: Ollama plus OpenAI-compatible providers; MCP client so the same tools serve every model; RAG that can reuse our Postgres/pgvector rather than adding a datastore; single sign-on and roles for the day a second person uses it; an OpenAI-compatible API out, so agents can call the UI's tools; OpenTelemetry or Prometheus output into the stack we already run; and a small container footprint on a box that already hosts Postgres, Prometheus, Loki, Grafana, Langfuse and fifteen Ollama models.

**Open WebUI (incumbent).** Meets every line. Native MCP client over streamable HTTP with OAuth 2.1 since 0.6.31. RAG with Chroma by default and Postgres/pgvector, Qdrant, Milvus and others as swappable backends. Groups, RBAC, OIDC, and LDAP group sync as of 0.11.0. Exposes its own OpenAI-compatible endpoint with API keys, and that endpoint can run its server-side tools. OTLP traces and metrics through `ENABLE_OTEL`, which lands in our Grafana directly. Recent releases added sub-agents, shared folders with ACLs, context compaction, pgvector hybrid search and human-in-the-loop tool approval. One upgrade hazard: a migration bug in 0.11.0 to 0.11.2 half-upgraded databases; 0.11.3 fixes it, so back up `webui.db` first. License: the branding clause only applies above fifty end users in thirty days. With one user it is inert; it would matter only if this became a client-facing product under DHG branding.

**LibreChat.** The one defensible alternative. Plain MIT, no branding clause. The deepest MCP implementation in the field (remote proxies, OAuth, per-request permission scoping, agents, sub-agents, human-in-the-loop). First-class observability since 0.8.6: Prometheus `/metrics`, backend OpenTelemetry, Langfuse scores. The cost is the stack: MongoDB, Meilisearch, a separate RAG API service and its own vector database, so four new residents on g700data1, and its RAG would not reuse our pgvector. It does not expose an OpenAI-compatible API of its own. Stable is 0.8.7 from June; the current work is in release candidates.

**LobeHub.** Has become a team agent-workspace, not a chat UI: the latest release adds planning leases, reviewer acceptance flows and chat-platform bots, ships four database migrations, and states that downgrade and rollback are unverified. Weekly releases with schema migrations most weeks is real operational tax for a surface with two chats. License adds commercial terms for derivative distribution.

**AnythingLLM.** MIT, self-contained RAG on embedded LanceDB, MCP, agent skills, scheduled jobs, model router. Its last six months of releases are desktop-focused (NPU runtimes, OS features). No documented OpenTelemetry or Prometheus output, no pgvector path. Simpler than what we have, not more capable.

**Onyx.** Enterprise search over forty-plus connectors with permission-aware retrieval; agents and MCP are core. SSO, SCIM and RBAC sit behind the enterprise license. Onyx Standard adds an index, connector workers, inference servers, Redis and MinIO. It is a better search platform than Open WebUI and not a better chat surface. Wrong category for this question.

**big-AGI.** Broadest provider matrix and an excellent protocol-debugging layer, but chats persist in the browser, cross-device sync is a paid feature, no auth, no multi-user, no server-side RAG, no observability hooks. A single-operator power tool, not a hosted surface.

**Hugging Face chat-ui.** Apache-2.0, MCP integrated, Ollama supported. Requires MongoDB. No built-in RAG comparable to knowledge bases, no OTel/Prometheus/Langfuse, no API out, one release since May.

**Desktop-only (Jan, Chatbox, Msty).** None runs as a server container with a multi-user store behind Cloudflare Access. Out.

**The no-package option: assistant-ui + CopilotKit in our own Next.js app.** CopilotKit now documents a Pydantic AI adapter, which fits our stack rule. It documents no Ollama or generic OpenAI-compatible adapter, so local models would route through a Pydantic AI agent pointed at Ollama's OpenAI-compatible URL. To match what Open WebUI gives for free we would build four things: a model picker fed from Ollama's tag list; upload, chunk, embed and retrieve against our pgvector; MCP client wiring with a tool-approval UI; and per-thread persistence with auth. That is a real build. It is also the only option that puts local models inside the product UI we actually use.

## 4. Verdict

**There is no well-justified reason to replace Open WebUI with another package.** I looked for one. Every migration argument current in 2026 is either the license clause, which does not apply at one user, or MCP and observability depth, where Open WebUI now matches the field except LibreChat, and LibreChat's edge costs four new services and gives up pgvector reuse. Nothing else is even in the same category.

The honest question is different: **should this surface exist at all?** Two chats since June says nobody is choosing to use it. A public hostname on a container seven releases behind is attack surface without benefit.

Recommendation, in order:

1. **Decide the purpose.** If a local-model chat and tool playground is something you want at hand, keep it. If the real goal is local models inside the DHG product UI, that is Track 6.3 territory (Pydantic AI agents plus the assistant-ui/CopilotKit front end), and Open WebUI should be retired when that lands rather than migrated anywhere first.
2. **If kept: upgrade 0.9.6 to 0.11.3 this week.** Back up `webui.db` first (the backups ship already captures the volume nightly), pull the 0.11.3 image rather than `:main` so the version is pinned, set `ENABLE_OTEL` and the OTLP endpoint so it reports into Grafana, and point `VECTOR_DB` at pgvector so its RAG stops carrying a private Chroma store. About an hour.
3. **If retired:** remove the container, the `open-terminal` companion, the tunnel ingress for chat.digitalharmonyai.com, and the Access application; keep the volume backup for thirty days.

Either way, the two deferred items about Open WebUI knowledge bases resolve with this decision: keep them only if the surface is kept.

## Appendix: sources for section 3

- Open WebUI: https://github.com/open-webui/open-webui/releases/tag/v0.11.3 · https://docs.openwebui.com/license/ · https://docs.openwebui.com/features/extensibility/mcp/ · https://docs.openwebui.com/reference/api-endpoints/ · https://docs.openwebui.com/reference/monitoring/otel/ · https://github.com/open-webui/open-webui/issues/29280 (0.11.x migration bug)
- LibreChat: https://www.librechat.ai/changelog · https://www.librechat.ai/changelog/v0.8.6 · https://www.librechat.ai/docs/configuration/metrics · https://www.librechat.ai/docs/features/agents
- LobeHub: https://github.com/lobehub/lobehub/releases/tag/v2.2.17 · https://raw.githubusercontent.com/lobehub/lobehub/main/LICENSE
- AnythingLLM: https://github.com/Mintplex-Labs/anything-llm/releases/tag/v1.16.1
- Onyx: https://github.com/onyx-dot-app/onyx/releases/tag/v4.7.6 · https://docs.onyx.app/deployment/overview · https://docs.ollama.com/integrations/onyx
- big-AGI: https://github.com/enricoros/big-AGI/releases/tag/v2.1.0 · https://big-agi.com/docs/self-host
- chat-ui: https://github.com/huggingface/chat-ui/releases/tag/v0.10.0
- assistant-ui / CopilotKit: https://www.assistant-ui.com/docs/runtimes/custom/overview · https://docs.copilotkit.ai/
- Langfuse OTLP ingestion (inference that Open WebUI OTLP can land in Langfuse; not documented by Open WebUI): https://langfuse.com/integrations/native/opentelemetry
