# Observability Rebuild Plan — 2026-09-04 (Phase 3, awaiting approval)

Built from `AUDIT-2026-09.md` v2. Nothing here is built until Stephen approves. Every work package (WP) ends with what Stephen opens and what he sees.

Out of scope for this plan, captured as deferred items in the registry with their own priority: dhg-remediator runaway (critical), LangSmith import failure in registry notifications (high), backups (critical, DR), incident API count drift, frontend `/dashboards` page, agent boilerplate LangSmith. The plan names where each one gates an observability item.

---

## 0. Decisions needed before build

| # | Decision | Recommendation | Why |
|---|---|---|---|
| D-A | Trace architecture | **Retire Tempo. OTel goes to Langfuse OTLP only.** | Tempo has 0 spans; Langfuse v3 accepts OTLP; fan-out adds a daemon for a copy nobody reads. [R3] |
| D-B | Scrape convention | **Static jobs are canonical for in-project services; docker-sd only for opt-in containers with no static job.** | SD instance labels are container IPs that churn; static feeds RegistryApiDown and frontend queries. [R2][R3] |
| D-C | Registry HTTP instrumentation (code change in `registry/`) in this ship | **Yes, as its own small PR inside Phase 4.** | Without it the registry dashboard cannot show request rate, errors or latency, and the frontend `/dashboards` page stays dead. [R3] |
| D-D | Human alert channel | **Telegram bot via Alertmanager `telegram_configs`** (revised 2026-09-04: DHG does not use Slack; Telegram is free, native in Alertmanager 0.27, phone push). Alternatives: Discord (native), ntfy self-hosted. | 117 incidents have never reached a human. Bot token and chat id go in Doppler `dhg-monitoring`. |
| D-E | dhg-remediator | **`docker stop dhg-remediator` now, pending its fix.** Production change, needs your yes. | 74K rows/day into the registry DB, no human surface for its "approval required" queue. [R2][R4] |
| D-F | LAN exposure of Prometheus, Alertmanager, Loki, Tempo, cAdvisor (0.0.0.0, no auth) | **ufw: allow those ports from your Mac and localhost only.** | Grafana stays the UI; frontend reaches them over the Docker network, unaffected. [R4] |
| D-G | GPU exporter | **`nvidia_gpu_exporter` container with `runtime: nvidia`** (wraps nvidia-smi; no DCGM install). | runc is default runtime, nvidia only for Ollama; this matches that policy. |
| D-H | Grafana upgrade (10.2.0, Nov 2023) | **Not in this ship.** `grafana-image-renderer` supports 10.2. | Upgrade risk on 9 dashboards; separate ship. |
| D-I | Loki ingress filter | **Drop `portage-e2e-*` ephemeral containers; keep plane-app and portage.** | Ephemeral test containers pollute label values; Portage logs are useful. |

---

## 1. WP0 — Verification access (prerequisite for every AC below)

- Create a Grafana service account `dhg-verify` with **Viewer** role, token stored in Doppler `dhg-monitoring` as `GRAFANA_SA_TOKEN`. Anonymous Viewer is rejected: Viewer grants Explore, which is unrestricted Loki read. [R3]
- Add `dhg-grafana-renderer` (`grafana/grafana-image-renderer`) to compose, wire `GF_RENDERING_SERVER_URL`.
- Add `observability/scripts/verify-dashboard.sh <uid>`: renders PNG via `/render/d/<uid>` with the SA token and replays every panel through `/api/ds/query`, failing on any error or 0-series panel not whitelisted.

AC: you open `observability/verify/<uid>.png` for each dashboard and see the real page. `verify-dashboard.sh` exits 0 for every kept dashboard.

## 2. WP1 — Scrape hygiene (`prometheus.yml`)

- Static jobs `registry-api`, `vs-engine`, `session-logger`, `memreg`, each with `service=<name>`; docker-sd relabel-drops any container that has a static job.
- Add `alertmanager` job (:9093), `blackbox` self job (:9115), `tempo` job only until D-A executes.
- node-exporter: `--no-collector.thermal_zone` (root cause of 708K error lines/day). [R2]
- Drop `container_network_advance_tcp_stats_total` at scrape (metric_relabel). [R4]
- cloudflared: `--metrics 0.0.0.0:20241` on both units, scrape job `cloudflared`. [A5]

AC: in Grafana Explore, `count(registry_db_connections)` = 1, `up{job="alertmanager"}` = 1, `up{job="cloudflared"}` = 2, `count({__name__="container_network_advance_tcp_stats_total"})` = 0, Loki `{container="dhg-node-exporter", level="error"}` rate < 1/min.

## 3. WP2 — Alert rules and delivery

