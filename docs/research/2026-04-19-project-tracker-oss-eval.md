# Project Intelligence Module — OSS Adoption Evaluation Memo

**Author:** Claude (research subagent)
**Date:** 2026-04-19
**Decision owner:** Stephen Webber
**Related plan:** `docs/superpowers/plans/2026-04-19-project-intel-module.md`
**Research time:** ~45 minutes (time-boxed)

---

## 1. Executive Summary

**Recommendation: BUILD FRESH on the existing DHG stack, with targeted inspiration from Plane (data model) and OpenProject (burndown math).** No evaluated candidate clears the non-negotiable integration bar. Every viable product carries its own opinionated Postgres/MongoDB/CockroachDB schema, its own auth system, its own Python/Ruby/PHP/TypeScript-Svelte frontend, and an API surface that was designed for humans clicking buttons — not for a LangGraph agent writing hundreds of evidence rows per night with confidence scores, stalled narratives, and embedding-linked docs. Integrating any of them costs more than the 4–6-week build the plan file already scopes, and every one of them would force DHG to maintain a second auth stack alongside Cloudflare Access + RBAC. The pre-research recommendation in the plan file (build-fresh) is confirmed.

---

## 2. Evaluation Matrix

| Candidate | License | Health | Auth fit | DB fit | Agent API | Embeddings | UI fit | Integration est. | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Plane** | AGPL-3.0 | Excellent (48.1k stars, v1.3.0 Apr 2026) | OIDC only, no JWT header trust | Own Django/Postgres schema | Strong REST + webhooks + SDKs | None native | Next.js/TS (close to ours) | 4–6 weeks to integrate cleanly | Inspiration-only |
| **Huly** | EPL-2.0 (NOT MIT as plan stated) | Very active (25.4k stars, daily commits) | Own auth, email/password or token | MongoDB legacy / **CockroachDB** v7 — not Postgres | WebSocket + REST typed client | None native | Svelte (33.6%) — wrong stack | 6–8 weeks | Reject |
| **OpenProject** | GPL-3.0 | Mature, actively maintained | LDAP/SAML/OIDC — no JWT trust | Own Ruby/Postgres schema | REST API v3 + webhooks plugin | None | Rails server-rendered + Angular | 4–6 weeks | Inspiration-only (burndown math) |
| **Leantime** | AGPL-3.0 | Active (9.5k stars, v3.7.3 Mar 2026) | Own session auth | **MySQL/MariaDB only** — disqualifies immediately | REST API + plugins | None | PHP + Blade templates | N/A | Reject |
| **Taiga** | MPL-2.0 | Maintained, 2026 Docker improvements | LDAP/OAuth providers | Own Django/Postgres schema + RabbitMQ + Celery + Redis | REST + webhooks | None | **AngularJS + CoffeeScript** — legacy | N/A | Reject |
| **Vikunja** | AGPL-3.0 | Active (4k stars, Go) | JWT own tokens, no external trust | Postgres/MySQL/SQLite | Solid REST + webhooks | None | Vue frontend | 3–5 weeks | Reject (UI stack mismatch, no RBAC per project) |
| **Focalboard** | MIT | **Unmaintained** (archived standalone Aug 2024, no maintainer found) | Own auth | Postgres/MySQL/SQLite | Limited REST | None | React | N/A | Reject — dead |
| **Tuleap** | GPLv2 | Mature, enterprise-backed (Enalean) | LDAP/SAML/OIDC | Own MySQL schema | REST + webhooks | None | PHP + jQuery era | N/A | Reject (MySQL, stack mismatch) |
| **Wekan** | MIT | Active | Own auth | MongoDB | REST | None | Meteor (legacy) | N/A | Reject |
| **Kanboard** | MIT | Maintenance mode, plugins stale | Own auth | MySQL/Postgres/SQLite | REST | None | PHP server-rendered | N/A | Reject |

**Unverified** in matrix: exact current commit cadence for Huly/OpenProject/Taiga (GitHub API access was unavailable in this session; figures from repo landing pages and third-party reviews).

---

## 3. Per-Candidate Deep Dive

### 3.1 Plane (https://github.com/makeplane/plane)
**What it is:** AI-native project management platform, Next.js/TypeScript frontend + Django/Postgres backend + Redis. Three products in one workspace (Projects, Wiki, AI). Community Edition under AGPL-3.0 with 48.1k GitHub stars, v1.3.0 released April 6, 2026. Supports work items, cycles, modules, pages, 5 layout views, REST API, webhooks, typed Node.js/Python SDKs, OIDC SSO.

