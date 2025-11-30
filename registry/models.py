"""
DHG Registry - SQLAlchemy Models
Media, Transcripts, Segments, Events tables
"""
from sqlalchemy import Column, String, Integer, BigInteger, Float, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
