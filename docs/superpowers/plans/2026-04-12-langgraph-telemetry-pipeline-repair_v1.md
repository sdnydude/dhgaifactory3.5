# LangGraph Telemetry Pipeline Repair — Implementation Plan (Phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the dormant Tempo → Prometheus telemetry pipeline so that LangGraph Cloud spans flow into queryable Prometheus metrics via a free Cloudflare-tunneled OTLP/HTTP endpoint, and add a local exporter for thread-state gauges.

**Architecture:** LangGraph Cloud emits OTLP/HTTP spans through `otel.digitalharmonyai.com` (new Cloudflare Access-gated tunnel route) into `dhg-tempo:4318`. Tempo's `metrics_generator` derives span-metrics and service-graphs and remote-writes them to `dhg-prometheus`. A new `dhg-langgraph-exporter` Docker service polls the LangGraph Cloud `/threads/search` API on a fixed 30-second schedule and exposes `langgraph_threads_by_state{state=...}` gauges for the cost-free Prometheus scrape fabric. Six alert rules are added to catch the most common failure modes.

**Tech Stack:** Python 3.12, `httpx`, `prometheus_client`, OpenTelemetry SDK (HTTP exporter), Docker Compose, Prometheus, Tempo, Cloudflare Tunnel with Access service tokens.

**Spec:** `docs/superpowers/specs/2026-04-12-langgraph-dashboards-design.md`

---

## File Structure

**Files to create:**
- `services/langgraph-exporter/exporter.py` — main service entrypoint (async poll loop + Prometheus gauges)
- `services/langgraph-exporter/test_exporter.py` — unit tests (mocked httpx)
- `services/langgraph-exporter/Dockerfile`
- `services/langgraph-exporter/requirements.txt`
- `observability/prometheus/alerts/langgraph.yml` — Phase 1 alert rules

**Files to modify:**
- `/etc/cloudflared/config.yml` — add `otel.digitalharmonyai.com` ingress rule *(host file, not in repo)*
- `langgraph_workflows/dhg-agents-cloud/src/tracing.py` — swap gRPC → HTTP OTLP exporter import, update default port
- `langgraph_workflows/dhg-agents-cloud/requirements.txt` — ensure `opentelemetry-exporter-otlp-proto-http` is present
- `docker-compose.override.yml` — add `--web.enable-remote-write-receiver` flag to `prometheus` service command, add `dhg-langgraph-exporter` service
- `observability/prometheus/prometheus.yml` — add `langgraph-exporter` scrape job, extend `rule_files` to include `alerts/langgraph.yml`
- `.env` — add `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` entries (values provided manually, never committed; generic naming since only one CF Access service token is in use)

**Production state changes requiring explicit approval before each task:**
- Cloudflare dashboard edits (Task 1)
- Cloudflared systemd restart (Task 2)
- LangGraph Cloud deployment env var edits (Task 4)
- Prometheus container restart (Task 5)
- Production container restarts for the exporter (Tasks 9–11)

---

## Task 1: Cloudflare Access service-token setup (manual prereq)

**Files:** none — this is browser work in the Cloudflare dashboard. Once complete, the service token credentials go into `.env`.

**Why this task exists:** The Cloudflare tunnel needs a protected hostname that only LangGraph Cloud can POST to. Without the Access application + service token, the endpoint would be open to the internet and could be spammed. This is manual because Cloudflare dashboard does not expose these operations via API in the free tier, and the one-time credentials must be pasted into `.env` by a human.

**⚠ Production: requires explicit approval before executing.**

- [ ] **Step 1: Create the DNS record for `otel.digitalharmonyai.com`**

In Cloudflare dashboard → `digitalharmonyai.com` zone → DNS → Records → "Add record":
- Type: `CNAME`
- Name: `otel`
- Target: `30437aa6-d3f8-4c52-85cc-be0a0bfe8478.cfargotunnel.com` (the existing tunnel ID from MEMORY.md)
- Proxy status: Proxied (orange cloud)
- TTL: Auto

Click "Save".

- [ ] **Step 2: Create a Cloudflare Access application**

In Cloudflare dashboard → Zero Trust → Access → Applications → "Add an application" → "Self-hosted":
- Application name: `LangGraph OTel Ingest`
- Session duration: `24 hours`
- Application domain: `otel.digitalharmonyai.com`
- Identity providers: leave default
- Skip the "Configure app launcher" step
- Policies: click "Next" (service-token-only policy is added in the next step)

Click "Save".

- [ ] **Step 3: Create a service token**

In the same Access section → Service Auth → Service Tokens → "Create Service Token":
- Name: `langgraph-cloud-otel`
- Duration: `Non-expiring`

Click "Generate token". Cloudflare shows the Client ID and Client Secret **once**. Copy both immediately.

- [ ] **Step 4: Bind the service token to the application**

Go back to Access → Applications → `LangGraph OTel Ingest` → Edit → Policies → "Add a policy":
- Policy name: `allow-langgraph-cloud`
- Action: `Service Auth`
- Include: `Service Token` → select `langgraph-cloud-otel`

Click "Save".

- [ ] **Step 5: Store credentials in `.env`**

Append to `/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/.env`:

```
# Cloudflare Access service token (single token reused for all Access-protected hostnames)
CF_ACCESS_CLIENT_ID=<client-id-from-step-3>
CF_ACCESS_CLIENT_SECRET=<client-secret-from-step-3>
```

Replace `<...>` with the actual values. **Never commit these.** `.env` is already in `.gitignore` — confirm with:

```bash
grep -E "^\.env$" .gitignore
```

Expected output: `.env`

- [ ] **Step 6: Commit nothing yet**

This task intentionally produces no commit. The credentials are operational state, not code.

---

## Task 2: Add `otel.digitalharmonyai.com` route to the cloudflared tunnel

**Files:**
- Modify: `/etc/cloudflared/config.yml` (host file, requires `sudo`)

