# Audit 4 — Telemetry Pipeline Health (READ-ONLY)

Collected 2026-09-04 ~08:12–08:17 UTC against g700data1 (10.0.0.251).
No files edited, no containers touched. All HTTP was GET; `docker logs` / `docker inspect` only.

---

## (a) Prometheus targets

`GET http://10.0.0.251:9090/api/v1/targets?state=any` → **17 active targets, 17 UP, 0 DOWN, 0 UNKNOWN. 5 dropped.**

The task brief listed 13 jobs; the live config has **14 job labels** because `docker-sd` relabels
one discovered container into its own job (`memreg`), per
`observability/prometheus/prometheus.yml:163-166`.

| job | target / scrapeUrl | instance | health | lastError | lastScrape age | interval | config |
|---|---|---|---|---|---|---|---|
| prometheus | http://localhost:9090/metrics | localhost:9090 | up | "" | 7.0s | 15s (global) | prometheus.yml:20-24 |
| registry-api | http://registry-api:8000/metrics | registry-api:8000 | up | "" | 2.3s | 10s | prometheus.yml:27-33 |
| postgres | http://postgres-exporter:9187/metrics | postgres-exporter:9187 | up | "" | 28.8s | 30s | prometheus.yml:37-42 |
| node-exporter | http://172.18.0.1:9100/metrics | 172.18.0.1:9100 | up | "" | 10.5s | 15s | prometheus.yml:45-50 |
| cadvisor | http://cadvisor:8080/metrics | cadvisor:8080 | up | "" | 7.6s | 30s | prometheus.yml:53-58 |
| vs-engine | http://dhg-vs-engine:8000/metrics | dhg-vs-engine:8000 | up | "" | 4.9s | 15s | prometheus.yml:61-67 |
| medkb | http://dhg-medkb-api:8015/metrics | dhg-medkb-api:8015 | up | "" | 7.2s | 15s | prometheus.yml:70-74 |
| portage-api | https://portage-api:8016/metrics | portage-api:8016 | up | "" | 3.0s | 15s | prometheus.yml:79-88 |
| blackbox-http | …/probe?module=http_2xx&target=http://dhg-ollama:11434/api/tags | http://dhg-ollama:11434/api/tags | up | "" | 19.1s | 30s | prometheus.yml:94-112 |
| blackbox-http | …/probe?module=http_2xx&target=http://10.0.0.251:11434/api/tags | http://10.0.0.251:11434/api/tags | up | "" | 24.8s | 30s | prometheus.yml:94-112 |
| blackbox-https | …/probe?module=http_2xx_insecure_tls&target=https://portage-api:8016/health | https://portage-api:8016/health | up | "" | 21.1s | 30s | prometheus.yml:114-129 |
| docker-sd | http://172.20.0.21:8000/metrics | container=dhg-registry-api | up | "" | 9.4s | 15s | prometheus.yml:143-169 |
| docker-sd | http://172.20.0.3:8000/metrics | container=dhg-vs-engine | up | "" | 9.6s | 15s | prometheus.yml:143-169 |
| docker-sd | http://172.20.0.4:8009/metrics | container=dhg-session-logger | up | "" | 14.3s | 15s | prometheus.yml:143-169 |
| **memreg** (docker-sd relabel) | http://172.20.0.22:8020/metrics | container=dhg-memreg-agent | up | "" | 9.0s | 15s | prometheus.yml:163-166 |
| loki | http://loki:3100/metrics | loki:3100 | up | "" | 14.2s | 15s | prometheus.yml:172-174 |
| alloy | http://alloy:12345/metrics | alloy:12345 | up | "" | 11.9s | 15s | prometheus.yml:177-179 |

### docker-sd discovery detail
- **4 containers discovered and kept**: `dhg-registry-api`, `dhg-vs-engine`, `dhg-session-logger`
  (job=docker-sd) and `dhg-memreg-agent` (relabeled to job=memreg).
