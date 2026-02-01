from datetime import datetime
import uuid
"""
DHG Registry - SQLAlchemy Models
Media, Transcripts, Segments, Events tables
"""
from sqlalchemy import Column, String, Integer, BigInteger, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class Media(Base):
    """Source media files"""
    __tablename__ = 'media'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(512), nullable=False)
    filepath = Column(String(1024), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(128), nullable=False)
    duration_seconds = Column(Float, nullable=True)
    status = Column(String(32), nullable=False, default='pending')  # pending, processing, completed, failed
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    transcripts = relationship("Transcript", back_populates="media", cascade="all, delete-orphan")


class Transcript(Base):
    """Complete transcription results"""
    __tablename__ = 'transcripts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey('media.id', ondelete='CASCADE'), nullable=False)
    full_text = Column(Text, nullable=False)
    language = Column(String(16), nullable=True)
    confidence_score = Column(Float, nullable=True)
    model_name = Column(String(64), nullable=True)
    model_version = Column(String(32), nullable=True)
    processing_time_seconds = Column(Float, nullable=False)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    media = relationship("Media", back_populates="transcripts")
    segments = relationship("Segment", back_populates="transcript", cascade="all, delete-orphan")


class Segment(Base):
    """Timestamped transcript segments"""
    __tablename__ = 'segments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcript_id = Column(UUID(as_uuid=True), ForeignKey('transcripts.id', ondelete='CASCADE'), nullable=False)
    segment_index = Column(Integer, nullable=False)
    start_time_seconds = Column(Float, nullable=False)
    end_time_seconds = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=True)
    speaker_id = Column(String(64), nullable=True)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    transcript = relationship("Transcript", back_populates="segments")


class Event(Base):
    """Audit log for all registry operations"""
    __tablename__ = 'events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(64), nullable=False)  # create, update, delete, transcribe, etc.
    entity_type = Column(String(64), nullable=False)  # media, transcript, segment
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(String(128), nullable=True)
    description = Column(Text, nullable=True)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Project(Base):
    """Claude AI Projects"""
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(512), nullable=False)
    project_id = Column(String(256), nullable=True, unique=True)
    description = Column(Text, nullable=True)
    custom_instructions = Column(Text, nullable=True)
    knowledge_files = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    meta_data = Column(JSONB, nullable=True)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="project", cascade="all, delete-orphan")


