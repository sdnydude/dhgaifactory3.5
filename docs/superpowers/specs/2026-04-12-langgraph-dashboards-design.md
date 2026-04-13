# LangGraph Dashboards — Design Spec

**Date:** 2026-04-12
**Author:** DHG AI Factory
**Status:** Approved for implementation planning
**Related:** `docs/superpowers/specs/2026-03-10-frontend-design-brainstorm.md` (parent mission-control board)

## Goal

Add a dedicated operational dashboard for the 17 registered LangGraph graphs (13 individual agents + 4 orchestrator compositions), fed by free Prometheus metrics derived from OTel span data. The board answers "is the agent fleet healthy right now, and where should I look when it isn't?" — at a glance, without interactive exploration, and without per-view paid API calls.

## Non-Goals

- Long-window trend analysis (days/weeks). That belongs in Grafana.
- Token/cost reporting. Requires separate instrumentation; deferred to a later phase.
- Individual run input-output inspection. LangSmith already does this; we link out.
- Real-time log tailing. Loki has a better tool for it.
- A human-review workflow UI. `/inbox` already exists.

## Motivating Constraints

1. **Cost-consciousness.** LangGraph Cloud API calls are metered. Per-viewer, per-refresh polling would burn paid quota continuously. The dashboard must read from free infrastructure.
2. **Scale trajectory.** The platform will grow to 100+ agents and subagents. Panel designs must degrade gracefully — adding 10× more agents must not force a redesign.
3. **Mission-control consistency.** The existing `/dashboards` page established the aesthetic, polling cadence, and "glance-and-go" interaction model. The new board must be a sibling, not an outlier.
4. **Production safety.** Production services (LangGraph Cloud deployment, Cloudflared tunnel, Prometheus container args) must only be touched after explicit approval and with verification at each step.

## Two-Phase Architecture

Phase 1 fixes a dormant-but-designed telemetry pipeline. Phase 2 builds the user-facing dashboard on top of the now-flowing metrics. Neither phase can be skipped; phase 2 has nothing to render without phase 1.

### Phase 1 — Pipeline Repair (Prerequisite)

**Current state, verified:**
- `observability/tempo/tempo-config.yml` has `metrics_generator` configured with `span-metrics` and `service-graphs` processors, remote-writing to `http://prometheus:9090/api/v1/write`.
- `langgraph_workflows/dhg-agents-cloud/src/tracing.py` defines `@traced_node` decorators and initializes an OTel TracerProvider with `OTLPSpanExporter` (gRPC).
- 85 `@traced_node` decorators exist across 9 content agents + orchestrator (per `CLAUDE.md`).
- **However:** `tempo_distributor_metrics_generator_clients == 0`, Tempo tag search returns `{}`, and no `traces_spanmetrics_*` metrics appear in Prometheus. The pipeline exists only on paper.

**Three root causes to fix:**

**(1) LangGraph Cloud cannot reach our Tempo.**
Tempo's OTLP endpoints (`:4317` gRPC, `:4318` HTTP) are bound to the LAN only. The `OTEL_EXPORTER_OTLP_ENDPOINT` default in `tracing.py` is `http://localhost:4317`, which inside the Cloud runtime points at the Cloud container's own localhost — not at g700data1. We need a public endpoint. Solution: **new Cloudflare tunnel route**.

