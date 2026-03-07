# Prometheus Configuration

Configure, validate, and troubleshoot Prometheus monitoring for the DHG AI Factory stack.

Use this command when: setting up or modifying scrape targets, writing recording rules, writing alert rules, diagnosing missing metrics, or verifying Prometheus can reach all five monitored services.

**Usage:** `/prometheus-configuration $ARGUMENTS`

Where `$ARGUMENTS` describes the specific task, for example:
- `add scrape target for new-service on port 8080`
- `add alert for high memory usage`
- `validate current config`
- `debug cadvisor not scraping`

## Capabilities

**What this command does:** Edits, validates, and reloads `prometheus.yml` and `alerts.yml` for the DHG AI Factory Prometheus instance, covering the five established scrape targets, recording rules, and SLO alert thresholds.

**Use it when you need to:**
- Add a new scrape target for a service on `dhgaifactory35_dhg-network` and verify it goes UP
- Write recording rules for HTTP request rate, error rate, or P95 latency to speed up Grafana panels
- Add or tune an alert rule with correct PromQL, `for` duration, severity, and runbook annotation
- Diagnose why cAdvisor, node-exporter, or postgres-exporter shows DOWN in the Prometheus targets UI
- Validate config with `promtool check` and hot-reload via the `/-/reload` HTTP endpoint

**Example invocations:**
- `/project:prometheus-configuration add scrape target for the new dhg-langgraph-api on port 8080`
- `/project:prometheus-configuration add alert for disk usage above 90% with a 5-minute for clause`
- `/project:prometheus-configuration debug why cadvisor is not scraping and fix the config`

---

## Project Context

**Config file:** `/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/observability/prometheus/prometheus.yml`
**Alert rules file:** `/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/observability/prometheus/alerts.yml`
**Prometheus UI:** `http://localhost:9090`
**Docker network:** `dhgaifactory35_dhg-network`
**Container name prefix:** `dhg-`

### Five Scrape Targets

| Job | Container / Address | Port | Interval |
|-----|---------------------|------|----------|
| `prometheus` | `localhost` | 9090 | 15s (global) |
| `registry-api` | `registry-api` | 8000 | 10s |
| `postgres` | `postgres-exporter` | 9187 | 30s |
| `node-exporter` | `172.18.0.1` (host network gateway) | 9100 | 15s |
| `cadvisor` | `cadvisor` | 8080 | 15s |

Note: `node-exporter` runs on the host network, not inside `dhgaifactory35_dhg-network`. It is reached via the Docker bridge gateway IP `172.18.0.1`. Do not change this to a container hostname.

Note: `registry-api` is reachable inside the network as `registry-api:8000`, NOT via `dhg-registry-api:8500`. The environment variable `AI_FACTORY_REGISTRY_URL` points to `http://dhg-registry-api:8000`.

---

## Step 1: Read Before Editing

Always read the current config before making any changes.

```bash
cat /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/observability/prometheus/prometheus.yml
cat /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/observability/prometheus/alerts.yml
```

State what you are changing and why before writing any edits.

---

## Step 2: prometheus.yml Structure

The canonical structure for this project:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'dhg-ai-factory'
    environment: 'local'

rule_files:
  - 'alerts.yml'

scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
        labels:
          service: 'prometheus'

  # Registry API service
  - job_name: 'registry-api'
    static_configs:
      - targets: ['registry-api:8000']
        labels:
          service: 'registry-api'
    metrics_path: '/metrics'
    scrape_interval: 10s

  # PostgreSQL metrics via postgres-exporter
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
        labels:
          service: 'registry-db'
    scrape_interval: 30s

  # Node Exporter — host network, reachable via dhg-network gateway
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['172.18.0.1:9100']
        labels:
          service: 'node-exporter'
    scrape_interval: 15s

  # cAdvisor (container metrics)
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
        labels:
          service: 'cadvisor'
    scrape_interval: 15s
```

---

## Step 3: Adding a New Scrape Target

When `$ARGUMENTS` requests a new target, append a new `scrape_configs` entry following this pattern:

```yaml
  - job_name: '<service-name>'
    static_configs:
      - targets: ['<container-name>:<port>']
        labels:
          service: '<service-name>'
    metrics_path: '/metrics'
    scrape_interval: 15s
