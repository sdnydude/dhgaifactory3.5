from datetime import datetime
import uuid
"""
DHG Registry - SQLAlchemy Models
Media, Transcripts, Segments, Events tables
"""
from sqlalchemy import Column, String, Integer, BigInteger, Float, Boolean, Text, DateTime, Date, ForeignKey, Index, UniqueConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TSVECTOR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
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
    
    # Run-tracking (added migration 008)
    intake_version = Column(Integer, nullable=False, server_default="1")
    current_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cme_pipeline_runs.run_id", ondelete="SET NULL"),
        nullable=True,
    )

    # Google Drive sync (added migration 010)
    drive_folder_id = Column(Text, nullable=True)
    drive_last_synced_at = Column(DateTime(timezone=True), nullable=True)
    drive_sync_status = Column(Text, nullable=True)

    # Relationships
    agent_outputs = relationship("CMEAgentOutput", back_populates="project", cascade="all, delete-orphan")
    review_assignments = relationship("CMEReviewAssignment", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("CMEDocument", back_populates="project")
    intake_fields = relationship("CMEIntakeField", back_populates="project")
    source_references = relationship("CMESourceReference", back_populates="project")
    pipeline_runs = relationship(
        "CMEPipelineRun",
        back_populates="project",
        cascade="all, delete-orphan",
        foreign_keys="CMEPipelineRun.project_id",
        order_by="CMEPipelineRun.run_number.desc()",
    )


class CMEPipelineRun(Base):
    """Individual pipeline execution runs for a CME project.

    Each rerun creates a new row. run_number is monotonic per project.
    current_run_id on cme_projects points at the active/latest row.
    """
    __tablename__ = "cme_pipeline_runs"

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cme_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_number = Column(Integer, nullable=False)
    thread_id = Column(String(100), nullable=False)
    langgraph_run_id = Column(String(100), nullable=False)
    intake_version_used = Column(Integer, nullable=False, default=1)
    triggered_by = Column(String(255), nullable=True)
    trigger_reason = Column(String(32), nullable=False, default="manual")
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(16), nullable=False, default="processing")
    error_message = Column(Text, nullable=True)
    final_agent = Column(String(100), nullable=True)
    reason = Column(Text, nullable=True)

    project = relationship(
        "CMEProject",
        back_populates="pipeline_runs",
        foreign_keys=[project_id],
    )

    __table_args__ = (
        UniqueConstraint("project_id", "run_number", name="uq_cme_pipeline_runs_project_run_number"),
        Index("ix_cme_pipeline_runs_project_run", "project_id", "run_number"),
        Index("ix_cme_pipeline_runs_status", "status"),
    )


class CMEAgentOutput(Base):
    """Individual outputs from each agent in the 12-agent pipeline"""
    __tablename__ = "cme_agent_outputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("cme_projects.id", ondelete="CASCADE"), nullable=False, index=True)

    agent_name = Column(String(100), nullable=False, index=True)
    output_type = Column(String(100), nullable=False)
    content = Column(JSONB, nullable=False)
    quality_score = Column(Float, nullable=True)

    # Extracted text for full-text search
    document_text = Column(Text, nullable=True)

    # Vector embedding and search
    embedding = Column(Vector(768), nullable=True)
    search_vector = Column(TSVECTOR, nullable=True)

    # LangSmith trace reference
    langsmith_trace_id = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    project = relationship("CMEProject", back_populates="agent_outputs")
    documents = relationship("CMEDocument", back_populates="agent_output")


# =============================================================================
# CME REVIEW WORKFLOW MODELS (Decisions R1-R7)
# =============================================================================

class CMEReviewerConfig(Base):
    """Admin-configurable list of reviewers (R1)"""
    __tablename__ = "cme_reviewer_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reviewer identity
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    
    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    max_concurrent_reviews = Column(Integer, default=5)  # Workload limit
    
    # Notification preferences
    notify_email = Column(Boolean, default=True)
    notify_google_chat = Column(Boolean, default=True)
    google_chat_webhook_url = Column(String(500), nullable=True)
    
    # Stats
    total_reviews = Column(Integer, default=0)
    avg_review_time_hours = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    assignments = relationship("CMEReviewAssignment", back_populates="reviewer")


