from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    corpus_id: str
    text: str
    section: str | None
    metadata: dict
    retriever_source: str
    raw_score: float
    fusion_rank: int | None = None


@runtime_checkable
class Retriever(Protocol):
    name: str

    async def retrieve(
        self,
        query: str,
        *,
        k: int,
        filters: dict | None = None,
        corpus_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]: ...
