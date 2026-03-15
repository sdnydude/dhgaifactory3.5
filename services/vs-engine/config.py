# services/vs-engine/config.py
"""Phase defaults and environment variable loading for VS Engine."""

import os
from typing import Any, Dict

PHASE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "brainstorm": {
        "k": 5, "tau": 0.08, "min_probability": 0.03,
        "model": "qwen3:14b", "confidence_framing": "confidence",
    },
    "cme_content": {
        "k": 5, "tau": 0.08, "min_probability": 0.03,
        "model": "claude-sonnet-4-20250514", "confidence_framing": "confidence",
    },
    "review": {
        "k": 5, "tau": 0.08, "min_probability": 0.03,
        "model": "qwen3:14b", "confidence_framing": "confidence",
    },
    "human_review": {
        "k": 3, "tau": 0.08, "min_probability": 0.05,
        "model": "claude-sonnet-4-20250514", "confidence_framing": "confidence",
    },
    "gap_analysis": {
        "k": 4, "tau": 0.10, "min_probability": 0.03,
        "model": "qwen3:14b", "confidence_framing": "confidence",
    },
    "custom": {
        "k": 5, "tau": 0.08, "min_probability": 0.03,
        "model": "qwen3:14b", "confidence_framing": "confidence",
    },
}


def get_phase_defaults(phase: str) -> Dict[str, Any]:
    """Return a copy of phase defaults for the given phase name.

    Falls back to "custom" defaults for unknown phase names.
    """
    return dict(PHASE_DEFAULTS.get(phase, PHASE_DEFAULTS["custom"]))


def get_ollama_url() -> str:
    """Return the Ollama base URL from environment or default."""
    return os.getenv("OLLAMA_BASE_URL", "http://dhg-ollama:11434")


def get_log_level() -> str:
    """Return the log level from environment or default INFO."""
    return os.getenv("LOG_LEVEL", "INFO")


CONFIDENCE_FRAMINGS: Dict[str, str] = {
    "confidence": "confidence",
    "likelihood": "likelihood",
    "probability": "probability",
    "percentage": "percentage",
    "explicit": "probability",
    "relative": "relative likelihood",
    "perplexity": "perplexity",
}
