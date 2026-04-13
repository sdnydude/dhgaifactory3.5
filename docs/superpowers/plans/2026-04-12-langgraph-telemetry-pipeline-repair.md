# LangGraph Telemetry Pipeline Repair — Implementation Plan v2

> **v1 lessons:** This is v2. v1 (`_v1.md`) was executed task-by-task in a multi-hour session and still left the pipeline dark. Two latent failures slipped past the gate:
> 1. v1 Task 4 Step 3 told you to set `OTEL_EXPORTER_OTLP_HEADERS=CF-Access-Client-Id=...,CF-Access-Client-Secret=...`. The code at `src/tracing.py:68-74` actually reads `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` as **two separate env vars**. Following the plan literally left `_headers = {}` at runtime, Cloudflare Access returned 401, `BatchSpanProcessor` silently dropped every batch.
> 2. v1 Task 5 (Prometheus `--web.enable-remote-write-receiver` flag) was listed but never actually applied to `docker-compose.override.yml`. Tempo's `metrics_generator` was producing span-metrics correctly and POSTing them to `http://prometheus:9090/api/v1/write`, receiving HTTP 404 every 15s for weeks. Nothing on the v1 gate checked for this.
>
> v2 detects both of these in under 2 minutes of reading, via §A + §B + §C.

**Goal:** Repair or verify the LangGraph Cloud → Tempo → Prometheus telemetry pipeline end-to-end so that agent spans produce queryable Prometheus metrics. Keep the greenfield thread-state exporter work (v1 Tasks 7-13) as Phase 2.

**Shape:** Fact-keyed, not task-keyed. Sections §A-§E are reference material you consult when something's broken. Section §F is ordered Phase 2 implementation. Section §G is a post-mortem checklist for future plans.

**Spec:** `docs/superpowers/specs/2026-04-12-langgraph-dashboards-design.md`

---

## §A — Code Contract (source of truth)

This section pins the operational contract that `tracing.py` actually implements. **If the live code has drifted from this table, fix the table first** before making any production change — otherwise v2 will repeat v1's mistake of fighting an imaginary contract.

**File:** `langgraph_workflows/dhg-agents-cloud/src/tracing.py` (as of commit `65d21fc`, 2026-04-13)

| Setting | Line | How it's read | Default |
|---|---|---|---|
| Service name resource | `:45` | hardcoded `SERVICE_NAME = "dhg-langgraph-agents"` | n/a |
| OTLP endpoint URL | `:49-52` | `os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", default)` | `https://otel.digitalharmonyai.com/v1/traces` (includes `/v1/traces` path) |
| CF Access client ID | `:68` | `os.getenv("CF_ACCESS_CLIENT_ID")` | none — header omitted if missing |
| CF Access client secret | `:69` | `os.getenv("CF_ACCESS_CLIENT_SECRET")` | none — header omitted if missing |
| Headers passed to exporter | `:76-79` | `{"CF-Access-Client-Id": ..., "CF-Access-Client-Secret": ...}` dict or `None` | `None` if either env var missing → **silent auth failure** |
| Exporter class | `:34` | `opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter` | HTTP, not gRPC |
| TracerProvider attach mode | `:86-93` | reuses existing SDK `TracerProvider` if LangSmith already installed one; else installs new | auto-detected; logged as `mode=attached-to-existing` or `mode=installed-new` |
| Init log line | `:97-104` | `OpenTelemetry initialized: service=... endpoint=... env=... mode=... provider=...` | grep for this in Cloud logs |
| Graceful no-op on import failure | `:29-39` | wraps all OTel imports in `try/except ImportError`; sets `_OTEL_AVAILABLE = False` | **tracing becomes a silent no-op** if the HTTP exporter wheel is missing from the image |

**Contract drift check:**

```bash
grep -n "CF_ACCESS\|OTEL_EXPORTER_OTLP_ENDPOINT\|OTLPSpanExporter\|dhg-langgraph-agents" \
  langgraph_workflows/dhg-agents-cloud/src/tracing.py
```

If any line numbers above have shifted or env var names have changed, **update this section in the same commit that changes the code**. v2's primary discipline.

**NOT a contract:** `OTEL_EXPORTER_OTLP_HEADERS` is **not** read by this code. v1 told you to set it as a comma-separated string; ignore that. If you find it already set on the deployment, it's harmless but does nothing.

