"""Pydantic schemas for the beta-reports API."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_STATUSES = {"open", "triaged", "in_progress", "resolved", "wont_fix"}


class BetaReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str = Field(..., min_length=1, max_length=100)
    reporter_email: str = Field(..., min_length=3, max_length=255)
    reporter_user_id: Optional[str] = Field(default=None, max_length=128)
    page: str = Field(..., min_length=1, max_length=500)
    area: Optional[str] = Field(default=None, max_length=100)
    severity: str = Field(..., max_length=20)
    description: str = Field(..., min_length=1)
    screenshot_url: Optional[str] = Field(default=None, max_length=1000)


class BetaReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_name: str
    reporter_email: str
    reporter_user_id: Optional[str]
    page: str
    area: Optional[str]
    severity: str
    description: str
    screenshot_url: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class BetaReportList(BaseModel):
    beta_reports: list[BetaReportResponse]
    total: int


class BetaReportUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[str] = Field(default=None, max_length=20)
    area: Optional[str] = Field(default=None, max_length=100)
    severity: Optional[str] = Field(default=None, max_length=20)
