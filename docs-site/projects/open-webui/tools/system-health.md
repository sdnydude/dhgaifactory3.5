---
id: system-health
title: DHG System Health
sidebar_position: 2
---

# DHG System Health

> Query DHG AI Factory system health, incidents, corrections, and deferred items from the Registry API.

| Property | Value |
|----------|-------|
| Tool id | `dhg_system_health` |
| Backend | Registry API (`:8011`) |
| Attached to | all 8 workspace models |

## Functions

### `get_container_health`

Returns the DHG Registry API health-check status — the response from the `GET /healthz` endpoint.

- **200 `"OK"`** — database reachable.
- **503** — database unavailable (`registry_db_errors` metric increments).

Backed by `registry/api.py` (`/healthz`).

### `get_system_health`

Returns overall DHG AI Factory system health, including feedback-pipeline status, incidents, corrections, and deferred items pulled from the registry.

## Example prompts

- *"What's the registry health right now?"*
- *"Is the feedback pipeline healthy? Any open incidents?"*
- *"Summarize the current system health."*

## Notes

This is the only tool attached to the two vision models, giving them a basic platform-status capability without log/KB access.
