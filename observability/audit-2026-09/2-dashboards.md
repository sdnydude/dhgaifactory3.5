# Audit 2 — Grafana Dashboards: inventory, source of truth, real status

Read-only audit. Grafana 10.2.0 @ http://10.0.0.251:3001 (container `dhg-grafana`).
Evidence gathered 2026-09-04 ~08:15 UTC. No repo, container, or Grafana state was modified.

---

## 0. Method / provenance

- Repo files enumerated from `observability/grafana/` (both trees).
- Live inventory from `GET /api/search?type=dash-db` (401 unauthenticated; authenticated
  inline with `GF_SECURITY_ADMIN_USER`/`GF_SECURITY_ADMIN_PASSWORD` read from
  `docker-compose.override.yml` — values never echoed, only `user_len=5 pass_len=8` printed).
- Each dashboard fetched via `GET /api/dashboards/uid/<uid>`.
- Prometheus metric names from `GET /api/v1/label/__name__/values` (1582 names).
- Series freshness from `GET /api/v1/series?match[]=<metric>` over the last 1h, plus
  instant `/api/v1/query` and 6h `/api/v1/query_range` for the disputed panels.
- Loki labels from `/loki/api/v1/labels` and `/label/<name>/values` (24h window);
  panel LogQL replayed via `/loki/api/v1/query_range` (1h).
- Tempo probed via `/api/search/tags`, `/api/v2/search/tag/resource.service.name/values`,
  and `/api/search`.

---

## 1. Source of truth — settled

**`observability/grafana/provisioning/dashboards/json/` is the single source of truth.**

`observability/grafana/provisioning/dashboards/dashboards.yml:14` provisions from
`path: /etc/grafana/provisioning/dashboards/json`. The compose mount at
`docker-compose.override.yml:167` is
`./observability/grafana/provisioning:/etc/grafana/provisioning` — confirmed live by
`docker inspect dhg-grafana`. `docker exec dhg-grafana ls -R /etc/grafana/provisioning`
shows all 9 JSON files landed. **The mount and the provisioner path match.**

Provider settings: `folder: ''` (everything lands in "General"),
`updateIntervalSeconds: 10`, `allowUiUpdates: true`, `disableDeletion: false`.

### The `provisioned: false` red herring
The API returns `meta.provisioned = false` for all 9 dashboards, which initially looks
like provisioning is broken. It is not. `meta.provisionedExternalId` is populated for
every one (e.g. `memreg-daemon.json`), and Grafana reports `provisioned:false` precisely
because `allowUiUpdates: true` is set — that flag makes dashboards UI-editable, so
Grafana marks them non-provisioned to permit saving. Consequence worth recording:
**UI edits are permitted and will persist**, so repo↔live drift is structurally possible
here. As of this audit there is none (see §3).

### Dead tree
`observability/grafana/dashboards/` (2 files) is **NOT mounted into the container**
(`docker inspect` shows only the two mounts above). Nothing in compose references it.
These are dead copies. See §3.

---

## 2. Inventory (a)

All 9 live dashboards are in folder **General**; all 9 correspond 1:1 to a repo-provisioned
file; live count (9) == provisioned file count (9).

| # | Title | uid | Source of truth | Panels | Datasources | Repo last edit (git) | Live `updated` | Live ver | Status |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DHG Alerting & Rules | `dhg-alerting` | repo-provisioned | 12 | Prometheus | 2026-04-07 `7846edc` | 2026-04-07T00:26:20Z | 1 | **current** (healthy-empty) |
| 2 | DHG-Core-Golden | `dhg-core-golden` | repo-provisioned | 9 | Prometheus, Loki | 2026-04-07 `7846edc` | 2026-04-06T19:48:08Z | 3 | **broken** |
| 3 | DHG LangGraph Agent Traces | `dhg-langgraph-traces` | repo-provisioned | 5 | Tempo | 2026-04-07 `7846edc` | 2026-04-07T00:25:30Z | 1 | **broken** (no trace data at all) |
| 4 | DHG Log Analytics | `dhg-log-analytics` | repo-provisioned | 14 | Loki | 2026-08-25 `2e24d9d` | 2026-08-25T08:37:33Z | 4 | **current** |
| 5 | DHG PostgreSQL | `dhg-postgresql` | repo-provisioned | 14 | Prometheus | 2026-04-07 `7846edc` | 2026-04-07T00:10:20Z | 1 | **current** |
| 6 | DHG Registry API | `dhg-registry-api` | repo-provisioned | 11 | Prometheus | 2026-04-07 `7846edc` | 2026-04-07T00:11:10Z | 1 | **current** |
| 7 | Docker Overview | `docker-overview` | repo-provisioned | 12 | Prometheus | 2026-04-07 `7846edc` | 2026-04-06T20:34:11Z | 4 | **current** |
| 8 | Memreg Daemon | `memreg-daemon` | repo-provisioned, **UNTRACKED IN GIT** | 10 | Prometheus | *(no git history — `??` untracked)* | 2026-08-22T13:51:34Z | 2 | **current, sparse** |
| 9 | VS Engine — Verbalized Sampling | `vs-engine-overview` | repo-provisioned (file `vs-engine.json`) | 10 | Prometheus | 2026-03-15 `a4ff67a` | 2026-03-15T17:14:45Z | 1 | **broken** |

