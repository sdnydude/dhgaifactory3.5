"""
DHG Registry API Service
FastAPI service with /healthz, /metrics, and CRUD operations
All data stored in PostgreSQL DHG Registry
"""
import os
import time
from contextlib import asynccontextmanager
from typing import List, Optional, Union
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, UUID4, UUID4, Field
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session, sessionmaker
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from models import Base, Media, Transcript, Segment, Event, Project, Conversation, Message, Artifact


# ============================================================================
# Prometheus Metrics
# ============================================================================
registry_write_latency = Histogram(
    'registry_write_latency',
    'Database write latency in milliseconds',
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
)

registry_read_latency = Histogram(
    'registry_read_latency',
    'Database read latency in milliseconds',
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000]
)

registry_write_operations = Counter(
    'registry_write_operations',
    'Total number of write operations',
    ['operation']
)

registry_read_operations = Counter(
    'registry_read_operations',
    'Total number of read operations',
    ['operation']
)

registry_errors = Counter(
    'registry_errors',
    'Total number of registry errors',
    ['error_type']
)

registry_db_errors = Counter(
    'registry_db_errors',
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


# ========================================
# Claude AI Data Endpoints
# ========================================

# Pydantic models for Claude data
class ProjectResponse(BaseModel):
    id: UUID4
    name: str
    project_id: Optional[str]
    description: Optional[str]
    custom_instructions: Optional[str]
    knowledge_files: Optional[Union[dict, list]]
    created_at: datetime
    updated_at: datetime
    conversation_count: int = 0

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: UUID4
    title: str
    conversation_id: Optional[str]
    export_source: str
    model_name: Optional[str]
    project_id: Optional[UUID4]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    artifact_count: int = 0

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: UUID4
    conversation_id: UUID4
    message_index: int
    role: str
    content: str
    attachments: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class ArtifactResponse(BaseModel):
    id: UUID4
    conversation_id: UUID4
    message_id: Optional[UUID4]
    title: str
    artifact_type: str
    language: Optional[str]
    content: str
    file_path: Optional[str]
    published_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Projects endpoints
@app.get("/api/v1/projects", response_model=List[ProjectResponse])
async def list_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all projects"""
    start = time.time()
    try:
        projects = db.query(Project).offset(skip).limit(limit).all()
        
        # Add conversation count
        result = []
        for project in projects:
            conv_count = db.query(Conversation).filter(Conversation.project_id == project.id).count()
            proj_dict = {
                'id': project.id,
                'name': project.name,
                'project_id': project.project_id,
                'description': project.description,
                'custom_instructions': project.custom_instructions,
                'knowledge_files': project.knowledge_files,
                'created_at': project.created_at,
                'updated_at': project.updated_at,
                'conversation_count': conv_count
            }
            result.append(ProjectResponse(**proj_dict))
        
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="list_projects").inc()
        return result
    except Exception as e:
        registry_errors.labels(error_type="list_projects").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID4, db: Session = Depends(get_db)):
    """Get a specific project"""
    start = time.time()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        conv_count = db.query(Conversation).filter(Conversation.project_id == project.id).count()
        proj_dict = {
            'id': project.id,
            'name': project.name,
            'project_id': project.project_id,
            'description': project.description,
            'custom_instructions': project.custom_instructions,
            'knowledge_files': project.knowledge_files,
            'created_at': project.created_at,
            'updated_at': project.updated_at,
            'conversation_count': conv_count
        }
        
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="get_project").inc()
        return ProjectResponse(**proj_dict)
    except HTTPException:
        raise
    except Exception as e:
        registry_errors.labels(error_type="get_project").inc()
        raise HTTPException(status_code=500, detail=str(e))


# Conversations endpoints
@app.get("/api/v1/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[UUID4] = None,
    export_source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List conversations with optional filtering"""
    start = time.time()
    try:
        query = db.query(Conversation)
        
        if project_id:
            query = query.filter(Conversation.project_id == project_id)
        if export_source:
            query = query.filter(Conversation.export_source == export_source)
        
        conversations = query.order_by(Conversation.created_at.desc()).offset(skip).limit(limit).all()
        
        # Add counts
        result = []
        for conv in conversations:
            msg_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
            art_count = db.query(Artifact).filter(Artifact.conversation_id == conv.id).count()
            conv_dict = {
                'id': conv.id,
                'title': conv.title,
                'conversation_id': conv.conversation_id,
                'export_source': conv.export_source,
                'model_name': conv.model_name,
                'project_id': conv.project_id,
                'created_at': conv.created_at,
                'updated_at': conv.updated_at,
                'message_count': msg_count,
                'artifact_count': art_count
            }
            result.append(ConversationResponse(**conv_dict))
        
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="list_conversations").inc()
        return result
    except Exception as e:
        registry_errors.labels(error_type="list_conversations").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: UUID4, db: Session = Depends(get_db)):
    """Get a specific conversation"""
    start = time.time()
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        msg_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
        art_count = db.query(Artifact).filter(Artifact.conversation_id == conv.id).count()
        conv_dict = {
            'id': conv.id,
            'title': conv.title,
            'conversation_id': conv.conversation_id,
            'export_source': conv.export_source,
            'model_name': conv.model_name,
            'project_id': conv.project_id,
            'created_at': conv.created_at,
            'updated_at': conv.updated_at,
            'message_count': msg_count,
            'artifact_count': art_count
        }
        
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="get_conversation").inc()
        return ConversationResponse(**conv_dict)
    except HTTPException:
        raise
    except Exception as e:
        registry_errors.labels(error_type="get_conversation").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/conversations/search")
