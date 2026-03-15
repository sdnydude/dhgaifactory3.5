"""Tests for DiversityEvaluator."""

import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestDiversityEvaluator:

    def test_identical_texts_have_low_diversity(self):
        from evaluators.diversity import compute_pairwise_diversity
        embeddings = [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
        result = compute_pairwise_diversity(embeddings)
        assert result["avg_diversity"] < 0.01

    def test_orthogonal_texts_have_high_diversity(self):
        from evaluators.diversity import compute_pairwise_diversity
        embeddings = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        result = compute_pairwise_diversity(embeddings)
        assert result["avg_diversity"] > 0.9

    def test_single_item_returns_zero_diversity(self):
        from evaluators.diversity import compute_pairwise_diversity
        result = compute_pairwise_diversity([[1.0, 0.0, 0.0]])
        assert result["avg_diversity"] == 0.0

    def test_empty_input_returns_zero_diversity(self):
        from evaluators.diversity import compute_pairwise_diversity
        result = compute_pairwise_diversity([])
        assert result["avg_diversity"] == 0.0

    def test_vocabulary_richness_calculation(self):
        from evaluators.diversity import compute_text_metrics
        texts = ["the quick brown fox", "the quick brown dog"]
        metrics = compute_text_metrics(texts)
        assert metrics["avg_response_length"] == 4
        assert metrics["vocabulary_richness"] > 0

    def test_vocabulary_richness_identical_texts(self):
        from evaluators.diversity import compute_text_metrics
        texts = ["hello world", "hello world"]
        metrics = compute_text_metrics(texts)
        assert metrics["vocabulary_richness"] == 0.5
