from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentPrintPayload(BaseModel):
    """Returned to the pdf-renderer via the frontend print route fetch."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    title: str
    graph_label: str
    review_round: int
    document_text: str


JobScope = Literal["document", "project"]
JobStatus = Literal["pending", "running", "succeeded", "failed"]


class DownloadJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    graph_id: str


class BundleJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    document_ids: list[UUID] | None = None  # None = all current docs
    include_manifest: bool = True
    include_intake: bool = False


class BundleJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    project_id: UUID | None
    scope: Literal["document", "project_bundle", "drive_sync"]
    status: Literal["pending", "running", "succeeded", "failed"]
    selected_document_ids: list[UUID] | None
    created_at: datetime
    completed_at: datetime | None
    artifact_bytes: int | None
    error: str | None


class DownloadJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    thread_id: str
    graph_id: str
    scope: JobScope
    status: JobStatus
    artifact_bytes: int | None = None
    artifact_sha256: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


class DownloadJobListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: list[DownloadJobResponse] = Field(default_factory=list)