---

## §B — Current State Audit (read-only, zero writes)

Run these six probes in order every time you pick up this plan. Zero writes. Output is a six-row checklist.

### B.1 — LangGraph Cloud deployment has the CF Access secrets

```bash
set -a; source .env; set +a
curl -s -H "x-api-key: $LANGCHAIN_API_KEY" \
  "https://api.host.langchain.com/v2/deployments/df113409-49ee-4f08-ac29-0c52402d54e6" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); \
    print('secrets:', sorted(s['name'] for s in d.get('secrets', [])))"
```

**OK:** a list containing at least `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET`.

**FAIL:**
- List missing either secret → **§D.1** (add via New Revision panel)
- 404 / auth error → `LANGCHAIN_API_KEY` isn't the one bound to this tenant; check `.env`

> **Scope trap:** Workspace-level secrets in LangSmith (Settings → Workspaces → Secrets) are **NOT** propagated to deployments. They must be attached to the deployment directly, and B.1 confirms that scope. Count the secrets returned — if you added them at workspace level and B.1 still shows only the 4 pre-existing ones, scope is wrong.

### B.2 — LangGraph Cloud deployment active revision

```bash
curl -s -H "x-api-key: $LANGCHAIN_API_KEY" \
  "https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app/info" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); \
    h = d.get('host', {}); \
    print('host_revision:', h.get('host_revision_id')); \
    print('internal_build_id:', h.get('revision_id'))"
```

**OK:** `host_revision` is the UUID of the latest deployed revision. `internal_build_id` is a short string like `3feb51d` — this is a LangGraph Platform **internal build revision**, **NOT** a git SHA. The real git commit is in the deployment's `source_revision_config.repo_commit_sha` field from B.1.

### B.3 — Cloudflared tunnel ingress for `otel.digitalharmonyai.com`

```bash
sudo grep -A 4 "otel.digitalharmonyai.com" /etc/cloudflared/config.yml
```

**OK:** an `ingress:` block routing the hostname to `http://localhost:4318` with a short `connectTimeout`.

**FAIL:** nothing printed → **§D.2** (add ingress rule + `systemctl restart cloudflared`)

### B.4 — Cloudflare Access application + service token bound

Manual check in the Zero Trust dashboard:

1. Applications → **LangGraph OTel Ingest** exists, domain `otel.digitalharmonyai.com`
2. Policies → has a policy with `Action: Service Auth`, `Include: Service Token → langgraph-cloud-otel`
3. Service Auth → Service Tokens → `langgraph-cloud-otel` exists and is not expired

**FAIL any of these:** → **§D.5**

### B.5 — Prometheus command flags include remote-write-receiver

```bash
docker inspect dhg-prometheus --format '{{range .Config.Cmd}}{{println .}}{{end}}' \
  | grep -E "remote-write|config.file|storage.tsdb"
```

**OK:** at least four lines including `--web.enable-remote-write-receiver`.