Rules (`alerts.yml`, Loki rules):
- Rewrite `ContainerCrashLoop`: `changes(container_start_time_seconds{name=~"dhg-.*"}[15m]) > 3`.
- Delete `ZombieProcessesHigh`.
- `MemregDLQBacklog`: `max_over_time(memreg_dlq_depth[15m]) > 0` for 15m; add `MemregDLQMetricMissing`: `absent(memreg_dlq_depth)` for 30m, warning.
- New: `AlertmanagerDown`, `PrometheusRuleEvalFailures`, `PrometheusNotificationsDropped`, `LokiRulerErrors`, `TextfileStale` (loki_store, backups when they exist).
- New symptom alerts: `PortageHighErrorRate` (5xx ratio > 5% for 10m), `PortageHighLatency` (p95 > 2s for 10m); registry equivalents once WP6 lands.
- Every rule gets `runbook_url` pointing at a docs-site page (WP8).
- Severity taxonomy documented: `critical` and `high` create incidents; `warning` notifies Telegram only; nothing else is used.

Delivery (`alertmanager.yml`):
- Receiver `telegram` (D-D) for all severities; registry webhook kept for critical/high.
- Fix `inhibit_rules`: `RegistryApiDown` inhibits registry-scoped alerts; `PrometheusTargetDown` inhibits per-service `*Down`.

AC: `p5-baseline.sh` silence round-trip passes; a deliberate test alert (`amtool alert add`) appears in `#dhg-alerts` on your phone within 60s; `/api/v1/rules` shows 0 rules with health != ok and every rule with a `runbook_url`.

## 4. WP3 — Dashboards

Standard (`observability/grafana/README.md`):
- Folders: `DHG / Platform`, `DHG / Services`, `DHG / AI`, `DHG / Alerting`. Names `dhg-<folder>-<subject>`.
- Row order per service board: RED (rate, errors, duration) then USE (CPU, memory, restarts) then dependencies then logs panel.
- Variables `$service`, `$instance` on every service board; `sum by (le)` on every quantile; units set; thresholds semantic (green/amber/red); tabular legends; refresh 30s; tags.
- Brand: Grafana org default theme dark, series palette classic; DHG purple only in text/link panels; never on thresholds. [R3]
- Every JSON provisioned, tracked in git, one file per dashboard, `version` reset to 1.

| uid | Action | Detail |
|---|---|---|
| dhg-registry-api | FIX | panels 1, 6: `sum(rate(...))`; 2: `registry_errors_total`; 10: `sum by (operation)`; 3, 4, 20, 21: `sum by (le)`; row 100 renamed "Database operations"; new "HTTP" row after WP6 |
| dhg-postgresql | FIX | 1: `sum()`, 5: `max()`, 20: legend `{{state}}`, 11: Fetched on right axis, 41: split into two panels, 40: filter `> 0`, 4: `increase(...[1h])` |
| vs-engine-overview | FIX | drop 7 dead panels, keep 4 live + duration; variables |
| memreg-daemon | FIX + COMMIT | `git add`; histogram panels use `increase(...[1h])` with `connectNulls`; DLQ panel shows "metric missing" state |
| docker-overview, dhg-log-analytics, dhg-alerting | KEEP | move to folders, add variables, no query changes |
| dhg-core-golden | RETIRE, replace with `dhg-platform-overview` | firing alerts, targets down, host, top error containers, GPU, disks |
| dhg-langgraph-traces | RETIRE | with D-A |
| `observability/grafana/dashboards/` | DELETE | dead tree |
| NEW `dhg-services-portage` | first new board | RED from `portage_http_*`, 142 series already there |
| NEW `dhg-ai-langfuse` | after WP5 | dh40801 host, 6 containers, health probe, synthetic trace freshness |
| NEW `dhg-platform-gpu` | after WP4 | util, VRAM, temp, per-process |
| NEW `dhg-platform-postgres` | after WP4 | all 7 instances via multi-target exporter, `$instance` variable |
| NEW `dhg-alerting-pipeline` | after WP2 | Alertmanager notifications, failures, rule eval, Loki ruler, incident counts (once API drift fixed) |

AC per dashboard: `verify-dashboard.sh <uid>` exits 0; you open the URL and every panel shows a number or a line, no "No data", no doubled tiles, legends readable.

## 5. WP4 — New exporters on g700data1

- `nvidia_gpu_exporter` (D-G), job `gpu`.
- `postgres-exporter` multi-target (`/probe?target=`) for medkb-db, portage-db, eval-db, transcribe-db, audio-postgres, plane-db; DSNs in Doppler.
- Blackbox: add targets frontend :3000, open-webui :3080, grafana :3001, `https://registry.digitalharmonyai.com/health`, Langfuse `/api/public/health`; add module `http_2xx_body` with `fail_if_body_not_matches_regexp`; ollama probe uses it once a container-only marker is confirmed (feasibility unverified, [R2]).
- audio-agent: add `prometheus.io/scrape` label.

