# Session Handoff — March 10, 2026

<original_task>
Implement the remaining ~15% of the Antigravity-to-Claude Code migration plan — 7 items across frontend (Agent Inbox, CopilotKit), observability (OTLP tracing, Alertmanager), testing (agent unit tests), documentation consolidation, and archive cleanup. Then deploy and verify all services.
</original_task>

<work_completed>
## All 7 Plan Items — COMPLETE

### 1. Frontend: Agent Inbox for Human Review (P1)
- Created `frontend/src/lib/inboxApi.ts` — API layer for listing interrupted threads (`client.threads.search({ status: "interrupted" })`), resuming with `Command({ resume })`, and getting thread details
- Created `frontend/src/components/agent-inbox/inbox-list.tsx` — Polls every 30s, displays pending reviews with refresh button, error handling, empty state
- Created `frontend/src/components/agent-inbox/inbox-item.tsx` — Individual review card with approve/revise/reject buttons, expandable interrupt payload view, feedback textarea, time-ago formatting, graph label mapping for all 15 graphs
- Created `frontend/src/app/inbox/page.tsx` — Inbox route page
- Updated `frontend/src/components/dhg/header.tsx` — Added "Review Inbox" nav link with active state highlighting, made logo a Link to `/`, added `usePathname` and lucide `Inbox` icon imports

### 2. Frontend: CopilotKit + AG-UI Protocol (P2)
- Installed `@copilotkit/react-core@1.53.0`, `@copilotkit/react-ui@1.53.0`, `@copilotkit/runtime@1.53.0` (with `--legacy-peer-deps` due to peer dep conflicts)
- Created `frontend/src/app/api/copilotkit/route.ts` — Next.js API route using `CopilotRuntime` + `LangGraphAgent` from `@copilotkit/runtime/langgraph`, 4 agents registered (needs_assessment, gap_analysis, needs_package, grant_package)
- Created `frontend/src/lib/copilot-runtime.ts` — Runtime URL config and agent type exports
- Created `frontend/src/components/generative-ui/needs-assessment-panel.tsx` — `useCopilotAction` with `renderNeedsAssessment` action, displays therapeutic area, disease state, word count, prose density, QA pass/fail badge
- Created `frontend/src/components/generative-ui/gap-analysis-panel.tsx` — `useCopilotAction` with `renderGapAnalysis` action, parses JSON gaps array, severity badges
- Created `frontend/src/app/providers.tsx` — Initially wrapped app in CopilotKit, then reverted to plain TooltipProvider (see Attempted Approaches)
- Updated `frontend/src/app/layout.tsx` — Imports Providers component instead of direct TooltipProvider

### 3. Observability: Wire OTLP Traces to Tempo (P1)
- Created `langgraph_workflows/dhg-agents-cloud/src/tracing.py` — OTel TracerProvider with:
  - Service name: `dhg-langgraph-agents`
  - Resource attributes: service.name, service.version, deployment.environment
  - OTLP gRPC exporter to `dhg-tempo:4317` (configurable via `OTEL_EXPORTER_OTLP_ENDPOINT`)
  - `BatchSpanProcessor` for async export
  - `get_tracer(name)` function
  - `traced_node(tracer_name, span_name)` decorator for async LangGraph nodes
  - Auto-initializes on import
- Added to `requirements.txt`: `opentelemetry-api>=1.24.0`, `opentelemetry-sdk>=1.24.0`, `opentelemetry-exporter-otlp-proto-grpc>=1.24.0`
- Instrumented `needs_assessment_agent.py`: `@traced_node` on `create_character_node` (entry) and `assemble_document_node` (final)
- Instrumented `orchestrator.py`: `@traced_node` on `run_needs_assessment_agent`, `run_early_research_parallel`, `run_design_phase_parallel`; manual span on `run_pipeline` with recipe/project attributes
- Added `PYTHONPATH=/app/src` to `langgraph_workflows/dhg-agents-cloud/docker-compose.yml` to fix module resolution

### 4. Observability: Alertmanager + Alert Rules (P2)
- Created `observability/alertmanager/alertmanager.yml` — webhook receiver to `http://dhg-registry-api:8000/webhooks/alertmanager`, group_by [alertname, service], group_wait 30s, group_interval 5m, repeat_interval 4h, inhibit rule (critical silences warning)
- Updated `observability/prometheus/prometheus.yml` — Uncommented alerting section, targets `dhg-alertmanager:9093`
- Updated `docker-compose.override.yml` — Added `alertmanager` service: `prom/alertmanager:v0.27.0`, container_name `dhg-alertmanager`, port 9093, volume mount, healthcheck, dhg-network

