# Audit 1 — Observability Architecture Currency (READ-ONLY)

Question: is the metrics/logs/traces layer design current, given LangGraph (cloud + local) and
LangSmith are deprecated in favour of Pydantic AI + Langfuse?

Verification date: 2026-09-04. Host g700data1 = 10.0.0.251. Langfuse host dh40801 = 10.0.0.179.

Headline: **metrics and logs are current and healthy; traces are entirely dead.** Tempo has
received **zero spans since it started ~19.5 days ago** while every trace producer in the repo
(both `traced_node` implementations, all 24 call sites) belongs to the deprecated LangGraph
agent set, which is not running. Langfuse is live on dh40801 but nothing on g700data1 points at
it — no `LANGFUSE_*` env exists on any running container, and the only Langfuse SDK code in the
repo is a single unexecuted prototype.

---

## (a) Telemetry path table

Legend for Status: **CURRENT** = feeds a live consumer; **LG/LS-DEP** = LangGraph/LangSmith
dependent; **NO-EQUIV** = something Langfuse/Pydantic AI should cover but nothing does;
**DEAD** = configured but nothing producing/consuming.

### Metrics

| # | Producer | Collector | Store | Consumer (dashboard/alert) | Status |
|---|---|---|---|---|---|
| M1 | registry-api `/metrics` (prometheus_client) `registry/api.py:298-301` | Prometheus job `registry-api` `observability/prometheus/prometheus.yml:26-33` **+ duplicate via `docker-sd`** (172.20.0.21:8000) | Prometheus (`dhg-prometheus`, prom/prometheus:v2.48.0, `docker-compose.override.yml:95-97`) | Grafana `dhg-registry-api.json`, `dhg-core-golden.json`; alert `RegistryApiDown` `alerts.yml:82-86`; frontend `/api/prometheus` proxy (200 live) | CURRENT |
| M2 | postgres-exporter :9187 | Prometheus job `postgres` (`prometheus.yml:36-42`) | Prometheus | `dhg-postgresql.json`; alert `PostgresConnectionsHigh` `alerts.yml:91-95` | CURRENT |
| M3 | node-exporter 172.18.0.1:9100 | job `node-exporter` (`prometheus.yml:44-50`) | Prometheus | `dhg-core-golden.json`; alerts `HostMemoryHigh`/`HostSwapHigh`/`RootDiskHigh`/`DataDiskHigh`/`ZombieProcessesHigh`/`LokiStoreGrowth` (`alerts.yml:17-48,100-104,152-156`) | CURRENT |
| M4 | cAdvisor :8080 | job `cadvisor` (`prometheus.yml:52-57`) | Prometheus | `docker-overview.json`; alerts `ContainerCrashLoop`, `ContainerMemoryLeak`, `ContainerHighCPU`, `ContainerHighMemory` (`alerts.yml:8-12,109-131`) | CURRENT |
| M5 | vs-engine `/metrics` (`services/vs-engine/main.py:23`) | job `vs-engine` (`prometheus.yml:59-66`) **+ duplicate via `docker-sd`** (172.20.0.3:8000) | Prometheus | `vs-engine.json` | CURRENT |
| M6 | medkb `/metrics` (`services/medkb/src/medkb/endpoints/health.py:4`, metrics defined `services/medkb/src/medkb/metrics.py:3`) | job `medkb` (`prometheus.yml:68-73`) | Prometheus | No dedicated dashboard found; no alert | CURRENT-but-unconsumed (scraped, target up, nothing reads it) |
| M7 | portage-api `/metrics` over TLS | job `portage-api` (`prometheus.yml:75-87`) | Prometheus | alert `PortageApiDown` `alerts.yml:73-77` | CURRENT (out-of-project service) |
| M8 | blackbox-exporter probes of Ollama (container + LAN) | job `blackbox-http` (`prometheus.yml:89-112`) | Prometheus | alert `OllamaDown` `alerts.yml:64-68` | CURRENT |
| M9 | blackbox probe of portage-api /health | job `blackbox-https` (`prometheus.yml:114-129`) | Prometheus | alert in `PortageApiDown` | CURRENT |
| M10 | memreg daemon :8020 (`memreg_*` metrics confirmed in Prometheus `__name__` index) | job `docker-sd` relabelled to `job="memreg"` (`prometheus.yml:139-172`) | Prometheus | `memreg-daemon.json`; alert `MemregDLQBacklog` `alerts.yml:139-143` | CURRENT (see note D3 — `memreg_dlq_depth` instant query returns empty) |
| M11 | session-logger `/metrics` (`services/session-logger/main.py:18`), 172.20.0.4:8009 | job `docker-sd` | Prometheus | No dashboard found | CURRENT-but-unconsumed |
| M12 | Loki self-metrics :3100 | job `loki` (`prometheus.yml:174-177`) | Prometheus | alert `LokiDown` `alerts.yml:161-165` | CURRENT |
| M13 | Alloy self-metrics :12345 | job `alloy` (`prometheus.yml:179-182`) | Prometheus | alert `AlloyDown` `alerts.yml:170-174` | CURRENT |
| M14 | Prometheus self | job `prometheus` | Prometheus | alert `PrometheusTargetDown` (`up == 0`) `alerts.yml:53-57` | CURRENT |
| M15 | Tempo metrics_generator span-metrics/service-graphs → `remote_write` to `http://prometheus:9090/api/v1/write` (`observability/tempo/tempo-config.yml:31-42`) | Prometheus remote-write receiver (`--web.enable-remote-write-receiver=true`, confirmed live) | Prometheus | Tempo service-map panels in `dhg-langgraph-traces.json` | **DEAD** — `count({__name__=~"traces_.*"})` returns empty; generator has no spans to derive from |
| M16 | Tempo self-metrics :3200/metrics (1002 lines served) | **no Prometheus job exists** | — | — | **DEAD** (target never defined; no `tempo` job in `prometheus.yml`, confirmed against `/api/v1/targets`) |

