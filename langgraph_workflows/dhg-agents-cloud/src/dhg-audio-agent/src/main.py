"""
DHG Audio Analysis Agent — FastAPI Application

Main application with startup health checks and endpoint stubs.
Per Build Spec Section 5.
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import torch
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from .config import settings
from .models import (
    AnalyzeRequest, JobResponse, JobDetailResponse, HealthResponse,
    ModelsResponse, FullAnalysisResult, TranscriptionResult,
    TranscriptSegment, TopicTag, AnalysisMetadata
)
from .ollama_client import check_ollama_health, get_available_models
from .db import init_db, check_db_health, AsyncSessionLocal, Job, Result
from .graph import run_audio_pipeline

# Logging setup
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Prometheus Metrics
# ============================================================================

jobs_total = Counter(
    "audio_agent_jobs_total",
    "Total jobs submitted",
    ["status"]
)
transcription_duration = Histogram(
    "audio_agent_transcription_duration_seconds",
    "Time spent in Whisper transcription",
    buckets=[1, 5, 10, 30, 60, 120, 300]
)
llm_call_duration = Histogram(
    "audio_agent_llm_call_duration_seconds",
    "Time per Ollama LLM call",
    ["node"]
)
pipeline_duration = Histogram(
    "audio_agent_pipeline_duration_seconds",
    "Total pipeline time"
)
audio_duration = Histogram(
    "audio_agent_audio_duration_seconds",
    "Duration of processed audio files"
)
active_jobs = Gauge(
    "audio_agent_active_jobs",
    "Number of currently processing jobs"
)
errors_total = Counter(
    "audio_agent_errors_total",
    "Total errors",
    ["node", "error_type"]
)


# ============================================================================
# In-memory job storage (replace with DB in production)
# ============================================================================

job_store: dict[str, dict] = {}


# ============================================================================
# Background Processing
# ============================================================================

async def process_job(job_id: str, request: AnalyzeRequest):
    """Run audio pipeline as background task."""
    start_time = time.time()
    active_jobs.inc()
    
    try:
        # Update job status
        job_store[job_id]["status"] = "processing"
        job_store[job_id]["started_at"] = datetime.utcnow()
        
        # Run pipeline
        result = await run_audio_pipeline(
            audio_path=request.audio_path,
            language_id=request.language_id,
            diarize=request.diarize,
            num_speakers=request.num_speakers,
        )
        
        processing_time = time.time() - start_time
        
        if result.get("error"):
            job_store[job_id]["status"] = "failed"
            job_store[job_id]["error"] = result["error"]
            jobs_total.labels(status="failed").inc()
            errors_total.labels(node="pipeline", error_type="execution").inc()
        else:
            job_store[job_id]["status"] = "completed"
            job_store[job_id]["result"] = result
            job_store[job_id]["processing_time"] = processing_time
            jobs_total.labels(status="completed").inc()
            
            # Record metrics
            if result.get("duration_seconds"):
                audio_duration.observe(result["duration_seconds"])
            pipeline_duration.observe(processing_time)
        
        job_store[job_id]["completed_at"] = datetime.utcnow()
        
    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = str(e)
        job_store[job_id]["completed_at"] = datetime.utcnow()
        jobs_total.labels(status="failed").inc()
        errors_total.labels(node="pipeline", error_type="exception").inc()
    
    finally:
        active_jobs.dec()


# ============================================================================
# Application Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Startup
    logger.info("=" * 60)
    logger.info("DHG Audio Analysis Agent starting...")
    logger.info("=" * 60)
    
    # Check Ollama
    ollama_ok = await check_ollama_health()
    if not ollama_ok:
        logger.warning("Ollama not available — LLM features will fail")
    
    # Check GPU
    gpu_available = torch.cuda.is_available()
    if gpu_available:
        logger.info(f"CUDA GPU available: {torch.cuda.get_device_name(0)}")
    else:
        logger.warning("No CUDA GPU — transcription will be slow")
    
    # Initialize database (optional)
    try:
        await init_db()
        db_ok = await check_db_health()
        logger.info(f"Database: {'connected' if db_ok else 'not available'}")
    except Exception as e:
        logger.warning(f"Database not available: {e}")
    
    logger.info("Startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="DHG Audio Analysis Agent",
    description="Self-hosted audio transcription, translation, summarization, and topic tagging",
    version="2.0.0",
    lifespan=lifespan,
)


# ============================================================================
# Endpoints per Build Spec Section 5.1
# ============================================================================

@app.post("/analyze", response_model=JobResponse)
async def analyze_audio(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
):
    """
    Submit audio for analysis.
    
    Kicks off async pipeline and returns job_id for polling.
    """
    job_id = str(uuid.uuid4())
    
    job_store[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "audio_path": request.audio_path,
        "created_at": datetime.utcnow(),
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
    }
    
    background_tasks.add_task(process_job, job_id, request)
    
    logger.info(f"Job {job_id} queued for {request.audio_path}")
    return JobResponse(job_id=job_id, status="queued")


@app.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job_status(job_id: str):
    """
    Get job status and result.
    
    Poll this endpoint to check job progress and retrieve results.
    """
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = job_store[job_id]
    
    response = JobDetailResponse(
        job_id=job_id,
        status=job["status"],
        error=job.get("error"),
        created_at=job.get("created_at"),
        completed_at=job.get("completed_at"),
    )
    
    # If completed, format full result
    if job["status"] == "completed" and job.get("result"):
        result = job["result"]
        
        response.result = FullAnalysisResult(
            transcription=TranscriptionResult(
                text=result.get("transcript_text", ""),
                segments=[
                    TranscriptSegment(**seg) 
                    for seg in result.get("transcript_segments", [])
                ],
                language=result.get("detected_language", "unknown"),
                confidence=result.get("confidence", 0.0),
            ),
            translation=result.get("translation"),
            summary=result.get("summary", ""),
            topics=[
                TopicTag(**t) 
                for t in result.get("topics", [])
            ],
            metadata=AnalysisMetadata(
                duration_seconds=result.get("duration_seconds", 0.0),
                processing_time_seconds=job.get("processing_time", 0.0),
                model_versions={
                    "whisper_model": settings.whisper_model_size,
                    "llm_model": settings.ollama_model,
                    "diarization_model": "pyannote/speaker-diarization-3.1",
                }
            )
        )
    
    return response


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns status of all dependencies: Whisper, Ollama, Postgres, GPU.
    """
    ollama_ok = await check_ollama_health()
    db_ok = await check_db_health()
    gpu_available = torch.cuda.is_available()
    
    # Check Whisper (lazy load means we just check if import works)
    try:
        import faster_whisper
        whisper_ok = True
    except ImportError:
        whisper_ok = False
    
    overall = "healthy" if (ollama_ok and whisper_ok) else "degraded"
    
    return HealthResponse(
        status=overall,
        whisper=whisper_ok,
        ollama=ollama_ok,
        postgres=db_ok,
        gpu_available=gpu_available,
    )


