"""
DHG Audio Analysis Agent — Pydantic Models

Request/response models for API endpoints per Build Spec Section 5.3.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


# ============================================================================
# Request Models
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze."""
    audio_path: str = Field(..., description="Path to audio file on local filesystem")
    language_id: Optional[str] = Field(None, description="ISO 639-1 language code (auto-detect if omitted)")
    diarize: bool = Field(True, description="Whether to perform speaker diarization")
    num_speakers: Optional[int] = Field(None, description="Expected number of speakers (hint)")


# ============================================================================
# Response Models — Nested Components
# ============================================================================

class TranscriptSegment(BaseModel):
    """A single segment of the transcript with timing and speaker info."""
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Segment text")
    speaker: Optional[str] = Field(None, description="Speaker label if diarized")


class TranscriptionResult(BaseModel):
    """Full transcription output."""
    text: str = Field(..., description="Full transcript as plain text")
    segments: list[TranscriptSegment] = Field(default_factory=list, description="Timed segments")
    language: str = Field(..., description="Detected/confirmed language code")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")


class TopicTag(BaseModel):
    """A topic extracted from the audio content."""
    label: str = Field(..., description="Topic label (2-5 words)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class AnalysisMetadata(BaseModel):
    """Processing metadata."""
    duration_seconds: float = Field(..., description="Audio duration")
    processing_time_seconds: float = Field(..., description="Total pipeline time")
    model_versions: dict[str, str] = Field(
        default_factory=dict,
        description="Model versions used (whisper_model, llm_model, diarization_model)"
    )


# ============================================================================
# Response Models — Full Results
# ============================================================================

class FullAnalysisResult(BaseModel):
    """Complete analysis output returned after successful processing."""
    transcription: TranscriptionResult
    translation: Optional[str] = Field(None, description="English translation (null if source is EN)")
    summary: str = Field(..., description="Executive summary (3-5 sentences)")
    topics: list[TopicTag] = Field(default_factory=list, description="Extracted topics (3-8)")
    metadata: AnalysisMetadata


class JobResponse(BaseModel):
    """Response for async job submission."""
    job_id: str = Field(..., description="UUID for the job")
    status: Literal["queued", "processing", "completed", "failed"] = Field(..., description="Job status")


class JobDetailResponse(BaseModel):
    """Detailed job status with optional result."""
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    result: Optional[FullAnalysisResult] = None
    error: Optional[str] = None
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Overall status")
    whisper: bool = Field(..., description="Whisper model loaded")
    ollama: bool = Field(..., description="Ollama reachable")
    postgres: bool = Field(..., description="PostgreSQL connected")
    gpu_available: bool = Field(..., description="CUDA GPU available")


class ModelsResponse(BaseModel):
    """Available models response."""
    whisper_model: str
    llm_model: str
    diarization_model: str
    ollama_models: list[str] = Field(default_factory=list)