- **5 dropped targets**: `/portage-api` ×4 (compose project `portage`, two networks × two
  duplicate entries: 172.20.0.16:8016 and 172.22.0.4:8016) and `/dhg-blackbox`
  (compose project `dhg-blackbox`, 172.20.0.28:9115). Both are dropped by the project-keep
  relabel at `prometheus.yml:154-156` (`regex: dhgaifactory35|dhg-memreg`).
  - portage-api is intentionally covered by the static `portage-api` job — comment at
    `prometheus.yml:76-78` states exactly this. **Not a gap.**
  - `dhg-blackbox` carries `prometheus.io/scrape: "true"` at
    `observability/blackbox/docker-compose.yml:18-21` but its compose project name is
    `dhg-blackbox` (`observability/blackbox/docker-compose.yml:6`), which the keep-regex
    excludes. **Blackbox exporter self-metrics are therefore not scraped anywhere.** Its
    probe results still arrive via the two blackbox-* jobs, so probes work; only
    `probe_*`-exporter internals (e.g. blackbox build/version, its own error counters) are
    absent. This is a live config/label mismatch — the label was written for a job whose
    relabel then filters the container out.

### Config vs. running-container cross-check (`docker ps`, 42 running `dhg-*` + portage)
- Every static target resolves to a running container. No stale address/port found.
- `dhg-medkb-api` declares Docker labels `prometheus.scrape=true` / `prometheus.port=8015`
  (`docker-compose.yml:338-340`) — the **dot form**, not the `prometheus.io/` form that
  docker-sd filters on (`prometheus.yml:148-149`). Discovery therefore ignores medkb; the
  static `medkb` job is what actually scrapes it. Cosmetic/consistency issue, not an outage.
- Node-exporter runs with `--path.rootfs=/host` and
  `--collector.textfile.directory=/host/mnt/4tb/observability/textfile` (docker inspect),
  which is how `loki_store_bytes` reaches Prometheus (see §f).

### medkb question (explicit)
The medkb target is **NOT on 10.0.0.251**. It is `http://dhg-medkb-api:8015/metrics`
(container DNS on `dhgaifactory35_dhg-network`), configured at `prometheus.yml:70-74`, and it
is **UP** with a 7.2s-old scrape. `dhg-medkb-api`, `dhg-medkb-db`, `dhg-medkb-cache` are all
still running locally on g700data1 — the recorded decision to relocate medkb to dh40801 has
**not** been executed as of this audit.

---

## (b) Alert rules

### Prometheus rules — `GET /api/v1/rules` → 3 groups, **18 alerting rules, all health=ok, all state=inactive, 0 firing**
File: `/etc/prometheus/alerts.yml` (repo: `observability/prometheus/alerts.yml`).
Group lastEvaluation at collection time: `dhg-infrastructure` 08:13:03.228Z (2.01 ms),
`dhg-logs` 08:12:55.213Z (0.26 ms), `dhg-memreg` 08:12:53.969Z (0.12 ms).

| # | rule | group | state | health | expr metrics present? | series |
|---|---|---|---|---|---|---|
| 1 | ContainerCrashLoop | dhg-infrastructure | inactive | ok | **NO** | `container_restart_count{name=~"dhg-.*"}` → **0 series** |
| 2 | HostMemoryHigh | dhg-infrastructure | inactive | ok | yes | node_memory_MemAvailable_bytes = 1 |
| 3 | HostSwapHigh | dhg-infrastructure | inactive | ok | yes | node_memory_SwapTotal_bytes = 1 (8.59 GB) |
| 4 | RootDiskHigh | dhg-infrastructure | inactive | ok | yes | mountpoint="/" = 1 |
| 5 | DataDiskHigh | dhg-infrastructure | inactive | ok | yes | mountpoint="/mnt/4tb" = 1 |
| 6 | PrometheusTargetDown | dhg-infrastructure | inactive | ok | yes | `up` = 17 series |
| 7 | OllamaDown | dhg-infrastructure | inactive | ok | yes | probe_success{service=ollama} = 2, both =1 |
| 8 | PortageApiDown | dhg-infrastructure | inactive | ok | yes | up{portage-api}=1, probe_success=1 |
| 9 | RegistryApiDown | dhg-infrastructure | inactive | ok | yes | up{registry-api}=1 |
| 10 | PostgresConnectionsHigh | dhg-infrastructure | inactive | ok | yes | pg_stat_activity_count = 30 series |
| 11 | ZombieProcessesHigh | dhg-infrastructure | inactive | ok | **NO** | `node_processes_zombies` → **0 series** |
| 12 | ContainerMemoryLeak | dhg-infrastructure | inactive | ok | yes | 42 series each side |
| 13 | ContainerHighCPU | dhg-infrastructure | inactive | ok | yes | 42 series |
| 14 | ContainerHighMemory | dhg-infrastructure | inactive | ok | yes | 42 series |
| 15 | LokiStoreGrowth | dhg-logs | inactive | ok | yes | loki_store_bytes = 1 (2,267,617,347 B ≈ 2.11 GiB; threshold 20 GiB) |
| 16 | LokiDown | dhg-logs | inactive | ok | yes | up{job=loki}=1 |
| 17 | AlloyDown | dhg-logs | inactive | ok | yes | up{job=alloy}=1 |
| 18 | MemregDLQBacklog | dhg-memreg | inactive | ok | **NO** | `memreg_dlq_depth` → **0 series** |

