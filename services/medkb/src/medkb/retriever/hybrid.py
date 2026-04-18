from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from medkb.retriever.protocol import RetrievedChunk

logger = logging.getLogger(__name__)

RRF_K = 60


class HybridRetriever:
    name: str = "hybrid"

    def __init__(
        self,
        *,
        dense,
        sparse,
        weight_dense: float = 0.7,
    ):
        self._dense = dense
        self._sparse = sparse
        self._weight_dense = weight_dense
        self._weight_sparse = 1.0 - weight_dense

    async def retrieve(
        self,
        query: str,
        *,
        k: int = 8,
        filters: dict | None = None,
        corpus_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        dense_results, sparse_results = await asyncio.gather(
            self._dense.retrieve(query, k=k * 2, filters=filters, corpus_ids=corpus_ids),
            self._sparse.retrieve(query, k=k * 2, filters=filters, corpus_ids=corpus_ids),
        )

        rrf_scores: dict[str, float] = defaultdict(float)
        chunk_map: dict[str, RetrievedChunk] = {}

        for rank, chunk in enumerate(dense_results):
            rrf_scores[chunk.chunk_id] += self._weight_dense / (RRF_K + rank + 1)
            chunk_map[chunk.chunk_id] = chunk

        for rank, chunk in enumerate(sparse_results):
            rrf_scores[chunk.chunk_id] += self._weight_sparse / (RRF_K + rank + 1)
            if chunk.chunk_id not in chunk_map:
                chunk_map[chunk.chunk_id] = chunk

        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)[:k]

        results = []
        for i, chunk_id in enumerate(sorted_ids):
            original = chunk_map[chunk_id]
            results.append(
                RetrievedChunk(
                    chunk_id=original.chunk_id,
                    document_id=original.document_id,
                    corpus_id=original.corpus_id,
                    text=original.text,
                    section=original.section,
                    metadata=original.metadata,
                    retriever_source="hybrid",
                    raw_score=rrf_scores[chunk_id],
                    fusion_rank=i + 1,
                )
            )
        return results
