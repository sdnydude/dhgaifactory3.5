# langgraph_workflows/dhg-agents-cloud/tests/test_vs_client.py
"""Tests for VS Engine client module."""

import os
import sys
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def mock_httpx_response():
    """Create a mock httpx Response."""
    def _make(status_code=200, json_data=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.raise_for_status = MagicMock()
        if status_code >= 400:
            from httpx import HTTPStatusError
            resp.raise_for_status.side_effect = HTTPStatusError(
                "error", request=MagicMock(), response=resp
            )
        return resp
    return _make


class TestVSGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_distribution(self, mock_httpx_response):
        from vs_client import vs_generate

        mock_resp = mock_httpx_response(200, {
            "distribution_id": "dist-123",
            "items": [
                {"content": "Approach A", "probability": 0.4, "metadata": {"label": "conventional"}},
                {"content": "Approach B", "probability": 0.35, "metadata": {"label": "novel"}},
                {"content": "Approach C", "probability": 0.25, "metadata": {"label": "exploratory"}},
            ],
            "model": "qwen3:14b",
            "phase": "gap_analysis",
            "k": 3,
            "tau": 0.08,
            "sum_probability": 1.0,
            "tau_relaxed": False,
            "num_filtered": 0,
            "created_at": "2026-03-14T12:00:00Z",
        })

        with patch("vs_client.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = mock_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await vs_generate(
                prompt="Generate 3 approaches to gap analysis for NSCLC",
                phase="gap_analysis",
                k=3,
            )

            assert result["distribution_id"] == "dist-123"
            assert len(result["items"]) == 3
            client_instance.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_graceful_degradation_when_unavailable(self, mock_httpx_response):
        from vs_client import vs_generate

        with patch("vs_client.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            import httpx
            client_instance.post.side_effect = httpx.ConnectError("Connection refused")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await vs_generate(
                prompt="Generate approaches",
                phase="gap_analysis",
            )

            # Graceful degradation: returns None, agent falls back to standard generation
            assert result is None

    @pytest.mark.asyncio
    async def test_generate_passes_custom_model(self, mock_httpx_response):
        from vs_client import vs_generate

        mock_resp = mock_httpx_response(200, {
            "distribution_id": "dist-456",
            "items": [{"content": "A", "probability": 1.0, "metadata": {}}],
            "model": "claude-sonnet-4-20250514",
            "phase": "custom",
            "k": 5, "tau": 0.08,
            "sum_probability": 1.0, "tau_relaxed": False,
            "num_filtered": 0, "created_at": "2026-03-14T12:00:00Z",
        })

        with patch("vs_client.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = mock_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await vs_generate(
                prompt="test", model="claude-sonnet-4-20250514",
            )

            call_args = client_instance.post.call_args
            body = call_args[1].get("json", {})
            assert body.get("model") == "claude-sonnet-4-20250514"


class TestVSSelect:
    @pytest.mark.asyncio
    async def test_select_argmax(self, mock_httpx_response):
        from vs_client import vs_select

        mock_resp = mock_httpx_response(200, {
            "selected": {"content": "Best approach", "probability": 0.4, "metadata": {}},
            "strategy_used": "argmax",
            "distribution_id": "dist-123",
        })

        with patch("vs_client.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = mock_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await vs_select("dist-123", strategy="argmax")
            assert result["strategy_used"] == "argmax"

    @pytest.mark.asyncio
    async def test_select_graceful_degradation(self, mock_httpx_response):
        from vs_client import vs_select

        with patch("vs_client.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            import httpx
            client_instance.post.side_effect = httpx.ConnectError("Connection refused")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await vs_select("dist-123", strategy="argmax")
            assert result is None


class TestVSErrorPaths:
    @pytest.mark.asyncio
    async def test_generate_returns_none_on_http_502(self, mock_httpx_response):
        from vs_client import vs_generate

        mock_resp = mock_httpx_response(502)

        with patch("vs_client.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = mock_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await vs_generate(prompt="test", phase="gap_analysis")
            assert result is None

    @pytest.mark.asyncio
    async def test_generate_returns_none_on_timeout(self):
        from vs_client import vs_generate

        with patch("vs_client.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            import httpx
            client_instance.post.side_effect = httpx.ReadTimeout("timed out")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await vs_generate(prompt="test", phase="gap_analysis")
            assert result is None

    @pytest.mark.asyncio
    async def test_generate_returns_none_on_malformed_json(self, mock_httpx_response):
        from vs_client import vs_generate

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.side_effect = ValueError("Invalid JSON")

        with patch("vs_client.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = mock_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await vs_generate(prompt="test", phase="gap_analysis")
            assert result is None


class TestVSHealthCheck:
    @pytest.mark.asyncio
    async def test_is_available_true(self, mock_httpx_response):
        from vs_client import vs_is_available

        mock_resp = mock_httpx_response(200, {"status": "healthy"})

        with patch("vs_client.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get.return_value = mock_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            assert await vs_is_available() is True

    @pytest.mark.asyncio
    async def test_is_available_false_when_unreachable(self, mock_httpx_response):
        from vs_client import vs_is_available

        with patch("vs_client.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            import httpx
            client_instance.get.side_effect = httpx.ConnectError("refused")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            assert await vs_is_available() is False