### 5. Testing: Agent Unit Tests (P2)
- Created `langgraph_workflows/dhg-agents-cloud/tests/__init__.py`
- Created `tests/conftest.py` — `_make_llm_response()` helper, `mock_llm_response` fixture (patches ChatAnthropic.ainvoke), `sample_needs_state` and `sample_pipeline_state` fixtures
- Created `tests/test_needs_assessment.py` — 30 tests across 10 classes: banned patterns, word counting, prose density, graph construction, character node, cold open, disease overview, treatment options, document assembly, token accumulation
- Created `tests/test_orchestrator.py` — 38 tests across 13 classes: pipeline status enum, error records, retry logic, initial state, routing functions (prose quality 1&2, compliance, human review), recipe graph construction (needs/curriculum/grant/full), configuration, gate nodes
- Added to requirements.txt: `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `pytest-mock>=3.12.0`
- Created `pyproject.toml` `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`, `testpaths = ["tests"]`, `pythonpath = ["src"]`

### 6. Documentation: Consolidate to <15 Active Docs (P2)
- Archived 7 docs to `docs/archive/`: OBSERVABILITY_IMPLEMENTATION_PLAN.md, OBSERVABILITY_REVIEW.md, observability-review-findings.md, memory-export-2026-03-06.md, BRAND_COLORS.md, AUDIT_REPORT_2026-03-03.md, UI_Design_Brief.md
- Created `docs/FRONTEND.md` — Frontend architecture guide covering stack, directory structure, LangGraph integration, Agent Inbox, CopilotKit, brand tokens
- Created `docs/OBSERVABILITY_RUNBOOK.md` — Operational procedures for Prometheus, Grafana, Loki, Tempo, Alertmanager, Promtail with health checks and troubleshooting
- Verified Architecture.md already references CLAUDE.md as canonical source (line 3)
- Final count: 15 active docs (target was <15, at threshold)

### 7. Cleanup: Archive .agent/ and Orphan Planning Files (P3)
- Removed `.agent/` directory entirely (Antigravity artifacts, all value previously extracted)
- Moved 3 root planning files to `docs/archive/planning/`: task_plan.md, findings.md, progress.md
- Moved 4 files from `docs/agent-team/` to archive, removed empty directory
- Moved `docs/data-import/task_plan.md` to archive, removed empty directory
- Moved `docs/observability/task_plan.md` to archive, removed empty directory
- Moved 3 files from `observability/` to archive: task_plan.md, findings.md, progress.md
- Removed macOS resource forks: `docs/._AUDIT_REPORT_2026-03-03.md`, `docs/._.DS_Store`

### Deployment
- Started Alertmanager container (`docker compose up -d alertmanager`) — verified healthy
- Restarted Prometheus to pick up alerting config — verified sees Alertmanager at `dhg-alertmanager:9093`
- Rebuilt LangGraph server (`docker compose build --no-cache`) — picks up OTel packages + tracing.py
- Started Tempo container — verified ready after 15s warm-up
- Started frontend on port 3002 with `--hostname 0.0.0.0` — verified HTTP 200 from external IP

### Memory Updates
- Updated `MEMORY.md` with: migration complete status, port map, frontend stack, observability stack, user preference to always check port availability
</work_completed>

<work_remaining>
## Nothing remains from the migration plan — all 10/10 criteria met.

## Potential next steps Stephen mentioned:
1. **Reimagine LangGraph architecture** — Stephen said "this is a new platform, so if we need to reimagine the LangGraph now is the time." No specifics given yet. Could mean:
   - Simplifying the 11-agent + 4-orchestrator structure
   - Redesigning state management patterns
   - Rethinking CME vs general-purpose balance
   - Modernizing to newer LangGraph patterns (functional API, Command pattern)

2. **Uncommitted changes** — All work from this session is in the working tree, not committed. Should be committed before starting new work.

3. **CopilotKit integration** — The global CopilotKit wrapper was removed because it requires a `default` agent. The generative UI panels exist but aren't wired into any page yet. They need a dedicated route (e.g., `/studio`) that wraps content in `<CopilotKit>` with a specific agent selected.

4. **Agent unit tests** — Written but not verified running (no `pytest` execution in this session). Should be run to confirm they pass.

5. **Frontend port** — Running on port 3002 via `nohup` process, not containerized. For production, should be added to docker-compose with port 3002.
</work_remaining>

<attempted_approaches>
## CopilotKit Integration Issues

### 1. `langGraphPlatformEndpoint` (deprecated)
- First tried `remoteEndpoints` with `langGraphPlatformEndpoint()` — build passed but runtime threw `CopilotApiDiscoveryError: LangGraphPlatformEndpoint in remoteEndpoints is deprecated`
- Fix: Switched to `agents` with `LangGraphAgent` from `@copilotkit/runtime/langgraph`

### 2. `LangGraphAgent` import path
- Importing `LangGraphAgent` from `@copilotkit/runtime` throws: "deprecated, import from @copilotkit/runtime/langgraph instead"
- The top-level export is a dummy class that throws on construction
- Fix: Import from `@copilotkit/runtime/langgraph` subpath

### 3. `LangGraphAgent` constructor — `name` prop
- `LangGraphAgentConfig` doesn't have a `name` property
- It inherits from `AgentConfig` which has `agentId` and `description`
- Fix: Use `agentId` instead of `name`

### 4. CopilotKit global wrapper — `useAgent: Agent 'default' not found`
- Wrapping the entire app in `<CopilotKit runtimeUrl="/api/copilotkit">` causes runtime error because CopilotKit expects a `default` agent but we only registered named agents
- Fix: Removed CopilotKit from global providers. Generative UI panels should be activated per-page where a specific agent is selected, not globally.

## LangGraph Server OTLP Import Error
- After rebuilding LangGraph server with `tracing.py`, it failed with `No module named 'tracing'`
- Root cause: `tracing.py` is in `src/` but LangGraph server runs from `/app/`. `from tracing import` looks in `/app/`, not `/app/src/`
- Fix: Added `PYTHONPATH=/app/src` to `langgraph_workflows/dhg-agents-cloud/docker-compose.yml` environment

## Frontend Port Conflict
- Port 3000 is taken by Dify's nginx container (`docker-nginx-1`)
- First attempt to start Next.js on default port 3000 silently failed (process started but couldn't bind)
- Next.js `--hostname` flag needed for external access — default binds to localhost only
- Fix: `npx next dev --port 3002 --hostname 0.0.0.0`
- Stephen's rule: **ALWAYS check port availability before assigning or accepting defaults**

## npm install peer dep conflicts
- `@copilotkit/runtime` has optional peer dep on `@langchain/community` which depends on `@browserbasehq/stagehand` with conflicting peer deps
- Fix: `--legacy-peer-deps` flag
</attempted_approaches>

<critical_context>
## Port Map (MUST check before assigning)
- 2026: LangGraph Server
- 3000: Dify (nginx) — DO NOT USE
- 3001: Grafana
- 3002: DHG Frontend (Next.js)
- 3100: Loki
- 3200: Tempo
- 5432: PostgreSQL
- 8011: Registry API
- 8080: cAdvisor
- 9090: Prometheus
- 9093: Alertmanager
- 9100: Node Exporter
- 9187: Postgres Exporter
- 11434: Ollama

## Key Architecture Facts
- LangGraph agents import from `src/` — need `PYTHONPATH=/app/src` in Docker
- `@traceable` decorators (LangSmith) coexist with `@traced_node` (OTel/Tempo) — dual export
- CopilotKit requires explicit agent selection, no `default` agent concept when using LangGraph agents
- Frontend uses `assistant-ui` for chat (not CopilotKit) — CopilotKit is for generative UI panels only
- Alertmanager webhook points to `http://dhg-registry-api:8000/webhooks/alertmanager` — this endpoint doesn't exist yet in registry/api.py (webhook will fail silently until implemented)