**DEAD RULES (3 of 18) — expression can never fire because the metric does not exist:**
1. **ContainerCrashLoop** (`observability/prometheus/alerts.yml`, group dhg-infrastructure) —
   `container_restart_count` is 0-series. cAdvisor is UP and exporting 42 series of
   `container_memory_usage_bytes` / `container_cpu_usage_seconds_total` for the same
   `name=~"dhg-.*"` selector, so the selector is fine; the *metric name* is not emitted by this
   cAdvisor build/flag set. This rule is also wired to incident trigger **T2** at
   `registry/api.py:326` — that trigger is unreachable.
2. **ZombieProcessesHigh** — `node_processes_zombies` is 0-series; node-exporter is UP but the
   `processes` collector is not enabled (its cmd is only `--path.rootfs` +
   `--collector.textfile.directory`). Wired to trigger **T12** at `registry/api.py:334` —
   unreachable.
3. **MemregDLQBacklog** — `memreg_dlq_depth` is 0-series. The `memreg` scrape target
   (172.20.0.22:8020) is UP, so the daemon is being scraped but does not publish this gauge
   under this name. This is the only rule in its group; the group is effectively inert.

### Loki ruler — **enabled and loading**
- Single-tenant id is **`fake`**, confirmed by `auth_enabled: false`
  (`observability/loki/loki-config.yml:9`) combined with `ruler.storage.type: local`,
  `directory: /etc/loki/rules` (`loki-config.yml:88-91`). The repo directory
  `observability/loki/rules/fake/alerts.yml` matches the required `<dir>/<tenant>/` layout.
- `GET http://10.0.0.251:3100/prometheus/api/v1/rules` returns group `dhg-log-alerts`,
  file `alerts.yml`, **5 rules, all health=ok, lastError=""**, lastEvaluation 08:13:54Z.
- `enable_api: true` (`loki-config.yml:101`), `alertmanager_url: http://dhg-alertmanager:9093`
  (`loki-config.yml:92`), `enable_alertmanager_v2: true` (`loki-config.yml:97`).

| rule | file:line | state | firing alerts |
|---|---|---|---|
| HighErrorRate | observability/loki/rules/fake/alerts.yml:4 | **firing** | 1 (value 2324) |
| ContainerErrorSpike | observability/loki/rules/fake/alerts.yml:15 | **firing** | 1 (container=dhg-node-exporter, value 2324) |
| PostgresFatalError | observability/loki/rules/fake/alerts.yml:26 | inactive | 0 |
| NoLogsFromRegistryApi | observability/loki/rules/fake/alerts.yml:37 | inactive | 0 |
| SecretLeakDetected | observability/loki/rules/fake/alerts.yml:51 | inactive | 0 |