**Why this task exists:** The DNS record created in Task 1 points at the tunnel, but the tunnel does not yet know how to route traffic for `otel.digitalharmonyai.com` — we have to add an ingress rule.

**⚠ Production: requires explicit approval before executing.**

- [ ] **Step 1: Read the current cloudflared config**

```bash
sudo cat /etc/cloudflared/config.yml
```

Expected output: a YAML file with a `tunnel:` line, a `credentials-file:` line, and an `ingress:` list containing entries for `app.digitalharmonyai.com` and `vs.digitalharmonyai.com` before a catch-all `- service: http_status:404`.

- [ ] **Step 2: Back up the current config**

```bash
sudo cp /etc/cloudflared/config.yml /etc/cloudflared/config.yml.bak-2026-04-12
```

Expected: no output on success. Verify with `sudo ls -l /etc/cloudflared/config.yml.bak-2026-04-12`.

- [ ] **Step 3: Add the new ingress rule**

Insert a new ingress entry *before* the catch-all `http_status:404` line. The added block is:

```yaml
  - hostname: otel.digitalharmonyai.com
    service: http://localhost:4318
    originRequest:
      connectTimeout: 10s
      noHappyEyeballs: true
```

Edit with `sudoedit /etc/cloudflared/config.yml` (or `sudo nano /etc/cloudflared/config.yml`). The file should end up looking like:

```yaml
tunnel: 30437aa6-d3f8-4c52-85cc-be0a0bfe8478
credentials-file: /etc/cloudflared/30437aa6-d3f8-4c52-85cc-be0a0bfe8478.json

ingress:
  - hostname: app.digitalharmonyai.com
    service: http://localhost:3000
  - hostname: vs.digitalharmonyai.com
    service: http://localhost:8013
  - hostname: otel.digitalharmonyai.com
    service: http://localhost:4318
    originRequest:
      connectTimeout: 10s
      noHappyEyeballs: true
  - service: http_status:404
```

(The existing entries may differ slightly — preserve whatever is already there; only insert the new `otel.digitalharmonyai.com` block before the catch-all.)

- [ ] **Step 4: Validate the config**

```bash
sudo cloudflared tunnel --config /etc/cloudflared/config.yml ingress validate
```

Expected output: `Validating rules from /etc/cloudflared/config.yml ... OK`.

If validation fails, restore the backup with `sudo cp /etc/cloudflared/config.yml.bak-2026-04-12 /etc/cloudflared/config.yml` and investigate before retrying.

- [ ] **Step 5: Restart cloudflared**

```bash
sudo systemctl restart cloudflared
sudo systemctl status cloudflared --no-pager | head -20
```

Expected: `Active: active (running)`, no `ERR` lines in recent log output.

- [ ] **Step 6: Verify the new route is reachable (from an internet client)**

From any machine (including g700data1 itself):

```bash
curl -sS -X POST \
  -H "Content-Type: application/x-protobuf" \
  -H "CF-Access-Client-Id: ${CF_ACCESS_CLIENT_ID}" \
  -H "CF-Access-Client-Secret: ${CF_ACCESS_CLIENT_SECRET}" \
  --data-binary @/dev/null \
  https://otel.digitalharmonyai.com/v1/traces -o /dev/null -w "HTTP %{http_code}\n"
```

