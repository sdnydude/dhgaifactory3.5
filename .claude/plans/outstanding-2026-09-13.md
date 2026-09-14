# Outstanding — everything open as of 2026-09-13 19:50 ET

Owner: Claude, every task. Where an action needs root, a physical hand, or a device I do not have,
the task stays mine: I prepare and dry-run it, and hand exactly one `!` line. Marked **[root]**,
**[physical]**, **[device]**. State changes still wait for a "go" (hard gate).
Every task: action → verify. Ticked as it lands.

## Track 0 — Portage "Create Listing" 500 — RESOLVED 2026-09-13

Root cause (schema drift: API image selected `ebay_returns_accepted`, `ebay_return_days`, `ebay_handling_days`;
DB lacked them). Fixed by Stephen. Verified 2026-09-13 21:58Z: all three columns present, `portage-api`
restarted 16:09Z, zero 5xx in the last 6 h, `POST /listings` → 201 at 21:46Z and 21:57Z.

- [x] 0.1–0.5 columns added, API restarted, listing creates succeed (Stephen).
- [ ] 0.6 **C** Portage backlog item: schema-parity check at API startup so an image never boots ahead of its DB again (bug-fix capture for this incident goes to the portage project, not dhg-ai-factory).

## Track 1 — Land PR #30 (backups + DR)

- [x] 1.1 Merge PR #29 (7e94d64, --no-ff, PR #29 MERGED) into master locally: `git checkout master && git merge --no-ff feat/observability-rebuild-2026-09 && git push`. Verify: master contains 4d3c87c; PR #29 shows merged.
- [x] 1.2 Retarget (done 2026-09-13 20:00 ET; base=master): `gh pr edit 30 --base master`. Verify: PR #30 base = master, GitHub Actions run starts.
- [x] 1.3 Shell tests: pass (2026-09-14T00:06Z run). Lint Python, Check Documentation Drift, Validate Docker Compose, Test Registry API: fail, pre-existing (Track 2).
- [ ] 1.4 Merge PR #30 the same way (`--no-ff`). Verify: `git log master -1` = merge commit; backups cron unaffected (scripts run from working tree on the merged branch).

## Track 2 — CI red baseline (blocks a fully green #30 run; small ship, own branch)

Four pre-existing red jobs on every PR to master:
- [ ] 2.1 Validate Docker Compose: `POSTGRES_PASSWORD` has no default → `docker compose config` fails in CI. Fix: `${POSTGRES_PASSWORD:?}` style guard that CI satisfies via a dummy env, or a CI-only `.env.ci`. Verify: job green.
- [ ] 2.2 Check Documentation Drift: CLAUDE.md container names out of date vs compose. Fix: regenerate. Verify: `python3 scripts/generate-docs.py --check` exit 0.
- [ ] 2.3 Lint Python: 62 ruff findings. Fix: the real ones; `--ignore` only what is deliberate, with a comment. Verify: `ruff check` clean.
- [ ] 2.4 Test Registry API: `uuid-ossp` missing in CI Postgres. Fix: `CREATE EXTENSION` in the alembic base migration or a CI init step. Verify: `alembic upgrade head` in CI green.
- [ ] 2.5 Run Track 2 as one `/ship` (simple) on its own branch off master after 1.1. Then 1.3 gets a fully green run.

## Track 3 — Items I flagged during the backups ship

- [x] 3.1 ContainerCrashLoop description "copies ContainerMemoryLeak's" — **re-verified 2026-09-13: false.** `alerts.yml` lines 69 and 180 carry distinct descriptions. Closed, nothing to do.
- [x] 3.2 NAS user `claude`: created by Stephen, intentional. Keep. Closed 2026-09-13.
- [x] 3.3 `produce_pg` fifo → coproc. **Dropped** (decided 2026-09-13): fifo path proven by 3 nightly runs + 13/13 drill; coproc adds bash pitfalls (single coproc, fd scoping) for zero behavior gain.
- [x] 3.4 bats setup dedup (a49259f, 40/40, names identical): one `observability/tests/test_helper.bash` (shims, temp dirs, reporter env), three `load` lines. On branch feat/backups-dr-2026-09 before 1.2. Verify: `bats observability/tests` 40/40 with identical test names; CI Shell tests job green on the retargeted PR.

## Track 4 — Backups ship follow-through (NAS / secrets / hardware)

