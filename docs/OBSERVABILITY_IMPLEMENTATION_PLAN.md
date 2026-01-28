# Observability Stack Implementation Plan

**Created:** 2026-01-28  
**Objective:** Deploy complete observability stack for DHG AI Factory  
**Execution:** Autonomous by Antigravity

---

## Scope

Deploy and configure:
- **Prometheus** — Metrics collection
- **Grafana** — Dashboards and visualization  
- **Loki** — Log aggregation
- **Promtail** — Log shipping
- **Alertmanager** — Alert routing

---

## Phase 1: Deploy Core Stack (Est. 30 min)

### 1.1 Create Docker Compose File
- [ ] Create `observability/docker-compose.yml`
- [ ] Define services: prometheus, grafana, loki, promtail, alertmanager
- [ ] Use existing network `dhgaifactory35_dhg-network`
- [ ] Mount existing config files from `observability/` subdirs

### 1.2 Start Core Services
- [ ] Run `docker compose up -d`
- [ ] Verify health: prometheus (:9090), grafana (:3001), loki (:3100)

---

## Phase 2: Configure Prometheus Targets (Est. 20 min)

### 2.1 Update prometheus.yml
Add missing scrape targets:
- [ ] Registry API (`dhg-registry-api:8000`)
- [ ] RAGFlow (`docker-ragflow-cpu-1`)  
- [ ] PostgreSQL exporter (deploy and add)
- [ ] MySQL exporter (for RAGFlow MySQL)
- [ ] Redis exporter

### 2.2 Deploy Database Exporters
- [ ] Deploy postgres_exporter for dhg-registry-db
- [ ] Deploy mysqld_exporter for docker-mysql-1
- [ ] Deploy redis_exporter for docker-redis-1

---

## Phase 3: Configure Loki + Promtail (Est. 15 min)

### 3.1 Create promtail-config.yml
- [ ] Configure Docker log scraping
- [ ] Add labels for service discovery
- [ ] Target containers: registry-api, ragflow, transcribe, etc.

### 3.2 Verify Log Ingestion
- [ ] Check Loki targets in Grafana
- [ ] Query logs via Explore panel

---

## Phase 4: Grafana Dashboards (Est. 20 min)

### 4.1 Configure Data Sources
- [ ] Add Prometheus data source
- [ ] Add Loki data source

### 4.2 Import/Create Dashboards
- [ ] Registry API metrics dashboard
- [ ] Container metrics (cAdvisor)
- [ ] Log viewer (Loki)
- [ ] System overview

---

## Phase 5: Alerting (Est. 15 min)

### 5.1 Configure Alertmanager
- [ ] Create alertmanager.yml with Slack integration
- [ ] Route critical alerts to Slack channel

### 5.2 Test Alert Pipeline
- [ ] Trigger test alert
- [ ] Verify Slack notification

---

## Ports

| Service | Port | Purpose |
|---------|------|---------|
| Prometheus | 9090 | Metrics UI |
| Grafana | 3001 | Dashboards |
| Loki | 3100 | Log API |
| Alertmanager | 9093 | Alert UI |

---

## Files to Create

1. `observability/docker-compose.yml` — Main compose file
2. `observability/prometheus/prometheus.yml` — Update existing
3. `observability/promtail/promtail-config.yml` — New
4. `observability/alertmanager/alertmanager.yml` — New

---

## Verification Checklist

- [ ] Prometheus targets all UP
- [ ] Grafana accessible at :3001
- [ ] Logs visible in Loki via Grafana
- [ ] Test alert fires and reaches Slack
- [ ] All containers healthy

---

## Rollback Plan

If issues arise:
```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/observability
docker compose down
```

Existing services unaffected — observability stack is isolated.
