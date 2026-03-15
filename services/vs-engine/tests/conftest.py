"""Shared test fixtures for VS Engine tests."""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directory to path so tests can import from the service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_parsed_responses():
    """Sample parsed LLM responses for testing postprocess_responses."""
    return [
        {"response": "Approach A: Focus on PD-L1 testing gaps", "probability": 0.25},
        {"response": "Approach B: Examine disparities in access", "probability": 0.20},
        {"response": "Approach C: Analyze biomarker utilization", "probability": 0.20},
        {"response": "Approach D: Review combination therapy awareness", "probability": 0.20},
        {"response": "Approach E: Assess real-world evidence gaps", "probability": 0.15},
    ]


@pytest.fixture
def mock_ollama_generate():
    """Mock httpx response from Ollama /api/generate."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": '{"responses": [{"content": "Response 1", "confidence": 0.3}, {"content": "Response 2", "confidence": 0.4}, {"content": "Response 3", "confidence": 0.3}]}'
    }
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.fixture
def mock_ollama_embed():
    """Mock httpx response from Ollama /api/embed."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "embeddings": [[0.1] * 768]
    }
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.fixture
def mock_ollama_health():
    """Mock httpx response from Ollama /api/tags (health check)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    return mock_response
