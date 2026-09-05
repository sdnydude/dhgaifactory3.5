# Audit 3 — "Broken pages": dhg-postgresql & dhg-registry-api

Read-only audit. No Grafana state changed, no repo file edited. Grafana 10.2.0 @ 10.0.0.251:3001, Prometheus @ 10.0.0.251:9090.

---

## 0. Headline

**Neither dashboard produces a datasource error.** Every single panel query was replayed through Grafana's own `/api/ds/query` endpoint (the exact call the browser makes) and **all 38 targets returned HTTP 200 with no `error` field**. Grafana's container log for the audit window contains **zero** panel or datasource errors.

What a viewer actually sees, and what is being reported as "errors", decomposes into three real defects:

1. **2 registry-api panels are permanently "No data"** — a PromQL vector-matching bug (`+` between two vectors with disjoint `operation` label values).
2. **Every registry-api panel except one renders doubled** — the registry container is scraped twice by two different Prometheus jobs, so each metric has 2 series. On `stat` panels that means two tiles crammed into one 4-column cell.
3. **Four PostgreSQL panels fan out** — unaggregated `pg_stat_activity_*` splits by `state`/`usename`, so a single-value `stat` tile renders 6 tiles.

The premise "the postgresql dashboard shows errors" is **not supported**. It has no failing queries, no missing metrics, and no bad datasource references. Its problems are display defects only.

### Method note / verification gap

- **Screenshots were NOT captured.** Two paths were attempted and both failed:
  - Grafana's server-side render (`/render/d/...`) returns HTTP 200 but the payload is a 478x208 placeholder reading *"No image renderer available/installed"* — the `grafana-image-renderer` plugin is not installed (`docker exec dhg-grafana ls /var/lib/grafana/plugins` → empty; Grafana log `logger=rendering ... no image renderer found/installed`). Placeholder saved as `3-render-unavailable-placeholder.png`.
  - Browser login requires typing `GF_SECURITY_ADMIN_PASSWORD`. Both credential-injection routes that avoid putting the secret in the transcript (browser reads it from a `file://` URL; browser reads it from a short-lived loopback HTTP server) were **denied by the permission classifier**. Per `.claude/rules/secret-safety.md` ("NEVER display full secret values in output") the value was not pasted into a tool argument instead.
- Consequence: **pixel-level rendering is UNVERIFIED**. Everything about queries, data, metric existence, labels, datasources, drift and layout geometry is verified from the Grafana HTTP API + Prometheus API + dashboard JSON, which is where all the decisive evidence lives. The display defects below are derived from series counts crossed with each panel's `reduceOptions`/`gridPos`, not from a screenshot.
- All API access used HTTP Basic auth with credentials held in shell variables, never echoed.

---

## 1. Datasource and provisioning sanity — both dashboards clean

| Check | Result |
|---|---|
| Datasource uids in Grafana | `prometheus`, `loki`, `tempo` |
| Datasource uid referenced by **every** panel on both dashboards | `{type: prometheus, uid: prometheus}` |
| Match against `observability/grafana/provisioning/datasources/prometheus.yml` | matches — **no wrong-datasource-uid defect anywhere** |
| Templating variables | **none** on either dashboard (so no broken `$var` interpolation) |
| Prometheus targets | **18/18 UP**, zero `lastError` |
| `postgres` job (`postgres-exporter:9187`) | UP |
| `registry-api` job (`registry-api:8000`) | UP |

**Repo drift: none.** Live dashboard JSON vs `observability/grafana/provisioning/dashboards/json/{dhg-postgresql,dhg-registry-api}.json` — identical panel-id / title / type / expression signature, identical `version` (1), identical `time`/`refresh`/`tags`. Both carry `meta.provisionedExternalId` pointing at their repo filename; `meta.provisioned: false` is expected because the provider sets `allowUiUpdates: true` (`observability/grafana/provisioning/dashboards/dashboards.yml`). Both files are present inside the container at `/etc/grafana/provisioning/dashboards/json`. Created/updated `2026-04-07`, never edited since.

---

