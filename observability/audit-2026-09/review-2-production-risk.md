# Adversarial Review 2 — Production Risk

Reviewer 2 of 4. Read-only. Scope: assume the Phase 1 audit's proposed removals and fixes ship — what breaks? And what did the audit mark dead/unconsumed that is in fact still consumed?

Method: live queries against Prometheus (10.0.0.251:9090), Loki (:3100), the registry API (:8011), `docker inspect` / `docker logs`, `docker --context dh40801`, and repo/config text search. No state was changed.

Severity: **CRITICAL** = outage or data loss. **HIGH** = breaks a consumer or a live-product signal. **MEDIUM** = needs a follow-up change. **LOW** = note.

---

## Part A — Refutations: things the audit called dead that are alive

### A1. `LOKI_URL` on dhg-registry-api IS consumed. D10 is wrong. — HIGH (as a fact error)

The audit (§6 D10) lists `LOKI_URL` under "nothing / vestigial." It has a live reader:

- `registry/logs_chat_service.py:30` — `LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100")`, used at `:52` (`/loki/api/v1/label/container/values`) and `:108` (`/loki/api/v1/query_range`).
- Wired into the live app: `registry/logs_chat_endpoints.py:22` imports it; `registry/api.py:221,261` includes the router.
- Live route confirmed in the running container's OpenAPI: `POST /api/logs/chat` is present in `http://10.0.0.251:8011/openapi.json`.
- Frontend surface exists at `frontend/src/app/api/logs-chat/`.
- Audit table `logs_chat_audit` exists (`registry/models.py:782`, migration `registry/alembic/versions/032_add_logs_chat_audit.py`).

Mitigating fact: the env value is `LOKI_URL=http://loki:3100`, identical to the code default, so deleting the env var alone would not break the feature today. The risk is the reasoning, not the byte: D10 asserts "no reader found," and any later change that acts on that belief (renaming the Loki service, moving registry off `dhg-network`, dropping the setting from a new deploy) silently kills the Loki-backed log-chat feature with no alert, because `registry_errors_total{error_type="logs_chat_failed"}` is not on any dashboard.

**Evidence:** `registry/logs_chat_service.py:30,52,108`; `registry/api.py:221,261`; `curl http://10.0.0.251:8011/openapi.json` → `/api/logs/chat`; `docker inspect dhg-registry-api` → `LOKI_URL=http://loki:3100`.

### A2. `registry_errors_total` is NOT "0 series ever." P9 is wrong. — MEDIUM

The audit (§5 P9) says the metric has had 0 series ever. Prometheus disagrees:

```
/api/v1/series?match[]=registry_errors_total       -> 2 series
query at t-7d                                      -> 2 results, value 1
query now / t-1d / t-14d / t-30d / t-60d           -> 0 results
```

It is a labeled counter: no child series exists until the first `.labels(...).inc()`, and the child resets on container restart. It had a real sample on ~2026-08-28 and the registry has since restarted. The metric works; it is simply rarely incremented and never graphed. Declaring it dead and deleting it would remove the only error counter the registry has, right when §7 G5 says the registry has no error signal at all.

**Evidence:** `curl -s 'http://10.0.0.251:9090/api/v1/series?match[]=registry_errors_total'` → 2 series; `query?query=registry_errors_total&time=<now-7d>` → `value 1`.

### A3. `memreg_dlq_depth` is not "declared, never populated." G3's diagnosis is wrong. — MEDIUM

Same pattern, but it matters more because G3 is filed CRITICAL:

```
query memreg_dlq_depth at t-30d  -> 1 series, value 1
query memreg_dlq_depth at t-14d  -> 1 series, value 0
query now                        -> 0 results
```

Direct scrape of `dhg-memreg-agent` (172.20.0.22:8020/metrics) shows `# HELP memreg_dlq_depth Current DLQ depth by pipeline (was unlabeled pre-P2; sum() for total)` and `# HELP memreg_captures_total Capture POSTs` — both declared, neither with a child series, while the sibling unlabeled counter `memreg_dlq_dropped_total 0.0` does publish.

