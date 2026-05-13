"""Pydantic schemas for the doc-pages API."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocPageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str = Field(..., min_length=1, max_length=100)
    source_file: str = Field(..., min_length=1, max_length=500)
    chunk_index: int = Field(default=0, ge=0)
    title: Optional[str] = Field(default=None, max_length=500)
    content: str = Field(..., min_length=1)
    heading_path: Optional[str] = None
    tags: Optional[list[str]] = None
    meta_data: Optional[dict[str, Any]] = None


class DocPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_name: str
    source_file: str
    chunk_index: int
    title: Optional[str]
    content: str
    heading_path: Optional[str]
    embedding_model: Optional[str]
    tags: Optional[list[str]]
    meta_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class DocPageList(BaseModel):
    doc_pages: list[DocPageResponse]
    total: int


class DocPageSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    project_name: Optional[str] = None
    tags: Optional[list[str]] = None
    limit: int = Field(default=10, ge=1, le=100)


class DocPageBulkIngest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str
    pages: list[DocPageCreate] = Field(..., min_length=1)
    sweep_stale: bool = False
