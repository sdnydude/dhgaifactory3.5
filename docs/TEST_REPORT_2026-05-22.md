# DHG AI Factory — Test Report

**Date:** 2026-05-22  
**Branch:** master  
**Last Commit:** `6892a09` fix(registry): harden CME stats endpoints + dashboard panels + memreg pipeline  
**Unstaged:** Pydantic response models for CME stats endpoints (`cme_schemas.py`, `cme_stats_endpoints.py`)

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | 527 |
| **Passed** | 527 |
| **Failed** | 0 |
| **Errors** | 0 |
| **Warnings** | 88 |
| **Duration** | 2.86s |
| **Test Files** | 24 (with tests) + 3 (empty scaffolds) = 27 total |
| **Test Classes** | 87 |

**Result: ALL TESTS PASSING**

---

## Test Files Breakdown

| File | Tests | Domain |
|------|------:|--------|
| test_cme_sync_service.py | 83 | CME sync/extraction |
| test_cme_endpoints.py | 48 | CME project CRUD + pipeline |
| test_security.py | 44 | Auth, RBAC, JWT |
| test_incident_endpoints.py | 35 | Incident management API |
| test_cme_search_service.py | 32 | CME fulltext + vector search |
| test_cme_project_service.py | 29 | CME project service layer |
| test_cme_review_service.py | 28 | CME review workflow |
| test_review_workflow.py | 25 | Human review assignments |
| test_incident_service.py | 23 | Incident service layer |
| test_kb_service.py | 21 | KB search aggregation |
| test_inference_service.py | 21 | Inference routing |
| test_cme_pipeline_service.py | 19 | Pipeline runs |
| test_deferred_items.py | 17 | Deferred items CRUD |
| test_bug_fixes.py | 14 | Bug fixes CRUD |
| test_test_coverage.py | 13 | Test coverage tracking |
| test_dev_changelog_endpoints.py | 13 | Dev changelog |
| test_cme_stats_endpoints.py | 13 | CME stats + helpers |
| test_doc_pages_service.py | 10 | Doc pages upsert |
| test_api.py | 9 | Core health, metrics, media |
| test_agent_endpoints.py | 9 | Agent registry |
| test_export_endpoints.py | 8 | PDF export + bundles |
| test_webhook_endpoints.py | 6 | Webhook dispatch |
| test_export_signing.py | 4 | HMAC token signing |
| test_projects_endpoints.py | 3 | Project listing |
| **Total** | **527** | |

### Empty Scaffold Files (0 tests each)

| File | Status |
|------|--------|
| test_coverage_endpoints.py | Scaffold only — no `def test_` functions |
| test_coverage_schemas.py | Scaffold only |
| test_coverage_service.py | Scaffold only |

---

## Coverage by Domain

| Domain | Files | Tests | % of Total |
|--------|------:|------:|-----------:|
| CME (pipeline, sync, search, review, stats, project) | 8 | 252 | 47.8% |
| Security & Auth | 1 | 44 | 8.4% |
| Incident Management | 2 | 58 | 11.0% |
| Memreg (bug fixes, deferred, test coverage, KB, insights, decisions) | 4 | 65 | 12.3% |
| Infrastructure (API, agents, export, webhooks, inference) | 6 | 51 | 9.7% |
| Review Workflow | 1 | 25 | 4.7% |
| Dev Changelog + Doc Pages | 2 | 23 | 4.4% |
| Projects | 1 | 3 | 0.6% |
| Export Signing | 1 | 4 | 0.8% |
| Dev Changelog | 1 | 13 | 2.5% |

---

## Warnings Analysis

All 88 warnings are a single type:

| Warning | Count | Source Files |
|---------|------:|--------------|
| `datetime.datetime.utcnow()` deprecation | 28 unique call sites | test_cme_review_service.py (15), test_cme_pipeline_service.py (12), test_review_workflow.py (9), test_cme_sync_service.py (6), test_agent_endpoints.py (3), test_cme_endpoints.py (2), models.py (1) |

