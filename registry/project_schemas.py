"""Pydantic schemas for project list + project documents endpoints.

Serializer-drift rule: every field is enumerated explicitly; extra fields
rejected at parse time. Response constructors in projects_endpoints.py
must pass each field by name — never `**model.__dict__`.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    status: str
    kind: str | None
    document_count: int
    last_activity_at: datetime | None
    drive_folder_id: str | None


class ProjectListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    projects: list[ProjectListItem]
    total: int
    limit: int
    offset: int


class ProjectDocumentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    document_type: str
    title: str | None
    word_count: int | None
    version: int
    is_current: bool
    created_at: datetime
    drive_file_id: str | None


class ProjectDocumentsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    documents: list[ProjectDocumentItem]
