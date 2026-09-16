---
title: "Deferred-backlog triage corrected by advisor review; Open WebUI made the DHG portal, then found unable to host apps; the CME rebuild researched end to end (2026-09-14 to 2026-09-16)"
registry_id: 58821801-f3d8-4823-9667-d6e76da9ddc5
---

# Triage, portal, and the CME rebuild research — 2026-09-14 to 2026-09-16

## Story

The session opened on 2026-09-14 with the scheduled deferred-backlog triage. The premise was wrong from the first query: 42 open items for this project, not 113 (that figure was every project combined). I presented a triage that Stephen called unintelligible, rewrote it in plain language grouped by decision instead of category, and then, at his request, ran three adversarial reviewers over it. They found five wrong facts I had presented as verified: the Portage images existed (I had looked in the wrong folder), the old ship copies were already archived, Open WebUI's knowledge bases held eleven documents (I had read a legacy field), and three "done" test items only had service-level tests that never touch the HTTP routes. The security reviewer found something worse: the Grafana admin password is a literal in the tracked override file, and the repository is public, so it has been readable since February. My "copy the container value into Doppler" recommendation would have made the leak official. Rotation is now plan item 5.8, critical. The reviewers also found the multi-database exporter does not cover the registry (so retiring the old exporter needs a module added first), three more LAN-open unauthenticated ports (old exporter, Ollama, Qdrant), and an untracked docs tree with 196 broken links. The triage stands as a corrected file awaiting Stephen's decisions; nothing in the registry was changed.

On 2026-09-16 Stephen asked what Open WebUI is for and whether anything on GitHub justified replacing it. From the container: one user, two chats ever, both on the setup day, seven releases behind. Twelve projects surveyed with GitHub API numbers and a documentation pass: no justified switch, LibreChat the only defensible alternative at the cost of four new services. Stephen then set the direction: Open WebUI is the DHG home portal for every app, service, model, observability view, settings page and the Docusaurus site. Recorded as a decision and in memory. The follow-up research against the 0.11.3 documentation and source found the hard limit: Open WebUI cannot host external apps as pages, has no custom navigation or home page, is not an identity provider, and above fifty users a DHG logo needs an enterprise license. Three portal shapes are documented; my recommendation is the inversion, the Next.js app as the shell with Open WebUI as the chat application inside it. Track 9 is on hold until Portage 1.0, so this is a decision Stephen owes, not a build.

The rest of the day was the CME rebuild research. Stephen's framing: the CME business decides Digital Harmony's next three months, two clients with money are waiting, the plan must be exhaustive, deferrals need his written approval, and when the build starts he will ask for a one-shot autonomous run. Planning only until Portage 1.0 ships. Six research passes ran, each verified at its most consequential claim before being written to `docs/research/`: the original pipeline's feature inventory and gap list (review off by default, zero structured outputs, zero tool calling, two dead agents, spoofable review identity, no full-pipeline graph despite CLAUDE.md); the copilot-route ecosystem (Pydantic AI 2.43 with capabilities and first-party durable execution, AG-UI as the common wire, assistant-ui's own AG-UI adapter ending CopilotKit lock-in, CopilotKit's free runtime versus paid persistence); the reuse inventory (eight prompts worth keeping as domain knowledge, the intake template as a schema, the style rules as a linter, three registry tables to carry forward as-is); the accreditor and supporter requirements (ACCME's April 2026 urgent alert and January 2026 AI guidance, verified in the PDF, make named human review, version traceability and tool disclosure accreditation-critical; a 25-item testable checklist); the durable-execution choice (DBOS, zero added infrastructure, Langfuse named in its docs; approval waits live in Postgres message history, never in a parked workflow; AG-UI cannot stream from a durable run today); and Open WebUI's real extension surface. The comparison document scores the copilot route over the original on every criterion and lays out the recommended shape.

Stephen added two deliverables after the plan: a client proposal from Digital Harmony Group and an investor package (financials deferred with his written approval), plus a retire-and-clean-up workstream. Model choice was discussed: Fable 5.1 for judgment-heavy research and review, Opus 5 for build phases. The work continues in a new session as a `/ship` through the planning phases only.

## Numbers

- Research files written: 6 under `docs/research/2026-09-16-*.md`, plus the corrected triage (3 versions) and the plan.
- Advisor reviews: 3 agents on the triage (6 closure changes, 1 critical security finding, 4 new items); research agents: 7.
- Captures this session: decisions 3, insights 6 (plus 2 by a research agent), deferred items 5, corrections 1, session reports 1.
- Registry changes from the triage: none (awaiting Stephen).
- Open item counts: 42 open for dhg-ai-factory; if the corrected triage is accepted, 20.

## Noticed, not acted on

- CLAUDE.md's ARCH line names four orchestrators including a full pipeline; three exist. Fix with the 6.3 cleanup.
- The CodeGraph index does not include `langgraph_workflows/dhg-agents-cloud/src/prompts/`, and its explore tool drifted to unrelated frontend files twice today.
- CopilotKit's docs call its open-source core Apache 2.0 while the repository LICENSE is MIT; needs written clarification before it carries CME revenue.
- The Mac's LAN address (10.0.0.238) in the port guard is a DHCP lease; a reservation would make the rule durable.
