from __future__ import annotations

import logging
from collections.abc import Callable

from medkb.retriever.bm25 import BM25Retriever
from medkb.retriever.hybrid import HybridRetriever
from medkb.retriever.pgvector import PgVectorRetriever
from medkb.retriever.protocol import Retriever

logger = logging.getLogger(__name__)


def build_default_retriever(
    *,
    session_factory: Callable,
    embed_fn: Callable,
    hybrid_weight_dense: float = 0.7,
) -> Retriever:
    dense = PgVectorRetriever(session_factory=session_factory, embed_fn=embed_fn)
    sparse = BM25Retriever(session_factory=session_factory)
    return HybridRetriever(
        dense=dense,
        sparse=sparse,
        weight_dense=hybrid_weight_dense,
    )


def build_dense_only_retriever(
    *,
    session_factory: Callable,
    embed_fn: Callable,
) -> Retriever:
    return PgVectorRetriever(session_factory=session_factory, embed_fn=embed_fn)
