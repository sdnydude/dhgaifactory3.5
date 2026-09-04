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

Four provisioning providers, one per folder, each pointed at its own subdirectory:

| Folder | Path | Holds |
|---|---|---|
| `DHG / Platform` | `json/platform` | host, containers, databases, logs, daemons |
| `DHG / Services` | `json/services` | one board per application service |
| `DHG / AI` | `json/ai` | model/agent/inference boards |
| `DHG / Alerting` | `json/alerting` | rule engine, delivery, alert state |

Provisioning creates the folders. Grafana 10.2 does **not** provision folder permissions
from files — after adding a folder, grant the Viewer role read on it via
`POST /api/access-control/folders/{uid}/users|builtInRoles`, or the `dhg-verify` service
account cannot render it.

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
  `bytes`, `short`. An unset unit is a defect.
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
- `refresh: "30s"`, `time.from: "now-6h"`, `version: 1`, `schemaVersion: 38`.
- `tags`: `["dhg", "<folder>", …subject]`, e.g. `["dhg", "services", "registry", "api"]`.

## Brand

Grafana org default dark theme, `palette-classic` series colours. DHG purple `#663399`
appears only in text and link panels — never on a threshold, where colour must mean
health and nothing else.

## Verification

`observability/scripts/verify-dashboard.sh <uid>` replays every panel through
`/api/ds/query` and renders the board to `observability/verify/<uid>.png`. Exit 0
requires every panel to answer without error and return at least one series.

A panel that is legitimately empty when the system is healthy is listed by panel id in
`observability/verify/allow-empty/<uid>.txt`, one per line, each with a trailing `#`
comment giving the reason. Nothing else belongs in those files — an allow-empty entry
added to silence a broken query is how a dead board survives.

Current entries:

- `dhg-log-analytics` 41 — registry-db error/fatal log lines; the DB logs nothing but `LOG` when healthy.
- `dhg-platform-overview` 10, 11 — targets-down and firing-alerts tables; empty is the goal state.
- `dhg-postgresql` 40 — lock modes filtered to `> 0`; no rows means no locks held.
