"""Pydantic schemas for the dev_changelog admin/reporting API.

Field ownership is enforced at the schema layer:
  agent-owned:  commits, commit_count, detected_status, window_start, window_end,
                sessions, detected_at, last_agent_run_at, source
  human-owned:  declared_status, key_insight, notes, priority, locked

DevChangelogPatch accepts only human-owned fields. `extra='forbid'` rejects
any agent-owned field in the request body before the endpoint sees it.
"""
from datetime import date, datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


Category = Literal["feature", "infra", "fix", "refactor", "docs", "debt"]
DetectedStatus = Literal["shipped", "in_progress", "backlog", "abandoned"]
DeclaredStatus = Literal["shipped", "in_progress", "backlog", "abandoned"]
Source = Literal["manual", "agent", "mixed"]


class DevChangelogEntry(BaseModel):
    """Full row — response schema for GET list and GET detail."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    epic: str
    category: Category
    detected_status: DetectedStatus
    declared_status: Optional[DeclaredStatus] = None
    window_start: date
    window_end: Optional[date] = None
    commit_count: int
    commits: list[dict[str, Any]] = Field(default_factory=list)
    sessions: list[dict[str, Any]] = Field(default_factory=list)
    key_insight: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[int] = None
    locked: bool
    source: Source
    detected_at: datetime
    last_agent_run_at: Optional[datetime] = None
    last_human_edit_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DevChangelogPatch(BaseModel):
    """Human-owned fields only. Any agent-owned field in the body is rejected.

    All fields optional so callers can PATCH a single column at a time.
    """

    model_config = ConfigDict(extra="forbid")

    declared_status: Optional[DeclaredStatus] = None
    key_insight: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[int] = None
    locked: Optional[bool] = None


class DevChangelogList(BaseModel):
    """Paginated list response for GET /api/dev-changelog."""

    entries: list[DevChangelogEntry]
    total: int