## 2. What the apps actually expose

### 2.1 registry-api `/metrics` — `http://10.0.0.251:8011/metrics` (HTTP 200, 8439 bytes)

Mounted at **`registry/api.py:298-301`**:

```python
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()
```

Plain `prometheus_client.generate_latest()` — **not** `prometheus-fastapi-instrumentator`, **not** `make_asgi_app()`. Metric families present (names only):

`process_cpu_seconds_total`, `process_max_fds`, `process_open_fds`, `process_resident_memory_bytes`, `process_start_time_seconds`, `process_virtual_memory_bytes`, `python_gc_collections_total`, `python_gc_objects_collected_total`, `python_gc_objects_uncollectable_total`, `python_info`, `registry_db_connections`, `registry_db_errors_created`, `registry_db_errors_total`, `registry_errors_total`, `registry_read_latency` (+`_bucket`/`_count`/`_sum`/`_created`), `registry_read_operations_total`, `registry_write_latency` (+buckets), `registry_write_operations_total`.

Definitions in **`registry/metrics.py:9-42`** and **`registry/database.py:13`**.

**Critical: there are no HTTP request metrics at all.** Grep of the exposition for `^http_request|^http_server|^fastapi` returns **0**. There is therefore **no `handler`, `path`, `endpoint`, `status`, or `status_code` label anywhere in the registry's exposition.** The only label keys the registry emits are `operation` (on the two op counters), `error_type` (on `registry_errors_total`), and `le` (on the histograms).

Implication: the dashboard's first row is titled **"Overview (RED Metrics)"** but true RED (per-route request rate, HTTP error ratio, request duration) is **unmeasurable** with this exposition. The dashboard substitutes DB-operation counters and DB-connection-error counts. The `handler`-vs-`path`-vs-`endpoint` label question is moot: none exist, and the dashboard correctly does not reference any.

**Also:** `registry_errors_total{error_type}` — the application's own error counter — is **never queried by the dashboard**, and has **0 series in Prometheus** (never incremented in the retention window). The panel titled "Error Rate" queries `registry_db_errors_total` instead, which counts only database-connection failures.

### 2.2 postgres-exporter — `http://10.0.0.251:9187/metrics` (HTTP 200, 446818 bytes)

Target `postgres` → `postgres-exporter:9187`, **UP**. Non-`pg_settings_*` families include: `pg_database_size_bytes`, `pg_locks_count`, `pg_replication_is_replica`, `pg_replication_lag_seconds`, `pg_stat_activity_count`, `pg_stat_activity_max_tx_duration`, `pg_stat_database_*` (`blks_hit`, `blks_read`, `deadlocks`, `tup_inserted/updated/deleted/fetched`, `xact_commit`, `xact_rollback`), `pg_stat_user_tables_*` (`n_dead_tup`, `size_bytes`), `pg_wal_size_bytes`, `pg_up`, `pg_exporter_*`, `pg_scrape_collector_*`.

**Every metric the dashboard queries exists.** Label carriage:

| Metric family | Labels carried |
|---|---|
| `pg_stat_activity_count`, `pg_stat_activity_max_tx_duration` | `datname`, `instance`, `job`, **`server`**, `service`, **`state`**, **`usename`** |
| `pg_stat_database_*` | `datid`, `datname`, `instance`, `job`, `service` |
| `pg_database_size_bytes` | `datname`, `instance`, `job`, `service` |
| `pg_stat_user_tables_*` | `datname`, `instance`, `job`, `relname`, `schemaname`, `service` |
| `pg_locks_count` | `datname`, `instance`, `job`, `mode`, `service` |
| `pg_wal_size_bytes` | `instance`, `job`, `service` (no `datname`) |

The dashboard filters on **`datname="dhg_registry"`** only. `datname` is present on every metric it filters — **no wrong-label defect**. It never filters on `server`; `server="registry-db:5432"` is single-valued so that is harmless. The dashboard does **not** use the `state` / `usename` labels that `pg_stat_activity_*` carries, and that omission is the source of the fan-out defect (§3).

