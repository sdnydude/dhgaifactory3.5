"""Talkback API schemas.

Talkback is the docs-hub assistant: hybrid doc_pages retrieval feeding a
streamed LLM answer. The endpoint responds with Server-Sent Events:

  event: citations   data: {"citations": [{"title", "project", "source_file", "url"}]}
  event: delta       data: {"text": "..."}          (repeated)
  event: error       data: {"message": "..."}       (terminal, replaces done)
  event: done        data: {"model": "...", "elapsed_ms": int}
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TalkbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=500)
    model: Literal["local", "haiku"] = "local"
    project_name: Optional[str] = None


class TalkbackCitation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: Optional[str] = None
    project: str
    source_file: str
    url: Optional[str] = None
