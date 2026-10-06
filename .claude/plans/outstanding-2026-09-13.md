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
- [x] 1.4 PR #30 merged into master 2026-09-13 20:12 ET (4720e18, --no-ff); main checkout now on master.

## Track 2 — CI red baseline — SHIPPED 2026-09-13 (PR #31, all 10 checks green; ship log 004)

Four pre-existing red jobs on every PR to master:
- [x] 2.1 Validate Docker Compose: `POSTGRES_PASSWORD` has no default → `docker compose config` fails in CI. Fix: `${POSTGRES_PASSWORD:?}` style guard that CI satisfies via a dummy env, or a CI-only `.env.ci`. Verify: job green.
- [x] 2.2 Check Documentation Drift: CLAUDE.md container names out of date vs compose. Fix: regenerate. Verify: `python3 scripts/generate-docs.py --check` exit 0.
- [x] 2.3 Lint Python: 62 ruff findings. Fix: the real ones; `--ignore` only what is deliberate, with a comment. Verify: `ruff check` clean.
- [x] 2.4 Test Registry API: `uuid-ossp` missing in CI Postgres. Fix: `CREATE EXTENSION` in the alembic base migration or a CI init step. Verify: `alembic upgrade head` in CI green.
- [x] 2.5 Run Track 2 as one `/ship` (simple) on its own branch off master after 1.1. Then 1.3 gets a fully green run.

## Track 3 — Items I flagged during the backups ship

- [x] 3.1 ContainerCrashLoop description "copies ContainerMemoryLeak's" — **re-verified 2026-09-13: false.** `alerts.yml` lines 69 and 180 carry distinct descriptions. Closed, nothing to do.
- [x] 3.2 NAS user `claude`: created by Stephen, intentional. Keep. Closed 2026-09-13.
- [x] 3.3 `produce_pg` fifo → coproc. **Dropped** (decided 2026-09-13): fifo path proven by 3 nightly runs + 13/13 drill; coproc adds bash pitfalls (single coproc, fd scoping) for zero behavior gain.
- [x] 3.4 bats setup dedup (a49259f, 40/40, names identical): one `observability/tests/test_helper.bash` (shims, temp dirs, reporter env), three `load` lines. On branch feat/backups-dr-2026-09 before 1.2. Verify: `bats observability/tests` 40/40 with identical test names; CI Shell tests job green on the retargeted PR.

## Track 4 — Backups ship follow-through (NAS / secrets / hardware)

- [x] 4.1 Snapshot schedule on `aifactory-backups`: daily 04:30, keep latest 14, applied 2026-09-13 20:08 ET via `observability/scripts/nas-snapshot-policy.sh` (DSM API; get_schedule next=2026-09-14 04:30 task_id=8; retention policyType=20 recently=14). Verify tomorrow: `SYNO.Core.Share.Snapshot list` shows one snapshot.
- [ ] 4.2 **[device]** Escrow `BACKUP_GPG_PASSPHRASE`: no password-manager CLI on g700data1 (op/bw/pass absent), so the store lives on the Mac. Hand line for the Mac: `doppler secrets get BACKUP_GPG_PASSPHRASE --project dhg-monitoring --config dev --plain | pbcopy`. Verify: entry exists in the manager (only checkable there).
- [x] 4.3 Telegram delivery live 2026-09-13 20:58 ET: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in Doppler dhg-monitoring/dev, Alertmanager rendered with telegram + webhook-and-telegram receivers, reload 200, TelegramDeliveryTest (warning) routed to telegram with no notify errors. Verified: Stephen received "[FIRING:1] TelegramDeliveryTest" on the phone 21:00 ET.
- [x] 4.4 Drive 1 replaced by Stephen 2026-09-13; pool repaired. Verified 2026-09-14 21:00 ET: `raidStatus{raidName="Storage Pool 1"}` = 1, no alerts firing.
- [ ] 4.5 DSM 7.2 upgrade after 4.4 (via DSM API `SYNO.Core.Upgrade`; only consideration is Video Station gone in 7.2.2), then immutable snapshots on `aifactory-backups`. Verify: DSM reports 7.2.x; registry deferred 8baeab4c resolved.

## Track 5 — Observability rebuild follow-through (override / root)

- [x] 5.1 DONE 2026-09-13 20:13 ET via `observability/scripts/override-wave1-edits.sh` (run by me; the script path is allowed, direct reads are not). `docker-compose.override.yml`: dropped `LANGGRAPH_API_URL` / `LANGCHAIN_API_KEY` from registry-api and frontend. Verify: `docker compose config | grep -c LANGGRAPH` = 0.
- [x] 5.2 DONE same run: node-exporter `--no-collector.thermal_zone` (0 thermal_zone errors after recreate; both node-exporter targets up; registry-api healthy).
  5.1+5.2 land together with `observability/scripts/override-wave1-edits.sh` (backup, both seds, config validation, masked before/after, recreate registry-api + node-exporter; sed logic dry-run on a fixture 2026-09-13). One line: `! observability/scripts/override-wave1-edits.sh`