So `MemregDLQBacklog` **has been firable** and the memreg pipeline is healthy right now. The actual defect is narrower and different from what the audit describes: after any daemon restart the gauge disappears until the next DLQ event, so a DLQ backlog that predates the restart is invisible to the alert. A fix framed as "the metric is never populated, wire it up" will produce the wrong change.

**Evidence:** `curl http://172.20.0.22:8020/metrics | grep '^# HELP memreg'`; Prometheus point-in-time queries above.

### A4. Loki stream census: 39 containers, not 16. `portage-api` is logging. P11 is partly wrong. — LOW

`sum by (container) (count_over_time({container=~".+"}[24h]))` returns **39** containers with a stream in 24h, including `portage-api` (2,281 lines), `portage-db` (562), `portage-rembg` (8,582), `portage-e2e-api-1` (5,666). The audit's §5 P11 says "16 of 42" and names `portage-app` and `dhg-frontend` as silent.

The two named silences hold — `portage-app` and `dhg-frontend` both exist as running containers and neither appears in the 24h census. But the 16/42 figure understates coverage and the phrase "portage-app: nothing" should not be generalised to Portage, whose API is logging normally.

**Evidence:** Loki `/loki/api/v1/query`, 24h census; `docker ps -a --format '{{.Names}}'`.

### A5. `ollama.service` is disabled and inactive, not merely "installed." G6's premise needs updating. — MEDIUM

```
systemctl is-enabled ollama.service -> disabled
systemctl is-active  ollama.service -> inactive
docker port dhg-ollama             -> 11434/tcp -> 0.0.0.0:11434
/usr/local/bin/ollama              -> present, 38 MB, Jun 4
/etc/systemd/system/ollama.service -> present
```

The container owns :11434. The host unit cannot start on boot. The residual path to a repeat of the 2026-08-15 port theft is a manual `systemctl start` or a package upgrade re-enabling the unit — lower probability than the audit implies, but not zero, and nothing detects it.

**On the audit's proposed detection (blackbox body match on a container-only model tag) — feasibility is UNVERIFIED and possibly false.** The container's model store is a docker volume, `/mnt/4tb/docker/volumes/dhgaifactory35_ollama-data/_data -> /root/.ollama`, separate from the host store at `/usr/share/ollama` (mode 750, owner `ollama`, unreadable without sudo). If the host store still holds any of the 15 container tags — plausible, since host ollama predates containerisation — a body match on a model name would return 200 from *both* and detect nothing. The discriminator must be validated against the actual host store before it is built.

**Evidence:** commands above; `docker inspect dhg-ollama` mounts; `curl http://10.0.0.251:11434/api/tags` → 15 tags.

---

## Part B — What breaks if the proposed removals ship

### B1. Removing the static `registry-api` scrape job kills a CRITICAL alert and a live frontend page. — HIGH

§5 P1 proposes collapsing the double scrape. Consumers keyed on `job="registry-api"`, which **only the static job produces** (docker-sd emits `job="docker-sd"`):

| Consumer | Location | Effect if static job removed |
|---|---|---|
| `RegistryApiDown`, severity **critical**, `for: 1m` | `observability/prometheus/alerts.yml:83` — `up{job="registry-api"} == 0` | becomes a permanently-dead rule (a 4th one). Coverage degrades to the generic `PrometheusTargetDown` (`alerts.yml:53`, `up == 0`) at **high / 2m** — a real downgrade in both severity and detection time for the most important service in the estate. |
| dhg-registry-api panel 31 (Process Memory) | dashboard JSON, only job-pinned panel | No data |
| Frontend `/dashboards` page | `frontend/src/components/dashboards/data.ts:242,244,247,273,275` | 5 PromQL strings pin `job="registry-api"` |