Alerting fan-out (single path): Prometheus `alerting:` → `dhg-alertmanager:9093`
(`prometheus.yml:9-12`) → webhook `http://dhg-registry-api:8000/webhooks/alertmanager`
(`observability/alertmanager/alertmanager.yml:11-15`), handled by `alertmanager_webhook`
`registry/api.py:338`. Live: Alertmanager `/api/v2/status` ready, 2 active alerts
(`HighErrorRate`, `ContainerErrorSpike`), registry webhook returns 405 to GET (route exists,
POST-only). **CURRENT.** Frontend also reads Alertmanager directly via
`frontend/src/app/api/alertmanager/[...path]/route.ts:3` (200 live). **CURRENT.**

### Logs

| # | Producer | Collector | Store | Consumer | Status |
|---|---|---|---|---|---|
| L1 | All Docker container stdout (docker socket SD) | **Grafana Alloy** `dhg-alloy` (grafana/alloy:v1.19.0, `docker-compose.override.yml:267-269`), config `observability/alloy/config.alloy` — 6 redaction stages, level extraction, healthcheck drop | Loki 3.7.6, filesystem, `retention_period: 0` keep-all (`observability/loki/loki-config.yml`) | Grafana `dhg-log-analytics.json`; Loki ruler → Alertmanager | CURRENT |
| L2 | Loki ruler rules `observability/loki/rules/fake/alerts.yml` (5 rules incl. `SecretLeakDetected`) | Loki ruler, `enable_alertmanager_v2: true` | — | `dhg-alertmanager:9093` (2 of these firing live) | CURRENT |
| L3 | **Promtail** config `observability/promtail/promtail-config.yml` | — | — | — | **DEAD** — no promtail container in `docker ps`; no promtail service in either compose file. Config file is an orphan superseded by Alloy (`config.alloy:1` says so explicitly). |

Live label set confirms L1: `compose_project`, `compose_service`, `container`, `job`, `level`;
`compose_project` values = `dhg-audio-agent, dhg-memreg, dhgaifactory35, plane-app, portage,
portage-e2e`. Note the Alloy config has **no compose_project filter**, so Loki ingests
non-DHG-AI-Factory projects (plane-app, portage) too, while Prometheus `docker-sd` *does*
filter (`prometheus.yml:150-153`). Asymmetry is intentional-looking but undocumented.

### Traces