class CMEReviewAssignment(Base):
    """Individual review assignment with SLA tracking (R2-R5)"""
    __tablename__ = "cme_review_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    project_id = Column(UUID(as_uuid=True), ForeignKey("cme_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("cme_reviewer_config.id"), nullable=False, index=True)
    
    # Assignment order (1, 2, or 3 per R2)
    reviewer_order = Column(Integer, nullable=False)
    
    # Status: pending, active, approved, revision_requested, timeout, skipped
    status = Column(String(50), nullable=False, default="pending")
    
    # SLA tracking (R3: 24 hours)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    sla_deadline = Column(DateTime(timezone=True), nullable=True)  # assigned_at + 24h
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Review content
    decision = Column(String(50), nullable=True)  # approved, revision_requested
    notes = Column(Text, nullable=True)
    
    # Plate JS annotations (stored as JSONB for inline suggestions)
    annotations = Column(JSONB, default=[])
    
    # Notification tracking
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    escalation_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    project = relationship("CMEProject", back_populates="review_assignments")
    reviewer = relationship("CMEReviewerConfig", back_populates="assignments")


# =============================================================================
# CME DOCUMENT STORAGE (Compliance — 7-year ACCME retention)
# =============================================================================

class CMEDocument(Base):
    """Immutable, versioned CME documents for compliance retention.

    Each agent output generates a document row. Revisions create new rows
    (incremented version) rather than updating existing ones. No row is ever
    deleted — ON DELETE RESTRICT on project_id enforces this at the DB level.
    """
    __tablename__ = "cme_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("cme_projects.id", ondelete="RESTRICT"), nullable=False, index=True)
    agent_output_id = Column(UUID(as_uuid=True), ForeignKey("cme_agent_outputs.id"), nullable=True)

    # Document identity
    document_type = Column(String(100), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    is_current = Column(Boolean, nullable=False, default=True)

    # Content
    title = Column(String(500), nullable=False)
    content_text = Column(Text, nullable=False)
    content_html = Column(Text, nullable=True)
    content_json = Column(JSONB, nullable=True)
    word_count = Column(Integer, nullable=True)

    # Quality metrics
    quality_score = Column(Float, nullable=True)
    quality_passed = Column(Boolean, nullable=True)
    quality_details = Column(JSONB, nullable=True)

    # Vector embedding and search
    embedding = Column(Vector(768), nullable=True)
    search_vector = Column(TSVECTOR, nullable=True)

    # Source tracking
    source_references = Column(JSONB, default=[])

    # Compliance
    created_by = Column(String(255), nullable=False, default="system")
    retention_until = Column(DateTime(timezone=True), nullable=False)
    is_archived = Column(Boolean, nullable=False, default=False)

    # Google Drive sync (added migration 010)
    drive_file_id = Column(Text, nullable=True)
    drive_synced_at = Column(DateTime(timezone=True), nullable=True)
    drive_md5 = Column(Text, nullable=True)

    # Immutable — no updated_at
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("CMEProject", back_populates="documents")
    agent_output = relationship("CMEAgentOutput", back_populates="documents")
    references = relationship("CMESourceReference", back_populates="document")


class CMEIntakeField(Base):
    """Structured extraction of intake form fields for search and reporting.

    Explodes the JSONB intake blob from cme_projects into individual
    searchable rows — one per field per section.
    """
    __tablename__ = "cme_intake_fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("cme_projects.id", ondelete="RESTRICT"), nullable=False, index=True)

    # Section/field identity
    section = Column(String(50), nullable=False, index=True)
    field_name = Column(String(100), nullable=False)
    field_label = Column(String(255), nullable=False)

    # Value (text for scalar, JSONB for arrays/objects)
    value_text = Column(Text, nullable=True)
    value_json = Column(JSONB, nullable=True)

    # Search
    search_vector = Column(TSVECTOR, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship
    project = relationship("CMEProject", back_populates="intake_fields")

    __table_args__ = (
        UniqueConstraint("project_id", "section", "field_name", name="uq_intake_project_section_field"),
    )


class CMESourceReference(Base):
    """Literature citations and references used by CME agents.

    Stores PubMed citations, guideline references, and URLs with cached
    content for 7-year compliance. Each reference is linked to the project
    and optionally to a specific document version.
    """
    __tablename__ = "cme_source_references"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("cme_projects.id", ondelete="RESTRICT"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("cme_documents.id"), nullable=True)

    # Reference identity
    ref_type = Column(String(50), nullable=False, index=True)  # pubmed, url, journal, guideline
    ref_id = Column(String(255), nullable=True, index=True)  # PubMed ID, DOI

    # Content
    title = Column(Text, nullable=False)
    authors = Column(Text, nullable=True)
    journal = Column(String(500), nullable=True)
    publication_date = Column(Date, nullable=True)
    url = Column(Text, nullable=True)
    abstract = Column(Text, nullable=True)

    # Vector embedding and search
    embedding = Column(Vector(768), nullable=True)
    search_vector = Column(TSVECTOR, nullable=True)

    # Compliance — cache full reference data (URLs die, papers get retracted)
    accessed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    cached_content = Column(JSONB, nullable=True)

    # Verification (populated by Citation Checker agent)
    verification_status = Column(String(50), nullable=True, index=True)  # verified | not_found | retracted | outdated | landmark
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("CMEProject", back_populates="source_references")
    document = relationship("CMEDocument", back_populates="references")


# =============================================================================
# SECURITY / RBAC MODELS
# =============================================================================

class SecurityUser(Base):
    """Authenticated user identity — created on first Cloudflare Access login."""
    __tablename__ = "security_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    cloudflare_id = Column(String(255), nullable=True, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user_roles = relationship("SecurityUserRole", back_populates="user", cascade="all, delete-orphan",
                              foreign_keys="SecurityUserRole.user_id")
    project_access = relationship("SecurityProjectAccess", back_populates="user", cascade="all, delete-orphan",
                                  foreign_keys="SecurityProjectAccess.user_id")


class SecurityRole(Base):
    """System role with a fixed permission set (admin, operations, finance, editor, viewer)."""
    __tablename__ = "security_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    permissions = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user_roles = relationship("SecurityUserRole", back_populates="role")


class SecurityUserRole(Base):
    """Many-to-many: a user can hold multiple roles simultaneously."""
    __tablename__ = "security_user_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("security_users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("security_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("security_users.id", ondelete="SET NULL"), nullable=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_security_user_role"),
    )

    # Relationships
    user = relationship("SecurityUser", back_populates="user_roles", foreign_keys=[user_id])
    role = relationship("SecurityRole", back_populates="user_roles")
    granter = relationship("SecurityUser", foreign_keys=[granted_by])


