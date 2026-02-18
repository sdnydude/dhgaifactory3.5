# Observability Stack — Progress Log

## Session: Feb 18, 2026 (11:00–11:15 EST)

### Work Done
- Ran full Prometheus target audit — found 3 DOWN targets (asr-service, cadvisor, node-exporter)
- Identified root cause: containers referenced in prometheus.yml but never added to docker-compose
- Identified Grafana dashboard mount bug: JSON files not mounted into container
- Created task_plan.md and findings.md
- Modified docker-compose.override.yml: added node-exporter, cadvisor, postgres-exporter; fixed Grafana dashboard volume mount
- Modified prometheus.yml: removed dead asr-service job, activated postgres scrape, fixed node-exporter target to use host gateway IP (172.18.0.1:9100)
- Created loki.yml datasource for Grafana provisioning

### Files Modified
- `docker-compose.override.yml` — 3 new services + Grafana volume fix
- `observability/prometheus/prometheus.yml` — removed asr-service, added postgres, fixed node-exporter IP
- `observability/grafana/provisioning/datasources/loki.yml` — new file

### Next Steps
- Start new containers: `docker compose -f docker-compose.override.yml up -d node-exporter cadvisor postgres-exporter`
- Restart Grafana and Prometheus to pick up config changes
- Verify all Prometheus targets are UP
- Verify Grafana dashboards load
- Commit and push