- [x] 4.1 Snapshot schedule on `aifactory-backups`: daily 04:30, keep latest 14, applied 2026-09-13 20:08 ET via `observability/scripts/nas-snapshot-policy.sh` (DSM API; get_schedule next=2026-09-14 04:30 task_id=8; retention policyType=20 recently=14). Verify tomorrow: `SYNO.Core.Share.Snapshot list` shows one snapshot.
- [ ] 4.2 **[device]** Escrow `BACKUP_GPG_PASSPHRASE`: no password-manager CLI on g700data1 (op/bw/pass absent), so the store lives on the Mac. Hand line for the Mac: `doppler secrets get BACKUP_GPG_PASSPHRASE --project dhg-monitoring --config dev --plain | pbcopy`. Verify: entry exists in the manager (only checkable there).
- [ ] 4.3 Telegram delivery: `TELEGRAM_BOT_TOKEN` now in Doppler dhg-monitoring/dev (2026-09-13). **[device]** `getUpdates` returns 0 updates: one message must be sent to the bot from the phone before the chat id exists. Then `doppler secrets set TELEGRAM_CHAT_ID`, `observability/scripts/render-alertmanager.sh`, reload :9093. Doppler currently has neither value. Verify: `amtool config routes` shows the telegram receiver; test alert lands on the phone.
- [ ] 4.4 **[physical]** Drive 1 replacement (SATA HDD ≥ 5.5 TB). I trigger the repair via DSM API once the disk is seated and confirm status. Verify: `NasRaidDegraded` clears; dashboard NAS row green.
- [ ] 4.5 DSM 7.2 upgrade after 4.4 (via DSM API `SYNO.Core.Upgrade`; only consideration is Video Station gone in 7.2.2), then immutable snapshots on `aifactory-backups`. Verify: DSM reports 7.2.x; registry deferred 8baeab4c resolved.

## Track 5 — Observability rebuild follow-through (override / root)

- [ ] 5.1 **[root-equivalent: file is permission-denied to my tools]** `docker-compose.override.yml`: drop `LANGGRAPH_API_URL` / `LANGCHAIN_API_KEY` from registry-api and frontend. Verify: `docker compose config | grep -c LANGGRAPH` = 0.
- [ ] 5.2 **[same]** override: node-exporter `--no-collector.thermal_zone`. Verify: thermal_zone errors gone from `docker logs dhg-node-exporter`.
  5.1+5.2 land together with `observability/scripts/override-wave1-edits.sh` (backup, both seds, config validation, masked before/after, recreate registry-api + node-exporter; sed logic dry-run on a fixture 2026-09-13). One line: `! observability/scripts/override-wave1-edits.sh`
- [ ] 5.3 **[root]** ufw rules per `docs/OBSERVABILITY_RUNBOOK.md` (WP9): I write `observability/scripts/ufw-apply.sh`, dry-run with `--dry-run`, hand one `! sudo …` line. Verify: `sudo ufw status numbered` matches the runbook table.
- [ ] 5.4 **[root]** cloudflared `--metrics` flags: `/etc/cloudflared/config.yml` is root:root 644; I prepare the edited copy in scratch, diff it, hand one `! sudo cp … && sudo systemctl restart cloudflared` line. Verify: Prometheus target `cloudflared` up.

## Track 6 — Wave 2 ships (each its own /ship; order fixed)

- [ ] 6.1 Auth on `/api/incidents/*` + approval surface (resume paused auth-wiring ship; spec approved, 18 ACs).
- [ ] 6.2 medkb relocation to dh40801 + GPU ingestion.
- [ ] 6.3 Migrate 15 LangGraph agent modules to Pydantic AI + Langfuse (includes `/inbox` list off the LangGraph SDK, registry 12bf2817).
- [ ] 6.4 dhg-transcribe pipeline refactor (10 containers, no tests).

## Watch (no action unless red)

- [x] First Sunday restore drill 2026-09-13 04:00 ET: 13/13 PASS.
- [x] Nightly backups 09-11, 09-12, 09-13: all targets ok, mirror ok.
- [x] Firing alerts: only `NasRaidDegraded` (expected until 4.4).

## Sequence

1. On "go": 3.4 bats dedup (commit + push to #30) → 1.1 merge #29 → 1.2 retarget #30 → 5.1 + 5.2 override edits (registry-api, frontend, node-exporter recreate) → 4.3 Telegram → 4.1 snapshot schedule via API.
2. Track 2 `/ship` next session; then 1.3 + 1.4.
3. 5.3 + 5.4 prepared now, each lands on one `!` line.
4. 4.4 when the disk arrives; 4.5 after it; 4.2 on the Mac.
5. Track 6 starts with 6.1 after #30 merges.
