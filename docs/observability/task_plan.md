# Observability Stack Implementation

**Goal:** Implement production-ready observability for 17+ agent architecture

**Status:** Phase 1 Complete

---

## Phase 1: Infrastructure Setup ✅ COMPLETE
- [x] Add Prometheus service to docker-compose.override.yml <!-- id: 1 -->
- [x] Add Loki service to docker-compose.override.yml <!-- id: 2 -->
- [x] Add Grafana service to docker-compose.override.yml <!-- id: 3 -->
- [x] Create Docker volumes for persistence <!-- id: 4 -->
- [x] Pull container images <!-- id: 5 -->
- [x] Fix port conflict (3000 → 3001 for Grafana) <!-- id: 6 -->
- [x] Start all containers <!-- id: 7 -->
- [x] Verify containers running with `docker ps` <!-- id: 8 -->

---

## Phase 2: Prometheus Configuration
### 2.1 Verify Existing Config
- [ ] Review `observability/prometheus/prometheus.yml` <!-- id: 10 -->
- [ ] Verify scrape_interval settings (currently 15s) <!-- id: 11 -->
- [ ] Check existing job definitions <!-- id: 12 -->

### 2.2 Add Scrape Targets for All Agents
- [ ] Add dhg-medical-llm:8002/health target <!-- id: 13 -->
- [ ] Add dhg-research:8003/health target <!-- id: 14 -->
- [ ] Add dhg-curriculum:8004/health target <!-- id: 15 -->
- [ ] Add dhg-outcomes:8005/health target <!-- id: 16 -->
- [ ] Add dhg-competitor-intel:8006/health target <!-- id: 17 -->
- [ ] Add dhg-qa-compliance:8007/health target <!-- id: 18 -->
- [ ] Add dhg-visuals-media:8008/health target <!-- id: 19 -->
- [ ] Add dhg-session-logger:8009/health target <!-- id: 20 -->
- [ ] Add dhg-registry-api:8011/metrics target <!-- id: 21 -->
- [ ] Add dhg-logo-maker:8012/health target <!-- id: 22 -->

### 2.3 Add Infrastructure Exporters
- [ ] Deploy node-exporter container for host metrics <!-- id: 23 -->
- [ ] Configure node-exporter in prometheus.yml <!-- id: 24 -->
- [ ] Deploy cAdvisor container for container metrics <!-- id: 25 -->
- [ ] Configure cAdvisor in prometheus.yml <!-- id: 26 -->

### 2.4 Verification
- [ ] Access Prometheus UI at http://10.0.0.251:9090 <!-- id: 27 -->
- [ ] Check Targets page shows all endpoints UP <!-- id: 28 -->
- [ ] Run test query: `up{job="registry-api"}` <!-- id: 29 -->
- [ ] Verify metrics are being scraped <!-- id: 30 -->

---

## Phase 3: Loki Log Aggregation
### 3.1 Docker Logging Driver
- [ ] Install Loki Docker logging driver plugin <!-- id: 31 -->
- [ ] Configure default logging driver in Docker daemon.json <!-- id: 32 -->
- [ ] Restart Docker daemon to apply changes <!-- id: 33 -->

### 3.2 Container Log Configuration
- [ ] Update docker-compose.yml with Loki log driver for agents <!-- id: 34 -->
- [ ] Configure log labels (container_name, service) <!-- id: 35 -->
- [ ] Set log retention and batch settings <!-- id: 36 -->

### 3.3 Verification
- [ ] Restart a test container with new logging <!-- id: 37 -->
- [ ] Query Loki API: `curl http://localhost:3100/loki/api/v1/labels` <!-- id: 38 -->
- [ ] Verify logs appear in Loki <!-- id: 39 -->

---