- [x] 5.3 LAN guard for 9090/9093/3100/8080. Runbook's ufw recipe cannot work (ufw disabled; Docker DNAT bypasses INPUT; dh40801 Alloy needs 3100). Built 2026-09-13 22:45 ET: `observability/scripts/docker-user-fw.sh` (DOCKER-USER chain `DHG-LAN-GUARD`, v6 via INPUT; Mac + dh40801:3100 allowed) + `observability/systemd/dhg-docker-user-fw.service` + 4 bats tests (suite 44/44); rules exercised against real iptables in a NET_ADMIN container (apply idempotent, status, remove clean). Runbook §3 rewritten, §1/§2 marked done, `prometheus.yml` cloudflared comment fixed. Open: Mac LAN IP (script default 10.0.0.238; SSH logins also seen from .235/.236/.237, so pin a DHCP reservation first). APPLIED 2026-09-13 22:52 ET by Stephen (unit active, chains as designed). Verified 22:55 ET: loopback + self 9090 = 200; from dh40801: 9090 and 8080 time out, 3100 = 200, 3001 = 200; cadvisor-dh40801 / node-exporter-dh40801 / cloudflared / blackbox-langfuse targets UP; a probe container log line on dh40801 landed in Loki through the guard; frontend `/api/prometheus/api/v1/query` = 200. Mac-side 200 still to be eyeballed by Stephen.
- [ ] 5.6 Retire the old `dhg-postgres-exporter` (plaintext DSN env, LAN-open :9187): add a registry-db auth module + target to the multi exporter's rendered config, confirm dashboards/alerts (keyed on `service`), then remove the container via an override script (registry deferred c1a51062).
- [ ] 5.7 Guard :9187, :11434 (Ollama), :6333 (Qdrant) with the DOCKER-USER guard script after confirming no dh40801 consumer; Grafana :3001 stays LAN-open once its admin password is rotated (triage 2026-09-14).
- [ ] 5.8 **[security]** Rotate the Grafana admin password: literal in tracked `docker-compose.override.yml` in a public repo since 2026-02. Reset on the running instance, new value in Doppler, override reads `${GF_SECURITY_ADMIN_PASSWORD}` via a script; history scrub is a separate decision.
- [ ] 5.5 **[root]** Host firewall (ufw default-deny) as its own item: input = full port map (`reference_port_map.md`) + every host listener (`ss -ltnp`), lock-out-safe rollout (allow 22 first, `ufw --dry-run`, console access at hand). Not folded into 5.3.
- [x] 5.4 cloudflared `--metrics` flags: already in place, found 2026-09-13 22:30 ET. Both units' `ExecStart` carry `--metrics 0.0.0.0:20241` / `:20242`, both listen on `*`, both Prometheus `cloudflared` targets UP. Stale text remains in `docs/OBSERVABILITY_RUNBOOK.md` §1 and the `prometheus.yml` job comment ("DOWN by design"); fix with the 5.3 commit.

## Track 6 — Wave 2 ships (each its own /ship; order fixed)