**Strengths:** Closest technical fit — TypeScript/Next.js frontend, Postgres backend, webhooks on every event, AI-agent-aware design (they ship "Plane Intelligence" — agents that act on work items). Licence permits internal commercial use.

**Blockers for DHG:**
- Its Django/Postgres schema is opinionated and will NOT cohabit with our 64-table Registry schema without namespace collisions or a separate DB.
- Auth is OIDC-provider-based, not Cloudflare JWT header trust — we would be running two auth layers in parallel.
- Frontend is a separate Next.js app, not drop-in components — we would either iframe it (ugly, auth friction) or rebuild the views anyway.
- **AGPL-3.0 § 13 (the "SaaS loophole closer")** applies to any modified Plane we expose over a network. Internal-only use is permissible but any CME grant package generated with Plane in the loop creates ambiguity if we ever let external reviewers access the UI.

**Disposition:** **Inspiration-only.** Borrow the work-items/cycles/modules data model and the webhook event taxonomy. Do not fork or run alongside.

### 3.2 Huly (https://github.com/hcengineering/platform)
**What it is:** All-in-one Linear/Jira/Slack/Notion alternative, TypeScript + Svelte. 25.4k stars, very active. Native velocity/burndown metrics. Plugin SDK + REST + WebSocket typed API client.

**Strengths:** Feature-rich, modern, actively developed. Burndown is native.

**Blockers for DHG:**
- **License is EPL-2.0**, not MIT as the plan file states — correct this. EPL-2.0 is weak copyleft (file-level) and is commercially permissive, but note the correction.
- **Svelte frontend (33.6%)** — completely incompatible with our Next.js + shadcn/ui + CopilotKit stack. We'd be shipping two frontend stacks.
- **v7 migrated from MongoDB to CockroachDB exclusively** — not Postgres, not pgvector. Cannot reuse our Registry DB. Would add Elasticsearch + MinIO + Kafka containers.
- Own auth (email/password or token); no Cloudflare JWT path.

**Disposition:** **Reject.** Wrong frontend stack + wrong database is two non-negotiables failed.

### 3.3 OpenProject (https://www.openproject.org)
**What it is:** Mature Rails-based PM platform, GPL-3.0, REST API v3, webhook plugin, native sprint burndown charts. Enterprise backing.

**Strengths:** Burndown math is battle-tested. REST + webhooks are complete. Mature RBAC model inside the app. Can run in Docker.

