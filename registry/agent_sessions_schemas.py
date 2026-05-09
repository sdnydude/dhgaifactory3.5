"""Pydantic schemas for the agent_sessions API.

Tracks Claude Code sessions, scheduled routines, and subagent runs
across all DHG projects with summary, tldr, commits, and skills_used.
"""
from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


Source = Literal["claude-code", "scheduled-routine", "subagent"]


class AgentSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    project: str
    branch: Optional[str] = None
    source: Source = "claude-code"
    model: Optional[str] = None
    summary: Optional[str] = None
    tldr: Optional[str] = None
    commits: list[str] = Field(default_factory=list)
    files_changed: Optional[int] = None
    skills_used: list[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    meta_data: Optional[dict[str, Any]] = None


class AgentSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: str
    project: str
    branch: Optional[str]
    source: str
    model: Optional[str]
    summary: Optional[str]
    tldr: Optional[str]
    commits: list[Any]
    files_changed: Optional[int]
    skills_used: list[Any]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime
    meta_data: Optional[dict[str, Any]]


class AgentSessionList(BaseModel):
    sessions: list[AgentSessionResponse]
    total: int
