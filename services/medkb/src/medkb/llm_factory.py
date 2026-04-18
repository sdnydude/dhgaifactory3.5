from __future__ import annotations

import logging
from functools import lru_cache

from langchain.chat_models import init_chat_model

logger = logging.getLogger(__name__)


@lru_cache(maxsize=16)
def get_llm(model_spec: str, *, temperature: float = 0.0):
    logger.info("Initializing LLM: %s", model_spec)
    return init_chat_model(model_spec, temperature=temperature)
