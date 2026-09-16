# Deferred backlog triage — 2026-09-14 (corrected after advisor review)

42 open items for this project. Three reviewers checked my first pass and found five wrong facts and several wrong sizes. This version fixes them. Earlier versions are saved as `_v1` (evidence) and `_v2` (first plain-language pass).

Nothing has been changed yet. Reply "all", or name the items you want handled differently.

---

## First: one security problem the review found

The Grafana admin password is written as a literal in `docker-compose.override.yml`. That file is tracked in git, and this repository is public on GitHub. The password has been readable by anyone since February.

What limits the damage: the public Grafana address is behind Cloudflare Access, so an outsider still needs a login there. But anyone on the home LAN can reach Grafana directly on port 3001 and log in as admin with the published value, and Grafana admin can read the registry database.

What to do this week, in this order:

1. Set a new admin password on the running Grafana (its admin API or `grafana-cli admin reset-admin-password`; changing the environment variable alone does not change an existing admin user).
2. Put the new password in Doppler.
3. Change the tracked override file to read `${GF_SECURITY_ADMIN_PASSWORD}` from the environment instead of the literal. The file is permission-denied to my tools, so this goes through a script like the one used for 5.1 and 5.2.
4. Decide separately whether to scrub the old value from git history. Since it is already public, rotation is what matters; a history rewrite is optional.

This replaces the earlier "copy the container's value into Doppler" recommendation, which would have made the published password official.

---

## Close as done (8 items)

