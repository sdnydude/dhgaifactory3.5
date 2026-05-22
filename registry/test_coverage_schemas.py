"""Pydantic schemas for the test-coverage API."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


VALID_CATEGORIES = {
    "admin",
    "api",
    "auth",
    "cme",
    "e2e",
    "integration",
    "langgraph",
    "marketplace",
    "other",
    "performance",
    "registry",
    "security",
    "unit",
}


class TestCoverageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., max_length=280)
    test_count_before: int
    test_count_after: int
    delta: int
    tests_added: Optional[list[str]] = None
    tests_removed: Optional[list[str]] = None
    tests_modified: Optional[list[str]] = None
    files_affected: Optional[list[str]] = None
    category: str = Field(..., max_length=64)
    trigger: Optional[str] = None
    project_name: str = Field(..., max_length=100)
    tags: Optional[list[str]] = None
    session_id: Optional[str] = Field(default=None, max_length=128)
    model_name: Optional[str] = Field(default=None, max_length=64)
    meta_data: Optional[dict[str, Any]] = None


class TestCoverageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    test_count_before: int
    test_count_after: int
    delta: int
    tests_added: Optional[list[str]]
    tests_removed: Optional[list[str]]
    tests_modified: Optional[list[str]]
    files_affected: Optional[list[str]]
    category: str
    trigger: Optional[str]
    project_name: str
    tags: Optional[list[str]]
    session_id: Optional[str]
    model_name: Optional[str]
    meta_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class TestCoverageList(BaseModel):
    test_coverage_events: list[TestCoverageResponse]
    total: int


class TestCoverageSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000)
    project_name: Optional[str] = None
    category: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)
