"""
Incident Record Library — API endpoints.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from incident_schemas import (
    ActionCreate,
    ActionResponse,
    EventCreate,
    EventResponse,
    IncidentCreate,
    IncidentDetailResponse,
    IncidentListResponse,
    IncidentResponse,
    IncidentStats,
    IncidentUpdate,
    PostmortemCreate,
    PostmortemResponse,
    PostmortemUpdate,
    RunbookCreate,
    RunbookResponse,
    RunbookUpdate,
)
import incident_service as svc

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


# ══════════════════════════════════════════════════════════════════════════
# STATIC PATHS — must be registered BEFORE /{incident_id} to avoid
# FastAPI matching "runbooks" or "stats" as a UUID path parameter.
# ══════════════════════════════════════════════════════════════════════════


# ── Incidents: collection ────────────────────────────────────────────────

@router.post("", response_model=IncidentResponse, status_code=201)
def create_incident(body: IncidentCreate, db: Session = Depends(get_db)):
    incident = svc.create_incident(
        db,
        title=body.title,
        severity=body.severity,
        category=body.category,
        trigger_rule=body.trigger_rule,
        affected_services=body.affected_services,
        affected_project_ids=body.affected_project_ids,
        tags=body.tags,
        pipeline_run_id=body.pipeline_run_id,
        parent_incident_id=body.parent_incident_id,
        system_snapshot=body.system_snapshot,
        impact_summary=body.impact_summary,
        started_at=body.started_at,
        created_by=body.created_by,
    )
    return incident


@router.get("", response_model=list[IncidentListResponse])
def list_incidents(
    status: str | None = Query(None),
    severity: str | None = Query(None),
    category: str | None = Query(None),
    service: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return svc.list_incidents(
        db, status=status, severity=severity,
        category=category, service=service,
        limit=limit, offset=offset,
    )


# ── Stats ────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=IncidentStats)
def get_stats(
    days: int = Query(30, ge=1, le=365),
    severity: str | None = Query(None),
    category: str | None = Query(None),
    service: str | None = Query(None),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return svc.compute_stats(
        db, since=since, severity=severity,
        category=category, service=service,
    )


# ── Runbooks ─────────────────────────────────────────────────────────────

@router.get("/runbooks", response_model=list[RunbookResponse])
def list_runbooks(
    enabled_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    return svc.list_runbooks(db, enabled_only=enabled_only)


@router.post("/runbooks", response_model=RunbookResponse, status_code=201)
def create_runbook(body: RunbookCreate, db: Session = Depends(get_db)):
    return svc.upsert_runbook(
        db,
        trigger_rule=body.trigger_rule,
        title=body.title,
        description=body.description,
        severity=body.severity,
        remediation_mode=body.remediation_mode,
        steps=body.steps,
        container_allowlist=body.container_allowlist,
        enabled=body.enabled,
    )


@router.post("/runbooks/seed")
def seed_runbooks(db: Session = Depends(get_db)):
    from seed_runbooks import seed_all
    return seed_all(db)


@router.patch("/runbooks/{trigger_rule}", response_model=RunbookResponse)
def update_runbook(trigger_rule: str, body: RunbookUpdate, db: Session = Depends(get_db)):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    updates["trigger_rule"] = trigger_rule
    runbook = svc.upsert_runbook(db, **updates)
    return runbook


# ══════════════════════════════════════════════════════════════════════════
# PARAMETERIZED PATHS — /{incident_id} and its sub-resources
# ══════════════════════════════════════════════════════════════════════════


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(incident_id: UUID, db: Session = Depends(get_db)):
    incident = svc.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return incident


@router.patch("/{incident_id}", response_model=IncidentResponse)
def update_incident(incident_id: UUID, body: IncidentUpdate, db: Session = Depends(get_db)):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    incident = svc.update_incident(db, incident_id, **updates)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return incident


@router.post("/{parent_id}/link/{child_id}", status_code=204)
def link_child(parent_id: UUID, child_id: UUID, db: Session = Depends(get_db)):
    if not svc.link_child(db, parent_id, child_id):
        raise HTTPException(404, "Child incident not found")


# ── Events ───────────────────────────────────────────────────────────────

@router.post("/{incident_id}/events", response_model=EventResponse, status_code=201)
def add_event(incident_id: UUID, body: EventCreate, db: Session = Depends(get_db)):
    if not svc.get_incident(db, incident_id):
        raise HTTPException(404, "Incident not found")
    return svc.add_event(
        db, incident_id,
        event_type=body.event_type,
        description=body.description,
        source=body.source,
        evidence=body.evidence,
        timestamp=body.timestamp,
    )


@router.get("/{incident_id}/events", response_model=list[EventResponse])
def list_events(incident_id: UUID, db: Session = Depends(get_db)):
    if not svc.get_incident(db, incident_id):
        raise HTTPException(404, "Incident not found")
    return svc.list_events(db, incident_id)


# ── Actions ──────────────────────────────────────────────────────────────

@router.post("/{incident_id}/actions", response_model=ActionResponse, status_code=201)
def add_action(incident_id: UUID, body: ActionCreate, db: Session = Depends(get_db)):
    if not svc.get_incident(db, incident_id):
        raise HTTPException(404, "Incident not found")
    return svc.add_action(
        db, incident_id,
        action_type=body.action_type,
        description=body.description,
        command=body.command,
        result=body.result,
        performed_by=body.performed_by,
        performed_at=body.performed_at,
    )


# ── Postmortems ──────────────────────────────────────────────────────────

@router.get("/{incident_id}/postmortem", response_model=PostmortemResponse)
def get_postmortem(incident_id: UUID, db: Session = Depends(get_db)):
    pm = svc.get_postmortem(db, incident_id)
    if not pm:
        raise HTTPException(404, "Postmortem not found for this incident")
    return pm


@router.post("/{incident_id}/postmortem", response_model=PostmortemResponse, status_code=201)
def create_postmortem(incident_id: UUID, body: PostmortemCreate, db: Session = Depends(get_db)):
    if not svc.get_incident(db, incident_id):
        raise HTTPException(404, "Incident not found")
    return svc.create_or_update_postmortem(
        db, incident_id, **body.model_dump(exclude_unset=True),
    )


@router.patch("/{incident_id}/postmortem", response_model=PostmortemResponse)
def update_postmortem(incident_id: UUID, body: PostmortemUpdate, db: Session = Depends(get_db)):
    pm = svc.get_postmortem(db, incident_id)
    if not pm:
        raise HTTPException(404, "Postmortem not found for this incident")
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    return svc.create_or_update_postmortem(db, incident_id, **updates)
