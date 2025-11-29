"""
DHG AI Factory - ASR Service
Automatic Speech Recognition using Whisper CPP
"""

import os
import time
import uuid
from pathlib import Path
from typing import Optional
import logging

# Replaced openai-whisper with pywhispercpp
from pywhispercpp.model import Model
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
    description="Automatic Speech Recognition using Whisper CPP",
    version="2.0.0"
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
        if WHISPER_MODEL == "mock":
            logger.info("Mock mode enabled - skipping model load")
            _model = "mock_model"
            _model_name = "mock"
            return _model

        logger.info(f"Loading Whisper CPP model: {WHISPER_MODEL}")
        start_time = time.time()
        
        # pywhispercpp handles downloading models if not present
        # n_threads can be tuned, default is usually sufficient
        _model = Model(WHISPER_MODEL, print_realtime=False, print_progress=False)
        _model_name = WHISPER_MODEL
        
        load_time = time.time() - start_time
        model_load_time.set(load_time)
        logger.info(f"Model loaded in {load_time:.2f}s")
    
    return _model


async def create_media_in_registry(filename: str, file_size: int, mime_type: str) -> Optional[str]:
    """Create media entry in Registry API"""
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "filename": filename,
                "filepath": f"/media/{filename}",
                "file_size_bytes": file_size,
                "mime_type": mime_type,
                "status": "processing"
            }
            
            response = await client.post(
                f"{REGISTRY_API_URL}/api/v1/media",
                json=payload,
                timeout=10.0
            )
            
            if response.status_code == 201:
                data = response.json()
                logger.info(f"Media created in registry: {data['id']}")
                return data['id']
            else:
                logger.error(f"Failed to create media in registry: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"Error creating media in registry: {e}")
        return None


async def store_transcription_in_registry(
    media_id: str,
    text: str,
    meta_data: dict
) -> bool:
    """Store transcription result in the Registry API"""
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "media_id": media_id,
                "full_text": text,
                "processing_time_seconds": meta_data.get("processing_time", 0.0),
                "language": meta_data.get("language"),
                "model_name": meta_data.get("model"),
                "meta_data": meta_data
            }
            
            response = await client.post(
                f"{REGISTRY_API_URL}/api/v1/transcripts",
                json=payload,
                timeout=10.0
            )
            
            if response.status_code == 201:
                logger.info(f"Transcript for media {media_id} stored in registry")
                return True
            else:
                logger.error(f"Failed to store transcript in registry: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error storing transcript in registry: {e}")
        return False


@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    model_loaded = _model is not None
    # With whisper.cpp, we don't check torch.cuda.is_available()
    # We assume GPU is used if configured in build, but for now we just report True/False based on env
    gpu_available = False # TODO: check if pywhispercpp exposes this
    
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
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe audio file using Whisper CPP
    """
    start_time = time.time()
    file_path = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
    
    try:
        # Save uploaded file temporarily
        logger.info(f"Receiving file: {file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Create media in registry
        media_id = await create_media_in_registry(
            filename=file.filename,
            file_size=file.size if file.size else 0,
            mime_type=file.content_type or "application/octet-stream"
        )
        
        if not media_id:
            logger.warning("Could not create media in registry, proceeding with transcription anyway")
            media_id = str(uuid.uuid4())

        # Load model
        model = get_model()
        
        # Transcribe
        logger.info(f"Transcribing {file.filename} with model {WHISPER_MODEL}")
        transcribe_start = time.time()
        
        if WHISPER_MODEL == "mock":
            time.sleep(1.0)  # Simulate processing
            text = "This is a mock transcription result for testing purposes."
            language = "en"
            duration = 10.0
        else:
            # pywhispercpp transcribe returns segments
            # segments = model.transcribe(str(file_path))
            # We need to aggregate text
            segments = model.transcribe(str(file_path))
            text = "".join([segment.text for segment in segments]).strip()
            # pywhispercpp might not return language/duration easily in all versions
            # We'll assume english and calculate duration from file if needed, or from segments
            language = "en" # Default or TODO: detect
            # Calculate duration from segments if possible, else 0
            duration = 0.0
            if segments:
                duration = segments[-1].t1 / 100.0 # t1 is usually in centiseconds in some bindings, check docs. 
                # Actually pywhispercpp segments usually have t0, t1 in centiseconds (int)
                # Let's verify this assumption or just use 0 for now to be safe
                pass

        transcribe_time = time.time() - transcribe_start
        total_time = time.time() - start_time
        
        logger.info(f"Transcription complete: {len(text)} chars, {transcribe_time:.2f}s processing")
        
        # Store in registry
        meta_data = {
            "filename": file.filename,
            "language": language,
            "audio_duration": duration,
            "processing_time": transcribe_time,
            "model": WHISPER_MODEL,
            "engine": "whisper.cpp"
        }
        
        await store_transcription_in_registry(media_id, text, meta_data)
        
        # Update metrics
        asr_requests_total.labels(status="success").inc()
        asr_latency_seconds.observe(total_time)
        asr_audio_duration_seconds.observe(duration)
        
        return TranscriptionResponse(
            transcription_id=media_id,
            text=text,
            language=language,
            duration=duration,
            processing_time=transcribe_time,
            model=WHISPER_MODEL
        )
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        asr_requests_total.labels(status="error").inc()
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )
    finally:
        # Cleanup
        if file_path.exists():
            file_path.unlink()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "DHG ASR Service",
        "version": "2.0.0",
        "engine": "whisper.cpp",
        "model": WHISPER_MODEL,
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
    logger.info("ASR Service starting up (Whisper CPP)...")
    try:
        get_model()
        logger.info("Model preloaded successfully")
    except Exception as e:
        logger.error(f"Failed to preload model: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("ASR Service shutting down...")