AC: `up{job="gpu"}` = 1 and `nvidia_smi_utilization_gpu_ratio` present; `pg_up` has 7 series; `probe_success` has 8 series all 1.

## 6. WP5 — dh40801 observability agent

- `dh40801/docker-compose.observability.yml`: node-exporter, cAdvisor, Alloy (logs to Loki at 10.0.0.251:3100), bound to 10.0.0.179; deploy via `docker --context dh40801 compose` (per standing decision).
- Static jobs `node-exporter-dh40801`, `cadvisor-dh40801`; `host` label on both hosts' jobs.
- Synthetic Langfuse round-trip: `observability/scripts/langfuse-canary.sh` posts a trace via public API every 5 min and writes `langfuse_canary_success_timestamp` to node-exporter textfile; alert `LangfuseCanaryStale` > 15m. This is the MinIO silent-drop detector.
- Alerts: `Dh40801Down`, `LangfuseUnhealthy`, `LangfuseContainerRestart`.

AC: `dhg-ai-langfuse` dashboard shows both hosts and all 6 Langfuse containers; stopping `dhg-langfuse-minio` for 2 minutes fires `LangfuseCanaryStale` in Telegram (test executed with your go-ahead, then reverted).

## 7. WP6 — Registry HTTP instrumentation (D-C)

- `prometheus-fastapi-instrumentator` in `registry/api.py`, metrics `http_requests_total{handler,method,status}` and `http_request_duration_seconds` with buckets tuned to observed latency.
- Registry dashboard gains a real RED row; `RegistryHighErrorRate` and `RegistryHighLatency` rules; frontend `data.ts` can be repointed (separate deferred item).

AC: `sum by (handler) (rate(http_requests_total{job="registry-api"}[5m]))` returns one series per route; registry dashboard RED row live.

## 8. WP7 — Tempo retirement and Langfuse OTLP (D-A)

- Remove `dhg-tempo` service, `observability/tempo/`, Tempo datasource, Loki `derivedFields`, Prometheus `exemplarTraceIdDestinations`, `--web.enable-remote-write-receiver`.
- Create Langfuse project `dhg-ai-factory`; keys in Doppler; medkb `OTEL_ENDPOINT` becomes `LANGFUSE_*` + OTLP endpoint `/api/public/otel`; both `traced_node` helpers documented as superseded by `Agent.instrument_all()` for Pydantic AI.
- Remove `dhg-langgraph-traces.json`, `observability/promtail/`.

AC: `docker ps` shows no dhg-tempo; Grafana datasources list is prometheus, loki; a medkb `/v1/query` (run once, with your go-ahead) produces a trace visible at `http://10.0.0.179:3000` under project dhg-ai-factory.

## 9. WP8 — Docs and repo hygiene

- Rewrite `docs/OBSERVABILITY_RUNBOOK.md`; runbook page per alert in docs-site (targets for `runbook_url`).
- Fix `.claude/commands/observability-engineer.md`, `grafana-dashboards.md`, `prometheus-configuration.md` to the new source of truth and 10.0.0.251.
- Update MEMORY.md and `reference_port_map.md` (new ports: renderer 8081 internal, gpu exporter 9835, dh40801 9100/8080).
- Commit memreg-daemon.json AND `observability/blackbox/` (compose + blackbox.yml, also untracked: `git status` shows `?? observability/blackbox/`); delete dead dashboard tree and promtail config.

AC: `grep -rn 'promtail\|observability/grafana/dashboards/\|localhost:9090' docs .claude/commands` returns 0; docs-site builds.

## 10. WP9 — LAN exposure (D-F)

ufw rules limiting 9090, 9093, 3100, 3200, 8080, 4317, 4318 to your Mac IP and 127.0.0.1. Grafana :3001 and frontend :3000 unchanged.

AC: from the Mac, `curl 10.0.0.251:9090/-/ready` = 200; from any other LAN host = timeout; frontend `/api/prometheus` still 200.

---

## 11. Order and gating

WP0 → WP1 → WP2 (needs D-D secret) → WP3 fixes → WP4 → WP5 → WP3 new boards → WP6 → WP7 → WP8 → WP9. Each WP is one Opus 5 build agent, one PR-sized commit, verified by me in a real browser render before the next starts. Backups staleness alert is added to WP2 the day the backup job exists.

## 12. What this plan does not do

Does not fix the remediator, the registry notification imports, backups, the incident API, the frontend dashboards page, or the agent boilerplate. All six are captured as deferred items with priority. Does not upgrade Grafana or Prometheus. Does not touch `docker-compose.yml` LangGraph service definitions or the 18 `@traceable` agent modules.
