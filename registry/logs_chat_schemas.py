"""Logs-chat API schemas (P5 T10).

POST /api/logs/chat answers a natural-language question about container logs.
SSE protocol (talkback lineage):

  event: citations  data: {"container", "queries": [{"desc","logql","lines"}], "sample": [str, ...]}
  event: heartbeat  data: {"phase": "retrieve"|"generate", "elapsed_ms": int}
  event: delta      data: {"text": "..."}          (repeated, post-grounding)
  event: degraded   data: {"message", "elapsed_ms"} (partial/late answer)
  event: error      data: {"message": "..."}       (terminal, replaces done)
  event: done       data: {"model", "elapsed_ms", "context_lines"}
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LogsChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    question: str = Field(min_length=3, max_length=500)
    container: Optional[str] = Field(default=None, max_length=128)
    minutes: int = Field(default=60, ge=1, le=1440)


class QuerySpec(BaseModel):
    """One deterministic LogQL query the service ran for an answer."""
    desc: str
    logql: str
    lines: int = 0
