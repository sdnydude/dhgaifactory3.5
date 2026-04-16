"""
Incident Record Library — service layer.

Handles incident CRUD, cascade detection, deduplication,
system snapshot capture, and SLA/MTTR aggregation.
"""
from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import (
    Incident,
    IncidentAction,
    IncidentEvent,
    IncidentPostmortem,
    IncidentRunbook,
)

logger = logging.getLogger("incident_service")

# ── Constants ────────────────────────────────────────────────────────────

DEDUP_WINDOW_MINUTES = 15
CASCADE_WINDOW_MINUTES = 5


# ── System snapshot ──────────────────────────────────────────────────────

def capture_system_snapshot() -> dict[str, Any]:
    """Capture host, container, and database state at incident creation time."""

    snapshot: dict[str, Any] = {"captured_at": datetime.now(timezone.utc).isoformat()}

    # Host metrics via /proc (always available on Linux)
    try:
        with open("/proc/meminfo") as f:
            meminfo = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    meminfo[parts[0].rstrip(":")] = int(parts[1])
            total_kb = meminfo.get("MemTotal", 0)
            avail_kb = meminfo.get("MemAvailable", 0)
            swap_total = meminfo.get("SwapTotal", 0)
            swap_free = meminfo.get("SwapFree", 0)
            snapshot["host"] = {
                "memory_total_gb": round(total_kb / 1048576, 1),
                "memory_used_gb": round((total_kb - avail_kb) / 1048576, 1),
                "memory_percent": round((total_kb - avail_kb) / total_kb * 100, 1) if total_kb else 0,
                "swap_total_gb": round(swap_total / 1048576, 1),
                "swap_used_gb": round((swap_total - swap_free) / 1048576, 1),
                "swap_percent": round((swap_total - swap_free) / swap_total * 100, 1) if swap_total else 0,
            }
        with open("/proc/loadavg") as f:
            parts = f.read().split()
            snapshot["host"]["load_avg_1m"] = float(parts[0])
    except Exception as exc:
        logger.warning("Failed to read host metrics: %s", exc)
        snapshot["host"] = {"error": str(exc)}

    # Container list via docker CLI (available if socket is mounted)
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            containers = []
            for line in result.stdout.strip().split("\n"):
                if "\t" in line:
                    name, status = line.split("\t", 1)
                    containers.append({"name": name, "status": status})
            snapshot["containers"] = containers
    except Exception as exc:
        logger.debug("Docker CLI unavailable for snapshot: %s", exc)

    # Database connection stats (caller can enrich with DB session)
    snapshot["database"] = {}

    return snapshot


def enrich_snapshot_with_db(snapshot: dict[str, Any], db: Session) -> None:
    """Add database connection stats to an existing snapshot."""
    try:
        row = db.execute(text("""
            SELECT
                count(*) AS total,
                count(*) FILTER (WHERE state = 'active') AS active,
                count(*) FILTER (WHERE state = 'idle') AS idle,
                count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_tx
            FROM pg_stat_activity
            WHERE datname = current_database()
        """)).one()
        snapshot["database"] = {
            "total_connections": row.total,
            "active": row.active,
            "idle": row.idle,
            "idle_in_transaction": row.idle_in_tx,
        }
    except Exception as exc:
        logger.warning("Failed to capture DB stats for snapshot: %s", exc)


# ── Deduplication ────────────────────────────────────────────────────────

def find_duplicate(
    db: Session,
    trigger_rule: str | None,
    affected_services: list[str],
) -> Incident | None:
    """Check for an open incident with the same trigger+service within the dedup window."""
    if not trigger_rule:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=DEDUP_WINDOW_MINUTES)

    query = (
        db.query(Incident)
        .filter(
            Incident.trigger_rule == trigger_rule,
            Incident.status.in_(["active", "mitigated"]),
            Incident.created_at >= cutoff,
        )
    )
    for incident in query.all():
        if set(incident.affected_services or []) & set(affected_services):
            return incident

    return None


# ── Cascade detection ────────────────────────────────────────────────────

