"""
Smoke tests for the DHG agent boilerplate.

These run with no Langfuse credentials and no LLM provider reachable: they
import the agent, assert tracing degrades to a documented no-op, and assert the
OTLP environment is built correctly when credentials *are* present. No network
call is made in either case.
"""

import base64
import importlib
import os

import pytest

LANGFUSE_ENV_KEYS = (
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_OTLP_ENDPOINT",
)
OTEL_ENV_KEYS = (
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_HEADERS",
    "OTEL_EXPORTER_OTLP_PROTOCOL",
)
PROVIDER_ENV_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AGENT_MODEL")
REGISTRY_ENV_KEYS = ("AI_FACTORY_REGISTRY_URL",)


@pytest.fixture
def no_langfuse(monkeypatch):
    """Environment with every Langfuse, OTLP and provider variable removed.

    The provider key is removed deliberately: the agent must import and build
    on a machine with no LLM credentials at all.
    """
    for key in LANGFUSE_ENV_KEYS + OTEL_ENV_KEYS + PROVIDER_ENV_KEYS + REGISTRY_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


def test_tracing_disabled_without_langfuse_keys(no_langfuse):
    import tracing

    importlib.reload(tracing)

    assert tracing.tracing_enabled() is False
    assert tracing.langfuse_credentials() is None
    assert tracing.configure_tracing("test-agent") is False
    # The no-op must not leak OTLP configuration into the process environment.
    for key in OTEL_ENV_KEYS:
        assert key not in os.environ


def test_agent_module_constructs_untraced(no_langfuse):
    import agent

    importlib.reload(agent)

    assert agent.TRACING_ENABLED is False
    assert agent.AGENT_ID
    assert agent.MODEL is None  # no default model id; unset constructs against the test model
    # The Pydantic AI agent and its typed output contract exist.
    assert agent.agent is not None
    assert "summary" in agent.AgentOutput.model_fields
    assert "confidence" in agent.AgentOutput.model_fields
    # The CLI entry point is wired.
    assert callable(agent.main)


def test_prompts_live_in_a_versioned_prompt_module(no_langfuse):
    import agent
    from prompts import template_agent

    importlib.reload(agent)

    assert template_agent.TEMPLATE_AGENT_SYSTEM_PROMPT.strip()
    assert "{topic}" in template_agent.TEMPLATE_AGENT_TASK_PROMPT
    assert agent.SYSTEM_PROMPT is template_agent.TEMPLATE_AGENT_SYSTEM_PROMPT


def test_otlp_env_built_from_dummy_keys(no_langfuse):
    """With credentials present the OTLP env is built. No network call is made:
    build_otlp_env is pure string work."""
    import tracing

    importlib.reload(tracing)

    no_langfuse.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-dummy")
    no_langfuse.setenv("LANGFUSE_SECRET_KEY", "sk-lf-dummy")

    assert tracing.tracing_enabled() is True

    built = tracing.build_otlp_env("pk-lf-dummy", "sk-lf-dummy")
    expected = base64.b64encode(b"pk-lf-dummy:sk-lf-dummy").decode("ascii")

    assert built["OTEL_EXPORTER_OTLP_ENDPOINT"] == tracing.DEFAULT_OTLP_ENDPOINT
    assert built["OTEL_EXPORTER_OTLP_HEADERS"] == f"Authorization=Basic {expected}"
    assert built["OTEL_EXPORTER_OTLP_PROTOCOL"] == "http/protobuf"


def test_registry_client_defaults_to_the_docker_network_name(no_langfuse):
    import agent

    importlib.reload(agent)

    client = agent.AIFactoryRegistry()
    assert client.registry_url == "http://dhg-registry-api:8000"

    manifest = client.get_manifest()
    assert manifest["service"]["id"] == agent.AGENT_ID
    assert manifest["service"]["type"] == "specialized_agent"
    assert manifest["service"]["tracing"] == "disabled"


def test_main_refuses_to_run_without_agent_model(no_langfuse):
    import agent

    importlib.reload(agent)

    assert agent.MODEL is None
    assert agent.main(["hello"]) == 2
