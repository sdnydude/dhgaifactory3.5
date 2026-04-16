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
  - Rate limit: 1 remediation per incident per cooldown window
  - Dry-run mode via REMEDIATOR_DRY_RUN=true
"""

import logging
import os
import re
import subprocess
import time
import httpx

# ── Configuration ───────────────────────────────────────────────────────

REGISTRY_URL = os.getenv("REGISTRY_URL", "http://dhg-registry-api:8000")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "600"))
DRY_RUN = os.getenv("REMEDIATOR_DRY_RUN", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

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

# ── State ───────────────────────────────────────────────────────────────

processed: dict[str, float] = {}  # incident_id -> last_processed_timestamp


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
            log.warning(
                "Skipping %s — affected services %s not in allowlist %s",
                inc_id[:8], services, allowlist,
            )
            record_action(
                inc_id,
                "diagnostic",
                f"Remediation skipped: affected services {services} "
                f"not in container allowlist {allowlist}",
            )
            processed[inc_id] = time.time()
            return

    sorted_steps = sorted(steps, key=lambda s: s.get("order", 0))

    for step in sorted_steps:
        action_desc = step.get("action", "unnamed step")
        command = step.get("command")
        order = step.get("order", 0)

        if not command:
            # Step without a command (e.g., manual instruction)
            record_action(
                inc_id,
                "diagnostic",
                f"[Step {order}] {action_desc} — manual step, no command",
            )
            continue

        # Safety: block dangerous commands
        if is_blocked(command):
            log.warning("BLOCKED dangerous command: %s", command)
            record_action(
                inc_id,
                "diagnostic",
                f"[Step {order}] {action_desc} — BLOCKED (dangerous command)",
                command=command,
                result="Command blocked by safety filter",
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


def poll_cycle() -> None:
    incidents = api_get("/api/incidents?status=active&limit=50")
    if not incidents:
        return

    runbooks = fetch_runbooks()
    if not runbooks:
        log.debug("No actionable runbooks (all mode=none or disabled)")
        return

    for incident in incidents:
        inc_id = incident["id"]
        trigger = incident.get("trigger_rule")

        if not trigger or trigger not in runbooks:
            continue

        if in_cooldown(inc_id):
            log.debug("Skipping %s — in cooldown", inc_id[:8])
            continue

        process_incident(incident, runbooks[trigger])


def main() -> None:
    mode_label = "DRY RUN" if DRY_RUN else "LIVE"
    log.info(
        "DHG Remediator starting [%s] — polling %s every %ds, cooldown %ds",
        mode_label, REGISTRY_URL, POLL_INTERVAL, COOLDOWN_SECONDS,
    )

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