Conversely, removing **docker-sd** is worse: it is the *only* discovery for `dhg-session-logger` (no static job) and it supplies `job="memreg"` via the relabel at `prometheus.yml:163-166`, which `memreg-daemon.json` keys on **13 times**. So docker-sd must stay.

Net: keeping docker-sd and dropping the static jobs breaks fewer consumers, **but `RegistryApiDown` must be rewritten in the same change or the estate silently loses its only critical down-alert.** `vs-engine` is clean — `vs-engine.json` has zero `job=` selectors and nothing keys on `service="vs-engine"`.

**Evidence:** `prometheus.yml:27-33,61-67,143-170`; `alerts.yml:53,83`; per-dashboard `job=` extraction; `curl /api/v1/query?query=up{job="docker-sd"}` → registry-api, session-logger, vs-engine only.

### B2. The frontend `/dashboards` page is already dead and its top three cards can never work. — HIGH

`frontend/src/app/dashboards/page.tsx` consumes `frontend/src/components/dashboards/data.ts`, which queries:

- `sum(rate(http_requests_total{job="registry-api"}[1m]))` (`:242`, `:273`)
- the same with `status=~"5.."` (`:244`)
- `histogram_quantile(0.95, ... http_request_duration_seconds_bucket{job="registry-api"} ...)` (`:247`, `:275`)
- `traces_spanmetrics_latency_bucket{service="dhg-langgraph-agents"}` (`:265`) and `traces_spanmetrics_calls_total{...}` (`:279`)

Live check: `http_requests_total` → **0 series**. `traces_spanmetrics_calls_total` → **0 series**. So a live, user-facing Next.js page is rendering empty tiles today, and the audit's §4 finding ("registry exposes no HTTP metrics at all," `registry/api.py:298`) means no dashboard edit can fix it — but the audit never connects that to the frontend page, and §6 does not list `data.ts` as a consumer of anything. This is a visible-surface defect (global CLAUDE.md §7) that Phase 1 did not surface.

Additional coupling: if D7 (remove Tempo) ships, the two `traces_spanmetrics_*` cards go from "empty" to "permanently unfixable," and `LG_SERVICE_SELECTOR` at `data.ts:19` becomes dead code in a live bundle.

**Evidence:** `frontend/src/components/dashboards/data.ts:19,242-279`; `frontend/src/app/dashboards/page.tsx`; `curl '/api/v1/series?match[]=http_requests_total'` → `[]`.

### B3. D2 is understated: the two registry LangSmith importers are ALREADY broken in production. — HIGH

The audit rates D2 "low risk; import only." The live container tells a different story:

```
docker exec dhg-registry-api pip show langsmith  -> WARNING: Package(s) not found
docker exec dhg-registry-api python -c "import notification_service" -> ModuleNotFoundError: No module named 'langsmith'
docker exec dhg-registry-api python -c "import timeout_handler"      -> ModuleNotFoundError: No module named 'langsmith'
```

`langsmith` is not in `registry/requirements.txt` (16 lines, verified). The imports at `registry/notification_service.py:22` and `registry/timeout_handler.py:18` are **unguarded**. CodeGraph confirms nothing else imports either module (`codegraph_callers notification_service` → only `timeout_handler.py`; `check_sla_timeouts` → only its own file).

So the CME review workflow's SLA timeout handler (R3 24-hour SLA), auto-escalation (R4), and HOLD notifications (R5) are **not running and cannot run** in the current image. This is a live functional outage in a pharma-grade compliance path, not an observability nit — and it is invisible because §7 G5 confirms the registry has no error signal.

Answer to the specific question asked: removing `langsmith` from registry requirements changes nothing, because it was never there. The correct finding is the inverse — the code assumes a dependency the image does not ship.

**Evidence:** commands above; `registry/requirements.txt`; `registry/notification_service.py:22`; `registry/timeout_handler.py:18`.

