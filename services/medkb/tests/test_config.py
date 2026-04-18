from medkb.config import Settings


def test_settings_defaults():
    s = Settings(
        medkb_db_url="postgresql+asyncpg://u:p@localhost:5433/medkb",
        medkb_redis_url="redis://localhost:6380/0",
    )
    assert s.service_name == "dhg-medkb"
    assert s.api_port == 8015
    assert s.embedding_model == "nomic-embed-text"
    assert s.default_generation_model == "claude-sonnet-4-6"
    assert s.default_grader_model == "ollama:qwen3:14b"
    assert s.default_rewriter_model == "ollama:llama3.1:8b"
    assert s.ollama_url == "http://dhg-ollama:11434"
    assert s.max_total_tokens == 50_000
    assert s.rate_limit_per_minute == 60
    assert s.otel_endpoint == "http://dhg-tempo:4318"
    assert s.langsmith_project == "dhg-medkb"


def test_settings_override_from_env(monkeypatch):
    monkeypatch.setenv("MEDKB_DB_URL", "postgresql+asyncpg://x:y@db:5432/test")
    monkeypatch.setenv("MEDKB_REDIS_URL", "redis://cache:6379/1")
    monkeypatch.setenv("DEFAULT_GENERATION_MODEL", "ollama:llama3.3:70b")
    monkeypatch.setenv("MAX_TOTAL_TOKENS", "100000")
    s = Settings()
    assert s.medkb_db_url == "postgresql+asyncpg://x:y@db:5432/test"
    assert s.default_generation_model == "ollama:llama3.3:70b"
    assert s.max_total_tokens == 100_000