**Standing alert, root cause identified:** both firing alerts are driven by a single container.
`sum by (container)(count_over_time({job="dhg-ai-factory", level=~"error|..."}[5m]))` returns
`dhg-node-exporter = 2554` and `dhg-grafana = 1`; nothing else. Sample lines pulled from Loki:
`level=error caller="error encoding and sending metric family: write tcp 127.0.0.1:9100" msg="->127.0.0.1:36240: write: connection reset by peer"`
and `level=error msg="collector failed" name=thermal_zone ... err="invalid argument"`.
Both alerts have been continuously firing since **activeAt 2026-08-25T09:16:54Z** (~10 days) —
i.e. since the P5 ruler cutover. The `HighErrorRate` threshold (>50/5m) and
`ContainerErrorSpike` (>20/5m) are both saturated ~50–125× over by this one noisy exporter.

---

## (c) Alertmanager delivery path

- `GET /api/v2/status` → version **0.27.0**, cluster status **ready**, uptime since
  2026-08-25T08:11:32.868Z. Loaded config matches `observability/alertmanager/alertmanager.yml`.
- `GET /api/v2/receivers` → exactly one: **`webhook`**.
- Webhook URL: **`http://dhg-registry-api:8000/webhooks/alertmanager`**, `send_resolved: true`
  — `observability/alertmanager/alertmanager.yml:11-15`.
- Route: `receiver: webhook`, `group_by: [alertname, service]`, `group_wait: 30s`,
  `group_interval: 5m`, `repeat_interval: 4h` (`alertmanager.yml:4-9`).
- One inhibit rule: critical inhibits warning on equal `[alertname, service]`
  (`alertmanager.yml:17-22`).

### Does the endpoint exist in the registry?
**Yes.** CodeGraph resolves `alertmanager_webhook` (function) to **`registry/api.py:338`**;
the decorator is `@app.post("/webhooks/alertmanager")` at **`registry/api.py:346`**, with
request models `AlertmanagerAlert` at `registry/api.py:307` and `AlertmanagerPayload` at
`registry/api.py:316`. Path and method match the Alertmanager config exactly.

### Has it ever received anything?
**Yes — verified from access logs, not inferred.**
`docker logs dhg-registry-api --since 168h | grep -ic alert` → **39** matching lines:
**38 × `POST /webhooks/alertmanager HTTP/1.1" 200 OK`** from `172.20.0.15` (the Alertmanager
container IP), plus 1 × `GET … 405 Method Not Allowed` from 10.0.0.251 (a human/probe hitting
it with GET). The POST cadence is consistent with `repeat_interval: 4h` × 2 alert groups over
the container's 5-day uptime. Delivery path is live and returning 200.

`docker logs dhg-alertmanager --since 168h 2>&1 | grep -i -E 'notify|error'` → **0 lines**; the
whole 168h window returns **0 log lines** for that container, so there is no notify-failure
evidence and no notify-success evidence on the Alertmanager side. The registry-side 200s are
the authoritative evidence.

### What the registry does with them
The two live alerts carry `severity: warning`. `registry/api.py:371-373` skips any alert whose
severity is not `critical`/`high`, so **no incidents are being created from the current firing
pair** — they are received, counted as `skipped`, and returned as 200. Additionally
`ALERT_TRIGGER_MAP` (`registry/api.py:325-343`) contains no entry for `HighErrorRate` or
`ContainerErrorSpike`, so even at higher severity they would map to `trigger_rule=None`.

### Silences
`GET /api/v2/silences` → **0 silences**. Nothing is suppressed.
`GET /api/v2/alerts` → **2 active alerts**, both state=`active` (not silenced, not inhibited):
`HighErrorRate{severity=warning,source=loki}` and
`ContainerErrorSpike{container=dhg-node-exporter,severity=warning,source=loki}`.

---

## (d) Loki coverage

- `GET /ready` → `ready`.
- `GET /loki/api/v1/labels` → **5 labels**: `compose_project`, `compose_service`, `container`,
  `job`, `level`. This is exactly the promtail-era label set — `discover_service_name: []`
  at `observability/loki/loki-config.yml:77` is what suppresses Loki 3.x's automatic
  `service_name` label, and it is working.