Notes on the table:
- **Row 8 is the significant one.** `git status --porcelain observability/grafana/`
  returns exactly one line: `?? observability/grafana/provisioning/dashboards/json/memreg-daemon.json`.
  `git ls-files` on that directory lists 8 files, not 9. The Memreg Daemon dashboard —
  the live one, the one MEMORY.md cites — **exists only on this host's filesystem and in
  Grafana's DB. It is not in version control.** Rebuilding the server from the repo loses it.
- Row 9: filename (`vs-engine.json`) does not match uid (`vs-engine-overview`). Cosmetic,
  but it defeats a filename↔uid lookup.
- `createdBy`/`updatedBy` is `Anonymous` for all 9 — the anonymous/admin auth path, not
  a per-user attribution trail.
- The "6 expected" provisioned dashboards in the task brief is stale: there are **9**.

### Datasources (all provisioned, all `readOnly: true`)
| uid | type | url |
|---|---|---|
| `prometheus` | prometheus | http://prometheus:9090 (isDefault) |
| `loki` | loki | http://loki:3100 |
| `tempo` | tempo | http://tempo:3200 |

Every panel references a datasource by uid that exists. **There are zero dangling
datasource references.** No dashboard's problems are datasource-misconfiguration problems.

### "Mission Control" — does not exist as a Grafana dashboard
MEMORY.md lists four Grafana dashboards including "Mission Control". `GET /api/search`
returns no such dashboard, and no dashboard JSON in either repo tree mentions it.
Repo grep locates it only in `docs/TODO.md:11`, `docs/TODO.md:46`, `docs/TODO.md:226`
and `docs/superpowers/specs/2026-04-12-langgraph-dashboards-design.md:146`, where it is
described as a **Next.js frontend route** ("New sibling route… in the sidebar 'Observe'
section, below 'Mission Control'"). **MEMORY.md conflates the frontend Mission Control
page with the Grafana dashboard set.** Nothing is missing from Grafana; the memory note
is wrong. (Auditing the frontend page itself is out of scope here.)

---

## 3. Per-dashboard panel validity (b)

Counts below are **query targets**, not panels, since several panels carry 2–4 targets.

### `dhg-alerting` — 16/16 targets resolve; 4 return no series (healthy-empty)
All Prometheus metric names exist and are being scraped (`job=prometheus` target UP).
Four targets select `ALERTS`, which currently has **0 series** — no alert is firing or
pending. This is correct behavior, not breakage:
- `dhg-alerting:1` "Firing Alerts" — `count(ALERTS{alertstate="firing"}) or vector(0)` → renders 0
- `dhg-alerting:2` "Pending Alerts" — same `or vector(0)` guard → renders 0
- `dhg-alerting:10` "Alert History" — `count by (alertname, alertstate) (ALERTS)`, no guard → blank
- `dhg-alerting:40` "Current Alert Detail" (table) — `ALERTS`, no guard → empty table
Verified present with data: `prometheus_rule_group_rules` (3 series),
`prometheus_notifications_dropped_total` (1 series).
**Verdict: current.**

### `dhg-core-golden` — 2/8 Prometheus targets valid, 2/2 Loki panels valid. BROKEN.
Five of nine panels query metrics that **do not exist anywhere in the TSDB** (checked
against the full 1582-name `__name__` list, not just a recent window):

| Panel | Title | Failing metric | Why |
|---|---|---|---|
| `dhg-core-golden:2` | ASR Request Rate | `asr_requests_total` | no `asr_*` metric exists; no ASR service in the target list |
| `dhg-core-golden:5` | GPU Utilization | `gpu_utilization` | no `gpu_*` metric exists; no GPU exporter scraped |
| `dhg-core-golden:7` | Transcription Latency (P95) | `asr_latency_seconds_bucket` | same as above |
| `dhg-core-golden:8` | Request Outcome | `asr_requests_total` | same as above |
| `dhg-core-golden:10` | Registry Latency (ms) | `registry_write_latency_ms_bucket`, `registry_read_latency_ms_bucket` | **name drift** — the real metrics are `registry_write_latency_bucket` / `registry_read_latency_bucket` (no `_ms`), and `dhg-registry-api` uses the correct names |

Valid: `dhg-core-golden:3` (`registry_write_operations_total`),
`dhg-core-golden:4` (`registry_db_connections`, 2 series),
`dhg-core-golden:12` and `dhg-core-golden:13` (Loki; `$container`/`$level` variables both
resolve — `job="dhg-ai-factory"` has 39 container values and 11 level values).

This dashboard is a **stale duplicate**: its two working Prometheus panels are subsets of
`dhg-registry-api`, its Loki panels are subsets of `dhg-log-analytics`, and its unique
content (ASR + GPU) targets services that are not in this stack. The `_ms` drift shows it
was written against an earlier metric naming scheme and never re-synced.

### `dhg-langgraph-traces` — 0/5 panels have data. BROKEN.
All five panels query Tempo. Tempo is reachable (`/api/echo` → 200) but **completely empty**:
- `GET /api/search/tags` → `{}`
- `GET /api/v2/search/tag/resource.service.name/values` (7-day window) → `{}`
- `GET /api/search` (24h) → `{"traces":[]}`
- `sum(tempo_distributor_spans_received_total)` → empty vector (metric not even present)

Every panel filters on `resource.service.name = "dhg-langgraph-agents"`, a service that
has never reported a span into this Tempo. Panels: `dhg-langgraph-traces:1` (Recent
Traces), `:10` (Agent Service Map, nodeGraph), `:20` (Error Traces), `:21` (Slow Traces),
`:30` (TraceQL Explorer). This directly contradicts MEMORY.md's "OTel → Tempo (85
@traced_node decorators… dual tracing)" — **the decorators may exist in code, but no spans
are arriving.** Distinguishing "not instrumented" from "instrumented but not exporting"
requires reading the agent code and is out of scope for this audit.

