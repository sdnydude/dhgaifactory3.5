"""Pydantic schemas for the bug-fixes API."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


VALID_SEVERITIES = {"low", "medium", "high", "critical"}

VALID_CATEGORIES = {
    "auth",
    "api",
    "cme",
    "config",
    "database",
    "frontend",
    "infra",
    "langgraph",
    "marketplace",
    "observability",
    "other",
    "performance",
    "registry",
    "security",
    "shared",
    "testing",
}


class BugFixCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tldr: str = Field(..., max_length=280)
    symptom: str
    root_cause: str
    fix_applied: str
    files_affected: Optional[list[str]] = None
    severity: str = Field(..., max_length=20)
    category: str = Field(..., max_length=64)
    project_name: str = Field(..., max_length=100)
    source_file: Optional[str] = Field(default=None, max_length=512)
    tags: Optional[list[str]] = None
    session_id: Optional[str] = Field(default=None, max_length=128)
    model_name: Optional[str] = Field(default=None, max_length=64)
    meta_data: Optional[dict[str, Any]] = None


class BugFixResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tldr: str
    symptom: str
    root_cause: str
    fix_applied: str
    files_affected: Optional[list[str]]
    severity: str
    category: str
    project_name: str
    source_file: Optional[str]
    tags: Optional[list[str]]
    session_id: Optional[str]
    model_name: Optional[str]
    meta_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class BugFixList(BaseModel):
    bug_fixes: list[BugFixResponse]
    total: int


class BugFixSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000)
    project_name: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)