- `GET /loki/api/v1/label/container/values` → **27 values**.
- `GET /loki/api/v1/label/compose_service/values` → **27 values**.
- `GET /loki/api/v1/label/compose_project/values` → **6**: `dhg-audio-agent`, `dhg-memreg`,
  `dhgaifactory35`, `plane-app`, `portage`, `portage-e2e`.
- `GET /loki/api/v1/series?match[]={container=~"dhg-.*"}` over the last 24h →
  **22 streams across 16 distinct `dhg-*` containers**.

### Coverage gap: 26 of 42 running `dhg-*` containers have NO Loki stream in the last 24h
Present (16): dhg-alloy, dhg-audio-agent, dhg-docs, dhg-grafana, dhg-loki, dhg-medkb-api,
dhg-memreg-agent, dhg-node-exporter, dhg-ollama, dhg-prometheus, dhg-registry-api,
dhg-registry-db, dhg-remediator, dhg-session-logger, dhg-tempo, dhg-vs-engine.

Absent (26): dhg-alertmanager, dhg-api-server, dhg-audio-postgres, dhg-blackbox, dhg-cadvisor,
dhg-eval-db, dhg-eval-viewer, dhg-frontend, dhg-graphify-wiki, dhg-medkb-cache, dhg-medkb-db,
dhg-nlp-enrichment, dhg-nlp-processor, dhg-open-terminal, dhg-open-webui, dhg-p5-loki-du,
dhg-pdf-renderer, dhg-postgres-exporter, dhg-preprocessor, dhg-qc-service, dhg-review,
dhg-transcribe-db, dhg-transcribe-minio, dhg-transcribe-qdrant, dhg-transcribe-redis,
dhg-worker.

Conversely, **0 containers appear in Loki that are not running** — no orphan streams.

**Is any of this an explicit exclusion?** No. Neither the alloy config nor the (orphaned)
promtail config filters containers by name. `discovery.docker "dhg_ai_factory"` at
`observability/alloy/config.alloy:7-10` has **no filter block** — every container on the
socket is a target. The relabel block (`config.alloy:12-35`) only *renames* labels
(container / job / compose_service / compose_project); there is no `drop`/`keep` action.
The only content filtering is line-level, not container-level:
- `stage.drop` healthcheck combined-log form, `observability/alloy/config.alloy:112-115`
- `stage.drop` healthcheck JSON/pino form, `observability/alloy/config.alloy:117-120`

The same two-stage structure exists in the promtail file
(`observability/promtail/promtail-config.yml:50-56`, single stage there).

