"""Pydantic schemas for the burndown-lists API."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


VALID_LIST_TYPES = {"debug", "release", "feature", "audit"}
VALID_LIST_STATUSES = {"active", "completed", "archived"}
VALID_ITEM_STATUSES = {"not_started", "pass", "fail", "blocked", "skipped"}
VALID_SEVERITIES = {"none", "low", "medium", "high", "critical"}
VALID_RESOLUTIONS = {"open", "investigating", "fixed", "deferred", "wont_fix"}


# --- List schemas ---

class BurndownListCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., max_length=280)
    description: Optional[str] = None
    project_name: str = Field(..., max_length=100)
    list_type: str = Field(default="debug", max_length=40)
    created_by: Optional[str] = Field(default=None, max_length=100)
    meta_data: Optional[dict[str, Any]] = None


class BurndownListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: Optional[str]
    project_name: str
    list_type: str
    status: str
    created_by: Optional[str]
    meta_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class BurndownListWithItems(BurndownListResponse):
    items: list["BurndownItemResponse"] = []
    stats: Optional[dict[str, Any]] = None


class BurndownListSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    project_name: str
    list_type: str
    status: str
    created_by: Optional[str]
    created_at: datetime
    total_items: int = 0
    passed: int = 0
    failed: int = 0
    blocked: int = 0
    not_started: int = 0
    skipped: int = 0


class BurndownListUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, max_length=280)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=20)


# --- Item schemas ---

class BurndownItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seq: int
    feature: str = Field(..., max_length=280)
    url: Optional[str] = Field(default=None, max_length=500)
    what_to_check: Optional[str] = None
    status: str = Field(default="not_started", max_length=20)
    severity: str = Field(default="none", max_length=20)
    user_comment: Optional[str] = None
    assigned_to: Optional[str] = Field(default=None, max_length=100)
    meta_data: Optional[dict[str, Any]] = None


class BurndownItemBulkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[BurndownItemCreate]


class BurndownItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    list_id: UUID
    seq: int
    feature: str
    url: Optional[str]
    what_to_check: Optional[str]
    status: str
    severity: str
    user_comment: Optional[str]
    console_errors: Optional[str]
    assigned_to: Optional[str]
    fixed_in_commit: Optional[str]
    checked_at: Optional[datetime]
    agent_findings: Optional[str]
    agent_actions: Optional[str]
    resolution: str
    meta_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class BurndownItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[str] = Field(default=None, max_length=20)
    severity: Optional[str] = Field(default=None, max_length=20)
    user_comment: Optional[str] = None
    console_errors: Optional[str] = None
    assigned_to: Optional[str] = Field(default=None, max_length=100)
    fixed_in_commit: Optional[str] = Field(default=None, max_length=100)
    agent_findings: Optional[str] = None
    agent_actions: Optional[str] = None
    resolution: Optional[str] = Field(default=None, max_length=20)
    meta_data: Optional[dict[str, Any]] = None


# Resolve forward references
BurndownListWithItems.model_rebuild()
