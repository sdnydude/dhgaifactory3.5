# Grafana Dashboards

Create and manage production Grafana dashboards for the DHG AI Factory observability stack.

## Capabilities

**What this command does:** Writes and deploys Grafana dashboard JSON files for the DHG AI Factory, using Prometheus and Loki data sources, following RED/USE methodology, and placing panels in the provisioning directory for auto-reload.

**Use it when you need to:**
- Create a new dashboard for agent performance (request rate, P95 latency, error rate) or token/cost usage
- Add panels to the system health dashboard covering host CPU, memory, disk, and container resource metrics
- Build a service status table or stat panel showing which DHG containers are UP or DOWN
- Add template variables to allow multi-service filtering by `job` or `container` label
- Troubleshoot a dashboard that shows "No data" by tracing the PromQL or Loki label mismatch

**Example invocations:**
- `/project:grafana-dashboards create a token usage dashboard showing LLM costs by agent and model`
- `/project:grafana-dashboards add a P95 latency time-series panel to the core golden signals dashboard`
- `/project:grafana-dashboards create a system health dashboard with host CPU, memory, disk, and PostgreSQL connection panels`

## Project Context

- Grafana runs at http://localhost:3001 (container: `dhg-grafana`, internal port 3000)
- Credentials: admin / admin123 (set via `GF_SECURITY_ADMIN_USER` / `GF_SECURITY_ADMIN_PASSWORD`)
- Dashboard JSON files live at: `observability/grafana/provisioning/dashboards/json/`
- Provisioning config: `observability/grafana/provisioning/dashboards/dashboards.yml`
- Grafana auto-reloads dashboards every 10 seconds (`updateIntervalSeconds: 10`)
- Data sources already provisioned:
  - **Prometheus** (default, uid: `prometheus`) — `http://prometheus:9090`, scrape interval 15s
  - **Loki** (uid: `loki`) — `http://loki:3100`, max lines 1000
- Docker network: `dhgaifactory35_dhg-network`

## Prometheus Scrape Targets

Current jobs defined in `observability/prometheus/prometheus.yml`:

| Job | Target | Scrape Interval |
|-----|--------|-----------------|
| `prometheus` | localhost:9090 | 15s |
| `registry-api` | registry-api:8000 | 10s |
| `postgres` | postgres-exporter:9187 | 30s |
| `node-exporter` | 172.18.0.1:9100 | 15s |
| `cadvisor` | cadvisor:8080 | 15s |

## Task: $ARGUMENTS

Clarify what dashboard is being built, which data source it targets, and what panels are needed. Then proceed with the steps below.

---

## Step 1 — Understand the Request

Before writing any JSON:

1. Identify the dashboard category (agent performance / token usage / system health / service SLO / custom)
2. Confirm which Prometheus metrics or Loki log streams are available for the required panels
3. Check whether an existing dashboard in `observability/grafana/provisioning/dashboards/json/` already covers this need

Read the existing `dhg-core-golden.json` to understand the established panel structure before diverging from it.

---

## Step 2 — Dashboard Design Principles

### Information Hierarchy (top to bottom in every dashboard)
```
┌─────────────────────────────────────┐
│  Critical Metrics (Stat panels)     │  ← row 0, full width
├─────────────────────────────────────┤
│  Key Trends (Time Series)           │  ← rows 1-2
├─────────────────────────────────────┤
│  Detailed Metrics (Tables/Heatmaps) │  ← rows 3+
└─────────────────────────────────────┘
```

### Method Selection

**RED Method** — for services (agents, APIs):
- Rate — requests per second
- Errors — error rate %
- Duration — latency (P50, P95, P99)

**USE Method** — for infrastructure (containers, host):
- Utilization — % time resource is busy
- Saturation — queue depth / wait time
- Errors — error counts

---

## Step 3 — Panel Type Reference