class SecurityProjectAccess(Base):
    """Per-project access grant — editors/viewers only see assigned projects."""
    __tablename__ = "security_project_access"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("security_users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("cme_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    access_level = Column(String(50), nullable=False, default="viewer")
    granted_by = Column(UUID(as_uuid=True), ForeignKey("security_users.id", ondelete="SET NULL"), nullable=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_security_user_project"),
    )

    # Relationships
    user = relationship("SecurityUser", back_populates="project_access", foreign_keys=[user_id])
    project = relationship("CMEProject")
    granter = relationship("SecurityUser", foreign_keys=[granted_by])


class SecurityAuditLog(Base):
    """Immutable audit trail — every security-relevant action recorded."""
    __tablename__ = "security_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("security_users.id", ondelete="SET NULL"), nullable=True)
    user_email = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(255), nullable=True)
    detail = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # No updated_at, no cascade delete — audit logs are immutable
    user = relationship("SecurityUser", foreign_keys=[user_id])


# =============================================================================
# FRONTEND DESIGN SPEC MODELS
# =============================================================================

class FrontendDesignSpec(Base):
    """Tracks frontend feature design specs with component lists and visual polish config."""
    __tablename__ = "frontend_design_specs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    status = Column(String(50), default="draft")
    spec_path = Column(String(512), nullable=False)
    comp_path = Column(String(512), nullable=True)
    description = Column(Text, nullable=False)
    components = Column(JSONB, default=[])
    design_tokens = Column(JSONB, default={})
    visual_polish = Column(JSONB, default={})
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    implemented_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# =============================================================================
# INFERENCE PLATFORM MODELS
# =============================================================================

class InferenceNode(Base):
    __tablename__ = "inference_nodes"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    node_name = Column(String(50), unique=True, nullable=False)
    host = Column(String(255), nullable=False)
    gateway_port = Column(Integer, default=8100)
    ollama_port = Column(Integer, default=11434)
    gpu_model = Column(String(100))
    gpu_vram_gb = Column(Integer)
    ram_gb = Column(Integer)
    status = Column(String(20), default="offline")
    fallback_enabled = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime(timezone=True))
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata_ = Column("metadata", JSONB, default={})
    models = relationship("InferenceModel", back_populates="node", cascade="all, delete-orphan")

class InferenceModel(Base):
    __tablename__ = "inference_models"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    node_id = Column(UUID(as_uuid=True), ForeignKey("inference_nodes.id", ondelete="CASCADE"))
    model_name = Column(String(255), nullable=False)
    model_alias = Column(String(100))
    task_types = Column(ARRAY(String), default=[])
    priority = Column(Integer, default=1)
    vram_usage_gb = Column(Numeric(4, 1))
    loaded = Column(Boolean, default=False)
    max_context_length = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    node = relationship("InferenceNode", back_populates="models")

