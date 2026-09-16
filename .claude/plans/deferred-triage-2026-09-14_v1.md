# Deferred-backlog triage — dhg-ai-factory — 2026-09-14 21:00 ET

Source: `GET /api/deferred-items?project_name=dhg-ai-factory&status=open` = **42 open** (37 older than 30 d).
The "113 open" in the plan was the all-projects count (115 today across portage, memreg, …).
Every recommendation below was checked against the live code, hooks, containers or registry tonight; the evidence is on the line.
Nothing changes until Stephen ticks. Tick = apply that recommendation; write a different word after the item to override.

Legend: **DO NOW** (small, this week) · **DONE** (close resolved, evidence given) · **WONT_FIX** (close) · **KEEP** (stays open, with where it lives)

## api (1)
- [ ] 6c68a9ef low — doc_pages DELETE by id / by source_file. **KEEP**, low. Still only `DELETE /project/{name}` (routes at doc_pages_endpoints.py:51-154). Small registry hygiene item; bundle with the next registry ship.

## config (3)
- [ ] b181b350 low — install langchain-openai + apscheduler into the LangGraph `.venv` for pyright. **WONT_FIX**. Packages still absent, but Track 6.3 replaces these LangGraph modules with Pydantic AI; pyright-only impact, venv would drift again.
- [ ] b12ec6ce high — promote ship_v4 to /ship, archive v1/v2/v4. **DONE** (promotion landed 2026-07-04: `.claude/commands/ship.md` is the 8-phase v5; `ship_v1.md`, `ship_v2-baseline.md` in `.claude/archive/commands/`). Leftover on close: `ship_v1.md`, `ship_v2.md`, `ship_v4.md` still also sit in `.claude/commands/` — move them to the archive in the same commit.
- [ ] 1b6ae512 high — Doppler `GF_SECURITY_ADMIN_PASSWORD` stale vs live Grafana. **DO NOW** (operator, one line, no output shown): set the Doppler secret to the container's value: `doppler secrets set GF_SECURITY_ADMIN_PASSWORD --project dhg-monitoring --config dev "$(docker inspect dhg-grafana --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^GF_SECURITY_ADMIN_PASSWORD=' | cut -d= -f2-)" >/dev/null`. Verify: `curl -s -o /dev/null -w '%{http_code}' -u "admin:$(doppler secrets get GF_SECURITY_ADMIN_PASSWORD --project dhg-monitoring --config dev --plain)" http://10.0.0.251:3001/api/org` = 200.

## docs (1)
- [ ] f69fabb4 medium — Portage e2e-verification page references 3 images that do not exist; build masked with `onBrokenMarkdownImages: 'warn'`. **DO NOW** (docs commit): drop the 3 dead `inline-edit/*.png` references, restore the Docusaurus default (throw), `docs-site/build-docs.sh` green. Belongs to Portage docs but lives in this repo's docs-site.

## frontend (1)
- [ ] 12bf2817 medium — `/inbox` still calls LangGraph Cloud via `listPendingReviews` (inbox-list.tsx:5, inbox-master-detail.tsx:9). **KEEP** — already scoped into Track 6.3 (plan line 6.3 names it). No separate item needed; close this one as duplicate when 6.3 ships, or keep as the tracker. Recommend keep.

