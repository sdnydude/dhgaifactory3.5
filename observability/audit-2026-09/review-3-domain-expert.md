# Review 3 — Observability Domain Expert (SRE practice)

Adversarial review of `observability/AUDIT-2026-09.md` and the current design. Read-only: no repo config, container, or Grafana state was changed. All live claims below come from `GET` against 10.0.0.251:9090 / :9093 / :3100 / :3001 and 10.0.0.179:3000 on 2026-09-04.

**Posture: the audit is factually careful and materially incomplete on the alerting side. Its biggest single miss is that nothing watches the alerting pipeline itself. Its biggest directional risk is proposing to retune a metric that should be deleted.**

---

## 0. Contradictions from §9, settled

| Item | Ruling | Evidence |
|---|---|---|
| 9.1 target count | **17**. A4 correct; A1/A3 wrong. | `/api/v1/targets?state=active` → 17 |
| 9.7 rule count | **18** Prometheus rules. A4/A5 correct; A1 wrong. | `/api/v1/rules` → 14 + 3 + 1 |

One more correction the audit did not catch: §4 says the registry read histogram is `[1..5000] ms`. It is not. **Read is `[1,5,10,25,50,100,250,500,1000]`; write is `[…,2500,5000]`** — two different bucket sets (`registry/metrics.py:12,18`, confirmed live). The audit conflated them.

---

## 1. Golden signals and alert quality

### 1.1 CRITICAL — the alerting pipeline is itself unmonitored, and the audit never noticed

`up{job=~".*alertmanager.*"}` returns **0 series**. Alertmanager is not a Prometheus scrape target. It is nonetheless serving metrics: `curl 10.0.0.251:9093/metrics` returns `alertmanager_notifications_failed_total{integration=...,reason=...}` right now.

Consequence: the entire incident path — Prometheus → Alertmanager → `dhg-registry-api:8000/webhooks/alertmanager` → incident row — has **no failure signal at any hop**. The audit's confidence in this path ("Webhook delivery to registry-api verified (38 POST 200)", §1) is a point-in-time log inspection, not a monitor. If the webhook starts returning 500, or Alertmanager wedges, nothing fires and nothing is dropped visibly.

Available today, unused, all scraped or one line from being scraped:

- `alertmanager_notifications_failed_total` (needs an Alertmanager scrape job — does not exist)
- `prometheus_notifications_dropped_total` — **scraped, value 0, no alert**
- `prometheus_rule_evaluation_failures_total` — **scraped, 3 rule_groups, all 0, no alert**
- `prometheus_notifications_alertmanagers_discovered` — scraped, no alert on `== 0`
- `loki_prometheus_notifications_errors_total`, `loki_ruler_config_last_reload_successful` — **scraped, no alert**

Note the audit's §5 P4 and the cited registry insight refer to `cortex_prometheus_notifications_dropped_total`. That metric name **no longer exists** on Loki 3.7.6 — the prefix is now `loki_prometheus_*` (verified: `cortex` → 0 matching names out of 1582 families). Any Phase 3 work that copies the old name forward will build a dead rule, exactly like the three it is trying to fix.

This is CRITICAL under the stated rubric because the audit's direction — add rules, add dashboards — makes the estate *less* safe while delivery is unwatched: more silent alerts, same silence. Google SRE Workbook ch.5 ("Alerting on SLOs") and ch.16 assume the notification path is itself monitored; Prometheus's own operational guidance treats `rule_evaluation_failures` and `notifications_dropped` as first-tier self-monitoring.

### 1.2 HIGH — four-value severity taxonomy, and `medium` is an accidental black hole

Live severities: `critical` (3), `high` (8), `medium` (2), `warning` (2) on the Prometheus side; Loki adds `critical` (2), `warning` (3). Four tiers, no written definition of what separates `high` from `medium` or `medium` from `warning`.

`registry/api.py:371-373` skips incident creation for anything not in `("critical","high")`. The audit flags this only for `warning`. **It also silently drops `medium`** — and `medium` is the severity on `DataDiskHigh` (`/mnt/4tb` > 80%) and `ZombieProcessesHigh`. A data-disk-filling precursor therefore produces no incident row. That is a real defect the audit missed.

**The drop itself is correct design, not a flaw.** SRE Book ch.6 and Workbook ch.5 are explicit: an alert that requires no human action should not create a ticket or page. `ContainerHighCPU > 90% for 10m` is not actionable on a box that runs LLM inference; it belongs on a dashboard, not in a rule file. The right fix is not to widen the webhook filter — it is to collapse to **two tiers** (`page` / `ticket`), delete the non-actionable rules outright (`ContainerHighCPU`, `ContainerHighMemory`), and promote `DataDiskHigh` to `high` so it lands.

### 1.3 HIGH — zero of 23 rules carry a runbook annotation

