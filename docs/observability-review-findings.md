# Observability Stack Review Findings

**Date:** 2026-01-27  
**Context:** Pre-implementation review to avoid duplication and bloat

---

## Discovery: Existing Infrastructure on 10.0.0.251

### Already Present (Configs Only — NOT Running)

The server has an `/observability/` directory with partially configured but **undeployed** monitoring:

| Component | Config Files | Status |
|-----------|--------------|--------|
| Prometheus | `prometheus.yml`, `alerts.yml` | Config exists, container not running |
| Loki | `loki-config.yml` | Config exists, container not running |
| Grafana | Dashboards + provisioning | Config exists, container not running |

**Docker images already pulled:**
- `prom/prometheus:latest`
- `grafana/grafana:10.1.0`, `latest`
- `grafana/loki:2.9.0`, `latest`
- `grafana/promtail:2.9.0`

### Existing Prometheus Config Analysis

The current `prometheus.yml` already defines:
- Self-monitoring (`localhost:9090`)
- `registry-api:8000/metrics`
- `asr-service:8000/metrics` 
- `node-exporter:9100`
- `cadvisor:8080`

**Missing from current config:**
- PostgreSQL exporter
- MySQL exporter
- Redis exporter
- MongoDB exporter
- Elasticsearch exporter
- GPU metrics (dcgm-exporter)
- Alertmanager integration

### Existing Alerts Analysis

`alerts.yml` has 7 alert rules for:
- ASR latency SLO
- Database write latency SLO
- Service uptime
- Prometheus target missing
- GPU unavailability
- High error rate
- Database connection failures

---

## What the Original Plan Proposed

The Phase 1 plan listed 12+ containers:
- Prometheus, Grafana, Loki, Promtail, Alertmanager
- node_exporter, dcgm-exporter, cAdvisor
- postgres_exporter, mysqld_exporter, redis_exporter
- mongodb_exporter, elasticsearch_exporter

---

## Recommendations: Build on Existing, Don't Recreate

### Use As-Is
- `prometheus.yml` structure (add missing exporters)
- `loki-config.yml` (retention already set to 31 days)
- Grafana provisioning setup
- Existing alert rules

### Add/Enhance
1. **Database exporters** — All 5 need to be added to compose and prometheus.yml
2. **GPU monitoring** — dcgm-exporter not configured
3. **Alertmanager** — Reference exists but commented out
4. **Promtail** — Config not found (needs creation)
5. **Docker Compose** — No compose file exists; must create to deploy everything

### Discovery Still Needed

Before finalizing compose, need to run these commands on .251:

```bash
# Docker network topology
docker network ls
docker inspect dhg-registry-db --format='{{json .NetworkSettings.Networks}}' | jq
docker inspect docker-mysql-1 --format='{{json .NetworkSettings.Networks}}' | jq

# Verify ports
docker port docker-es01-1

# NVIDIA status
nvidia-smi --query-gpu=driver_version --format=csv,noheader
nvidia-ctk --version
```

---

## Verdict: No Bloat Risk

The original plan from the previous conversation is **not duplicating** anything. The configs exist but nothing is deployed. The recommendation is:

1. **Reuse existing configs** in `observability/`
2. **Create docker-compose.observability.yml** to deploy the stack
3. **Extend prometheus.yml** with missing exporters
4. **Create promtail-config.yml**
5. **Run discovery commands** before finalizing network config

This is enhancement, not duplication.
