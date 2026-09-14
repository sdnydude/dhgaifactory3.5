# Adversarial Review 1 — Skeptic / Fabrication Hunter

Phase 2 review of `observability/AUDIT-2026-09.md`. Read-only. Every claim below was
re-derived from the live system or the cited file at the cited line by this reviewer;
nothing was accepted from the Phase 1 reports.

Run time: 2026-09-04 ~04:35–04:45 EDT on g700data1.

**Totals: 78 claims checked — 58 CONFIRMED, 20 REFUTED/MISLEADING, 8 UNVERIFIABLE.**
(Counts overlap: several claims are confirmed in count but refuted in stated cause.)

---

## A. Section 9 disagreements — settled

### 9.1 Target count: **17 is correct. A1 and A3 (18) are wrong.**

`GET /api/v1/targets` → `activeTargets` = **17**, all `health: up`, all `lastError: ""`.
The full list:

| job | scrapeUrl |
|---|---|
| alloy | http://alloy:12345/metrics |
| blackbox-http | probe → http://dhg-ollama:11434/api/tags |
| blackbox-http | probe → http://10.0.0.251:11434/api/tags |
| blackbox-https | probe → https://portage-api:8016/health |
| cadvisor | http://cadvisor:8080/metrics |
| docker-sd | http://172.20.0.21:8000/metrics (dhg-registry-api) |
| docker-sd | http://172.20.0.3:8000/metrics (dhg-vs-engine) |
| docker-sd | http://172.20.0.4:8009/metrics (dhg-session-logger) |
| memreg | http://172.20.0.22:8020/metrics (dhg-memreg-agent) |
| loki | http://loki:3100/metrics |
| medkb | http://dhg-medkb-api:8015/metrics |
| node-exporter | http://172.18.0.1:9100/metrics |
| portage-api | https://portage-api:8016/metrics |
| postgres | http://postgres-exporter:9187/metrics |
| prometheus | http://localhost:9090/metrics |
| registry-api | http://registry-api:8000/metrics |
| vs-engine | http://dhg-vs-engine:8000/metrics |

`droppedTargets` = **5**, all in job `docker-sd`: four are `portage-api` (two IPs × two
port-public-IP variants, compose project `portage`), one is `dhg-blackbox` (compose
project `dhg-blackbox`). Both fail the keep regex at `prometheus.yml:154-156`
(`dhgaifactory35|dhg-memreg`). The likely source of the "18" is counting a dropped
target, or counting the two `blackbox-http` probes plus a phantom.

### 9.7 Prometheus rule count: **18 is correct. A1 (17) is wrong.**

`GET /api/v1/rules`, all from `/etc/prometheus/alerts.yml`:
- group `dhg-infrastructure` — 14 rules (ContainerCrashLoop, HostMemoryHigh, HostSwapHigh,
  RootDiskHigh, DataDiskHigh, PrometheusTargetDown, OllamaDown, PortageApiDown,
  RegistryApiDown, PostgresConnectionsHigh, ZombieProcessesHigh, ContainerMemoryLeak,
  ContainerHighCPU, ContainerHighMemory)
- group `dhg-logs` — 3 (LokiStoreGrowth, LokiDown, AlloyDown)
- group `dhg-memreg` — 1 (MemregDLQBacklog)

**Total 18.** All 18 currently `inactive`. Loki ruler is separate: 5 rules, confirmed.

---

## B. REFUTED and MISLEADING

### HIGH

**R1 — §2 scoreboard and P11: the Loki container coverage numbers are inverted.**
Synthesis: "16 of 42 dhg-* containers emitted in 24h" / P11 "26 of 42 dhg-* containers
have no Loki stream in 24h."
Truth: 42 `dhg-*` containers running; Loki `label/container/values` over the last 24h
returns 39 containers, of which **26 are `dhg-*`**. So **26 emitted, 16 were silent** —
the reverse of what the audit says. Log-pipeline coverage is 62%, not 38%. P11's fix
target ("Alloy has no container filter, so these containers emit nothing") is stated over
the wrong set and a Phase 3 decision sized off "26 silent containers" would be wrong.

