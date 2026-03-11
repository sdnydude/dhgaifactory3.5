# Observability Stack — Task Plan

**Project:** DHG AI Factory Observability
**Started:** Feb 18, 2026
**Goal:** Complete Prometheus exporters + Grafana dashboards

---

## Phase 1: Fix Broken Prometheus Targets <!-- status: in_progress -->

- [ ] Remove dead `asr-service` scrape job from prometheus.yml <!-- id: 1 -->
- [ ] Add `node-exporter` container to docker-compose.override.yml <!-- id: 2 -->
- [ ] Add `cadvisor` container to docker-compose.override.yml <!-- id: 3 -->
- [ ] Add `postgres-exporter` container for registry-db <!-- id: 4 -->
- [ ] Update prometheus.yml to add postgres scrape job <!-- id: 5 -->
- [ ] Restart prometheus to pick up config changes <!-- id: 6 -->
- [ ] Verify all targets UP in Prometheus UI <!-- id: 7 -->

## Phase 2: Fix Grafana Dashboard Provisioning <!-- status: not_started -->

- [ ] Wire dashboard JSON files to Grafana volume mount <!-- id: 8 -->
- [ ] Add Loki datasource to Grafana provisioning <!-- id: 9 -->
- [ ] Verify existing dashboards load (dhg-core-golden.json, docker-overview.json) <!-- id: 10 -->
- [ ] Create DHG Agent Overview dashboard (LangGraph + agent health) <!-- id: 11 -->
- [ ] Create PostgreSQL dashboard (registry-db metrics) <!-- id: 12 -->
- [ ] Restart Grafana to reload provisioning <!-- id: 13 -->

## Phase 3: Commit and Verify <!-- status: not_started -->

- [ ] Commit all observability config changes <!-- id: 14 -->
- [ ] Push to GitHub <!-- id: 15 -->
- [ ] Update TODO.md to mark tasks complete <!-- id: 16 -->
