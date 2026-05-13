"""Pydantic schemas for the ship-sessions API."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ShipSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str
    feature: str
    approach: Optional[str] = None
    status: str = "in_progress"
    complexity: Optional[str] = None
    tdd: Optional[bool] = None
    pr_url: Optional[str] = None
    branch: Optional[str] = None
    commits: list[str] = Field(default_factory=list)
    deferred: list[str] = Field(default_factory=list)
    surprises: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    review: Optional[dict[str, Any]] = None
    verification: Optional[dict[str, Any]] = None
    file_map: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    session_id: Optional[str] = None
    model_name: Optional[str] = None
    meta_data: Optional[dict[str, Any]] = None
    completed_at: Optional[datetime] = None


class ShipSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_name: str
    feature: str
    approach: Optional[str]
    status: str
    complexity: Optional[str]
    tdd: Optional[bool]
    pr_url: Optional[str]
    branch: Optional[str]
    commits: list[Any]
    deferred: list[Any]
    surprises: list[Any]
    decisions: list[Any]
    review: Optional[dict[str, Any]]
    verification: Optional[dict[str, Any]]
    file_map: Optional[dict[str, Any]]
    tags: Optional[list[str]]
    session_id: Optional[str]
    model_name: Optional[str]
    meta_data: Optional[dict[str, Any]]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ShipSessionList(BaseModel):
    ship_sessions: list[ShipSessionResponse]
    total: int


class ShipSessionSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    project_name: Optional[str] = None
    status: Optional[str] = None
    limit: int = 10