**R2 — §1 and G1: "Langfuse … wired to nothing on g700data1. No env keys on any running
container" is false.**
Enumerating env *key names* on all 60 running containers: `portage-api` (running on
g700data1, joined to `dhgaifactory35_dhg-network`) carries `LANGFUSE_BASE_URL`,
`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`. A Langfuse client is already wired on this
host. The audit is internally inconsistent here — §9.9 asks "whether Portage traces are
landing right now," which presupposes exactly the wiring §1 denies. Any Phase 3 plan built
on "nothing is wired to Langfuse" starts from a false premise.

**R3 — P3 and G3: `memreg_dlq_depth` / `memreg_captures_total` are NOT "declared, never
populated".**
`GET /api/v1/series` over 2026-08-01 → 2026-09-04 returns:
- `memreg_dlq_depth` — 2 series (instances 172.20.0.22 and 172.20.0.26);
  `max_over_time(memreg_dlq_depth[30d])` = **1** on 172.20.0.26.
- `memreg_captures_total{status="success",type="dlq_replay"}` — 1 series, max 1.

Both have been populated. The instant query returns 0 series only because the current
daemon's live `/metrics` (fetched directly from 172.20.0.22:8020) does not currently
export either family — they appear lazily. `MemregDLQBacklog` is
`memreg_dlq_depth > 0` **for 1h**; a transient depth of 1 that then disappears can never
satisfy a 1h `for:`. The rule is effectively dead, but for a different reason than stated,
so the fix target ("populate the metric") is wrong.

### MEDIUM

**R4 — P9: `registry_errors_total` does not have "0 series ever".**
Two series exist in the last 34 days: `registry_errors_total{error_type="logs_chat_unauthorized"}`
under both `job="registry-api"` and `job="docker-sd"`, `max_over_time(...[30d])` = 1.
It is instrumented and has fired at least once. The conclusion (effectively unused, never
queried by a dashboard) stands; the absolute "0 series ever" is false.

**R5 — G6: "`ollama.service` still installed" is false on g700data1.**
`systemctl list-unit-files | grep -i ollama` → nothing. `systemctl is-active ollama` →
`inactive` (no such unit). The **binary** exists (`/usr/local/bin/ollama`, 38MB, dated
Jun 4), but there is no systemd unit to mask or remove. Port 11434 is held by the Docker
publish. A remediation item "mask ollama.service" has nothing to act on.

**R6 — G6: "The prometheus.yml comment claiming coverage is wrong" misreads the comment.**
The comment at `prometheus.yml:90-93` says only: Ollama exposes no `/metrics`, so probe it
two ways — container DNS (is it serving?) and the LAN published port (is the host port
mapping alive?) — and notes the 2026-08-15 silent death. It makes **no** claim about
detecting a host Ollama impostor. The underlying gap is real (`blackbox.yml` `http_2xx`
has only `valid_status_codes: [200]`, no `fail_if_body_not_matches_regexp` — confirmed),
but the accusation against the comment is unfounded.

