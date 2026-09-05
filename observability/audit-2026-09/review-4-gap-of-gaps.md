# Review 4 of 4 — Gap-of-Gaps

Adversarial review of `observability/AUDIT-2026-09.md` and the five raw reports. Scope: what the five
audit agents did not look at. Read-only; every finding verified with one command or file read, quoted
below. No repo, container, or Grafana state was changed.

Hosts: g700data1 = 10.0.0.251, dh40801 = 10.0.0.179. Time of review: 2026-09-04 ~04:40 EDT.

---

## CRITICAL — changes a Phase 3 decision

### C1. The alert terminus is a queue nobody reads, and no human is ever notified

No agent asked where an alert ends up for a person.

`observability/alertmanager/alertmanager.yml` has exactly one receiver, one route, no sub-routes:

```
route:
  receiver: 'webhook'
receivers:
  - name: 'webhook'
    webhook_configs:
      - url: 'http://dhg-registry-api:8000/webhooks/alertmanager'
```

There is no email, Slack, PagerDuty, push, or any other human-facing notifier in the estate. Every
alert terminates as a database row. What is in that database:

```
$ curl -s http://10.0.0.251:8011/api/incidents/stats
{"total":124,"by_severity":{"critical":3,"high":121},
 "by_status":{"active":117,"resolved":7},
 "avg_ttd_minutes":null,"avg_ttm_minutes":null,"avg_ttr_minutes":null,
 "top_triggers":[{"trigger_rule":"T13","count":58},{"trigger_rule":"T4","count":48},...]}
```

`avg_ttd/ttm/ttr` are all `null` — no incident has ever been detected-to-acknowledged, mitigated, or
resolved by anyone. The oldest still-active incident dates to **2026-07-24** (42 days):

```
$ curl -s "http://10.0.0.251:8011/api/incidents?status=active&limit=200" | ...
rows: 200  status: {'active': 200}  severity: {'critical': 1, 'high': 199}
oldest: 2026-07-24T05:20:39Z   newest: 2026-08-25T17:23:24Z
```

A **critical, still-active** `[PostgresFatalError] PostgreSQL FATAL/PANIC error detected` has been
open since 2026-08-25T17:23Z.

The synthesis §8 lists "Alertmanager to registry webhook path (verified 38 deliveries)" under **"What
is healthy. Do not rebuild."** Delivery is healthy. Consumption is not: this is the single largest
observability gap in the estate and it is currently classified as a strength. Every dashboard fix in
Phase 3 is downstream of the fact that nothing pages anyone.

Related, also unasked: `SecretLeakDetected` **has** fired — a `secretleak-drill` incident on
2026-08-25T09:07Z (resolved), which is the `p5-seeded-secret.sh` drill (see H4). The audit listed the
rule as "inactive, 0" and never checked history.

### C2. `dhg-remediator` — a live auto-remediation agent, uncharacterized, and structurally blind

`dhg-remediator` appears in exactly one of the five reports, as a container name in a list. It is in
fact the only active consumer of the alert pipeline. Live logs:

```
$ docker logs dhg-remediator --tail 8
[INFO] Approval required for step 3: Stop container (if approved)
[INFO] HTTP Request: POST http://dhg-registry-api:8000/api/incidents/<id>/actions "201 Created"
[INFO] Finished processing incident e42f0107
[INFO] HTTP Request: GET http://dhg-registry-api:8000/api/incidents?status=active&limit=50 "200 OK"
[INFO] HTTP Request: GET http://dhg-registry-api:8000/api/incidents/runbooks "200 OK"
```

Three defects, each verified:

1. **It sees at most 50 of ≥200 active incidents.** It polls `?status=active&limit=50`, page 1 only,
   no cursor. In the last hour it touched exactly **49 distinct incidents**, each **6 times**:
   ```
   $ docker logs dhg-remediator --since 1h | grep -o 'Finished processing incident [0-9a-f]*' | sort -u | wc -l
   49
   $ ... | sort | uniq -c | sort -rn | head -1
   6 Finished processing incident fa866983
   ```
   Because incidents are never resolved, the same 49 rows are reprocessed forever and ≥150 active
   incidents — including anything newer than the page-1 window — are never evaluated at all.
