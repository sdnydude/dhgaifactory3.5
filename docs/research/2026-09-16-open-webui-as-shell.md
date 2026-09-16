# Open WebUI as the DHG portal shell: what it can and cannot host

Date: 2026-09-16. Sources: Open WebUI 0.11 documentation and release notes (URLs inline), the LICENSE file verbatim, and the 0.11.3 backend source (`config.py`, `env.py`) checked in the main session for shell-customization settings.

## The finding that changes the portal plan

Open WebUI is a chat and knowledge application with a plugin system. It is not an application shell. Verified against the 0.11.3 source: the only settings that touch the shell are the product name (`WEBUI_NAME`, `CUSTOM_NAME`) and admin banners (`WEBUI_BANNERS`). There is no setting, plugin slot or route for custom navigation, a custom home page, dashboard widgets, or mounting another web application as a page. The documentation sitemap has no page for any of those either.

What that means for the decision that Open WebUI is the home for every DHG app: the apps cannot live inside it as pages. They can be linked from it, or narrow widgets can render inside chat messages. A single-shell experience with the Next.js app, Grafana and Docusaurus as first-class pages requires either forking Open WebUI's Svelte frontend, or inverting the plan so the Next.js app is the shell and Open WebUI is the chat application inside it.

## What Open WebUI does offer, by area

**Extension surface.** Four Python function types: Pipe (registers as a model in the sidebar, can expose several models), Filter (intercepts inlet, stream, outlet and, since 0.11.2, request), Action (message toolbar button), Event (system events). Pipelines are documented as legacy and not recommended. The only embedding feature is Rich UI: a Tool or Action returns HTML that renders as a sandboxed iframe inside a chat message; scripts allowed, same-origin and forms off by default and per-user toggles; the embed cannot read the Open WebUI session. Banners are the one place to inject links into the shell (HTML subset with anchors). Custom CSS is a community Docker technique, not a product feature.
Sources: https://docs.openwebui.com/features/extensibility/plugin/functions/ · https://docs.openwebui.com/features/extensibility/plugin/development/rich-ui/ · https://docs.openwebui.com/features/administration/banners · https://docs.openwebui.com/features/extensibility/pipelines/

**Identity.** Open WebUI is an OIDC client, not a provider. Trusted-header auth lets a proxy assert identity, groups and role (with the documented warning that a misconfigured proxy lets anyone be anyone). OAuth token exchange lets an external app obtain an Open WebUI session token as the user, one way. Groups and roles can be mapped from IdP claims; SCIM and LDAP group sync exist. Recommended pattern: one external identity provider, both Open WebUI and the Next.js app as OIDC clients, Cloudflare Access in front, CME client organizations mapped to groups by claim.
Source: https://docs.openwebui.com/features/authentication-access/auth/sso/

**Agents as models.** An external agent appears in chat through a plain OpenAI-compatible endpoint added under Connections, or through a Pipe function when the protocol is not OpenAI-shaped. There is no AG-UI support in the docs. MCP is native over streamable HTTP only, admin-configured. Native tool calling is the default since 0.10.0; human-in-the-loop tool approval arrived in 0.11.1; sub-agents in 0.11.0. Generative UI tops out at HTML inside a message.
Sources: https://docs.openwebui.com/getting-started/quick-start/connect-an-agent/ · https://docs.openwebui.com/features/extensibility/mcp · https://github.com/open-webui/open-webui/releases/tag/v0.11.1

**Admin and observability.** Roles, groups, per-resource grants (additive only, no deny), an admin view that resolves every grant for a user or group, analytics with REST endpoints, an evaluation leaderboard, audit log levels, webhooks. OTLP export of traces, metrics and logs with the standard environment variables. No Prometheus scrape endpoint and no way to embed Grafana or any external dashboard.
Sources: https://docs.openwebui.com/features/authentication-access/rbac/ · https://docs.openwebui.com/features/administration/analytics/ · https://docs.openwebui.com/reference/monitoring/otel

**License.** Clause 4 of the LICENSE, verbatim: branding may not be altered, removed, obscured or replaced in any deployment except where end users do not exceed fifty in any rolling thirty-day period, or with written permission, or under an enterprise license. The docs' license page adds that co-branding (your logo beside theirs), white-labeling and recoloring the logo require an enterprise license, while an unobtrusive "Managed by" footer is permitted. That co-branding reading is the project's published guidance, not LICENSE text. Enterprise pricing is not public; sales asks for the seat count.
Sources: https://raw.githubusercontent.com/open-webui/open-webui/main/LICENSE · https://docs.openwebui.com/license · https://docs.openwebui.com/enterprise

**Upgrade 0.9.6 to 0.11.3.** Seven releases. 0.10.0 flips tool calling to native for every model, moves auth config, sandboxes Pyodide, renames a web-fetch variable, and states downgrades are unsupported. 0.11.0 has schema changes that break rolling updates. 0.11.0 through 0.11.2 could start on a half-applied migration; 0.11.3 stops at the error. Back up first, pin `v0.11.3`, stop all replicas together, persist the secret key, clear browser caches after. Switching the vector store to pgvector requires a full re-embed of every knowledge base through the admin reindex action; pgvector hybrid search since 0.10.0 makes the switch worth doing in the same window.
Sources: https://github.com/open-webui/open-webui/releases/tag/v0.10.0 · https://github.com/open-webui/open-webui/releases/tag/v0.11.0 · https://github.com/open-webui/open-webui/releases/tag/v0.11.3 · https://docs.openwebui.com/getting-started/updating · https://docs.openwebui.com/troubleshooting/rag/

## Three realistic portal shapes

1. **Open WebUI is the front door; apps are linked.** All local models, CME agents as OpenAI-compatible connections or Pipes, MCP tools, knowledge on pgvector, channels for client collaboration live natively. Grafana, Docusaurus and the Next.js surfaces are reached through banner links. Compact live widgets (a pipeline status card) render inside chat via Rich UI. Cheapest. Not a single shell.
2. **Next.js is the shell; Open WebUI is the chat app inside it.** The Next.js app already has admin, dashboards, monitoring, inbox, projects and studio routes. Open WebUI is embedded by iframe (its frame options are configurable; the hardening guide recommends deny, so this is a deliberate setting) or linked. Identity in one IdP. DHG branding lives on the shell, so the Open WebUI license clause is not triggered. This delivers the single-shell experience the decision describes.
3. **Fork Open WebUI's frontend.** Full control of navigation and pages. A permanent merge burden against a project that ships weekly, and the branding clause still applies above fifty users.

## Hard limits to carry into any plan

- No external app as a page in the shell without a fork.
- No custom navigation, home page or widgets; banners and the product name are the only shell settings.
- Not an identity provider; one-way token exchange only.
- No DHG branding above fifty end users in thirty days without an enterprise license; the project's own guidance treats adding a DHG logo beside theirs as a breach.
- No rolling upgrades across schema changes; never land on 0.11.0 to 0.11.2.
- A vector store switch is a full re-embed.

Unverified: the shipped default of the frame options setting, and whether a Rich UI embed may nest an external URL.
