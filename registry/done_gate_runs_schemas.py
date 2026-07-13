"""Pydantic schemas for the done-gate runs API — Loop 4 self-training."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


VALID_VERDICTS = {"pass", "fail", "no_claim"}
VALID_ADJUDICATIONS = {"true_positive", "false_positive", "false_negative"}


class DoneGateRunCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")  # hook may add fields; never reject a capture

    session_id: str = Field(..., max_length=128)
    project: str = Field(..., max_length=100)
    verdict: str = Field(..., max_length=16)
    claim: Optional[dict[str, Any]] = None
    evidence: Optional[list[str]] = None
    gate_mode: str = Field(default="observe", max_length=16)
    check_version: int = Field(default=1, ge=1)
    sampled: bool = False  # recall-sampling row (protocol §12.3 false-negative path)
    meta_data: Optional[dict[str, Any]] = None


class DoneGateRunAdjudicate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adjudication: str = Field(..., max_length=16)


class DoneGateRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: str
    project: str
    verdict: str
    claim: Optional[dict[str, Any]]
    evidence: Optional[list[str]]
    gate_mode: str
    check_version: int
    adjudication: Optional[str]
    sampled: bool
    adjudicated_at: Optional[datetime] = None
    meta_data: Optional[dict[str, Any]]
    created_at: datetime


class DoneGateRunList(BaseModel):
    runs: list[DoneGateRunResponse]
    total: int


class DoneGateStats(BaseModel):
    """Per-check_version rollup — the ratchet promotion input (§12.5)."""
    check_version: int
    total: int
    passes: int
    fails: int
    adjudicated: int
    true_positives: int
    false_positives: int
    false_negatives: int = 0   # from sampled rows (§12.3 recall path)
    sampled_total: int = 0
    precision: Optional[float] = None  # tp / (tp + fp), None until any fail adjudicated


class DoneGateStatsResponse(BaseModel):
    project: Optional[str] = None
    versions: list[DoneGateStats]
