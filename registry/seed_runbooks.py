"""
Seed incident_runbooks from observability/runbooks/*.yml.

The YAML files are the source of truth; the table is a cache of them. Each
file becomes one row keyed by trigger_rule, with its `diagnostics` as the
steps (order/action/command) — human_steps are never stored, so nothing the
remediator reads can ask it to do more than read-only diagnostics. Rows whose
trigger_rule no longer has a YAML file are disabled, not deleted, so old
incidents keep their trigger reference.

Usage:
    python seed_runbooks.py           # standalone (RUNBOOKS_DIR optional)
    POST /api/incidents/runbooks/seed  # via API (see incident_endpoints.py)

Inside the registry container the directory is bind-mounted at /app/runbooks
(docker-compose.yml); on a checkout it is found relative to this file.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from models import IncidentRunbook

logger = logging.getLogger("seed_runbooks")

REQUIRED_KEYS = ("alert", "trigger_rule", "severity", "mode", "title", "diagnostics")
VALID_SEVERITIES = ("critical", "high", "warning")
VALID_MODES = ("notify",)


def runbooks_dir() -> Path:
    override = os.getenv("RUNBOOKS_DIR")
    if override:
        return Path(override)
    in_container = Path("/app/runbooks")
    if in_container.is_dir():
        return in_container
    return Path(__file__).resolve().parent.parent / "observability" / "runbooks"


def runbook_to_row(doc: dict, source: str = "<yaml>") -> dict:
    """Validate one YAML document and shape it as IncidentRunbook columns."""
    missing = [k for k in REQUIRED_KEYS if k not in doc]
    if missing:
        raise ValueError(f"{source}: missing keys {missing}")
    if doc["severity"] not in VALID_SEVERITIES:
        raise ValueError(f"{source}: severity must be one of {VALID_SEVERITIES}")
    if doc["mode"] not in VALID_MODES:
        raise ValueError(f"{source}: mode must be one of {VALID_MODES}")

    steps = []
    for step in doc["diagnostics"]:
        for key in ("order", "description", "command"):
            if key not in step:
                raise ValueError(f"{source}: diagnostic missing '{key}'")
        steps.append({
            "order": int(step["order"]),
            "action": step["description"],
            "command": step["command"],
        })
    steps.sort(key=lambda s: s["order"])

    return {
        "trigger_rule": doc["trigger_rule"],
        "title": f"{doc['alert']}: {doc['title']}",
        "description": doc.get("description") or "",
        "severity": doc["severity"],
        "remediation_mode": doc["mode"],
        "container_allowlist": [],
        "steps": steps,
        "enabled": True,
    }


def load_runbooks(directory: Path | None = None) -> list[dict]:
    """Every observability/runbooks/*.yml as IncidentRunbook column dicts."""
    directory = directory or runbooks_dir()
    files = sorted(directory.glob("*.yml"))
    if not files:
        raise FileNotFoundError(f"no runbook YAML under {directory}")
    rows = []
    seen: dict[str, str] = {}
    for path in files:
        with open(path) as fh:
            doc = yaml.safe_load(fh)
        if doc.get("alert") != path.stem:
            raise ValueError(f"{path.name}: alert '{doc.get('alert')}' must match the file name")
        row = runbook_to_row(doc, path.name)
        if row["trigger_rule"] in seen:
            raise ValueError(
                f"{path.name}: trigger_rule {row['trigger_rule']} already used by {seen[row['trigger_rule']]}"
            )
        seen[row["trigger_rule"]] = path.name
        rows.append(row)
    return rows


def seed_all(db: Session) -> dict[str, int]:
    """Upsert every YAML runbook; disable rows with no YAML.

    Returns {"created": N, "updated": M, "disabled": K}.
    """
    rows = load_runbooks()
    created = updated = disabled = 0

    for row in rows:
        existing = db.query(IncidentRunbook).filter(
            IncidentRunbook.trigger_rule == row["trigger_rule"]
        ).first()
        if existing:
            for key, value in row.items():
                setattr(existing, key, value)
            updated += 1
        else:
            db.add(IncidentRunbook(**row))
            created += 1

    live = {row["trigger_rule"] for row in rows}
    for stale in db.query(IncidentRunbook).filter(IncidentRunbook.enabled.is_(True)).all():
        if stale.trigger_rule not in live:
            stale.enabled = False
            disabled += 1

    db.commit()
    logger.info(
        "Runbook seed complete: %d created, %d updated, %d disabled (no YAML)",
        created, updated, disabled,
    )
    return {"created": created, "updated": updated, "disabled": disabled}


if __name__ == "__main__":
    import sys
    from database import SessionLocal

    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        result = seed_all(db)
        print(f"Seeded runbooks: {result}")
    finally:
        db.close()
    sys.exit(0)