- [ ] 6.1 Auth on `/api/incidents/*` + approval surface (resume paused auth-wiring ship; spec approved, 18 ACs). Added 2026-09-14: fold in the `/inbox` list swap off the LangGraph SDK (12bf2817; same two components), inventory every client of those endpoints (the runbook seeding script posts with no token), and add a capture-rate metric before the 48 h observe window.
- [x] ~~6.2 medkb relocation to dh40801 + GPU ingestion.~~ CANCELLED 2026-10-02: medkb removed from the stack (PR #32, tag `medkb-parked-2026-10`); registry deferred item c60008ba closed as won't-fix.
- [ ] 6.3 PLANNING NOW, BUILD AFTER PORTAGE 1.0 (Stephen 2026-09-16 11:06 "No just planning"). (research done 2026-09-16: gap list in registry insight 7d9ad700; architecture comparison and recommended shape in `docs/research/2026-09-16-cme-copilot-vs-pipeline.md`; CLAUDE.md ARCH line is wrong — 3 orchestrators, no full_pipeline) REFRAMED 2026-09-16 (Stephen): not a tracing swap but a rebuild of the DHG CME pipeline agents on Pydantic AI + Langfuse. Step one is a critical review of the existing 13 agent graphs + 4 orchestrators against what a medical-education business needs in production (the first build was a good first effort, shallow, never shippable); the existing work informs the new agents and features, it is not ported. Expected faster than the first build. Original line follows. Migrate 15 LangGraph agent modules to Pydantic AI + Langfuse (includes `/inbox` list off the LangGraph SDK, registry 12bf2817). Found 2026-09-13: `REGISTRY_WEBHOOK_SECRET` is blank everywhere (override interpolates an unset shell var; not in .env or Doppler), so `/api/cme/webhook` (LangGraph drive-sync hook) always 401s. Remove endpoint + override line + `NEXT_PUBLIC_LANGGRAPH_API_URL` (frontend) in this ship.
- [ ] 6.3-C Retire and clean up (Stephen 2026-09-16: "get rid of anything that is just not going to be needed once we start building"). Step one is a read-only inventory producing a delete list for approval; deletions only against that list, each with a verification. Known now: `langgraph_workflows/` + the LangGraph Cloud deployment (after the new package passes evals); `agents/` (legacy Docker agents); `web-ui/` (broken legacy UI); LangGraph/LangSmith residue (`/api/cme/webhook` + blank `REGISTRY_WEBHOOK_SECRET`, `NEXT_PUBLIC_LANGGRAPH_API_URL`, `@langchain/langgraph-sdk` + `@assistant-ui/react-langgraph` in frontend, LangSmith `@traceable` in templates/agent-boilerplate); dead registry pieces (4 legacy single-reviewer columns on CMEProject, self-asserting `test_review_workflow.py`, unused `citation_checker`/`registry` graphs); tree hygiene (`.venv-prototype/`, untracked `docs-site/docs/`, stale planning files, CLAUDE.md ARCH line).
- [ ] 6.3-P Client proposal from Digital Harmony Group, derived from the approved 6.3 plan, written for the two waiting CME clients and reusable for others (Stephen 2026-09-16).
- [ ] 6.3-I Investor package derived from the same material. Financials and other items not covered by planning and building are deferred WITH Stephen's written approval (2026-09-16 message) until he reopens them.
- [ ] 6.4 dhg-transcribe pipeline refactor (10 containers, no tests).
- [ ] 6.5 memreg reporting suite: capture-rate metrics, read-side usage, Grafana boards beyond memreg-daemon, periodic summary (registry deferred a54005bf); plus session transcript ingest to session-logger `/sessions/ingest-log` (leftover from a6d34749).
- [ ] 6.6 Registry endpoint test coverage for 13 endpoint files (8 untested, 2 partial, 3 with service-only tests: kb, inference, doc_pages) + doc_pages DELETE by id (consolidates thirteen May deferred items + 6c68a9ef).

## Track 8 — Dependency security (151 Dependabot alerts on master, split per lockfile; triage 2026-09-14)

- [ ] 8.1 Frontend npm (81): Next.js 16.3.3 first (AVIF image-optimization RCE, the one critical that applies), then `npm audit fix`, expect majors on a Next 16 app.
- [ ] 8.2 docs-site npm (55): two criticals are dev-server/build-path only (site served static); two alerts have no patch.
- [ ] 8.3 Registry pip (13): `cryptography` 46 → 50 with the full test run; PyJWT bump cheap, not exploitable (RS256 pinned).
- [ ] 8.4 Accept-and-document the three unpatchable alerts (two docs-site `image-size`, one session-logger `weasyprint`).

## Track 9 — DHG portal on Open WebUI — ON HOLD until Portage 1.0 ships (Stephen 2026-09-16; close). Apps arrive as handoffs from Stephen's team of trusted professionals; Claude continues the build with Stephen after each handoff. 9.0 (upgrade to 0.11.3) may run before the hold lifts.

## Track 9 detail (Stephen 2026-09-16: Open WebUI is the home for all DHG apps, services, models, observability, settings, Docusaurus, control panel)

- [ ] 9.0 Upgrade dhg-open-webui 0.9.6 → 0.11.3 (backup webui.db first; 0.11.0–0.11.2 migration bug fixed in 0.11.3), pin the image tag, ENABLE_OTEL to the OTLP endpoint, VECTOR_DB=pgvector.
- [ ] 9.1 Spec (no build without go): verify Open WebUI's extension surface against the portal needs (embedded app modules, links/widgets, homepage control panel, Docusaurus, observability, user/admin settings) from the 0.11 docs; resolve the license branding clause (>50 end users / 30 d) for a DHG-branded portal with CME learners; define how the Next.js frontend (:3000, /inbox, Mission Control) becomes a module.
- [ ] 9.2 Build phases per the approved spec.

## Track 7 — Deferred-backlog triage (scheduled 2026-09-14 21:00 ET, Stephen)

- [x] 7.1 (2026-09-14 21:00 ET; 42 open, not 113 — that was all projects; advisor-reviewed list in `.claude/plans/deferred-triage-2026-09-14.md`) Pull all open registry deferred items for dhg-ai-factory (113 open, 109 > 30 d as of 2026-09-13). Present as a checkbox list grouped by category with one recommendation each: do now / close done / close wont_fix / keep. No item changes before Stephen decides.
- [ ] 7.2 Apply decisions via the registry API (bearer token, `resolution_reason`), re-run `/api/deferred-items/stats`. Verify: open count matches the list of kept items.

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