Because there is no exclusion, the 26 absent containers are best explained by those containers
simply not writing to stdout/stderr in the window, or writing only healthcheck-shaped lines
that both drop stages remove — consistent with the previously recorded "C10 resolved:
containers not in Loki simply haven't logged" finding. **I did not verify this per-container**
(would require reading 26 containers' `docker logs`); see §h.

One structural note: `dhg-p5-loki-du` produces **no log output at all** (`docker logs
dhg-p5-loki-du --tail 8` → empty), so its absence from Loki is fully explained.

`limits_config.retention_period: 0` (`loki-config.yml:74`) = keep-all/infinite, deliberate per
the header comment at `loki-config.yml:1-7`. `reject_old_samples_max_age: 168h`
(`loki-config.yml:80`) means anything replayed older than 7 days is rejected.

---

## (e) Tempo ingestion state

**Zero spans. Tempo has received nothing since the process started (~2 weeks uptime).**

- `GET :3200/ready` → `ready`. `GET :3200/status` → tempo **2.3.1**, all 16 modules `Running`
  (distributor, ingester, metrics-generator, querier, compactor, store, …). No failures.
- `GET :3200/metrics` (1434 lines) contains **no `tempo_distributor_spans_received_total`**
  and **no `tempo_ingester_traces_created_total` at all** — those counters are lazily created
  on first receipt, so their absence is itself the proof of zero ingestion.
- The counters that do exist are all zero: `tempo_distributor_push_duration_seconds_count 0`,
  every `tempo_distributor_push_duration_seconds_bucket 0`,
  `tempo_distributor_traces_per_batch_bucket 0`, `tempo_ingester_blocks_flushed_total 0`,
  `tempo_distributor_ingester_clients 0`, `tempo_distributor_metrics_generator_clients 0`.
- `GET :3200/api/search/tag/service.name/values` → `{}` — **zero `service.name` values**.
- `GET :3200/api/search/tags` → `{}`.
- `GET :3200/api/search?start=<now-24h>&end=<now>&limit=5` → `{"traces":[],...}`; Tempo's own
  log confirms `totalBlocks=0 inspectedBytes=0 inspectedTraces=0`.

So: **zero spans in the last hour, last 24h, and for the entire container uptime.** Stated as
measured, not inferred.

Supporting wiring facts:
- OTLP receivers ARE configured and listening: `observability/tempo/tempo-config.yml:4-11`
  (grpc 0.0.0.0:4317, http 0.0.0.0:4318), and `docker ps` shows 4317-4318 published.
- Exactly **one** running container carries any OTLP/Tempo env var (checked all `dhg-*` and
  `portage*` containers via `docker inspect ... .Config.Env`): **`dhg-medkb-api`** with
  `OTEL_ENDPOINT=http://dhg-tempo:4318` (`docker-compose.yml:335`). Note the var name is
  `OTEL_ENDPOINT`, not the SDK-standard `OTEL_EXPORTER_OTLP_ENDPOINT`. Nothing else in the
  stack is pointed at Tempo.
- **Tempo is not scraped by Prometheus** — there is no `tempo` job in `prometheus.yml`, and
  `up{job=~".*tempo.*"}` returns an empty vector. Tempo's own health is therefore invisible to
  the alerting stack (there is a `LokiDown` and an `AlloyDown` rule but no `TempoDown` rule).
- `metrics_generator.storage.remote_write` targets `http://prometheus:9090/api/v1/write`
  (`tempo-config.yml:35-37`) and Prometheus does run with `--web.enable-remote-write-receiver`
  (docker inspect; `GET /api/v1/write` returns 405 = handler present). But with zero spans,
  `count({__name__=~"traces_.*"})` returns an **empty vector** — no span-metrics or
  service-graph series exist. The whole generator path is wired and idle.

---

## (f) alloy / promtail / p5-loki-du roles

### dhg-alloy — the live log shipper
- Definition: `docker-compose.override.yml:267-278` (service `alloy`), image
  **`grafana/alloy:v1.19.0`**, mounts `./observability/alloy:/etc/alloy:ro` and named volume
  `alloy_data:/var/lib/alloy` (volume declared `docker-compose.override.yml:459`).
- Runtime: `docker inspect dhg-alloy` → status **running**, health **healthy**, **0 restarts**,
  cmd `run --server.http.listen-addr=0.0.0.0:12345 --storage.path=/var/lib/alloy/data /etc/alloy/config.alloy`.
- **Logs only.** `observability/alloy/config.alloy` defines exactly one pipeline:
  `discovery.docker` (:7) → `loki.source.docker` (:37) → `loki.process` (:45) →
  `loki.write "default"` → **`http://loki:3100/loki/api/v1/push`** (`config.alloy:124-128`).
  There is **no** `prometheus.scrape`/`prometheus.remote_write` component and **no**
  `otelcol.*` component anywhere in the file — Alloy ships **no metrics and no traces**.
  Its own self-metrics on :12345 are scraped by the `alloy` Prometheus job.
- Beyond promtail parity it adds **6 redaction stages** (`config.alloy:53-86`: Authorization,
  JWT shape, Cookie, api_key/token/secret/password, OAuth URL params, Doppler token shapes)
  and a second JSON-form healthcheck drop (`config.alloy:117-120`).

### promtail — decommissioned; config file is an orphan
- `docker ps -a --filter name=promtail` → **empty**. No promtail container exists, running or
  stopped.
- Text search over `docker-compose.yml` and `docker-compose.override.yml` finds **no promtail
  service definition**.
- `observability/promtail/promtail-config.yml` (56 lines) is therefore **dead config still in
  the repo**. `observability/alloy/config.alloy:1` states it directly:
  "Grafana Alloy — P5 log collection (replaces promtail, EOL 2026-03-02)."
- **No double-shipping.** Only one writer exists against
  `http://loki:3100/loki/api/v1/push` — Alloy. Confirmed three ways: no promtail container,
  no promtail compose service, and Loki's stream count (22 streams / 16 containers) shows no
  duplicated label sets.

### dhg-p5-loki-du — a disk-usage gauge feeder
- Definition: `docker-compose.override.yml:245-265` (service `p5-loki-du`,
  container_name `dhg-p5-loki-du`), image **`alpine:3.20`**.
- Runtime: **running**, **0 restarts**, started 2026-08-25T08:26:30Z, **no healthcheck defined**
  (`health=none` — so "healthy" cannot be asserted from Docker; see §h).
- What it does (from `docker inspect .Config.Cmd`): every 300s it runs `du -sb /loki`, writes
  a Prometheus textfile
  `# TYPE loki_store_bytes gauge` / `loki_store_bytes <n>` to `/textfile/loki_store.prom`
  via a `.tmp` + `mv` atomic swap.
- Mounts: `dhgaifactory35_loki_data` volume → `/loki:ro`, and
  `/mnt/4tb/observability/textfile` → `/textfile:rw`.
- That directory is exactly node-exporter's
  `--collector.textfile.directory=/host/mnt/4tb/observability/textfile`, which is why
  `loki_store_bytes` shows up in Prometheus carrying `job="node-exporter"`,
  `instance="172.18.0.1:9100"`. **Functionally verified end-to-end**: the gauge is present and
  fresh with value **2,267,617,347 bytes (≈2.11 GiB)**, feeding the `LokiStoreGrowth` rule
  (`observability/prometheus/alerts.yml`, threshold 20 GiB). The container is doing its job.
- One caveat baked into its own script: on `du` failure it prints
  `"p5-loki-du: du failed; keeping previous gauge"` (`docker-compose.override.yml:261`) —
  i.e. the gauge goes **stale rather than absent** on failure, and nothing alerts on staleness.
  Its stderr would carry that string, and `docker logs dhg-p5-loki-du` is currently empty
  (no failures in the retained buffer).

---

## (g) LangGraph / LangSmith / LangChain / port-2026 leftovers

Text search over `observability/` for `langgraph|langsmith|langchain|:2026|port 2026`:

1. **`observability/grafana/provisioning/dashboards/json/dhg-langgraph-traces.json` — a fully
   dead provisioned dashboard.** 8 hits, all pinning Tempo queries to a service that has never
   reported:
   - `:28` filter `service.name = "dhg-langgraph-agents"` (scope resource)
   - `:51` `"serviceMapQuery": "{ resource.service.name = \"dhg-langgraph-agents\" }"`
   - `:74` and `:94` — same service-name filter in two more panels
   - `:121` `"query": "{ resource.service.name = \"dhg-langgraph-agents\" }"`
   - `:137` `"tags": ["dhg","langgraph","traces","tempo"]`
   - `:142` title "DHG LangGraph Agent Traces", `:143` uid `dhg-langgraph-traces`
   This directory **is** the live provisioning path — `dashboards.yml:12` sets
   `path: /etc/grafana/provisioning/dashboards/json` and Grafana mounts
   `observability/grafana/provisioning → /etc/grafana/provisioning` (docker inspect). So this
   dashboard is loaded in Grafana today and every panel renders empty: Tempo's
   `service.name` value list is `{}` (§e). This is the single clearest LangGraph-era leftover
   in the telemetry pipeline.

2. **`docker-compose.yml:334` `LANGSMITH_PROJECT=dhg-medkb`** and
   **`docker-compose.yml:336` `LANGCHAIN_API_KEY=${LANGCHAIN_API_KEY}`** on `dhg-medkb-api`,
   sitting immediately around `OTEL_ENDPOINT` (`:335`). These are LangSmith-era tracing
   config living in the medkb service's telemetry env block. (Outside `observability/`, but
   directly part of the trace-export path, so listed here.)

