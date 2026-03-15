# langgraph_workflows/dhg-agents-cloud/src/vs_client.py
"""VS Engine client for LangGraph agents.

Provides async functions to call the dhg-vs-engine service for divergent
generation via Verbalized Sampling. Gracefully degrades when the VS engine
is unavailable — agents fall back to standard single-output generation.

Usage in any agent node:
    from vs_client import vs_generate, vs_select, vs_is_available

    result = await vs_generate(prompt="...", phase="gap_analysis", k=5)
    if result:
        selected = await vs_select(result["distribution_id"], strategy="sample")
"""

import os
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

VS_ENGINE_URL = os.environ.get("VS_ENGINE_URL", "http://dhg-vs-engine:8000")
VS_TIMEOUT = float(os.environ.get("VS_TIMEOUT", "120.0"))  # Match server-side timeout (spec Section 8.4)


async def vs_is_available() -> bool:
    """Check if the VS engine is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{VS_ENGINE_URL}/health")
            return resp.status_code == 200
    except Exception:
        return False


async def vs_generate(
    prompt: str,
    phase: str = "custom",
    k: Optional[int] = None,
    tau: Optional[float] = None,
    min_probability: Optional[float] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    confidence_framing: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Call /vs/generate to produce a distribution of diverse outputs.

    Returns None if the VS engine is unavailable (graceful degradation).
    The calling agent should fall back to standard LLM generation.
    """
    body: Dict[str, Any] = {"prompt": prompt, "phase": phase}
    if k is not None:
        body["k"] = k
    if tau is not None:
        body["tau"] = tau
    if min_probability is not None:
        body["min_probability"] = min_probability
    if model is not None:
        body["model"] = model
    if system_prompt is not None:
        body["system_prompt"] = system_prompt
    if confidence_framing is not None:
        body["confidence_framing"] = confidence_framing

    try:
        async with httpx.AsyncClient(timeout=VS_TIMEOUT) as client:
            resp = await client.post(f"{VS_ENGINE_URL}/vs/generate", json=body)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        logger.warning("VS engine unavailable at %s — falling back to standard generation", VS_ENGINE_URL)
        return None
    except httpx.TimeoutException:
        logger.warning("VS engine timed out — falling back to standard generation")
        return None
    except Exception as e:
        logger.error("VS engine error: %s — falling back to standard generation", e)
        return None


async def vs_select(
    distribution_id: str,
    strategy: str = "sample",
    human_selection_index: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Call /vs/select to pick one item from a cached distribution.

    Returns None if the VS engine is unavailable.
    """
    body: Dict[str, Any] = {
        "distribution_id": distribution_id,
        "strategy": strategy,
    }
    if human_selection_index is not None:
        body["human_selection_index"] = human_selection_index

    try:
        async with httpx.AsyncClient(timeout=VS_TIMEOUT) as client:
            resp = await client.post(f"{VS_ENGINE_URL}/vs/select", json=body)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("VS select failed: %s", e)
        return None
