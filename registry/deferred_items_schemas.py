"""Pydantic schemas for the deferred-items API."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


VALID_PRIORITIES = {"low", "medium", "high", "critical"}

VALID_CATEGORIES = {
    "auth",
    "api",
    "cme",
    "config",
    "database",
    "docs",
    "frontend",
    "infra",
    "langgraph",
    "marketplace",
    "observability",
    "other",
    "performance",
    "registry",
    "security",
    "testing",
}

VALID_STATUSES = {"open", "in_progress", "resolved", "wont_fix"}


class DeferredItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., max_length=280)
    description: str
    reason: str
    source_context: Optional[str] = None
    priority: str = Field(default="medium", max_length=20)
    category: str = Field(..., max_length=64)
    status: str = Field(default="open", max_length=20)
    affected_files: Optional[list[str]] = None
    project_name: str = Field(..., max_length=100)
    tags: Optional[list[str]] = None
    session_id: Optional[str] = Field(default=None, max_length=128)
    model_name: Optional[str] = Field(default=None, max_length=64)
    meta_data: Optional[dict[str, Any]] = None


class DeferredItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    reason: str
    source_context: Optional[str]
    priority: str
    category: str
    status: str
    affected_files: Optional[list[str]]
    project_name: str
    tags: Optional[list[str]]
    session_id: Optional[str]
    model_name: Optional[str]
    meta_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class DeferredItemList(BaseModel):
    deferred_items: list[DeferredItemResponse]
    total: int


class DeferredItemSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000)
    project_name: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)
