# services/vs-engine/llm_router.py
"""LLM connection management for the VS Engine.

Routes requests to Ollama (local), Anthropic (cloud), or OpenAI-compatible
endpoints based on model name patterns.
"""

import json
import logging
import os
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OLLAMA_PATTERNS = re.compile(r"^(qwen|llama|nomic|mistral|phi|gemma|codellama)")
ANTHROPIC_PATTERNS = re.compile(r"^claude-")
OPENAI_PATTERNS = re.compile(r"^(gpt-|o1-|o3-)")


def detect_provider(model: str) -> str:
    if OLLAMA_PATTERNS.match(model):
        return "ollama"
    if ANTHROPIC_PATTERNS.match(model):
        return "anthropic"
    if OPENAI_PATTERNS.match(model):
        return "openai"
    return "ollama"


async def generate_with_ollama(
    prompt: str, model: str, ollama_url: str,
    temperature: float = 1.0, timeout: float = 120.0,
) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False,
                  "options": {"temperature": temperature}},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json().get("response", "")


async def generate_with_anthropic(
    prompt: str, model: str, system_prompt: Optional[str] = None,
    temperature: float = 1.0, timeout: float = 120.0,
) -> str:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed")

    from config import get_anthropic_api_key
    api_key = get_anthropic_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")

    client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout)
    messages = [{"role": "user", "content": prompt}]
    response = await client.messages.create(
        model=model, max_tokens=4096, temperature=temperature,
        system=system_prompt or "", messages=messages,
    )
    return response.content[0].text


async def generate_with_openai(
    prompt: str, model: str, system_prompt: Optional[str] = None,
    temperature: float = 1.0, timeout: float = 120.0,
) -> str:
    base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": temperature},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def generate(
    prompt: str, model: str, ollama_url: str,
    system_prompt: Optional[str] = None,
    temperature: float = 1.0, timeout: float = 120.0,
) -> str:
    provider = detect_provider(model)
    logger.info(f"Routing to {provider} for model {model}")

    if provider == "ollama":
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        return await generate_with_ollama(full_prompt, model, ollama_url, temperature, timeout)
    if provider == "anthropic":
        return await generate_with_anthropic(prompt, model, system_prompt, temperature, timeout)
    return await generate_with_openai(prompt, model, system_prompt, temperature, timeout)


async def check_ollama_health(ollama_url: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{ollama_url}/api/tags", timeout=5.0)
            return "connected" if resp.status_code == 200 else f"error: {resp.status_code}"
    except Exception as e:
        return f"error: {str(e)}"


def check_anthropic_configured() -> str:
    return "configured" if os.getenv("ANTHROPIC_API_KEY") else "not_configured"


async def embed_with_ollama(
    text: str, model: str, ollama_url: str, timeout: float = 30.0,
) -> list[float]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ollama_url}/api/embed",
            json={"model": model, "input": text[:8000]},
            timeout=timeout,
        )
        response.raise_for_status()
        embeddings = response.json().get("embeddings")
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
        raise ValueError("No embeddings returned from Ollama")