### Stat Panel (single critical KPI)
```json
{
  "type": "stat",
  "title": "Active Agents",
  "datasource": {"type": "prometheus", "uid": "prometheus"},
  "targets": [{
    "expr": "count(up{job=~\"registry-api\"} == 1)",
    "refId": "A"
  }],
  "options": {
    "reduceOptions": {"calcs": ["lastNotNull"]},
    "orientation": "auto",
    "textMode": "auto",
    "colorMode": "background"
  },
  "fieldConfig": {
    "defaults": {
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {"value": null, "color": "red"},
          {"value": 1, "color": "yellow"},
          {"value": 3, "color": "green"}
        ]
      }
    }
  },
  "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4}
}
```

### Time Series Panel
```json
{
  "type": "timeseries",
  "title": "Agent Request Rate",
  "datasource": {"type": "prometheus", "uid": "prometheus"},
  "targets": [{
    "expr": "sum(rate(http_requests_total{job=\"registry-api\"}[5m])) by (service)",
    "legendFormat": "{{service}}",
    "refId": "A"
  }],
  "fieldConfig": {
    "defaults": {
      "custom": {
        "drawStyle": "line",
        "lineInterpolation": "linear",
        "fillOpacity": 10,
        "lineWidth": 1,
        "showPoints": "auto",
        "spanNulls": false
      },
      "unit": "reqps"
    }
  },
  "options": {
    "legend": {"displayMode": "list", "placement": "bottom", "showLegend": true},
    "tooltip": {"mode": "single", "sort": "none"}
  },
  "gridPos": {"x": 0, "y": 4, "w": 12, "h": 8}
}
```

### Table Panel (service status)
```json
{
  "type": "table",
  "title": "Service Status",
  "datasource": {"type": "prometheus", "uid": "prometheus"},
  "targets": [{
    "expr": "up",
    "format": "table",
    "instant": true,
    "refId": "A"
  }],
  "transformations": [
    {
      "id": "organize",
      "options": {
        "excludeByName": {"Time": true, "__name__": true},
        "renameByName": {
          "instance": "Instance",
          "job": "Service",
          "Value": "Up"
        }
      }
    }
  ],
  "gridPos": {"x": 0, "y": 16, "w": 24, "h": 8}
}
```

### Heatmap Panel (latency distribution)
```json
{
  "type": "heatmap",
  "title": "Request Latency Heatmap",
  "datasource": {"type": "prometheus", "uid": "prometheus"},
  "targets": [{
    "expr": "sum(rate(http_request_duration_seconds_bucket[5m])) by (le)",
    "format": "heatmap",
    "refId": "A"
  }],
  "options": {
    "calculate": false,
    "yAxis": {"unit": "s"}
  },
  "gridPos": {"x": 0, "y": 24, "w": 24, "h": 8}
}
```

### Loki Logs Panel
```json
{
  "type": "logs",
  "title": "Agent Logs",
  "datasource": {"type": "loki", "uid": "loki"},
  "targets": [{
    "expr": "{container=\"dhg-agents-cloud\"} |= \"ERROR\"",
    "refId": "A"
  }],
  "options": {
    "dedupStrategy": "none",
    "showLabels": false,
    "wrapLogMessage": true,
    "sortOrder": "Descending"
  },
  "gridPos": {"x": 0, "y": 32, "w": 24, "h": 10}
}
```

---

## Step 4 — DHG-Specific Dashboard Templates

### Agent Performance Dashboard

Filename: `observability/grafana/provisioning/dashboards/json/dhg-agent-performance.json`

Key panels in order:
1. **Stat row** — Agent count (up), total requests served (counter), active errors (rate)
2. **Time series** — Request rate per agent (`rate(http_requests_total[5m]) by (job)`)
3. **Time series** — P95 latency per agent (`histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]) by (le, job))`)
4. **Time series** — Error rate % (`rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100`)
5. **Heatmap** — Latency distribution
6. **Logs panel** — Agent error log stream from Loki

### Token Usage Dashboard

Filename: `observability/grafana/provisioning/dashboards/json/dhg-token-usage.json`

Assumes LangGraph agents expose token metrics via `/metrics`. If not yet instrumented, note which metrics need adding to the agent code using `prometheus_client` (Python).

