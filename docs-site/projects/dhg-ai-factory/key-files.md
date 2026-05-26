---
sidebar_position: 4
title: Key Files
---

# Key File Locations

## Docker

| Purpose | Path |
|---------|------|
| Main compose | `docker-compose.yml` |
| Override compose | `docker-compose.override.yml` |
| LangGraph compose | `langgraph_workflows/dhg-agents-cloud/docker-compose.yml` |

## LangGraph Agents

| Purpose | Path |
|---------|------|
| LangGraph config | `langgraph_workflows/dhg-agents-cloud/langgraph.json` |
| Agent source | `langgraph_workflows/dhg-agents-cloud/src/*.py` |
| Orchestrator | `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py` |
| OTel tracing | `langgraph_workflows/dhg-agents-cloud/src/tracing.py` |
| Drive sync hook | `langgraph_workflows/dhg-agents-cloud/src/drive_sync.py` |

## Registry

| Purpose | Path |
|---------|------|
| API app | `registry/api.py` |
| CME endpoints | `registry/cme_endpoints.py` |
| Agent endpoints | `registry/agent_endpoints.py` |
| DB models | `registry/models.py` |
| Schemas | `registry/schemas.py` |
| Auth module | `registry/auth.py` |
| Security API | `registry/security_endpoints.py` |
| Export signing | `registry/export_signing.py` |
| Export endpoints | `registry/export_endpoints.py` |
| Tests | `registry/test_*.py` (5 files, 105 tests) |

## Frontend

| Purpose | Path |
|---------|------|
| Source | `frontend/src/` |
| Auth middleware | `frontend/src/middleware.ts` |
| Permissions | `frontend/src/lib/permissions.ts` |
| Inbox API | `frontend/src/lib/inboxApi.ts` |
| Files API | `frontend/src/lib/filesApi.ts` |
| Review components | `frontend/src/components/review/` |
| Print tokens | `frontend/src/lib/printTokens.ts` |
| Registry proxy | `frontend/src/app/api/registry/[...path]/route.ts` |

## Services

| Purpose | Path |
|---------|------|
| VS Engine | `services/vs-engine/` |
| PDF renderer | `services/pdf-renderer/` (main.py, renderer.py, bundler.py, drive_client.py, worker.py) |
| MedKB | `services/medkb/src/medkb/` |

## Observability

| Purpose | Path |
|---------|------|
| All configs | `observability/` |
| Prometheus | `observability/prometheus/` |
| Grafana | `observability/grafana/` |
| Alertmanager | `observability/alertmanager/` |

## Documentation

| Purpose | Path |
|---------|------|
| Architecture docs | `docs/architecture/` |
| Agent docs | `DHG-CME-12-Agent-Docs/` |
| Current priorities | `docs/TODO.md` |
| Resolved issues | `docs/resolved-issues.md` |