- [ ] **Promote the ship workflow to v5 and archive the old versions.** Done July 4. The old versions are already in the archive folder. No file moves needed (my earlier note about stale copies was wrong).
- [ ] **Build a session close-out skill for memreg.** `/wrap` covers it, except one piece: posting the session transcript to the session logger. That piece becomes part of Track 6.5 below.
- [ ] **Stop orphaned Claude session processes piling up.** A cron job reaps stale sessions daily at 6:00 and ran on the 12th and 13th. Note: about 46 helper processes are alive right now, all attached to three live sessions, so the reaper is working but sessions themselves are heavy.
- [ ] **Move 17 registry records to the new project name.** Zero records left under the old name.
- [ ] **Fix the age histogram in deferred-item stats.** Code counts open items only; tonight's numbers add up.
- [ ] **Add a response schema to the feedback-loop health endpoint.** Present. The real path is `/api/feedback-loop/health` (the item's `/v1/` path never existed).
- [ ] **Write tests for the security endpoints.** 44 tests exist and drive the routes.
- [ ] **Re-load 11 documents into Open WebUI's knowledge bases.** Already there: 11 files across the three knowledge bases, loaded June 5. I had read a legacy field that this version no longer fills.

---

## Close, won't do (5 items)

- [ ] **"B4 smoke deferred."** Fake row from a test.
- [ ] **"E2E TEST: seat A2 dead-wiring verification."** Fake row from a test.
- [ ] **Fix about five type-annotation mismatches in the LangGraph agents.** Code runs correctly; those modules are replaced by Track 6.3.
- [ ] **Add debug logging to one memreg hook script.** Cosmetic; the hook works.
- [ ] **A wrong default project name in the feedback-loop code.** Dead code. The only file that imports it is not registered as a graph and is imported by nothing. It disappears with Track 6.3.

---

## Your call (1 item)

- [ ] **New: an unbuilt docs tree with 196 broken image links.** `docs-site/docs/` holds 7 markdown files that are not in git and are not built or published (the site only builds `projects/`). Recommend delete. Say "keep" if you want them migrated instead.

## Decided 2026-09-16: Open WebUI is the DHG home portal

Stephen's decision: every DHG app, service, model, observability view, settings page and the Docusaurus site is reached from or built inside Open WebUI. So:

- [ ] **Sync project docs into Open WebUI's knowledge bases.** KEEP. Becomes part of the portal track below.
- [ ] **Upgrade Open WebUI 0.9.6 to 0.11.3.** Moves to "do this week": back up `webui.db`, pin the image tag, turn on OpenTelemetry, move RAG to pgvector. About an hour.
- [ ] **New Track 9, DHG portal on Open WebUI.** Needs a spec before any build: what the extension surface really supports (embedded apps, widgets, control panel, Docusaurus), the license branding clause above 50 users, and how the Next.js frontend relates to the portal.

## Do this week (8 items, all small)

- [ ] **Rotate the Grafana admin password** as described at the top. About an hour including the override script.
- [ ] **Set the docs build back to strict.** All the images exist (I looked in the wrong folder). One config line back to `throw`, run the build, show it green. Half an hour.
- [ ] **Install `apscheduler` into the LangGraph virtual environment.** It is a real registry dependency the type checker cannot see. One pip install, five minutes. (The other package in that item, `langchain-openai`, is not needed; that half closes.)
- [ ] **Shrink the session-start briefing to under 200 tokens.** About an hour. The script lives in the dhg-memreg repo, so the registry record moves to that project.
- [ ] **Close three more LAN-open ports with the guard that shipped last night.** The old Postgres exporter on 9187 serves registry table names and sizes to the whole LAN with no login; Ollama on 11434 and Qdrant on 6333 are also open to the LAN with no login. Adding them to the guard is a constant change, the tests, a reinstall, and one root line. Before adding 11434 and 6333 I confirm nothing on dh40801 uses them (its containers' environments show nothing pointing at them tonight). Grafana on 3001 stays open to the LAN once the password is rotated.
- [ ] **Frontend Next.js critical bump.** One of the four critical Dependabot alerts applies to us: an image-optimization vulnerability in Next.js, fixed in 16.3.3, in range for `npm audit fix`. Do that one now; the rest of Dependabot is Track 8 below.
- [ ] **DSM 7.2 upgrade** stays plan item 4.5, but the reviewer is right that it is an attended job, not an errand: a major upgrade and reboot of the backup target, needing a window clear of the nightly backup and a fallback if the share does not remount. Three to six hours with you present. You pick the day.

---

## Tracked work (19 items become 8 rows across Tracks 5, 6 and 8)

Track 5, same override-script pattern as 5.1/5.2:

- [ ] **5.6 Retire the old Postgres exporter properly.** The newer multi-database exporter does not cover the registry database (it has six modules; registry is not one). Work: add a registry module to its rendered config, add the scrape target, confirm the dashboards and alerts still light up (they key on the service label, so they should), then remove the old container. Two to four hours.

Track 6, reordered on the reviewers' advice:

- [ ] **6.1 Auth on the incident endpoints.** Two additions: the inbox page's remaining LangGraph call moves in here, because 6.1 edits those same two components and doing it later means rework; and an inventory of every client that posts to those endpoints, since at least one script seeds runbooks with no token today. Also add a capture-rate metric before the rollout so the 48-hour observation window can actually show captures failing.
- [ ] **6.2 Move medkb to dh40801.** No code dependency on anything else; sequence it on host availability. Before scheduling, confirm dh40801 actually has the GPU the ingestion plan assumes (Prometheus shows a GPU exporter only on this host).
- [ ] **6.3 LangGraph agents to Pydantic AI and Langfuse.** Unchanged.
- [ ] **6.4 Transcribe pipeline refactor.** Unchanged.
- [ ] **6.5 memreg reporting suite.** Now also includes posting session transcripts to the session logger (the leftover from the close-out item).
- [ ] **6.6 Registry endpoint tests.** Thirteen files, not ten: the three I wrongly called done (KB search, inference, doc-pages) have service-level tests that never hit the HTTP routes. Plus the doc-pages delete-by-id.

Track 8, new, dependency security (was one "clear 151 alerts" item):

- [ ] **8.1 Frontend npm** (81 alerts). Beyond the Next.js bump above, expect some major-version bumps on a Next 16 app.
- [ ] **8.2 docs-site npm** (55 alerts). Two criticals there are in the dev server and build path only; the site is served as static files. Two alerts have no fix available.
- [ ] **8.3 Registry pip** (13 alerts). Includes `cryptography` 46 to 50, a four-major jump, with the full 745-test run. The PyJWT alert does not apply to us (we pin RS256) but the bump is cheap.
- [ ] **8.4 Accept-and-document** the three alerts with no patch (two in docs-site, one in session-logger).

Moves to the Portage project:

- [ ] **Evaluate PostHog for Portage analytics.** Waits for external users; that trigger lives in Portage.

---

## What happens after you answer

1. Every closed item gets its new status and a reason in the registry; the two reassignments get their project name changed; the thirteen test items close into one Track 6.6 item; four new items are recorded (Grafana rotation, open ports, unbuilt docs tree, transcript ingest).
2. Tracks 5.6 and 8 are added to the outstanding plan and Track 6 is reordered.
3. The "do this week" items start with the Grafana rotation.
4. I re-run the stats and report the open count. If you accept everything: 42 open become 20, and every one of the 20 has a week, a track, or a project.
