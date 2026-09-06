# DHG Grafana dashboard standard

Grafana 10.2.0 at `http://10.0.0.251:3001` (container `dhg-grafana`). This file is the
source of truth for how DHG dashboards are built. A board that breaks a rule here does
not ship.

## Source of truth

`observability/grafana/provisioning/dashboards/json/<folder>/` is the only place a
dashboard lives. One file per dashboard, tracked in git, provisioned into the container
via the `observability/grafana/provisioning` bind mount. There is no second tree, and no
dashboard is authored in the UI: `allowUiUpdates: true` means a UI save persists, so any
UI edit must be copied back into the repo file in the same session or it is lost on the
next provisioning pass.

## Folders

Five provisioning providers, one per folder, each pointed at its own subdirectory:

| Folder | Path | Holds |
|---|---|---|
| `DHG / Platform` | `json/platform` | host, containers, databases, logs, daemons |
| `DHG / Services` | `json/services` | one board per application service |
| `DHG / AI` | `json/ai` | model/agent/inference boards |
| `DHG / Alerting` | `json/alerting` | rule engine, delivery, alert state |
| `DHG / Registry` | `json/registry` | boards over the registry Postgres (SQL, not Prometheus) |

Provisioning creates the folders — **with no permissions at all**. Grafana 10.2 applies
the default ACL (creator → Admin, built-in Editor → Edit, built-in Viewer → View) only
when a folder is created through the UI or the folder API. The dashboard file provisioner
creates its folder under a background identity with `userID=0`, logs
`Could not make user admin ... identifier is not initialized`, and leaves
`GET /api/folders/{uid}/permissions` returning `[]`. Because dashboard access in Grafana
is entirely folder-scoped — the OSS basic Viewer role carries `datasources:read` but no
global `dashboards:read` — a freshly provisioned folder is invisible to every non-Admin
identity, including the `dhg-verify` service account (`/api/search` omits it,
`GET /api/dashboards/uid/<uid>` returns 403). File-based provisioning of folder
permissions is Grafana Enterprise only, so the OSS fix is a script:

```
observability/scripts/grant-folder-viewer.sh          # --dry-run to preview
```

It walks `/api/folders` and grants built-in Viewer → View and Editor → Edit on any folder
missing them, preserving existing user and team grants. It is idempotent — folders that
already have both are reported `unchanged`. **Run it after every
`docker compose up -d grafana` / `docker compose restart grafana`**, which is the only
time a new provider folder can appear (provider config is read at startup only). Grafana
caches RBAC decisions for a few seconds, so a newly granted folder may 403 for one more
request before it answers 200.

It authenticates as the Grafana admin: user from `docker inspect dhg-grafana`
(`GF_SECURITY_ADMIN_USER`), password from Doppler `dhg-monitoring/dev`
`GF_SECURITY_ADMIN_PASSWORD`; both are overridable with `GF_ADMIN_USER` /
`GF_ADMIN_PASSWORD`.

Provider config (`dashboards/dashboards.yml`) is read at Grafana **startup only**;
restart `dhg-grafana` after editing it. Dashboard JSON re-provisions live every 10s.

## Naming

- `uid`: kebab-case, stable forever. Changing a uid breaks bookmarks, `verify-dashboard.sh`
  and every `allow-empty` file. New boards use `dhg-<folder>-<subject>`; existing uids are
  never renamed.
- Filename matches the uid exactly (`vs-engine-overview.json`, not `vs-engine.json`).
- `title`: human sentence case, no uid echo.

## Layout

Row order on a service board: **RED** (rate, errors, duration) → **USE** (CPU, memory,
restarts) → dependencies → logs. Platform boards run health → detail → containers →
services → logs.

- Grid is 24 columns; every row band must sum to exactly 24 with no overlaps and no gaps.
- Top row is stat tiles, height 4. Below that, timeseries at height 8.
- Rare-but-useful detail goes in a `collapsed: true` row.

## Queries

- **`sum by (le)` on every quantile.** `histogram_quantile(q, sum by (le) (rate(x_bucket[5m])))`.
  Without it the quantile silently splits per replica the day a second one appears.
- **Aggregate before you add.** Two counters with disjoint label values cannot be added
  with a bare `+` — the vector match produces an empty result. `sum(rate(a)) + sum(rate(b))`.
- **Aggregate away labels the panel does not show.** A stat tile fed an unaggregated
  metric renders one tile per series. `sum()`, `max()`, or a `by ()` clause that matches
  the legend.
- **Sparse series need a wider window.** A histogram observed a few times an hour is NaN
  in nearly every 5m window. Use `increase(...[1h])` and set `spanNulls: true`.
- **Pin the job or the label selector**, never a hardcoded instance address.
- **`or vector(0)` only where absence is genuinely ambiguous** (alert counts, error
  counters that have never fired). Where absence means a broken exporter, pair the
  guarded panel with an explicit "metric present" tile so a zero cannot be misread.

