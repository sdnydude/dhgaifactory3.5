from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy import text

from medkb.retriever.protocol import RetrievedChunk

logger = logging.getLogger(__name__)


class BM25Retriever:
    name: str = "bm25"

    def __init__(self, *, session_factory: Callable):
        self._session_factory = session_factory

    async def retrieve(
        self,
        query: str,
        *,
        k: int,
        filters: dict | None = None,
        corpus_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        corpus_filter = ""
        params: dict[str, Any] = {"query": query, "k": k}

        if corpus_ids:
            corpus_filter = "AND cor.name = ANY(:corpus_names)"
            params["corpus_names"] = corpus_ids

        sql = text(f"""
            SELECT c.id, c.document_id, c.corpus_id, c.chunk_text, c.section,
                   c.metadata,
                   ts_rank_cd(c.tsv, plainto_tsquery('english', :query)) AS rank
            FROM medkb.chunks c
            JOIN medkb.corpora cor ON cor.id = c.corpus_id
            WHERE c.tsv @@ plainto_tsquery('english', :query)
              {corpus_filter}
            ORDER BY rank DESC
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
                raw_score=float(row.rank),
            )
            for row in rows
        ]
