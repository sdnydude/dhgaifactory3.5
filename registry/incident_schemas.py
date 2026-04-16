from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Shared literals ──────────────────────────────────────────────────────

IncidentSeverity = Literal["critical", "high", "medium", "low"]
IncidentStatus = Literal["active", "mitigated", "resolved", "postmortem"]
IncidentCategory = Literal["infrastructure", "pipeline", "data", "integration", "security", "performance"]
RootCauseCategory = Literal[
    "memory_leak", "config_error", "type_error", "dependency_failure",
    "resource_exhaustion", "network", "crash_loop", "connection_leak",
    "disk_pressure", "other",
]
EventType = Literal["symptom", "diagnosis", "escalation", "action", "resolution", "notification"]
ActionType = Literal["diagnostic", "mitigation", "fix", "prevention", "auto_remediation"]
RemediationMode = Literal["auto", "approval", "none"]


# ── Incident CRUD ────────────────────────────────────────────────────────

class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=5, max_length=500)
    severity: IncidentSeverity
    category: IncidentCategory
    trigger_rule: str | None = None
    affected_services: list[str] = Field(default_factory=list)
    affected_project_ids: list[UUID] | None = None
    tags: list[str] = Field(default_factory=list)
    pipeline_run_id: UUID | None = None
    parent_incident_id: UUID | None = None
    system_snapshot: dict | None = None
    impact_summary: str | None = None
    started_at: datetime | None = None
    created_by: str | None = None


class IncidentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    severity: IncidentSeverity | None = None
    status: IncidentStatus | None = None
    category: IncidentCategory | None = None
    root_cause: str | None = None
    root_cause_category: RootCauseCategory | None = None
    impact_summary: str | None = None
    prevention: str | None = None
    affected_services: list[str] | None = None
    tags: list[str] | None = None
    mitigated_at: datetime | None = None
    resolved_at: datetime | None = None


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    severity: str
    status: str
    category: str
    root_cause: str | None
    root_cause_category: str | None
    impact_summary: str | None
    prevention: str | None
    trigger_rule: str | None
    affected_services: list[str]
    affected_project_ids: list[UUID] | None
    tags: list[str]
    parent_incident_id: UUID | None
    pipeline_run_id: UUID | None
    system_snapshot: dict | None
    created_by: str | None
    started_at: datetime | None
    detected_at: datetime
    mitigated_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IncidentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    severity: str
    status: str
    category: str
    trigger_rule: str | None
    affected_services: list[str]
    parent_incident_id: UUID | None
    detected_at: datetime
    mitigated_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime


# ── Events ───────────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: EventType
    description: str = Field(..., min_length=5)
    source: str | None = None
    evidence: dict | None = None
    timestamp: datetime | None = None  # defaults to now() server-side


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    timestamp: datetime
    event_type: str
    source: str | None
    description: str
    evidence: dict | None
    created_at: datetime


# ── Actions ──────────────────────────────────────────────────────────────

class ActionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: ActionType
    description: str = Field(..., min_length=5)
    command: str | None = None
    result: str | None = None
    performed_by: str | None = None
    performed_at: datetime | None = None


class ActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    action_type: str
    description: str
    command: str | None
    result: str | None
    performed_at: datetime
    performed_by: str | None
    created_at: datetime


# ── Runbooks ─────────────────────────────────────────────────────────────

class RunbookCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_rule: str = Field(..., max_length=50)
    title: str
    description: str | None = None
    severity: IncidentSeverity
    remediation_mode: RemediationMode = "none"
    steps: list[dict] = Field(default_factory=list)
    container_allowlist: list[str] = Field(default_factory=list)
    enabled: bool = True


class RunbookUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    severity: IncidentSeverity | None = None
    remediation_mode: RemediationMode | None = None
    steps: list[dict] | None = None
    container_allowlist: list[str] | None = None
    enabled: bool | None = None


class RunbookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trigger_rule: str
    title: str
    description: str | None
    severity: str
    remediation_mode: str
    steps: list[dict]
    container_allowlist: list[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime


# ── Post-mortems ─────────────────────────────────────────────────────────

class PostmortemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str | None = None
    timeline_markdown: str | None = None
    root_cause_analysis: str | None = None
    impact_analysis: str | None = None
    resolution_details: str | None = None
    prevention_measures: str | None = None
    lessons_learned: str | None = None
    sla_metrics: dict | None = None
    edited_by: str | None = None


class PostmortemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str | None = None
    timeline_markdown: str | None = None
    root_cause_analysis: str | None = None
    impact_analysis: str | None = None
    resolution_details: str | None = None
    prevention_measures: str | None = None
    lessons_learned: str | None = None
    sla_metrics: dict | None = None
    edited_by: str | None = None


class PostmortemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    summary: str | None
    timeline_markdown: str | None
    root_cause_analysis: str | None
    impact_analysis: str | None
    resolution_details: str | None
    prevention_measures: str | None
    lessons_learned: str | None
    sla_metrics: dict | None
    generated_at: datetime
    last_edited_at: datetime | None
    edited_by: str | None
    created_at: datetime


# ── Stats / aggregates ───────────────────────────────────────────────────

class IncidentStats(BaseModel):
    total: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    by_category: dict[str, int]
    avg_ttd_minutes: float | None  # time to detect
    avg_ttm_minutes: float | None  # time to mitigate
    avg_ttr_minutes: float | None  # time to resolve
    top_triggers: list[dict]  # [{trigger_rule, count}]


class IncidentDetailResponse(IncidentResponse):
    """Full incident with nested events, actions, and postmortem."""
    events: list[EventResponse] | None = Field(default=None)
    actions: list[ActionResponse] | None = Field(default=None)
    postmortem: PostmortemResponse | None = None
    children: list[IncidentListResponse] | None = Field(default=None)