Live `/api/v1/rules` shows annotations are `['summary']` on 15 rules and `['description','summary']` on 3. **No rule has `runbook_url`.** The Loki rules are the same. SRE Workbook ch.8 treats the runbook link as part of the alert definition, not documentation debt — the alert exists to route a human to a procedure. Several of these rules already *contain* their runbook inline in the `description` (`LokiDown`, `AlloyDown`, `OllamaDown` in its summary), which proves the operator knows the procedure and has nowhere structured to put it. The audit does not mention runbooks anywhere.

### 1.4 Symptom vs cause: the estate has no symptom alerts on anything that serves traffic

Classifying the 23 rules:

- **Symptom-based (7):** `RegistryApiDown`, `PortageApiDown`, `OllamaDown`, `LokiDown`, `PostgresFatalError`, `NoLogsFromRegistryApi`, `SecretLeakDetected`.
- **Cause / saturation-based (16):** everything else — memory, swap, both disks, connections, zombies, container CPU/memory/restarts, DLQ depth, store growth, target-down, log-line counts.

All seven "symptom" alerts are **binary liveness**. Not one rule anywhere in the estate alerts on **latency or error ratio**. SRE Book ch.6 ("Monitoring Distributed Systems", the four golden signals) puts latency and errors first; this estate alerts on saturation and availability only. A service that is up and returning 500s at 40% is invisible.

This reframes the audit's G8. Portage is the *only* service that can support a real symptom alert today — `portage_http_requests_total{route,status_code}` and `portage_http_request_duration_seconds_bucket` are live and correctly named (verified in `/api/v1/label/__name__/values`). The audit ranks G8 fourth in HIGH, below infra gaps. **It should be first**, because it is the only place where correct practice is currently achievable without writing instrumentation.

### 1.5 `absent()` — used zero times in Prometheus; and the naive fix would be wrong

`absent()` appears **nowhere** in `alerts.yml`. `absent_over_time` appears once, correctly, in `loki/rules/fake/alerts.yml:39` (`NoLogsFromRegistryApi`).

Should the three dead rules get `absent()`? **Only one of them, and the distinction matters:**

- `memreg_dlq_depth` — **yes.** The metric is declared and *should* be populated; `absent(memreg_dlq_depth)` correctly detects "the memreg pipeline stopped reporting", which is the actual failure mode. Every `auto-*-capture` rule depends on it.
- `container_restart_count` — **no.** cAdvisor v0.51 does not export this name at all; `absent()` would fire permanently, forever. See 1.6.
- `node_processes_zombies` — **no.** The processes collector is disabled by choice. `absent()` fires permanently. Delete the rule (see 8.3).

The rule an SRE would write down: `absent()` guards a metric that exists and might vanish. It is not a repair for a wrong metric name. A Phase 3 that adds `absent()` to all three creates two permanently-firing alerts and teaches the operator to ignore the channel.

### 1.6 HIGH — G4 is graded CRITICAL but is a one-line expression fix

The audit says `ContainerCrashLoop` is dead and "55 of 61 containers have no death signal at all", severity CRITICAL. The premise is right; the conclusion overstates by a lot.

cAdvisor exports `container_start_time_seconds` — **42 live `dhg-*` series** confirmed. The standard crash-loop expression is:

```
changes(container_start_time_seconds{name=~"dhg-.*"}[15m]) > 3
```

That is a working detector available today with zero new components. The gap is a wrong metric name in one rule, not an absent capability. Keeping it as a CRITICAL alongside "Langfuse host unmonitored" flattens two very different amounts of work.

### 1.7 MEDIUM — `LokiStoreGrowth` depends on an unguarded hand-rolled gauge

`loki_store_bytes` is **not a Loki metric**. It carries `job="node-exporter"` and comes from a textfile: `/host/mnt/4tb/observability/textfile/loki_store.prom` (confirmed via `node_textfile_mtime_seconds`). If whatever writes that file stops, the series goes stale and then absent, and `LokiStoreGrowth` silently never fires again.

`node_textfile_mtime_seconds` and `node_textfile_scrape_error` are both already scraped and both unalerted. A textfile-collector gauge without a staleness guard is a textbook silent-failure. Audit does not mention it.

### 1.8 MEDIUM — Alertmanager routing was never opened

`observability/alertmanager/alertmanager.yml` appears in no finding in the audit. Two problems in 23 lines:

- The `inhibit_rule` (`severity=critical` inhibits `severity=warning`, `equal: [alertname, service]`) is a **no-op**. A single alertname never emits two severities, so the equality condition can never be satisfied by two different rules. Inhibition exists to let a coarse alert suppress fine ones (SRE Book ch.6 on alert fan-out); this one suppresses nothing.
- The real fan-out is unaddressed. When registry-api dies, **three alerts fire for one event**: `RegistryApiDown` (critical) plus `PrometheusTargetDown` twice — once for `job="registry-api"` and once for `job="docker-sd"`, because the container is scraped by both (§2.1). They land in different `group_by: [alertname, service]` groups (docker-sd targets carry no `service` label), so they arrive as separate webhook POSTs and become **three incident rows for one outage**. The audit identifies the double scrape (P1) and the webhook (P4) separately and never connects them.

---

## 2. Scrape design

