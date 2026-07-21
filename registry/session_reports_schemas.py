"""Pydantic schemas for the session-reports API."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


VALID_CATEGORIES = {
    "bugfix",
    "docs",
    "feature",
    "infra",
    "investigation",
    "mixed",
    "other",
    "release",
}


class SessionReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., max_length=280)
    session_span: Optional[str] = None
    report_md: str
    prs: Optional[list[str]] = None
    learnings: Optional[list[str]] = None
    insights: Optional[list[str]] = None
    deferred: Optional[list[str]] = None
    category: Optional[str] = Field(default=None, max_length=64)
    project_name: str = Field(..., max_length=100)
    source_file: Optional[str] = Field(default=None, max_length=512)
    tags: Optional[list[str]] = None
    session_id: Optional[str] = Field(default=None, max_length=128)
    model_name: Optional[str] = Field(default=None, max_length=64)
    meta_data: Optional[dict[str, Any]] = None


class SessionReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    session_span: Optional[str]
    report_md: str
    prs: Optional[list[str]]
    learnings: Optional[list[str]]
    insights: Optional[list[str]]
    deferred: Optional[list[str]]
    category: Optional[str]
    project_name: str
    source_file: Optional[str]
    tags: Optional[list[str]]
    session_id: Optional[str]
    model_name: Optional[str]
    meta_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class SessionReportList(BaseModel):
    session_reports: list[SessionReportResponse]
    total: int


class SessionReportSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000)
    project_name: Optional[str] = None
    category: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)