## Variables

`$service` and `$instance` on service boards, and only where the metric actually carries
those labels — added blindly they produce selectors that match nothing. Both are
`type: query`, `multi: true`, `includeAll: true`, `refresh: 2` (on time range change),
`sort: 1`, with `current` set to All. Selectors use `=~`, e.g.
`registry_read_latency_bucket{service=~"$service", instance=~"$instance"}`.

## Presentation

- `unit` is set on every field: `ops`, `reqps`, `percent`, `percentunit`, `s`, `ms`,
  `bytes`, `short`. An unset unit is a defect. Use `none`, not `short`, on any stat
  whose exact value is the point — `short` renders 1,113 as "1 K", which is precisely
  the rounding an honesty tile exists to avoid.
- Thresholds are semantic — green healthy, amber degraded, red act now — and absolute,
  never decorative. Health direction is encoded in the step order (a cache-hit gauge runs
  red → green).
- Legends are `displayMode: "table"` with `calcs`, and carry a real label
  (`{{operation}}`, `{{mountpoint}}`, `{{name}}`). A static legend string over a
  multi-series query is a defect — every entry renders with the same name.
- Series with magnitudes an order apart go on a right-hand axis via a `byName` override,
  or into their own panel.
- Every panel has a `description` saying what it measures and what a bad value means.
  Where a metric does not measure what its title suggests, the description says so.
- `refresh: "30s"`, `time.from: "now-6h"`, `version: 1`, `schemaVersion: 38`. SQL
  boards over the registry capture tables are the one exception to `now-6h`: those
  rows arrive a handful a day, so `dhg-registry-activity` defaults to `now-30d` — a
  6h window on it is legitimately, and uselessly, empty.
- `tags`: `["dhg", "<folder>", …subject]`, e.g. `["dhg", "services", "registry", "api"]`.

## Brand

Grafana org default dark theme, `palette-classic` series colours. DHG purple `#663399`
appears only in text and link panels — never on a threshold, where colour must mean
health and nothing else.

## Verification

`observability/scripts/verify-dashboard.sh <uid>` replays every panel through
`/api/ds/query` and renders the board to `observability/verify/<uid>.png`. Exit 0
requires every panel to answer without error and return at least one series.

Prometheus and Loki panels are replayed over `now-1h`. Postgres panels are replayed
over the **dashboard's own `time.from`**, because their `$__timeFilter()` is expanded
server-side against the request window and registry capture rows are sparse — a
`now-1h` replay of a 30-day board would call every SQL panel empty and be wrong.

A panel that is legitimately empty when the system is healthy is listed by panel id in
`observability/verify/allow-empty/<uid>.txt`, one per line, each with a trailing `#`
comment giving the reason. Nothing else belongs in those files — an allow-empty entry
added to silence a broken query is how a dead board survives.

Current allow-empty entries:

- `dhg-ai-langfuse` 20 — error/warn/fatal log lines from dh40801 containers; the two log-volume panels above it prove logs are still flowing.
- `dhg-alerting-pipeline` 10, 11, 50 — firing alerts by severity, pending alerts by rule, targets-down table; nothing firing / nothing down is the goal state.
- `dhg-log-analytics` 41 — registry-db error/fatal log lines; the DB logs nothing but `LOG` when healthy.
- `dhg-platform-overview` 10, 11 — targets-down and firing-alerts tables; empty is the goal state.
- `dhg-postgresql` 40 — lock modes filtered to `> 0`; no rows means no locks held.

## Current dashboards

Thirteen boards. Filename = uid; the folder is the subdirectory under
`provisioning/dashboards/json/`.

| Folder | uid | Purpose |
|---|---|---|
| `platform` | `dhg-platform-overview` | Platform-wide first look for g700data1: what is firing, what is down, host/container/service health. The reference board for the standard above. |
| `platform` | `docker-overview` | Per-container CPU, memory, network and restart counts from cAdvisor. |
| `platform` | `dhg-platform-gpu` | RTX 5080 health from `nvidia_gpu_exporter` — VRAM, utilisation, temperature, power. |
| `platform` | `dhg-platform-postgres` | All seven PostgreSQL instances on one board (`postgres` + `postgres-multi` jobs), keyed by `service`. |
| `platform` | `dhg-postgresql` | registry-db detail: connections, transactions, locks, table and index stats. |
| `platform` | `dhg-log-analytics` | Loki log volume by container, error rates, pattern search. |
| `platform` | `memreg-daemon` | memreg capture daemon (`job="memreg"`) — sweeps, DLQ depth, capture outcomes. |
| `services` | `dhg-registry-api` | Registry API RED signals plus its DB-operation counters and latency histograms. |
| `ai` | `dhg-ai-langfuse` | Langfuse on dh40801 and the host it runs on: health probe, canary round-trip, container and host metrics. |
| `ai` | `vs-engine-overview` | Verbalized Sampling engine, scoped to what the service actually exposes today. |
| `alerting` | `dhg-alerting` | Alert state overview — firing/resolved history by rule and severity. |
| `alerting` | `dhg-alerting-pipeline` | The alerting path end to end: rule evaluation in Prometheus and the Loki ruler, delivery through Alertmanager to Slack and the registry webhook. |
| `registry` | `dhg-registry-activity` | What the registry has captured — deferred items, decisions, insights, corrections, bug fixes, ship and agent sessions, test coverage. SQL over the small indexed capture tables only. |