| # | Producer | Collector | Store | Consumer | Status |
|---|---|---|---|---|---|
| T1 | `traced_node` OTel decorator, LangGraph agents — `langgraph_workflows/dhg-agents-cloud/src/tracing.py:118`, exporter OTLP **HTTP** (`tracing.py:34`), endpoint `os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://otel.digitalharmonyai.com/v1/traces")` `tracing.py:48-51`. 15 agent modules decorate nodes. | Tempo OTLP receiver 4317/4318 (`tempo-config.yml:6-13`) | Tempo local blocks, 744h retention | Grafana `dhg-langgraph-traces.json` (Tempo datasource) | **LG/LS-DEP + DEAD.** None of the 8 LangGraph agent containers in `docker-compose.yml` (orchestrator, medical-llm, research, curriculum, outcomes, competitor-intel, qa-compliance, visuals) is running. `OTEL_EXPORTER_OTLP_ENDPOINT` is set on **no** running container. Default endpoint `otel.digitalharmonyai.com` resolves to Cloudflare and returns **401** (Access) to an unauthenticated POST. |
| T2 | `traced_node` OTel decorator, medkb — `services/medkb/src/medkb/tracing.py:61`; exporter OTLP HTTP built as `f"{endpoint}/v1/traces"` `tracing.py:42`; initialised in `services/medkb/src/medkb/main.py:25` from `settings.otel_endpoint`; container env key `OTEL_ENDPOINT=http://dhg-tempo:4318` (`docker-compose.yml:335`). OTel SDK confirmed importable inside `dhg-medkb-api`. 9 graph nodes decorated. | Tempo 4318 | Tempo | `dhg-langgraph-traces.json` | **DEAD in practice** — `tempo_distributor_push_duration_seconds_count == 0` and `/api/search` over the last 24h returns `{"traces":[]}`. Tempo `process_start_time_seconds` = 1786824089 (≈19.5 days ago), so **zero spans ever received in this process lifetime**. Whether this is "medkb graph never invoked" vs "export silently failing" is **UNVERIFIED** (medkb logs show only healthz/metrics traffic; no `OTel tracing initialized` line survives in the retained log window). |
| T3 | LangSmith `@traceable` — 22 import sites (see (c)) | LangSmith SaaS `https://api.smith.langchain.com` (`docker-compose.yml:45`) | LangSmith cloud | LangSmith UI | **LG/LS-DEP.** `LANGCHAIN_TRACING_V2=true` appears only on the `orchestrator` service `docker-compose.yml:42` — a container that is **not running**. No running container carries `LANGCHAIN_TRACING_V2`. |
| T4 | Langfuse (`@observe`, `Agent.instrument_all()`) — `langgraph_workflows/dhg-agents-cloud/src/research_agent_pydantic_prototype.py:38-47` | Langfuse v3 self-hosted on dh40801 (`dhg-langfuse-web`, worker, clickhouse, postgres, redis, minio — all Up 2 weeks; `http://10.0.0.179:3000/api/public/health` → 200) | Langfuse ClickHouse | Langfuse UI | **NO-EQUIV / not wired.** Prototype only, gated on `LANGFUSE_PUBLIC_KEY`+`LANGFUSE_SECRET_KEY` (`:38`). Neither key, nor `LANGFUSE_HOST`/`LANGFUSE_BASE_URL`, is present on any running g700data1 container. Langfuse is **not** a target of Prometheus, is **not** a Grafana datasource, and its logs are not in Loki (dh40801 is a separate Docker host; Alloy only reads the local socket). |

### Grafana

Datasources provisioned (`observability/grafana/provisioning/datasources/`): Prometheus
(default, uid `prometheus`, exemplar link → tempo), Loki (uid `loki`, derived field `TraceID`
→ tempo), Tempo (uid `tempo`, tracesToLogsV2 → loki, serviceMap → prometheus). Grafana
10.2.0 on host port 3001. 9 dashboards provisioned from
`observability/grafana/provisioning/dashboards/json/`. **No Langfuse datasource exists.**
The Loki→Tempo derived field and the Prometheus exemplar link are both **DEAD** while Tempo
holds no spans.

---

## (b) Instrumentation findings (file:line)

- **Two independent `traced_node` implementations, both OTLP-HTTP, different endpoint contracts.**
  - `langgraph_workflows/dhg-agents-cloud/src/tracing.py:118` — reads `OTEL_EXPORTER_OTLP_ENDPOINT`
    (`:48`), default is a **full** `.../v1/traces` URL over the public Cloudflare hostname; service
    name `dhg-langgraph-agents` (`:44`). Whole module is guarded by an `ImportError` fallback
    (`:29-37`) that makes the decorator a silent no-op — the header states this is expected on
    LangGraph Cloud.
  - `services/medkb/src/medkb/tracing.py:61` — reads env key `OTEL_ENDPOINT` (not the OTel standard
    name), and **appends** `/v1/traces` itself (`:42`); service name `dhg-medkb` (`:27`). Same
    silent-no-op ImportError guard (`:11-23`).
  - Divergent env key names (`OTEL_EXPORTER_OTLP_ENDPOINT` vs `OTEL_ENDPOINT`) and divergent
    base-vs-full-URL conventions are a real inconsistency between the two.
