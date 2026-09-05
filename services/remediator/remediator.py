"""
DHG Remediation Sidecar
=======================
Polls for active incidents, matches them to runbooks, and executes
remediation steps — recording every action via the registry API.

Modes:
  auto     — execute all steps automatically
  approval — execute diagnostic steps only; destructive steps logged as pending
  none     — skip (no remediation)

Safety:
  - Hard-blocked commands: rm -rf, docker rmi, volume removal
  - container_allowlist enforcement
  - A runbook re-runs only when the incident's actionable state changes;
    the cooldown window is a second, independent guard
  - Only steps that were executed or proposed for approval record an action
  - Dry-run mode via REMEDIATOR_DRY_RUN=true

Observability:
  Prometheus metrics on METRICS_PORT (default 9105) at /metrics —
  remediator_cycles_total, remediator_incidents_seen,
  remediator_actions_total{kind}.
"""

import logging
import os
import re
import subprocess
import time
from datetime import datetime, timezone
import httpx
from prometheus_client import CollectorRegistry, Counter, Gauge, start_http_server

# ── Configuration ───────────────────────────────────────────────────────

REGISTRY_URL = os.getenv("REGISTRY_URL", "http://dhg-registry-api:8000")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "600"))
DRY_RUN = os.getenv("REMEDIATOR_DRY_RUN", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Incidents are fetched a page at a time until a short page comes back. The
# old single 50-row request saw 50 of the 1,112 active incidents.
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "200"))
MAX_INCIDENTS_PER_CYCLE = int(os.getenv("MAX_INCIDENTS_PER_CYCLE", "5000"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "9105"))
# Incidents older than this are left alone (see is_stale).
MAX_INCIDENT_AGE_HOURS = int(os.getenv("MAX_INCIDENT_AGE_HOURS", "24"))

BLOCKED_PATTERNS = [
    re.compile(r"\brm\s+-rf\b"),
    re.compile(r"\bdocker\s+rmi\b"),
    re.compile(r"\bdocker\s+volume\s+rm\b"),
    re.compile(r"\bdocker\s+system\s+prune\b"),
    re.compile(r"\bdocker\s+compose\s+down\b"),
    re.compile(r">\s*/dev/sd"),
    re.compile(r"\bdd\s+if="),
]

DESTRUCTIVE_MARKERS = ["restart", "stop", "kill", "terminate", "drop", "delete"]

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("remediator")

# ── Metrics ─────────────────────────────────────────────────────────────
# Own registry so the scrape carries only these series, not the default
# process/GC collectors.

METRICS_REGISTRY = CollectorRegistry()

cycles_total = Counter(
    "remediator_cycles_total",
    "Poll cycles completed",
    registry=METRICS_REGISTRY,
)
incidents_seen = Gauge(
    "remediator_incidents_seen",
    "Active incidents returned by the last full poll (all pages)",
    registry=METRICS_REGISTRY,
)
actions_total = Counter(
    "remediator_actions_total",
    "Incident actions recorded, by action type",
    ["kind"],
    registry=METRICS_REGISTRY,
)

# ── State ───────────────────────────────────────────────────────────────

processed: dict[str, float] = {}  # incident_id -> last_processed_timestamp

# incident_id -> the state key we last acted on. A runbook is re-run only when
# something the runbook actually reacts to has changed; polling an unchanged
# incident every 30s is what wrote 13,576 action rows for a single incident.
handled_state: dict[str, str] = {}


# ── Helpers ─────────────────────────────────────────────────────────────