**R7 — §8: "Alertmanager to registry webhook path (verified 38 deliveries)".**
Loki count of `POST /webhooks/alertmanager HTTP/1.1" 200` in `dhg-registry-api`:
12 over 24h, **60 over 5d** (= the registry container's full uptime), 84 over 7d.
38 matches no window. The conclusion (webhook delivering) is CONFIRMED; the number is not
reproducible.

**R8 — §2 scoreboard: "incident endpoint `registry/api.py:338`".**
`registry/api.py:338` is the comment `# P5 log program (2026-08-25)` inside the
`ALERT_TRIGGER_MAP` dict. The endpoint is `@app.post("/webhooks/alertmanager")` at
**`registry/api.py:346`**.

**R9 — G1 (MISLEADING): "Volumes 52GB, 81% reclaimable" reads as a Langfuse problem.**
`docker --context dh40801 system df` confirms 52.09GB total / 42.35GB (81%) reclaimable
exactly. But `system df -v` shows the reclaimable bulk is **not Langfuse**:
`vllm_huggingface-cache` 36.02GB (0 links), `openshell-cluster-nemoclaw` 6.05GB (0 links),
`vllm_open-webui-data` 277MB (0 links). All six `dhg-langfuse_*` volumes are linked and
total ~9.7GB (clickhouse_data 8.67GB, clickhouse_logs 999MB, postgres 46.7MB,
minio 26.9MB, redis 0.6MB). Filing this under the Langfuse gap overstates the Langfuse
disk risk.

**R10 — §1 and D3: `@traceable` inventory undercounts.**
§1 says "22 `@traceable` import sites"; D3 says "17 `langgraph_workflows/dhg-agents-cloud/src/`
modules + 2 Archive". Walking every `.py` outside worktrees for
`from langsmith import … traceable`: **24 files**, comprising **18** in
`langgraph_workflows/dhg-agents-cloud/src/`, 2 in `langgraph_workflows/Archive/`,
2 in `registry/`, `templates/agent-boilerplate/src/agent.py`, and one the audit never
names: **`website/website_agents_claude/generate_agent_prompts.py`**.

**R11 — D5: "`traced_node` … (15 call sites)" conflates files with call sites.**
`@traced_node(` appears **104 times across 15 files** in
`langgraph_workflows/dhg-agents-cloud/src/`. (D6's medkb figure is correct: 9 sites in
9 files.) A removal-effort estimate built on "15 call sites" is off by ~7×.
Related: MEMORY.md's "85 @traced_node decorators" is also stale — the true total is 113.

**R12 — P10: "12 `medkb_*` families declared".**
Scanning `services/medkb/**/*.py` for `medkb_*` metric-name literals yields **18** distinct
families (budget_exceeded, cache_operations, chunks_corpus, chunks_parent, chunks_total,
documents_corpus_audience, documents_valid, groundedness_score, ingestion_pending,
llm_call_latency_seconds, llm_tokens, query_audit_caller, query_errors,
query_latency_seconds, query_requests, redaction_events, retriever_errors,
retriever_latency_seconds). "0 series in Prometheus" is CONFIRMED — no `medkb_*` name
appears in `/label/__name__/values` at all.

### LOW

**R13 — P11: "`dhg-frontend` and `portage-app`: nothing in 7 days".**
`dhg-frontend` CONFIRMED (0 lines in 7d, absent from the 7d container label values).
`portage-app` is REFUTED — it appears in the 7d label values and
`sum(count_over_time({container="portage-app"}[7d]))` = **5**. Five lines is effectively
nothing, but the literal claim is false.

**R14 — §1 (MISLEADING): Tempo "zero spans **ever** received in 19.5 days of uptime".**
Verified: `dhg-tempo` `State.StartedAt` = 2026-08-15T20:01:30Z, `RestartCount` = 0 →
**19.52 days**, matching host uptime (1,686,983s). `tempo_distributor_push_duration_seconds_count`
= **0** (scraped directly from 10.0.0.251:3200; Prometheus has no tempo job, so the
PromQL route the audit implies returns 0 series for a different reason).
`GET /api/search?limit=5` → `{"traces":[],"metrics":{"completedJobs":1,"totalJobs":1}}`.
So "0 spans in 19.5 days" is CONFIRMED — but the counter resets at process start and the
container was **created 2026-04-06**. Nothing in the evidence covers Apr 6 → Aug 15;
"ever" is inferred, not verified.

**R15 — §4 postgres panel 40: "9 series all 0".**
9 series CONFIRMED, but `pg_locks_count{datname="dhg_registry",mode="accesssharelock"}` = **1**.
Eight are 0, not nine.

**R16 — §4 postgres panel 20: "6 series, all legend-named `dhg_registry`".**
Panel 20 has **two** targets: `pg_stat_activity_count{datname="dhg_registry"}`
(legend `dhg_registry`, 6 series — the fan-out by `state` is CONFIRMED) and
`sum(pg_stat_activity_count)` (legend `Total (all DBs)`, 1 series). 7 series total;
6 share the legend.

**R17 — P1 citation `prometheus.yml:59-66` (vs-engine).** Line 59 is blank, 60 is the
comment; the `vs-engine` job is **60-67** (`job_name` at 61). Off by one.

**R18 — P7/D7 citation `tempo-config.yml:31-42`.** The `metrics_generator:` block starts at
**line 28**; :31 is `source: tempo` inside `external_labels`. The `remote_write` to
`http://prometheus:9090/api/v1/write` with `send_exemplars: true` is at :35-37 and the
processors `[service-graphs, span-metrics]` at :42 — both CONFIRMED. `traces_*` families:
0 names in Prometheus, CONFIRMED.

**R19 — §8: "cAdvisor 61/61 containers".** Right now `docker ps -q | wc -l` = 60 and
`count(count by (name) (container_last_seen{name!=""}))` = **60**. cAdvisor coverage is
100%, which is the load-bearing part, but the number is 60/60 today, not 61/61. G4's
"55 of 61 containers" inherits the same drift.

**R20 — D1 citation `dashboards.yml:12`.** Line 12 of
`observability/grafana/provisioning/dashboards/dashboards.yml` is
`path: /etc/grafana/provisioning/dashboards/json` — the provisioner directory, not a
reference to `dhg-langgraph-traces.json`. The dashboard is provisioned by virtue of being
a file in that directory; there is no per-dashboard line to cite.

---

## C. UNVERIFIABLE

**U1 — "zero drift between repo JSON and live JSON on all 9" (§3).** Grafana
`GET /api/search?type=dash-db` on 10.0.0.251:3001 returns `401 Unauthorized`; anonymous
access is off and reading the admin password would violate the secret-safety rule. No
service-account token is available. The audit could not have verified this either without
the same credential, so I record it as unverified rather than accepting it.

**U2 — "All 38 targets returned HTTP 200 with no error field" via `/api/ds/query` (§4).**
Same 401 gate. I did independently confirm the **count**: `dhg-registry-api.json` has 18
targets and `dhg-postgresql.json` has 20 = 38. Every underlying PromQL I replayed against
Prometheus directly did return `status: success`.

**U3 — "9 dashboards … in live Grafana" (§3).** Confirmed to the extent possible without
auth: 9 JSON files on disk, and `docker exec dhg-grafana ls
/etc/grafana/provisioning/dashboards/json/` lists the same 9. The Grafana dashboard
*registry* itself could not be listed (401).

**U4 — 9.2, why Tempo has zero spans from medkb.** Agreed with the audit: distinguishing
"never invoked" from "silent export failure" needs a medkb query, which is a state change.
Supporting evidence re-derived: 0 `medkb_*` series in Prometheus, and
`OTEL_ENDPOINT` is present on `dhg-medkb-api` (key confirmed present, value not read).

**U5 — 9.5, backups running elsewhere.** Confirmed on g700data1: no backup timer in
`systemctl list-timers --all` (only sysstat, phpsessionclean, fwupd, apt, anacron,
motd-news, update-notifier, tmpfiles-clean, dpkg-db-backup, logrotate, man-db, e2scrub,
fstrim) and no backup entry in the user crontab (5 entries: journal-age, reembed-nulls,
reap-stale-claude-sessions, sync-memory). Whether a backup runs from another user, host,
or Doppler job remains unverifiable, exactly as the audit states.

**U6 — G2 "7 instances".** 7 Postgres data containers confirmed running on g700data1:
portage-db, dhg-eval-db, dhg-registry-db, plane-app-plane-db-1, dhg-medkb-db,
dhg-audio-postgres, dhg-transcribe-db. Whether any performs its own internal dump was not
checked. G10 ("6 of 7 have no exporter") is CONFIRMED: `count by (server) (pg_up)` = 1
(registry-db:5432 only).

**U7 — 9.8, whether the webhook POSTs created incident rows.** Not checked; would require
querying the registry DB. The audit correctly labels this as inferred from code.

**U8 — §3 "MEMORY.md is wrong on two counts".** CONFIRMED for the original lines (the
Observability Stack section still says "Grafana dashboards: core golden signals, Docker
overview, Mission Control, Memreg Daemon" and "OTel → Tempo (85 @traced_node decorators
via tracing.py) + LangSmith @traceable — dual tracing"). But MEMORY.md **lines 41 and 43
already contain the audit's own corrections**, appended during Phase 1. The file is now
self-contradictory, and a reader checking "is MEMORY.md wrong?" today gets both answers.
Flagging so Phase 3 does not treat MEMORY.md as an independent witness for any audit claim.

---

## D. CONFIRMED (re-derived independently)

**Prometheus / targets**
1. 17 active targets, all UP, all `lastError` empty. ✓
2. 18 Prometheus alert rules across 3 groups. ✓
3. 5 dropped docker-sd targets; `dhg-blackbox` among them; cause is the compose-project
   keep regex at `prometheus.yml:154-156` (`dhgaifactory35|dhg-memreg`) — `dhg-blackbox`'s
   project is `dhg-blackbox`. P5 ✓
4. No `tempo` job anywhere in `prometheus.yml`. P2 ✓
5. `prometheus.yml:27-29` is exactly the static `registry-api` job
   (27 `job_name`, 28 `static_configs`, 29 `targets: ['registry-api:8000']`). ✓
6. `prometheus.yml:143-170` is exactly the `docker-sd` job (143 `job_name`, 169 last
   relabel rule). ✓
7. `prometheus.yml:70-74` is the `medkb` job. medkb still targets `dhg-medkb-api:8015` on
   10.0.0.251 and is UP — relocation to dh40801 has not happened. P10 ✓
8. Double scrape CONFIRMED at the series level: `registry_db_connections` returns **2**
   series, one `job="registry-api"`, one `job="docker-sd" container="dhg-registry-api"`.
   Same for `registry_db_errors_total` (2), `histogram_quantile(…registry_write_latency…)`
   (2). `dhg-vs-engine` is likewise both a static `vs-engine` target and a docker-sd
   target. P1 ✓
9. `container_restart_count` — 0 series over 34 days. `ContainerCrashLoop` expr is
   `increase(container_restart_count{name=~"dhg-.*"}[15m]) > 3`. G4/P3 ✓
10. `node_processes_zombies` — 0 series over 34 days. `ZombieProcessesHigh` is
    `node_processes_zombies > 50`. G15/P3 ✓
11. `gpu_utilization` — 0 series; `nvidia-smi` works (RTX 5080, 10% util, 1411MiB).
    G7 ✓
12. `traces_*` — 0 metric names in Prometheus. P7 ✓
13. `portage_http_requests_total` and `portage_http_request_duration_seconds_*` exist
    (40 `portage_*` families total). G8's premise ✓
14. `count by (server) (pg_up)` = 1. G10 ✓

**Tempo**
15. Tempo container up 19.52 days, 0 restarts, `/ready` = ready, build 2.3.1. ✓
16. `tempo_distributor_push_duration_seconds_count` = 0; `/api/search?limit=5` returns
    zero traces. ✓ (scope caveat in R14)
17. `tempo-config.yml` metrics_generator remote_write to Prometheus with
    `send_exemplars: true`, processors `[service-graphs, span-metrics]`. P7 ✓
18. Datasource cross-links to Tempo exist and are inert: `prometheus.yml`
    `exemplarTraceIdDestinations → datasourceUid: tempo` (:13-15), `loki.yml`
    `derivedFields → datasourceUid: tempo` (:13-14), `tempo.yml` `tracesToLogsV2 → loki`.
    P8 ✓

**Loki / Alloy**
19. `dhg-alloy` up 9 days, healthy. `config.alloy:1-2` names promtail's replacement.
    `observability/promtail/promtail-config.yml` exists; no promtail container; no
    promtail service in `docker-compose.yml`. P6 ✓
20. 6 `stage.replace` redaction blocks in `config.alloy` (lines 53, 59, 65, 71, 77, 83). ✓
21. 5 Loki ruler rules. `HighErrorRate` and `ContainerErrorSpike` both **firing**, both
    `severity: warning`, both `activeAt: 2026-08-25T09:16:54Z`. P4 ✓
22. `sum(count_over_time({container="dhg-node-exporter", level="error"}[5m]))` = **2489**
    at check time (audit said 2554 — a live-varying value, same order). P4 ✓
23. `registry/api.py:371-373` is exactly
    `if severity not in ("critical", "high"): skipped += 1; continue` — warning-severity
    alerts create no incident. P4 ✓
24. `loki_store_bytes` = 2,266,176,663 = **2.11 GiB**. §8 ✓

**Registry**
25. `registry/api.py:298` is `@app.get("/metrics", …)`; :301 is a bare
    `return generate_latest()` — no HTTP instrumentation. §4 row 100 / G5 ✓
26. `registry/metrics.py:33-37` defines `Counter("registry_errors", …, ["error_type"])`. ✓
27. `registry/notification_service.py:22` = `from langsmith import traceable`. D2 ✓
28. `registry/timeout_handler.py:18` = `from langsmith import traceable`. D2 ✓
29. No running container has `LANGCHAIN_TRACING_V2` set (all 60 checked, key names only).
    §1 ✓
30. `LANGCHAIN_API_KEY` present on `dhg-registry-api`, `dhg-medkb-api`, `dhg-frontend`;
    `LOKI_URL` on `dhg-registry-api`; `LANGSMITH_PROJECT` and `OTEL_ENDPOINT` on
    `dhg-medkb-api`. D10/D6 ✓ (values never read)

**Dashboards**
31. 9 JSON files in `observability/grafana/provisioning/dashboards/json/`; the same 9 in
    the container at `/etc/grafana/provisioning/dashboards/json/`; `dashboards.yml` points
    there. §3 ✓
32. `git ls-files` on that directory returns **8**; `memreg-daemon.json` is untracked. §3 ✓
33. `observability/grafana/dashboards/` contains exactly `dhg-core-golden.json` and
    `docker-overview.json`, is not the provisioned path. Its `docker-overview.json` has
    6 data panels / 8 targets, and all 8 exprs are unparseable — 6 carry literal
    backslash-escaped quotes (`{image!\"\"}`), 2 use `{image!""}` which is missing the
    `!=` operator. §3 ✓
34. `.claude/commands/observability-engineer.md:48` = "Grafana dashboards (source):
    `observability/grafana/dashboards/`"; :326 repeats the path. §3 ✓
35. `dhg-registry-api` uid, 11 data panels (9 top-level + 2 nested in the collapsed
    "Infrastructure" row 103), 18 targets. §4 ✓
36. Panel 1 `rate(write)+rate(read)` → **0 series**; panel 6
    `registry_write_operations_total + registry_read_operations_total` → **0 series**.
    Both permanently No data, exactly as described (disjoint `operation` label sets). ✓
37. Panel 2 queries `registry_db_errors_total`; `registry_errors_total` is queried by no
    dashboard. ✓
38. Panel 10: `count(rate(read)) + count(rate(write)) + count(rate(db_errors))` = **50**
    series, static legends `Reads`/`Writes`/`Errors`; `rate(registry_read_operations_total[5m])`
    alone = **22** series → 22 lines all named "Reads". ✓
39. Read-latency histogram: top finite bucket `le="1000"` = 1900, `le="+Inf"` = 1909 →
    **0.47%** overflow. Exact. ✓
40. Panel 31 is the only job-pinned panel: `process_resident_memory_bytes{job="registry-api"}`
    returns **1** series. ✓
41. `dhg-postgresql`: 14 data panels, 20 targets, all Prometheus datasource, `datname`
    filter valid, every metric returns data. ✓
42. `pg_stat_activity_count{datname="dhg_registry"}` = **6** series (fan-out by `state`),
    driving panels 1, 5, 20. ✓
43. Panel 41 magnitude mismatch confirmed exactly: `pg_wal_size_bytes` = 83,886,080
    (80 MiB) vs `pg_database_size_bytes{datname="dhg_registry"}` = 1,653,609,263
    (1.54 GiB). ✓
44. Panel 4 `pg_stat_database_deadlocks{…}` is a raw counter with no `rate()`. ✓
45. `dhg-core-golden`: 9 data panels, 10 targets (8 Prometheus + 2 Loki). Of the 8
    Prometheus targets, **6 are dead** — `asr_requests_total` ×2, `asr_latency_seconds_bucket`,
    `gpu_utilization`, `registry_write_latency_ms_bucket`, `registry_read_latency_ms_bucket`.
    The real names have no `_ms`. Exactly 6/8. ✓
46. `vs-engine` (uid `vs-engine-overview`): 10 data panels, 14 targets, **10 dead**.
    Only 5 `vs_*` names exist in Prometheus (`vs_distributions_cached`,
    `vs_generation_duration_seconds_{bucket,count,created,sum}`); **7** distinct queried
    names do not exist (`vs_generations_total`, `vs_repair_weight_total`,
    `vs_diversity_score_bucket`, `vs_ttct_composite_bucket`, `vs_tau_relaxed_total`,
    `vs_items_filtered_total`, `vs_selections_total`). Both numbers exact. ✓
47. `dhg-langgraph-traces`: 5 data panels, 5 targets, all `datasource: tempo`; panel 30
    pins `{ resource.service.name = "dhg-langgraph-agents" }`. 5/5 dead. ✓
48. `dhg-alerting` 16 targets, `docker-overview` 16 targets, `dhg-log-analytics` 14 Loki
    panels — the "16/16" and "14" figures are target counts, and they check out. ✓
49. `/var/lib/grafana/plugins/` inside `dhg-grafana` is empty — no image renderer. P12 ✓

**Deprecation inventory**
50. `templates/agent-boilerplate/src/agent.py:22` = `from langsmith import traceable`. D4 ✓
51. `langgraph_workflows/dhg-agents-cloud/src/tracing.py:118` = `def traced_node(`. D5 ✓
52. `services/medkb/src/medkb/tracing.py:61` = `def traced_node(`, 9 call sites across
    9 node modules. D6 ✓
53. `docker-compose.yml:31` = `orchestrator:` (start of the LangGraph agent block);
    `:228` = `restart: "no"`; `:334` = `LANGSMITH_PROJECT=…`; `:336` = `LANGCHAIN_API_KEY=…`.
    D8 ✓ (values not read)
54. `frontend/src/app/api/langgraph/[...path]/route.ts` exists;
    `frontend/src/app/api/copilotkit/route.ts:11-12` resolves to the LangGraph Cloud URL
    hardcoded at :8-9. D9 ✓
55. No scrape job, alert rule, Loki rule, relabel, or datasource names
    langgraph/langsmith/langchain; port 2026 absent from `observability/`. §6 ✓
56. `langgraph.json` registers **17** graphs; the Pydantic AI prototype
    (`langgraph_workflows/dhg-agents-cloud/src/research_agent_pydantic_prototype.py`) is
    the only first-party `pydantic_ai` file and is not among them. The other 218
    `pydantic_ai` hits are inside `.venv-prototype/lib/python3.12/site-packages/`. §1 ✓

**Cross-host / gaps**
57. dh40801: 6 Langfuse containers up 2 weeks, all healthy.
    `http://10.0.0.179:3000/api/public/health` → **200**; `:3000/metrics` → **404**;
    no node-exporter on :9100, no Prometheus on :9090, no Grafana on :3001; and no
    dh40801 target in the 17. G1 ✓
58. Two cloudflared systemd units active (`cloudflared.service`,
    `cloudflared-portage.service`); no scrape job for them. G9 ✓
59. `dhg-audio-agent` serves Prometheus text on 172.28.0.3:8000/metrics, sits on its own
    network `dhg-audio-agent_audio-net`, and carries no `prometheus.io/*` labels — so it
    is unscrapable by docker-sd. G16 ✓

---

## E. Bottom line for Phase 3

The audit's **structural** conclusions survive: 17 targets all UP, 18 Prometheus + 5 Loki
rules, Tempo has taken zero spans for its whole current run, the registry container is
genuinely double-scraped, `dhg-registry-api` panels 1 and 6 are permanently empty, the
two "error-filled" pages contain no errors, core-golden and vs-engine really are broken on
the metric names claimed, and the renderer/plugin/backup/GPU/Cloudflare/Langfuse-monitoring
gaps are all real.

What must not carry into Phase 3 unchanged: the **inverted Loki coverage numbers** (R1),
the claim that **nothing on g700data1 is wired to Langfuse** (R2), and the stated cause of
the **dead MemregDLQBacklog rule** (R3). Each of those would send a fix at the wrong
target. The `registry_errors_total` "0 series ever" (R4), the missing `ollama.service`
(R5), and the `traced_node` call-site count (R11) would each mislead scoping.