- **`traced_node` call sites: 24 files** (codegraph_callers, aggregated over both symbols) —
  9 in `services/medkb/src/medkb/graph/nodes/` and 15 in
  `langgraph_workflows/dhg-agents-cloud/src/` (`orchestrator.py`, `research_agent.py`,
  `gap_analysis_agent.py`, `grant_writer_agent.py`, `curriculum_design_agent.py`,
  `learning_objectives_agent.py`, `marketing_plan_agent.py`, `citation_checker_agent.py`,
  `clinical_practice_agent.py`, `compliance_review_agent.py`, `intake_prefill_agent.py`,
  `needs_assessment_agent.py`, `prose_quality_agent.py`, `registry_agent.py`,
  `research_protocol_agent.py`). **Only the medkb 9 are in a running service.**
- **LangSmith `@traceable` import sites: 22 files**, split as:
  - `langgraph_workflows/dhg-agents-cloud/src/` — **17** (`agent.py:46`, `orchestrator.py:46`,
    `extract_topic.py:14`, `pubmed_client.py:15`, plus the 13 agent modules at
    `citation_checker_agent.py:29`, `clinical_practice_agent.py:24`,
    `compliance_review_agent.py:21`, `curriculum_design_agent.py:21`, `gap_analysis_agent.py:21`,
    `grant_writer_agent.py:22`, `intake_prefill_agent.py:19`,
    `learning_objectives_agent.py:21`, `marketing_plan_agent.py:21`,
    `needs_assessment_agent.py:30`, `prose_quality_agent.py:28`, `registry_agent.py:27`,
    `research_agent.py:23`, `research_protocol_agent.py:21`)
  - **`registry/` — 2, and these are in the LIVE served path**: `registry/notification_service.py:22`
    and `registry/timeout_handler.py:18`. `langsmith` is therefore a hard runtime import
    dependency of the running registry API even though `LANGCHAIN_TRACING_V2` is unset on that
    container (so the decorator is inert — it costs an import, not a trace).
  - `langgraph_workflows/Archive/` — 2 (`dhg-cme-research-agent-cloud/src/agent.py:39`,
    `dhg-cme-research-agent/src/agents/research_agent.py:26`)
  - `templates/agent-boilerplate/src/agent.py:22` — 1. **The boilerplate new agents are scaffolded
    from still teaches LangSmith `@traceable`.**
  - `agents/` legacy: **0** `@traceable` sites; legacy `agents/orchestrator/api.py:18` does use
    `prometheus_client`.
- **Pydantic AI / Langfuse SDK: exactly one file**, `research_agent_pydantic_prototype.py`
  (`pydantic_ai` `:31`, `pydantic_graph` `:33`, `langfuse` `:41-47`). Its docstring states the
  intended substitution outright (`:11`): `LangSmith @traceable -> Langfuse @observe /
  Agent.instrument_all()`, per ADR-001. It is a standalone script run from `.venv-prototype`
  (`:19`), not served, not containerised, not in any compose file.
- **registry-api `/metrics`**: `prometheus_client`, `from prometheus_client import generate_latest`
  at `registry/api.py:21`, route `@app.get("/metrics", response_class=PlainTextResponse)` at
  `registry/api.py:298-301` returning `generate_latest()` over the default global REGISTRY. No
  `prometheus-fastapi-instrumentator` / `make_asgi_app` anywhere in the repo. Metric definitions
  are centralised in `registry/metrics.py:9-42` (6 metrics: `registry_write_latency`,
  `registry_read_latency`, `registry_write_operations`, `registry_read_operations`,
  `registry_errors`, `registry_db_errors`) plus a Gauge in `registry/database.py:8`. Live:
  `sum(registry_write_operations_total)` = 1018.
- Other `/metrics` producers: `services/vs-engine/main.py:23`, `services/session-logger/main.py:18`,
  `services/medkb/src/medkb/endpoints/health.py:4`,
  `langgraph_workflows/dhg-agents-cloud/src/dhg-audio-agent/src/main.py:18`,
  `agents/orchestrator/api.py:18` (legacy, not running).