3. **No scrape job, alert rule, Loki rule, relabel, or datasource references langgraph /
   langsmith / langchain.** Checked: `observability/prometheus/prometheus.yml` (0 hits),
   `observability/prometheus/alerts.yml` (0 hits), `observability/loki/rules/fake/alerts.yml`
   (0 hits), `observability/alloy/config.alloy` (0 hits), all three files under
   `observability/grafana/provisioning/datasources/` (0 hits).

4. **Port 2026 appears nowhere in `observability/`.** The only `2026` matches are calendar
   dates (e.g. `prometheus.yml:93` "…silently died on 2026-08-15"). No local-LangGraph-dev
   scrape target survives.

5. Non-LangGraph dead config found in passing: **`observability/grafana/dashboards/`**
   (`dhg-core-golden.json`, `docker-overview.json`) is **not** the provisioned path —
   provisioning reads `provisioning/dashboards/json/`, which holds its own copies of both
   files. That top-level directory is an unmounted duplicate.

6. Stale prose, not stale wiring: `observability/loki/rules/fake/alerts.yml:46` still says
   "…or **Promtail** may have lost connectivity" in the `NoLogsFromRegistryApi` description,
   and `observability/loki/loki-config.yml:75` / `observability/alloy/config.alloy:88` carry
   "promtail-era"/"unchanged from promtail" comments. The rule itself is correct and healthy.