## Registry DB datasource

`uid: registry-pg`, name **Registry DB**, type `postgres`, pointed at
`dhg-registry-db:5432/dhg_registry` over the internal docker network
(`sslmode: disable` — the DB publishes no TLS endpoint). Pool is deliberately small:
`maxOpenConns: 3`, `maxIdleConns: 1`, `connMaxLifetime: 300`.

**The role, not the pool, is what makes this safe.** Grafana connects as
`grafana_ro`, created 2026-09-05:

- `LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE`
- `CONNECT` on `dhg_registry`, `USAGE` on `public`, `SELECT` on all tables in
  `public`, plus `ALTER DEFAULT PRIVILEGES ... GRANT SELECT ON TABLES` so new
  tables are readable without a re-grant. No INSERT/UPDATE/DELETE anywhere.
- `ALTER ROLE grafana_ro SET statement_timeout = '10s'` — the load guard. The
  registry DB runs on `max_connections = 100` and serves the application; without
  this, one bad panel pins a connection against a multi-hundred-MB sequential scan
  (AUDIT-2026-09 advisor review, HIGH finding on `incident_actions`).
- `ALTER ROLE grafana_ro SET default_transaction_read_only = on` — belt and braces:
  even a mistaken grant cannot produce a write.

Before it existed, `dhg` — a SUPERUSER — was the only login role on that database.
Never point a dashboard at `dhg`.

**Provisioning is rendered, not tracked.** Grafana's `secureJsonData.password` takes
a literal, so:

| File | Tracked? | What it is |
|---|---|---|
| `provisioning/datasources/registry-postgres.yml.tmpl` | yes | source of truth |
| `provisioning/datasources/registry-postgres.yml` | **no** (gitignored) | rendered, contains the password |

```
observability/scripts/render-grafana-datasources.sh   # reads Doppler dhg-monitoring/dev
docker compose up -d grafana                          # datasources load at startup only
```

The password lives in Doppler `dhg-monitoring/dev` as `REGISTRY_GRAFANA_RO_PASSWORD`.
To rotate: `ALTER ROLE grafana_ro PASSWORD '<new>'`, update the Doppler secret,
re-render, restart Grafana. Health check:
`GET /api/datasources/uid/registry-pg/health` → `Database Connection OK`.

**What SQL boards may query.** Only the small indexed capture tables
(`deferred_items`, `decision_logs`, `insights`, `corrections`, `bug_fixes`,
`ship_sessions`, `agent_sessions`, `test_coverage`), all of which carry
`created_at` and an index on it. `incident_actions` and `incident_events` are
2.6M rows / ~700 MB each with no usable time index — **no panel may query them.**
`incidents` itself is limited to the single deliberately-labelled raw-count stat on
`dhg-registry-activity`: the table says ~1,113 active while `/api/incidents/stats`
says 110, and that gap is tracked as two open deferred items. Until it is fixed, no
incidents board.

## Tracing

Tempo was retired 2026-09-04 (AUDIT-2026-09 section 7, decision D-A): it never received
a span in production. The service definition still lives in `docker-compose.override.yml`
but is held out of `docker compose up` by a `profiles: ["retired"]` merge stanza in
`docker-compose.yml`; its data volume `dhgaifactory35_tempo_data` is left in place.
Grafana therefore has no `derivedFields` / `exemplarTraceIdDestinations` trace
links. Its three datasources are Prometheus, Loki and the read-only Registry DB
(see below).

All OTLP now goes to Langfuse at `http://10.0.0.179:3000/api/public/otel`
(traces: `/v1/traces`), authenticated with a project key pair as HTTP Basic.

To enable medkb trace export:

1. In the Langfuse UI (`http://10.0.0.179:3000`), create the project `dhg-ai-factory`
   and mint an API key pair. Do not reuse the portage or canary keys.
2. `doppler secrets set LANGFUSE_AIFACTORY_PUBLIC_KEY` and
   `LANGFUSE_AIFACTORY_SECRET_KEY` in project `dhg-monitoring`, config `dev`.
3. `observability/scripts/render-medkb-otel-env.sh` — writes the gitignored
   `services/medkb/.env.otel` (mode 600). Without the keys it warns and exits 0,
   and medkb starts with tracing disabled.
4. `docker compose up -d dhg-medkb-api`.

Pydantic AI agents do not use the legacy `traced_node` decorators: they call
`Agent.instrument_all()` and inherit the same Langfuse OTLP env.