- **Env keys, by name, on running containers** (`docker inspect`, values never read):
  - `dhg-registry-api`: `LANGCHAIN_API_KEY`, `LANGGRAPH_API_URL`, `LOKI_URL`, `ANTHROPIC_API_KEY`
  - `dhg-medkb-api`: `LANGCHAIN_API_KEY`, `LANGSMITH_PROJECT`, `OTEL_ENDPOINT`, `ANTHROPIC_API_KEY`
  - `dhg-frontend`: `LANGCHAIN_API_KEY`
  - `dhg-vs-engine`, `dhg-memreg-agent`, `dhg-session-logger`: none of the telemetry keys
  - **Absent everywhere: `LANGCHAIN_TRACING_V2`, `LANGFUSE_HOST`, `LANGFUSE_BASE_URL`,
    `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `OTEL_EXPORTER_OTLP_ENDPOINT`.**
  - In `docker-compose.yml` (not running): `LANGCHAIN_TRACING_V2` `:42`, `LANGCHAIN_API_KEY` `:43`,
    `LANGCHAIN_PROJECT` `:44`, `LANGCHAIN_ENDPOINT` `:45`, `LANGSMITH_WORKSPACE_ID` `:46`,
    `LANGSMITH_PROJECT` `:334`, `OTEL_ENDPOINT` `:335`, `LANGCHAIN_API_KEY` `:336`.
  - `docker-compose.override.yml` could not be grepped for env key names — a repo hook blocks
    pattern searches against that file. Its service/image/container lines were readable. See (e).
- **Frontend consumers** (Next.js proxies, `frontend/src/app/api/`):
  `prometheus/[...path]` (live, 200), `alertmanager/[...path]` (live, 200,
  `route.ts:3` default `http://dhg-alertmanager:9093`), `monitoring/[...path]`,
  `registry/[...path]`, `health/[service]`, and **`langgraph/[...path]`** whose default is the
  LangGraph Cloud URL (`route.ts:3`) and which returns **503** live. `copilotkit/route.ts:11`
  targets the same `LANGGRAPH_API_URL`. There is **no `langfuse/[...path]` proxy**.

---

## (c) Deprecated-dependency list, with the evidence of what still consumes it

1. **LangSmith `@traceable` in the live registry API** — `registry/notification_service.py:22`,
   `registry/timeout_handler.py:18`. Consumer evidence: `dhg-registry-api` is Up 5 days and
   scraped; but it has no `LANGCHAIN_TRACING_V2`, so nothing consumes the traces. The dependency
   is an import, not a data path.
2. **LangSmith `@traceable` across 17 LangGraph agent modules** — consumer evidence: none live;
   the only container ever configured to emit (`orchestrator`, `docker-compose.yml:31-46`) is
   not running.
3. **`templates/agent-boilerplate/src/agent.py:22`** — the scaffold for new agents still imports
   LangSmith; consumer evidence: it is the documented starting point (`memory/langgraph-agent-template.md`
   referenced from MEMORY.md), so every new agent inherits the deprecated dependency.
4. **Grafana dashboard `dhg-langgraph-traces.json`** (uid `dhg-langgraph-traces`) — 6 panels, all
   Tempo `traceqlSearch`/`serviceMap`. Consumer evidence: it is provisioned and visible, and it
   renders empty (Tempo has 0 traces). It is the only trace-facing dashboard.
5. **Tempo itself + its OTLP receivers + metrics_generator remote_write** — consumer evidence for
   *removal candidacy*: only LangGraph agents and medkb produce OTel spans, and 0 spans have
   arrived in 19.5 days. Counter-evidence for *keeping*: medkb (`OTEL_ENDPOINT` `:335`) is a
   current, non-deprecated service and is wired to it; Langfuse v3 also speaks OTLP, so the
   receiver could be repointed rather than deleted. Not my call — flagging both sides.
6. **`frontend/src/app/api/langgraph/[...path]/route.ts` + `copilotkit/route.ts:11`** — consumer
   evidence: served by `dhg-frontend` (Up 9 days, healthy) and returns 503 on `/info`.
7. **`docker-compose.yml:31-228`** — 8 LangGraph/legacy agent service definitions with the full
   `LANGCHAIN_*`/`LANGSMITH_*` env block; none running.
