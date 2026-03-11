# Observability Stack — Findings

**Research Date:** Feb 18, 2026

---

## Current Prometheus Target Status

| Job | Status | Reason |
|---|---|---|
| `prometheus` | ✅ UP | Self-monitoring, works |
| `registry-api` | ✅ UP | Scraping `registry-api:8000/metrics` |
| `asr-service` | ❌ DOWN | Container doesn't exist — DNS lookup fails |
| `cadvisor` | ❌ DOWN | Container doesn't exist — DNS lookup fails |
| `node-exporter` | ❌ DOWN | Container doesn't exist — DNS lookup fails |

**Root cause:** prometheus.yml references containers that were never added to docker-compose.

---

## Grafana Mount Analysis

| Source | Destination |
|---|---|
| `dhgaifactory35_grafana_data` volume | `/var/lib/grafana` |
| `./observability/grafana/provisioning` | `/etc/grafana/provisioning` |

**Problem:** Dashboard JSON files are in `./observability/grafana/dashboards/` on host, but Grafana's dashboard provider config (`dashboards.yml`) points to `/var/lib/grafana/dashboards` inside the container — which is the volume, not the host mount. The JSON files are NOT being loaded.

**Fix:** Either:
- Option A: Add a volume mount `./observability/grafana/dashboards:/var/lib/grafana/dashboards` to docker-compose.override.yml
- Option B: Change `dashboards.yml` path to a provisioning subdirectory that IS mounted

**Chosen fix:** Option A — add volume mount. Simpler, no config change needed.

---

## Existing Dashboard Files

| File | Size | Purpose |
|---|---|---|
| `dhg-core-golden.json` | 15.6KB | Core DHG service metrics |
| `docker-overview.json` | 2.9KB | Docker container overview |

Both exist but are not loading due to the mount issue above.

---

## Loki Datasource

Grafana provisioning only has Prometheus datasource. Loki is running on `:3100` but not provisioned as a Grafana datasource — logs are not queryable from Grafana yet.

---

## Databases to Monitor

| Database | Container | Port | Exporter Needed |
|---|---|---|---|
| `dhg_registry` (PostgreSQL) | `986cbb4003b3_dhg-registry-db` | 5432 | `postgres-exporter` |
| Transcribe DB (PostgreSQL) | `dhg-transcribe-db` | 5433 | Optional |
| Audio DB (pgvector) | `dhg-audio-postgres` | 5434 | Optional |

**Priority:** registry-db only for now (P1). Others are P2.

---

## Docker Network

Prometheus is on `dhg-network`. New exporters must also join `dhg-network` to resolve container hostnames.

---

## Postgres Exporter Config

Standard image: `prometheuscommunity/postgres-exporter`
Connection string: `postgresql://dhg:weenie64@registry-db:5432/dhg_registry?sslmode=disable`
Metrics port: `9187`
