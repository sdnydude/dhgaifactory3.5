"""Pydantic schemas for the decision-logs API."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DecisionLogCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    choice: str
    alternatives_rejected: Optional[str] = None
    rationale: str
    domain: str
    supersedes: Optional[str] = None
    project_name: str
    source_file: Optional[str] = None
    tags: Optional[list[str]] = None
    session_id: Optional[str] = None
    model_name: Optional[str] = None
    meta_data: Optional[dict[str, Any]] = None


class DecisionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    choice: str
    alternatives_rejected: Optional[str]
    rationale: str
    domain: str
    supersedes: Optional[str]
    project_name: str
    source_file: Optional[str]
    tags: Optional[list[str]]
    session_id: Optional[str]
    model_name: Optional[str]
    meta_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class DecisionLogList(BaseModel):
    decision_logs: list[DecisionLogResponse]
    total: int


class DecisionLogSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    project_name: Optional[str] = None
    domain: Optional[str] = None
    limit: int = 10