## Phase 4: Grafana Dashboards
### 4.1 Datasource Configuration
- [ ] Login to Grafana at http://10.0.0.251:3001 <!-- id: 40 -->
- [ ] Add Prometheus datasource (http://prometheus:9090) <!-- id: 41 -->
- [ ] Add Loki datasource (http://loki:3100) <!-- id: 42 -->
- [ ] Test both datasource connections <!-- id: 43 -->

### 4.2 Agent Health Dashboard
- [ ] Create new dashboard "DHG Agent Health" <!-- id: 44 -->
- [ ] Add panel: Agent Status (up/down for each agent) <!-- id: 45 -->
- [ ] Add panel: Agent Response Times (histogram) <!-- id: 46 -->
- [ ] Add panel: Request Counts (by agent) <!-- id: 47 -->
- [ ] Add panel: Error Rate (by agent) <!-- id: 48 -->

### 4.3 Infrastructure Dashboard
- [ ] Create dashboard "DHG Infrastructure" <!-- id: 49 -->
- [ ] Add panel: CPU Usage (from node-exporter) <!-- id: 50 -->
- [ ] Add panel: Memory Usage <!-- id: 51 -->
- [ ] Add panel: Disk I/O <!-- id: 52 -->
- [ ] Add panel: Network Traffic <!-- id: 53 -->
- [ ] Add panel: GPU Utilization (if nvidia-exporter available) <!-- id: 54 -->

### 4.4 Container Metrics Dashboard
- [ ] Create dashboard "DHG Containers" <!-- id: 55 -->
- [ ] Add panel: Container CPU by name <!-- id: 56 -->
- [ ] Add panel: Container Memory by name <!-- id: 57 -->
- [ ] Add panel: Container Network I/O <!-- id: 58 -->
- [ ] Add panel: Container Restart Count <!-- id: 59 -->

### 4.5 Logs Dashboard
- [ ] Create dashboard "DHG Logs Explorer" <!-- id: 60 -->
- [ ] Add panel: Log Volume by Container <!-- id: 61 -->
- [ ] Add panel: Error Log Stream (filtered) <!-- id: 62 -->
- [ ] Add panel: Full Log Stream (with filters) <!-- id: 63 -->
- [ ] Add saved queries for common searches <!-- id: 64 -->

---

## Phase 5: Agent Integration
### 5.1 Metrics Endpoints
- [ ] Audit which agents have /metrics endpoint <!-- id: 65 -->
- [ ] Add prometheus_client to agents missing it <!-- id: 66 -->
- [ ] Standardize metrics: request_count, request_latency, error_count <!-- id: 67 -->
- [ ] Add custom business metrics per agent <!-- id: 68 -->

### 5.2 Structured Logging
- [ ] Define JSON log schema (timestamp, level, service, message, trace_id) <!-- id: 69 -->
- [ ] Update logging config in each agent <!-- id: 70 -->
- [ ] Add correlation/trace IDs to requests <!-- id: 71 -->
- [ ] Test log parsing in Loki <!-- id: 72 -->

### 5.3 Health Check Standardization
- [ ] Define health check response schema <!-- id: 73 -->
- [ ] Update all agents to return consistent format <!-- id: 74 -->
- [ ] Add dependency health (DB, LLM, etc.) to health checks <!-- id: 75 -->

---

## Phase 6: Alerting (Optional)
### 6.1 Alertmanager Setup
- [ ] Add Alertmanager container to docker-compose <!-- id: 76 -->
- [ ] Configure alertmanager.yml <!-- id: 77 -->
- [ ] Link Prometheus to Alertmanager <!-- id: 78 -->

### 6.2 Alert Rules
- [ ] Create alerts.yml in Prometheus config <!-- id: 79 -->
- [ ] Alert: Agent Down (up == 0 for 1m) <!-- id: 80 -->
- [ ] Alert: High Latency (p99 > 5s) <!-- id: 81 -->
- [ ] Alert: High Error Rate (> 5% errors) <!-- id: 82 -->
- [ ] Alert: Disk Space Low (< 10% free) <!-- id: 83 -->

### 6.3 Notifications
- [ ] Configure email receiver <!-- id: 84 -->
- [ ] Configure Slack webhook (optional) <!-- id: 85 -->
- [ ] Test alert firing and notification <!-- id: 86 -->

---

## Phase 7: LibreNMS Network Monitoring
### 7.1 LibreNMS Deployment
- [ ] Add LibreNMS to docker-compose.override.yml <!-- id: 87 -->
- [ ] Create MySQL/MariaDB container for LibreNMS <!-- id: 88 -->
- [ ] Configure persistent volumes for data <!-- id: 89 -->
- [ ] Start LibreNMS container <!-- id: 90 -->
- [ ] Access LibreNMS UI and create admin user <!-- id: 91 -->

### 7.2 SNMP Configuration on Devices
- [ ] Enable SNMP on Windows machines (Add-WindowsFeature SNMP) <!-- id: 92 -->
- [ ] Enable SNMP on macOS (System Preferences → Sharing) <!-- id: 93 -->
- [ ] Install snmpd on Linux servers <!-- id: 94 -->
- [ ] Configure SNMP community string on all devices <!-- id: 95 -->
- [ ] Document SNMP settings (community string, version) <!-- id: 96 -->

### 7.3 Device Discovery
- [ ] Add network range for auto-discovery <!-- id: 97 -->
- [ ] Run initial device discovery scan <!-- id: 98 -->
- [ ] Verify all devices detected and polling <!-- id: 99 -->
- [ ] Configure device groups/locations <!-- id: 100 -->

### 7.4 Alerting
- [ ] Configure alert rules for device down <!-- id: 101 -->
- [ ] Configure alert rules for high CPU/memory <!-- id: 102 -->
- [ ] Set up email/Slack notifications <!-- id: 103 -->

**Resources:**
- Website: https://www.librenms.org
- Docker Install: https://docs.librenms.org/Installation/Docker/
- GitHub: https://github.com/librenms/librenms

---

## Current Access

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://10.0.0.251:3001 | admin / admin123 |
| Prometheus | http://10.0.0.251:9090 | N/A |
| Loki | http://10.0.0.251:3100 | API only |

---

## Errors Encountered

| Error | Phase | Resolution |
|-------|-------|------------|
| Port 3000 conflict | 1 | Changed Grafana to 3001 |

---

## Estimated Effort

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1 | 8 | ✅ Complete |
| Phase 2 | 21 | 1-2 hours |
| Phase 3 | 9 | 1 hour |
| Phase 4 | 25 | 2-3 hours |
| Phase 5 | 11 | 2-3 hours |
| Phase 6 | 11 | 1-2 hours |
| Phase 7 | 17 | 2-3 hours |
| **Total** | **102** | **9-14 hours** |
