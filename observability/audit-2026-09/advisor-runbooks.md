# Advisor review — runbooks-as-code / remediator plan (2026-09-05)

Read-only review. Evidence gathered from `services/remediator/remediator.py`, `registry/seed_runbooks.py`, `registry/api.py:350-437`, `registry/incident_endpoints.py`, `frontend/src/lib/incidentsApi.ts`, the seven alert rule files, `docs-site/projects/dhg-ai-factory/runbooks/alerts.md`, `docker inspect dhg-remediator`, and SELECT-only queries against `dhg_registry`.

## VERDICT: REJECT as shaped — approve a narrower, notify-first scope (below)

## Findings

| Sev | Finding | Evidence |
|---|---|---|
| CRITICAL | The remediator has executed zero remediations in its lifetime and cannot execute any today; the plan spends its budget making a daemon "work" whose only product has been 2.6M action rows. | 45 seeded steps = 24 diagnostics, 11 remediations, 10 manual. Of the 11: T1 restart is reachable only via `ContainerHighCPU` (severity warning, filtered at `api.py:397`); T2/T5/T6 are `mode=none`; T3/T4/T8/T13 are `approval` and write "PENDING APPROVAL" rows nobody reads (819,872 such rows); T10/T11 are `auto` but no alertname maps to T10/T11 in `ALERT_TRIGGER_MAP`. |
| CRITICAL | Destructive-step classification is by the step's *action text*, not the command; a fixed step set still runs `docker image prune -a -f` (T6) and `echo 3 > /proc/sys/vm/drop_caches` (T3) as "diagnostic" because the words "Prune"/"Clear" are not in `DESTRUCTIVE_MARKERS`. `docker image prune` is not in `BLOCKED_PATTERNS` either. | `remediator.py:57` (`DESTRUCTIVE_MARKERS`), `:48-56` (`BLOCKED_PATTERNS`), `seed_runbooks.py:57,96`. |
| CRITICAL | Approval surface before auth = unauthenticated command execution. Incident endpoints have no auth dependency (only `get_db`); `GET /api/incidents/runbooks` returns 200 from the LAN with no credentials; codegraph finds no callers of `get_current_user` outside `security_endpoints.py`. An "approve" endpoint or Telegram bot added on top of this lets any LAN client trigger `docker restart`. | `incident_endpoints.py:9-33`; live curl `GET 10.0.0.251:8011/api/incidents/runbooks → 200`. |
| HIGH | Blast radius once `{container}` resolution is "fixed": `RegistryApiDown → T8 → docker restart dhg-registry-api` restarts the API the remediator itself polls and records to; `HostMemoryHigh → T3 → docker stop <top consumer>` on a single host during beta can stop Postgres or the frontend. Today these resolve to job labels (`node-exporter`, `registry-api`) and fail harmlessly. | `api.py:386` (`service = labels.name or labels.job`), `remediator.py:141-144`, `seed_runbooks.py:56,123`. Active backlog: T8 455, T4 420, no-trigger 106, T3 74, T13 59. |
| HIGH | Coverage is mostly human-only; the plan's "generator" is mostly a docs generator. 45 rules = 10 critical / 22 high / 13 warning. The webhook creates incidents only for critical/high (`api.py:397`), so 13 warning alerts (incl. `ContainerHighCPU`, `ContainerHighMemory`, `DataDiskHigh` — three of the mapped ones) never reach the remediator. Plausibly automatable ≈16 (container-down restarts: PrometheusTargetDown, OllamaDown, PortageApiDown, AlertmanagerDown, LokiDown, AlloyDown, FrontendDown, OpenWebUIDown, GrafanaDown; memory: ContainerMemoryLeak, ContainerHighMemory, HostMemoryHigh, HostSwapHigh; disk: RootDiskHigh, DataDiskHigh, LokiStoreGrowth; DB: PostgresConnectionsHigh). Human-only ≈29 (pipeline self-checks, latency/error-rate, DLQ, GPU, PostgresDown/FatalError, SecretLeak, all five Loki rules, all five dh40801 rules — remote host, no socket, CrashLoop). | Rule files under `observability/prometheus/`, `rules.d/`, `loki/rules/fake/alerts.yml`. |
| HIGH | `ALERT_TRIGGER_MAP` is stale and partly wrong: 16 keys; `ZombieProcessesHigh` is not a rule anywhere; 30 of 45 alertnames have no T-rule; T15/T16/T17 are mapped but have no `incident_runbooks` row (DB has T1–T14 only); `SecretLeakDetected → T14` whose runbook is "External 5xx rate" (runs `docker logs dhg-registry-api` for a secret leak). | `api.py:350-368`; `SELECT trigger_rule FROM incident_runbooks` → T1..T14. |
| HIGH | Estimate is off by ~5x. 45 YAML runbooks with honest content (the hand-written page is 1,535 lines / 45 `###` sections), a safe harness, a coverage map and a generator are not 1.5 h. Four parallel agents on 240 + 418 lines of code is coordination cost, not parallelism. | `wc -l alerts.md` = 1535; `seed_runbooks.py` 240, `remediator.py` 418, `test_remediator.py` 221. |
| MEDIUM | Generation direction: the DB is not an editing surface today. `Runbook` type and `listRunbooks()` exist in `incidentsApi.ts:104,200` but have zero callers; `frontend/src/components/incidents/` has no runbook component. `seed_all` already overwrites every field on upsert (`seed_runbooks.py:216-219`), so any future frontend edit would be clobbered. YAML → DB is acceptable only if the DB is declared a cache; otherwise DB → docs. Do not replace `alerts.md` — it is the human runbook every rule's `runbook_url` points at and is better than the 14 step sets. Append a generated "Automation" block per section instead. | codegraph `listRunbooks` callers = none; `ls components/incidents`. |
| MEDIUM | Harness "execute every diagnostic step live" is unsafe as stated: T4 step 2 walks `/proc/[0-9]*` in a shell loop, T3/T13 fan out `docker stats`, T9–T11 run `psql` against the production DB, and the misclassified prune/drop_caches steps above would run. Classify by command prefix allowlist (`docker logs|inspect|ps|stats --no-stream`, `curl` GET to Prometheus/Loki, `psql -c "SELECT ..."`), run only allowlisted steps live, everything else against fixtures (45 alert label sets → resolved command → allowlist verdict). | `seed_runbooks.py:69,54-55,134-160`. |
| MEDIUM | Telegram inline-keyboard approve/deny = a new long-running process (polling or webhook) holding a bot token with execute authority, chat-id allowlist, replay protection, and a public ingress. A frontend button → `POST /api/incidents/{id}/actions/{aid}/approve` that the remediator polls is ~60 lines, no new process, and sits behind Cloudflare Access already. Smaller and safer — but only after the auth finding above is closed. | `observability/alertmanager/*.yml` has one receiver (registry webhook); Telegram is not configured. |
| MEDIUM | `incident_events` growth is the remediator's growth: `event_type=action` = 2,615,191 rows ≈ `incident_actions` 2,615,016; 24.5K rows/day steady until today's fix (9,582 yesterday, 667 today). Cleanup A must delete the mirrored events or 678 MB stays. Any future step set that writes one row per step per incident re-creates the problem; write one enriched action per incident state change. | `SELECT event_type, count(*)` / per-day counts. |
| MEDIUM | Docker socket: mounted `rw=false`, which is meaningless for a socket (the API is fully writable); container runs as root (`Config.User` empty). If the shape becomes notify/enrich, the socket can go: `docker logs/inspect/ps` are replaceable by Loki queries and cAdvisor/Prometheus queries over HTTP. | `docker inspect dhg-remediator` mounts. |
| LOW | Context claim "every executed step in the last 3 hours failed" is not exact: 248 success / 409 failed rows by `dhg-remediator` in 3 h (`docker logs`/`docker ps` steps exit 0 even with a wrong name). Still 409 failures and 0 remediations. | SELECT on `incident_actions`. |
| LOW | Loki rules live under `observability/loki/rules/fake/` (tenant "fake"); a YAML-per-alert generator must not assume one rules root. | path. |

