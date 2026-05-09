"""Pydantic schemas for the memory_metrics API."""
from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


SyncMode = Literal["full", "light"]


class MemoryMetricsCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    sync_mode: SyncMode
    sync_run_at: datetime
    hot_areas: Optional[list[dict[str, Any]]] = None
    workflow_distribution: Optional[dict[str, Any]] = None
    workflow_trend: Optional[dict[str, Any]] = None
    memory_health: dict[str, Any]
    decision_stats: Optional[dict[str, Any]] = None
    contradictions: Optional[list[dict[str, Any]]] = None
    unfinished_branches: Optional[list[dict[str, Any]]] = None
    journal_backfills: Optional[int] = None
    patterns_detected: Optional[int] = None


class MemoryMetricsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project: str
    sync_mode: str
    sync_run_at: datetime
    hot_areas: Optional[list[dict[str, Any]]]
    workflow_distribution: Optional[dict[str, Any]]
    workflow_trend: Optional[dict[str, Any]]
    memory_health: dict[str, Any]
    decision_stats: Optional[dict[str, Any]]
    contradictions: Optional[list[dict[str, Any]]]
    unfinished_branches: Optional[list[dict[str, Any]]]
    journal_backfills: Optional[int]
    patterns_detected: Optional[int]
    created_at: datetime


class MemoryMetricsList(BaseModel):
    metrics: list[MemoryMetricsResponse]
    total: int
