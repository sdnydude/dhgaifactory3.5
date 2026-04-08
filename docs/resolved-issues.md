# Resolved Issues (Feb-April 2026)

Archived from CLAUDE.md on 2026-04-08. These issues are fully resolved and retained for historical reference.

## Infrastructure

- **C1 Port 8011 conflict** — RESOLVED. Legacy orchestrator moved to 2024, registry-api owns 8011.
- **C3 LangGraph network isolation** — MITIGATED. Production runs in LangGraph Cloud (no local network needed). Dev instance still uses host.docker.internal.
- **C4 Infisical crash-looping** — RESOLVED. All 5 Infisical containers running stable (Up 2+ days).
- **C5 Hardcoded IPs in web-ui** — RESOLVED. Legacy web-ui decommissioned. New frontend uses env vars.
- **C6 Stale files at root** — RESOLVED. Proxy scripts removed, .bak files cleaned.
- Registry-db healthcheck, restart policy, cAdvisor version — all fixed.
- Healthchecks added to all containers (Promtail, Ollama, Tempo, Node Exporter, Postgres Exporter, LangGraph).

## Frontend

- **C2 Web-UI can't reach LangGraph** — RESOLVED. Legacy web-ui decommissioned. New dhg-frontend connects directly to LangGraph Cloud via langgraph-sdk.

## Observability & Testing

- **C7 No CI/CD** — RESOLVED. GitHub Actions CI in `.github/workflows/ci.yml` (lint, test, compose validation).
- **C8 Minimal test coverage** — IMPROVED. 44 tests across 7 test files (registry API + CME + agent endpoints). CI runs pytest.
- **C10 Loki no log ingestion** — RESOLVED. Promtail configured, shipping Docker container logs to Loki. Volume mount corrected for Docker Root Dir at `/mnt/4tb/docker`.
- OTel tracing added to all 11 LangGraph agents (85 @traced_node decorators).

## Documentation

- **C9 Documentation sprawl** — IMPROVED. 42 stale docs archived to `docs/archive/`. CLAUDE.md is canonical.

## Decommissioned Services

- **Dify** — DECOMMISSIONED. Zero usage, workers crash-looping (80 restarts). All containers, volumes, databases, and directories deleted.
- **RAGFlow** — DECOMMISSIONED. Zero usage, idle task executor. All containers, volumes, and directories deleted.
