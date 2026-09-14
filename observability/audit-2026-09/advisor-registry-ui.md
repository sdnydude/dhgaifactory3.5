# Advisor review — "Postgres datasource + Registry folder in Grafana"

Date: 2026-09-05 · Reviewer: advisor (read-only) · Scope: the recommendation quoted in the brief

## VERDICT

**Approve with changes.** The direction (read the registry with an off-the-shelf reader
instead of writing UI) is right. As written it is wrong on three counts: it would connect
Grafana to the production DB as a **superuser**, its flagship board (incidents) would
render numbers that are **10x wrong**, and its "operator home page" **already exists** at
`/dashboards`. Cut it to one board plus a read-only role.

## Findings

```
CRITICAL | Grafana would connect as `dhg`, the only login role on the registry DB, and it is SUPERUSER | pg_roles WHERE rolcanlogin -> single row: dhg, rolsuper=t, rolcreatedb=t. No read-only role exists. pg_stat_replication -> 0 rows, so no replica to point at either.
CRITICAL | The incidents board would show meaningless numbers. SQL says 1,112 active incidents; /api/incidents/stats says 110 active / 117 total | psql: SELECT status,severity,count(*) FROM incidents -> active/high 1033 + active/critical 79 = 1112 active, 1143 total. curl http://10.0.0.251:8011/api/incidents/stats -> {"total":117,...,"by_status":{"active":110,"resolved":7}}. Two open deferred_items rows (2026-09-04) already name this: "dhg-remediator re-processes the same 50 open incidents every 30s" (critical) and "Incident API count drift" (medium). Building the board does not surface the problem; it launders it into a dashboard the CEO will read as fact.
HIGH | incident_actions has NO time index. 2,614,357 rows / 741 MB — 47% of the 1,577 MB database — and its only indexes are the pkey and incident_id | \d incident_actions -> Indexes: incident_actions_pkey (btree id), ix_incident_actions_incident_id. A "captures/actions per day" panel filters on performed_at, so every panel refresh is a 741 MB sequential scan against the same Postgres that serves the app on max_connections=100. incident_events (2,615,949 rows / 678 MB) at least has ix_incident_events_timestamp DESC.
HIGH | The "operator home page" is already built and running | frontend/src/components/dashboards/data.ts fetchTelemetry() fans out to Prometheus targets, Alertmanager active alerts, registry req-rate/err-rate/p95, pg_stat_activity, node load/mem, LangGraph spanmetrics calls+p95+topk, /api/cme/stats/pipeline, /api/cme/stats/services, /api/corrections/stats, /api/feedback-loop/health, /api/deferred-items/stats — polled every 10 s and rendered as Mission Control at /dashboards (HTTP 200). Rebuilding this in Grafana is duplicate surface with a second refresh loop against the same backends.
HIGH | "Langfuse trace volume" is not buildable in Grafana today, with or without new software | observability/grafana/provisioning/datasources/ contains loki.yml and prometheus.yml only; prometheus.yml carries `deleteDatasources: [Tempo]` with the note "Tempo retired 2026-09-04 ... OTLP now goes to Langfuse (http://10.0.0.179:3000)". Langfuse is reachable (HTTP 200) but there is no Grafana datasource for it. The panel is a promise the stack cannot keep.
MEDIUM | Claude cannot supply the DB credential through the sanctioned path. Grafana's env is assembled in docker-compose.override.yml (off-limits): docker inspect dhg-grafana shows GF_SECURITY_ADMIN_USER / GF_USERS_ALLOW_SIGN_UP, which do not appear in docker-compose.yml — that file's grafana stanza sets only the two GF_RENDERING_* vars | Grafana 10.2 does support env interpolation in provisioning YAML (`$VAR`, `${VAR}`, and `$__env{PG_PASSWORD}` in secureJsonData — confirmed against Grafana's provisioning and postgres-datasource docs), so the mechanism is fine; the blocker is who may add the variable. The repo already has the answer as precedent: observability/postgres-exporter/render-postgres-exporter.sh renders postgres_exporter.yml from Doppler and .gitignore:137-139 keeps it out of git, with a tracked .example for shape. Do the same: datasource.yml.example tracked, rendered datasource yml gitignored.
MEDIUM | Grafana is a poor reader for the text-heavy tables the recommendation puts in it | decision_logs.choice / .rationale / .alternatives_rejected are `text`; insights, session_reports and bug_fixes are the same shape (session_reports: 10 rows but 1,344 kB). Grafana's table panel truncates long cells, renders no markdown, and offers no row drill-in. Decisions/insights/reports read badly there. Incidents, deferred items and capture counts are genuinely tabular and read fine.
MEDIUM | Two of the proposed boards have no data source at all | "captures per day by type" has no aggregate API (openapi.json exposes /stats only for corrections, deferred-items, incidents, done-gate-runs, cme) and would need raw SQL per table; "dead-letter count" has no home in this DB — SELECT tablename FROM pg_tables WHERE tablename ILIKE any of '%dead%','%letter%','%queue%' returns 0 rows. The dead-letter queue lives in the memreg daemon, outside Postgres.
LOW | /inbox is not an operator surface and never was | frontend/src/app/inbox/page.tsx is a 7-line wrapper around InboxMasterDetail, which calls listPendingReviews()/resumeThread() (LangGraph CME human-in-the-loop) and falls back to DEMO_REVIEWS when the list is empty. Nothing about the registry. Not a substitute, not a conflict.
LOW | The auth asymmetry runs the opposite way to the assumption | Grafana at :3001 returns 401 on /api/search with no credentials; the registry API at :8011 returns 200 on /api/deferred-items and /api/decision-logs with none. For 50 leadership readers Grafana is the better-gated of the two — but only behind Cloudflare Access, and Grafana 10.2 OSS has no per-folder read scoping worth the name.
LOW | The small capture tables are in good shape for boards — no schema work needed | deferred_items has ix_deferred_items_created, _status, _priority, _project_category; decision_logs has ix_decision_logs_created and _project_domain; agent_sessions (2,820 rows) has ix_agent_sessions_project_created. All carry created_at; deferred_items carries status + priority + updated_at + last_surfaced_at.
LOW | The remediator's steady-state write rate is ~24.5K action rows/day, not 74K | incident_actions grouped by performed_at::date -> 24,457 (09-01), 24,620 (09-02), 24,457 (09-03). Still 9 GB/year of churn on a 1.6 GB database, but size the fix to the real number.
```