### B4. D6 / D7 (medkb OTLP, Tempo) — safe today, and confirms 9.2. — LOW

`docker logs dhg-medkb-api --since 168h` = 60,432 lines, of which **40,322 are `GET /metrics`** (Prometheus) and **20,109 are `GET /v1/healthz`** (healthcheck). **Zero `/v1/query` requests in 7 days.** This settles UNVERIFIED item 9.2 in favour of "never invoked," not "silent export failure."

Corroborated by `.claude/ship-state_v10.md:31`: "Move medkb to dh40801 … Verified safe: ZERO consumers in the codebase, 8 MB of data (sample seed only)." CodeGraph shows every `medkb.*` import is internal to `services/medkb/`.

Residual: `OTEL_ENDPOINT=http://dhg-medkb-api`'s value is `http://dhg-tempo:4318` (confirmed on the container). If Tempo is deleted while that env stays set, medkb's 9 `traced_node` sites will attempt exports to a nonexistent host. Whether that degrades quietly or raises is unverified (would require invoking `/v1/query`, a state change). Sequence the env removal with the Tempo removal.

**Evidence:** `docker logs dhg-medkb-api --since 168h`; `docker inspect dhg-medkb-api` → `OTEL_ENDPOINT`; `.claude/ship-state_v10.md:31`.

### B5. P6 (delete promtail config) leaves the runbook lying. — MEDIUM

`observability/promtail/promtail-config.yml` has no code consumer, but `docs/OBSERVABILITY_RUNBOOK.md` still presents Promtail as the live log shipper at `:15` (component table), `:29` (`docker compose ps | grep …promtail…`), `:85` ("Promtail config: observability/promtail/promtail-config.yml"), `:143` ("Verify Promtail running: `docker logs dhg-promtail`"), and `:154` (`docker compose restart … dhg-promtail`).

The runbook is **already** wrong — Alloy replaced Promtail on 2026-08-25 and `dhg-promtail` does not exist, so `:154` fails today. Deleting the config file without the doc edit converts a wrong runbook into a wrong runbook with a dangling path. Same class: `docs/DHG_AI_FACTORY_BRIEF.md:168,239,482` lists `dhg-promtail` as healthy.

**Evidence:** grep of `docs/`; `docker ps -a` has no promtail container.

### B6. `.claude/commands/grafana-dashboards.md` points new work at a broken reference dashboard. — MEDIUM

Beyond the dead-tree reference the audit found at `.claude/commands/observability-engineer.md:48,326`, the dashboard-authoring command names the broken dashboards as templates:

- `grafana-dashboards.md:463` — "`…/json/dhg-core-golden.json` — reference dashboard"
- `grafana-dashboards.md:464` — "`…/json/docker-overview.json` — container metrics reference"

`dhg-core-golden.json` is the 6-of-8-targets-dead dashboard (§3). Any dashboard scaffolded from that command inherits its metric-name drift. This is a live authoring path, not documentation.

### B7. P4 — excluding node-exporter is safe; raising the threshold is not. — MEDIUM

Top containers by `count_over_time({level="error"}[24h])`:

| container | error lines / 24h |
|---|---|
| dhg-node-exporter | **708,212** |
| dhg-ollama | 7 |
| dhg-grafana | 3 |
| portage-api | 1 |

Only four containers emit `level="error"` at all, and non-node-exporter error volume is **11 lines/day**. Two consequences the audit does not draw:

1. **Excluding `dhg-node-exporter` from the two Loki rules masks nothing.** Safe.
2. **Raising the thresholds above the node-exporter floor (2,554 lines/5m) masks everything.** A genuine incident producing hundreds of error lines would sit four orders of magnitude below the new threshold and never fire. If Phase 4 chooses "raise thresholds" over "exclude the source," the log alerting layer becomes decorative.

Separately, `portage-api` emitting exactly 1 error line in 24h alongside 2,281 total lines suggests the `level` label is being derived for very few containers — a level-parsing question §5 P11 does not cover.