async def search_conversations(
    q: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Search conversations by title or content"""
    start = time.time()
    try:
        # Search in conversation titles
        conversations = db.query(Conversation).filter(
            Conversation.title.ilike(f'%{q}%')
        ).order_by(Conversation.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for conv in conversations:
            msg_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
            art_count = db.query(Artifact).filter(Artifact.conversation_id == conv.id).count()
            conv_dict = {
                'id': conv.id,
                'title': conv.title,
                'conversation_id': conv.conversation_id,
                'export_source': conv.export_source,
                'model_name': conv.model_name,
                'project_id': conv.project_id,
                'created_at': conv.created_at,
                'updated_at': conv.updated_at,
                'message_count': msg_count,
                'artifact_count': art_count
            }
            result.append(conv_dict)
        
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="search_conversations").inc()
        return result
    except Exception as e:
        registry_errors.labels(error_type="search_conversations").inc()
        raise HTTPException(status_code=500, detail=str(e))


# Messages endpoints
@app.get("/api/v1/messages/conversation/{conversation_id}", response_model=List[MessageResponse])
async def list_messages(conversation_id: UUID4, db: Session = Depends(get_db)):
    """List messages for a conversation"""
    start = time.time()
    try:
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.message_index).all()
        
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="list_messages").inc()
        return messages
    except Exception as e:
        registry_errors.labels(error_type="list_messages").inc()
        raise HTTPException(status_code=500, detail=str(e))


# Artifacts endpoints
@app.get("/api/v1/artifacts", response_model=List[ArtifactResponse])
async def list_artifacts(
    skip: int = 0,
    limit: int = 100,
    artifact_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List artifacts with optional filtering"""
    start = time.time()
    try:
        query = db.query(Artifact)
        
        if artifact_type:
            query = query.filter(Artifact.artifact_type == artifact_type)
        
        artifacts = query.order_by(Artifact.created_at.desc()).offset(skip).limit(limit).all()
        
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="list_artifacts").inc()
        return artifacts
    except Exception as e:
        registry_errors.labels(error_type="list_artifacts").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/artifacts/conversation/{conversation_id}", response_model=List[ArtifactResponse])
async def list_artifacts_by_conversation(conversation_id: UUID4, db: Session = Depends(get_db)):
    """List artifacts for a specific conversation"""
    start = time.time()
    try:
        artifacts = db.query(Artifact).filter(
            Artifact.conversation_id == conversation_id
        ).order_by(Artifact.created_at).all()
        
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="list_artifacts_by_conversation").inc()
        return artifacts
    except Exception as e:
        registry_errors.labels(error_type="list_artifacts_by_conversation").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: UUID4, db: Session = Depends(get_db)):
    """Get a specific artifact"""
    start = time.time()
    try:
        artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="get_artifact").inc()
        return artifact
    except HTTPException:
        raise
    except Exception as e:
        registry_errors.labels(error_type="get_artifact").inc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================
from fastapi import WebSocket, WebSocketDisconnect
from websocket_manager import manager as ws_manager

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: Optional[str] = None):
    """WebSocket endpoint for real-time communication with UI"""
    client_id = await ws_manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Process message and get response
            response = await ws_manager.handle_client_message(client_id, data)
            
            # Send response if one was returned
            if response:
                await ws_manager.send_message(client_id, response)
                
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
    except Exception as e:
        logger.error("websocket_error", client_id=client_id, error=str(e))
        ws_manager.disconnect(client_id)


@app.get("/api/v1/ws/status")
async def websocket_status():
    """Get WebSocket connection status"""
    return {
        "active_connections": len(ws_manager.active_connections),
        "sessions": len(ws_manager.sessions)
    }
