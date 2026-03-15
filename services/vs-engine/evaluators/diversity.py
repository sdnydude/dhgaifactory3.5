# Copyright 2024 CHATS-lab contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Ported and adapted for DHG AI Factory VS Engine from CHATS-lab analysis/evals/
"""Diversity evaluation utilities for Verbalized Sampling responses.

Provides pairwise embedding diversity (cosine distance) and text-level
lexical richness metrics. Uses pure numpy — no torch or sklearn dependency.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def compute_pairwise_diversity(
    embeddings: list[list[float]],
) -> dict[str, float]:
    """Compute pairwise diversity across a set of embeddings.

    Diversity for a pair is defined as 1 - cosine_similarity, so identical
    vectors yield 0.0 and orthogonal vectors yield 1.0.

    Only the upper triangle of the pairwise matrix is used — no diagonal,
    no double-counting.

    Args:
        embeddings: List of embedding vectors (lists or numpy arrays).
            All vectors must have the same dimensionality.

    Returns:
        Dict with keys:
            avg_diversity  — mean pairwise diversity (0.0 when < 2 items)
            min_diversity  — minimum pairwise diversity (0.0 when < 2 items)
            max_diversity  — maximum pairwise diversity (0.0 when < 2 items)
            std_diversity  — std dev of pairwise diversity (0.0 when < 2 items)
            num_pairs      — number of pairs evaluated
    """
    zero_result: dict[str, float] = {
        "avg_diversity": 0.0,
        "min_diversity": 0.0,
        "max_diversity": 0.0,
        "std_diversity": 0.0,
        "num_pairs": 0.0,
    }

    if len(embeddings) < 2:
        return zero_result

    mat = np.array(embeddings, dtype=np.float64)  # shape (n, d)
    n = mat.shape[0]

    # L2-normalise each row so cosine similarity = dot product.
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    # Guard against zero-norm vectors.
    norms = np.where(norms == 0.0, 1.0, norms)
    mat = mat / norms  # (n, d) — unit vectors

    # Full pairwise cosine similarity matrix.
    sim_matrix = mat @ mat.T  # (n, n)

    # Extract upper triangle indices (above diagonal).
    row_idx, col_idx = np.triu_indices(n, k=1)
    pairwise_sim = sim_matrix[row_idx, col_idx]

    # Diversity = 1 - similarity; clip to [0, 1] to handle float rounding.
    pairwise_div = np.clip(1.0 - pairwise_sim, 0.0, 1.0)

    return {
        "avg_diversity": float(np.mean(pairwise_div)),
        "min_diversity": float(np.min(pairwise_div)),
        "max_diversity": float(np.max(pairwise_div)),
        "std_diversity": float(np.std(pairwise_div)),
        "num_pairs": float(len(pairwise_div)),
    }


def compute_text_metrics(texts: list[str]) -> dict[str, Any]:
    """Compute lexical richness and length metrics across a set of texts.

    Args:
        texts: List of response strings.

    Returns:
        Dict with keys:
            avg_response_length  — mean word count per text
            vocabulary_richness  — unique tokens / total tokens across all texts
            total_tokens         — total word count across all texts
            unique_tokens        — unique word count across all texts
            num_texts            — number of texts evaluated
    """
    if not texts:
        return {
            "avg_response_length": 0.0,
            "vocabulary_richness": 0.0,
            "total_tokens": 0,
            "unique_tokens": 0,
            "num_texts": 0,
        }

    word_counts: list[int] = []
    all_tokens: list[str] = []

    for text in texts:
        tokens = text.split()
        word_counts.append(len(tokens))
        all_tokens.extend(tokens)

    total_tokens = len(all_tokens)
    unique_tokens = len(set(all_tokens))

    vocabulary_richness = (
        unique_tokens / total_tokens if total_tokens > 0 else 0.0
    )
    avg_response_length = (
        sum(word_counts) / len(word_counts) if word_counts else 0.0
    )

    return {
        "avg_response_length": avg_response_length,
        "vocabulary_richness": vocabulary_richness,
        "total_tokens": total_tokens,
        "unique_tokens": unique_tokens,
        "num_texts": len(texts),
    }
