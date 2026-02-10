"""
DHG Audio Analysis Agent — Ollama LLM Client

Shared async HTTP client for Ollama API per Build Spec Section 4.1.
"""

import httpx
import logging
from typing import Optional

from .config import settings

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Exception raised when Ollama API call fails."""
    
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Ollama error ({status_code}): {message}")


async def call_ollama(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 1000,
    temperature: float = 0.3,
) -> str:
    """
    Call Ollama API to generate text.
    
    Args:
        system_prompt: System instruction for the model
        user_prompt: User message/content to process
        model: Model name (defaults to settings.ollama_model)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0-1)
    
    Returns:
        Generated text string
    
    Raises:
        OllamaError: If API call fails after retries
    """
    model = model or settings.ollama_model
    url = f"{settings.ollama_base_url}/api/generate"
    
    payload = {
        "model": model,
        "prompt": user_prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        }
    }
    
    # Retry logic: up to 2 retries with 3-second backoff
    max_retries = 2
    last_error = None
    
    async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
        for attempt in range(max_retries + 1):
            try:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "")
                
                # Server error — retry
                if response.status_code >= 500:
                    last_error = OllamaError(response.status_code, response.text)
                    if attempt < max_retries:
                        logger.warning(f"Ollama 5xx error, retry {attempt + 1}/{max_retries}")
                        import asyncio
                        await asyncio.sleep(3)
                        continue
                
                # Client error — don't retry
                raise OllamaError(response.status_code, response.text)
                
            except httpx.ConnectError as e:
                last_error = OllamaError(0, f"Connection failed: {e}")
                if attempt < max_retries:
                    logger.warning(f"Ollama connection error, retry {attempt + 1}/{max_retries}")
                    import asyncio
                    await asyncio.sleep(3)
                    continue
            
            except httpx.TimeoutException as e:
                last_error = OllamaError(0, f"Timeout: {e}")
                if attempt < max_retries:
                    logger.warning(f"Ollama timeout, retry {attempt + 1}/{max_retries}")
                    import asyncio
                    await asyncio.sleep(3)
                    continue
    
    raise last_error or OllamaError(0, "Unknown error")


async def check_ollama_health() -> bool:
    """
    Check if Ollama is reachable and the required model is available.
    
    Returns:
        True if healthy, False otherwise
    """
    try:
        url = f"{settings.ollama_base_url}/api/tags"
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
                logger.error(f"Ollama health check failed: {response.status_code}")
                return False
            
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            
            # Check if required model is available
            required_model = settings.ollama_model
            if required_model not in models and f"{required_model}:latest" not in models:
                # Check for partial match (model without tag)
                model_base = required_model.split(":")[0]
                if not any(model_base in m for m in models):
                    logger.error(f"Required model '{required_model}' not found. Available: {models}")
                    return False
            
            logger.info(f"Ollama healthy. Available models: {models}")
            return True
            
    except Exception as e:
        logger.error(f"Ollama health check error: {e}")
        return False


async def get_available_models() -> list[str]:
    """Get list of models available in Ollama."""
    try:
        url = f"{settings.ollama_base_url}/api/tags"
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return [m.get("name", "") for m in data.get("models", [])]
    except Exception as e:
        logger.error(f"Failed to get Ollama models: {e}")
    
    return []
