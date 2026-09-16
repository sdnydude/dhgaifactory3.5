# Deferred backlog triage — 2026-09-14 (v2: first plain-language pass, before advisor review — superseded)

Reconstructed after the fact: this version was overwritten without being saved first. Kept for the record; the current file corrects five wrong facts found by the advisor review.

There are 42 open deferred items for this project. (The plan said 113; that number was every project combined.)

The four possible outcomes: Close as done · Close, won't do · Do this week · Keep.

## Close as done (10 items)
- Promote the ship workflow to v5 and archive the old versions. (Claimed three stale copies still in the commands folder — wrong; they were already archived.)
- Build a session close-out skill for memreg. (Superseded by /wrap.)
- Stop orphaned Claude session processes from piling up. (Cron reaper exists.)
- Move 17 registry records from the old project name to the new one.
- Fix the age histogram in the deferred-items stats.
- Add a response schema to the feedback-loop health endpoint.
- Write tests for the security endpoints. 44 tests.
- Write tests for the knowledge-base search endpoint. 22 tests. (Wrong: service-level only.)
- Write tests for the inference endpoints. 21 tests. (Wrong: service-level only.)
- Write tests for the doc-pages endpoints. 10 tests. (Wrong: service-level only.)

## Close, won't do (7 items)
- "B4 smoke deferred."
- "E2E TEST: seat A2 dead-wiring verification."
- Install two packages into the LangGraph virtual environment. (Half wrong: apscheduler is a registry dependency.)
- Fix about five type-annotation mismatches in the LangGraph agents.
- Add debug logging to one memreg hook script.
- Sync project docs into Open WebUI's knowledge bases. (Premise wrong: the KBs hold 11 files.)
- Re-load 11 documents into Open WebUI's knowledge bases. (Wrong: already done.)

## Do this week (6 items)
- Fix the stale Grafana admin password in Doppler by copying the container's value. (Wrong direction: the value is a literal in a public repo; rotate instead.)
- Remove three broken image links from a Portage docs page. (Wrong: the images exist; only the strict flag needs restoring.)
- Upgrade the Synology to DSM 7.2 and turn on immutable snapshots. (Undersized: an attended job.)
- Retire the old Postgres exporter with a plaintext password. (Premise wrong: the multi exporter does not cover the registry DB.)
- Shrink the session-start briefing to under 200 tokens.
- Clear the 151 Dependabot security alerts. (Undersized: three unpatchable, one four-major pip bump.)

## Keep (19 items, becomes 9)
- Move medkb to dh40801 (6.2); LangGraph to Langfuse (6.3); inbox page LangGraph call (6.3); feedback-loop default name (6.3 — actually dead code); transcribe refactor (6.4); ufw (5.5).
- memreg reporting suite → Track 6.5.
- Ten "no tests" items + doc-pages delete-by-id → Track 6.6.
- PostHog → Portage project.

Tally: 42 → 15.