class LLMInteraction(Base):
    __tablename__ = "llm_interactions"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(UUID(as_uuid=True), nullable=True)
    node_id = Column(UUID(as_uuid=True), ForeignKey("inference_nodes.id"))
    model_name = Column(String(255), nullable=False)
    model_source = Column(String(50), nullable=False)
    model_digest = Column(String(64))
    task_type = Column(String(50))
    agent_name = Column(String(100))
    session_id = Column(UUID(as_uuid=True))
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    latency_ms = Column(Integer)
    input_hash = Column(String(64))
    input_summary = Column(Text)
    input_has_image = Column(Boolean, default=False)
    output = Column(JSONB)
    output_validated = Column(Boolean)
    output_schema_name = Column(String(100))
    fallback_used = Column(Boolean, default=False)
    fallback_reason = Column(Text)
    retry_count = Column(Integer, default=0)
    estimated_cost_usd = Column(Numeric(10, 6))
    synced_at = Column(DateTime(timezone=True))

class LLMQualityEval(Base):
    __tablename__ = "llm_quality_evals"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    interaction_id = Column(UUID(as_uuid=True), ForeignKey("llm_interactions.id"))
    grade = Column(Integer)
    criteria = Column(JSONB)
    issues = Column(ARRAY(String))
    graded_by = Column(String(100))
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())

class ModelUpdateLog(Base):
    __tablename__ = "model_update_log"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    node_id = Column(UUID(as_uuid=True), ForeignKey("inference_nodes.id"))
    model_name = Column(String(255))
    old_digest = Column(String(64))
    new_digest = Column(String(64))
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(String(100))

class RoutingConfig(Base):
    __tablename__ = "routing_config"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    task_type = Column(String(100), unique=True, nullable=False)
    prefer = Column(String(100), nullable=False)
    fallback = Column(String(100))
    enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class DevChangelog(Base):
    """Admin/Reporting dev changelog — agent-assisted editable development log.

    Field ownership split (enforced at schema + endpoint layer, not DB):
      agent-owned:  commits, commit_count, detected_status, window_start, window_end,
                    sessions, detected_at, last_agent_run_at, source
      human-owned:  declared_status, key_insight, notes, priority, locked
    Display uses COALESCE(declared_status, detected_status).
    locked=true causes the future nightly (3am) agent to skip the row entirely.
    """
    __tablename__ = "dev_changelog"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    slug = Column(String(255), nullable=False, unique=True)
    epic = Column(String(500), nullable=False)
    category = Column(String(50), nullable=False)  # feature|infra|fix|refactor|docs|debt
    detected_status = Column(String(50), nullable=False)  # shipped|in_progress|backlog|abandoned
    declared_status = Column(String(50), nullable=True)
    window_start = Column(Date, nullable=False)
    window_end = Column(Date, nullable=True)
    commit_count = Column(Integer, nullable=False, default=0)
    commits = Column(JSONB, nullable=False, default=list)  # [{sha, date, subject, author}]
    sessions = Column(JSONB, nullable=False, default=list)  # [{session_id, chunk_idx, note}]
    key_insight = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    priority = Column(Integer, nullable=True)
    locked = Column(Boolean, nullable=False, default=False)
    source = Column(String(20), nullable=False, default="manual")  # manual|agent|mixed
    detected_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_agent_run_at = Column(DateTime(timezone=True), nullable=True)
    last_human_edit_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_dev_changelog_detected_status", "detected_status"),
        Index("ix_dev_changelog_declared_status", "declared_status"),
        Index("ix_dev_changelog_category", "category"),
        Index("ix_dev_changelog_window_start", "window_start"),
    )


class DownloadJob(Base):
    __tablename__ = "download_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(Text, nullable=False)
    graph_id = Column(Text, nullable=False)
    scope = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="pending")
    artifact_path = Column(Text, nullable=True)
    artifact_sha256 = Column(Text, nullable=True)
    artifact_bytes = Column(BigInteger, nullable=True)
    created_by = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cme_projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    selected_document_ids = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_download_jobs_status_created_at", "status", "created_at"),
        Index(
            "ix_download_jobs_thread_scope_status",
            "thread_id", "scope", "status",
        ),
        Index(
            "ix_download_jobs_project_status",
            "project_id", "status",
        ),
    )

    def __repr__(self) -> str:
        return f"<DownloadJob id={self.id} scope={self.scope} status={self.status}>"