**Evidence:** Loki `/loki/api/v1/query`, `topk(10, sum by (container) (count_over_time({level="error"}[24h])))`.

---

## Part C — Risks the audit did not find

### C1. `dhg-remediator` is writing ~74,000 rows/day into the registry DB, unbounded, unmonitored. — CRITICAL

Not mentioned anywhere in the Phase 1 synthesis or the five raw reports.

`dhg-remediator` (compose project `dhgaifactory35`, image `dhgaifactory35-dhg-remediator`) polls `GET /api/incidents?status=active&limit=50` every 30 s, re-processes **the same 50 incidents forever**, and POSTs an action row per step:

```
docker logs dhg-remediator --since 24h | grep -vc "GET http"   -> 74,016
```

The incident lifecycle never terminates. One incident, created **2026-08-11**, is still `status=active` and has accumulated:

```
GET /api/incidents/2046ae68-…  -> actions on this incident: 13,472
```

The oldest active incidents date to 2026-08-11/08-15 and are still being replayed. Registry DB growth:

```
pg_database_size_bytes{datname="dhg_registry"}  30d ago: 1,231.0 MB   now: 1,653.6 MB
```

+423 MB in 30 days, ~34 %/month, dominated by this loop. The remediator carries **no** `prometheus.io/scrape` label, appears in no scrape job, no dashboard, and no alert — while executing a runbook engine that logs `Approval required for step 3: Stop container`. It is currently in dry-run for the shell steps (`[DRY RUN] Would execute: free -h`), which is the only reason this is a growth problem rather than an availability one.

This lands squarely against §8 "Alertmanager to registry webhook path (verified 38 deliveries) — healthy, do not rebuild." The delivery path works; what it feeds is a non-terminating loop.

**Evidence:** `docker logs dhg-remediator --since 24h`; `curl http://10.0.0.251:8011/api/incidents?status=active&limit=50`; `curl .../api/incidents/2046ae68-9b8a-4489-ba36-fd6d92e042c9`; Prometheus `pg_database_size_bytes` now vs t-30d; `docker inspect dhg-remediator` → no `prometheus.io/scrape` label.

### C2. G2 stays CRITICAL, and it is worse than "no evidence." — CRITICAL

Searched exhaustively:

| Location | Result |
|---|---|
| `/etc/cron.d/` | anacron, e2scrub_all, php, sysstat, .placeholder — no backup |
| `/etc/cron.daily/` | 0anacron, apache2, apport, apt-compat, dpkg, google-chrome, logrotate, man-db, sysstat — no backup |
| `crontab -l` (swebber64) | 5 entries: journal-age, reembed-nulls, session reaper, sync-memory — **no backup** |
| `systemctl list-timers --all` | 18 timers, all distro (sysstat, apt, logrotate, fstrim, dpkg-db-backup, …) — no DB backup |
| `docker ps -a` matching dump/backup/restic/borg/pgbackrest/wal-g | **none** |
| `/mnt/4tb/backups/` | one file: `loki-data-pre-p5-2026-08-25.tar.gz` (1.6 GB) — a one-off pre-migration Loki tarball, not a database backup |
| disk-wide `*.sql.gz` / `*.dump` | exactly one: `dhgaifactory3.5/backups/dhg_registry_2026-07-07_02-52-42.sql.gz` (173 MB) |
| dh40801 (via ssh) | no user crontab, no `/etc/systemd/system/*.timer` |

So: the single registry Postgres backup in existence is **59 days old**, was taken manually, sits **inside the git working tree**, and predates 423 MB of growth. `scripts/backup.sh` exists and works but writes to a relative `./backups` and is invoked by nothing.

This extends beyond G2's scope: dh40801 has no backup schedule either, so Langfuse's `dhg-langfuse-postgres`, `dhg-langfuse-clickhouse`, and `dhg-langfuse-minio` — the store for Portage's live LLM traces — are also unbacked. Seven Postgres instances on .251 plus three stores on .179, one 59-day-old dump between them.

