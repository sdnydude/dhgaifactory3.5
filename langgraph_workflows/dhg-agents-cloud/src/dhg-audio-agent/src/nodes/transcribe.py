"""
Node 2: transcribe

Transcribe audio using faster-whisper with optional pyannote speaker diarization.
Per Build Spec Section 3.3 Node 2.
"""

import logging
import numpy as np
from typing import Optional

from ..state import AudioAgentState
from ..config import settings

logger = logging.getLogger(__name__)

# Lazy load models to avoid startup delay
_whisper_model = None
_diarization_pipeline = None


def get_whisper_model():
    """Lazy load Whisper model."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        logger.info(f"Loading Whisper model: {settings.whisper_model_size}")
        _whisper_model = WhisperModel(
            settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        logger.info("Whisper model loaded")
    return _whisper_model


def get_diarization_pipeline():
    """Lazy load pyannote diarization pipeline."""
    global _diarization_pipeline
    if _diarization_pipeline is None:
        if not settings.hf_token:
            logger.warning("HF_TOKEN not set — diarization disabled")
            return None
        
        from pyannote.audio import Pipeline
        logger.info("Loading pyannote diarization pipeline")
        _diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=settings.hf_token,
        )
        # Move to GPU if available
        import torch
        if torch.cuda.is_available():
            _diarization_pipeline.to(torch.device("cuda"))
        logger.info("Diarization pipeline loaded")
    return _diarization_pipeline


def assign_speakers_to_segments(
    segments: list[dict],
    diarization_result,
) -> list[dict]:
    """
    Assign speaker labels to transcript segments based on diarization.
    
    Uses overlapping timestamps to match speakers to segments.
    """
    if diarization_result is None:
        return segments
    
    # Build speaker timeline
    speaker_timeline = []
    for turn, _, speaker in diarization_result.itertracks(yield_label=True):
        speaker_timeline.append({
            "start": turn.start,
            "end": turn.end,
            "speaker": speaker,
        })
    
    # Assign speakers to segments
    for segment in segments:
        seg_start = segment["start"]
        seg_end = segment["end"]
        seg_mid = (seg_start + seg_end) / 2
        
        # Find speaker at segment midpoint
        assigned_speaker = None
        for sp in speaker_timeline:
            if sp["start"] <= seg_mid <= sp["end"]:
                assigned_speaker = sp["speaker"]
                break
        
        segment["speaker"] = assigned_speaker
    
    return segments


async def transcribe(state: AudioAgentState) -> dict:
    """
    Transcribe audio file using faster-whisper.
    
    Optionally performs speaker diarization with pyannote if enabled.
    
    Returns:
        dict with transcript_text, transcript_segments, detected_language,
        confidence, duration_seconds
    """
    # Skip if error already set
    if state.get("error"):
        return {}
    
    audio_path = state["audio_path"]
    language_id = state.get("language_id")
    diarize = state.get("diarize", True)
    num_speakers = state.get("num_speakers")
    
    try:
        model = get_whisper_model()
        
        # Transcribe with Whisper
        logger.info(f"Transcribing: {audio_path}")
        segments_gen, info = model.transcribe(
            audio_path,
            language=language_id,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
        )
        
        # Collect segments
        segments = []
        confidences = []
        
        for seg in segments_gen:
            segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "speaker": None,  # Will be set by diarization
            })
            # Convert log prob to confidence
            if seg.avg_logprob:
                conf = np.exp(seg.avg_logprob)
                confidences.append(min(1.0, max(0.0, conf)))
        
        # Calculate overall confidence
        avg_confidence = float(np.mean(confidences)) if confidences else 0.5
        
        # Build full transcript
        transcript_text = " ".join(seg["text"] for seg in segments)
        
        # Perform diarization if requested
        if diarize:
            try:
                pipeline = get_diarization_pipeline()
                if pipeline:
                    logger.info("Running speaker diarization...")
                    diarization_result = pipeline(
                        audio_path,
                        num_speakers=num_speakers,
                    )
                    segments = assign_speakers_to_segments(segments, diarization_result)
                    logger.info("Diarization complete")
            except Exception as e:
                logger.warning(f"Diarization failed (continuing without): {e}")
        
        logger.info(f"Transcription complete: {len(segments)} segments, "
                   f"{info.duration:.1f}s, language={info.language}")
        
        return {
            "transcript_text": transcript_text,
            "transcript_segments": segments,
            "detected_language": info.language,
            "confidence": avg_confidence,
            "duration_seconds": info.duration,
        }
        
    except FileNotFoundError as e:
        logger.error(f"Audio file not found: {e}")
        return {"error": f"Audio file not found: {e}"}
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return {"error": f"Transcription failed: {e}"}
