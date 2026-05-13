"""Pydantic schemas for the unified KB search API."""
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


VALID_SOURCES = {"docs", "insights", "decisions", "ship_sessions"}


class KBSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000)
    project_name: Optional[str] = Field(default=None, max_length=100)
    sources: Optional[list[str]] = Field(
        default=None,
        description="Filter to specific sources. Valid values: docs, insights, decisions, ship_sessions",
    )
    limit: int = Field(default=10, ge=1, le=100)


class KBSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    source_id: UUID
    title: str
    content: str
    score: float
    project_name: str
    metadata: dict[str, Any]


class KBSearchResponse(BaseModel):
    query: str
    results: list[KBSearchResult]
    total: int
    searched_sources: list[str]
