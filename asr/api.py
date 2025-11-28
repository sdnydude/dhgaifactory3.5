"""
DHG AI Factory - ASR Service
Automatic Speech Recognition using OpenAI Whisper
"""

import os
import time
import uuid
from pathlib import Path
from typing import Optional
import logging

import whisper
import torch
import httpx
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
REGISTRY_API_URL = os.getenv("REGISTRY_API_URL", "http://registry-api:8000")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
UPLOAD_DIR = Path("/tmp/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title="DHG ASR Service",
    description="Automatic Speech Recognition using Whisper",
    version="1.0.0"
)

# Prometheus metrics
asr_requests_total = Counter(
    'asr_requests_total',
    'Total number of ASR requests',
    ['status']
)
asr_latency_seconds = Histogram(
    'asr_latency_seconds',
    'ASR processing latency in seconds',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)
asr_audio_duration_seconds = Histogram(
    'asr_audio_duration_seconds',
    'Duration of audio files processed',
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0]
)
gpu_utilization = Gauge(
    'gpu_utilization',
    'GPU utilization percentage (simulated for now)',
)
model_load_time = Gauge(
    'model_load_time_seconds',
    'Time taken to load the Whisper model'
)

# Global model instance
_model = None
_model_name = None


class TranscriptionResponse(BaseModel):
    """Response model for transcription"""
    transcription_id: str
    text: str
    language: Optional[str] = None
    duration: float
    processing_time: float
    model: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    model_name: Optional[str]
    gpu_available: bool
    registry_api: str


def get_model():
    """Lazy load Whisper model"""
    global _model, _model_name
    
    if _model is None or _model_name != WHISPER_MODEL:
        logger.info(f"Loading Whisper model: {WHISPER_MODEL}")
        start_time = time.time()
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        _model = whisper.load_model(WHISPER_MODEL, device=device)
        _model_name = WHISPER_MODEL
        
        load_time = time.time() - start_time
        model_load_time.set(load_time)
        logger.info(f"Model loaded in {load_time:.2f}s")
    
    return _model


async def store_transcription_in_registry(
    transcription_id: str,
    text: str,
    meta_data: dict
) -> bool:
    """Store transcription result in the Registry API"""
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "transcription_id": transcription_id,
                "text": text,
                "meta_data": meta_data
            }
            
            response = await client.post(
                f"{REGISTRY_API_URL}/api/v1/transcriptions",
                json=payload,
                timeout=10.0
            )
            
            if response.status_code == 201:
                logger.info(f"Transcription {transcription_id} stored in registry")
                return True
            else:
                logger.error(f"Failed to store in registry: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Error storing in registry: {e}")
        return False


@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    model_loaded = _model is not None
    gpu_available = torch.cuda.is_available()
    
    # Check registry connectivity
    registry_status = "unknown"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{REGISTRY_API_URL}/healthz",
                timeout=5.0
            )
            registry_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception as e:
        registry_status = f"unreachable: {str(e)}"
    
    return HealthResponse(
        status="healthy",
        model_loaded=model_loaded,
        model_name=_model_name,
        gpu_available=gpu_available,
        registry_api=registry_status
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    # Update GPU utilization (simulated for now, in production use pynvml)
    if torch.cuda.is_available():
        try:
            # This is a placeholder - in production, use nvidia-smi or pynvml
            gpu_utilization.set(50.0)  # Simulated value
        except Exception as e:
            logger.warning(f"Could not get GPU metrics: {e}")
    
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe audio file using Whisper
    
    Accepts audio files in various formats (mp3, wav, m4a, etc.)
    Returns transcription text and metadata
    """
    transcription_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('audio/'):
            logger.warning(f"Invalid content type: {file.content_type}")
            # Allow it anyway - Whisper can handle many formats
        
        # Save uploaded file temporarily
        file_path = UPLOAD_DIR / f"{transcription_id}_{file.filename}"
        
        logger.info(f"Receiving file: {file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Load model
        model = get_model()
        
        # Transcribe
        logger.info(f"Transcribing {file.filename} with model {WHISPER_MODEL}")
        transcribe_start = time.time()
        
        result = model.transcribe(str(file_path))
        
        transcribe_time = time.time() - transcribe_start
        total_time = time.time() - start_time
        
        # Extract results
        text = result["text"].strip()
        language = result.get("language")
        duration = result.get("duration", 0.0)
        
        logger.info(f"Transcription complete: {len(text)} chars, {duration:.2f}s audio, {transcribe_time:.2f}s processing")
        
        # Store in registry
        meta_data = {
            "filename": file.filename,
            "language": language,
            "audio_duration": duration,
            "processing_time": transcribe_time,
            "model": WHISPER_MODEL,
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }
        
        await store_transcription_in_registry(transcription_id, text, meta_data)
        
        # Update metrics
        asr_requests_total.labels(status="success").inc()
        asr_latency_seconds.observe(total_time)
        asr_audio_duration_seconds.observe(duration)
        
        # Cleanup
        file_path.unlink()
        
        return TranscriptionResponse(
            transcription_id=transcription_id,
            text=text,
            language=language,
            duration=duration,
            processing_time=transcribe_time,
            model=WHISPER_MODEL
        )
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        asr_requests_total.labels(status="error").inc()
        
        # Cleanup on error
        if file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "DHG ASR Service",
        "version": "1.0.0",
        "model": WHISPER_MODEL,
        "gpu_available": torch.cuda.is_available(),
        "endpoints": {
            "health": "/healthz",
            "metrics": "/metrics",
            "transcribe": "/transcribe (POST)"
        }
    }


# Preload model on startup (optional - can be lazy loaded on first request)
@app.on_event("startup")
async def startup_event():
    """Preload model on startup"""
    logger.info("ASR Service starting up...")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"CUDA device: {torch.cuda.get_device_name(0)}")
    
    # Preload model
    try:
        get_model()
        logger.info("Model preloaded successfully")
    except Exception as e:
        logger.error(f"Failed to preload model: {e}")
        # Don't fail startup - model can be lazy loaded


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("ASR Service shutting down...")
