"""
DHG Audio Analysis Agent — Database Layer

SQLAlchemy models and async session factory per Build Spec Section 7.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Text, Float, Boolean, DateTime, ForeignKey,
    create_engine, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship

from .config import settings

# Base class for all models
Base = declarative_base()


# ============================================================================
# Models
# ============================================================================

class Job(Base):
    """
    Job tracking table per Build Spec Section 7.1.
    """
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audio_path = Column(Text, nullable=False)
    language_id = Column(String(10), nullable=True)
    diarize = Column(Boolean, default=True)
    num_speakers = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="queued")
    progress = Column(Float, default=0.0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship to result
    result = relationship("Result", back_populates="job", uselist=False)


class Result(Base):
    """
    Analysis result table per Build Spec Section 7.2.
    """
    __tablename__ = "results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), unique=True, nullable=False)
    transcript_text = Column(Text, nullable=False)
    transcript_segments = Column(JSONB, nullable=False)
    detected_language = Column(String(10), nullable=False)
    confidence = Column(Float, nullable=False)
    translation = Column(Text, nullable=True)
    summary = Column(Text, nullable=False)
    topics = Column(JSONB, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    processing_seconds = Column(Float, nullable=False)
    # pgvector embedding column for future semantic search
    # Note: vector(1536) requires pgvector extension
    # transcript_embedding = Column(Vector(1536), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationship to job
    job = relationship("Job", back_populates="result")


# ============================================================================
# Database Engine and Session
# ============================================================================

# Async engine
async_engine = create_async_engine(
    settings.postgres_url,
    echo=False,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncSession:
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create all tables if they don't exist."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_health() -> bool:
    """Check if database is reachable."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False
