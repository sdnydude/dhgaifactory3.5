# services/vs-engine/tests/test_api.py
"""Integration tests for VS Engine API endpoints."""

import os
import sys
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with mocked LLM dependencies."""
    with patch("llm_router.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = json.dumps({
            "responses": [
                {"content": "Response A", "confidence": 0.35},
                {"content": "Response B", "confidence": 0.35},
                {"content": "Response C", "confidence": 0.30},
            ]
        })
        from main import app
        with TestClient(app) as c:
            yield c, mock_gen


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        c, _ = client
        response = c.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_includes_component_status(self, client):
        c, _ = client
        response = c.get("/health")
        data = response.json()
        assert "ollama" in data
        assert "anthropic" in data
        assert "distributions_cached" in data


class TestMetricsEndpoint:
    def test_metrics_returns_prometheus_format(self, client):
        c, _ = client
        response = c.get("/metrics")
        assert response.status_code == 200
        assert "vs_generations_total" in response.text
        assert "vs_distributions_cached" in response.text


class TestGenerateEndpoint:
    def test_generate_returns_distribution(self, client):
        c, mock_gen = client
        response = c.post("/vs/generate", json={
            "prompt": "Generate 3 approaches",
            "k": 3,
            "tau": 0.10,
        })
        assert response.status_code == 200
        data = response.json()
        assert "distribution_id" in data
        assert "items" in data
        assert len(data["items"]) >= 1
        # Verify spec-compliant response fields (C2 fix)
        assert "k" in data
        assert "tau" in data
        assert "sum_probability" in data
        assert "num_filtered" in data
        assert "created_at" in data
        # Verify item metadata structure (C1 fix)
        item = data["items"][0]
        assert "metadata" in item
        assert "label" in item["metadata"]
        assert item["metadata"]["label"] in ("conventional", "novel", "exploratory")

    def test_generate_uses_phase_defaults(self, client):
        c, mock_gen = client
        response = c.post("/vs/generate", json={
            "prompt": "Generate gap analysis",
            "phase": "gap_analysis",
        })
        assert response.status_code == 200
        data = response.json()
        # gap_analysis phase defaults: k=4, tau=0.10
        assert data["k"] == 4
        assert data["tau"] == 0.10

    def test_generate_validates_prompt_required(self, client):
        c, _ = client
        response = c.post("/vs/generate", json={})
        assert response.status_code == 422

    def test_generate_unsupported_variant_returns_422(self, client):
        c, _ = client
        response = c.post("/vs/generate", json={
            "prompt": "test",
            "variant": "multi",
        })
        assert response.status_code == 422


class TestSelectEndpoint:
    def test_select_from_cached_distribution(self, client):
        c, mock_gen = client
        gen_response = c.post("/vs/generate", json={
            "prompt": "Generate approaches", "k": 3,
        })
        dist_id = gen_response.json()["distribution_id"]
        sel_response = c.post("/vs/select", json={
            "distribution_id": dist_id, "strategy": "argmax",
        })
        assert sel_response.status_code == 200
        data = sel_response.json()
        assert "selected" in data
        assert data["strategy_used"] == "argmax"

    def test_select_unknown_distribution_returns_404(self, client):
        c, _ = client
        response = c.post("/vs/select", json={
            "distribution_id": "nonexistent-id", "strategy": "argmax",
        })
        assert response.status_code == 404

    def test_select_human_requires_index(self, client):
        c, mock_gen = client
        gen_response = c.post("/vs/generate", json={"prompt": "test", "k": 3})
        dist_id = gen_response.json()["distribution_id"]
        response = c.post("/vs/select", json={
            "distribution_id": dist_id, "strategy": "human",
        })
        assert response.status_code == 422

    def test_select_human_index_out_of_bounds(self, client):
        c, mock_gen = client
        gen_response = c.post("/vs/generate", json={"prompt": "test", "k": 3})
        dist_id = gen_response.json()["distribution_id"]
        response = c.post("/vs/select", json={
            "distribution_id": dist_id, "strategy": "human", "human_selection_index": 99,
        })
        assert response.status_code == 422


class TestErrorPaths:
    def test_generate_llm_failure_returns_502(self, client):
        c, mock_gen = client
        mock_gen.side_effect = RuntimeError("Anthropic API error")
        response = c.post("/vs/generate", json={"prompt": "test", "k": 3})
        assert response.status_code == 502

    def test_generate_ollama_unreachable_returns_503(self, client):
        c, mock_gen = client
        import httpx as httpx_mod
        mock_gen.side_effect = httpx_mod.ConnectError("Connection refused")
        response = c.post("/vs/generate", json={"prompt": "test", "k": 3})
        assert response.status_code == 503

    def test_generate_unparseable_json_retries(self, client):
        c, mock_gen = client
        import json as json_mod
        mock_gen.side_effect = [
            "this is not json at all",
            json_mod.dumps({"responses": [
                {"content": "A", "confidence": 0.5},
                {"content": "B", "confidence": 0.5},
            ]}),
        ]
        response = c.post("/vs/generate", json={"prompt": "test", "k": 2})
        assert response.status_code == 200
        assert mock_gen.call_count == 2


class TestEvaluateEndpoint:
    def test_evaluate_diversity_only(self, client):
        c, _ = client
        with patch("evaluators.diversity.compute_pairwise_diversity") as mock_div, \
             patch("llm_router.embed_with_ollama", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 768
            mock_div.return_value = {
                "avg_diversity": 0.72, "min_diversity": 0.58,
                "max_diversity": 0.89, "std_diversity": 0.11,
            }
            response = c.post("/vs/evaluate", json={
                "items": [
                    {"content": "Response A", "probability": 0.5},
                    {"content": "Response B", "probability": 0.5},
                ],
                "evaluators": ["diversity"],
            })
            assert response.status_code == 200
            data = response.json()
            assert "diversity" in data

    def test_evaluate_requires_min_2_items(self, client):
        c, _ = client
        response = c.post("/vs/evaluate", json={
            "items": [{"content": "Only one", "probability": 1.0}],
            "evaluators": ["diversity"],
        })
        assert response.status_code == 422

    def test_evaluate_both_evaluators(self, client):
        c, mock_gen = client
        import json as json_mod
        mock_gen.return_value = json_mod.dumps({
            "fluency": {"score": 4, "justification": "Good"},
            "flexibility": {"score": 3, "justification": "OK"},
            "originality": {"score": 4, "justification": "Novel"},
            "elaboration": {"score": 3, "justification": "Adequate"},
        })
        with patch("evaluators.diversity.compute_pairwise_diversity") as mock_div, \
             patch("llm_router.embed_with_ollama", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 768
            mock_div.return_value = {
                "avg_diversity": 0.72, "min_diversity": 0.58,
                "max_diversity": 0.89, "std_diversity": 0.11,
            }
            response = c.post("/vs/evaluate", json={
                "items": [
                    {"content": "Response A", "probability": 0.5},
                    {"content": "Response B", "probability": 0.5},
                ],
                "evaluators": ["diversity", "ttct"],
            })
            assert response.status_code == 200
            data = response.json()
            assert "diversity" in data
            assert "ttct" in data

    def test_evaluate_ttct_failure_partial_success(self, client):
        c, mock_gen = client
        mock_gen.side_effect = RuntimeError("Judge model unavailable")
        with patch("evaluators.diversity.compute_pairwise_diversity") as mock_div, \
             patch("llm_router.embed_with_ollama", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 768
            mock_div.return_value = {
                "avg_diversity": 0.72, "min_diversity": 0.58,
                "max_diversity": 0.89, "std_diversity": 0.11,
            }
            response = c.post("/vs/evaluate", json={
                "items": [
                    {"content": "A", "probability": 0.5},
                    {"content": "B", "probability": 0.5},
                ],
                "evaluators": ["diversity", "ttct"],
            })
            assert response.status_code == 200
            data = response.json()
            assert "diversity" in data
            assert "error" in data.get("ttct", {})

    def test_evaluate_ttct_only_failure_returns_503(self, client):
        c, mock_gen = client
        mock_gen.side_effect = RuntimeError("Judge model unavailable")
        response = c.post("/vs/evaluate", json={
            "items": [
                {"content": "A", "probability": 0.5},
                {"content": "B", "probability": 0.5},
            ],
            "evaluators": ["ttct"],
        })
        assert response.status_code == 503