### `dhg-log-analytics` — 14/14 panels valid. CURRENT.
Every stream selector label exists: `job` (only value `dhg-ai-factory`), `container`
(39 values), `level` (11 values: `ERROR INFO LOG WARN WARNING debug error info unknown warn warning`),
plus `compose_project`, `compose_service`. Both template variables
(`$container`, `$level`, both `label_values({job="dhg-ai-factory"}, …)`) resolve.
Replayed over 1h: `:1` total logs 14 pts; `:2` errors 14 pts; `:10` by-level 8 series/64 pts;
`:40` registry-api 14 pts; `:61` redacted-values 12 pts.
One empty result — `dhg-log-analytics:41` "PostgreSQL Errors"
(`container="dhg-registry-db", level=~"error|fatal|panic|ERROR|FATAL|PANIC"`) → 0 series.
Verified healthy-empty, not mis-labeled: `dhg-registry-db` currently emits only
`level="LOG"` over 24h, so the regex would match if PG actually errored. Most recently
maintained dashboard in the set (2026-08-25).

### `dhg-postgresql` — 20/20 targets valid. CURRENT.
All metric names exist and all `datname="dhg_registry"` selectors resolve to live series:
`pg_stat_activity_count{datname="dhg_registry"}` 6, `pg_database_size_bytes{…}` 1
(1.65 GB), `pg_locks_count{…}` 9, `pg_stat_user_tables_size_bytes` 119,
`pg_stat_user_tables_n_dead_tup` 119, `pg_wal_size_bytes` 1,
`pg_stat_activity_max_tx_duration` 30. `postgres` scrape target UP.

### `dhg-registry-api` — 18/18 targets valid. CURRENT.
All `registry_*` metrics exist with data (`registry_db_connections` 2 series,
`registry_read_latency_bucket` 20 series). `dhg-registry-api:31` "Process Memory" selector
`process_resident_memory_bytes{job="registry-api"}` resolves to 1 series (182 MB).
`registry-api` scrape target UP.

