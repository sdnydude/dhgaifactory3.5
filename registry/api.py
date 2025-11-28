"""
DHG Registry API Service
FastAPI service with /healthz, /metrics, and CRUD operations
All data stored in PostgreSQL DHG Registry
"""
import os
import time
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session, sessionmaker
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from models import Base, Media, Transcript, Segment, Event


# ============================================================================
# Prometheus Metrics
# ============================================================================
registry_write_latency = Histogram(
    'registry_write_latency_ms',
    'Database write latency in milliseconds',
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
)

registry_read_latency = Histogram(
    'registry_read_latency_ms',
    'Database read latency in milliseconds',
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000]
)

registry_write_operations = Counter(
    'registry_write_operations_total',
    'Total number of write operations',
    ['operation']
)

registry_read_operations = Counter(
    'registry_read_operations_total',
    'Total number of read operations',
    ['operation']
)

registry_errors = Counter(
    'registry_errors_total',
    'Total number of registry errors',
    ['error_type']
)

registry_db_errors = Counter(
    'registry_db_errors_total',
    'Total number of database connection errors'
)

db_connections = Gauge(
    'registry_db_connections',
    'Number of active database connections'
)


# ============================================================================
# Database Setup
# ============================================================================
def get_database_url() -> str:
    """Get database URL with password from secret file"""
    db_password_file = os.getenv("DB_PASSWORD_FILE", "/run/secrets/db_password")
    try:
        with open(db_password_file, 'r') as f:
            password = f.read().strip()
    except FileNotFoundError:
        # Fallback for local development
        password = os.getenv("DB_PASSWORD", "dhg_password")
    
    db_url = os.getenv("DATABASE_URL", "postgresql://dhg_user@registry-db:5432/dhg_registry")
    # Insert password into URL
    if "@" in db_url:
        protocol, rest = db_url.split("://", 1)
        user_host = rest.split("@", 1)
        if len(user_host) == 2:
            user, host = user_host
            db_url = f"{protocol}://{user}:{password}@{host}"
    
    return db_url


DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    db_connections.inc()
    try:
        yield db
    except Exception as e:
        registry_db_errors.inc()
        raise
    finally:
        db_connections.dec()
        db.close()


# ============================================================================
# Pydantic Models (DTOs)
# ============================================================================
class MediaCreate(BaseModel):
    filename: str
    filepath: str
    file_size_bytes: int
    mime_type: str
    duration_seconds: Optional[float] = None
    meta_data: Optional[dict] = None


class MediaResponse(BaseModel):
    id: uuid.UUID
    filename: str
    filepath: str
    file_size_bytes: int
    mime_type: str
    duration_seconds: Optional[float]
    status: str
    meta_data: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TranscriptCreate(BaseModel):
    media_id: uuid.UUID
    full_text: str
    language: Optional[str] = None
    confidence_score: Optional[float] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    processing_time_seconds: float
    meta_data: Optional[dict] = None


class TranscriptResponse(BaseModel):
    id: uuid.UUID
    media_id: uuid.UUID
    full_text: str
    language: Optional[str]
    confidence_score: Optional[float]
    model_name: Optional[str]
    model_version: Optional[str]
    processing_time_seconds: float
    meta_data: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class SegmentCreate(BaseModel):
    transcript_id: uuid.UUID
    segment_index: int
    start_time_seconds: float
    end_time_seconds: float
    text: str
    confidence_score: Optional[float] = None
    speaker_id: Optional[str] = None
    meta_data: Optional[dict] = None


class SegmentResponse(BaseModel):
    id: uuid.UUID
    transcript_id: uuid.UUID
    segment_index: int
    start_time_seconds: float
    end_time_seconds: float
    text: str
    confidence_score: Optional[float]
    speaker_id: Optional[str]
    meta_data: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    event_type: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    user_id: Optional[str] = None
    description: Optional[str] = None
    meta_data: Optional[dict] = None


class EventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    entity_type: str
    entity_id: Optional[uuid.UUID]
    user_id: Optional[str]
    description: Optional[str]
    meta_data: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# FastAPI Application
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    # Startup: Ensure database is accessible
    try:
        with engine.connect() as conn:
            conn.execute(select(1))
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        registry_db_errors.inc()
    
    yield
    
    # Shutdown
    print("Shutting down Registry API...")