@app.post("/analyze/sync", response_model=FullAnalysisResult)
async def analyze_audio_sync(request: AnalyzeRequest):
    """
    Synchronous analysis endpoint.
    
    Blocks until complete. Use for short audio only (< 10 minutes).
    Timeout: 300 seconds.
    """
    start_time = time.time()
    
    result = await asyncio.wait_for(
        run_audio_pipeline(
            audio_path=request.audio_path,
            language_id=request.language_id,
            diarize=request.diarize,
            num_speakers=request.num_speakers,
        ),
        timeout=300,
    )
    
    processing_time = time.time() - start_time
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return FullAnalysisResult(
        transcription=TranscriptionResult(
            text=result.get("transcript_text", ""),
            segments=[
                TranscriptSegment(**seg) 
                for seg in result.get("transcript_segments", [])
            ],
            language=result.get("detected_language", "unknown"),
            confidence=result.get("confidence", 0.0),
        ),
        translation=result.get("translation"),
        summary=result.get("summary", ""),
        topics=[
            TopicTag(**t) 
            for t in result.get("topics", [])
        ],
        metadata=AnalysisMetadata(
            duration_seconds=result.get("duration_seconds", 0.0),
            processing_time_seconds=processing_time,
            model_versions={
                "whisper_model": settings.whisper_model_size,
                "llm_model": settings.ollama_model,
                "diarization_model": "pyannote/speaker-diarization-3.1",
            }
        )
    )


@app.get("/models", response_model=ModelsResponse)
async def get_models():
    """Get available models."""
    ollama_models = await get_available_models()
    
    return ModelsResponse(
        whisper_model=settings.whisper_model_size,
        llm_model=settings.ollama_model,
        diarization_model="pyannote/speaker-diarization-3.1",
        ollama_models=ollama_models,
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