class Conversation(Base):
    """Claude AI Conversations"""
    __tablename__ = 'conversations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(1024), nullable=False)
    conversation_id = Column(String(256), nullable=True, unique=True)
    export_source = Column(String(64), nullable=False)
    model_name = Column(String(128), nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    meta_data = Column(JSONB, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.message_index")
    artifacts = relationship("Artifact", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Individual messages in Claude conversations"""
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)
    message_index = Column(Integer, nullable=False)
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    attachments = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    meta_data = Column(JSONB, nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    artifacts = relationship("Artifact", back_populates="message")


class Artifact(Base):
    """Claude AI Artifacts (code, documents, visualizations, etc.)"""
    __tablename__ = 'artifacts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)
    message_id = Column(UUID(as_uuid=True), ForeignKey('messages.id', ondelete='SET NULL'), nullable=True)
    title = Column(String(512), nullable=False)
    artifact_type = Column(String(64), nullable=False)
    language = Column(String(64), nullable=True)
    content = Column(Text, nullable=False)
    file_path = Column(String(1024), nullable=True)
    published_url = Column(String(1024), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    meta_data = Column(JSONB, nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="artifacts")
    message = relationship("Message", back_populates="artifacts")


# =============================================================================
# AGENT REGISTRY MODELS (for LangSmith Cloud)
# =============================================================================

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    division = Column(String, nullable=False)
    type = Column(String, nullable=False)
    description = Column(Text)
    
    # Deployment info
    deployment_type = Column(String, default="langsmith_cloud")
    deployment_url = Column(String)
    langsmith_deployment_id = Column(String)
    langsmith_org = Column(String)
    
    # GitHub integration
    github_repo = Column(String)
    github_branch = Column(String, default="main")
    github_path = Column(String)
    
    # Legacy self-hosted (backward compatibility)
    endpoint = Column(String)
    
    # Capabilities and schemas (JSONB for flexibility)
    capabilities = Column(JSONB)
    io_schema = Column(JSONB)
    models = Column(JSONB)
    external_apis = Column(JSONB)
    observability = Column(JSONB)
    
    # Status
    status = Column(String, default="healthy")
    last_heartbeat = Column(DateTime(timezone=True))
    
    # Timestamps
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    heartbeats = relationship("AgentHeartbeat", back_populates="agent", cascade="all, delete-orphan")


class AgentHeartbeat(Base):
    __tablename__ = "agent_heartbeats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Model status
    models = Column(JSONB)
    
    # Metrics
    requests_total = Column(Integer, default=0)
    requests_success = Column(Integer, default=0)
    requests_failed = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0.0)
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    
    # LangSmith Cloud metrics
    langsmith_deployment_status = Column(String)
    langsmith_traces_count = Column(Integer)
    deployment_tier = Column(String)
    
    # Relationship
    agent = relationship("Agent", back_populates="heartbeats")


# =============================================================================
# ANTIGRAVITY TRACKING MODELS
# =============================================================================

class AntigravityChat(Base):
    __tablename__ = "antigravity_chats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(Text)
    summary = Column(Text)
    user_objective = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_modified = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    status = Column(String, default="active", index=True)
    tags = Column(ARRAY(String))
    extra_processing_metadata = Column('metadata', JSONB)
    
    # Relationship
    files = relationship("AntigravityFile", back_populates="chat", cascade="all, delete-orphan")


class AntigravityFile(Base):
    __tablename__ = "antigravity_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(String, ForeignKey("antigravity_chats.conversation_id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(Text, nullable=False)
    file_type = Column(String, index=True)
    file_size_bytes = Column(BigInteger)
    artifact_type = Column(String, index=True)
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_modified = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    extra_processing_metadata = Column('metadata', JSONB)
    
    # Relationship
    chat = relationship("AntigravityChat", back_populates="files")


# =============================================================================
# RESEARCH REQUEST MODELS
# =============================================================================

class ResearchRequest(Base):
    """Research request tracking"""
    __tablename__ = "research_requests"
    
    request_id = Column(String, primary_key=True, default=lambda: f"req_{uuid.uuid4().hex[:12]}")
    user_id = Column(String, nullable=False, index=True)
    agent_type = Column(String, nullable=False, default="cme_research")
    status = Column(String, nullable=False, default="pending", index=True)  # pending, running, completed, failed
    
    # Input parameters (JSON)
    input_params = Column(JSONB, nullable=False)
    
    # Output summary (JSON)
    output_summary = Column(JSONB, nullable=True)
    
    # Metadata (JSON)
    processing_metadata = Column(JSONB, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_research_user_created", "user_id", "created_at"),
        Index("idx_research_status_created", "status", "created_at"),
    )


# =============================================================================
# CME PROJECT MODELS
# =============================================================================

class CMEProject(Base):
    """CME Grant projects with intake data and pipeline execution status"""
    __tablename__ = "cme_projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Project basics
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="intake")  # intake/processing/review/complete/failed/cancelled
    
    # Full intake form stored as JSONB (10 sections, 47 fields)
    intake = Column(JSONB, nullable=False)
    
    # Pipeline execution tracking
    current_agent = Column(String(100), nullable=True)
    progress_percent = Column(Integer, default=0)
    agents_completed = Column(ARRAY(String), default=[])
    agents_pending = Column(ARRAY(String), default=[])
    
    # LangGraph integration
    pipeline_thread_id = Column(String(100), nullable=True)
    langsmith_run_id = Column(String(100), nullable=True)
    
    # Outputs from each agent stored as JSONB
    outputs = Column(JSONB, default={})
    
    # Error tracking
    errors = Column(JSONB, default=[])
    
    # Human review
    human_review_status = Column(String(50), nullable=True)
    human_review_notes = Column(Text, nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    agent_outputs = relationship("CMEAgentOutput", back_populates="project", cascade="all, delete-orphan")


class CMEAgentOutput(Base):
    """Individual outputs from each agent in the 12-agent pipeline"""
    __tablename__ = "cme_agent_outputs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("cme_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    agent_name = Column(String(100), nullable=False, index=True)
    output_type = Column(String(100), nullable=False)
    content = Column(JSONB, nullable=False)
    quality_score = Column(Float, nullable=True)
    
    # LangSmith trace reference
    langsmith_trace_id = Column(String(100), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship
    project = relationship("CMEProject", back_populates="agent_outputs")
