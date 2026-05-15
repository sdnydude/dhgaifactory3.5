"""Pydantic schemas for the corrections API — Loop 4 self-training."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


VALID_CATEGORIES = {
    "docker-guessing",
    "fabrication",
    "missed-context",
    "wrong-assumption",
    "repeated-instruction",
    "workflow-violation",
    "other",
}


class CorrectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str = Field(..., max_length=100)
    category: str = Field(..., max_length=64)
    user_message: str
    context: Optional[str] = None
    claude_action: Optional[str] = None
    session_id: Optional[str] = Field(default=None, max_length=128)
    tags: Optional[list[str]] = None
    model_name: Optional[str] = Field(default=None, max_length=64)
    meta_data: Optional[dict[str, Any]] = None


class CorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_name: str
    category: str
    user_message: str
    upsert_key_hash: str
    context: Optional[str]
    claude_action: Optional[str]
    session_id: Optional[str]
    tags: Optional[list[str]]
    model_name: Optional[str]
    meta_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class CorrectionList(BaseModel):
    corrections: list[CorrectionResponse]
    total: int


class CorrectionSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000)
    project_name: Optional[str] = None
    category: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)
