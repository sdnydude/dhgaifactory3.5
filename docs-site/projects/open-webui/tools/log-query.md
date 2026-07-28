---
id: log-query
title: DHG Log Query
sidebar_position: 4
---

# DHG Log Query

> Query container logs from Loki for DHG AI Factory services. Search by container, log level, or text.

| Property | Value |
|----------|-------|
| Tool id | `dhg_log_query` |
| Backend | Loki (`:3100`, LogQL) |
| Attached to | 6 text models |

## Functions

### `query_logs`

Query logs from a specific DHG container via Loki — filterable by container, log level, and text. Common containers include `dhg-registry-api`, `dhg-registry-db`, `dhg-loki`, and the rest of the stack.

### `search_errors`

Search for error-level logs across **all** DHG containers in the last *N* minutes — useful for "what's broken right now?" triage.

## Backend

Loki runs as `dhg-loki` on port 3100 with 31-day retention. Logs are shipped by Promtail via Docker service discovery, labelled `container`, `compose_service`, `compose_project`, `job`, and `level`. Healthcheck and metrics log lines are dropped by the Promtail pipeline. Config: `observability/loki/loki-config.yml`.

## Example prompts

- *"Show me the last 20 lines from dhg-registry-api."*
- *"Any errors across all containers in the last 15 minutes?"*
- *"Find warning-level logs mentioning 'timeout' in dhg-registry-db."*
