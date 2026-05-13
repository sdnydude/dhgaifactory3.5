"""Shared embedding utilities for the registry.

Uses Ollama nomic-embed-text (768 dimensions) for all vector embeddings.
"""
import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://dhg-ollama:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
EMBED_DIMENSIONS = 768


async def get_embedding(text: str) -> Optional[list[float]]:
    """Get embedding vector from Ollama. Returns None on failure (fire-and-forget safe)."""
    if not text or not text.strip():
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text[:8000]},
            )
            if resp.status_code == 200:
                return resp.json().get("embedding")
            logger.warning("Embedding request failed: %d", resp.status_code)
    except Exception as e:
        logger.warning("Embedding error: %s", e)
    return None