## Answers to A–G

**A.** Diagnostic value is the real value (24/45 steps; the 11 remediations have never run). A shell-executing daemon with a socket is the wrong shape for that: the same information is a Loki/Prometheus query or a Grafana deep link. Restart-on-down for user-facing containers on a single host during beta is not something to automate before there is an operator who can be paged. Make the remediator an enricher: one action row per incident state change with the numbers, forwarded to Telegram once configured.

**B.** Treat YAML as source and DB as a cache (it already is — seed overwrites). Generate an appended automation block into `alerts.md`; do not regenerate the page.

**C.** Allowlist by command prefix; live only for allowlisted read-only prefixes; fixtures for everything else. `test_remediator.py` is the right home.

**D.** ≈16 automatable / ≈29 human-only; 13 never reach the daemon due to the severity gate. Yes — "human only" for the majority is the honest outcome, and it turns the plan into a docs+notifier plan.

**E.** Frontend button + registry endpoint the remediator polls. Blocked until incident endpoints have auth.

**F.** One Fable agent, sequential, with a review gate after the notifier rewrite. No Opus split — there is no generation-heavy part large enough to justify it.

**G.** See findings: stale map, no runbook UI, events mirror actions, no auth, socket unnecessary in the notify shape.

## Scope I would approve

1. Remediator → enrich/notify: drop execution of any step matching restart/stop/kill/terminate/prune/drop_caches regardless of mode; keep an allowlisted read-only set (or replace with HTTP queries and drop the socket); one action row per state change. Verify: 24 h with `remediator_actions_total{kind="auto_remediation"}` = 0 and action rows/day < 200.
2. Fix `ALERT_TRIGGER_MAP`: remove `ZombieProcessesHigh`, correct `SecretLeakDetected`, add or drop T15–T17, decide the warning gate explicitly. Verify: every key is a live alertname and has a runbook row.
3. Runbooks-as-code for the ≈16 automatable alerts only, YAML → seed (DB as cache), generated "Automation" block appended per section of `alerts.md`; coverage table (16/29) in the same page. Human-only alerts get no YAML.
4. Fixture harness in `test_remediator.py` + a `verify-runbooks.sh` that runs only allowlisted prefixes live.
5. Approval surface: not now. Prerequisite: auth on `/api/incidents/*`. Then frontend button, not Telegram bot.

## Corrected estimate

Approved scope: ~4 h wall-clock, one Fable agent sequential, ~400–500K tokens, review gate after step 1. Plan as written: 8–12 h, 1.5–2M tokens, and step 5 is blocked on auth regardless.
