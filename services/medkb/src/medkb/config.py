from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "", "case_sensitive": False}

    service_name: str = "dhg-medkb"
    api_port: int = 8015

    medkb_db_url: str = "postgresql+asyncpg://medkb:medkb@dhg-medkb-db:5432/medkb"
    medkb_redis_url: str = "redis://dhg-medkb-cache:6379/0"
    ollama_url: str = "http://dhg-ollama:11434"

    embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768
    default_generation_model: str = "claude-sonnet-4-6"
    default_classifier_model: str = "ollama:llama3.1:8b"
    default_grader_model: str = "ollama:qwen3:14b"
    default_groundedness_model: str = "ollama:qwen3:14b"
    default_rewriter_model: str = "ollama:llama3.1:8b"

    max_total_tokens: int = 50_000
    rate_limit_per_minute: int = 60
    query_cache_ttl_seconds: int = 300
    embedding_cache_ttl_days: int = 7

    otel_endpoint: str = "http://dhg-tempo:4318"
    langsmith_project: str = "dhg-medkb"

    default_k: int = 8
    default_hybrid_weight_dense: float = 0.7
    default_groundedness_threshold: float = 0.8
    default_max_retries: int = 2