2. **It queues approvals into the void.** "Approval required for step 3: Stop container" is written
   as an incident action. There is no human-facing surface for that queue (same root cause as C1).
3. **It is itself unobserved.** `docker inspect dhg-remediator` shows no `prometheus.io/scrape`
   label, so it has no scrape target, no metrics, no dashboard, and no alert if it dies or wedges.
   The component that acts on alerts is the one component with no telemetry.

### C3. G2 is not "unverified" — it is a documented, undelivered AC of a ship marked complete

The audit lists G2 (no Postgres backup job) as CRITICAL but hedges it in 9.5 ("may run elsewhere").
No agent opened `.claude/ship-state.md`. Its header:

```
status: complete
phase: 7
completed_at: 2026-07-29T08:36Z
feature: Self-hosted Langfuse v3 on dh40801 ...
```

Its acceptance criteria, `### Monitoring, backup, docs`, lines 151-156:

```
50. node-exporter + cadvisor + promtail on dh40801; Prometheus static job on .251; disk alerts 75%/85%
51. Blackbox probe from .251 to the Langfuse health endpoint — the only detector of a dead collector,
    since the client fails silently by design
52. Nightly `pg_dump` of the Langfuse Postgres to .251 (holds orgs, projects, and the API keys prod
    authenticates with)
53. FIX EXISTING GAP: `scripts/backup.sh` is not in any crontab — registry backups are not running
    today. Schedule it alongside the Langfuse backup
```

AC 50, 51, 52, 53 are all still undelivered, verified today:

```
$ crontab -l          # 4 entries: journal-age, reembed-nulls, reap-stale-sessions, sync-memory.
                      # scripts/backup.sh appears in none.
$ ls -la scripts/backup.sh
-rwxr-xr-x 1 swebber64 swebber64 1437 Jul  7 02:52 scripts/backup.sh
$ ls /mnt/4tb/backups
loki-data-pre-p5-2026-08-25.tar.gz     # one Loki tarball. Zero pg_dumps. Nothing else.
$ systemctl list-timers --all | grep -i backup     # nothing
$ timeout 3 bash -c '</dev/tcp/10.0.0.179/9100'    # closed — no node-exporter on dh40801 (AC50)
$ curl -o /dev/null -w '%{http_code}' http://10.0.0.179:3000/metrics    # 404 (AC51 context)
```

Mechanism, which matters more than the fact: the Phase 3 task list
(`.claude/ship-state.md:256-283`) contains **only** A1-A6 and B1-B5. ACs 50-56 were dropped between
Phase 1 and Phase 3 in a ship whose own §24 heading reads "**Full scope — nothing deferred**" and
whose `kb_findings` line warns "Active correction patterns — workflow-violation INCREASING and
repeated scope-cutting (three instances this session): do NOT cut scope."

This resolves audit 9.5 (backups do not run, anywhere, on this host) **and** reframes G1: Langfuse
being unmonitored is not a newly discovered gap, it is a written, approved, undelivered commitment
from five weeks ago. Phase 3 should treat ACs 50-53 as re-opened work with existing sign-off, not as
new proposals needing fresh approval.

---

## HIGH — adds a gap at HIGH or above

### H1. Doppler was never consulted, and it is the answer to two of the audit's own open items

Audit 9.4: "`docker-compose.override.yml` env keys could not be grepped (secret-safety hook)".
Audit 9.3: Phase 4 "must solve login without exposing the password (e.g. a Grafana service account
token stored in Doppler)". Doppler is installed, authenticated, and holds a project named for exactly
this stack — no agent ran `doppler`:

