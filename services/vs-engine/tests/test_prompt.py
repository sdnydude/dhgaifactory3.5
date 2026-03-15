# services/vs-engine/tests/test_prompt.py
import pytest


class TestPromptBuilder:
    def test_standard_prompt_contains_k(self):
        from prompt_builder import build_vs_prompt
        prompt = build_vs_prompt(user_prompt="Generate gap analysis", k=5, tau=0.08, confidence_framing="confidence")
        assert "5 distinct responses" in prompt

    def test_standard_prompt_contains_tau(self):
        from prompt_builder import build_vs_prompt
        prompt = build_vs_prompt(user_prompt="Generate gap analysis", k=5, tau=0.08, confidence_framing="confidence")
        assert "0.08" in prompt

    def test_prompt_contains_user_prompt(self):
        from prompt_builder import build_vs_prompt
        prompt = build_vs_prompt(user_prompt="Analyze NSCLC immunotherapy gaps", k=3, tau=0.10, confidence_framing="confidence")
        assert "Analyze NSCLC immunotherapy gaps" in prompt

    def test_prompt_contains_json_format(self):
        from prompt_builder import build_vs_prompt
        prompt = build_vs_prompt(user_prompt="test", k=3, tau=0.10, confidence_framing="confidence")
        assert '"responses"' in prompt
        assert '"content"' in prompt
        assert '"confidence"' in prompt

    def test_framing_substitution(self):
        from prompt_builder import build_vs_prompt
        prompt = build_vs_prompt(user_prompt="test", k=3, tau=0.10, confidence_framing="likelihood")
        assert "likelihood" in prompt

    def test_system_prompt_prepended(self):
        from prompt_builder import build_vs_prompt
        prompt = build_vs_prompt(user_prompt="test", k=3, tau=0.10, confidence_framing="confidence", system_prompt="You are a medical expert.")
        assert prompt.startswith("You are a medical expert.")