**Blockers for DHG:**
- Ruby on Rails server-rendered + Angular frontend — zero overlap with Next.js 16.
- Own Postgres schema, separate database required.
- Auth is LDAP/SAML/OIDC, not Cloudflare JWT header pass-through.
- Burndown plugin has known longstanding bugs (community topics #34437, #1711 show "burndown chart not displayed" issues persisting across releases — **unverified** as to whether fixed in latest).

**Disposition:** **Inspiration-only.** Borrow the burndown calculation (remaining story points per sprint, ideal linear burn-down reference line).

### 3.4 Leantime (https://github.com/Leantime/leantime)
**What it is:** AGPL-3.0, PHP/Blade, neurodivergent-focused (ADHD/autism/dyslexia-friendly UX). 9.5k stars, v3.7.3 Mar 2026.

**Strengths:** The neurodivergent UX angle is genuinely thoughtful and worth studying for our own design.

**Blockers for DHG:**
- **MySQL/MariaDB only** — immediate disqualification. Cannot reuse Postgres/pgvector.
- PHP/Blade stack — incompatible with Next.js.
- Own session auth.

**Disposition:** **Reject.** UX inspiration optional.

### 3.5 Taiga (https://github.com/taigaio)
**What it is:** MPL-2.0, Django + AngularJS/CoffeeScript, Scrum + Kanban. 2026 release notes mention Docker stability and OAuth improvements.

**Strengths:** MPL-2.0 is the least viral of the copyleft options (file-level).

**Blockers for DHG:**
- **AngularJS + CoffeeScript frontend** — a decade-old stack. Any UI integration is dead on arrival.
- Heavy runtime (Django + Celery + RabbitMQ + Postgres + Redis) — duplicates infra we already have.
- Own Postgres schema.

**Disposition:** **Reject.**

### 3.6 Vikunja (https://vikunja.io)
**What it is:** AGPL-3.0, Go backend + Vue frontend, solid REST + webhook API, JWT auth, Postgres/MySQL/SQLite.

**Strengths:** Clean Go API. Docker single-container deployment. Postgres support means DB reuse is *theoretically* possible, but schema is still separate.

**Blockers for DHG:**
- Vue frontend, not React/Next.js.
- JWT auth is its own issuer, not Cloudflare Access JWT trust.
- No per-project RBAC in the shape of `security_project_access`.
- No burndown chart native; no embeddings.
- **Webhooks are fire-and-forget (no retry on failure)** — documented limitation. A LangGraph agent relying on webhooks for status changes would silently drop events.

**Disposition:** **Reject.**

### 3.7 Focalboard (https://github.com/mattermost-community/focalboard)
**What it is:** Was a Trello/Notion alternative, MIT-licensed.

**Blockers for DHG:**
- **Standalone project archived by Mattermost Aug 28, 2024.** Actively seeking a maintainer; none found as of search date. The Mattermost plugin variant lives on at `mattermost/mattermost-plugin-boards` but requires running Mattermost.
- Dead code.

**Disposition:** **Reject — unmaintained.**

### 3.8 Tuleap, Wekan, Kanboard (abbreviated)
- **Tuleap** (GPLv2, PHP, MySQL, Enalean-backed): Burndown + REST API exist, but PHP/MySQL stack mismatch is fatal for DHG's integration goals.
- **Wekan** (MIT, Meteor + MongoDB): Active but legacy Meteor stack. Reject.
- **Kanboard** (MIT, PHP): In maintenance mode, plugin ecosystem stale. Reject.

---

## 4. Recommendation — Build Fresh, with Borrowed Ideas

**Path: Proceed with the plan file as written (Phases 0 → 6 on existing DHG stack).**

Concrete rationale:
1. **Non-negotiables cannot be met by any candidate.** Cloudflare Access JWT trust, reuse of `security_users`/`security_project_access` RBAC, reuse of Registry Postgres + pgvector, Next.js 16 + shadcn/ui + Tremor + CopilotKit, and a LangGraph-agent-driven write path are all table stakes. No candidate clears all five; most clear zero.
2. **The infrastructure is already 70% built.** Registry API + Cloudflare JWT + pgvector + OTel tracing + LangGraph Cloud cron + dhg-pdf-renderer already exist. The new code is ~8 tables, ~16 endpoints, one LangGraph agent, and four React views. The plan's 4–6 week estimate is credible.
3. **Agent-first design is the differentiator and the blocker.** None of these tools were designed to have an LLM agent continuously writing evidence rows with confidence scores. Bolting that onto any of them is as much work as building fresh — with the added burden of fighting the tool's own status machinery.

**Ideas to borrow (inspiration-only, no code copied):**
- **From Plane:** work-item / cycle / module hierarchy; webhook event names (`item.created`, `item.status_changed`, `item.evidence_added`); OIDC-compatible endpoint naming conventions.
- **From OpenProject:** sprint burndown math — remaining story points per day + ideal linear burn line + projected completion date extrapolation.
- **From Leantime:** neurodivergent-friendly UX cues — emotion-based prioritization, contextual reminders, low-distraction default views. This dovetails with Stephen's ADHD cognitive assistant project and is worth cross-pollinating.
- **From Huly:** the "one tab, four synchronized views" URL pattern.

**Next steps (unchanged from plan Phase 0):**
1. Stephen approves this memo.
2. Proceed to Phase 0.1 (design spec) and Phase 0.4 (worktree branch cut).
3. Do **not** install Plane/Huly/anything alongside — keep the container count flat.

---

## 5. Hidden Costs / Gotchas

1. **AGPL-3.0 § 13 ("SaaS loophole closer") matters even for internal use.** If DHG ever exposes a Plane/Vikunja/Leantime UI to an external CME reviewer, grant sponsor, or auditor through the Cloudflare tunnel, AGPL obligations to publish modified source code are triggered. This is a non-obvious trap — "internal only" is fine until marketing decides to demo it. Build-fresh avoids the question entirely. Internal-only MPL-2.0 (Taiga) and GPL-3.0 (OpenProject) are safer but still bring file-level/project-level copyleft obligations on any patches.
2. **Dual-auth maintenance burden.** Running a second auth stack (Plane's OIDC, OpenProject's SAML, Huly's token) alongside Cloudflare Access means every new role, every user off-boarding, and every audit must be performed twice. Stephen's $600/hr rate makes this easily the single largest hidden cost — estimated 4–8 hours/month indefinitely.
3. **DB schema cohabitation.** Running a candidate's Postgres in the same `dhg-registry-db` instance with its own schema is possible but invites future migration conflicts; running a separate DB means a new container, new backup policy, new pgvector extension install per DB, new Prometheus exporter. None is acceptable under the "no new containers" plan constraint.
4. **UI framework mismatch is the killer.** Rails/Angular (OpenProject), AngularJS/CoffeeScript (Taiga), Svelte (Huly), PHP/Blade (Leantime), Vue (Vikunja), Meteor (Wekan) — six different frontend stacks across the candidate set. Even Plane's Next.js/TS would require adopter-specific theming to match DHG brand (Graphite/Purple/Orange, Inter, 60-30-10 layout). Brand consistency is a real requirement for a Fortune-500-positioned product, and drop-in UIs break it.
5. **Webhook reliability.** Vikunja's fire-and-forget webhook delivery (no retry) is a silent-data-loss class of bug for an agent-driven system. Plane's HMAC-signed webhooks are better. Our own write path (LangGraph agent writing direct to Registry DB) has no webhook at all — a correctness advantage.
6. **"AI agent" claims in Plane's marketing should be treated as marketing, not capability.** Unverified whether Plane's AI agents meet DHG's needs (structured output, confidence scoring, evidence linking, LangSmith-compatible tracing). Worth a 2-hour spike before committing to "Plane is at least future-compatible" as an assumption.

---

## 6. Sources

Accessed 2026-04-19:

- [Plane — AI-native project management](https://plane.so/) + [Plane Developer Docs](https://developers.plane.so/) + [Plane Self-Hosted](https://plane.so/self-hosted) + [makeplane/plane on GitHub](https://github.com/makeplane/plane) + [Plane OIDC SSO docs](https://developers.plane.so/self-hosting/govern/oidc-sso)
- [Huly Platform on GitHub](https://github.com/hcengineering/platform) + [huly-selfhost](https://github.com/hcengineering/huly-selfhost) + [Huly MongoDB config (DeepWiki)](https://deepwiki.com/hcengineering/huly-selfhost/7.4.3-mongodb-configuration) + [Huly API issue #6996](https://github.com/hcengineering/platform/issues/6996)
- [OpenProject API & Webhooks docs](https://www.openproject.org/docs/system-admin-guide/api-and-webhooks/) + [openproject-webhooks GitHub](https://github.com/opf/openproject-webhooks) + [OpenProject community burndown bugs](https://community.openproject.org/work_packages/34437)
- [Leantime on GitHub](https://github.com/Leantime/leantime) + [Leantime selfhostedworld](https://selfhostedworld.com/software/leantime)
- [Taiga Wikipedia](https://en.wikipedia.org/wiki/Taiga_(project_management)) + [ServerSpan 2026 Taiga runbook](https://www.serverspan.com/en/blog/how-to-self-host-taiga-project-management-on-your-linux-vps-in-2026-full-docker-nginx-runbook-for-teams)
- [Vikunja webhooks docs](https://vikunja.io/docs/webhooks/) + [go-vikunja/vikunja on GitHub](https://github.com/go-vikunja/vikunja) + [Vikunja DeepWiki](https://deepwiki.com/go-vikunja/vikunja)
- [Focalboard archival issue #5038](https://github.com/mattermost-community/focalboard/issues/5038) + [focalboard GitHub](https://github.com/mattermost-community/focalboard)
- [Tuleap Community Edition](https://www.tuleap.com/tuleap-community-edition-free-jira-alternative/)
- [Wekan status](https://wekan.fi/status/) + [Kanboard community discussion](https://kanboard.discourse.group/t/new-to-kanboard/2423)
- AGPL analysis: [FOSSA — AGPL 101](https://fossa.com/blog/open-source-software-licenses-101-agpl-license/) + [Mend — SaaS loophole in GPL](https://www.mend.io/blog/the-saas-loophole-in-gpl-open-source-licenses/) + [Open Core Ventures — AGPL non-starter](https://www.opencoreventures.com/blog/agpl-license-is-a-non-starter-for-most-companies)

---

## Version History

- v1 (2026-04-19) — Initial memo. Recommendation: build fresh. Awaiting Stephen review.
