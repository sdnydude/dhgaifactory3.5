from __future__ import annotations

import logging
from functools import lru_cache

from langchain.chat_models import init_chat_model

from medkb.config import Settings

logger = logging.getLogger(__name__)

_settings = Settings()


@lru_cache(maxsize=16)
def get_llm(model_spec: str, *, temperature: float = 0.0):
    logger.info("Initializing LLM: %s", model_spec)
    kwargs: dict = {"temperature": temperature}
    if model_spec.startswith("ollama:"):
        kwargs["base_url"] = _settings.ollama_url
    return init_chat_model(model_spec, **kwargs)