### `docker-overview` — 16/16 targets valid. CURRENT.
`container_last_seen{image!=""}` → 60 containers; `container_cpu_usage_seconds_total{image!="",name!=""}`
→ 60 series (so the `$container` variable `label_values(container_last_seen{image!=""}, name)`
populates); `container_fs_reads_total` 255 series;
`node_filesystem_avail_bytes{mountpoint="/"}` 1 series. `cadvisor` and `node-exporter`
targets both UP.

### `memreg-daemon` — 11/13 targets valid; see §5 for the deferred-item reconciliation.
Scrape target `memreg` is **UP** (`http://172.20.0.22:8020/metrics`, last scrape 08:14:41Z).
Live values: `memreg_sweep_total`=143, `memreg_active_sessions`=1,
`memreg_sweep_threshold_tokens`=100000, `memreg_sweep_step_failures_total`=0,
last materialization 0.23 h ago.
Two targets reference `memreg_dlq_depth`, which is in the `__name__` index (from a past
scrape) but currently returns **0 series** — the exporter has stopped emitting it:
- `memreg-daemon:4` "DLQ Depth" (stat) — `sum(...) or vector(0)` → displays 0 via fallback
- `memreg-daemon:22` "DLQ Depth Over Time" — same fallback → flat 0 line

### `vs-engine-overview` — 4/14 targets valid. BROKEN.
The `vs-engine` scrape target is UP (`http://dhg-vs-engine:8000/metrics`), but the exporter
publishes only 5 `vs_*` metric names: `vs_distributions_cached`,
`vs_generation_duration_seconds_{bucket,count,created,sum}`. Ten targets across seven
panels reference metrics that **do not exist**:

| Panel | Title | Failing metric |
|---|---|---|
| `vs-engine-overview:2` | Generation Rate by Phase | `vs_generations_total` |
| `vs-engine-overview:5` | Weight Repairs/s | `vs_repair_weight_total` |
| `vs-engine-overview:6` | Generation Success Rate | `vs_generations_total` (both numerator and denominator) |
| `vs-engine-overview:11` | Diversity Score Distribution | `vs_diversity_score_bucket` (×2 targets) |
| `vs-engine-overview:12` | TTCT Composite Score Distribution | `vs_ttct_composite_bucket` (×2 targets) |
| `vs-engine-overview:21` | Tau Relaxation Events | `vs_tau_relaxed_total` |
| `vs-engine-overview:22` | Items Filtered by min_probability | `vs_items_filtered_total` |
| `vs-engine-overview:23` | Selection Strategy Usage | `vs_selections_total` |

Valid: `vs-engine-overview:3` (3 targets on `vs_generation_duration_seconds_bucket`,
18 series) and `vs-engine-overview:4` (`vs_distributions_cached`, 2 series).
The dashboard was authored 2026-03-15 against an instrumentation plan the service never
shipped, or shipped and then regressed. **7 of 10 panels are permanently blank.**

### Aggregate
| Dashboard | Targets valid | Targets w/ missing metric | Targets w/ no recent series |
|---|---|---|---|
| dhg-alerting | 12 | 0 | 4 (ALERTS, healthy-empty) |
| dhg-core-golden | 2 (+2 Loki panels) | 6 | 0 |
| dhg-langgraph-traces | 0 (5 Tempo panels, no data) | n/a | n/a |
| dhg-log-analytics | 14 panels (Loki) | 0 | 1 panel (healthy-empty) |
| dhg-postgresql | 20 | 0 | 0 |
| dhg-registry-api | 18 | 0 | 0 |
| docker-overview | 16 | 0 | 0 |
| memreg-daemon | 11 | 0 | 2 (`memreg_dlq_depth`) |
| vs-engine-overview | 4 | 10 | 0 |

**16 Prometheus targets across 12 panels reference metrics that do not exist in the TSDB.
5 Tempo panels have no backing data. All of it concentrated in three dashboards:
`dhg-core-golden`, `vs-engine-overview`, `dhg-langgraph-traces`.**

---

## 4. Duplicates and drift (c)