### 2.3 The duplicate-scrape defect (registry-api only)

`registry_db_connections` returns **2 series**:

```
{__name__=..., container="dhg-registry-api", instance="172.20.0.21:8000", job="docker-sd"}
{__name__=..., instance="registry-api:8000",  job="registry-api", service="registry-api"}
```

The same container is scraped by **two Prometheus jobs**:
- static job `registry-api` → target `registry-api:8000` (`observability/prometheus/prometheus.yml:27-29`)
- job `docker-sd` → `docker_sd_configs` auto-discovers any container labelled `prometheus.io/scrape` (`observability/prometheus/prometheus.yml:143-170`), which matches `dhg-registry-api` at `172.20.0.21:8000`

Both hit `registry/api.py:298`. The two jobs relabel differently — `docker-sd` adds `container`, the static job adds `service` — so the label sets are **not** identical and Prometheus keeps both. Every `registry_*` and `process_*` series from that container is therefore doubled.

Only **one** registry panel guards against this: id=31 "Process Memory", which pins `job="registry-api"`. All ten other registry panels do not, and get 2x every series.

The postgres dashboard is unaffected (postgres-exporter is scraped by exactly one job).

---

## 3. dhg-postgresql — panel by panel

Live JSON: 19 panels (5 rows + 14 data panels). All `datasource = prometheus` (correct). All expressions parse and execute. All metrics exist.

| id | Title | Type | Root cause class | Decisive evidence |
|---|---|---|---|---|
| 100 | Overview (row) | row | actually fine | — |
| **1** | **Active Connections** | stat, w4 | **layout/display defect — missing aggregation** | `pg_stat_activity_count{datname="dhg_registry"}` → **6 series**, split by `state`: `active=1`, `idle=5`, `disabled=0`, `fastpath function call=0`, `idle in transaction=0`, `idle in transaction (aborted)=0`. `reduceOptions={calcs:[lastNotNull], values:false}` on a 4-column stat → Grafana renders 6 tiles in one cell. Needs `sum(...)` or a `state="active"` filter. |
| 2 | Database Size | stat | actually fine | 1 series, `1653183279` B (1.54 GiB); unit `bytes` correct |
| 3 | Cache Hit Ratio | gauge | actually fine | 1 series = `99.946`; unit `percent`, thresholds sane |
| 4 | Deadlocks | stat | actually fine (semantic nit) | 1 series = `0`. Nit: it displays a lifetime **counter** raw, not `rate()`/`increase()`, so it will only ever ratchet up and never returns to 0 after a deadlock. Unit `short`. |
| **5** | **Longest TX** | stat, w4 | **layout/display defect — missing aggregation** | `pg_stat_activity_max_tx_duration{datname="dhg_registry"}` → **6 series** (same `state` fan-out as id=1). Needs `max(...)`. Unit `s` is correct for this metric. |
| 6 | WAL Size | stat | actually fine | 1 series = `83886080` B (80 MiB); unit `bytes` correct |
| 101 | Transactions (row) | row | actually fine | — |
| 10 | Transactions / sec | timeseries | actually fine | Commits `2.28/s`, Rollbacks `0.21/s`; 1 series each; unit `ops` correct |
| **11** | **Row Operations / sec** | timeseries | **display defect — mismatched magnitude on a shared linear axis** | 4 series, all OK: Fetched `533.97/s` vs Inserted `0.0296/s`, Updated `0`, Deleted `0`. Fetched is ~18,000x the others, so on one linear axis the three write series are pinned flat at zero and unreadable. Fetched belongs on a right axis or its own panel. |
| 102 | Connections & Cache (row) | row | actually fine | — |
| **20** | **Active Connections** | timeseries | **display defect — missing aggregation + misleading legend** | Target A `pg_stat_activity_count{datname="dhg_registry"}` → **6 series** but `legendFormat: "dhg_registry"` is a static string, so all 6 legend entries render with the **identical** name "dhg_registry" and cannot be told apart. Target B `sum(pg_stat_activity_count)` → 1 series (`6`) and is correct. |
| 21 | Cache Hit Ratio Over Time | timeseries | actually fine | 1 series = `99.995%`; the `+0.001` denominator guard prevents div-by-zero correctly |
| 103 | Table Health (collapsed row) | row | actually fine | collapsed by default; children expand correctly |
| 30 | Dead Tuples (Top 10 Tables) | timeseries | actually fine (minor inconsistency) | `topk(10, pg_stat_user_tables_n_dead_tup)` → 10 series, top value `992`. Minor: unlike every other panel it has **no `datname` filter**; verified harmless today because all 119 series carry `datname="dhg_registry"`, but it will silently mix databases if another DB is ever added to the exporter. |
| 31 | Table Sizes (Top 15) | table, instant | actually fine (minor inconsistency) | `topk(15, pg_stat_user_tables_size_bytes)` → 15 series, top `776388608` B (740 MiB); `format: table`, `instant: true` — correct config for a table panel. Same missing-`datname` note as id=30. |
| 104 | Locks & Storage (collapsed row) | row | actually fine | — |
| **40** | **Locks by Mode** | timeseries | **useless panel (not an error)** | `pg_locks_count{datname="dhg_registry"}` → 9 series, **every one currently `0`**. Renders as nine overlapping flat-zero lines. Technically correct, informationally empty at this workload. |
| **41** | **WAL & Database Size** | timeseries | **display defect — mismatched magnitude** | Both targets OK (WAL `83886080` = 80 MiB, DB `1653183279` = 1.54 GiB). On one linear `bytes` axis WAL is ~5% of DB size and reads as a flat line at the bottom. |