**Evidence:** all commands above; `ssh dh40801 'crontab -l; ls /etc/systemd/system/*.timer'` → empty.

### C3. G1 prerequisites: cross-host monitoring is unblocked at L3, blocked at the exporter layer. — MEDIUM

Reachability from .251 to .179:

```
http://10.0.0.179:3000/api/public/health   -> 200
:9100 (node-exporter)  -> closed
:8080 (cAdvisor)       -> closed
:9115 (blackbox)       -> closed
:9090                  -> closed
docker --context dh40801 ps -> works (ssh://swebber64@10.0.0.179), 6 Langfuse containers Up 2 weeks
```

No Cloudflare Access sits between the hosts — :3000 answers directly over LAN. `sudo -n ufw status` on .179 is denied, so a host firewall cannot be ruled out; but the more likely reason 9100/8080/9115 are closed is simply that no exporter is deployed there. So G1 needs *deployment* on dh40801 (via the existing, working remote Docker context, per the standing "deploy to dh40801 via remote Docker context, not Ansible" decision), plus a `.179` scrape stanza in `prometheus.yml`. No new network path is required. Note the SSH context depends on `swebber64`'s key; a Prometheus container scraping :9100 does not go through SSH, so the ports must actually be published on .179.

**On Langfuse as an OTLP sink** (relevant to D6/D7): `GET /api/public/otel/v1/traces` returns **405** (method not allowed — the endpoint exists and is POST-only); `GET /api/public/otel` returns 404. So repointing medkb or a future Pydantic AI OTel exporter at Langfuse v3 is viable. `GET /metrics` on Langfuse returns **404** — confirming §7 G1's claim that there is nothing for Prometheus to scrape on the Langfuse web container itself.

**Evidence:** the curls and `docker --context dh40801 ps` above.

### C4. §8 "healthy — do not rebuild": LokiStoreGrowth is genuinely safe. — LOW (clears a suspicion)

Checked because the review brief flagged keep-all retention on a large disk as a possible hidden risk. It is not one:

```
loki_store_bytes   now: 2,266,176,663 (2.11 GiB)   t-7d: 2,187,464,376 (2.04 GiB)
```

= **+78.7 MB / 7 days ≈ 11 MB/day ≈ 4 GB/year**. The `LokiStoreGrowth` threshold is 20 GiB (`alerts.yml`), i.e. roughly **4 years** of headroom, on `/mnt/4tb` with **2.9 TB free (15 % used)**. `/` has 1.5 TB free. The keep-all directive is sound and the alert watermark is correctly placed. Note the growth is dominated by the node-exporter spam in B7 — fixing P4 at the source would cut Loki ingest substantially as a side effect.

### C5. Stale git worktree carrying a full duplicate of the observability tree. — LOW

`.claude/worktrees/stoic-nightingale-005718/` contains a complete second copy of the repo, including `docs/OBSERVABILITY_RUNBOOK.md`, `CLAUDE.md`, and observability planning docs. Every text search of `.claude/` returns doubled hits from it, which is how a Phase 4 grep-based cleanup could "fix" a file and leave the duplicate behind, or edit the duplicate by mistake. Out of observability scope; flagged so the cleanup does not trip on it.

### C6. Uncommitted dashboard: `memreg-daemon.json` — recoverable, but only from Grafana. — MEDIUM

```
git status --short  -> ?? observability/grafana/provisioning/dashboards/json/memreg-daemon.json
git log -- <path>   -> (no commits)
git check-ignore -v -> exit 1 (NOT gitignored — simply never added)
```

There is exactly **one** copy on disk. Grafana reads it through a bind mount of that same host directory (`docker exec dhg-grafana ls /etc/grafana/provisioning/dashboards/json/` shows the same 9 files), so the container is not a second copy. No generator script exists in `~/DHG/dhg-memreg` or `services/memreg` — searched, nothing.