### 2.1 The audit is right that the double scrape is a defect. It does not say which path should win, and the answer is not the obvious one.

Proof of the collision, live: `registry_read_latency_count` returns two series with the identical value `1909` — `{job="registry-api", instance="registry-api:8000", service="registry-api"}` and `{job="docker-sd", instance="172.20.0.21:8000", container="dhg-registry-api"}`.

The instinct is to keep docker-sd (self-maintaining, label-driven). **That is wrong for this estate, for a reason the audit misses: docker-sd targets are `IP:port`.** Every container recreate assigns a new IP, which mints a brand-new `instance` series and orphans the old one. Any dashboard, silence, or recording rule keyed on `instance` breaks on every `docker compose up -d`. Static targets are DNS names and are stable across recreates.

Two further nails:

- docker-sd's `keep` regex (`prometheus.yml:154-156`) is `dhgaifactory35|dhg-memreg`. Portage lives in a different compose project, so it *cannot* be discovered and already needs a static job (`prometheus.yml:79-88`). Same for dh40801 when that is wired. So the "no config edits" benefit is already not being realised — you edit `prometheus.yml` either way. The regex itself was hand-edited once to add `dhg-memreg`.
- docker-sd already loses to the static path on labels: `service` exists on 8 targets (all static), `container` on 4 (all docker-sd), and **the two sets are disjoint** — no target carries both.

**Recommendation: one convention — static jobs with an explicit `service` label; delete the `docker-sd` job.** Seventeen targets across two hosts and two compose projects does not justify service discovery. This also fixes P5 (`dhg-blackbox` unscraped because it fails the project regex) for free, and removes the triple-alert fan-out in 1.8.

The counter-argument to state honestly: if the estate grows past ~30 services or containers start being created dynamically, static breaks down and docker-sd wins. That is not this estate, and adopting SD *now* to serve a future that Pydantic AI (one or two long-lived API containers) does not obviously bring is over-building.

### 2.2 HIGH — label hygiene cannot support the audit's implied per-service dashboard template

Live label values:

- `service` → `cadvisor, node-exporter, ollama, portage-api, prometheus, registry-api, registry-db, vs-engine` (8)
- `container` → `dhg-memreg-agent, dhg-registry-api, dhg-session-logger, dhg-vs-engine` (4)
- **`medkb`, `loki`, and `alloy` jobs carry neither** — `prometheus.yml:70-74,172-179` declare no `labels:` block at all.

A `$service` template variable would therefore silently omit medkb, Loki, and Alloy; a `$container` variable would omit almost everything. The audit's §3 dashboard direction assumes a per-service template is reachable. It is not, until §2.1 is settled and every static job gets a `service` label. That ordering matters for Phase 3: **label convention is a prerequisite for the dashboard work, not a parallel task.**

`instance` is likewise inconsistent by construction (DNS name for static, container IP for SD, probe URL for blackbox). That is fine — `instance` should identify the target, not the service — but it means `instance` is not a usable dashboard variable across jobs.

---

## 3. Histograms

### 3.1 CRITICAL (direction) — the audit proposes retuning buckets on a metric that should not exist

The audit's §4 flags "read histogram top finite bucket 1000ms with 0.47% overflow to +Inf, p99 unreliable" and the framing invites Phase 3 to add bucket boundaries. **Do not.** Three reasons:

1. **The diagnosis is imprecise.** The +Inf overflow is not what makes p99 unreliable. Live cumulative counts: `le=500 → 1872`, `le=1000 → 1900`, `+Inf → 1909`. p99 of 1909 observations = the 1890th, which falls **inside the 500→1000 ms bucket** and is linearly interpolated across a 500 ms-wide bucket while p50 is under 5 ms. The error bar on p99 is ±250 ms. Adding a 2500/5000 bucket (matching the write histogram) fixes nothing; the tail resolution problem is between 100 and 1000.

2. **The metric violates Prometheus naming convention twice.** `registry/metrics.py:9-19` declares `registry_write_latency` / `registry_read_latency` with docstrings saying "in milliseconds". Prometheus naming docs require base units (seconds) and a unit suffix (`_seconds`). These have neither. `dhg-registry-api.json` compensates with `unit: "ms"` on the panels, which locks the mistake in.

3. **It measures the wrong thing.** These are *database call* latencies. The audit's own G5 says the registry has no HTTP golden signals and §4 row 100 correctly notes `registry/api.py:298` is a bare `generate_latest()`. Retuning DB buckets produces a better-looking panel that still cannot answer "is the API slow for a caller".

**The correct move is deletion-and-replacement, not tuning.** Portage already demonstrates it in this estate: `portage_http_request_duration_seconds_bucket` — base unit, correct suffix, labelled by route and status. Instrument the registry the same way (`prometheus-fastapi-instrumentator` or equivalent), keep or drop the DB histograms as an internal detail, and use the standard `[.005,.01,.025,.05,.1,.25,.5,1,2.5,5,10]` second buckets rather than inventing new edges.

### 3.2 Native histograms: no. Over-built for this estate.