```

Rules for new targets:
- `job_name` must be lowercase with hyphens, matching the Docker service name
- Use the Docker service name (not the container name with `dhg-` prefix) as the hostname within `dhgaifactory35_dhg-network`
- `metrics_path` defaults to `/metrics`; only specify if the service uses a different path
- Do not invent ports — verify the actual exposed port from `docker-compose.yml`

---

## Step 4: Recording Rules

Recording rules go in a dedicated file, referenced from `rule_files`. Create `/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/observability/prometheus/recording_rules.yml` if it does not exist, then add it to `rule_files`.

Template for DHG AI Factory recording rules:

```yaml
groups:
  - name: api_metrics
    interval: 15s
    rules:
      # HTTP request rate per service
      - record: job:http_requests:rate5m
        expr: sum by (job) (rate(http_requests_total[5m]))

      # Error rate percentage
      - record: job:http_requests_errors:rate5m
        expr: sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))

      - record: job:http_requests_error_rate:percentage
        expr: |
          (job:http_requests_errors:rate5m / job:http_requests:rate5m) * 100

      # P95 latency
      - record: job:http_request_duration:p95
        expr: |
          histogram_quantile(0.95,
            sum by (job, le) (rate(http_request_duration_seconds_bucket[5m]))
          )

  - name: resource_metrics
    interval: 30s
    rules:
      # CPU utilization percentage
      - record: instance:node_cpu:utilization
        expr: |
          100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

      # Memory utilization percentage
      - record: instance:node_memory:utilization
        expr: |
          100 - ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100)

      # Disk usage percentage
      - record: instance:node_disk:utilization
        expr: |
          100 - ((node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100)
```

---

## Step 5: Alert Rules

Alert rules live in `/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/observability/prometheus/alerts.yml`.

The existing DHG alert groups are:
- `dhg_slo_alerts` — SLO-based alerts for ASR latency, database write latency, service uptime, and high error rates

When adding a new alert, append to the existing group that fits best, or create a new named group. Do not delete existing alerts.

Template for a new alert:

```yaml
      - alert: <AlertName>
        expr: <promql_expression>
        for: <duration>
        labels:
          severity: critical|warning|info
          slo: <optional_slo_name>
        annotations:
          summary: "<short description with {{ $labels.instance }} if useful>"
          description: "<detail with {{ $value }} showing the measured value>"
```

Existing SLO thresholds for reference:
- ASR p95 latency SLO: < 2 seconds
- Database write p95 latency SLO: < 50ms
- Service uptime SLO: > 99.5% (`up{job=~"registry-api|asr-service"} == 0` fires after 1m)

Standard infrastructure alert thresholds:
- CPU: warning at 80%, critical at 95%
- Memory: warning at 85%, critical at 95%
- Disk: critical at 90%

```yaml
  - name: infrastructure_alerts
    interval: 1m
    rules:
      - alert: HighCPUUsage
        expr: instance:node_cpu:utilization > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is {{ $value }}%"

      - alert: HighMemoryUsage
        expr: instance:node_memory:utilization > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage is {{ $value }}%"

      - alert: DiskSpaceLow
        expr: instance:node_disk:utilization > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Low disk space on {{ $labels.instance }}"
          description: "Disk usage is {{ $value }}%"
```

---

## Step 6: Validate Configuration

After every edit, validate before reloading. Run inside the Prometheus container:

```bash
docker exec dhg-prometheus promtool check config /etc/prometheus/prometheus.yml
docker exec dhg-prometheus promtool check rules /etc/prometheus/alerts.yml
```

If `promtool` is not available as a separate binary:

```bash
docker exec dhg-prometheus /bin/promtool check config /etc/prometheus/prometheus.yml
```

Expected output on success:
```
Checking /etc/prometheus/prometheus.yml
  SUCCESS: /etc/prometheus/prometheus.yml is valid prometheus config file syntax
```

---

## Step 7: Reload Prometheus

Prometheus supports hot-reload via SIGHUP or the reload endpoint. Use the HTTP endpoint — it is safer:

```bash
curl -X POST http://localhost:9090/-/reload
```

Verify the reload succeeded:

```bash
curl -s http://localhost:9090/api/v1/status/config | python3 -m json.tool | head -30
```

If the container needs a full restart:

```bash
docker restart dhg-prometheus
docker logs dhg-prometheus --tail 20
```

---

## Step 8: Verify Targets Are Up

Check the Prometheus targets API immediately after reload:

```bash
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool
```

All five targets should show `"health": "up"`. A target in `"health": "down"` means Prometheus cannot reach it.

Simplified check showing only health status per job:

```bash
curl -s 'http://localhost:9090/api/v1/targets' \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
for t in data['data']['activeTargets']:
    print(t['labels'].get('job','?'), '->', t['health'], t.get('lastError',''))
"
```

Instant query to confirm all five jobs are up:

```bash
curl -s 'http://localhost:9090/api/v1/query?query=up' | python3 -m json.tool
```

---

## Troubleshooting

### Target shows "down" — connection refused

The container is not running or is not on `dhgaifactory35_dhg-network`.

```bash
docker ps --filter name=dhg- --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker network inspect dhgaifactory35_dhg-network --format '{{range .Containers}}{{.Name}} {{end}}'
```

### node-exporter target is down

`node-exporter` runs on the host network. Verify the gateway IP is still `172.18.0.1`:

```bash
docker network inspect dhgaifactory35_dhg-network --format '{{.IPAM.Config}}'
```

If the gateway IP has changed, update `172.18.0.1` in `prometheus.yml` to match.

Also verify node-exporter is running on the host:

```bash
curl -s http://172.18.0.1:9100/metrics | head -5
```

### cadvisor target is down

Check the cadvisor container is running and using the correct Docker API version:

```bash
docker logs dhg-cadvisor --tail 20
```

cadvisor must be at v0.51.0 or higher for Docker API 1.44+ compatibility.

### Configuration reload silently fails

Check Prometheus logs immediately after the reload call:

```bash
docker logs dhg-prometheus --since 30s
```

YAML errors in `prometheus.yml` or `alerts.yml` will appear here. Prometheus will continue running with the previous valid config if a reload fails.

### Checking scrape configuration in effect

```bash
curl http://localhost:9090/api/v1/status/config
```

### Testing a PromQL query

```bash
curl -G 'http://localhost:9090/api/v1/query' --data-urlencode 'query=up'
curl -G 'http://localhost:9090/api/v1/query' --data-urlencode 'query=rate(http_requests_total[5m])'
```

---

## Docker Compose Service Discovery Pattern

When adding observability exporters for new services via Docker Compose, follow this pattern. The exporter runs as a sidecar on the same network and Prometheus scrapes it by container hostname.

```yaml
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: dhg-postgres-exporter
    environment:
      DATA_SOURCE_NAME: "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@registry-db:5432/${POSTGRES_DB}?sslmode=disable"
    networks:
      - dhg-network
    restart: unless-stopped
```

Then add the corresponding scrape job to `prometheus.yml` using the service name (`postgres-exporter`) as the target hostname, not the container name (`dhg-postgres-exporter`).

---

## Prometheus Architecture in This Stack

```
┌─────────────────────────────────────────────────────────┐
│              dhgaifactory35_dhg-network                 │
│                                                         │
│  registry-api:8000  ──────────────────────────────┐    │
│  postgres-exporter:9187  ─────────────────────┐   │    │
│  cadvisor:8080  ──────────────────────────┐   │   │    │
│  172.18.0.1:9100 (host node-exporter)  ─┐ │   │   │    │
│                                         │ │   │   │    │
│  ┌─────────────────────────────────┐    │ │   │   │    │
│  │  dhg-prometheus (port 9090)     │◄───┘ ┘   ┘   ┘    │
│  │  scrapes all 5 targets every    │                   │
│  │  10-30s per job config          │                   │
│  └──────────────┬──────────────────┘                   │
│                 │                                       │
│  ┌──────────────▼──────────────────┐                   │
│  │  dhg-grafana (port 3000)        │                   │
│  │  datasource: prometheus:9090    │                   │
│  └─────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

---

## Best Practices for This Project

1. Use consistent `job_name` values that match Docker service names (without the `dhg-` container prefix)
2. Always add a `service` label to every static target for Grafana filtering
3. Set per-job `scrape_interval` only when it differs from the 15s global — do not repeat the global default
4. Use recording rules for any PromQL expression queried in more than one Grafana panel
5. Alert `for:` duration must be at least 1 minute — do not fire on transient single-scrape failures
6. Validate with `promtool` and reload via HTTP before declaring the work done
7. All container names use `dhg-` prefix; Docker service names (used as hostnames) do not
8. Never use port 8500 for the registry API — use port 8000

---

## Definition of Done

A Prometheus configuration change is complete when:
- `promtool check config` returns SUCCESS with no warnings
- `promtool check rules` returns SUCCESS for all rule files
- `curl http://localhost:9090/-/reload` returns 200
- `curl http://localhost:9090/api/v1/targets` shows all intended targets with `"health": "up"`
- No error lines appear in `docker logs dhg-prometheus --since 60s`