def api_get(path: str) -> list | dict | None:
    try:
        r = httpx.get(f"{REGISTRY_URL}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        log.error("GET %s failed: %s", path, e)
        return None


def api_post(path: str, body: dict) -> dict | None:
    try:
        r = httpx.post(f"{REGISTRY_URL}{path}", json=body, timeout=10)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        log.error("POST %s failed: %s", path, e)
        return None


def is_blocked(command: str) -> bool:
    return any(pat.search(command) for pat in BLOCKED_PATTERNS)


def is_destructive(step: dict) -> bool:
    action_lower = step.get("action", "").lower()
    cmd = step.get("command", "")
    if not cmd:
        return False
    return any(m in action_lower for m in DESTRUCTIVE_MARKERS)


def resolve_placeholders(command: str, incident: dict) -> str:
    services = incident.get("affected_services", [])
    container = services[0] if services else "unknown"
    return command.replace("{container}", container)


def execute_command(command: str) -> tuple[int, str]:
    if DRY_RUN:
        log.info("[DRY RUN] Would execute: %s", command)
        return 0, "[dry run] command skipped"
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = (result.stdout + result.stderr).strip()
        if len(output) > 2000:
            output = output[:2000] + "\n... (truncated)"
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return -1, "Command timed out after 60s"
    except Exception as e:
        return -1, f"Execution error: {e}"


def record_action(
    incident_id: str,
    action_type: str,
    description: str,
    command: str | None = None,
    result: str | None = None,
) -> None:
    body: dict = {
        "action_type": action_type,
        "description": description,
        "performed_by": "dhg-remediator",
    }
    if command:
        body["command"] = command
    if result:
        body["result"] = result
    api_post(f"/api/incidents/{incident_id}/actions", body)
    actions_total.labels(kind=action_type).inc()


def in_cooldown(incident_id: str) -> bool:
    last = processed.get(incident_id, 0)
    return (time.time() - last) < COOLDOWN_SECONDS


# ── Core Loop ───────────────────────────────────────────────────────────

def fetch_runbooks() -> dict[str, dict]:
    data = api_get("/api/incidents/runbooks")
    if not data:
        return {}
    return {
        rb["trigger_rule"]: rb
        for rb in data
        if rb.get("enabled") and rb.get("remediation_mode") != "none"
    }


def process_incident(incident: dict, runbook: dict) -> None:
    inc_id = incident["id"]
    trigger = incident.get("trigger_rule", "?")
    mode = runbook["remediation_mode"]
    steps = runbook.get("steps", [])
    allowlist = runbook.get("container_allowlist", [])

    log.info(
        "Processing incident %s (trigger=%s, mode=%s, steps=%d)",
        inc_id[:8], trigger, mode, len(steps),
    )

    # Allowlist check
    services = incident.get("affected_services", [])
    if allowlist:
        if not any(svc in allowlist for svc in services):
            # Log only. Nothing was taken and nothing was proposed, so there
            # is no action to record — writing one here just grew the table.
            log.warning(
                "Skipping %s — affected services %s not in allowlist %s",
                inc_id[:8], services, allowlist,
            )
            return

    sorted_steps = sorted(steps, key=lambda s: s.get("order", 0))

    for step in sorted_steps:
        action_desc = step.get("action", "unnamed step")
        command = step.get("command")
        order = step.get("order", 0)

        if not command:
            # Manual instruction for a human — the remediator neither took
            # nor proposed anything, so it records nothing.
            log.info("[Step %d] %s — manual step, no command", order, action_desc)
            continue

        # Safety: block dangerous commands
        if is_blocked(command):
            # A refusal is neither an action taken nor one proposed. It is a
            # runbook authoring bug and belongs in the log, where it is
            # visible without adding a row per poll.
            log.warning(
                "BLOCKED dangerous command in runbook step %d (%s): %s",
                order, action_desc, command,
            )
            continue

        resolved_cmd = resolve_placeholders(command, incident)

        # approval mode: skip destructive steps
        if mode == "approval" and is_destructive(step):
            log.info(
                "Approval required for step %d: %s", order, action_desc,
            )
            record_action(
                inc_id,
                "diagnostic",
                f"[Step {order}] {action_desc} — PENDING APPROVAL",
                command=resolved_cmd,
                result="Destructive step requires human approval",
            )
            continue

        # Execute the command
        log.info("Executing step %d: %s", order, action_desc)
        returncode, output = execute_command(resolved_cmd)

        action_type = "auto_remediation" if is_destructive(step) else "diagnostic"
        status = "success" if returncode == 0 else f"failed (exit {returncode})"

        record_action(
            inc_id,
            action_type,
            f"[Step {order}] {action_desc} — {status}",
            command=resolved_cmd,
            result=output or "(no output)",
        )

        if returncode != 0:
            log.warning(
                "Step %d failed (exit %d), stopping runbook for %s",
                order, returncode, inc_id[:8],
            )
            break

    processed[inc_id] = time.time()
    log.info("Finished processing incident %s", inc_id[:8])


def fetch_active_incidents() -> list[dict]:
    """Walk every page of active incidents, not just the first."""
    collected: list[dict] = []
    offset = 0

    while offset < MAX_INCIDENTS_PER_CYCLE:
        page = api_get(
            f"/api/incidents?status=active&limit={PAGE_SIZE}&offset={offset}"
        )
        if not page:
            break
        collected.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return collected


def is_stale(incident: dict) -> bool:
    """True when the incident is too old to be worth remediating now.

    handled_state is in-memory, so after a restart every open incident looks
    unhandled. Without this guard a restart re-runs runbooks across the whole
    open backlog — the very stampede that filled incident_actions. A runbook
    that did not fix a condition when it was fresh will not fix it months
    later; a still-live condition re-alerts and gets a fresh incident.
    """
    stamp = incident.get("detected_at") or incident.get("created_at")
    if not stamp:
        return False
    try:
        detected = datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return False
    if detected.tzinfo is None:
        detected = detected.replace(tzinfo=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - detected).total_seconds() / 3600
    return age_hours > MAX_INCIDENT_AGE_HOURS


def incident_state_key(incident: dict) -> str:
    """The parts of an incident a runbook actually reacts to.

    Deliberately excludes updated_at and occurrence_count: an alert re-firing
    against an already-open incident is not a new state to remediate.
    """
    return "|".join([
        incident.get("status") or "",
        incident.get("severity") or "",
        incident.get("trigger_rule") or "",
        ",".join(sorted(incident.get("affected_services") or [])),
    ])


def poll_cycle() -> None:
    incidents = fetch_active_incidents()
    incidents_seen.set(len(incidents))
    runbooks = fetch_runbooks() if incidents else {}

    if not incidents or not runbooks:
        if incidents:
            log.debug("No actionable runbooks (all mode=none or disabled)")
        cycles_total.inc()
        return

    for incident in incidents:
        inc_id = incident["id"]
        trigger = incident.get("trigger_rule")

        if not trigger or trigger not in runbooks:
            continue

        if is_stale(incident):
            log.debug("Skipping %s — older than %dh", inc_id[:8], MAX_INCIDENT_AGE_HOURS)
            continue

        state_key = incident_state_key(incident)
        if handled_state.get(inc_id) == state_key:
            continue

        if in_cooldown(inc_id):
            log.debug("Skipping %s — in cooldown", inc_id[:8])
            continue

        process_incident(incident, runbooks[trigger])
        handled_state[inc_id] = state_key
        processed[inc_id] = time.time()

    cycles_total.inc()


def main() -> None:
    mode_label = "DRY RUN" if DRY_RUN else "LIVE"
    log.info(
        "DHG Remediator starting [%s] — polling %s every %ds, cooldown %ds",
        mode_label, REGISTRY_URL, POLL_INTERVAL, COOLDOWN_SECONDS,
    )

    start_http_server(METRICS_PORT, registry=METRICS_REGISTRY)
    log.info("Metrics served on :%d/metrics", METRICS_PORT)

    # Wait for registry API to be available
    for attempt in range(30):
        try:
            r = httpx.get(f"{REGISTRY_URL}/healthz", timeout=5)
            if r.status_code == 200:
                log.info("Registry API is healthy")
                break
        except httpx.HTTPError:
            pass
        log.info("Waiting for registry API (attempt %d/30)...", attempt + 1)
        time.sleep(5)
    else:
        log.error("Registry API not available after 150s, starting anyway")

    while True:
        try:
            poll_cycle()
        except Exception:
            log.exception("Unexpected error in poll cycle")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