Prometheus is **2.48.0** (verified `/api/v1/status/buildinfo`), where native histograms are experimental behind `--enable-feature=native-histograms`. Grafana is **10.2.0**. Python `prometheus_client` native-histogram support is recent and experimental. Adopting native histograms would mean an experimental feature flag on a stale Prometheus, an experimental client path, and no query-side maturity in Grafana 10.2 — for a service handling ~1900 reads in the observed window. Classic over-build. Revisit if and when the stack moves to Prometheus 3.x for other reasons.

### 3.3 HIGH — `histogram_quantile` without `sum by (le)` is a real bug, and the estate already knows the fix

`histogram_quantile` without `le`-aggregation is not "acceptable here" — it is wrong, and it is why panels double. Prometheus documentation for `histogram_quantile` specifies aggregating with `sum by (le)` (plus any dimensions you want to keep) before taking the quantile; without it you get one quantile series per underlying label set.

Live count across the 9 dashboards: **22 `histogram_quantile` calls, 10 of them missing `sum by (le)`** — 8 in `dhg-registry-api.json` (panels 3, 4, 20, 21), 2 in `memreg-daemon.json` (panel 11).

`vs-engine.json` **already does it correctly**: `histogram_quantile(0.95, sum(rate(vs_generation_duration_seconds_bucket[5m])) by (le))` and, where a dimension is wanted, `by (le, phase)`.

So this is an inconsistency inside the estate, not missing knowledge. It also means the audit's §4 attribution is incomplete: fixing the double scrape would make the registry panels *look* fixed while leaving the underlying query still wrong — it would re-break on the next label added anywhere (a `route` label, for instance, which §3.1 recommends adding).

---

## 4. Logs

### 4.1 Alloy config is good. Leave it alone.

Six redaction stages with the capture-group semantics documented inline, level extraction with a three-way fallback and an explicit `unknown`, `label_drop` of the extraction temporaries, and healthcheck drops in both combined-log and JSON forms. `SecretLeakDetected` (`loki/rules/fake/alerts.yml:51-60`) is a **post-redaction verification alert** on the stored data — that is the right control, and it is the single best-designed rule in the estate. Nothing here needs Phase 3 attention.

### 4.2 `retention_period: 0` is defensible. The alert protecting it is slightly over-built.

Live: `loki_store_bytes` = 2.27 GiB. Free space: **/ = 1630 GB, /mnt/4tb = 3183 GB**. At the observed store size, keep-all has a runway measured in decades, and `RootDiskHigh`/`DataDiskHigh` already cover the real risk (disk pressure), regardless of what is consuming it. `LokiStoreGrowth` at 20 GiB will therefore fire while 1.6 TB is still free — it is a policy-review prompt, which the rule's own description says explicitly. Fine as designed; just do not treat it as a capacity control. The genuine defect here is its unguarded dependency (§1.7), not its threshold.

### 4.3 Five labels is the right label set. Do not add a `service` label to Loki.

`job`, `container`, `compose_service`, `compose_project`, `level`. Loki's own label guidance is to keep label cardinality low and put everything else in the log line — this set is deliberately minimal and `discover_service_name: []` explicitly suppresses Loki 3.x's auto-added `service_name` to preserve parity. Correct.

The audit implies per-service log panels need service-level labels. They do not: `compose_service` already *is* the service-level label, and it is present on every stream. Adding a Prometheus-matching `service` label would raise stream cardinality to solve a problem that a dashboard variable on `compose_service` already solves.

### 4.4 The compose_project asymmetry is a symptom of §2.1, not an independent defect

Loki ingests everything on the Docker socket (no container filter); Prometheus's docker-sd keeps only `dhgaifactory35|dhg-memreg`. "Log everything, scrape selectively" is a normal and defensible posture — logs are cheap and retrospective, scrapes cost cardinality.

The problem is the specific consequence: **portage logs are in Loki while portage metrics reach Prometheus only through a hand-written static job**, and portage has the best instrumentation in the estate with no dashboard (G8). That is the docker-sd keep-regex failing to express the estate, i.e. §2.1. Deleting docker-sd dissolves the asymmetry.

On P11 (26 of 42 containers silent in 24h): the audit's conclusion — app-side, not pipeline-side — is sound and well-evidenced. But `dhg-frontend` emitting nothing in **7 days** is not "quiet", it is a Next.js container with no request logging, and it is worth one line in Phase 3. Not a pipeline finding.

---

## 5. Traces — target architecture

### 5.1 Verified facts (not inferred)

- Langfuse on dh40801 is **v3.224.1** (`GET 10.0.0.179:3000/api/public/health` → `{"status":"OK","version":"3.224.1"}`).
- Langfuse self-hosted supports OTLP trace ingestion at `{host}/api/public/otel` **from v3.22.0 onward** (Langfuse docs, `content/integrations/native/opentelemetry`). Auth is `Authorization: Basic base64(public_key:secret_key)` plus header `x-langfuse-ingestion-version: 4`.
- Confirmed live on this instance: `POST 10.0.0.179:3000/api/public/otel/v1/traces` → **401**, not 404. The endpoint exists and is gated on auth, exactly as documented.
- Langfuse exposes **no Prometheus metrics endpoint**: `GET 10.0.0.179:3000/metrics` → **404**. This corroborates G1 and constrains §7 below.

