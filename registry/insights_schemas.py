"""Pydantic schemas for the insights API."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InsightCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tldr: str
    insight_statement: str
    project_name: str
    category: str
    subcategory: Optional[str] = None
    source_file: Optional[str] = None
    source_language: Optional[str] = None
    source_framework: Optional[str] = None
    tags: Optional[list[str]] = None
    session_id: Optional[str] = None
    model_name: Optional[str] = None
    meta_data: Optional[dict[str, Any]] = None


class InsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tldr: str
    insight_statement: str
    project_name: str
    category: str
    subcategory: Optional[str]
    source_file: Optional[str]
    source_language: Optional[str]
    source_framework: Optional[str]
    tags: Optional[list[str]]
    session_id: Optional[str]
    model_name: Optional[str]
    meta_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class InsightList(BaseModel):
    insights: list[InsightResponse]
    total: int


class InsightSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    project_name: Optional[str] = None
    category: Optional[str] = None
    limit: int = 10