```
$ doppler projects
dhg-monitoring | Observability stack - Grafana, Prometheus, Loki, Tempo, Alertmanager
$ doppler secrets --project dhg-monitoring --config prd --only-names
DOPPLER_CONFIG, DOPPLER_ENVIRONMENT, DOPPLER_PROJECT, GF_SECURITY_ADMIN_PASSWORD,
GRAFANA_PORT, PROMETHEUS_PORT
$ doppler configs --project dhg-monitoring     # dev last fetch 2026-04-26T18:25Z
```

Two consequences. (a) Key-name enumeration was available all along without violating secret-safety —
9.4 did not need to stay open. (b) The `dhg-monitoring` project holds three keys and has not been
fetched since 2026-04-26: the observability stack is **not** run under `doppler run`, so the Grafana
admin password in `docker-compose.override.yml` is the live one and the Doppler copy is stale. Any
Phase 3 plan that assumes Doppler governs observability secrets is wrong.

### H2. Prometheus, Alertmanager, Loki, Tempo and cAdvisor are bound 0.0.0.0 with no authentication

No agent ran `docker port` on the observability containers or tested unauthenticated access.

```
$ docker port dhg-prometheus     9090/tcp -> 0.0.0.0:9090
$ docker port dhg-alertmanager   9093/tcp -> 0.0.0.0:9093
$ docker port dhg-loki           3100/tcp -> 0.0.0.0:3100
$ docker port dhg-tempo          3200 -> 0.0.0.0:3200, 4317 -> 0.0.0.0:4317, 4318 -> 0.0.0.0:4318
$ docker port dhg-cadvisor       8080/tcp -> 0.0.0.0:8080
$ docker port dhg-blackbox       9115/tcp -> 127.0.0.1:9115      # the only one done correctly
```

Verified reachable with no credentials:

```
prom /api/v1/status/config: 200      # returns the entire scrape config
alertmanager /api/v2/status: 200     # silences are writable on this same unauthenticated API
loki /loki/api/v1/labels: 200        # all log labels; /query_range reads log bodies
cadvisor /metrics: 200
```

