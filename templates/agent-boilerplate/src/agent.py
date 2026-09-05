"""
DHG AI FACTORY - AGENT BOILERPLATE
==================================
Standard template for building DHG agents on Pydantic AI, traced with the
self-hosted Langfuse (ADR-001: LangGraph/LangSmith retired in favour of
Pydantic AI + Langfuse).

INSTRUCTIONS
1. Search and replace "TEMPLATE-AGENT" / "template_agent" with your agent name.
2. Rename src/prompts/template_agent.py and its constants to match, and edit
   the prompt text there -- never inline a prompt literal in this file.
3. Replace the AgentOutput fields with your agent's real output contract.
4. Fill in the capabilities and io_schema of the registry manifest.
5. Add tools with @agent.tool_plain / @agent.tool as the job requires.

SURFACE
This template is a library module plus a CLI (`python src/agent.py "<topic>"`),
which is the surface the previous LangGraph boilerplate had. It serves no HTTP,
so it exposes no /metrics endpoint; if you wrap it in a FastAPI service, add
prometheus_client and a /metrics route in that service, the way
services/vs-engine and services/session-logger do.

ENVIRONMENT
  AGENT_MODEL              LLM-agnostic model string, required for real runs (no default)
  ANTHROPIC_API_KEY        provider credential for the default model
  AI_FACTORY_REGISTRY_URL  registry base URL (default: the docker network name)
  LANGFUSE_PUBLIC_KEY      optional: enables tracing (see tracing.py)
  LANGFUSE_SECRET_KEY      optional: enables tracing (see tracing.py)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from prompts.template_agent import (
    TEMPLATE_AGENT_SYSTEM_PROMPT,
    TEMPLATE_AGENT_TASK_PROMPT,
)
from tracing import configure_tracing

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
LOGGER = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

AGENT_ID = "TEMPLATE-AGENT"
AGENT_NAME = "TEMPLATE-AGENT Name"
AGENT_VERSION = "1.0.0"

# LLM-agnostic model string: `<provider>:<model>`. Swap providers by setting
# AGENT_MODEL -- no code change. See README.md for the Ollama example.
# There is deliberately no default model id (DHG rule: never hardcode model
# IDs in configs). Without AGENT_MODEL the agent still imports and constructs,
# against pydantic_ai's built-in "test" model, and main() refuses to run.
MODEL = os.getenv("AGENT_MODEL")

# Registry reachable by container name on dhgaifactory35_dhg-network. From the
# host, set AI_FACTORY_REGISTRY_URL=http://10.0.0.251:8011.
DEFAULT_REGISTRY_URL = "http://dhg-registry-api:8000"

AGENT_TIMEOUT_SECONDS = float(os.getenv("AGENT_TIMEOUT_SECONDS", "300"))

SYSTEM_PROMPT = TEMPLATE_AGENT_SYSTEM_PROMPT

# Tracing is configured once, at import, and is a no-op without Langfuse keys.
TRACING_ENABLED = configure_tracing(AGENT_ID)


# =============================================================================
# OUTPUT CONTRACT
# =============================================================================


class Finding(BaseModel):
    """One specific, independently checkable observation."""

    statement: str = Field(description="The finding, stated in one sentence.")
    evidence: str = Field(description="What in the source material supports it.")


class AgentOutput(BaseModel):
    """Typed result the model must return. Pydantic AI validates and retries."""

    summary: str = Field(description="Assessment of the topic, for a professional reader.")
    findings: List[Finding] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, description="Calibrated 0-1 confidence.")


# =============================================================================
# AGENT
# =============================================================================

# defer_model_check keeps import cheap and credential-free: the provider is
# resolved on the first run, so the module imports in CI with no API key set.
agent = Agent(
    MODEL or "test",
    output_type=AgentOutput,
    system_prompt=SYSTEM_PROMPT,
    name=AGENT_ID,
    retries=2,
    defer_model_check=True,
)


# =============================================================================
# REGISTRY CLIENT
# =============================================================================


class AIFactoryRegistry:
    """Heartbeat and request tracking against the DHG Registry.

    Every call is best-effort: the registry being down degrades observability,
    never the agent run.
    """

    def __init__(self, registry_url: Optional[str] = None):
        self.registry_url = (
            registry_url or os.getenv("AI_FACTORY_REGISTRY_URL", "").strip() or DEFAULT_REGISTRY_URL
        )
        self.service_id = AGENT_ID
        self.version = AGENT_VERSION

    def get_manifest(self) -> Dict[str, Any]:
        return {
            "service": {
                "id": self.service_id,
                "name": AGENT_NAME,
                "version": self.version,
                "division": "DHG",
                "type": "specialized_agent",
                "model": MODEL,
                "tracing": "langfuse" if TRACING_ENABLED else "disabled",
            },
            "capabilities": {"primary": [], "secondary": []},
            "io_schema": {
                "inputs": {"topic": "str"},
                "outputs": AgentOutput.model_json_schema(),
            },
        }

    async def register(self) -> bool:
        """Heartbeat: announce this agent to the registry. True when accepted."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.registry_url}/api/v1/agents/register",
                    json=self.get_manifest(),
                )
                return response.status_code < 400
        except httpx.HTTPError as exc:
            LOGGER.warning("Registry heartbeat failed: %s", exc)
            return False

    async def log_request(self, user_id: str, params: Dict[str, Any]) -> Optional[str]:
        """Open a request record. Returns its id, or None if unavailable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.registry_url}/api/v1/research/requests",
                    json={
                        "user_id": user_id,
                        "agent_type": self.service_id,
                        "input_params": params,
                    },
                )
                if response.status_code == 201:
                    return response.json().get("request_id")
                return None
        except httpx.HTTPError as exc:
            LOGGER.warning("Registry log_request failed: %s", exc)
            return None

    async def update_request(
        self,
        request_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Close out a request record."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.patch(
                    f"{self.registry_url}/api/v1/research/requests/{request_id}",
                    json={"status": status, "output_summary": result},
                )
                return response.status_code < 400
        except httpx.HTTPError as exc:
            LOGGER.warning("Registry update_request failed: %s", exc)
            return False


registry = AIFactoryRegistry()


# =============================================================================
# RUN
# =============================================================================


async def run_agent(topic: str, user_id: str = "anonymous") -> AgentOutput:
    """Run the agent end to end, with registry tracking around the LLM call."""
    await registry.register()
    request_id = await registry.log_request(user_id, {"topic": topic})

    try:
        result = await asyncio.wait_for(
            agent.run(TEMPLATE_AGENT_TASK_PROMPT.format(topic=topic)),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        if request_id:
            await registry.update_request(
                request_id,
                "failed",
                {"error": f"timed out after {AGENT_TIMEOUT_SECONDS}s"},
            )
        raise

    output = result.output
    if request_id:
        usage = result.usage()
        await registry.update_request(
            request_id,
            "completed",
            {
                "confidence": output.confidence,
                "findings": len(output.findings),
                "input_tokens": getattr(usage, "input_tokens", 0) or 0,
                "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            },
        )
    return output


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point: `python src/agent.py "<topic>"`."""
    parser = argparse.ArgumentParser(description=f"Run {AGENT_NAME}.")
    parser.add_argument("topic", help="The topic to assess.")
    parser.add_argument("--user-id", default="cli", help="Requesting user id.")
    args = parser.parse_args(argv)

    if not MODEL:
        LOGGER.error("AGENT_MODEL is required, e.g. anthropic:<model-id> or ollama:<model>; nothing was run")
        return 2
    LOGGER.info("model=%s tracing=%s", MODEL, "on" if TRACING_ENABLED else "off")
    output = asyncio.run(run_agent(args.topic, args.user_id))
    print(json.dumps(output.model_dump(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
