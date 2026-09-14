# Advisor review — LangGraph-era removal claims and recommendation

Branch: feat/observability-rebuild-2026-09. Read-only verification, 2026-09-06.
Method: every claim re-run with its own command; codegraph for symbols, AST (not grep) for Python,
`docker inspect` for env key names (values never printed), Grafana API with admin creds held in shell
variables. docker-compose.override.yml was not opened.

Severity key: HIGH = CEO told something false; MEDIUM = imprecise; LOW = note.

## Claims

### 1. No running container has LANGCHAIN_TRACING_V2 — CONFIRMED
`docker inspect` env key names across all 52 dhg-*/portage-* containers: 0 occurrences.

### 2. registry/ has zero langsmith imports or @traceable — CONFIRMED
AST scan of 201 .py files under registry/: 0 langsmith/langchain/langgraph imports, 0 `traceable`/`traced_node`
decorators. Codegraph symbol search agrees (only frontend hits for the env names).

### 3. medkb env clean; medkb depends on langchain — CONFIRMED, LOW precision note
dhg-medkb-api env keys matching LANGSMITH_/LANGCHAIN_/OTEL_: none.
services/medkb/requirements.txt pins langchain, langchain-core, langchain-anthropic, langchain-ollama,
**langgraph** and **langsmith**. Imports (AST, 58 files): `langchain.chat_models` (llm_factory.py:6),
`langgraph.graph` (graph/builder.py:3), `langchain_core.messages` (nodes/rewrite|grade|generate.py:6).
Note: the RAG graph is built with langgraph, not just langchain; langsmith is pinned but never imported.

### 4. Only two comment/description lines in live observability config — CONFIRMED
grep over yml/yaml/json/alloy/tmpl/ini/conf under observability/ (excluding audit-2026-09/, AUDIT*.md):
exactly prometheus/rules.d/gpu.yml:15 (alert description) and prometheus/prometheus.yml:206 (comment).
Only other file of any type: observability/REBUILD-PLAN-2026-09.md (prose, not config).

### 5. Tempo not running; no Grafana datasource/derived-field/exemplar link — CONFIRMED
`docker ps -a`: no tempo container in any state. provisioning/datasources/prometheus.yml uses
`deleteDatasources: [Tempo]`; loki.yml has no derivedFields. Live `/api/datasources`: Prometheus, Loki,
Registry DB only, no derivedFields/exemplarTraceIdDestinations/tracesToLogs in jsonData.
LOW: `tempo` is still a compose service in docker-compose.yml, held out via `profiles: ["retired"]`
(README line 229-232 documents this) — consistent with "not running", but it is not gone from compose.

### 6. dhg-langgraph-traces dashboard gone — CONFIRMED
Deleted in commit 3189bdd (`.../dashboards/json/dhg-langgraph-traces.json`); `git ls-files` shows no
langgraph file under observability/grafana; live `/api/search?query=langgraph` returns `[]`; 13 dashboards
listed, none LangGraph.

### 7. templates/agent-boilerplate has no langchain-family imports/deps — CONFIRMED
6 .py files, 0 imports; requirements*.txt contain no langchain/langgraph/langsmith; README line 4-5 states
the retirement explicitly.

### 8. registry-api carries LANGGRAPH_API_URL + LANGCHAIN_API_KEY; frontend carries LANGCHAIN_API_KEY — CONFIRMED
Key names from `docker inspect`: dhg-registry-api: LANGGRAPH_API_URL, LANGCHAIN_API_KEY.
dhg-frontend: LANGCHAIN_API_KEY. No other dhg-/portage- container carries any LANGCHAIN_/LANGSMITH_/
LANGGRAPH_/OTEL_ key. Both containers' compose labels list docker-compose.yml + docker-compose.override.yml;
in docker-compose.yml `registry-api` has only a `volumes:` key and `frontend` is not defined at all, so those
env lines come from the override (inferred from labels; override not read).

### 9. Eight LangGraph-era services, none running; five LANGCHAIN_/LANGSMITH_ lines — CONFIRMED, MEDIUM precision note
docker-compose.yml services include exactly orchestrator, medical-llm, research, curriculum, outcomes,
competitor-intel, qa-compliance, visuals (container_names dhg-aifactory-orchestrator, dhg-medical-llm,
dhg-research, dhg-curriculum, dhg-outcomes, dhg-competitor-intel, dhg-qa-compliance, dhg-visuals-media);
none exists in any state; all `restart: "no"`; each `depends_on: [registry-db]` only; nothing depends on them.
LANGCHAIN_/LANGSMITH_ lines: exactly five (L42-46). **All five sit inside the `orchestrator` service block.**
They are not a separate item — deleting the service deletes them. Phrasing them as an additional action
overstates the change.