---

## (h) UNVERIFIED items and why

1. **Per-container reason for the 26 missing Loki streams.** I established there is no
   container-level exclusion in the Alloy config (no filter, no keep/drop relabel), and that
   only two line-level healthcheck drop stages exist. I did **not** run `docker logs` against
   each of the 26 absent containers to confirm each one is genuinely silent (or emitting only
   drop-matched healthcheck lines). Stated as "best explained by", not as fact.

2. **`dhg-p5-loki-du` health.** The container defines **no Docker healthcheck**
   (`docker inspect` → `health=none`), so I cannot report a health status. I verified its
   *function* instead (fresh `loki_store_bytes` gauge in Prometheus). "Running and producing
   correct output" ≠ "healthy" as Docker reports it.

3. **Alertmanager-side delivery history beyond the registry's log window.**
   `docker logs dhg-alertmanager --since 168h` returned **0 lines total**, so I have no
   Alertmanager-side notify record at all. `dhg-registry-api` has only been up 5 days, so the
   38 observed POSTs cover ≤5 days, not the full 168h I asked for. Whether webhooks were
   delivered *before* that window is unverified.

4. **Whether the 38 webhook POSTs produced any incident rows.** I read the handler logic
   (`registry/api.py:366-394`) and the severity gate, and inferred `incidents_created=0` for
   the current warning-severity pair. I did **not** query the registry incidents table to
   confirm zero rows were created. Read-only DB queries were out of the stated tool scope.

5. **Why `container_restart_count`, `node_processes_zombies`, and `memreg_dlq_depth` are
   absent.** I confirmed all three return 0 series and that their exporters are UP. For
   node-exporter I can point at the cmd flags (no `processes` collector). For cAdvisor and the
   memreg daemon I did **not** inspect their flags/source to establish *why* the metric name
   is missing — only that it is.

6. **Whether `dhg-medkb-api` ever attempts an OTLP export.** It is the only container with
   `OTEL_ENDPOINT` set, and Tempo shows zero receipts. I did not read medkb's source to
   determine whether the app actually reads `OTEL_ENDPOINT` and initialises an exporter, so I
   cannot say whether this is a silent export failure or code that never exports.

7. **Historical span data.** Tempo's counters are process-lifetime. The container has ~2 weeks
   uptime, and `block_retention: 744h` (31 days, `tempo-config.yml:18`) means older blocks
   could in principle exist — but `totalBlocks=0` on a 24h search and
   `tempo_ingester_blocks_flushed_total 0` argue against any. I did not search a 31-day window.

8. **Scrape-interval attribution.** The `loki` and `alloy` jobs
   (`prometheus.yml:172-179`) declare no explicit `scrape_interval`; the 15s shown is the
   global default from `prometheus.yml:2`, as reported by the targets API — not a per-job
   setting in the file.