It is not unrecoverable: provisioned dashboards are persisted into Grafana's own database, so the JSON could be exported from `/api/dashboards/uid/memreg-daemon`. But that recovery path depends on the Grafana volume surviving — and per C2 nothing backs it up. Treat as MEDIUM: one `git add` closes it.

### C7. Settled contradictions from §9

- **9.1 (target count):** **17**, not 18. `curl '/api/v1/targets?state=active'` returns 17 activeTargets, all `up`: docker-sd ×3, blackbox-http ×2, and one each of alloy, blackbox-https, cadvisor, memreg, loki, medkb, node-exporter, portage-api, postgres, prometheus, registry-api, vs-engine. A4 is right; A1 and A3 are wrong.
- **9.2 (why Tempo has no medkb spans):** **never invoked** — see B4. Zero `/v1/query` in 7 days.
- **9.7 (rule count):** **18** Prometheus alert rules. `grep -c 'alert:' observability/prometheus/alerts.yml` → 18 (ContainerCrashLoop, HostMemoryHigh, HostSwapHigh, RootDiskHigh, DataDiskHigh, PrometheusTargetDown, OllamaDown, PortageApiDown, RegistryApiDown, PostgresConnectionsHigh, ZombieProcessesHigh, ContainerMemoryLeak, ContainerHighCPU, ContainerHighMemory, MemregDLQBacklog, LokiStoreGrowth, LokiDown, AlloyDown). A4 and A5 are right; A1 is wrong.
- **§7 G8 (Portage has no dashboard):** confirmed. `portage_http_requests_total` has **142 series** in Prometheus; `grep -rn portage observability/grafana/` returns **zero** hits. Portage's `up` has been 1.0 averaged over 7 days, so the signal is there and nothing looks at it.
- **§5 P3 dead-metric claims, re-verified:** `container_restart_count` → 0 series (G4 stands). `gpu_utilization` → 0 series (G7 stands). `traces_spanmetrics_calls_total` and `tempo_distributor_spans_received_total` → 0 series (P2/P7 stand).

---

## Part D — Removal safety table

| Item | Audit verdict | This review | Blocking prerequisite |
|---|---|---|---|
| D1 langgraph-traces dashboard | none | agree, safe | — |
| D2 LangSmith in registry | low | **HIGH** — modules already fail to import; CME SLA/notify path dead | fix the two imports; decide whether the feature ships |
| D3 LangSmith in agent modules | none | agree | — |
| D4 agent boilerplate | must fix first | agree — `templates/agent-boilerplate/src/agent.py:22` confirmed | — |
| D5 `traced_node` in langgraph tracing | none | agree | — |
| D6 medkb OTLP → Tempo | keep open | safe now (zero traffic) | remove `OTEL_ENDPOINT` in the same change as Tempo |
| D7 Tempo | not a delete decision | safe for backend; **breaks 2 live frontend cards further** | fix/remove `data.ts:19,265,279` |
| D8 compose LangGraph services | compose cleanup | agree | — |
| D9 frontend langgraph routes | frontend scope | agree | — |
| D10 `LANGCHAIN_API_KEY` | vestigial | agree on the key | — |
| D10 `LOKI_URL` | vestigial | **WRONG — live reader** (A1) | do not remove |
| P1 drop static jobs | — | rewrite `RegistryApiDown` in the same change | `alerts.yml:83` |
| P1 drop docker-sd | — | **do not** — sole discovery for session-logger and `job="memreg"` | — |
| P4 raise thresholds | — | **masks all real errors** (B7) | exclude the source instead |
| P6 delete promtail config | — | update `docs/OBSERVABILITY_RUNBOOK.md:15,29,85,143,154` first | — |

---

## Version history
- v1 2026-09-04: adversarial review 2 of 4 (production risk), from live queries against g700data1 and dh40801.