Expected: `HTTP 400` (Tempo rejects an empty protobuf body — that's fine; it proves the tunnel reaches Tempo and Access authorizes the request).

Troubleshooting: if you see `HTTP 403`, the Access policy is wrong. If you see `HTTP 530`, the tunnel is not routing yet (wait 30s and retry). If you see `HTTP 000`, DNS has not propagated.

- [ ] **Step 7: No commit** — host config files are not in the repo.

---

## Task 3: Swap `tracing.py` to the OTLP/HTTP exporter

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/src/tracing.py:34` (import), `:51` (default endpoint), `:69-72` (exporter instantiation)

**Why this task exists:** The current gRPC exporter targets `http://localhost:4317`, which cannot be tunneled through Cloudflare without `http2Origin: true` and strict TLS-ALPN handling. Switching to OTLP/HTTP lets the spans traverse the existing HTTPS tunnel like any other request. This is a three-line code change.

- [ ] **Step 1: Read the current file and confirm line numbers**

```bash
sed -n '30,80p' langgraph_workflows/dhg-agents-cloud/src/tracing.py
```

Expected: the imports block, `TEMPO_ENDPOINT` assignment, and `_exporter = OTLPSpanExporter(...)` call match the locations listed above.

- [ ] **Step 2: Swap the import**

Change line 34:

```python
# Before
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# After
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
```

- [ ] **Step 3: Update the default endpoint port**

Change the fallback in the `TEMPO_ENDPOINT` declaration (around line 49–52):

```python
# Before
TEMPO_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "http://localhost:4317",
)

# After
TEMPO_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "http://localhost:4318",
)
```

- [ ] **Step 4: Simplify the exporter instantiation**

Change lines 69–72:

```python
# Before
    _exporter = OTLPSpanExporter(
        endpoint=TEMPO_ENDPOINT,
        insecure=True,
    )

# After — OTLP/HTTP exporter reads OTEL_EXPORTER_OTLP_ENDPOINT and
# OTEL_EXPORTER_OTLP_HEADERS from the environment automatically.
# Passing them explicitly would force local callers to format the
# /v1/traces suffix themselves. Letting the SDK handle it is cleaner.
    _exporter = OTLPSpanExporter()
```

The HTTP exporter does not accept an `insecure` kwarg (the scheme in the URL handles it), so removing it prevents a `TypeError` at import time.

- [ ] **Step 5: Run existing tracing-adjacent tests**

```bash
cd langgraph_workflows/dhg-agents-cloud
python -c "from src.tracing import traced_node, get_tracer; print('import ok')"
```

Expected: `import ok`. If it errors with `ModuleNotFoundError: opentelemetry.exporter.otlp.proto.http`, the HTTP exporter package is not installed locally — continue to Task 4 Step 2 which adds it to the requirements file.

- [ ] **Step 6: Commit**

```bash
git add langgraph_workflows/dhg-agents-cloud/src/tracing.py
git commit -m "fix(tracing): swap OTLP gRPC exporter for HTTP exporter

Prepares LangGraph Cloud for tunneled span export via
otel.digitalharmonyai.com. The HTTP exporter traverses
Cloudflare tunnels without http2Origin configuration and
reads endpoint + headers from OTEL_EXPORTER_OTLP_* env vars."
```

---

## Task 4: Configure LangGraph Cloud deployment for OTLP/HTTP export

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/requirements.txt` — ensure `opentelemetry-exporter-otlp-proto-http` is listed
- Modify: LangGraph Cloud deployment environment (via the LangSmith / LangGraph Cloud dashboard or `langgraph` CLI)

**Why this task exists:** `tracing.py` silently no-ops if the OTel wheels are missing from the Cloud runtime, so we must guarantee the HTTP exporter package is installed in the deployment image. The env vars tell the exporter where to send spans and how to authenticate.

**⚠ Production: requires explicit approval before Step 3.**

- [ ] **Step 1: Read the current requirements file**

```bash
grep -n "opentelemetry" langgraph_workflows/dhg-agents-cloud/requirements.txt
```

Expected output: entries for `opentelemetry-api`, `opentelemetry-sdk`, and either `opentelemetry-exporter-otlp-proto-grpc` or `opentelemetry-exporter-otlp-proto-http` (ideally both, to keep local gRPC dev working).

- [ ] **Step 2: Add the HTTP exporter package if missing**

If `opentelemetry-exporter-otlp-proto-http` is not already present, append it to `langgraph_workflows/dhg-agents-cloud/requirements.txt`:

```
opentelemetry-exporter-otlp-proto-http>=1.25.0
```

Leave any existing `opentelemetry-exporter-otlp-proto-grpc` line in place — removing it would break anyone running the graphs locally against the existing gRPC endpoint.

- [ ] **Step 3: Set env vars on the LangGraph Cloud deployment**

In the LangSmith dashboard → Deployments → `dhg-agents` → Environment Variables → Add:

```
OTEL_EXPORTER_OTLP_ENDPOINT = https://otel.digitalharmonyai.com
OTEL_EXPORTER_OTLP_HEADERS = CF-Access-Client-Id=<value from .env>,CF-Access-Client-Secret=<value from .env>
```

Important: the `OTEL_EXPORTER_OTLP_HEADERS` value is a **single string** with comma-separated `key=value` pairs, no spaces, no quotes. The OTel SDK parses it directly.

Save, then trigger a redeploy (LangGraph Cloud rebuilds the image when requirements or env vars change).

- [ ] **Step 4: Wait for redeploy and check logs**

In the LangSmith dashboard → Deployments → `dhg-agents` → Logs. Wait for the new revision to go live. Search for the log line:

```
OpenTelemetry initialized: service=dhg-langgraph-agents endpoint=https://otel.digitalharmonyai.com env=production
```

If you see `OpenTelemetry not available — tracing disabled`, the HTTP exporter package did not make it into the image — re-check Step 2 and redeploy.

- [ ] **Step 5: Commit the requirements change**

```bash
git add langgraph_workflows/dhg-agents-cloud/requirements.txt
git commit -m "feat(tracing): add OTLP/HTTP exporter to cloud requirements

Required for LangGraph Cloud to emit spans through the
Cloudflare-tunneled otel.digitalharmonyai.com endpoint."
```

---

## Task 5: Enable Prometheus remote-write receiver

**Files:**
- Modify: `docker-compose.override.yml` — add `--web.enable-remote-write-receiver` flag to the `prometheus` service `command:` list

**Why this task exists:** Tempo's `metrics_generator` is configured to push derived span-metrics and service-graph metrics to Prometheus via remote_write. Prometheus rejects remote writes unless this flag is set, so the derived metrics currently vanish on arrival.

**⚠ Production: requires explicit approval before Step 3 (container restart).**

- [ ] **Step 1: Read the current Prometheus command block**

```bash
grep -n -A 10 "prometheus:" docker-compose.override.yml | head -30
```

Expected: the `command:` list currently has `--config.file`, `--storage.tsdb.path`, and `--storage.tsdb.retention.time` entries, but no `--web.enable-remote-write-receiver`.

- [ ] **Step 2: Add the flag**

Edit `docker-compose.override.yml`. Find the `prometheus` service block and add one line to its `command:` list:

```yaml
  prometheus:
    image: prom/prometheus:v2.48.0
    container_name: dhg-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./observability/prometheus:/etc/prometheus
      - prometheus_data:/prometheus
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-remote-write-receiver'   # <-- new
    healthcheck:
      ...
```

- [ ] **Step 3: Recreate the Prometheus container**

```bash
docker compose up -d prometheus
```

Expected: `Recreating dhg-prometheus ... done`. The container restarts with the new flag.

- [ ] **Step 4: Verify the flag is active**

```bash
docker inspect dhg-prometheus --format '{{.Config.Cmd}}' | tr ' ' '\n' | grep remote-write
```

Expected: `--web.enable-remote-write-receiver`

```bash
docker logs dhg-prometheus 2>&1 | tail -20 | grep -i "remote"
```

Expected: a log line mentioning remote write being enabled (text varies by version).

- [ ] **Step 5: Smoke-test the remote_write endpoint**

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST \
  -H "Content-Type: application/x-protobuf" \
  --data-binary "" \
  http://localhost:9090/api/v1/write
```

Expected: `HTTP 400` (Prometheus accepts the POST but rejects the empty body — that's the right answer; before the flag it would have been `HTTP 404`).

- [ ] **Step 6: Commit**

```bash
git add docker-compose.override.yml
git commit -m "feat(prometheus): enable remote-write receiver for Tempo metrics

Unblocks the Tempo metrics_generator remote_write path so
span-metrics and service-graph metrics land in Prometheus."
```

---

## Task 6: Phase 1 Gate A — verify end-to-end span flow

**Files:** none (verification only)

**Why this task exists:** Before building the exporter on top of this pipeline, we need to prove that a real span from LangGraph Cloud actually traverses the full path: Cloud → tunnel → Tempo → remote_write → Prometheus. This is a gate: if it fails, Tasks 7–13 are premature.

- [ ] **Step 1: Trigger a LangGraph run**

From the DHG frontend or via the LangGraph SDK, start a `needs_assessment` run (the smallest graph). Any real invocation works. Note the trace ID or thread ID.

- [ ] **Step 2: Wait 30 seconds, then query Tempo for the trace**

```bash
curl -s "http://localhost:3200/api/search?tags=service.name%3Ddhg-langgraph-agents&limit=5" | jq '.traces | length'
```

Expected: `>= 1`.

If it returns `0`, check:
1. `docker logs dhg-tempo --tail 50 | grep -i error`
2. LangSmith dashboard logs for the deployment — look for `OpenTelemetry initialized:` and any exporter errors.
3. Re-verify the tunnel test from Task 2 Step 6.

- [ ] **Step 3: Verify Tempo is pushing metrics to Prometheus**

```bash
curl -s http://localhost:9090/api/v1/query?query=tempo_distributor_metrics_generator_clients | jq '.data.result[0].value[1]'
```

Expected: a string like `"1"` (not `"0"`). This indicates Tempo's metrics-generator has at least one active client pushing remote writes.

- [ ] **Step 4: Query Prometheus for derived span-metrics**

```bash
curl -s 'http://localhost:9090/api/v1/query?query=traces_spanmetrics_calls_total' | jq '.data.result | length'
```

Expected: `>= 1`.

This is the definitive success signal for Phase 1 Gate A: LangGraph spans are flowing, Tempo is deriving metrics, and Prometheus is accepting them.

- [ ] **Step 5: Record gate-pass in plan tracking**

No commit. If this gate passes, proceed to Task 7. If it fails after troubleshooting, stop and reassess — do not build the exporter on an unverified pipeline.

---

## Task 7: Thread-state exporter — scaffold + failing tests (TDD)

**Files:**
- Create: `services/langgraph-exporter/test_exporter.py`
- Create: `services/langgraph-exporter/exporter.py` (empty stub only for this task)
- Create: `services/langgraph-exporter/requirements.txt`

**Why this task exists:** The exporter bridges the metered LangGraph Cloud API into the free Prometheus scrape fabric. TDD here protects against silent regressions in the parsing logic (miscounting thread states would directly corrupt dashboard data).

- [ ] **Step 1: Create the service directory**

```bash
mkdir -p services/langgraph-exporter
```

- [ ] **Step 2: Write `requirements.txt`**

Create `services/langgraph-exporter/requirements.txt`:

```
httpx==0.27.0
prometheus-client==0.20.0
pytest==8.2.0
pytest-asyncio==0.23.6
respx==0.21.1
```

(`respx` provides httpx mocking for unit tests.)

- [ ] **Step 3: Write the empty stub `exporter.py`**

Create `services/langgraph-exporter/exporter.py` with just enough to be importable:

```python
"""DHG LangGraph thread-state exporter.

Polls the LangGraph Cloud /threads/search endpoint once per state
and exposes thread counts as Prometheus gauges.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Iterable

import httpx
from prometheus_client import Gauge, Counter, CollectorRegistry, generate_latest

logger = logging.getLogger(__name__)

THREAD_STATES: tuple[str, ...] = (
    "idle",
    "running",
    "pending",
    "interrupted",
    "error",
)


def build_registry() -> tuple[CollectorRegistry, Gauge, Gauge, Counter]:
    """Create a fresh Prometheus registry and the three exported metrics.

    Returning a fresh registry per call keeps unit tests isolated —
    production uses a module-level singleton created in main().
    """
    raise NotImplementedError  # implemented in Task 8


async def scrape_once(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    states: Iterable[str] = THREAD_STATES,
) -> dict[str, int]:
    """Issue one /threads/search call per state and return counts.

    Raises httpx.HTTPError on network or HTTP failures so the caller can
    count them and freeze gauges at last-known values.
    """
    raise NotImplementedError  # implemented in Task 8
```

- [ ] **Step 4: Write the failing tests**

Create `services/langgraph-exporter/test_exporter.py`:

```python
"""Unit tests for the LangGraph thread-state exporter."""

from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response
from prometheus_client import generate_latest

from exporter import (
    THREAD_STATES,
    build_registry,
    scrape_once,
)


BASE_URL = "https://example.langgraph.app"
API_KEY = "test-key-1234567890"


def _threads_payload(n: int) -> list[dict]:
    return [{"thread_id": f"t-{i}", "status": "any"} for i in range(n)]


@pytest.fixture
def reg():
    return build_registry()


def test_build_registry_exposes_three_metric_families(reg):
    registry, threads_gauge, ts_gauge, err_counter = reg
    exposition = generate_latest(registry).decode()
    assert "langgraph_threads_by_state" in exposition
    assert "langgraph_exporter_last_scrape_timestamp_seconds" in exposition
    assert "langgraph_exporter_scrape_errors_total" in exposition


def test_build_registry_initializes_all_five_state_labels(reg):
    registry, threads_gauge, ts_gauge, err_counter = reg
    exposition = generate_latest(registry).decode()
    for state in THREAD_STATES:
        assert f'langgraph_threads_by_state{{state="{state}"}}' in exposition


@pytest.mark.asyncio
@respx.mock
async def test_scrape_once_counts_threads_per_state():
    respx.post(f"{BASE_URL}/threads/search").mock(
        side_effect=[
            Response(200, json=_threads_payload(3)),  # idle
            Response(200, json=_threads_payload(2)),  # running
            Response(200, json=_threads_payload(0)),  # pending
            Response(200, json=_threads_payload(1)),  # interrupted
            Response(200, json=_threads_payload(0)),  # error
        ]
    )
    async with AsyncClient() as client:
        counts = await scrape_once(client, BASE_URL, API_KEY)
    assert counts == {
        "idle": 3,
        "running": 2,
        "pending": 0,
        "interrupted": 1,
        "error": 0,
    }


@pytest.mark.asyncio
@respx.mock
async def test_scrape_once_sends_api_key_header():
    route = respx.post(f"{BASE_URL}/threads/search").mock(
        return_value=Response(200, json=[])
    )
    async with AsyncClient() as client:
        await scrape_once(client, BASE_URL, API_KEY)
    assert route.called
    sent = route.calls[0].request
    assert sent.headers.get("x-api-key") == API_KEY


@pytest.mark.asyncio
@respx.mock
async def test_scrape_once_raises_on_http_error():
    respx.post(f"{BASE_URL}/threads/search").mock(return_value=Response(503))
    async with AsyncClient() as client:
        with pytest.raises(Exception):
            await scrape_once(client, BASE_URL, API_KEY)
```

- [ ] **Step 5: Run the tests and confirm they fail**

```bash
cd services/langgraph-exporter
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -v
```

Expected: all tests fail with `NotImplementedError` (for `build_registry` and `scrape_once`). This is the correct TDD starting state.

- [ ] **Step 6: Commit the failing-test scaffold**

```bash
git add services/langgraph-exporter/
git commit -m "test(langgraph-exporter): scaffold + failing tests

Sets up the thread-state exporter service with TDD-first
failing tests for registry construction and scrape_once()."
```

---

## Task 8: Thread-state exporter — implementation

**Files:**
- Modify: `services/langgraph-exporter/exporter.py` — implement `build_registry`, `scrape_once`, and a `main()` poll loop

**Why this task exists:** Turn the failing tests green and add the minimal main loop that wires everything together.

- [ ] **Step 1: Implement `build_registry`**

Replace the `build_registry` stub in `services/langgraph-exporter/exporter.py`:

```python
def build_registry() -> tuple[CollectorRegistry, Gauge, Gauge, Counter]:
    """Create a fresh Prometheus registry and the three exported metrics.

    Returning a fresh registry per call keeps unit tests isolated —
    production uses a module-level singleton created in main().
    """
    registry = CollectorRegistry()
    threads_gauge = Gauge(
        "langgraph_threads_by_state",
        "Count of LangGraph threads currently in each state.",
        labelnames=("state",),
        registry=registry,
    )
    for state in THREAD_STATES:
        threads_gauge.labels(state=state).set(0)

    last_scrape = Gauge(
        "langgraph_exporter_last_scrape_timestamp_seconds",
        "Unix timestamp of the last successful Cloud API scrape.",
        registry=registry,
    )
    last_scrape.set(0)

    errors = Counter(
        "langgraph_exporter_scrape_errors_total",
        "Total Cloud API scrape errors since exporter start.",
        registry=registry,
    )
    return registry, threads_gauge, last_scrape, errors
```

- [ ] **Step 2: Implement `scrape_once`**

Replace the `scrape_once` stub in the same file:

```python
async def scrape_once(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    states: Iterable[str] = THREAD_STATES,
) -> dict[str, int]:
    """Issue one /threads/search call per state and return counts.

    Raises httpx.HTTPError on network or HTTP failures so the caller can
    count them and freeze gauges at last-known values.
    """
    headers = {"x-api-key": api_key, "content-type": "application/json"}
    counts: dict[str, int] = {}
    for state in states:
        resp = await client.post(
            f"{base_url}/threads/search",
            headers=headers,
            json={"status": state, "limit": 1000},
            timeout=10.0,
        )
        resp.raise_for_status()
        payload = resp.json()
        counts[state] = len(payload) if isinstance(payload, list) else 0
    return counts
```

- [ ] **Step 3: Run tests, expect PASS**

```bash
cd services/langgraph-exporter
source .venv/bin/activate
pytest -v
```

Expected: `5 passed`.

- [ ] **Step 4: Add the main poll loop and HTTP server**

Append to `services/langgraph-exporter/exporter.py`:

```python
# ---------------------------------------------------------------------------
# Production entrypoint
# ---------------------------------------------------------------------------

from aiohttp import web  # noqa: E402  (imported here to keep unit tests fast)


SCRAPE_INTERVAL_SECONDS = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "30"))
LANGGRAPH_URL = os.getenv(
    "LANGGRAPH_API_URL",
    "https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app",
)
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
PORT = int(os.getenv("EXPORTER_PORT", "8014"))


async def _poll_loop(
    client: httpx.AsyncClient,
    threads_gauge: Gauge,
    last_scrape: Gauge,
    errors: Counter,
) -> None:
    while True:
        try:
            counts = await scrape_once(client, LANGGRAPH_URL, LANGCHAIN_API_KEY)
            for state, n in counts.items():
                threads_gauge.labels(state=state).set(n)
            last_scrape.set(time.time())
        except Exception as exc:  # noqa: BLE001 — we want to catch every failure
            errors.inc()
            logger.warning("Scrape failed: %s", exc)
        await asyncio.sleep(SCRAPE_INTERVAL_SECONDS)


async def _metrics_handler(request: web.Request) -> web.Response:
    registry = request.app["registry"]
    return web.Response(
        body=generate_latest(registry),
        headers={"Content-Type": "text/plain; version=0.0.4; charset=utf-8"},
    )


async def _health_handler(request: web.Request) -> web.Response:
    return web.Response(text="ok")


def _must_have_api_key() -> None:
    if not LANGCHAIN_API_KEY:
        raise SystemExit(
            "LANGCHAIN_API_KEY env var is required but not set."
        )


async def _main_async() -> None:
    _must_have_api_key()
    registry, threads_gauge, last_scrape, errors = build_registry()

    app = web.Application()
    app["registry"] = registry
    app.router.add_get("/metrics", _metrics_handler)
    app.router.add_get("/healthz", _health_handler)

    async with httpx.AsyncClient() as client:
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logger.info(
            "exporter ready: port=%s url=%s interval=%ds",
            PORT,
            LANGGRAPH_URL,
            SCRAPE_INTERVAL_SECONDS,
        )
        await _poll_loop(client, threads_gauge, last_scrape, errors)


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Add `aiohttp` to requirements**

Append to `services/langgraph-exporter/requirements.txt`:

```
aiohttp==3.9.5
```

Reinstall:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 6: Re-run tests to confirm still green**

```bash
pytest -v
```

Expected: `5 passed`. The main-loop additions are not exercised by unit tests (that's an integration concern handled in Task 10).

- [ ] **Step 7: Commit**

```bash
git add services/langgraph-exporter/
git commit -m "feat(langgraph-exporter): implement poll loop + /metrics server

build_registry() exposes the three contract metrics with all
five state labels pre-initialized to 0. scrape_once() issues
one /threads/search call per state. The main async loop polls
every SCRAPE_INTERVAL_SECONDS (default 30) and serves metrics
on port 8014 via aiohttp."
```

---

## Task 9: Thread-state exporter — Dockerfile + local build verification

**Files:**
- Create: `services/langgraph-exporter/Dockerfile`
- Create: `services/langgraph-exporter/.dockerignore`

- [ ] **Step 1: Write the Dockerfile**

Create `services/langgraph-exporter/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY exporter.py .

EXPOSE 8014

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8014/healthz || exit 1

CMD ["python", "exporter.py"]
```

- [ ] **Step 2: Write `.dockerignore`**

Create `services/langgraph-exporter/.dockerignore`:

```
.venv
__pycache__
*.pyc
test_exporter.py
```

(Test file is excluded from the image to keep it small.)

- [ ] **Step 3: Build the image**

```bash
docker build -t dhg-langgraph-exporter:dev services/langgraph-exporter/
```

Expected: successful build ending in `Successfully tagged dhg-langgraph-exporter:dev`.

- [ ] **Step 4: Smoke-run the container without real API access**

```bash
docker run --rm -e LANGCHAIN_API_KEY=fake -e LANGGRAPH_API_URL=http://nonexistent.invalid \
  -p 18014:8014 dhg-langgraph-exporter:dev &
DOCKER_PID=$!
sleep 3
curl -s http://localhost:18014/metrics | grep -E "^langgraph_" | head -20
kill $DOCKER_PID
```

Expected: output includes all five `langgraph_threads_by_state{state="..."} 0.0` lines, plus `langgraph_exporter_last_scrape_timestamp_seconds 0.0` and `langgraph_exporter_scrape_errors_total` (value will be >0 once the first poll fails against the fake URL).

- [ ] **Step 5: Commit**

```bash
git add services/langgraph-exporter/Dockerfile services/langgraph-exporter/.dockerignore
git commit -m "feat(langgraph-exporter): add Dockerfile + healthcheck"
```

---

## Task 10: Wire the exporter into docker-compose.override.yml

**Files:**
- Modify: `docker-compose.override.yml` — add the `langgraph-exporter` service block

**⚠ Production: requires explicit approval before Step 3 (bringing up the service on the live network).**

- [ ] **Step 1: Add the service block**

Insert after the existing `vs-engine:` block (and before the `volumes:` section at the bottom) in `docker-compose.override.yml`:

```yaml
  langgraph-exporter:
    build:
      context: ./services/langgraph-exporter
      dockerfile: Dockerfile
    container_name: dhg-langgraph-exporter
    environment:
      - LANGCHAIN_API_KEY=${LANGCHAIN_API_KEY}
      - LANGGRAPH_API_URL=${LANGGRAPH_API_URL:-https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app}
      - SCRAPE_INTERVAL_SECONDS=30
      - LOG_LEVEL=INFO
    labels:
      prometheus.io/scrape: "true"
      prometheus.io/port: "8014"
      prometheus.io/path: "/metrics"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8014/healthz"]
      interval: 30s
      timeout: 5s
      retries: 3
    networks:
      - dhg-network
    restart: unless-stopped
```

Note: we do **not** expose port 8014 to the host. Prometheus will scrape via the container network, and there's no reason to bind it externally.

- [ ] **Step 2: Validate the compose file**

```bash
docker compose config --quiet
```

Expected: no output (success) or a specific error message if YAML is malformed.

- [ ] **Step 3: Bring up the service**

```bash
docker compose up -d langgraph-exporter
docker compose ps langgraph-exporter
```

Expected: state `Up (healthy)` within 60 seconds. If it shows `Up (unhealthy)`, check logs:

```bash
docker logs dhg-langgraph-exporter --tail 50
```

- [ ] **Step 4: Verify the exporter is actually scraping the Cloud API**

```bash
docker exec dhg-langgraph-exporter curl -s http://localhost:8014/metrics | \
  grep -E "^langgraph_exporter_last_scrape_timestamp_seconds"
```

Expected: a non-zero Unix timestamp (`langgraph_exporter_last_scrape_timestamp_seconds 1.712...e+09`). If it's `0`, the first poll has not completed or is failing — check `langgraph_exporter_scrape_errors_total` and the container logs.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.override.yml
git commit -m "feat(compose): add dhg-langgraph-exporter service

Exposes langgraph_threads_by_state gauges on the container
network for Prometheus to scrape. Shares LANGCHAIN_API_KEY
with the existing inbox proxy."
```

---

## Task 11: Add the Prometheus scrape job

**Files:**
- Modify: `observability/prometheus/prometheus.yml` — append a new scrape_config entry

- [ ] **Step 1: Append the scrape job**

Add to the bottom of the `scrape_configs:` list in `observability/prometheus/prometheus.yml`:

```yaml
  # LangGraph thread-state exporter — bridges Cloud API into free Prometheus scrape fabric
  - job_name: 'langgraph-exporter'
    static_configs:
      - targets: ['dhg-langgraph-exporter:8014']
        labels:
          service: 'langgraph-exporter'
    metrics_path: /metrics
    scrape_interval: 30s
```

- [ ] **Step 2: Reload the Prometheus config in place**

```bash
curl -s -X POST http://localhost:9090/-/reload
```

Expected: empty response body, HTTP 200. Verify with:

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST http://localhost:9090/-/reload
```

Expected: `HTTP 200`.

- [ ] **Step 3: Verify the target is being scraped**

```bash
curl -s 'http://localhost:9090/api/v1/targets?state=active' | \
  jq '.data.activeTargets[] | select(.labels.job=="langgraph-exporter") | {health, lastScrape, lastError}'
```

Expected: `health: "up"`, a recent `lastScrape` timestamp, and `lastError: ""`.

- [ ] **Step 4: Query the new metric**

```bash
curl -s 'http://localhost:9090/api/v1/query?query=langgraph_threads_by_state' | \
  jq '.data.result | length'
```

Expected: `5` (one series per state label).

- [ ] **Step 5: Commit**

```bash
git add observability/prometheus/prometheus.yml
git commit -m "feat(prometheus): scrape dhg-langgraph-exporter"
```

---

## Task 12: Phase 1 alert rules

**Files:**
- Create: `observability/prometheus/alerts/langgraph.yml`
- Modify: `observability/prometheus/prometheus.yml` — add the new rules file to `rule_files:`

- [ ] **Step 1: Create the rules directory**

```bash
mkdir -p observability/prometheus/alerts
```

- [ ] **Step 2: Write the alert rules file**

Create `observability/prometheus/alerts/langgraph.yml`:

```yaml
groups:
  - name: langgraph
    interval: 30s
    rules:

      # Per-graph error rate over the last 5 minutes, >5% for 5m
      - alert: LangGraphHighErrorRate
        expr: |
          (
            sum by (service_name) (
              rate(traces_spanmetrics_calls_total{status_code="STATUS_CODE_ERROR"}[5m])
            )
            /
            sum by (service_name) (
              rate(traces_spanmetrics_calls_total[5m])
            )
          ) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LangGraph graph {{ $labels.service_name }} error rate > 5%"
          description: "5-minute error rate has been above 5% for the last 5 minutes."

      # Per-node p95 latency > 30 seconds for 10m
      # Starting threshold — tune per-node after 1 week of observed data (see spec open question #1)
      - alert: LangGraphSlowNode
        expr: |
          histogram_quantile(
            0.95,
            sum by (le, span_name, service_name) (
              rate(traces_spanmetrics_latency_bucket[10m])
            )
          ) > 30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "LangGraph node {{ $labels.span_name }} in {{ $labels.service_name }} p95 > 30s"
          description: "p95 latency has been above 30s for 10m. Tune per-node thresholds as data accumulates."

      # No spans from a specific graph for 10m during business hours (9–18 America/Los_Angeles)
      - alert: LangGraphNoTraffic
        expr: |
          sum by (service_name) (
            rate(traces_spanmetrics_calls_total[10m])
          ) == 0
          and on() (hour() >= 17 and hour() < 2)  # 09:00–18:00 PT in UTC (winter)
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "LangGraph graph {{ $labels.service_name }} idle during business hours"
          description: "No spans received in 10 minutes during expected active window."

      # Thread stuck in running state via the exporter — using the running gauge as a proxy.
      # If the running count stays > 0 AND does not change for 30m, something is stuck.
      - alert: LangGraphStuckThread
        expr: |
          langgraph_threads_by_state{state="running"} > 0
          and
          (
            langgraph_threads_by_state{state="running"}
            -
            langgraph_threads_by_state{state="running"} offset 30m
            == 0
          )
        for: 30m
        labels:
          severity: critical
        annotations:
          summary: "LangGraph has stuck running threads"
          description: "At least one thread has been in running state for > 30m without state change."

      # Exporter has not scraped Cloud API in 90 seconds
      - alert: LangGraphExporterStalled
        expr: |
          (time() - langgraph_exporter_last_scrape_timestamp_seconds) > 90
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "LangGraph exporter scrape stalled"
          description: "langgraph_exporter_last_scrape_timestamp_seconds is > 90s old."

      # No spans arriving at Tempo's ingest pipeline for 10m
      - alert: OtelIngestStalled
        expr: |
          rate(tempo_distributor_spans_received_total[10m]) == 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "OTel ingest to Tempo stalled"
          description: "tempo_distributor_spans_received_total has a zero rate for 10 minutes."
```

- [ ] **Step 3: Extend `rule_files:` in `prometheus.yml`**

Edit `observability/prometheus/prometheus.yml`. Change:

```yaml
# Load alert rules
rule_files:
  - 'alerts.yml'
```

to:

```yaml
# Load alert rules
rule_files:
  - 'alerts.yml'
  - 'alerts/langgraph.yml'
```

- [ ] **Step 4: Validate the rules with `promtool`**

```bash
docker exec dhg-prometheus promtool check rules /etc/prometheus/alerts/langgraph.yml
```

Expected: `SUCCESS: 6 rules found`.

If validation fails, fix the indicated line and re-run. Do not proceed to Step 5 with broken rules — Prometheus will reject the reload.

- [ ] **Step 5: Reload Prometheus and verify the new rules are loaded**

```bash
curl -s -X POST http://localhost:9090/-/reload
curl -s 'http://localhost:9090/api/v1/rules' | \
  jq '.data.groups[] | select(.name=="langgraph") | .rules | length'
```

Expected: `6`.

- [ ] **Step 6: Commit**

```bash
git add observability/prometheus/alerts/langgraph.yml observability/prometheus/prometheus.yml
git commit -m "feat(alerts): add six LangGraph Phase 1 alert rules

Covers error rate, slow nodes, idle graphs during business hours,
stuck threads, exporter freshness, and OTel ingest freshness."
```

---

## Task 13: Phase 1 Gate B — end-to-end verification

**Files:** none (verification only)

**Why this task exists:** Close the loop. Every piece built in Tasks 1–12 must be operating in concert for Phase 1 to be declared done.

- [ ] **Step 1: Confirm all Phase 1 success criteria from the spec**

Run each check and record the output:

```bash
# 1. Synthetic span ends up in Tempo
curl -s "http://localhost:3200/api/search?tags=service.name%3Ddhg-langgraph-agents&limit=1" | jq '.traces | length'
# Expected: >= 1

# 2. span-metrics present for every invoked graph
curl -s 'http://localhost:9090/api/v1/query?query=count%20by%20(service_name)%20(traces_spanmetrics_calls_total)' | jq '.data.result | length'
# Expected: >= 1 (grows as more graphs are invoked)

# 3. Thread-state metrics scraped
curl -s 'http://localhost:9090/api/v1/query?query=langgraph_threads_by_state' | jq '.data.result | length'
# Expected: 5

# 4. All six alert rules loaded
curl -s 'http://localhost:9090/api/v1/rules' | jq '[.data.groups[] | select(.name=="langgraph") | .rules[]] | length'
# Expected: 6

# 5. Exporter freshness
curl -s 'http://localhost:9090/api/v1/query?query=time()%20-%20langgraph_exporter_last_scrape_timestamp_seconds' | jq -r '.data.result[0].value[1]'
# Expected: < 60 (seconds since last scrape)
```

- [ ] **Step 2: Synthetic alert firing test**

Temporarily tighten one alert rule to force it to fire, confirm Alertmanager receives it, then revert. Pick `LangGraphExporterStalled` because it's the safest to toggle:

```bash
# Show current rule
docker exec dhg-prometheus cat /etc/prometheus/alerts/langgraph.yml | grep -A 3 "LangGraphExporterStalled"
```

Temporarily edit `observability/prometheus/alerts/langgraph.yml` and change:

```yaml
          (time() - langgraph_exporter_last_scrape_timestamp_seconds) > 90
```

to:

```yaml
          (time() - langgraph_exporter_last_scrape_timestamp_seconds) > 0
```

Reload:

```bash
curl -s -X POST http://localhost:9090/-/reload
sleep 150  # for:2m must elapse
curl -s 'http://localhost:9090/api/v1/alerts' | jq '.data.alerts[] | select(.labels.alertname=="LangGraphExporterStalled") | .state'
```

Expected: `"firing"`. Confirm Alertmanager received it:

```bash
curl -s http://localhost:9093/api/v2/alerts | jq '.[] | select(.labels.alertname=="LangGraphExporterStalled") | .status.state'
```

Expected: `"active"`.

Now revert the rule file (change `> 0` back to `> 90`) and reload:

```bash
curl -s -X POST http://localhost:9090/-/reload
sleep 150
curl -s 'http://localhost:9090/api/v1/alerts' | jq '.data.alerts[] | select(.labels.alertname=="LangGraphExporterStalled") | .state'
```

Expected: the alert is no longer in the response (or is in state `"inactive"`).

- [ ] **Step 3: No commit for the toggle-back test**

The file ends Step 2 in its original committed state.

- [ ] **Step 4: Final Phase 1 completion note**

Phase 1 is done when all five checks in Step 1 pass and the synthetic firing test in Step 2 completes cleanly. Any failure here is a blocker for Phase 2.

---

## Self-Review Results

**Spec coverage:**
- Cloudflare tunnel route → Task 2 ✓
- `tracing.py` import swap → Task 3 ✓
- Cloud deployment env vars + OTel packages → Task 4 ✓
- Prometheus `--web.enable-remote-write-receiver` → Task 5 ✓
- Local thread-state exporter → Tasks 7–10 ✓
- Prometheus scrape job → Task 11 ✓
- Six alert rules → Task 12 ✓
- Phase 1 success criteria verification → Tasks 6 and 13 ✓
- Deferred (Phase 2 plan): all dashboard UI, orchestrator stages constants, topology rendering, animated markers

**Placeholder scan:** None — every code step contains the actual code, every command step contains the actual command with expected output.

**Type consistency:** `build_registry` returns `(CollectorRegistry, Gauge, Gauge, Counter)` in both the stub (Task 7 Step 3) and the implementation (Task 8 Step 1). `scrape_once` returns `dict[str, int]` in both places. `THREAD_STATES` is a `tuple[str, ...]` declared once at module level.

**Production gates:** Tasks 1, 2, 4, 5, 10 explicitly require approval before state-changing steps. Tasks 6 and 13 are read-only verification and do not require approval.

---

## What Plan B (Phase 2) will cover

Plan B will be written *after* Phase 1 is validated, so it can reference real metric label names and values. Scope:
- `/dashboards/agents` fleet page with A1 grid, B1/B9/C1/C7/D1/D9 panels
- `/dashboards/agents/[graphId]` detail page with per-node table, topology ASCII, recent runs, error breakdown
- Sidebar navigation entry
- `orchestrator_stages.py` constants module + build-time JSON export
- Animated orchestrator markers with `unstable_cache` + Tempo `/api/search` integration
- Playwright E2E and visual regression tests
- CSS additions to `globals.css` if any (likely none — reuses existing `.mc-*` classes)
