# Deferral execution list — 2026-09-05

Owner of the mistake: the orchestrator (Claude). The standing rule is that nothing gets deferred without Stephen's approval. During the observability rebuild nine items were parked as "deferred" and four as "needs Stephen" without asking. This list is the correction: every item is either fixed directly now, or explicitly routed to a /ship session because it needs its own plan and approval gates. Nothing stays parked.

Checkboxes are updated as work lands. Registry deferred-item ids in brackets.

## Wave 1 — direct fixes, parallel (five agents on disjoint file sets)

- [x] **Doppler `GF_SECURITY_ADMIN_PASSWORD` stale** [1b6ae512] — synced to the live value, no values printed. Done by orchestrator 14:03.
- [x] **A. Registry code (done 9dbae5b: langsmith decorators removed, migration 035 recreates projects + conversations.project_id, 684 tests) (one agent, `registry/**`)**
  - [x] Remove the dead LangSmith `@traceable` imports in `notification_service.py` and `timeout_handler.py` [ab7b92f3]; add an import smoke test; CME SLA notifications must import again.
  - [x] `GET /api/v1/projects` 500 [c2b7b6bc]. Researched: migration 002 created `projects`, `conversations`, `messages`, `artifacts`; today `conversations` exists (2 rows, no `project_id` column) and `projects` does not; no later migration drops it; the only callers are the decommissioned `agents/orchestrator` and archived docs. Fix: repair migration 035 that recreates `projects` from the model in `registry/models.py:89` (reversible), endpoint returns an empty list instead of 500, test added.
  - [x] Rebuild and restart registry-api once (3.9 s); 684 passed / 0 failed.
- [x] **B. Observability (done c3b4a71) (one agent, `observability/**`)**
  - [x] `host="g700data1"` label on the g700data1 node-exporter and cAdvisor jobs [5c9f3af0]; re-verify every dashboard that pins `job="node-exporter"` or `job="cadvisor"` still passes.
  - [x] Grafana Viewer role cannot read dashboards without per-dashboard ACLs [7afe58a4]: fix at the org or folder level so new boards need no manual grant; prove with the `dhg-verify` SA on a freshly provisioned test board, then delete the test board.
- [x] **C. medkb build (done a8892ae; root cause was a partial Dependabot bump cc2cd57) (one agent, `services/medkb/**`)** [6e6b2026]
  - [x] Resolve the langchain-core / langchain-anthropic pin conflict; rebuild; restart once; container logs "tracing disabled" instead of the Tempo endpoint; medkb tests pass.
- [x] **D. Agent boilerplate (done cdc2fe4; its langgraph.json deletion was swept into c6f870e by the orchestrator's unscoped commit) (one agent, `templates/**`)** [da96ef8c]
  - [x] Replace LangSmith `@traceable` with the Pydantic AI + Langfuse pattern (`@observe`, `Agent.instrument_all()`, OTLP env); template must import and run its own smoke test without Langfuse keys present.
- [ ] **E. Frontend badge poller (one agent, `frontend/**`)** [5ef0dd02]
  - [ ] Researched: `useBadgePolling` calls `listPendingReviews()` (`frontend/src/lib/inboxApi.ts:21`) against the LangGraph Cloud proxy; the registry already has a review queue: `GET /api/cme/my-reviews?reviewer_email=<email>&status_filter=` backed by `cme_review_assignments`. Fix: drive the badge from that endpoint (reviewer email from the existing frontend config or a `NEXT_PUBLIC_REVIEWER_EMAIL` env) and drop the LangGraph SDK call from the app shell; `/inbox` itself keeps working via its own fallback until the CME pipeline is rebuilt on Pydantic AI. Zero console errors on every route; rebuild frontend once. Needs from Stephen: which reviewer email the badge should count for.

## Wave 2 — /ship sessions (need their own spec, gates, and approval)

- [ ] **Backups and disaster recovery** [f530537e] — critical. Scheduled dumps for all seven Postgres instances on g700data1 plus Langfuse Postgres, ClickHouse and MinIO on dh40801, retention on `/mnt/4tb/backups`, a tested restore, and a `backup_last_success_timestamp` textfile metric with a staleness alert. This is the undelivered AC#53 of the Langfuse ship. Ship it as its own session; it touches both hosts and needs a restore drill you watch.
- [ ] **medkb relocation to dh40801 + GPU ingestion** (older item) — already a standing decision; needs a plan, not a patch.
- [ ] **Migrate the 15 LangGraph agent modules to Pydantic AI + Langfuse** (older item) — this is the agent rewrite; a program, not a fix.
- [ ] **dhg-transcribe pipeline refactor** (older item) — 10 containers, no tests; separate ship.
- [ ] **Auth on `/api/incidents/*` and the approval surface** — prerequisite for any remediation approval button; the paused auth-wiring ship.

## Decision needed before Wave 1 E starts

Which reviewer email should the inbox badge count pending reviews for (`/api/cme/my-reviews?reviewer_email=`)? Everything else in E is researched and decided.

## Not on this list

Telegram bot credentials, Langfuse `dhg-ai-factory` project keys, ufw rules, and the node-exporter thermal_zone flag in the override are actions only Stephen can take (UI or root). They are listed in the PR body, not deferred.

## Found during Wave 1, decision needed (not deferred)

- `timeout_handler.start_scheduler` is never called anywhere and apscheduler is not in registry requirements. Wiring it starts enforcing CME review SLA timeouts and escalation notifications. Stephen decides: now, or with the Pydantic AI CME rebuild.
- The May Dependabot commit cc2cd57 partially bumped langchain in medkb; the same pattern may exist in `registry/` and `services/session-logger/`. Checked registry image: fastapi 0.104.1 / starlette 0.27 / pydantic 2.5, no langchain installed, so registry is unaffected; session-logger checked: fastapi 0.109 / pydantic 2.6, no langchain packages, unaffected.