**Layout geometry (from `gridPos`): clean.** Programmatic overlap check across all visible panels found **zero overlapping cells**. Row stack is contiguous: row100@y0 → stats y1-y5 (six w4 tiles filling all 24 columns) → row101@y5 → y6-y14 → row102@y14 → y15-y23 → row103@y23 (collapsed) → row104@y24 (collapsed). No empty rows. No gaps.

**Verdict for dhg-postgresql: no errors of any kind.** 14/14 data panels return data. Defects are 4 display problems (ids 1, 5, 20 fan-out; ids 11, 41 axis scaling), 1 low-value panel (id 40), and 1 semantic nit (id 4 raw counter).

---

## 4. dhg-registry-api — panel by panel

Live JSON: 15 panels (4 rows + 11 data panels). All `datasource = prometheus` (correct). All expressions parse. All metrics exist. **Two panels return an empty vector.**

| id | Title | Type | Root cause class | Decisive evidence |
|---|---|---|---|---|
| 100 | Overview (RED Metrics) (row) | row | **mislabelled** | Row claims RED but the app exposes **zero** HTTP request metrics (§2.1). No request rate, no status-code errors, no request duration is obtainable. |
| **1** | **Request Rate** | stat | **BAD QUERY SYNTAX — PromQL vector matching → permanently No data** | `rate(registry_write_operations_total[5m]) + rate(registry_read_operations_total[5m])`. Binary `+` requires **identical label sets** on both sides. Both operands carry `operation`, but the value sets are **disjoint**: WRITE = `bulk_ingest_doc_pages, create_agent_session, create_bug_fix, create_correction, create_decision_log, create_insight, create_memory_metrics, create_session_report, create_ship_session, create_test_coverage, mark_surfaced, update_agent_session, update_deferred_item`; READ = `correction_stats, kb_search, list_agent_sessions, list_bug_fixes, list_corrections, list_decision_logs, list_deferred_items, list_done_gate_runs, list_insights, list_memory_metrics, list_ship_sessions`. Intersection is empty → result vector is empty. `/api/v1/query` → **`success, 0 series`**. `/api/ds/query` → HTTP 200, `frames=1, series=0, maxpoints=0`. Needs `sum(rate(...)) + sum(rate(...))` or `ignoring(operation)`. |
| **2** | **Error Rate** | stat | **duplicate scrape (2 tiles) + wrong metric semantically** | `rate(registry_db_errors_total[5m])` → **2 series** (jobs `registry-api` + `docker-sd`, §2.3), both `0`. Semantic defect: `registry_db_errors_total` counts only DB-connection failures; the app's real error counter `registry_errors_total{error_type}` (defined `registry/metrics.py:33-37`) is **never queried** and has **0 series** in Prometheus. |
| **3** | **Write P95** | stat | **duplicate scrape (2 tiles)** | `histogram_quantile(0.95, rate(registry_write_latency_bucket[5m]))` → **2 series**, both `24.25`. Unit `ms` is **correct** — `registry/metrics.py:9-13` declares "Database write latency in milliseconds", buckets `[1,5,10,25,50,100,250,500,1000,2500,5000]`. No `by (le)` clause; works only because Prometheus implicitly groups by all labels except `le`. |
| **4** | **Read P95** | stat | **duplicate scrape (2 tiles) + histogram top-bucket saturation** | → **2 series**, both `99.29` ms. Unit `ms` correct (`registry/metrics.py:15-19`). Saturation: read histogram's largest finite bucket is `le=1000` (`registry_read_latency_bucket{le="1000.0"}=1888` of `registry_read_latency_count=1897`), so **9 observations (0.47%) exceed 1000 ms and land in `+Inf`**. Any quantile above p99.53 is unresolvable, and p99 itself interpolates inside the very coarse 500–1000 ms bucket. |
| **5** | **DB Connections** | stat | **duplicate scrape (2 tiles) + metric does not measure what the title says** | `registry_db_connections` → **2 series**, both `0` right now; `max_over_time(...[24h])` = **`1`** on both jobs. A gauge that never exceeds 1 is not a connection *pool* measurement. Gauge defined at `registry/database.py:13`; `codegraph_callers` finds **no callers** — *(UNVERIFIED where/whether it is set; the grep needed to confirm was blocked by the repo's codegraph-first hook, but the 24h max of 1 proves it is written at least occasionally)*. |
| **6** | **Total Ops (lifetime)** | stat | **BAD QUERY SYNTAX — same vector-matching failure → permanently No data** | `registry_write_operations_total + registry_read_operations_total` — identical disjoint-`operation` problem as id=1. `/api/v1/query` → **`success, 0 series`**; `/api/ds/query` → `frames=1, series=0, maxpoints=0`. Secondary defect: even once fixed, summing raw counters is misleading across process restarts ("lifetime" resets to 0). |
| 101 | Request Rate (row) | row | actually fine | — |
| **10** | **Operations Rate (reads / writes / errors)** | timeseries, w24 | **display defect — missing aggregation, 50 series, duplicate legend names** | Targets return **22 + 26 + 2 = 50 series** (11 read ops x 2 jobs, 13 write ops x 2 jobs, 1 error counter x 2 jobs). `legendFormat` is the static string "Reads"/"Writes"/"Errors", so the legend shows **22 entries all named "Reads"** and **26 all named "Writes"** — indistinguishable. Needs `sum(rate(...))`. Sample values: reads `0.0175/s`, writes `0`, errors `0`. |
| 102 | Latency (row) | row | actually fine | — |
| **20** | **Write Latency (p50/p95/p99)** | timeseries | **duplicate scrape — 6 lines for 3 intended series** | Each of the three `histogram_quantile` targets returns **2 series**. Values: p50 `17.5`, p95 `24.25`, p99 `24.85` ms. Unit `ms` correct. |
| **21** | **Read Latency (p50/p95/p99)** | timeseries | **duplicate scrape — 6 lines for 3 intended — plus p99 unreliable** | Each target returns **2 series**. p50 `41.67`, p95 `99.29`, p99 `890.0` ms. The p99 of 890 ms sits inside the widest bucket (500–1000 ms) with 0.47% of samples already overflowing to `+Inf` — the interpolated value carries large error. |
| 103 | Infrastructure (collapsed row) | row | actually fine | — |
| **30** | **DB Connection Pool** | timeseries | **duplicate scrape (2 lines) + metric does not measure a pool** | `registry_db_connections` → **2 series**, both `0`, 24h max `1`. Same issue as id=5. |
| 31 | Process Memory | timeseries | **actually fine — the only correctly-scoped panel** | `process_resident_memory_bytes{job="registry-api"}` → **1 series** (`182616064` B = 174 MiB); `process_virtual_memory_bytes{job="registry-api"}` → **1 series** (`1614823424` B = 1.5 GiB). The explicit `job=` filter is exactly what every other panel is missing. Unit `bytes` correct. Minor: RSS and VSZ on one linear axis differ ~9x. |

**Layout geometry: clean.** Zero overlapping cells. Contiguous stack: row100@y0 → six w4 stat tiles y1-y5 → row101@y5 → panel10 w24 y6-y14 → row102@y14 → two w12 panels y15-y23 → row103@y23 collapsed. No empty rows.

**Visible consequence in the Overview row:** of six stat tiles, **2 read "No data"** (ids 1, 6) and **4 render doubled** (ids 2, 3, 4, 5). Not one of the six top-row tiles displays a single clean number. That is almost certainly what is being described as "the dashboard shows errors."

---

## 5. Root-cause classification summary

| Class | Count | Panels |
|---|---|---|
| Bad query syntax (PromQL vector matching) | 2 | REG 1, REG 6 |
| Duplicate scrape → doubled series | 7 | REG 2, 3, 4, 5, 10, 20, 21, 30 (8 incl. 30) |
| Missing aggregation → series fan-out | 4 | PG 1, PG 5, PG 20, REG 10 |
| Mismatched magnitude on shared axis | 2 | PG 11, PG 41 |
| Histogram top-bucket saturation | 2 | REG 4, REG 21 |
| Metric semantics mismatch (title ≠ metric) | 4 | REG 2 ("Error Rate" = DB errors only), REG 5 & 30 ("pool" max=1), REG row 100 ("RED Metrics" with no HTTP metrics) |
| Useless / all-zero | 1 | PG 40 |
| Actually fine | 10 | PG 2, 3, 4, 6, 10, 21, 30, 31; REG 31; all rows |
| **Missing exporter** | **0** | — all 18 targets UP |
| **Renamed metric** | **0** | — every referenced metric exists |
| **Metric never existed** | **0** | — every referenced metric has series |
| **Wrong label** | **0** | — `datname` present on all filtered PG metrics; registry panels use no labels |
| **Wrong datasource uid** | **0** | — all reference `prometheus`, which exists |
| **Layout overlap / empty row** | **0** | — programmatic gridPos check clean on both |

## 6. Cross-cutting infrastructure defects (not panel-local)

1. **Double scrape of `dhg-registry-api`.** `observability/prometheus/prometheus.yml:27-29` (static `registry-api`) and `:143-170` (`docker-sd` via the `prometheus.io/scrape` container label) both scrape `registry/api.py:298`. Doubles storage and breaks 8 of 11 registry panels visually. *(Worth checking whether `dhg-vs-engine` and `dhg-session-logger` have the same collision — `process_resident_memory_bytes` shows `dhg-vs-engine` under both `docker-sd` and `vs-engine` jobs. Not in scope for this audit.)*
2. **No HTTP instrumentation on the registry.** `registry/api.py:298` returns bare `generate_latest()`. Without `prometheus-fastapi-instrumentator` or equivalent there is no per-route request rate, no HTTP status-code error ratio, and no request duration — so the "RED Metrics" row cannot be made correct by editing the dashboard alone.
3. **`registry_errors_total` is dead.** Defined at `registry/metrics.py:33-37`, imported by ~15 endpoint modules, but has **0 series** in Prometheus over the retention window and is queried by no dashboard.
4. **`grafana-image-renderer` is not installed**, so no alert screenshots, no PDF/PNG export, and no scripted dashboard capture. `/var/lib/grafana/plugins` is empty.
5. **Read-latency histogram is under-bucketed** for its observed distribution: top finite bucket 1000 ms with 0.47% overflow, and a 500→1000 ms gap that is where p99 currently lands.

---

*No fixes proposed — audit only. No Grafana state modified; no repo file modified.*
