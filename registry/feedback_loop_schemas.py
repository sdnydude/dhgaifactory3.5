"""Pydantic schemas for feedback-loop endpoints."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class TypeStat(BaseModel):
    type: str
    count_7d: int
    count_total: int
    last_capture: Optional[str] = None


class FeedbackLoopHealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "dead"]
    healthy_types: int
    total_types: int
    types: list[TypeStat]