## Minimal scope I would approve

1. **Create a read-only role first — this gates everything else.** As `dhg`:
   ```sql
   CREATE ROLE grafana_ro LOGIN PASSWORD '<from Doppler>';
   GRANT CONNECT ON DATABASE dhg_registry TO grafana_ro;
   GRANT USAGE ON SCHEMA public TO grafana_ro;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_ro;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO grafana_ro;
   ALTER ROLE grafana_ro SET statement_timeout = '10s';
   ALTER ROLE grafana_ro SET default_transaction_read_only = on;
   ```
   The `statement_timeout` is the load guard that makes the whole idea safe; without it one
   bad panel pins a connection against a 741 MB scan.
2. **One datasource**, provisioned from a gitignored rendered file (postgres-exporter
   pattern), `jsonData.maxOpenConns: 3`, `sslmode: disable` (same Docker network).
3. **One board: "Registry Activity".** Only the small, indexed tables — deferred items open
   by priority, decisions/insights/bug-fixes/corrections per week, ship + agent sessions,
   test-coverage trend. Table panels with `created_at` filters that hit existing indexes.
   Nothing touching incident_actions or incident_events.
4. **No incidents board until the remediator loop is fixed.** Put a single stat panel —
   `SELECT count(*) FROM incidents WHERE status='active'` — on the existing `/dashboards`
   page instead, labelled as raw count, so the 1,112-vs-110 gap is visible rather than
   dressed up.
5. **No second home page.** `/dashboards` is the one URL. If Langfuse volume belongs
   anywhere it is a tile there, fetched from Langfuse's own API through the existing
   `/api/*` proxy pattern, not a Grafana panel with no datasource behind it.

**Effort.** Recommendation as written: seven boards plus a home page, each needing a
`verify-dashboard.sh` render pass — 2-3 days, and roughly half of it re-implements
`/dashboards`. Minimal scope above: 2-4 hours, most of it the role and the credential
render script.

**Second ship, in order.** (a) Fix the remediator re-processing loop and the incident API
count drift — both already captured as open deferred items; a dashboard over broken data is
worse than no dashboard. (b) Add a retention/partition policy for incident_actions and
incident_events before they double again. (c) *Then* revisit a row-editing tool. On that
question the recommendation's own second choice is the better first one for a single
operator who wants to click "acknowledge": **NocoDB** points at the existing Postgres, needs
no modelling, and is one compose service — but it needs write credentials, which is exactly
the decision the read-only role above is designed to postpone until the incident data is
trustworthy. Metabase is the right answer only if funding diligence needs saved questions
and shareable charts; it is a heavier install (its own app DB) for one reader today.

## What the recommendation is blind to

- **Auth for 50 leadership readers.** Grafana 10.2 OSS has no usable per-folder read
  scoping; everyone lands as Viewer over every folder including infrastructure. Cloudflare
  Access in front is mandatory, and that is a dashboard-only change nobody has scoped.
- **Mobile.** Grafana table panels are unusable on a phone. "One URL to know what is
  happening" is a phone question more often than a desk question.
- **The remediator queue is the story, not a footnote.** 1.4 GB of the 1.577 GB database is
  two tables of robot chatter. Any honest "what is happening" answer leads with that.
- **Diligence optics.** A Grafana board reading 1,112 active incidents, in a folder next to
  the platform-health boards, is a worse artifact to show an investor than no board at all.