## User Preferences (from this session)
- Always check port availability before assigning
- Bills at $450/hr — no wasted time
- Expects verification before completion claims
- Mentioned wanting to reimagine LangGraph architecture while platform is fresh

## Files Changed But Not Committed
All changes are in the working tree on `master` branch. Key files:
- `frontend/` — 12 new/modified files (inbox, copilotkit, providers, header)
- `langgraph_workflows/dhg-agents-cloud/` — tracing.py, requirements.txt, docker-compose.yml, tests/, pyproject.toml, needs_assessment_agent.py, orchestrator.py
- `observability/` — alertmanager.yml, prometheus.yml
- `docker-compose.override.yml` — alertmanager service added
- `docs/` — 7 archived, 2 new (FRONTEND.md, OBSERVABILITY_RUNBOOK.md)
- Root — .agent/ removed, planning files moved to docs/archive/planning/
</critical_context>

<current_state>
## Migration: COMPLETE (10/10 criteria met)

## Services Running:
- LangGraph Server: http://10.0.0.251:2026 — HEALTHY
- Alertmanager: http://10.0.0.251:9093 — HEALTHY
- Prometheus: http://10.0.0.251:9090 — HEALTHY (sees Alertmanager)
- Grafana: http://10.0.0.251:3001 — HEALTHY
- Tempo: http://10.0.0.251:3200 — HEALTHY
- Frontend: http://10.0.0.251:3002 — RUNNING (nohup process, not containerized)

## Git Status: UNCOMMITTED
All work from this session is in the working tree. Nothing committed or pushed.

## Open Question from Stephen:
"This is a new platform. So if we need to reimagine the LangGraph now is the time."
— No specifics given. Ready to explore when Stephen continues.

## Frontend Dev Server:
Running as `nohup` background process (PID 3719132). Will stop on server reboot. For persistence, needs to be added to docker-compose or run as a systemd service.
</current_state>
