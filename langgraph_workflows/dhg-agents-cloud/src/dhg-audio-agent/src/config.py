"""
DHG Audio Analysis Agent Configuration

Pydantic BaseSettings for all environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Ollama LLM Configuration
    ollama_base_url: str = Field(
        default="http://ollama:11434",
        description="Ollama API base URL"
    )
    ollama_model: str = Field(
        default="llama3.1:8b-instruct-q4_K_M",
        description="Ollama model for translation/summarization/tagging"
    )
    ollama_timeout: int = Field(
        default=120,
        description="Timeout for Ollama API calls in seconds"
    )
    
    # Whisper Configuration
    whisper_model_size: str = Field(
        default="large-v3",
        description="Whisper model size (tiny, base, small, medium, large-v3)"
    )
    whisper_device: str = Field(
        default="cuda",
        description="Device for Whisper inference (cuda or cpu)"
    )
    whisper_compute_type: str = Field(
        default="int8",
        description="Compute type for Whisper (int8 for GPU, float32 for CPU)"
    )
    
    # HuggingFace Configuration (for pyannote)
    hf_token: Optional[str] = Field(
        default=None,
        description="HuggingFace token for pyannote model download (free)"
    )
    
    # PostgreSQL Configuration
    postgres_url: str = Field(
        default="postgresql+asyncpg://user:pass@postgres:5432/audio_agent",
        description="PostgreSQL connection URL"
    )
    
    # File Storage
    audio_upload_dir: str = Field(
        default="/data/audio",
        description="Directory for audio file storage"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars like POSTGRES_USER


# Singleton instance
settings = Settings()