**FAIL:** missing the flag → **§D.3** (this is v1's biggest silent failure mode)

### B.6 — `tracing.py` and `requirements.txt` match §A

```bash
grep -c "opentelemetry-exporter-otlp-proto-http" \
  langgraph_workflows/dhg-agents-cloud/requirements.txt
grep -cE "CF_ACCESS_CLIENT|OTLPSpanExporter|dhg-langgraph-agents" \
  langgraph_workflows/dhg-agents-cloud/src/tracing.py
```

**OK:** first command returns `1`; second returns `≥ 4`.

**FAIL:** either returns `0` → code has drifted from §A. **Do not continue** until §A is updated or the code is restored. Do not run §D-§E against a mismatched contract.

---

## §C — Diagnostic Ladder

Use this when Gate A (§E) fails. Walk top-down. If a higher rung is OK, don't test lower rungs.

### C.1 — Does Prometheus have `traces_spanmetrics_*` series?

```bash
curl -s 'http://localhost:9090/api/v1/query?query=traces_spanmetrics_calls_total' \
  | jq '.data.result | length'
```

**OK:** `≥ 1`. Gate A E.3 passes. Stop.

**FAIL (`== 0`):** descend to C.2.

### C.2 — Is Tempo producing span-metrics and trying to remote_write them?

```bash
docker logs dhg-tempo --tail 200 2>&1 | grep -iE "level=error.*remote|level=error.*generator" | tail -5
```

**OK signal:** no recent error lines, AND C.3 shows traces present → check the Tempo `metrics_generator` config in `observability/tempo/tempo.yaml` (should have `processors: [service-graphs, span-metrics]` and a `remote_write` entry pointing at `http://prometheus:9090/api/v1/write`).

**FAIL signals (error lines present):**
- `404 Not Found: remote write receiver needs to be enabled` → **§D.3** ← this is the v1 silent failure
- `connection refused` → Prometheus container is down → `docker compose up -d prometheus`
- `context deadline exceeded` → Prometheus overloaded; check CPU/memory on `dhg-prometheus`

### C.3 — Is Tempo receiving traces from the tunnel?

```bash
curl -s "http://localhost:3200/api/search?tags=service.name%3Ddhg-langgraph-agents&limit=5" \
  | jq '.traces | length'
```

**OK:** `≥ 1` → pipeline is flowing end-to-end but something in the Tempo generator path is broken → back to C.2 with that context.

**FAIL (`== 0`):** descend to C.4.

### C.4 — Does the tunnel accept authed POSTs to `otel.digitalharmonyai.com`?

```bash
set -a; source .env; set +a
curl -sS -X POST -o /dev/null -w "HTTP %{http_code}\n" \
  -H "Content-Type: application/x-protobuf" \
  -H "CF-Access-Client-Id: $CF_ACCESS_CLIENT_ID" \
  -H "CF-Access-Client-Secret: $CF_ACCESS_CLIENT_SECRET" \
  --data-binary @/dev/null \
  https://otel.digitalharmonyai.com/v1/traces
```

**OK:** `HTTP 400` — tunnel routes, Access authorizes, Tempo rejects empty protobuf body. This is the correct "alive and authed" signal.

**FAIL:**
- `HTTP 401` / `HTTP 403` → service token wrong or not bound to Access app → **§D.5**
- `HTTP 530` → tunnel isn't routing → `sudo systemctl status cloudflared`; restart if needed
- `HTTP 000` → DNS unresolved; the CNAME may have been deleted
- `HTTP 404` → Tempo `/v1/traces` path not responding; check `dhg-tempo` container health

### C.5 — Is LangGraph Cloud actually emitting spans from the current revision?

LangSmith Cloud dashboard → Deployments → `dhg-agents` → Logs tab. Search for:

```
OpenTelemetry initialized: service=dhg-langgraph-agents endpoint=... env=production mode=...
```

**OK:** the line appears for the latest revision, AND there are no subsequent `OpenTelemetry not available` or `Max retries exceeded` / `401 Unauthorized` lines from the exporter.

**FAIL modes:**
- `OpenTelemetry not available — tracing disabled (expected in Cloud)` → HTTP exporter wheel missing from image → **§D.4**
- Init line shows `mode=installed-new` AND LangSmith tracing is enabled → possible race with LangSmith's `TracerProvider`. The code at `tracing.py:86-93` handles this by attaching to the existing provider; if `mode=installed-new` still appears AND spans don't flow, the LangSmith SDK may have changed behavior — check the `isinstance(_existing, TracerProvider)` branch
- No init line at all → `tracing.py` module isn't being imported; at least one agent in `src/` must `from src.tracing import traced_node`
- 401s after init line → **§D.1** (secrets not on the deployment)

---

## §D — Remediation Playbook

Flat list. Symptom-keyed. Each entry is self-contained.

### D.1 — CF Access secrets missing from LangGraph Cloud deployment

**Why:** Without `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` on the *deployment*, `tracing.py:67-74` builds `_headers = {}`, `OTLPSpanExporter` POSTs without auth headers, Cloudflare Access returns 401, `BatchSpanProcessor` logs a warning at DEBUG level and silently drops the batch. No exception propagates. No user-visible failure anywhere except "zero traces in Tempo." **This is the primary failure mode v1 could not detect.**

**Scope trap:** Workspace-level secrets (LangSmith → Settings → Workspaces → Secrets) are scoped to the Playground and evaluators. They are **not** propagated to deployments. Deployment secrets must be attached directly to the deployment.

**Fix A — via the LangSmith Cloud UI:**

1. LangSmith Cloud → Deployments → `dhg-agents` → the Deployment view (not the Revisions tab)
2. Click the `+ New Revision` button (top right)
3. In the revision modal, field #3 is the env vars / secrets section
4. Add `CF_ACCESS_CLIENT_ID` as a secret (value from local `.env`)
5. Add `CF_ACCESS_CLIENT_SECRET` as a secret (value from local `.env`)
6. Submit. Triggers a new revision build: QUEUED → BUILDING → DEPLOYED (~2-5 min)
7. Re-run §B.1 to verify — the secrets list should now include both names

> **"There is no Variables tab" gotcha:** LangSmith Cloud's deployment view has no "Variables" or "Environment" tab. Secrets are only editable through the `+ New Revision` modal. If you're looking for a Variables tab, stop — you're on the wrong path.

**Fix B — via the control plane API (scripted):**

Same endpoint as §B.1 supports writes. Fetch current deployment, append the two secrets, PATCH or POST back. Caveat: expect full-replacement semantics; include all existing secrets in the request body or they'll be dropped. Prefer Fix A unless you're automating this.

**Verify:**

```bash
curl -s -H "x-api-key: $LANGCHAIN_API_KEY" \
  "https://api.host.langchain.com/v2/deployments/df113409-49ee-4f08-ac29-0c52402d54e6/revisions/<new_revision_id>" \
  | jq -r '.status'
# Poll until: DEPLOYED
```

Then re-run §B.1 and §C.5.

### D.2 — Cloudflared ingress rule missing or wrong

**Why:** The tunnel doesn't know how to route `otel.digitalharmonyai.com` to `http://localhost:4318`.

**Fix:**

```bash
sudo cp /etc/cloudflared/config.yml /etc/cloudflared/config.yml.bak-$(date +%F)
sudoedit /etc/cloudflared/config.yml
```

Insert **before** the catch-all `- service: http_status:404`:

```yaml
  - hostname: otel.digitalharmonyai.com
    service: http://localhost:4318
    originRequest:
      connectTimeout: 10s
      noHappyEyeballs: true
```

```bash
sudo cloudflared tunnel --config /etc/cloudflared/config.yml ingress validate
# Expect: Validating rules from /etc/cloudflared/config.yml ... OK
sudo systemctl restart cloudflared
sudo systemctl status cloudflared --no-pager | head -10
```

**Verify:** re-run C.4; expect `HTTP 400`.

### D.3 — Prometheus `--web.enable-remote-write-receiver` flag missing

**Why:** Tempo's `metrics_generator` POSTs derived span-metrics to `http://prometheus:9090/api/v1/write`. Without the flag, Prometheus returns 404 on every push. Tempo logs one error per push cycle (~15s). **This is the v1 silent failure that caused weeks of dormant metrics.**

**Fix:** edit `docker-compose.override.yml`, prometheus service `command:` block, add:

```yaml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-remote-write-receiver'   # <-- add this
```

Recreate the container:

```bash
docker compose up -d prometheus
# 5-10 sec downtime for recreate; TSDB data preserved via named volume
```

**Verify:**

```bash
docker inspect dhg-prometheus --format '{{.Config.Cmd}}' | grep remote-write
# Expect: --web.enable-remote-write-receiver

curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST \
  -H "Content-Type: application/x-protobuf" --data-binary "" \
  http://localhost:9090/api/v1/write
# Expect: HTTP 400 (endpoint alive, empty body rejected)
# Before the flag:  HTTP 404
```

Wait ~60s for Tempo's next push cycle, then re-run C.1. Expect `≥ 1` series.

**Reference:** commit `65d21fc` applied this fix on 2026-04-13.

### D.4 — `opentelemetry-exporter-otlp-proto-http` missing from deployment image

**Why:** `tracing.py:29-39` wraps all OTel imports in `try/except ImportError`. If the HTTP exporter wheel isn't in the deployed image, `_OTEL_AVAILABLE` silently becomes `False` and `@traced_node` becomes a no-op passthrough — you get no spans and no error.

**Fix:**

```bash
grep "opentelemetry-exporter-otlp-proto-http" \
  langgraph_workflows/dhg-agents-cloud/requirements.txt \
  || echo "opentelemetry-exporter-otlp-proto-http>=1.25.0" \
     >> langgraph_workflows/dhg-agents-cloud/requirements.txt

git add langgraph_workflows/dhg-agents-cloud/requirements.txt
git commit -m "deps(tracing): ensure OTLP HTTP exporter in Cloud runtime"
git push
# LangGraph Cloud auto-deploys on push; watch B.2 until host_revision changes
```

Re-run C.5 to confirm the init log line appears.

### D.5 — CF service token wrong scope, wrong binding, or wrong value

**Why:** Either (a) the service token bound to the Access application isn't the one whose values are in the deployment secrets, or (b) the Access policy doesn't include the service token.

**Fix (Cloudflare Zero Trust dashboard):**

1. Service Auth → Service Tokens → confirm `langgraph-cloud-otel` exists, isn't expired
2. Applications → `LangGraph OTel Ingest` → Policies → a policy with `Action: Service Auth` and `Include: Service Token → langgraph-cloud-otel`
3. If the token values in the deployment (from §B.1) don't match the token you see in the Cloudflare dashboard, either re-generate the token and re-run §D.1, or update the deployment secrets to match

**Verify:** re-run C.4; expect `HTTP 400`.

---

## §E — Gate A (final verification)

Runs after any remediation. Gate A has two pass criteria — both must be green.

### E.1 — Trigger a run

```bash
set -a; source .env; set +a

# 1. Look up the needs_assessment assistant UUID
ASSISTANT_ID=$(curl -s -H "x-api-key: $LANGCHAIN_API_KEY" \
  "https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app/assistants/search" \
  -X POST -H "Content-Type: application/json" \
  -d '{"graph_id": "needs_assessment", "limit": 1}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)[0]['assistant_id'])")

# 2. Fire a background run (returns immediately)
curl -sS -X POST -H "x-api-key: $LANGCHAIN_API_KEY" -H "Content-Type: application/json" \
  -d "{\"assistant_id\": \"$ASSISTANT_ID\", \"input\": {\"topic\": \"gate-a-smoke-$(date +%Y%m%d%H%M)\"}}" \
  "https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app/runs" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print('run_id:', d.get('run_id'))"
```

Background run returns immediately. Spans emit as nodes fire via `@traced_node`. Wait **60-90 seconds** for BatchSpanProcessor flush (~5s) + Tempo ingest lag + one metrics_generator remote_write cycle.

### E.2 — Pass criterion 1: Tempo has traces

```bash
curl -s "http://localhost:3200/api/search?tags=service.name%3Ddhg-langgraph-agents&limit=10" \
  | jq '.traces | length'
```

**Pass:** `≥ 1`.
**Fail:** start at §C.2 and walk the ladder.

### E.3 — Pass criterion 2: Prometheus has span-metrics

```bash
curl -s 'http://localhost:9090/api/v1/query?query=traces_spanmetrics_calls_total{service="dhg-langgraph-agents"}' \
  | jq '.data.result | length'
```

**Pass:** `≥ 1`.
**Fail:** start at §C.1. Usually this means Tempo has traces but remote_write is 404-ing → §D.3.

### E.4 — Bonus signal: DHG dashboard panel

`https://app.digitalharmonyai.com/dashboards` → scroll to Panel D1 "LangGraph Agents · Span Telemetry." Should show non-zero for "Node invocations · 15m" and at least one entry in "Top nodes by call count." Same data as E.3, through the product surface. Added in commit `8be7160`.

---

## §F — Phase 2 (Thread-State Exporter)

Tasks 7-13 from v1 are unchanged scope and sound implementation. They build a new `services/langgraph-exporter/` Docker service that polls `/threads/search` on the LangGraph Cloud API every 30s and exposes `langgraph_threads_by_state{state=...}` gauges for the free Prometheus scrape fabric.

**Why this is Phase 2 and not Phase 1:** Phase 1 (span telemetry) must be green before exporter work is worth doing. The exporter is parallel, unrelated infrastructure — if Phase 1 were broken, green Phase 2 metrics would give false confidence by masking the dead upstream path.

**See:** `2026-04-12-langgraph-telemetry-pipeline-repair_v1.md` Tasks 7-13 for full step-by-step implementation. No changes to those tasks are needed — they were never attempted in v1 and are still sound:

- **v1 Task 7** — Exporter scaffold + failing TDD tests (~200 lines)
- **v1 Task 8** — Exporter implementation (httpx poll loop, prometheus_client gauges, error counter)
- **v1 Task 9** — Dockerfile + local build verification
- **v1 Task 10** — Wire service into `docker-compose.override.yml`
- **v1 Task 11** — Add `langgraph-exporter` scrape job to `observability/prometheus/prometheus.yml`
- **v1 Task 12** — Six Phase 1 alert rules in `observability/prometheus/alerts/langgraph.yml`
- **v1 Task 13** — Gate B: end-to-end verification (Gate A signals + `langgraph_threads_by_state` gauge presence + alert rules loaded)

**Gate B:** combines Phase 1 Gate A (from §E above) with:

```bash
curl -s 'http://localhost:9090/api/v1/query?query=langgraph_threads_by_state' \
  | jq '.data.result | length'
# Expect: 5  (one series per state: idle, running, pending, interrupted, error)
```

---

## §G — Plan Failure Mode Inventory

For future-plan hygiene. When authoring a plan like this, explicitly check these modes.

| # | Failure mode | v1 instance | v2 mitigation |
|---|---|---|---|
| G1 | Plan assumes env var contract that doesn't match code | v1 Task 4 Step 3: `OTEL_EXPORTER_OTLP_HEADERS=k=v,k2=v2` vs the actual individual `os.getenv("CF_ACCESS_CLIENT_ID")` lookups | §A pins the contract with file:line references |
| G2 | Plan has no "is this already done?" check before acting | Every v1 task was procedural; nothing said "first look at current state" | §B is a read-only audit that runs first, every time |
| G3 | Plan has a single Gate with generic troubleshooting | v1 Task 6 Gate A: "query Tempo, expect ≥1"; three generic bullet points on fail | §C is a top-down diagnostic ladder with explicit probe → remediation mapping |
| G4 | Remediation is buried inside task steps | To find the Prometheus remote-write fix you had to re-read v1 Task 5 in full | §D is flat, symptom-keyed, one section per fix |
| G5 | Plan doesn't get updated when code gets updated mid-session | Commit `4153902` moved from env-var headers to individual lookups; v1 plan stayed wrong forever | **Rule:** if the code changes §A, §A changes in the same commit |
| G6 | No catalogue of observed failure modes | Each failure had to be recognized from scratch | §G documents them |
| G7 | Plan checks downstream success signals only | v1 Gate A checked "Tempo has traces + Prometheus has metrics" but not "secrets attached to the deployment" — the actual root cause sat one hop upstream | §B and §C explicitly probe upstream state before concluding downstream is broken |

---

## Version History

- **v1** (saved as `2026-04-12-langgraph-telemetry-pipeline-repair_v1.md`): Linear Task 1-13 checklist with checkboxes. Ran in a multi-hour session that failed at Gate A due to §A contract drift (plan vs code on CF secrets) and §D.3 (Prometheus flag never actually applied). All 74 checkboxes remained unchecked even as 9 commits landed — confirming G5.
- **v2** (this file, 2026-04-13): Restructured into reference sections §A-§E + unchanged Phase 2 pointer §F + failure-mode post-mortem §G. Primary discipline change: §A makes the code contract explicit so future drift is caught in code review, not at Gate A.

---

## Recorded Resolutions (2026-04-13 session)

These are the fixes that banked Phase 1 Gate A. Preserved here as ground truth for anyone reading this after the fact.

1. **Revision `7477443f-006a-49f4-8d8a-aef320bbf109` deployed** with `CF_ACCESS_CLIENT_ID` + `CF_ACCESS_CLIENT_SECRET` attached via the LangSmith `+ New Revision` panel. Confirmed via §B.1: deployment secrets went from 4 → 6.
2. **Commit `65d21fc`** added `--web.enable-remote-write-receiver` to `docker-compose.override.yml`. Container recreated at ~20:50Z. Verified via `docker inspect` and the `POST /api/v1/write` probe (404 → 400).
3. **Commit `8be7160`** added the LangGraph span telemetry panel (D1) to `/dashboards`, including five Prometheus queries via the existing `/api/prometheus` proxy.
4. **Gate A verified:** 3 traces in Tempo, 3 series in `traces_spanmetrics_calls_total{service="dhg-langgraph-agents"}`, no remote_write errors in Tempo logs after the Prometheus recreate.