### 10. frontend langgraph/copilotkit routes → LangGraph Cloud, 503 live; /inbox uses @langchain/langgraph-sdk — PARTIALLY CONFIRMED, MEDIUM
- `api/langgraph/[...path]/route.ts` and `api/copilotkit/route.ts` both default to
  `https://dhg-agents-...us.langgraph.app` and read `process.env.LANGCHAIN_API_KEY`. CONFIRMED.
- Live: GET /api/langgraph/threads → 503; /api/langgraph/ok|info|assistants/search → 503 with body
  "upstream connect error ... Connection refused". Direct GET to the cloud `/ok` with no key → 503. So the
  deployment itself is down at the edge; the 503 is not an auth failure. CONFIRMED for the proxy.
- copilotkit "returns 503": UNVERIFIABLE under read-only constraints. GET → 405, empty POST → 400. A real
  CopilotKit GraphQL POST was not sent (data-sending); by code, a LangGraph failure would surface inside the
  runtime response, not as a bare HTTP 503.
- /inbox: page.tsx → components/review/inbox-master-detail.tsx → lib/inboxApi.ts → `Client` from
  `@langchain/langgraph-sdk` (package.json ^1.6.5). CONFIRMED. Page shell renders 200; its data call goes
  through the 503 proxy.

### 11. 18 modules import langsmith traceable, ~104 traced_node sites, none running — COUNTS CONFIRMED; "no container" MEDIUM
AST over langgraph_workflows/dhg-agents-cloud/src (57 files): 18 modules import `langsmith.traceable`,
104 `@traced_node` sites, 160 `@traceable` sites — matches. However **dhg-audio-agent is a running container
built from that tree** (compose project dhg-audio-agent, working_dir
`.../dhg-agents-cloud/src/dhg-audio-agent`, image has langgraph 1.0.8, langsmith 0.6.9, langchain-core 1.2.9;
graph.py:9 imports `langgraph.graph`). It contains 0 of the 18 traceable modules and 0 traced_node sites and
has no LANGCHAIN_* env, so the tracing statement holds — but "no container runs from this src tree" is false.

### 12. What in registry reads LANGGRAPH_API_URL / LANGCHAIN_API_KEY — ANSWERED (codegraph found no symbol; AST found the reads)
registry/cme_endpoints.py only: `os.getenv("LANGGRAPH_API_URL", LANGGRAPH_CLOUD_URL)` and
`os.getenv("LANGCHAIN_API_KEY", "")` at L58-59, 100-101, 126-127, 162-163 (default URL constant L48 = the same
cloud URL). Consumers: `trigger_langgraph_pipeline` (POST /projects/{id}/start L453, /rerun L609),
`cancel_langgraph_run` (POST /cancel L575, and rerun), `trigger_intake_prefill` (intake-prefill route, L251),
`_fetch_thread_from_cloud` (POST /projects/{id}/sync L199, POST /sync-active L216, GET /projects/{id}/status
L499 auto-sync). No scheduler calls them (apscheduler appears only in timeout_handler.py). cme_sync_service.py
does not read the env.
What breaks if removed: LANGGRAPH_API_URL — nothing (default identical). LANGCHAIN_API_KEY — header becomes
`""`; today the cloud refuses the connection before auth, so those endpoints already fail (502/500). Live
outcome unchanged; if the deployment were revived before Wave 2, these routes would fail 401/403 instead of
succeeding.

## Recommendation verdict: APPROVE WITH CHANGES

Safe subset, in this order:
1. Delete the eight service blocks from docker-compose.yml. Nothing references them as compose targets:
   depends_on is outbound-only (registry-db); no docs-site, .claude/commands, scripts/, Makefile or
   .github/ reference the service or container names (only stale copies under .claude/worktrees/*, and
   scripts/add_openai_endpoints.sh which edits agents/ source dirs, not compose). CI runs
   `docker compose config --quiet` — run it locally after the edit. Bonus: `make up` currently would try to
   build all eight from agents/*/Dockerfile; deletion removes that hazard.
2. The "five env lines" are inside the orchestrator block and disappear with step 1 — drop them from the
   change description rather than listing a second action.
3. Override: registry-api `LANGGRAPH_API_URL` — delete, zero behavior change. `LANGCHAIN_API_KEY` on
   registry-api and frontend — deleting changes nothing live (cloud is 503 pre-auth; /inbox and copilotkit
   already cannot reach it) and removes a possibly unrotated key from two running containers. Accept, with
   the stated consequence that the CME start/rerun/cancel/sync/status routes and /inbox stay broken until
   Wave 2 replaces them (they are broken now regardless).
4. Follow-ups outside this change: docs-site/projects/dhg-ai-factory/architecture.md:44 will describe
   services compose no longer defines (one-line edit); `tempo` remains in compose under `profiles: [retired]`.