**Recommendation:** Replace `datetime.utcnow()` with `datetime.now(datetime.UTC)` across test files and `models.py`. Low priority — Python 3.12 deprecation warning, no behavioral impact until Python 3.14+.

---

## Live Endpoint Verification

### Response Times

| Endpoint | Latency | Status |
|----------|--------:|--------|
| `GET /healthz` | 1.2ms | OK |
| `GET /api/cme/stats/pipeline` | 3.6ms | 200 |
| `GET /api/cme/stats/services` | 2.5ms | 200 |

### Pipeline Stats (Live Data)

| Metric | Value |
|--------|-------|
| Total Projects | 6 |
| Total Runs | 28 |
| Total Documents | 43 |
| Total References | 269 |
| Avg Run Duration | 11,907.6s (~3.3 hrs) |
| Active Pipelines | 3 (all in `review` status) |
| Agents Reporting | 11 |
| Document Types | 11 |

### Service Health (Live Data)

| Metric | Value |
|--------|-------|
| Registered Services | 29 |
| DB Active Connections | 4 |
| Database Tables | 94 |
| Largest Table | incident_actions (521,106 rows) |

### Pydantic Response Models

Both CME stats endpoints now use typed Pydantic response models:

| Endpoint | Response Model | Sub-Models |
|----------|---------------|------------|
| `/api/cme/stats/pipeline` | `PipelineStatsResponse` | `AgentCompletionItem`, `DocumentThroughputItem`, `ActivePipelineItem` |
| `/api/cme/stats/services` | `ServiceHealthResponse` | `ServiceItem` |

Verified: live data serializes cleanly through all models with no validation errors.

---

## Infrastructure Health

| Container | Status | Uptime |
|-----------|--------|--------|
| dhg-registry-api | healthy | 5 min (just rebuilt) |
| dhg-registry-db | healthy | 5 days |
| dhg-frontend | healthy | 21 min |
| dhg-prometheus | healthy | 5 days |
| dhg-grafana | healthy | 5 days |
| dhg-loki | healthy | 5 days |
| dhg-tempo | healthy | 5 days |
| dhg-ollama | healthy | 5 days |
| dhg-medkb-api | healthy | 5 days |
| dhg-vs-engine | healthy | 5 days |

**Unhealthy:** `dhg-medkb-ingestor` (stub service — expected, activates Phase 5)

**Total DHG containers:** 35 running

---

## Test Quality Observations

### Strengths
- **High coverage of CME domain** — 252 tests (48%) cover the core revenue-generating pipeline
- **Service layer isolation** — service tests mock DB, endpoint tests use TestClient with fixtures
- **Error path testing** — every endpoint has a "service error returns 500" test
- **Edge cases covered** — empty data, missing fields, duplicate detection, concurrent writes
- **Helper function testing** — `_float_or_none`, `_int_or_zero` have dedicated unit tests

### Gaps to Address
- **3 empty scaffold files** — `test_coverage_endpoints.py`, `test_coverage_schemas.py`, `test_coverage_service.py` have no tests
- **No integration tests** hitting the live database (all use SQLite in-memory via conftest)
- **No E2E tests** for the CME stats → dashboard pipeline (frontend fetches, renders)
- **Projects endpoints** only have 3 tests — lowest coverage
- **`datetime.utcnow()` deprecation** — 28 call sites across 7 files need updating

---

## Recent Changes (This Session)

| Change | File | Impact |
|--------|------|--------|
| Added 6 Pydantic response models | `cme_schemas.py` | OpenAPI schema generation, output validation |
| Wired `response_model=` on both endpoints | `cme_stats_endpoints.py` | Info-leak prevention, type safety |
| Removed double-logging from service layer | `cme_stats_service.py` | Cleaner error boundaries |
| Added `console.warn` to dashboard fetch | `dashboards/page.tsx` | Debug visibility |
| Updated Loki/Promtail docs | `CLAUDE.md` | Accurate container discovery description |
| Added 5 helper tests | `test_cme_stats_endpoints.py` | `_float_or_none`, `_int_or_zero` coverage |

---

*Generated 2026-05-22 12:35 EDT from `master` branch on g700data1 (10.0.0.251)*