8. **`observability/promtail/promtail-config.yml`** — superseded by Alloy on 2026-08-25
   (`config.alloy:1-2` names promtail EOL 2026-03-02); no promtail container, no compose service.
   Not LangGraph-related, but dead config in the same tree.

---

## (d) NO-EQUIVALENT list (Langfuse / Pydantic AI should cover it; nothing does today)

1. **LLM-call tracing for any running service.** With LangSmith inert and Langfuse unwired, there
   is currently **zero** LLM-level observability anywhere in the stack. `dhg-registry-api`,
   `dhg-medkb-api` and `dhg-vs-engine` all carry `ANTHROPIC_API_KEY` and make model calls with no
   trace destination.
2. **Langfuse itself is unmonitored.** Six containers on dh40801, none scraped by Prometheus
   (no job, no blackbox probe), no Grafana datasource, no alert, and their logs are not in Loki
   (Alloy reads only the local g700data1 docker socket). A Langfuse worker or ClickHouse outage
   would be silent.
3. **No cross-host telemetry collection.** The whole design assumes one Docker host. dh40801 has
   no Alloy, no node-exporter, no cAdvisor.
4. **No trace-ingest health signal.** `alerts.yml` has no rule on Tempo (no `up{job="tempo"}`,
   no span-rate alert) — which is precisely why 19.5 days of zero traces produced no alert.
5. **No token-cost / model-usage metrics.** LangSmith used to be the de-facto source; Langfuse
   would be the replacement; nothing in Prometheus carries cost or token counters today
   (`__name__` index has no `llm_*`, `token_*`, or `cost_*` families).
6. **No Pydantic AI instrumentation contract.** The prototype uses `Agent.instrument_all()`
   (`research_agent_pydantic_prototype.py:44`), which emits **OpenTelemetry**; there is no
   decision recorded in the observability configs about whether those spans land in Tempo, in
   Langfuse's OTLP endpoint, or both. The two existing `traced_node` helpers would be redundant
   with it.

---

## (e) Open questions / UNVERIFIED

- **UNVERIFIED — why Tempo has zero spans.** Confirmed zero
  (`tempo_distributor_push_duration_seconds_count 0`, `/api/search` 24h empty, process up 19.5d).
  Not distinguished: medkb graph nodes never executed vs. OTLP export failing silently. Deciding
  this needs either a medkb `/v1/query` invocation (a state change — out of scope for a read-only
  audit) or debug-level medkb logs, which are not retained in the visible window.
- **UNVERIFIED — telemetry env keys in `docker-compose.override.yml`.** A repo hook denied every
  grep of that file for `LANG*`/`OTEL*`/`TRACING*` key names (secret-safety). I substituted
  `docker inspect` on the running containers, which gives the *effective* env keys and is
  arguably better evidence — but a key defined in the override for a **stopped** service would
  not appear. Structural lines (service names, images, container names, volumes) were readable
  and are cited above.
- **UNVERIFIED — Grafana dashboard runtime state.** Grafana `/api/search` returns 401 without
  credentials; I read the provisioned JSON on disk instead. Whether an operator has since added
  unprovisioned dashboards (e.g. pointing at Langfuse) is unknown.
- **UNVERIFIED — whether a Cloudflare Access service token exists for
  `otel.digitalharmonyai.com`.** The hostname resolves (Cloudflare IPs) and returns 401 to an
  unauthenticated POST. Whether LangGraph Cloud was ever able to push through it cannot be
  determined without reading Access config.
- **UNVERIFIED — `LOKI_URL` on `dhg-registry-api`.** The env key is set, but CodeGraph finds no
  `LOKI_URL` symbol anywhere in the indexed source; I could not confirm any read side. Possibly
  vestigial.
- **UNVERIFIED — `memreg_dlq_depth`.** Present in Prometheus's `__name__` index but an instant
  query returns no series, so alert `MemregDLQBacklog` (`alerts.yml:139-143`) may be unfirable
  right now. Could be a conditionally-registered gauge; not chased further.
- **Noted, not chased:** registry-api and vs-engine are each scraped twice (dedicated static job
  *and* `docker-sd`), producing duplicate series under different `job` labels.
- graphify's stored graph is stale (pre-#1504 node ids, archive-heavy) and was not used;
  CodeGraph + config reads + live HTTP were the evidence base.
