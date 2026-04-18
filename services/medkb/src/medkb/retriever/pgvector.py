from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy import text

from medkb.retriever.protocol import RetrievedChunk

logger = logging.getLogger(__name__)


class PgVectorRetriever:
    name: str = "pgvector"

    def __init__(
        self,
        *,
        session_factory: Callable,
        embed_fn: Callable,
    ):
        self._session_factory = session_factory
        self._embed_fn = embed_fn

    async def retrieve(
        self,
        query: str,
        *,
        k: int,
        filters: dict | None = None,
        corpus_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        query_embedding = await self._embed_fn(query)

        corpus_filter = ""
        params: dict[str, Any] = {
            "embedding": str(query_embedding),
            "k": k,
        }

        if corpus_ids:
            corpus_filter = "AND c.corpus_id = ANY(:corpus_ids)"
            params["corpus_ids"] = corpus_ids

        sql = text(f"""
            SELECT c.id, c.document_id, c.corpus_id, c.chunk_text, c.section,
                   c.metadata,
                   CASE WHEN c.active_version = 1
                        THEN c.embedding_v1 <=> :embedding::vector
                        ELSE c.embedding_v2 <=> :embedding::vector
                   END AS distance
            FROM medkb.chunks c
            WHERE c.embedding_v1 IS NOT NULL
              {corpus_filter}
            ORDER BY distance ASC
            LIMIT :k
        """)

        session_ctx = await self._session_factory()
        async with session_ctx as session:
            result = await session.execute(sql, params)
            rows = result.all()

        return [
            RetrievedChunk(
                chunk_id=str(row.id),
                document_id=str(row.document_id),
                corpus_id=str(row.corpus_id),
                text=row.chunk_text,
                section=row.section,
                metadata=row.metadata_ if hasattr(row, "metadata_") else (row.metadata or {}),
                retriever_source=self.name,
                raw_score=1.0 - (row.distance or 0.0),
            )
            for row in rows
        ]