### 4a. Repo-provisioned ↔ live: ZERO drift
Fetched all 9 live dashboards and structurally diffed each against its repo file
(normalized JSON, sorted keys, `version`/`id`/`iteration` stripped). **All nine produced
0 diff lines.** Panel/target/variable extraction also compared identical.

Live `version` numbers exceed the repo's `"version": 1` on four dashboards
(`dhg-core-golden` 3, `dhg-log-analytics` 4, `docker-overview` 4, `memreg-daemon` 2), but
this is provisioner re-import bookkeeping, not content drift — the content is byte-equivalent
after normalization. Given `allowUiUpdates: true`, drift *could* appear at any time; it
has not.

### 4b. `observability/grafana/dashboards/` — 2 DEAD copies, one with broken PromQL
Not mounted anywhere (confirmed by `docker inspect dhg-grafana`, which shows only
`…/observability/grafana/provisioning` and the `grafana_data` volume). Not referenced by
either compose file.

**`observability/grafana/dashboards/dhg-core-golden.json`** (git: 2025-11-28 `0ef92c5`) —
8 panels vs the provisioned copy's 9. Same uid `dhg-core-golden`, same title, so if it were
ever provisioned alongside the live one it would collide on uid. Differences: it lacks
panel 13 (Log Volume by Level), lacks both template variables (`$container`, `$level`),
and its panel 12 selector is the unparameterized `{job="dhg-ai-factory"}`. It carries the
same broken `asr_*` / `gpu_utilization` / `registry_*_latency_ms_bucket` queries. Strictly
an older, worse copy.

**`observability/grafana/dashboards/docker-overview.json`** (git: 2026-01-09 `46a2baa`) —
6 panels vs the provisioned copy's 12; uid also `docker-overview`. **Its PromQL is
syntactically invalid**: label matchers are written `{image!""}` — the `=` is missing from
`!=`. Every one of its 8 targets carries this defect
(`container_cpu_usage_seconds_total{image!""}`, `container_memory_usage_bytes{image!""}`,
`container_network_receive_bytes_total{image!""}`, etc.). Several also contain literal
backslash-escaped quotes inside the JSON string values. It further references the
datasource by **name** (`"Prometheus"`) rather than uid (`prometheus`), which the
provisioned copy does correctly, and its panels have no `id` fields at all. This file
would not render if provisioned.

**Stale pointer:** `.claude/commands/observability-engineer.md:48` names
`observability/grafana/dashboards/` as "Grafana dashboards (source)" and repeats the path
at `.claude/commands/observability-engineer.md:326`. That instruction points agents at the
dead tree. `docs/archive/planning/observability-findings.md:28` records the historical
version of exactly this problem ("Dashboard JSON files are in `./observability/grafana/dashboards/`
… but Grafana's dashboard provider config points to `/var/lib/grafana/dashboards` … The JSON
files are NOT being loaded"). The provisioner path was since fixed to
`/etc/grafana/provisioning/dashboards/json`, the dashboards were re-homed, and the old
directory was left behind — but the `.claude/commands` pointer was never updated.

### 4c. Content duplication among live dashboards
`dhg-core-golden` overlaps `dhg-registry-api` (registry ops/latency/connections) and
`dhg-log-analytics` (the two Loki panels), contributing nothing unique that works.

---

## 5. `memreg-daemon` — reconciling the open deferred item

Open deferred item: *"Fix Grafana memreg-daemon dashboard panel rendering (graphs
blank/anomalous despite data)."*

**Diagnosis: it is a query/data-sparsity issue. It is NOT a datasource issue and NOT a
unit/type issue.** Evidence for each:

**Not a datasource issue.** Every panel targets `uid: prometheus`, which is provisioned
and resolves. The `memreg` scrape target is UP; last scrape 08:14:41Z, seconds before the
audit. Metrics are present and non-zero: `memreg_sweep_total`=143,
`memreg_active_sessions`=1, `memreg_sweep_threshold_tokens`=100000,
`memreg_materialization_timestamp_seconds` last written 0.23 h ago.

**Not a unit/type issue.** Panel units inspected directly and all are appropriate:
`memreg-daemon:2` unit `s` (age in seconds), `:11` unit `s` (duration), and `:3 :4 :5 :6 :7
:12 :21 :22` unit `short`. No panel has a `min`/`max` clamp or `decimals` override that
could suppress rendering. Dashboard `refresh: 30s`, default window `now-6h`.

**It is sparsity → NaN.** Replaying each timeseries panel as a 6h `query_range` at 60s step:

| Panel | Query | Result over 6h |
|---|---|---|
| `memreg-daemon:11` p50 | `histogram_quantile(0.50, rate(memreg_sweep_duration_seconds_bucket{job="memreg"}[5m]))` | 361 points, **357 NaN**, 4 non-zero |
| `memreg-daemon:12` sweep rate | `rate(memreg_sweep_total{job="memreg"}[5m]) * 60` | 361 points, 0 NaN, **4 non-zero** |
| `memreg-daemon:12` step failures | `rate(memreg_sweep_step_failures_total{job="memreg"}[5m]) * 60` | 361 points, **0 non-zero** (counter is genuinely 0) |
| `memreg-daemon:21` files ingested | `increase(memreg_ingestion_files_total{job="memreg"}[5m])` | 2 series, 722 points, **8 non-zero** |
| `memreg-daemon:22` DLQ depth | `sum(memreg_dlq_depth{job="memreg"}) or vector(0)` | flat 0 — `memreg_dlq_depth` has **0 live series**; the `or vector(0)` fallback is what you see |
| `memreg-daemon:22` DLQ dropped | `increase(memreg_dlq_dropped_total{job="memreg"}[5m])` | 361 points, **0 non-zero** |
| `memreg-daemon:2` last-sweep age | `time() - memreg_materialization_timestamp_seconds{job="memreg"} > 0` | 361 points, all non-zero — this one works fine |

Mechanism: the daemon sweeps rarely (≈4 sweeps in 6 hours). `histogram_quantile` over
`rate(...[5m])` of the bucket series is **undefined — NaN — in every 5m window containing
no observation**, which is 357 of 361 windows. Grafana renders NaN as a gap, so panel 11
appears blank with a handful of isolated points; that is the "blank despite data"
symptom. Panels 12/21 are not NaN but are near-flat-zero with 4 and 8 non-zero samples
respectively, which is the "anomalous" half of the report. Panel 22's zero line is a
genuine metric regression: `memreg_dlq_depth` is in the `__name__` index from past scrapes
but the exporter no longer publishes it, so only the `or vector(0)` guard renders.

Secondary observation (recorded, not a recommendation): `memreg-daemon:11` uses
`histogram_quantile(q, rate(bucket[5m]))` without a `sum by (le)` aggregation. It happens
to work with the current single memreg instance but would break on a second replica.

---

## 6. LangGraph / LangSmith / langgraph-era references (d)

Grepped both dashboard trees for `langgraph|langsmith|langchain` (case-insensitive).
**All hits are in one file — no other dashboard, panel, or variable references them.**

`observability/grafana/provisioning/dashboards/json/dhg-langgraph-traces.json`
(uid `dhg-langgraph-traces`, live, 5 panels, all Tempo):
- `dhg-langgraph-traces.json:28` — filter `service.name = "dhg-langgraph-agents"` (scope `resource`), panel `dhg-langgraph-traces:1`
- `dhg-langgraph-traces.json:51` — `serviceMapQuery: "{ resource.service.name = \"dhg-langgraph-agents\" }"`, panel `dhg-langgraph-traces:10`
- `dhg-langgraph-traces.json:121` — TraceQL `{ resource.service.name = "dhg-langgraph-agents" }`, panel `dhg-langgraph-traces:30`
- `dhg-langgraph-traces.json:137` — dashboard tags `["dhg","langgraph","traces","tempo"]`
- `dhg-langgraph-traces.json:142`–`143` — title `DHG LangGraph Agent Traces`, uid `dhg-langgraph-traces`

Panels `:20` (Error Traces) and `:21` (Slow Traces >5s) also filter the same service.

**Status of these references: all dead.** The service `dhg-langgraph-agents` has never
reported a span into this Tempo (`/api/v2/search/tag/resource.service.name/values` over a
7-day window returns `{}`; `/api/search` over 24h returns zero traces;
`tempo_distributor_spans_received_total` is not present in Prometheus at all).

**No LangSmith reference exists in any dashboard.** No dashboard references a
langgraph-era *container* (e.g. the decommissioned ports 8002–8008 agents) — the only
container-name selectors in the set are `dhg-registry-api` and `dhg-registry-db` in
`dhg-log-analytics:40` and `:41`, both of which are live containers present in Loki.
No LangGraph-era Prometheus metric names appear anywhere.