app = FastAPI(
    title="DHG Registry API",
    description="Central data registry for DHG AI Factory",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# Health & Metrics Endpoints
# ============================================================================
@app.get("/healthz", response_class=PlainTextResponse)
async def health():
    """Health check endpoint"""
    try:
        with engine.connect() as conn:
            conn.execute(select(1))
        return "OK"
    except Exception as e:
        registry_db_errors.inc()
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()


# ============================================================================
# Media Endpoints
# ============================================================================
@app.post("/api/v1/media", response_model=MediaResponse, status_code=status.HTTP_201_CREATED)
async def create_media(media: MediaCreate, db: Session = Depends(get_db)):
    """Create a new media entry"""
    start_time = time.time()
    try:
        db_media = Media(**media.model_dump())
        db.add(db_media)
        db.commit()
        db.refresh(db_media)
        
        # Log event
        db_event = Event(
            event_type="create",
            entity_type="media",
            entity_id=db_media.id,
            description=f"Created media: {media.filename}"
        )
        db.add(db_event)
        db.commit()
        
        registry_write_operations.labels(operation='create_media').inc()
        registry_write_latency.observe((time.time() - start_time) * 1000)
        
        return db_media
    except Exception as e:
        registry_errors.labels(error_type='create_media_failed').inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/media", response_model=List[MediaResponse])
async def list_media(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all media entries"""
    start_time = time.time()
    try:
        media = db.query(Media).offset(skip).limit(limit).all()
        registry_read_operations.labels(operation='list_media').inc()
        registry_read_latency.observe((time.time() - start_time) * 1000)
        return media
    except Exception as e:
        registry_errors.labels(error_type='list_media_failed').inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/media/{media_id}", response_model=MediaResponse)
async def get_media(media_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a specific media entry"""
    start_time = time.time()
    try:
        media = db.query(Media).filter(Media.id == media_id).first()
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")
        registry_read_operations.labels(operation='get_media').inc()
        registry_read_latency.observe((time.time() - start_time) * 1000)
        return media
    except HTTPException:
        raise
    except Exception as e:
        registry_errors.labels(error_type='get_media_failed').inc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Transcript Endpoints
# ============================================================================
@app.post("/api/v1/transcripts", response_model=TranscriptResponse, status_code=status.HTTP_201_CREATED)
async def create_transcript(transcript: TranscriptCreate, db: Session = Depends(get_db)):
    """Create a new transcript"""
    start_time = time.time()
    try:
        # Verify media exists
        media = db.query(Media).filter(Media.id == transcript.media_id).first()
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")
        
        db_transcript = Transcript(**transcript.model_dump())
        db.add(db_transcript)
        
        # Update media status
        media.status = "completed"
        
        db.commit()
        db.refresh(db_transcript)
        
        # Log event
        db_event = Event(
            event_type="transcribe",
            entity_type="transcript",
            entity_id=db_transcript.id,
            description=f"Transcribed media {transcript.media_id}"
        )
        db.add(db_event)
        db.commit()
        
        registry_write_operations.labels(operation='create_transcript').inc()
        registry_write_latency.observe((time.time() - start_time) * 1000)
        
        return db_transcript
    except HTTPException:
        raise
    except Exception as e:
        registry_errors.labels(error_type='create_transcript_failed').inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/transcripts", response_model=List[TranscriptResponse])
async def list_transcripts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all transcripts"""
    start_time = time.time()
    try:
        transcripts = db.query(Transcript).offset(skip).limit(limit).all()
        registry_read_operations.labels(operation='list_transcripts').inc()
        registry_read_latency.observe((time.time() - start_time) * 1000)
        return transcripts
    except Exception as e:
        registry_errors.labels(error_type='list_transcripts_failed').inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/transcripts/media/{media_id}", response_model=List[TranscriptResponse])
async def get_transcripts_by_media(media_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get all transcripts for a specific media"""
    start_time = time.time()
    try:
        transcripts = db.query(Transcript).filter(Transcript.media_id == media_id).all()
        registry_read_operations.labels(operation='get_transcripts_by_media').inc()
        registry_read_latency.observe((time.time() - start_time) * 1000)
        return transcripts
    except Exception as e:
        registry_errors.labels(error_type='get_transcripts_by_media_failed').inc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Segment Endpoints
# ============================================================================
@app.post("/api/v1/segments", response_model=SegmentResponse, status_code=status.HTTP_201_CREATED)
async def create_segment(segment: SegmentCreate, db: Session = Depends(get_db)):
    """Create a new segment"""
    start_time = time.time()
    try:
        db_segment = Segment(**segment.model_dump())
        db.add(db_segment)
        db.commit()
        db.refresh(db_segment)
        
        registry_write_operations.labels(operation='create_segment').inc()
        registry_write_latency.observe((time.time() - start_time) * 1000)
        
        return db_segment
    except Exception as e:
        registry_errors.labels(error_type='create_segment_failed').inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/segments/transcript/{transcript_id}", response_model=List[SegmentResponse])
async def get_segments_by_transcript(transcript_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get all segments for a specific transcript"""
    start_time = time.time()
    try:
        segments = db.query(Segment).filter(Segment.transcript_id == transcript_id).order_by(Segment.segment_index).all()
        registry_read_operations.labels(operation='get_segments_by_transcript').inc()
        registry_read_latency.observe((time.time() - start_time) * 1000)
        return segments
    except Exception as e:
        registry_errors.labels(error_type='get_segments_by_transcript_failed').inc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Event Endpoints
# ============================================================================
@app.post("/api/v1/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(event: EventCreate, db: Session = Depends(get_db)):
    """Create a new event"""
    start_time = time.time()
    try:
        db_event = Event(**event.model_dump())
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        
        registry_write_operations.labels(operation='create_event').inc()
        registry_write_latency.observe((time.time() - start_time) * 1000)
        
        return db_event
    except Exception as e:
        registry_errors.labels(error_type='create_event_failed').inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/events", response_model=List[EventResponse])
async def list_events(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all events"""
    start_time = time.time()
    try:
        events = db.query(Event).order_by(Event.created_at.desc()).offset(skip).limit(limit).all()
        registry_read_operations.labels(operation='list_events').inc()
        registry_read_latency.observe((time.time() - start_time) * 1000)
        return events
    except Exception as e:
        registry_errors.labels(error_type='list_events_failed').inc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
