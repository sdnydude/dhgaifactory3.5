# services/vs-engine/tests/test_config.py
import os
import pytest


class TestPhaseDefaults:
    def test_known_phase_returns_defaults(self):
        from config import get_phase_defaults
        defaults = get_phase_defaults("brainstorm")
        assert defaults["k"] == 5
        assert defaults["tau"] == 0.08
        assert defaults["min_probability"] == 0.03
        assert defaults["model"] == "qwen3:14b"

    def test_unknown_phase_returns_custom_defaults(self):
        from config import get_phase_defaults
        defaults = get_phase_defaults("nonexistent_phase")
        assert defaults["k"] == 5
        assert defaults["model"] == "qwen3:14b"

    def test_human_review_has_higher_min_p(self):
        from config import get_phase_defaults
        defaults = get_phase_defaults("human_review")
        assert defaults["min_probability"] == 0.05
        assert defaults["k"] == 3

    def test_cme_content_uses_claude(self):
        from config import get_phase_defaults
        defaults = get_phase_defaults("cme_content")
        assert "claude" in defaults["model"]


class TestEnvConfig:
    def test_ollama_url_default(self):
        from config import get_ollama_url
        url = get_ollama_url()
        assert "11434" in url

    def test_ollama_url_from_env(self, monkeypatch):
        from config import get_ollama_url
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom:9999")
        import importlib
        import config
        importlib.reload(config)
        from config import get_ollama_url
        assert get_ollama_url() == "http://custom:9999"

    def test_log_level_default(self):
        from config import get_log_level
        assert get_log_level() in ("INFO", "DEBUG", "WARNING", "ERROR")
