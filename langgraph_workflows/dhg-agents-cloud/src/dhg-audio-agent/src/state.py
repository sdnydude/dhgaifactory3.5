"""
DHG Audio Analysis Agent — LangGraph State Schema

TypedDict state for the processing pipeline per Build Spec Section 3.2.
"""

from typing import TypedDict, Optional


class AudioAgentState(TypedDict, total=False):
    """
    State object shared across all pipeline nodes.
    
    Inputs (set by caller):
        audio_path: Absolute path to audio file
        language_id: ISO 639-1 code (None = auto-detect)
        diarize: Whether to identify speakers
        num_speakers: Hint for diarization
    
    Transcription outputs (set by transcribe node):
        transcript_text: Full transcript as plain text
        transcript_segments: List of {start, end, text, speaker}
        detected_language: Language Whisper detected
        confidence: Overall confidence 0-1
        duration_seconds: Audio duration
    
    LLM outputs (set by translate/summarize/tag nodes):
        translation: English translation (None if source is EN)
        summary: Executive summary
        topics: List of {label, confidence}
    
    Control:
        error: Error message (if set, pipeline stops)
    """
    
    # Inputs
    audio_path: str
    language_id: Optional[str]
    diarize: bool
    num_speakers: Optional[int]
    
    # Transcription outputs
    transcript_text: str
    transcript_segments: list[dict]
    detected_language: str
    confidence: float
    duration_seconds: float
    
    # LLM outputs
    translation: Optional[str]
    summary: str
    topics: list[dict]
    
    # Control
    error: Optional[str]