### 5.2 The option I would defend: **(a) OTel → Langfuse OTLP only; retire Tempo.**

- **(b) OTel Collector fan-out to both** is the over-built option and I would push back hard on it. It adds a fourth long-lived daemon to a two-host, single-operator estate in order to maintain a second copy of spans that nobody queries. Tempo has held **zero spans in 19.5 days**; a fan-out preserves a consumer that has never existed. Collectors earn their keep at multi-team scale where routing, sampling, and tenancy differ per producer. None of that applies here.
- **(c) Tempo for infra spans, Langfuse for LLM spans** is (b) with the fan-out replaced by manual endpoint bookkeeping in every service, and it presumes "infra spans" that this estate has never produced. `services/medkb/src/medkb/tracing.py:61` already points at `http://dhg-tempo:4318` and has emitted nothing; the deprecated `langgraph_workflows/.../tracing.py:118` points at a Cloudflare hostname that 401s. Two OTLP destinations in a codebase that cannot keep one working is not a design, it is a second thing to leave broken.
- **(a)** matches the stated direction: Pydantic AI's `instrument_all()` emits OpenTelemetry, and Langfuse ingests OpenTelemetry natively at a documented, live, versioned endpoint. One exporter env pair per service, one destination, one UI. Tempo, its OTLP receivers, its metrics_generator remote-write (`tempo-config.yml:31-42`, P7), its 31-day block retention, and its Grafana datasource all go away.

**Retiring Tempo is not a single delete.** It must take with it: `grafana/provisioning/datasources/tempo.yml`; the `derivedFields` TraceID link in `loki.yml:16-21`; `exemplarTraceIdDestinations` in `prometheus.yml` datasource provisioning; `dhg-langgraph-traces.json`; and the `OTEL_ENDPOINT=http://dhg-tempo:4318` on medkb. The audit lists these as "inert" (P8, D1, D6, D7) without tying them to the Tempo decision — leaving any of them behind reproduces today's condition, where Grafana advertises trace links that go nowhere. **That, not "Tempo is dead", is the actual harm:** tooling that visibly offers a capability it does not have trains the operator to distrust the whole console.

**The one honest caveat.** Option (a) makes dh40801 a single point of failure for all tracing, and dh40801 is currently unmonitored (G1) with a prior MinIO-bucket silent-drop incident on record. That argues for doing §7 *before* or *with* the cutover — it does not argue for keeping Tempo. Keeping a second trace store as insurance against an unmonitored host is treating the symptom.

### 5.3 Do not add a `TempoDown` alert (audit P2)

P2 proposes a TempoDown / span-rate alert. Alerting on a component with no producers and no consumers manufactures a signal about something nobody depends on. Decide Tempo's fate first; if it stays, alert on it; if it goes, the alert is deleted work. This is a small instance of the general pattern below: the audit occasionally proposes monitoring for things whose existence is itself the open question.

---

## 6. Dashboard design

### 6.1 Measured state against a golden-signals template

Across the 9 provisioned dashboards:

| Dimension | Finding |
|---|---|
| Template variables | Only 3 of 9 have any (`$container`, `$level`). **None use `$job` or `$instance`.** No dashboard is reusable across services. |
| Refresh | `5s` (core-golden), `15s`, `30s`×6, **none** (langgraph-traces). 5s refresh against a 15s scrape interval re-renders the same data three times. |
| Default time range | `now-15m`, `now-1h`×2, `now-6h`×6. |
| Units | `dhg-core-golden`: units on **2 of 13** panels. `dhg-langgraph-traces`: **0 of 9**. `dhg-registry-api` uses `ms` (correct for the metric, wrong for the convention — see §3.1). |
| Thresholds | 0–6 panels per board; no shared semantic. |
| Legends | **60 literal `legendFormat` strings** with no `{{label}}` interpolation across the estate. The audit's "22 lines all named Reads" (panel 10) is not one bad panel — it is the house style. |
| Row order | No consistent RED-then-USE ordering; `dhg-registry-api` opens with stat tiles, `dhg-postgresql` with connections, `vs-engine` with domain metrics. |

### 6.2 MEDIUM — "one dashboard per service" is the wrong direction for this estate

The audit's §3 inventory and §7 gaps (G8 portage no dashboard, G13 medkb no dashboard, G17 session-logger no dashboard) push toward one board per service. For a single operator, more boards means more surfaces to keep synchronised and more places for metric-name drift — which is already the estate's dominant dashboard failure mode (G12 core-golden, G14 vs-engine: 16 dead targets between them, from names that drifted and nobody noticed).

**Better shape — fewer, denser, templated:**