Grafana is the only component with auth (`GF_SECURITY_ADMIN_USER`/`GF_SECURITY_ADMIN_PASSWORD`
present, no `GF_AUTH_ANONYMOUS_*` key, so anonymous is off — audit 9.3's premise is correct). But
Grafana's auth is cosmetic while Prometheus and Loki serve the same data unauthenticated on the LAN
next door, and `p5-baseline.sh` already demonstrates that Alertmanager silences can be created and
deleted over that open API. Tempo's OTLP 4317/4318 on 0.0.0.0 accepts spans from any LAN host.

### H3. The whole stack is pinned roughly two years behind, and no agent recorded a version

```
prometheus  2.48.0   (via grafana container -> /api/v1/status/buildinfo)
tempo       2.3.1    (via /status/version)
grafana     10.2.0   (via /api/health, commit 895fbafb7a)
```

All three are ~Nov 2023 releases. This is a Phase 3 input, not trivia: the plan to install
`grafana-image-renderer` (P12), to use newer panel types, or to adopt anything from the Grafana 11/12
alerting or Loki 3.x query surface runs into a 10.2 ceiling, and a version bump is a different-sized
change than a dashboard edit. Note the version skew inside the stack too — Loki is 3.7.6 (per commit
`dd7a92e`) while Grafana is 10.2.

### H4. `observability/scripts/` — an existing verification harness, zero mentions in five reports

```
observability/scripts/p5-baseline.sh
observability/scripts/p5-seeded-secret.sh
observability/scripts/baselines/floor-pre.json
observability/scripts/baselines/labels-pre.json
```

`grep -l 'p5-baseline\|floor-pre\|labels-pre\|p5-seeded' observability/audit-2026-09/* observability/AUDIT-2026-09.md`
returns nothing. What was missed:

- **`p5-baseline.sh` is the only automated end-to-end alert-path test that exists.** Step 3 creates
  and expires an Alertmanager v2 silence and fails hard if the round-trip breaks. Phase 3 should
  extend this, not invent a new verification approach.
- **It also performs the Loki store backup** (`docker run --rm -v dhgaifactory35_loki_data:/loki:ro
  ... tar czf /backup/loki-data-pre-p5-<date>.tar.gz`, min-size gate 100 MB). That explains the one
  file in `/mnt/4tb/backups` and confirms it was a manual one-shot, not a schedule.
- **`baselines/labels-pre.json` is a hard 2026-08-25 baseline of the Loki label space** — 22
  `container` values, 22 `compose_service`, 5 `compose_project`, 7 `level`. The audit's P11 stream
  analysis ("26 of 42 dhg-* containers have no Loki stream in 24h") should have been a diff against
  this file. Doing that diff is what surfaces H5 below.
- **`baselines/floor-pre.json`**: `{"floor_29d_registry_api": 644917, "at": "2026-08-25T08:09:25Z"}`
  — a retention floor the P5 program is meant to defend. Nobody checked whether it still holds.
- **`p5-seeded-secret.sh`** is the drill that produced the resolved `SecretLeakDetected` incident of
  2026-08-25T09:07Z, which is the evidence that rule works (see C1).

### H5. Loki's stream namespace is one third non-DHG, and includes ephemeral test containers

The audit framed the log universe as "42 dhg-* containers". The live label space is wider:

```
$ curl -s 'http://10.0.0.251:3100/loki/api/v1/label/container/values'   # 38 values
26 x dhg-*
 5 x plane-app-{admin,plane-db,space,web,worker}-1
 4 x portage-{api,db,graph,rembg}
 3 x portage-e2e-{api,app,db}-1        <-- E2E test-harness containers
```

`portage-e2e-*` are ephemeral test containers writing into the production log store whose retention
the P5 program governs; they are not in the 2026-08-25 baseline (H4), so they arrived since. Alloy
has no container filter (`config.alloy:7-10`, correctly noted by A4 as "keep-all"), so any container
started on this host by any project silently becomes a Loki tenant. P11 measured only the silence and
never the uninvited ingress. This is a scoping decision Phase 3 has to make explicitly — the audit
never surfaced that there is one.

### H6. `dh40801/docker-compose.langfuse.yml` is in this repo and no agent opened it

```
$ grep -n 'docker-compose.langfuse\|LANGFUSE_SELFHOST_HANDOFF\|dh40801/' observability/audit-2026-09/*.md observability/AUDIT-2026-09.md
(no matches)
$ ls -la dh40801/
-rw-rw-r-- 1 swebber64 swebber64 7470 Jul 28 07:29 docker-compose.langfuse.yml
```

Seven services: `dhg-langfuse-web` (langfuse/langfuse:3), `-worker`, `-postgres` (postgres:17),
`-clickhouse` (25.12), `-redis` (redis:7), `-minio` (chainguard), `-minio-init`. **Zero
`prometheus.io/*` labels anywhere in the file** — which confirms G1's cause is omission at authoring
time, and hands Phase 3 the exact file and the exact five containers (postgres, clickhouse, redis,
minio, worker) that need targets or a health probe. Also unopened: `LANGFUSE_SELFHOST_HANDOFF.md`,
which is one of only two files in the repo still referencing `cloud.langfuse.com` (the other is
`.claude/ship-state.md`, which already documents the handoff's claim as false at line 32).

---

## MEDIUM — corrects a fact in the audit

### M1. 9.9 RESOLVED — Portage traces ARE landing in Langfuse, verified today

Queried with `portage-api`'s own keys read from the container env and never printed:

```
$ curl -s -u "$PUB:$SEC" "$LANGFUSE_BASE_URL/api/public/traces?limit=3"
meta: {'page': 1, 'limit': 3, 'totalItems': 252, 'totalPages': 84}
 2026-09-02T16:28:17Z  scan-refine  userId=c19b95dc-0d37-4d4b-9c00-fe86861c7034
 2026-09-01T19:54:24Z  scan-refine  userId=c19b95dc-...
 2026-09-01T19:35:39Z  scan-refine  userId=c19b95dc-...
```

252 traces since the 2026-07-27 cutover (~6/day), newest two days old. Two corrections fall out:

- **`userId` is a raw UUID, not the email** that ship Workstream E specified ("Langfuse user id =
  `req.user.email`, plus `tier` + internal UUID as metadata"). Partially delivered.
- **The ship's own liveness signal no longer exists.** Gate B3 was verified by a
  `"Langfuse tracing enabled"` startup log line. `docker logs portage-api | grep -ic langfuse` = **0**
  on the current 31-hour-old container, yet traces flow. So the only human-checkable proof that LLM
  tracing is alive is a manual API call — which is exactly why G1 (no collector-death detector) is
  CRITICAL, and the audit could not tell whether traces were flowing at all.

### M2. 9.1 and 9.7 SETTLED — A4 is right on both counts

```
$ curl -s http://10.0.0.251:9090/api/v1/targets
activeTargets: 17   droppedTargets: 5   health: {'up': 17}
by job: alloy 1, blackbox-http 2, blackbox-https 1, cadvisor 1, docker-sd 3, memreg 1, loki 1,
        medkb 1, node-exporter 1, portage-api 1, postgres 1, prometheus 1, registry-api 1, vs-engine 1
$ curl -s http://10.0.0.251:9090/api/v1/rules
groups: 3   rules: 18   (dhg-infrastructure 14, dhg-logs 3, dhg-memreg 1)
```

17 active targets across 14 job labels; A1/A3's 18 is wrong. 18 Prometheus rules; A1's 17 is wrong.
The prompt's "13 scrape jobs" is also wrong (14 job labels), as the audit already suspected.

### M3. G6 is overstated — host `ollama.service` is inactive AND disabled

```
$ systemctl is-active ollama   -> inactive
$ systemctl is-enabled ollama  -> disabled
```

The blackbox `http_2xx`-with-no-body-match weakness is real and worth fixing, but the failure mode it
would miss (host ollama seizing :11434 on boot) cannot currently occur — the unit will not start.
G6 belongs at MEDIUM, not HIGH, and the fix is a probe hardening rather than an incident risk.

### M4. Retention and cardinality were never asked

```
$ curl -s http://10.0.0.251:9090/api/v1/status/flags
storage.tsdb.retention.time = 30d
storage.tsdb.retention.size = 0B          <-- no size cap at all
$ curl -s http://10.0.0.251:9090/api/v1/status/tsdb
numSeries 27480   chunkCount 106393
top by series: container_network_advance_tcp_stats_total 6039   <-- 22% of the entire TSDB
               loki_boltdb_shipper_table_sync_latency_seconds_bucket 636
               portage_http_request_duration_seconds_bucket 387
$ docker run --rm -v ...prometheus_data:/p:ro -v ...loki_data:/l:ro -v ...tempo_data:/t:ro alpine du -sh /p /l /t
3.1G  /p     2.2G  /l     40.0K  /t
$ df -h / /mnt/4tb   -> 15% and 15%      $ df -i / /mnt/4tb -> 3% and 8% inodes
```

Findings: (a) one cAdvisor metric, `container_network_advance_tcp_stats_total`, is 22% of the head
series and is queried by no dashboard — a free 6k-series reduction via `metric_relabel_configs`.
(b) There is no `retention.size` cap; only the 30d time cap bounds Prometheus disk. (c) Tempo's data
volume is **40 KiB**, independently corroborating "zero spans ever". (d) Disk and inode headroom is
ample, so the P5 `LokiStoreGrowth >20 GB` alert is nowhere near threshold and the 2.2 GiB store is
not a pressure point — the audit implied urgency it does not have. Note CLAUDE.md says the 1.9 TB
disk is "11% used"; it is 15%.

### M5. `.claude/commands/prometheus-configuration.md` is materially stale and was never opened

The audit checked `observability-engineer.md` only. `prometheus-configuration.md:17` says the file
covers "**the five established scrape targets**" and hardcodes exactly five job blocks (prometheus,
registry-api, postgres, node-exporter, cadvisor). The live config has 14 job labels plus docker-sd
service discovery. Line 320 also instructs `curl -s http://localhost:9090/api/v1/targets`, against
the standing "use 10.0.0.251 not localhost" rule. Any future agent invoking this command is
misdirected.

Separately, the two command files contradict each other on the dashboard source of truth:
`grafana-dashboards.md:25,463-464` names the **live** tree
(`observability/grafana/provisioning/dashboards/json/`), while `observability-engineer.md:48,326`
names the **dead** tree (`observability/grafana/dashboards/`). A2 flagged only the second; the
disagreement between the two, not just the staleness of one, is what makes this confusing to fix.

### M6. Incident API count drift — the audit inferred from code and never queried

```
/api/incidents/stats                        -> total 124, active 117
/api/incidents?status=active&limit=200      -> 200 rows, all status=active
/api/incidents?limit=500                    -> 0 rows
```

The stats endpoint undercounts active incidents by at least 83, and the list endpoint silently
returns an empty array above some limit rather than erroring or capping. This is the project's
documented serializer/count-drift failure mode (`feedback_serializer_drift.md`) sitting in the exact
API that Phase 3 will build an incident surface on top of. Audit 9.8 flagged "DB not queried" and
left it; the query changes both the count and the credibility of the stats endpoint.

### M7. Grafana's own log was never read, and there is a 500 on one flagged dashboard

A3 replayed panels through `/api/ds/query` and concluded "All 38 targets returned HTTP 200 with no
error field" and, for `dhg-postgresql`, "No errors of any kind." Nobody read Grafana's log:

```
$ docker logs dhg-grafana --since 24h | grep -iE 'level=error|level=warn'
t=2026-09-04T05:44:04Z level=error msg="Failed to get annotations" error="context canceled"
  ... method=GET path=/api/annotations status=500
  referer="http://10.0.0.251:3001/d/dhg-registry-api/dhg-registry-api?from=now-1h&refresh=30s"
t=2026-09-04T08:13:32Z level=error msg="Failed to parse user ID" error="identifier is not initialized"
t=...  level=warn msg="Could not render image, no image renderer found/installed"   (x3)
```

Honest reading: `context canceled` on `/api/annotations` most likely means the browser navigated away
mid-request, not a server defect — I am not claiming a bug. The real finding is methodological:
A3's replay exercised only the datasource-query path. Annotation queries, alert-state queries,
template-variable queries and panel rendering were never exercised by any agent, and a 500 on the
flagged dashboard's own request stream went unseen. Phase 4's "did it actually render" verification
needs Grafana's log in the loop, not just `/api/ds/query`.

---

## LOW — informational

### L1. Datasource health is fine — rule this hypothesis out

From inside `dhg-grafana`, all three provisioned datasources answer:
`prometheus:9090/api/v1/status/buildinfo` 200, `loki:3100/ready` "ready",
`tempo:3200/status/version` "tempo, version 2.3.1". Provisioned uids are `prometheus`, `loki`,
`tempo` and all resolve. No datasource-level failure exists; the broken dashboards are broken on
metric names and empty stores, exactly as A2 said.

### L2. Timezone and clock skew — not a problem, question closed

Host is `America/New_York` (EDT), `System clock synchronized: yes`, `NTP service: active`. All
containers report UTC (`dhg-grafana`, `dhg-prometheus`, `dhg-registry-api` all `08:39:53 UTC` against
host `04:39:53 EDT` — consistent, zero skew). Dashboards inherit browser time, so panels read ET for
Stephen. No Prometheus staleness risk from clock drift. Nobody checked; the answer is clean.

### L3. Container count is 60, not 61

`docker ps -q | wc -l` = **60**. The synthesis §8 credits cAdvisor with "61/61 containers".

### L4. Nobody asked who else runs on this host, or whether that is intended

The audit scoped itself to `dhg-*` and Langfuse. The host actually runs, unscraped and unquestioned:
`plane-app` (13 containers, 5 of them logging into Loki), `dhg-transcribe`
(api-server/worker/db/minio/qdrant/redis, project `dhg-transcribe`), `dhg-research-eval-viewer`,
`pgadmin`, `dhg-nlp-enrichment` / `dhg-nlp-processor` / `dhg-preprocessor` / `dhg-qc-service`,
`dhg-graphify-wiki`, `dhg-open-terminal`, `dhg-pdf-renderer`, `dhg-docs`, and `dhg-review` — the last
being a bare `nginx:alpine` with **no compose project label at all** (`docker inspect` returns empty
for `com.docker.compose.project`), i.e. a hand-started container nobody owns. Each of these names
appears at most twice across 1,821 lines of audit, always incidentally. Whether they should be
scraped, or explicitly declared out of scope, is a Phase 3 scoping question that no agent raised.

### L5. The prompt's "85 @traced_node decorators" — flag, do not reconcile

The audit found `traced_node` at 15 call sites in `langgraph_workflows/.../tracing.py` consumers
(D5) and 9 in `services/medkb` (D6) = 24. `.claude/ship-state.md:13` independently records a
CodeGraph scan finding "`from tracing import traced_node` in exactly 14 modules". Three independent
counts (85, 24, 14) measure three different things (decorated nodes vs. call sites vs. importing
modules). The "85" in MEMORY.md is unsourced and should be corrected or dropped rather than
reconciled — it is the kind of stale number that keeps re-entering prompts as an assumption.

### L6. The Mac leg of the memreg capture pipeline is unobserved — inferred, not verified

G3 correctly notes `memreg_dlq_depth` and `memreg_captures_total` are declared but never populated.
Not asked: memreg hooks also run on the Mac workstation (per global CLAUDE.md), posting to
`10.0.0.251:8011` over the LAN, and fail silently off-LAN by design. With both metric families empty
there is no signal for either leg — a Mac session that captures nothing for a week is
indistinguishable from one that captures normally. I could not verify Mac-side behaviour from this
host, so this is an inference from the metric gap, flagged as such.

---

## Summary of corrections to the synthesis

| Audit item | Correction |
|---|---|
| §8 "Alertmanager to registry webhook path — healthy, do not rebuild" | Delivery is healthy; **consumption is the largest gap in the estate** (C1) |
| 9.5 backups "may run elsewhere" | Verified: they run nowhere; documented as a known gap since 2026-07-21 (C3) |
| 9.8 "whether the 38 POSTs created incident rows (DB not queried)" | ≥200 active rows, oldest 42 days, zero ever acknowledged (C1, M6) |
| 9.9 "whether Portage traces are landing right now" | Yes — 252 traces, newest 2026-09-02 (M1) |
| 9.1 / 9.7 target and rule counts | 17 targets / 14 jobs / 18 rules; A4 correct (M2) |
| 9.4 "override env keys could not be grepped" | Doppler key-name enumeration was available and unused (H1) |
| G1 Langfuse unmonitored | Not a new gap — an undelivered, signed-off AC (C3, H6) |
| G6 host ollama | Unit is inactive and disabled; downgrade to MEDIUM (M3) |
| §8 "cAdvisor 61/61 containers" | 60 containers running (L3) |

## Sources of truth the audit never opened

`observability/scripts/` (2 scripts + 2 baselines) · `dh40801/docker-compose.langfuse.yml` ·
`LANGFUSE_SELFHOST_HANDOFF.md` · `.claude/ship-state.md` and `_v10`/`_v11` ·
`.claude/commands/prometheus-configuration.md` · `.claude/commands/grafana-dashboards.md` ·
`docs-site/docs/monitoring.md` and `docs-site/projects/portage/monitoring.md` (which document 8
`portage_*` metrics and claim a prebuilt Portage Grafana dashboard exists in the Portage repo at
`observability/grafana/portage-dashboard.json` — relevant to G8, and not present on this host) ·
Doppler (`dhg-monitoring` project) · the Langfuse public API · the registry incident API ·
Grafana's own log · `docker port` / `systemctl` / `nvidia-smi` / `timedatectl` on the host.