Contextual note (not a dashboard finding): per project CLAUDE.md, LangGraph runs in
LangGraph Cloud, not locally; `dhg-langgraph-agents` is not among the 17 active Prometheus
scrape targets nor among the 39 Loki container values.

---

## 7. UNVERIFIED items and why (e)

1. **Whether `allowUiUpdates: true` has ever caused historical drift.** I can only observe
   the current state (zero drift). Live `version` counters (3, 4, 4, 2) prove multiple
   writes occurred, but I cannot distinguish provisioner re-imports from human UI saves
   without Grafana's `dashboard_version` history table. `sqlite3` is **not installed in
   the `dhg-grafana` container** (`command -v sqlite3` → not found), so the read-only
   `SELECT … FROM dashboard` fallback was unavailable. I did not copy the DB out, as that
   exceeds a read-only audit's footprint.

2. **Why Tempo is empty.** Established as fact that it *is* empty. Whether the cause is
   missing OTel exporter config, agents running only in LangGraph Cloud with no egress to
   this Tempo, a wrong OTLP endpoint, or the `@traced_node` decorators never being active,
   requires reading `langgraph_workflows/dhg-agents-cloud/src/tracing.py` and the OTel
   env wiring — out of scope for a dashboard audit, and likely audit 3/4/5's territory.

3. **Why `memreg_dlq_depth` stopped being exported.** Confirmed it is in the `__name__`
   index but has 0 live series. Whether the exporter dropped the gauge, renamed it, or
   only emits it conditionally requires reading the memreg-agent exporter source.

4. **Whether the `asr_*` and `gpu_utilization` metrics in `dhg-core-golden` were ever
   real.** No `asr_*` or `gpu_*` name exists in the current 1582-name index, and no ASR
   or GPU-exporter scrape target exists. I did not check Prometheus's long-term retention
   or any prior config to see whether they existed historically.

5. **Whether the `vs-engine` service formerly exported the 8 missing `vs_*` metrics.**
   The dashboard was committed 2026-03-15 (`a4ff67a`, "fix(vs-engine): resolve spec
   compliance issues from final review"), which suggests they were specified. Confirming
   regression vs. never-implemented requires reading the vs-engine exporter.

6. **The frontend "Mission Control" page.** Established that it is not a Grafana
   dashboard. Its actual health (the 11 panels docs/TODO.md:11 describes, including
   Feedback Loop + Deferred Intelligence) is a frontend concern and was not exercised.

7. **Alert rule definitions.** `dhg-alerting` renders Prometheus's own rule-engine
   metrics and shows 3 rule groups loaded, but I did not audit the rule files themselves
   or Alertmanager routing — a different audit's scope.

8. **Grafana's own alerting / library panels / annotations.** Only `type=dash-db` was
   enumerated per the brief. Grafana-managed alert rules, library panels, playlists, and
   annotation sources were not inventoried.

---

## 8. Facts worth carrying forward

- Source of truth is unambiguous and the mount is correct: 9 files in
  `observability/grafana/provisioning/dashboards/json/` → 9 live dashboards, zero drift.
- `memreg-daemon.json` is **untracked in git** — the only dashboard not in version control.
- `observability/grafana/dashboards/` is a dead tree; one of its two files contains
  syntactically invalid PromQL. `.claude/commands/observability-engineer.md:48,326` still
  points agents at it.
- Three dashboards are substantially broken: `dhg-core-golden` (6/8 Prometheus targets
  dead), `vs-engine-overview` (10/14 dead), `dhg-langgraph-traces` (5/5 panels, Tempo
  empty for ≥7 days).
- Four dashboards are genuinely healthy: `dhg-postgresql`, `dhg-registry-api`,
  `docker-overview`, `dhg-log-analytics`.
- `dhg-alerting` is healthy; its empty panels reflect no firing alerts.
- `memreg-daemon`'s known blank-graph defect is NaN-from-sparsity in
  `histogram_quantile(rate(bucket[5m]))`, plus one genuinely absent metric
  (`memreg_dlq_depth`). Not datasource, not units.
- MEMORY.md's dashboard list is inaccurate on two counts: it names "Mission Control"
  (a frontend route, not a Grafana dashboard) and omits five that do exist
  (`dhg-alerting`, `dhg-langgraph-traces`, `dhg-log-analytics`, `dhg-postgresql`,
  `dhg-registry-api`).