Key panels:
1. **Stat row** — Total tokens today, estimated cost today, requests in last hour
2. **Time series** — Token consumption rate by model (`rate(llm_tokens_total[5m]) by (model)`)
3. **Time series** — Input vs output tokens split
4. **Bar chart** — Cost per agent (if per-agent attribution is available)
5. **Table** — Top 10 most expensive requests (if request-level data is scraped)

Required custom Prometheus metrics (add to agent code if missing):
```python
from prometheus_client import Counter, Histogram, start_http_server

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    ["model", "agent", "direction"]  # direction: input|output
)
llm_request_cost_dollars = Counter(
    "llm_request_cost_dollars_total",
    "Estimated LLM cost in USD",
    ["model", "agent"]
)
llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM API call duration",
    ["model", "agent"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60]
)
```

### System Health Dashboard

Filename: `observability/grafana/provisioning/dashboards/json/dhg-system-health.json`

Key panels:
1. **Stat row** — Host CPU %, host memory %, disk used %, containers running
2. **Time series** — CPU utilization (`100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`)
3. **Time series** — Memory usage (`(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100`)
4. **Time series** — Container CPU per service (`rate(container_cpu_usage_seconds_total{name=~"dhg-.*"}[5m]) * 100`)
5. **Time series** — Container memory per service (`container_memory_usage_bytes{name=~"dhg-.*"}`)
6. **Time series** — Network I/O (`rate(node_network_receive_bytes_total[5m])`, `rate(node_network_transmit_bytes_total[5m])`)
7. **Time series** — Disk I/O (`rate(node_disk_read_bytes_total[5m])`, `rate(node_disk_written_bytes_total[5m])`)
8. **Table** — PostgreSQL connections and query latency (from `postgres-exporter`)
9. **Alerts panel** — Active firing alerts

Useful cAdvisor metric names:
- `container_cpu_usage_seconds_total{name=~"dhg-.*"}`
- `container_memory_usage_bytes{name=~"dhg-.*"}`
- `container_fs_reads_bytes_total{name=~"dhg-.*"}`
- `container_network_receive_bytes_total{name=~"dhg-.*"}`

---

## Step 5 — Dashboard JSON Skeleton

Use this as the outer wrapper for every new dashboard. Fill in `title`, `uid`, `tags`, and `panels`:

```json
{
  "annotations": {
    "list": [{
      "builtIn": 1,
      "datasource": {"type": "grafana", "uid": "-- Grafana --"},
      "enable": true,
      "hide": true,
      "iconColor": "rgba(0, 211, 255, 1)",
      "name": "Annotations & Alerts",
      "type": "dashboard"
    }]
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "id": null,
  "links": [],
  "liveNow": false,
  "panels": [],
  "refresh": "30s",
  "schemaVersion": 38,
  "tags": ["dhg", "CATEGORY"],
  "templating": {"list": []},
  "time": {"from": "now-6h", "to": "now"},
  "timepicker": {},
  "timezone": "browser",
  "title": "DHG — DASHBOARD TITLE",
  "uid": "dhg-UNIQUE-ID",
  "version": 1
}
```

**uid rules:**
- Must be unique across all dashboards
- Use kebab-case: `dhg-agent-performance`, `dhg-token-usage`, `dhg-system-health`

---

## Step 6 — Template Variables

Add to `templating.list` for multi-service filtering:

```json
{
  "templating": {
    "list": [
      {
        "name": "job",
        "label": "Service",
        "type": "query",
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "query": "label_values(up, job)",
        "refresh": 2,
        "multi": true,
        "includeAll": true,
        "sort": 1
      },
      {
        "name": "container",
        "label": "Container",
        "type": "query",
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "query": "label_values(container_cpu_usage_seconds_total{name=~\"dhg-.*\"}, name)",
        "refresh": 2,
        "multi": true,
        "includeAll": true,
        "sort": 1
      }
    ]
  }
}
```

Use variables in queries:
```
rate(http_requests_total{job=~"$job"}[5m])
container_memory_usage_bytes{name=~"$container"}
```

---

## Step 7 — Alert Definitions

DHG uses Grafana-provisioned alerts evaluated by the unified alerting engine. Existing SLO alerts are defined in `observability/prometheus/alerts.yml` and evaluated by Prometheus. For dashboard-embedded annotations (not alerting rules), use:

```json
{
  "alert": {
    "name": "High Agent Error Rate",
    "conditions": [{
      "evaluator": {"params": [5], "type": "gt"},
      "operator": {"type": "and"},
      "query": {"params": ["A", "5m", "now"]},
      "reducer": {"type": "avg"},
      "type": "query"
    }],
    "executionErrorState": "alerting",
    "for": "5m",
    "frequency": "1m",
    "message": "Agent error rate exceeds 5% — check Loki logs",
    "noDataState": "no_data"
  }
}
```

Existing alert rules to be aware of (from `alerts.yml`):
- `ASRLatencyHigh` — p95 > 2s for 2m
- `DatabaseWriteLatencyHigh` — p95 > 50ms for 2m
- `ServiceUptimeLow` — any `registry-api` or `asr-service` target down > 1m
- `HighErrorRate` — `asr_errors_total` or `registry_errors_total` rate > 0.1/s
- `DatabaseConnectionFailure` — `registry_db_errors_total` rate > 0 for 1m

---

## Step 8 — Deployment

1. Write the dashboard JSON to `observability/grafana/provisioning/dashboards/json/<name>.json`
2. Grafana detects the file within 10 seconds (no restart needed)
3. Verify at http://localhost:3001 — navigate to Dashboards and find the new entry
4. If the dashboard does not appear, check Grafana logs:
   ```bash
   docker logs dhg-grafana --tail 50
   ```
5. Validate all panel queries return data by opening each panel in edit mode and running the query manually

### Common Deployment Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Dashboard not appearing | JSON syntax error | Run `python3 -m json.tool <file>.json` to validate |
| "No data" on Prometheus panels | Metric does not exist yet | Verify metric name with `curl http://localhost:9090/api/v1/label/__name__/values` |
| "No data" on Loki panels | Container label mismatch | Check available labels: `curl http://localhost:3100/loki/api/v1/labels` |
| Duplicate UID error | uid clash with existing dashboard | Choose a unique uid and verify against existing files |
| Panel overlaps | gridPos x+w > 24 | Grafana grid is 24 columns wide — all panels in a row must sum to ≤ 24 |

---

## Step 9 — Best Practices

1. Every dashboard needs a **title row panel** separating logical sections (`"type": "row"`)
2. Set `"refresh": "30s"` on operational dashboards, `"1m"` for historical ones
3. Set default time range to `"from": "now-6h"` for operational, `"now-24h"` for trend dashboards
4. Add `"description"` to every panel explaining what it measures and what action to take if it fires
5. Use `"unit"` in `fieldConfig.defaults` — common values: `reqps`, `percentunit`, `s`, `ms`, `bytes`, `short`
6. Assign `"color": "fixed"` overrides using DHG brand colours where colour carries meaning:
   - Healthy / normal: `#32374A` (Graphite)
   - Warning: `#F77E2D` (Orange)
   - Critical / error: `#663399` (Purple) or Grafana red (`red`)
7. Group all DHG dashboards under the same folder by setting `folder: 'DHG AI Factory'` in `dashboards.yml` if you add a second provider block
8. Never hardcode instance addresses in queries — use label selectors (`job`, `name`, variables)
9. After adding a metric to agent code, add its scrape job to `observability/prometheus/prometheus.yml` and reload Prometheus:
   ```bash
   curl -X POST http://localhost:9090/-/reload
   ```
10. Test every dashboard with the time range set to "Last 5 minutes" to confirm live data flows correctly

---

## Related Files

- `observability/grafana/provisioning/dashboards/json/dhg-core-golden.json` — reference dashboard
- `observability/grafana/provisioning/dashboards/json/docker-overview.json` — container metrics reference
- `observability/prometheus/prometheus.yml` — scrape job definitions
- `observability/prometheus/alerts.yml` — existing SLO alert rules
- `observability/grafana/provisioning/datasources/prometheus.yml` — Prometheus datasource config
- `observability/grafana/provisioning/datasources/loki.yml` — Loki datasource config
- `docker-compose.override.yml` — Grafana, Prometheus, Loki, cAdvisor, postgres-exporter service definitions
