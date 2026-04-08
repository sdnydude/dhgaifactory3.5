# DHG AI Factory — Observability Runbook

Operational procedures for the monitoring stack.

---

## Stack Overview

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| Prometheus | dhg-prometheus | 9090 | Metrics collection |
| Grafana | dhg-grafana | 3001 | Dashboards |
| Loki | dhg-loki | 3100 | Log aggregation |
| Tempo | dhg-tempo | 3200 | Distributed tracing |
| Promtail | dhg-promtail | — | Log shipping (Docker logs) |
| Alertmanager | dhg-alertmanager | 9093 | Alert routing |
| Node Exporter | dhg-node-exporter | 9100 | Host metrics |
| cAdvisor | dhg-cadvisor | 8080 | Container metrics |
| Postgres Exporter | dhg-postgres-exporter | 9187 | Registry-db metrics |

All services defined in `docker-compose.override.yml`, configs in `observability/`.

---

## Health Checks

```bash
# All services healthy?
docker compose ps | grep -E "dhg-(prometheus|grafana|loki|tempo|promtail|alertmanager|cadvisor|node-exporter|postgres-exporter)"

# Individual checks
curl -s http://localhost:9090/-/healthy        # Prometheus
curl -s http://localhost:3001/api/health        # Grafana
curl -s http://localhost:3100/ready             # Loki
curl -s http://localhost:3200/ready             # Tempo
curl -s http://localhost:9093/-/healthy         # Alertmanager
```

---

## Prometheus

**Config:** `observability/prometheus/prometheus.yml`

**Scrape targets (6, all UP as of April 2026):**
- `prometheus` (self, :9090)
- `registry-api` (:8000/metrics)
- `vs-engine` (:8000/metrics)
- `postgres` (postgres-exporter, :9187)
- `node-exporter` (host gateway, :9100)
- `cadvisor` (:8080)

**Check targets:** http://localhost:9090/targets

**Alert rules:** `observability/prometheus/alerts.yml` (7 rules)

---

## Grafana

**URL:** http://localhost:3001 (default admin/admin)

**Datasources (auto-provisioned):**
- Prometheus (http://prometheus:9090)
- Loki (http://loki:3100)
- Tempo (http://tempo:3200) — traces-to-logs linking enabled

**Dashboards (8):** `observability/grafana/provisioning/dashboards/json/`

| Dashboard | File | Purpose |
|-----------|------|---------|
| Core Golden Signals | `dhg-core-golden.json` | CPU, memory, network, disk — the four golden signals |
| Docker Overview | `docker-overview.json` | Per-container resource usage, restart counts |
| Registry API | `dhg-registry-api.json` | Request rate, latency, error rate for FastAPI endpoints |
| PostgreSQL | `dhg-postgresql.json` | Connection pool, query performance, table stats |
| Log Analytics | `dhg-log-analytics.json` | Log volume by container, error rates, pattern search |
| LangGraph Traces | `dhg-langgraph-traces.json` | Tempo trace search by service, duration, status |
| Alerting | `dhg-alerting.json` | Alert state overview, firing/resolved history |
| VS Engine | `vs-engine.json` | Verbalized Sampling metrics (generate, select, latency) |

---

## Loki + Promtail

**Promtail config:** `observability/promtail/promtail-config.yml`
Scrapes Docker container logs. **Important:** Docker Root Dir is `/mnt/4tb/docker`, so the volume mount maps `/mnt/4tb/docker/containers` to `/var/lib/docker/containers` inside the container.

**Loki alerting rules:** `observability/loki/rules/dhg-ai-factory/alerts.yml`

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighErrorRate | >50 error-level log lines across all containers in 5m | warning |
| ContainerErrorSpike | >20 errors from a single container in 5m | warning |
| PostgresFatalError | Any FATAL/PANIC from registry-db | critical |
| NoLogsFromRegistryApi | No logs received from registry-api for 10+ minutes | warning |

**Query logs in Grafana:**
```logql
{container_name="dhg-registry-api"} |= "error"
{container_name=~"dhg-.*"} | json | level="error"
```

---

## Tempo (Tracing)

**Config:** `observability/tempo/tempo-config.yml`

**OTLP receivers:**
- gRPC: `dhg-tempo:4317`
- HTTP: `dhg-tempo:4318`

**Trace retention:** 31 days

LangGraph agents export traces via OpenTelemetry SDK to `dhg-tempo:4317`. Agents also trace via LangSmith (@traceable decorators) for dual visibility.

**Search traces:** Grafana Explore → Tempo datasource → Search by service name `dhg-langgraph-agents`.

---

## Alertmanager

**Config:** `observability/alertmanager/alertmanager.yml`

**Check firing alerts:**
```bash
curl -s http://localhost:9093/api/v2/alerts | python3 -m json.tool
```

**Silence an alert:**
Use Alertmanager UI at http://localhost:9093

---

## Common Troubleshooting

**Prometheus target down:**
1. Check container running: `docker ps | grep <service>`
2. Check metrics endpoint: `curl http://localhost:<port>/metrics`
3. Check Prometheus config for correct target address

**No logs in Loki:**
1. Verify Promtail running: `docker logs dhg-promtail --tail 20`
2. Check Promtail targets: `curl http://localhost:9080/targets`
3. Verify Loki ingestion: `curl http://localhost:3100/loki/api/v1/labels`

**No traces in Tempo:**
1. Verify agent has opentelemetry packages installed
2. Check OTLP endpoint reachable: `curl http://localhost:4318/v1/traces` (should return method not allowed)
3. Check agent logs for OTLP export errors

**Restart observability stack:**
```bash
docker compose restart dhg-prometheus dhg-grafana dhg-loki dhg-tempo dhg-promtail dhg-alertmanager
```