## infra (10)
- [ ] e373dec7 low — "B4 smoke deferred". **WONT_FIX** (synthetic test row).
- [ ] a6d34749 medium — build a dhg-memreg end-session skill. **DONE** — superseded by the global `/wrap` (handoff + capture sweep + session summary + memory + git close-out), used last night.
- [ ] 49d2cb97 medium — shrink `session-start-kb-briefing.sh` to <200 tokens. **KEEP**, reassign `project_name` → `dhg-memreg` (the file lives there; 3.9 KB script, tonight's SessionStart briefing was still ~1.5 KB). Real, not urgent.
- [ ] 7b6dc1a1 low — add `debug()` logging to `pre-tool-kb-search-inject.sh`. **WONT_FIX** (0 debug calls today, hook works, cosmetic consistency).
- [ ] 807a25d6 medium — dhg-transcribe refactor. **KEEP** = Track 6.4.
- [ ] 6de6cf42 medium — Open WebUI KB sync (oikb + ENABLE_KB_EXEC). **WONT_FIX** unless Open WebUI is a knowledge path you use: all 3 KBs still hold 0 files (webui.db tonight), and medkb + the registry KB are the knowledge stack. Your call; recommendation is close.
- [ ] 333d0551 high — stop orphaned Claude session trees re-accumulating. **DONE** — crontab has `reap-stale-claude-sessions.sh --execute` daily 06:00, idle ≥ 4 d; 6 MCP/LSP helper processes alive tonight, all attached to live sessions.
- [ ] c60008ba medium — relocate medkb to dh40801 + GPU ingestion. **KEEP** = Track 6.2 (the 3 medkb containers still on .251).
- [ ] 8baeab4c high — DSM 7.2 upgrade + immutable snapshots. **DO NOW** = plan 4.5: pool is back to normal (raidStatus 1 tonight), so the blocker is gone. I drive `SYNO.Core.Upgrade` via the DSM API; NAS reboot timing is yours.
- [ ] bbc17a92 medium — ufw default-deny as its own project. **KEEP** = plan 5.5 (added last night).

## langgraph (3)
- [ ] 0ee89fca low — ~5 pyright annotation mismatches. **WONT_FIX** — modules replaced by Track 6.3; runtime correct.
- [ ] d571a7d6 medium — migrate 15 LangGraph modules to Langfuse tracing. **KEEP** = Track 6.3.
- [ ] 146c8096 low — `feedback_loop.py:94` default `project_name="dhg-cme-research-agent"` (still there tonight). **KEEP**, fold into 6.3 (same module set); close as duplicate of d571a7d6 if you prefer one row.

## observability (2)
- [ ] a54005bf medium — memreg reporting suite + capture-rate observability. **KEEP** — only `memreg-daemon.json` exists; you asked for this. Candidate Track 6.5 after 6.1.
- [ ] 4d2d9975 low — evaluate PostHog for Portage product analytics. **KEEP**, reassign → `portage` (trigger is Portage external users; docs-site already runs a PostHog wizard integration, untracked `docs-site/posthog-setup-report.md`).

## other (2)
- [ ] a28356ba medium — re-ingest 11 docs into Open WebUI KBs. **WONT_FIX** together with 6de6cf42 (same call: KBs empty, Open WebUI not the knowledge path). If you keep 6de6cf42, keep this too.
- [ ] 49a7c6e5 medium — "E2E TEST: seat A2 dead-wiring verification". **WONT_FIX** (synthetic row).

## registry (3)
- [ ] f0f39473 medium — migrate 17 records from `dhgaifactory3.5` to `dhg-ai-factory`. **DONE** — `stats?project_name=dhgaifactory3.5` = 0 rows tonight.
- [ ] 98ab8c17 low — age-histogram universe mismatch. **DONE** — `deferred_items_service.py:241-259` filters `status == "open"` for every bin; tonight's histogram sums to exactly the 42 open.
- [ ] 2bab10e7 low — missing `response_model` on feedback-loop health. **DONE** — OpenAPI shows `FeedbackLoopHealthResponse` on `/api/feedback-loop/health`.

## security (2)
- [ ] c1a51062 medium — postgres-exporter `DATA_SOURCE_NAME` plaintext in the override. **DO NOW**, reshaped: `dhg-postgres-exporter` (single, plaintext DSN env) still runs and is still scraped as job `postgres`, alongside `dhg-postgres-exporter-multi` (6 auth modules, secrets in its own config). Step: confirm the multi exporter covers the registry DB; if so retire the single exporter + its scrape job (override edit via a script, like 5.1/5.2); else move the DSN into the multi exporter's config. Small, bundles with the next observability chore.
- [ ] 1ebb7a6f high — 151 Dependabot alerts. **DO NOW** as one chore ship. Breakdown tonight (open): frontend npm 81 (2 critical, 30 high), docs-site npm 55 (2 critical, 27 high), registry pip 13 (5 high), session-logger pip 2. Plan: `npm audit fix` per lockfile + build/test, then registry `requirements.txt` bumps with the 745-test suite; anything that needs a major bump gets its own line.

## testing (14) — the May "no test coverage" sweep
Since May: security 44 tests, kb 22, inference 21, doc_pages 10 (service-level), agent_sessions 4 (update path only), claude 1. Eight files still at zero.
- [ ] ae1873fc high — security_endpoints. **DONE** (`test_security.py`, 44 tests).
- [ ] 46bb304e high — kb_endpoints. **DONE** (`test_kb_service.py`, 22).
- [ ] 50785b46 high — inference_endpoints. **DONE** (`test_inference_service.py`, 21).
- [ ] 0aeb4a86 medium — doc_pages_endpoints. **DONE** (`test_doc_pages_service.py`, 10).
- [ ] ecd5a7ff medium — agent_sessions_endpoints (4 tests, update path only). **KEEP → consolidate** (below).
- [ ] 1fc3b402 low — claude_endpoints (1 test). **KEEP → consolidate**.
- [ ] 8be09d70 medium — corrections_endpoints (0). **KEEP → consolidate**.
- [ ] b1385cfc medium — decision_logs_endpoints (0). **KEEP → consolidate**.
- [ ] f32480fa medium — insights_endpoints (0). **KEEP → consolidate**.
- [ ] 1f9e3995 medium — ship_sessions_endpoints (0). **KEEP → consolidate**.
- [ ] f1c05d5c low — memory_metrics_endpoints (0). **KEEP → consolidate**.
- [ ] 2adc8173 low — research_endpoints (0). **KEEP → consolidate**.
- [ ] aa7cc48f low — frontend_specs_endpoints (0). **KEEP → consolidate**.
- [ ] 40c301e6 low — antigravity_endpoints (0). **KEEP → consolidate**, lowest: Antigravity IDE capture may itself be retired; decide in the consolidated item.
- [ ] NEW — "Registry endpoint test coverage: 10 memreg capture/CRUD endpoint files (8 at zero, 2 partial)" replaces the ten rows above (they close with `resolution_reason: consolidated into <new id>`). One ship, one baseline delta; pattern `registry/test_incident_endpoints.py`.

## Apply plan (after ticks)
1. `PATCH /api/deferred-items/{id}` with `status` + `resolution_reason` for every DONE / WONT_FIX; `project_name` PATCH for the two reassignments; POST the consolidated testing item, then close its ten.
2. Working-tree pieces of DO NOW items (ship archive move, Portage image refs) go on one `chore/deferred-triage-2026-09-14` branch, `--no-ff`.
3. Re-run `GET /api/deferred-items/stats?project_name=dhg-ai-factory`; expected open count = KEEP rows + new consolidated row + DO NOW rows not yet finished. Report the number.

## Tally if every recommendation is accepted
DONE 10 · WONT_FIX 7 · DO NOW 5 · KEEP 20 (10 of which collapse into 1) → **open goes 42 → 16** (5 do-now + 10 keep + 1 consolidated), with Tracks 6.2/6.3/6.4/5.5 each holding one row.