- Hostname: `otel.digitalharmonyai.com`
- Target: `http://localhost:4318` (Tempo's OTLP/HTTP ingest)
- Auth: Cloudflare Access application with a service token (`CF-Access-Client-Id` + `CF-Access-Client-Secret`)

**Why OTLP/HTTP over gRPC:** Cloudflared can tunnel gRPC but requires `http2Origin: true` and strict TLS-ALPN handling on the client side. OTLP/HTTP uses the same protobuf wire format over plain HTTPS — the tunnel treats it like any other HTTPS request, and it can be tested with `curl` during debugging.

**Code change in `tracing.py`:** one import swap.
```python
# from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
```
No other `tracing.py` logic changes.

**LangGraph Cloud environment variables to set:**
```
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.digitalharmonyai.com
OTEL_EXPORTER_OTLP_HEADERS=CF-Access-Client-Id=<id>,CF-Access-Client-Secret=<secret>
```
The OTel SDK reads both env vars automatically; no code change beyond the import.

**Verify OTel SDK is actually installed in the Cloud runtime.** `tracing.py` silently no-ops when the `opentelemetry-*` wheels are missing (with a log line: *"OpenTelemetry not available — tracing disabled (expected in Cloud)"*). Phase 1 must confirm the required packages are in the Cloud deployment's requirements:
- `opentelemetry-api`
- `opentelemetry-sdk`
- `opentelemetry-exporter-otlp-proto-http`

**(2) Prometheus refuses remote writes.**
Prometheus is missing the `--web.enable-remote-write-receiver` flag, so Tempo's `remote_write` target would 404 even if spans were arriving. Solution: add the flag to Prometheus's container args in `docker-compose.yml`, then restart `dhg-prometheus`.

**(3) No `langgraph_threads_by_state` metrics exist.**
Span-metrics alone cannot answer "how many threads are currently interrupted/running/pending" — that is a gauge of *state*, not a counter of events. Thread-state information lives only in the LangGraph Cloud API. To surface it on the dashboard without per-viewer API cost, we introduce a small **local thread-state exporter**.

### Local Thread-State Exporter (new component)

**Purpose:** Bridge the metered LangGraph Cloud API into the free Prometheus scrape fabric. Pulls thread counts on a fixed schedule shared across all viewers.

**Deliverable:** One new Docker service, `dhg-langgraph-exporter`, on `dhgaifactory35_dhg-network`.

**Behavior:**
- Every 30 seconds, issues up to 5 `GET /threads/search?status=<state>` calls to LangGraph Cloud (one per state: `idle`, `running`, `pending`, `interrupted`, `error`).
- Counts results per state.
- Exposes the counts as Prometheus gauges on its own `/metrics` endpoint.

**Exported metrics contract:**
```
langgraph_threads_by_state{state="idle"} <n>
langgraph_threads_by_state{state="running"} <n>
langgraph_threads_by_state{state="pending"} <n>
langgraph_threads_by_state{state="interrupted"} <n>
langgraph_threads_by_state{state="error"} <n>
langgraph_exporter_last_scrape_timestamp_seconds <unix_ts>
langgraph_exporter_scrape_errors_total <counter>
```

**Cost envelope:** 10 API calls/minute, 14,400/day, constant regardless of dashboard viewer count. Independent of agent count.

**Deployment shape:**
- Service name: `dhg-langgraph-exporter`
- Port: `8014` (confirmed free 2026-04-12)
- Image: `python:3.12-slim` + `httpx` + `prometheus_client` (~35 MB)
- Healthcheck: HTTP 200 on `/metrics`
- Restart policy: `unless-stopped`
- Secrets: `LANGCHAIN_API_KEY` from `.env` (same key the inbox proxy uses)

**Failure behavior:** On Cloud API error, metrics freeze at last-known values and `langgraph_exporter_scrape_errors_total` increments. The freshness readout on the fleet page reflects `langgraph_exporter_last_scrape_timestamp_seconds` — operators immediately see if the exporter has stalled.

### Prometheus Scrape Job Additions

Two new jobs in `observability/prometheus/prometheus.yml`:

```yaml
- job_name: 'tempo-metrics-generator'
  # Receives span-metrics and service-graph metrics from Tempo via remote_write
  # (no scrape target — remote_write is pushed by Tempo)

- job_name: 'langgraph-exporter'
  static_configs:
    - targets: ['dhg-langgraph-exporter:8014']
```

### Phase 1 Prometheus Alert Rules

Added to `observability/prometheus/alerts.yml`:

| Alert | Condition | Severity |
|---|---|---|
| `LangGraphHighErrorRate` | Per-graph span error rate > 5% for 5m | warning |
| `LangGraphSlowNode` | Per-node p95 > configured threshold for 10m (per-node tunable) | warning |
| `LangGraphNoTraffic` | No spans from a specific graph for 10m during business hours | info |
| `LangGraphStuckThread` | Thread in `running` state for > 30m (via exporter) | critical |
| `LangGraphExporterStalled` | `langgraph_exporter_last_scrape_timestamp_seconds` > 90s old | warning |
| `OtelIngestStalled` | `tempo_distributor_spans_received_total` rate == 0 for 10m | warning |

These route through the existing Alertmanager → registry-api webhook flow, lighting up the existing `B9` Alertmanager panel on `/dashboards` when they fire.

---

### Phase 2 — Dashboard Surfaces

Two pages. Both share the `.mc-*` styling from `globals.css` and the JetBrains Mono telemetry font from `layout.tsx`.

#### Page 1: `/dashboards/agents` (Agent Ops — Fleet View)

New sibling route. Gets its own entry in the sidebar "Observe" section, below "Mission Control". Polls every 10 seconds to match the existing board.

**Panel slate:**

| Coord | Panel | Data source | Scale behavior |
|---|---|---|---|
| Header | Agent Ops title, UTC clock, NOMINAL/DEGRADED readout, trace-ingest freshness | Computed from the below | — |
| **A1** | Graph Fleet Grid — one tile per graph (17 now, 100+ future). Each tile: name, status dot, success % 5m, p95, mini sparkline, last-run timestamp. Click → drill-down. | `traces_spanmetrics_calls_total`, `traces_spanmetrics_latency_bucket` | Grid reflows; tiles stay constant size; scrolls vertically past ~30 |
| **B1** | Top 5 Slowest Nodes — table sorted by p95 desc. Columns: agent, node, p95, trend arrow. | `traces_spanmetrics_latency_bucket` | Fixed 5 rows; grows zero with agent count |
| **B9** | Error Rate + Ingest Freshness — single big readout (rolling 15m error %), broken down by graph if non-zero, plus a sub-block showing trace-ingest lag | `traces_spanmetrics_calls_total{status_code="ERROR"}` + derived `rate()`; `tempo_distributor_spans_received_total` for freshness | Constant |
| **C1** | **Orchestrator Pipelines Spotlight** — one row per orchestrator composition. Each row: pipeline name, in-flight count, avg duration, and for each in-flight run, a **stage rail with an animated cyan marker** at the current node position. | Tempo search API for unfinished traces tagged `graph_id=<orchestrator>` | Grows with orchestrator count (not agent count); caps at ~10 in-flight markers per orchestrator, then collapses to "… +N more" |
| **C7** | Human Review Queue — big "N WAITING" readout, oldest wait time, pulsing link to `/inbox`, plus a thread-state line (running / pending / idle / error) | `langgraph_threads_by_state` (from local exporter) | Constant |
| **D1** | Anomaly Edges — table of service-graph edges with error rate > 1% *or* p95 > 2× historical median. Empty most of the time. Footer shows "N other edges healthy · hidden". | `traces_service_graph_request_total`, `traces_service_graph_request_failed_total` | Signal-filtered; stays small at any scale |
| **D9** | Deep Inspect Links — escape hatches to LangSmith, Tempo, LangGraph Studio, Prometheus raw query | Static | Constant |

#### Page 2: `/dashboards/agents/[graphId]` (Graph Detail)

Dynamic Next.js route. Linked from every fleet tile. Deep-linkable — URL carries the graph ID so bookmarks and Slack links land on specific detail views.

**Panel slate:**

| Coord | Panel | Content |
|---|---|---|
| Header | Graph name, file path, line count, role (standalone vs. orchestrator stage), current health readout |
| **B1** | Per-Node Metrics Table — every node in this graph: calls, p95, error %, last timestamp. Sorted by p95 desc. Click a row → Tempo trace search for that node. |
| **B9** | Throughput Sparkline — runs/min for this graph over 15m |
| **C1** | Graph Topology DAG — node graph rendered from service-graph metrics, nodes colored by latency (green ≤ 1s · amber 1–5s · red > 5s). See "Topology Rendering" below. |
| **C7** | Recent Runs Table — last 20 runs: timestamp, trace ID (clickable → Tempo), duration, status. |
| **D1** | Error Breakdown — if errors exist: grouped by node and exception class. Otherwise "NO ERRORS IN WINDOW". |

---

## Topology Rendering

The `C1` panel on the detail page renders the graph's DAG using `traces_service_graph_request_total` edges, where the `client` and `server` labels identify node-to-node calls within a single LangGraph invocation. For v1 the rendering is deliberately simple:

- Nodes laid out in execution order (topological sort via `orchestrator.py` and per-agent graph definitions, or falling back to edge-frequency ordering if AST parsing is too brittle)
- ASCII-arrow rendering (`[node1] ─→ [node2] ─→ [node3]`) for the v1 implementation
- Node color by latest p95 from `traces_spanmetrics_latency_bucket`

A full D3 force-directed visualization is explicitly deferred. If the 17-graph version lands well, a follow-on plan can upgrade the renderer.

## Animated Orchestrator Markers (C1 fleet panel)

The marker animation is the most involved piece of the dashboard. Design:

**Data source.** Tempo's `/api/search` endpoint queries unfinished traces (traces with at least one span but no root-span end timestamp yet) tagged with `graph_id=<orchestrator_name>`. For each unfinished trace, the most recent unclosed span identifies the current stage.

**Stage extraction.** Each orchestrator graph (`needs_package`, `curriculum_package`, `grant_package`, `full_pipeline`) has a known, ordered list of stages defined in `orchestrator.py`. The fleet page reads these stage lists at build time (server component) so the rail structure is stable across polls.

**Server-side caching.** The Tempo search is fanned out once per poll on the Next.js server, not per viewer. An `unstable_cache` wrapper with a 2.5s TTL ensures that N concurrent viewers share a single Tempo query. This is the equivalent of the existing `/api/prometheus/[...path]` pattern.

**Client-side animation.** CSS transitions on the marker's `left` property. Poll every 2.5s; new marker positions are applied smoothly. A marker that is stuck (span age > 2× historical p95 for that node) stops pulsing and turns amber — visual cue for stuck runs without needing a latency threshold config.

**Cap on concurrent markers.** If more than 10 runs are in flight for a single orchestrator, markers collapse into an aggregate "🟢 12 runs in flight" bar, with a link to a dedicated all-runs view. This prevents chaos at scale.

**Fallback when Tempo search is slow or errors.** The rail still renders; markers are simply omitted and the header reads "marker data unavailable". The rest of the panel (pipeline name, historical avg duration) keeps working.

## Scale Considerations (17 → 100+ agents)

| Panel | Behavior at 17 | Behavior at 100 | Behavior at 500 |
|---|---|---|---|
| A1 Fleet Grid | 17 tiles, 3 rows × 6 | 100 tiles, ~16 rows × 6, scrollable | Needs pagination or category collapsing |
| B1 Top 5 Slow | Fixed 5 rows | Fixed 5 rows | Fixed 5 rows |
| B9 Error + Freshness | Single readout | Single readout | Single readout |
| C1 Orchestrators | ~4 rows | ~20 rows | ~20–50 rows |
| C7 Review Queue | Single readout | Single readout | Single readout |
| D1 Anomaly Edges | Usually 0 rows, rarely 5 | Usually 0 rows, rarely 5 | Usually 0 rows, rarely 5 |
| D9 Links | Static | Static | Static |

A1 is the only panel that has a redesign threshold. The redesign (category collapsing or pagination) is out of scope for v1. The other panels are designed to stay constant in size regardless of fleet growth.

## Data Flow

```
LangGraph Cloud (9 content agents + orchestrator, @traced_node decorators)
        │
        │  OTLP/HTTP (protobuf)
        │  + CF-Access-Client-Id/Secret headers
        ▼
  cloudflared (otel.digitalharmonyai.com)
        │
        ▼
  dhg-tempo:4318  ──→  metrics_generator  ──→  remote_write  ──→  dhg-prometheus:9090
        │                                                              ▲
        │                                                              │
        ▼                                                              │
   trace storage                                                       │
                                                                       │
  LangGraph Cloud API ◀── /threads/search ── dhg-langgraph-exporter ───┘
                                              (30s poll, 5 calls)

  dhg-frontend  ──→  /api/prometheus/[...path]  ──→  dhg-prometheus
                ──→  /api/tempo/[...path]       ──→  dhg-tempo (for trace lookups only)
```

The frontend never touches LangGraph Cloud directly for dashboard data. The existing `/api/langgraph/*` proxy stays in place for the `/inbox` feature, which *does* need thread-level state manipulation.

## Component Boundaries

| Unit | Purpose | Interface | Depends on |
|---|---|---|---|
| `tracing.py` (modified) | Initialize OTel SDK with OTLP/HTTP exporter, decorate nodes with spans | Python decorator `@traced_node` | `opentelemetry-*` wheels, `OTEL_EXPORTER_OTLP_*` env vars |
| `dhg-langgraph-exporter` (new) | Poll Cloud API for thread states, expose Prometheus metrics | HTTP `GET /metrics` | `LANGCHAIN_API_KEY`, LangGraph Cloud availability |
| Tempo metrics_generator (config only) | Derive span-metrics + service-graph metrics from spans | Prometheus remote_write | Prometheus accepting writes |
| Prometheus (config only) | Accept remote writes, scrape exporter, evaluate alerts | HTTP `GET /api/v1/query`, scrape jobs | Tempo, exporter, alerts.yml |
| `/api/prometheus/[...path]` (existing) | Proxy browser PromQL queries server-side | HTTP passthrough | Prometheus |
| `/api/tempo/[...path]` (new) | Proxy Tempo `/api/search` for animated markers; cached | HTTP passthrough with `unstable_cache` | Tempo |
| `/dashboards/agents/page.tsx` (new) | Fleet page rendering | React component | `/api/prometheus/*`, `/api/tempo/*` |
| `/dashboards/agents/[graphId]/page.tsx` (new) | Detail page rendering | React component | `/api/prometheus/*`, `/api/tempo/*` |
| Sidebar nav (modified) | Add "Agent Ops" entry under Observe | JSX | — |

Each unit is independently testable: the exporter has its own unit tests (mocked Cloud API), the topology rendering has snapshot tests against recorded metric fixtures, the marker animation has a visual regression test via Playwright.

## Testing Approach

**Phase 1 verification (infra):**
1. Curl `https://otel.digitalharmonyai.com/v1/traces` with correct CF-Access headers — expect HTTP 200
2. Send a synthetic span via `otel-cli` and confirm it appears in Tempo `api/search`
3. Query Prometheus for `traces_spanmetrics_calls_total` — expect non-empty result
4. Query Prometheus for `langgraph_threads_by_state` — expect all 5 state labels present
5. Restart `dhg-langgraph-exporter`, confirm `langgraph_exporter_last_scrape_timestamp_seconds` updates within 35s

**Phase 2 verification (UI):**
1. Unit tests for metric-parsing helpers (fleet tile computation, slow-node ranking, anomaly-edge filter)
2. Snapshot tests for fleet page and detail page using recorded Prometheus query fixtures
3. Playwright E2E: load `/dashboards/agents`, assert fleet grid has 17 tiles with non-`——` values, assert sidebar has new "Agent Ops" entry, click a tile and assert URL changes to `/dashboards/agents/<id>`
4. Playwright visual regression on the orchestrator marker animation (capture keyframes, assert marker position changes between frames)

## Security & Cost

- `otel.digitalharmonyai.com` is gated by Cloudflare Access service token — only LangGraph Cloud (which holds the service-token secret) can POST spans. Prevents random internet traffic polluting Tempo.
- `LANGCHAIN_API_KEY` in the exporter stays in `.env` and is mounted as an env var. Never logged, never exposed.
- Dashboard viewers make zero paid LangGraph Cloud API calls — all traffic flows through free Prometheus.
- Tempo trace search (used for markers) is free and local.

## Resolved Design Decisions

- **Stage list extraction.** Single source of truth in `langgraph_workflows/dhg-agents-cloud/src/orchestrator_stages.py` (a new Python constants module). A build-time script (`scripts/export-orchestrator-stages.ts` or a `make` target) serializes the constants to `frontend/src/generated/orchestrator-stages.json`, which the fleet page imports. The Python module is imported by `orchestrator.py` itself so drift is caught at import time, not dashboard-render time.
- **Exporter port.** `8014` — confirmed free on host and in Docker as of 2026-04-12.

## Open Questions (non-blocking — resolvable during implementation)

1. **Alert thresholds.** `LangGraphSlowNode` needs per-node p95 thresholds. Starting values can be derived from the first week of recorded metrics; bake defaults into `alerts.yml` with inline comments.
2. **Tempo search API latency.** Need to benchmark `/api/search` for unfinished traces at the current fleet scale. If too slow, fall back to querying by `span_start_time > now - 10m AND span_end_time == null`.

## Success Criteria

Phase 1 is done when:
- A synthetic span sent from LangGraph Cloud lands in Tempo within 10 seconds
- Prometheus shows non-zero `traces_spanmetrics_calls_total` for every graph that has been invoked
- `langgraph_threads_by_state` is scraped and visible in Prometheus
- All six new alert rules load without syntax errors and at least one fires correctly in a synthetic test

Phase 2 is done when:
- `/dashboards/agents` renders with live data for all 17 graphs and 4 orchestrators
- At least one animated marker is observed on the orchestrator spotlight during a real grant_package run
- A click on a fleet tile navigates to `/dashboards/agents/<graphId>` with a populated detail page
- The sidebar has a new "Agent Ops" entry and it's role-gated consistently with the existing pattern
- All Playwright tests pass against a live frontend container
- The board works in both light and dark modes (though v1 uses the dark mission-control palette exclusively, consistent with `/dashboards`)
- A hard refresh from a cold state never shows a stale frame — loading states are explicit

## Out of Scope for v1 (tracked for future)

- Token-count and cost panels (requires adding token attributes to `@traced_node` spans)
- D3 force-directed topology view (v1 uses ASCII arrows)
- Category-collapsing for the fleet grid at 100+ agents
- A dedicated `/dashboards/agents/topology` explorer page
- A "queued / in-flight / done" timeline view
- Light-mode variant of the Agent Ops board
- Mobile layout