def find_parent_incident(
    db: Session,
    affected_services: list[str],
    exclude_id: UUID | None = None,
) -> Incident | None:
    """Find the earliest open incident created within the cascade window
    that shares at least one affected service."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=CASCADE_WINDOW_MINUTES)

    query = (
        db.query(Incident)
        .filter(
            Incident.status.in_(["active", "mitigated"]),
            Incident.created_at >= cutoff,
            Incident.parent_incident_id.is_(None),  # only root incidents
        )
        .order_by(Incident.created_at.asc())
    )
    if exclude_id:
        query = query.filter(Incident.id != exclude_id)

    for candidate in query.all():
        if set(candidate.affected_services or []) & set(affected_services):
            return candidate

    return None


# ── CRUD: Incidents ──────────────────────────────────────────────────────

def create_incident(
    db: Session,
    *,
    title: str,
    severity: str,
    category: str,
    trigger_rule: str | None = None,
    affected_services: list[str] | None = None,
    affected_project_ids: list[UUID] | None = None,
    tags: list[str] | None = None,
    pipeline_run_id: UUID | None = None,
    parent_incident_id: UUID | None = None,
    system_snapshot: dict | None = None,
    impact_summary: str | None = None,
    started_at: datetime | None = None,
    created_by: str | None = None,
    auto_snapshot: bool = True,
    auto_cascade: bool = True,
) -> Incident:
    """Create an incident with optional dedup, cascade detection, and snapshot."""

    services = affected_services or []

    # Deduplication check
    dup = find_duplicate(db, trigger_rule, services)
    if dup:
        # Add an event to the existing incident instead of creating a new one
        event = IncidentEvent(
            incident_id=dup.id,
            event_type="symptom",
            source="dedup",
            description=f"Duplicate trigger fired: {title}",
        )
        db.add(event)
        db.commit()
        db.refresh(dup)
        return dup

    # Capture snapshot
    if auto_snapshot and system_snapshot is None:
        system_snapshot = capture_system_snapshot()
        enrich_snapshot_with_db(system_snapshot, db)

    incident = Incident(
        title=title,
        severity=severity,
        category=category,
        trigger_rule=trigger_rule,
        affected_services=services,
        affected_project_ids=affected_project_ids,
        tags=tags or [],
        pipeline_run_id=pipeline_run_id,
        parent_incident_id=parent_incident_id,
        system_snapshot=system_snapshot,
        impact_summary=impact_summary,
        started_at=started_at,
        created_by=created_by,
    )
    db.add(incident)
    db.flush()  # get incident.id before cascade check

    # Cascade detection
    if auto_cascade and not parent_incident_id and services:
        parent = find_parent_incident(db, services, exclude_id=incident.id)
        if parent:
            incident.parent_incident_id = parent.id
            # Update parent impact summary
            child_note = f"Cascaded: {title} ({severity})"
            if parent.impact_summary:
                parent.impact_summary += f"\n{child_note}"
            else:
                parent.impact_summary = child_note

    # Initial event
    event = IncidentEvent(
        incident_id=incident.id,
        event_type="symptom",
        source=trigger_rule or "manual",
        description=f"Incident created: {title}",
    )
    db.add(event)
    db.commit()
    db.refresh(incident)
    return incident


def get_incident(db: Session, incident_id: UUID) -> Incident | None:
    return db.query(Incident).filter(Incident.id == incident_id).first()


def list_incidents(
    db: Session,
    *,
    status: str | None = None,
    severity: str | None = None,
    category: str | None = None,
    service: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Incident]:
    query = db.query(Incident).order_by(Incident.created_at.desc())
    if status:
        query = query.filter(Incident.status == status)
    if severity:
        query = query.filter(Incident.severity == severity)
    if category:
        query = query.filter(Incident.category == category)
    if service:
        query = query.filter(Incident.affected_services.any(service))
    return query.offset(offset).limit(limit).all()


def update_incident(db: Session, incident_id: UUID, **fields: Any) -> Incident | None:
    incident = get_incident(db, incident_id)
    if not incident:
        return None

    for key, value in fields.items():
        if value is not None and hasattr(incident, key):
            setattr(incident, key, value)

    # Auto-transition: if resolved_at is set and status is still active/mitigated, move to resolved
    if fields.get("resolved_at") and incident.status in ("active", "mitigated"):
        incident.status = "resolved"
    elif fields.get("mitigated_at") and incident.status == "active":
        incident.status = "mitigated"

    db.commit()
    db.refresh(incident)
    return incident


def link_child(db: Session, parent_id: UUID, child_id: UUID) -> bool:
    """Link child incident to parent for cascade tracking."""
    child = get_incident(db, child_id)
    if not child:
        return False
    child.parent_incident_id = parent_id
    db.commit()
    return True


# ── CRUD: Events ─────────────────────────────────────────────────────────

def add_event(
    db: Session,
    incident_id: UUID,
    *,
    event_type: str,
    description: str,
    source: str | None = None,
    evidence: dict | None = None,
    timestamp: datetime | None = None,
) -> IncidentEvent:
    event = IncidentEvent(
        incident_id=incident_id,
        event_type=event_type,
        description=description,
        source=source,
        evidence=evidence,
    )
    if timestamp:
        event.timestamp = timestamp
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(db: Session, incident_id: UUID) -> list[IncidentEvent]:
    return (
        db.query(IncidentEvent)
        .filter(IncidentEvent.incident_id == incident_id)
        .order_by(IncidentEvent.timestamp.desc())
        .all()
    )


# ── CRUD: Actions ────────────────────────────────────────────────────────

def add_action(
    db: Session,
    incident_id: UUID,
    *,
    action_type: str,
    description: str,
    command: str | None = None,
    result: str | None = None,
    performed_by: str | None = None,
    performed_at: datetime | None = None,
) -> IncidentAction:
    action = IncidentAction(
        incident_id=incident_id,
        action_type=action_type,
        description=description,
        command=command,
        result=result,
        performed_by=performed_by,
    )
    if performed_at:
        action.performed_at = performed_at
    db.add(action)
    db.commit()
    db.refresh(action)

    # Also log as timeline event
    add_event(
        db, incident_id,
        event_type="action",
        source=performed_by or "system",
        description=f"[{action_type}] {description}",
    )
    return action


# ── CRUD: Runbooks ───────────────────────────────────────────────────────

def get_runbook(db: Session, trigger_rule: str) -> IncidentRunbook | None:
    return db.query(IncidentRunbook).filter(IncidentRunbook.trigger_rule == trigger_rule).first()


def list_runbooks(db: Session, enabled_only: bool = True) -> list[IncidentRunbook]:
    query = db.query(IncidentRunbook)
    if enabled_only:
        query = query.filter(IncidentRunbook.enabled.is_(True))
    return query.order_by(IncidentRunbook.trigger_rule).all()


def upsert_runbook(db: Session, **fields: Any) -> IncidentRunbook:
    trigger = fields.get("trigger_rule")
    existing = get_runbook(db, trigger) if trigger else None
    if existing:
        for key, value in fields.items():
            if value is not None and hasattr(existing, key):
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    runbook = IncidentRunbook(**fields)
    db.add(runbook)
    db.commit()
    db.refresh(runbook)
    return runbook


# ── CRUD: Postmortems ───────────────────────────────────────────────────

def get_postmortem(db: Session, incident_id: UUID) -> IncidentPostmortem | None:
    return db.query(IncidentPostmortem).filter(IncidentPostmortem.incident_id == incident_id).first()


def create_or_update_postmortem(
    db: Session, incident_id: UUID, **fields: Any,
) -> IncidentPostmortem:
    existing = get_postmortem(db, incident_id)
    if existing:
        for key, value in fields.items():
            if value is not None and hasattr(existing, key):
                setattr(existing, key, value)
        existing.last_edited_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing

    pm = IncidentPostmortem(incident_id=incident_id, **fields)
    db.add(pm)
    db.commit()
    db.refresh(pm)

    # Transition incident to postmortem status
    incident = get_incident(db, incident_id)
    if incident and incident.status == "resolved":
        incident.status = "postmortem"
        db.commit()

    return pm


# ── Stats / MTTR ─────────────────────────────────────────────────────────

def compute_stats(
    db: Session,
    *,
    since: datetime | None = None,
    severity: str | None = None,
    category: str | None = None,
    service: str | None = None,
) -> dict[str, Any]:
    """Compute aggregate incident stats including SLA metrics."""

    query = db.query(Incident)
    if since:
        query = query.filter(Incident.created_at >= since)
    if severity:
        query = query.filter(Incident.severity == severity)
    if category:
        query = query.filter(Incident.category == category)
    if service:
        query = query.filter(Incident.affected_services.any(service))

    incidents = query.all()
    total = len(incidents)

    by_severity: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}
    ttd_values: list[float] = []
    ttm_values: list[float] = []
    ttr_values: list[float] = []

    for inc in incidents:
        by_severity[inc.severity] = by_severity.get(inc.severity, 0) + 1
        by_status[inc.status] = by_status.get(inc.status, 0) + 1
        by_category[inc.category] = by_category.get(inc.category, 0) + 1

        # TTD: started_at → detected_at
        if inc.started_at and inc.detected_at:
            ttd = (inc.detected_at - inc.started_at).total_seconds() / 60
            if ttd >= 0:
                ttd_values.append(ttd)

        # TTM: detected_at → mitigated_at
        if inc.detected_at and inc.mitigated_at:
            ttm = (inc.mitigated_at - inc.detected_at).total_seconds() / 60
            if ttm >= 0:
                ttm_values.append(ttm)

        # TTR: detected_at → resolved_at
        if inc.detected_at and inc.resolved_at:
            ttr = (inc.resolved_at - inc.detected_at).total_seconds() / 60
            if ttr >= 0:
                ttr_values.append(ttr)

    def avg_or_none(vals: list[float]) -> float | None:
        return round(sum(vals) / len(vals), 1) if vals else None

    # Top triggers
    trigger_counts: dict[str, int] = {}
    for inc in incidents:
        if inc.trigger_rule:
            trigger_counts[inc.trigger_rule] = trigger_counts.get(inc.trigger_rule, 0) + 1
    top_triggers = sorted(
        [{"trigger_rule": k, "count": v} for k, v in trigger_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    return {
        "total": total,
        "by_severity": by_severity,
        "by_status": by_status,
        "by_category": by_category,
        "avg_ttd_minutes": avg_or_none(ttd_values),
        "avg_ttm_minutes": avg_or_none(ttm_values),
        "avg_ttr_minutes": avg_or_none(ttr_values),
        "top_triggers": top_triggers,
    }