1. One **templated service board** (`$job` + `$instance`), RED on top, USE below, that covers registry, portage, medkb, vs-engine, session-logger, memreg from one JSON. This is the payoff for the label convention in §2.2 — and it is unreachable until that lands.
2. One **estate overview** (targets up, alert state, host/disk, container churn) — `dhg-alerting` and `docker-overview` are already close and both are healthy.
3. One **log board** — `dhg-log-analytics`, healthy, keep.
4. Purpose-built boards **only where the domain genuinely differs**: Postgres (keep, it works), VS-engine (domain metrics like diversity/TTCT have no generic template), and eventually Langfuse/LLM (tokens, cost, tool-call failures — genuinely a different shape).

That is 5–6 boards, down from 9, with 3 of the current 9 (core-golden, vs-engine, langgraph-traces) either rebuilt from live metric names or deleted. Every new board should be justified by "the generic template cannot express this", the same standard `.claude/rules/frontend-consistency.md` already applies to components.

Also: `memreg-daemon.json` is **untracked in git** (audit §3, confirmed). A provisioned dashboard outside version control contradicts `CLAUDE.md`'s "version control is sole source of truth" and should be a Phase 3 blocker, not a footnote.

### 6.3 MEDIUM — the dhg-brand token requirement mostly does not apply to Grafana, and applying it to thresholds would be harmful

`.claude/rules/dhg-brand.md` mandates light+dark CSS tokens and "no raw hex in components". Grafana is not a component surface the estate controls:

- **What is reachable:** `GF_USERS_DEFAULT_THEME` (light/dark — Grafana already ships both and honours the user's choice, so the light+dark requirement is satisfied by default), and a **custom series colour palette** so charts read as DHG rather than Grafana-default. Panel-level `fieldConfig.color` overrides for named series are also reachable.
- **What is not:** Grafana chrome, nav, and panel frames are themed by Grafana's own theme system, not by CSS variables you can inject; custom theming in OSS Grafana 10.2 means forking CSS, which is unmaintainable across upgrades.
- **What would be actively wrong:** using brand colours for *threshold* states. Threshold colour is semantic — green/amber/red is a learned signal, and substituting purple/orange for "warning"/"critical" degrades readability of the exact panels that exist to be read under stress. Brand identity applies to series palettes; it must not apply to state encoding.

Recommend Phase 3 scope this explicitly as "default theme + series palette", and record the threshold-colour carve-out as a decision so a later session does not re-litigate it.

### 6.4 MEDIUM — Grafana 10.2.0 and Prometheus 2.48.0 are three years stale; the audit never checks versions

Verified live: Grafana `10.2.0` (`/api/health`, commit `895fbafb7a`; image pinned at `docker-compose.override.yml:158`), Prometheus `2.48.0`. Both are late-2023 builds. Meanwhile Loki is `3.7.6` (built 2026-08-05) and Alloy is current.

The P5 log program modernised the logging half of the stack and left the metrics half on 2023 releases. This matters beyond hygiene: it constrains native histograms (§3.2), it constrains dashboard schema features Phase 3 might reach for, and Grafana 10.x is outside its supported window. I have not enumerated specific CVEs and will not assert any — but "supported version" is itself a prerequisite the audit should have surfaced before proposing dashboard work on this Grafana.

---

## 7. Cross-host observation of dh40801

### 7.1 Blackbox-only is insufficient. Put an agent on the host.

The failure already on record — a MinIO bucket problem causing silent trace drop — returns HTTP 200 from `/api/public/health`. A synthetic probe cannot see it. Blackbox-only would reproduce the exact blind spot that motivated G1.

**Minimal correct shape (three containers, ~15 lines of config):**

- `node-exporter` and `cAdvisor` on dh40801, **pulled** by g700data1's Prometheus via two static jobs with `instance: dh40801`. Pull, not push: Prometheus 2.48 remote-write receiver would have to be enabled on the g700 side, and pull gives you `up == 0` as a free liveness signal for the host itself, which push does not.
- `Alloy` on dh40801 forwarding to g700's Loki (`loki:3100` is not currently LAN-exposed — that is a one-line port publication, and it is the only new network surface this creates; scope it to the LAN).
- Keep the blackbox probe of `/api/public/health` as well. It is cheap and it is the only thing that exercises the full request path including the reverse proxy.

This is the same static-job convention as §2.1, which is another argument for settling on static: docker-sd structurally cannot reach a second host.

### 7.2 What Langfuse itself is worth alerting on — and an honest limit

**Verified: Langfuse OSS exposes no `/metrics` endpoint** (`GET :3000/metrics` → 404). Any Phase 3 plan that assumes a Langfuse Prometheus scrape is building on a false premise. What is actually available:

- `GET /api/public/health` — returns `{"status","version"}`, 200 verified. Blackbox with a **body match** on `"status":"OK"` (not bare `http_2xx` — see §8.4 on why bare status-code matching already failed this estate once).
- `GET /api/public/ready`.
- **The signal that actually matters is ingestion freshness, and it has to be synthesised**: poll the Langfuse public API for trace count in the last N minutes and expose it as a textfile gauge, then alert on staleness. That is the direct analogue of the MinIO silent-drop failure and it is the only check that would have caught it. It is also the one piece of genuinely new build work in this whole area — worth naming as such rather than burying it in "monitor Langfuse".
- Host-level: disk on the volume holding Langfuse's Postgres/ClickHouse/MinIO (the audit notes 52 GB, 81% reclaimable), container restarts via cAdvisor, and the Langfuse worker on :3030 (loopback-bound — reachable from an on-host agent, not from g700; another point for the agent over the probe).

---

## 8. What the audit over- and under-weights

### 8.1 G2 (no backup signal) — real, correctly severe, wrong document

A backup that is not verified is not a backup, and SRE Book ch.26 ("Data Integrity") treats backup-restore verification as a first-class monitored signal. So the concern is legitimate and CRITICAL.

But the audit conflates two findings. The **observability** finding is: *no `backup_last_success_timestamp` metric exists, therefore no staleness alert is possible* — that is a small, cheap deliverable (a textfile gauge plus `time() - backup_last_success_timestamp > 26h`). The **ops/DR** finding is: *there may be no backups at all for 7 Postgres instances* — which is far more serious and is not an observability ship.

Leaving it as CRITICAL #2 in an observability audit invites Phase 3 to scope a backup *system* into an observability plan, which is how a focused ship turns into an abandoned one. **Recommendation: keep it visible, retitle to the observable deliverable, and escalate the underlying question to Stephen separately and immediately.** §9.5 correctly flags that backups may run somewhere unseen — that should be resolved by asking, not by building.

### 8.2 "Tempo dead" — correctly *not* CRITICAL, and the audit gets this right

The audit's scoreboard calls traces DEAD but does not put Tempo in the CRITICAL gap list. That is the correct call: zero spans, zero consumers, zero user impact. It is a decision plus a cleanup. The one place the audit drifts is P2's proposed TempoDown alert (§5.3). Cut it.

### 8.3 HIGH gaps that are LOW for a single-operator estate — argued

- **G11 (no uptime probe on frontend :3000 / Open WebUI :3080)** — LOW. The operator is effectively the only user of both and will discover an outage by opening the page. An alert here pages a human about something the same human is already looking at.
- **G16 (audio-agent exposes /metrics, unscraped)** and **G17 (session-logger has no dashboard)** — LOW. Add the scrape when something consumes it. A scrape target with no dashboard and no alert is cardinality with no reader.
- **G13 (medkb: rich metrics, no traffic alert)** — LOW, and an alert here would be actively wrong. medkb has 0 series across 12 declared families because it has **0 traffic**. Alerting on absence of traffic for a service nobody calls generates a permanent alert. Revisit after the dh40801 relocation, when medkb has users.
- **G15 (`ZombieProcessesHigh` inert)** — LOW, and the fix is **delete the rule**, not enable the collector. Zombie processes are a symptom of a parent that is not reaping; on a 64 GB box running containers, PID pressure is not a live risk and this rule has no plausible action attached to it. `--collector.processes` also adds meaningful `/proc` scrape cost. The audit lists it as MEDIUM to fix; it should be MEDIUM to remove.

Genuinely correctly ranked HIGH: G5 (registry has no HTTP golden signals), G7 (no GPU telemetry — an RTX 5080 running local inference with no VRAM/thermal signal is a real operational blind spot), G9 (Cloudflare tunnels are the ingress for `registry.digitalharmonyai.com`; a tunnel failure is externally visible and internally silent), G10 (6 of 7 Postgres instances unexported).

### 8.4 Under-weighted

- **G8 (Portage)** — should be first, not fourth. See §1.4. It is the only place a symptom-based alert can be written today.
- **G6 (host-ollama-steals-:11434)** — the audit correctly notes `http_2xx` has no body match and that the `prometheus.yml:90-93` comment claiming coverage is wrong. Underweighted consequence: `blackbox.yml` defines **only** `valid_status_codes: [200]` for both modules, so *every* blackbox check in the estate — ollama container, ollama LAN, portage `/health` — verifies nothing beyond "something answered". Adding `fail_if_body_not_matches_regexp` is a three-line change to `blackbox.yml` that fixes all three probes and is a prerequisite for the Langfuse probe in §7.2.

---

## 9. Phase 4 verification method

The audit's §9.3 treats this as one problem. **It is two**, and conflating them is why it looks harder than it is.

**Problem A — does the panel return data?** A Grafana **service account** with `Viewer` role, token in Doppler, driving `/api/ds/query` and `/api/dashboards/uid/<uid>`. Service accounts are GA in Grafana 10.2, the token is revocable and scoped, and nothing about it touches the admin password (which currently sits in `docker-compose.override.yml` — a separate problem, and one that C11 in `CLAUDE.md` already acknowledges). This is what Phase 1 was actually reaching for and it fully solves data verification, non-interactively, within the secret-safety rule.

**Problem B — does the panel *look* right?** A token does not produce pixels. Two options:

- `grafana-image-renderer` as a sidecar. Grafana mints a short-lived render key per request, so there is no standing credential and no new human-facing auth surface. **Security trade-off to state plainly:** the renderer is an unauthenticated internal HTTP service that will render whatever URL Grafana hands it — bind it to the compose network and never publish the port. That is the whole exposure, and it is acceptable.
- Playwright (already available in this session's toolchain) driving a real browser against Grafana. Needs a login, which reintroduces the password problem — unless the renderer route is taken anyway.

**An SRE picks the service-account token plus the image renderer, and rejects anonymous Viewer.** The reasoning is specific to this estate rather than generic: Grafana's `Viewer` role grants **Explore**, and Explore against the Loki datasource is unrestricted read of the entire log store. This estate ships a `SecretLeakDetected` rule precisely because it knows redaction can fail. Turning on anonymous access to the log store to save the trouble of minting a token trades a real, known secret-exposure risk for a small convenience. It is the wrong trade even on a LAN — and I could find no evidence either way about whether Grafana :3001 is behind a Cloudflare tunnel (no tunnel config is in this repo; the config is root-owned per `reference_cloudflare_tunnels.md`), which means the LAN-only premise is **unverified**. Do not build a security decision on it.

---

## 10. Summary of severities

| Sev | § | Finding |
|---|---|---|
| CRITICAL | 1.1 | Alerting pipeline unmonitored — Alertmanager not scraped; `alertmanager_notifications_failed_total`, `prometheus_rule_evaluation_failures_total`, `prometheus_notifications_dropped_total`, `loki_prometheus_notifications_errors_total` all available and unalerted. Audit misses entirely. |
| CRITICAL | 3.1 | Audit's implied "retune registry latency buckets" direction is wrong; the metric violates naming convention, is in ms, and measures DB calls not requests. Replace, don't tune. |
| HIGH | 1.2 | 4-value severity taxonomy; webhook drops `medium` as well as `warning`, silently discarding `DataDiskHigh`. The drop is correct; the taxonomy is not. |
| HIGH | 1.3 | 0 of 23 rules carry `runbook_url`. |
| HIGH | 1.6 | G4 graded CRITICAL but is a one-line fix: `changes(container_start_time_seconds[15m]) > 3`, 42 series live. |
| HIGH | 2.1 | Double scrape is a defect; canonical path should be **static**, not docker-sd, because SD targets are container IPs that churn on every recreate. |
| HIGH | 2.2 | `service`/`container` labels are disjoint; medkb/loki/alloy have neither. Label convention is a prerequisite for the dashboard work. |
| HIGH | 3.3 | 10 of 22 `histogram_quantile` calls omit `sum by (le)`; `vs-engine.json` already does it right. |
| HIGH | 1.4 / 8.4 | No latency or error-ratio alert anywhere. G8 (Portage) is the only service that can support one today and should be ranked first. |
| MEDIUM | 1.5 | `absent()` used zero times; correct for `memreg_dlq_depth` only — applying it to the other two dead rules creates permanent alerts. |
| MEDIUM | 1.7 | `LokiStoreGrowth` depends on an unguarded textfile gauge; `node_textfile_mtime_seconds` scraped and unalerted. |
| MEDIUM | 1.8 | Alertmanager `inhibit_rule` is a no-op; registry outage produces 3 alerts / 3 incident rows. `alertmanager.yml` never examined by the audit. |
| MEDIUM | 5.2 | Recommend option (a): OTel → Langfuse OTLP only, retire Tempo. (b) and (c) over-built for two hosts. Retirement must also remove the Loki derived field, Prometheus exemplar destination, and Tempo datasource. |
| MEDIUM | 6.2 | "One dashboard per service" is wrong; 5–6 templated boards, not 9+. |
| MEDIUM | 6.3 | dhg-brand tokens largely inapplicable to Grafana; brand colour on thresholds would be harmful. |
| MEDIUM | 6.4 | Grafana 10.2.0 / Prometheus 2.48.0 are 2023 builds; audit never checks versions. |
| MEDIUM | 7.1 | Agent on dh40801 (node-exporter + cAdvisor + Alloy, pulled), not blackbox-only. Langfuse has no `/metrics` (verified 404); ingestion-freshness must be synthesised. |
| MEDIUM | 8.1 | G2 is a DR finding in an observability document; keep visible, retitle to the observable deliverable, escalate separately. |
| MEDIUM | 8.4 | `blackbox.yml` has no body match on any module — all three probes verify only "something answered". |
| LOW | 8.3 | G11, G13, G16, G17 are LOW for a single operator; G15 should be "delete the rule", not "enable the collector". |
| LOW | 0 | Audit misstates read-histogram buckets as `[1..5000]`; read is `[1..1000]`, write is `[1..5000]`. |
| LOW | 6.2 | `memreg-daemon.json` provisioned but untracked in git — contradicts "version control is sole source of truth". |
| LOW | 9 | Phase 4 verification is two problems, not one: service-account token for data, image renderer for pixels. Reject anonymous Viewer (Explore ⇒ unrestricted Loki read). |

---

## Version history
- v1 2026-09-04: initial adversarial review (reviewer 3 of 4, observability domain expert).
