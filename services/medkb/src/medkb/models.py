from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


@event.listens_for(Base, "init", propagate=True)
def _apply_column_defaults(
    target: Base, args: tuple, kwargs: dict  # type: ignore[type-arg]
) -> None:
    """Apply Python-side column defaults at object instantiation.

    SQLAlchemy's ``mapped_column(default=...)`` is a DML-level default — it
    fires at INSERT time, not at ``__init__`` time.  This listener fills in
    scalar and callable column defaults so that model instances reflect their
    expected defaults before any DB round-trip, which is the behaviour the
    test suite (and application code) depends on.
    """
    for col in target.__table__.columns:
        if col.name not in kwargs and col.default is not None:
            if col.default.is_scalar:
                kwargs[col.name] = col.default.arg
            elif col.default.is_callable:
                kwargs[col.name] = col.default.arg({})


class Corpus(Base):
    __tablename__ = "corpora"
    __table_args__ = (
        CheckConstraint(
            "visibility IN ('public','dhg_internal','division_only')",
            name="corpora_visibility_check",
        ),
        {"schema": "medkb"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(Text, nullable=False)
    contains_phi: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_chunker: Mapped[str] = mapped_column(
        Text, nullable=False, default="markdown"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("corpus_id", "source", "source_id"),
        Index("medkb_documents_corpus_audience", "corpus_id", "audience"),
        Index(
            "medkb_documents_valid",
            "valid_to",
            postgresql_where="valid_to IS NULL",
        ),
        {"schema": "medkb"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    corpus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medkb.corpora.id"), nullable=False
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    audience: Mapped[str | None] = mapped_column(Text)
    authority: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[datetime | None] = mapped_column(Date)
    valid_to: Mapped[datetime | None] = mapped_column(Date)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medkb.documents.id")
    )
    version_label: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index"),
        CheckConstraint("active_version IN (1,2)", name="chunks_active_version_check"),
        Index("medkb_chunks_corpus", "corpus_id"),
        Index("medkb_chunks_parent", "parent_chunk_id"),
        {"schema": "medkb"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medkb.documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    corpus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medkb.corpora.id"), nullable=False
    )
    parent_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medkb.chunks.id")
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    readability_grade: Mapped[float | None] = mapped_column(Numeric(4, 1))
    embedding_v1 = mapped_column(Vector(768))
    embedding_v2 = mapped_column(Vector(768))
    active_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tsv = mapped_column(TSVECTOR)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','running','completed','failed')",
            name="ingestion_jobs_status_check",
        ),
        Index(
            "medkb_ingestion_pending",
            "status",
            "created_at",
            postgresql_where="status = 'pending'",
        ),
        {"schema": "medkb"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    corpus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medkb.corpora.id"), nullable=False
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result_summary: Mapped[dict | None] = mapped_column(JSONB)
    items_total: Mapped[int | None] = mapped_column(Integer)
    items_done: Mapped[int] = mapped_column(Integer, default=0)
    items_error: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"
    __table_args__ = {"schema": "medkb"}

    text_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(768), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class QueryAudit(Base):
    __tablename__ = "query_audit"
    __table_args__ = (
        Index("medkb_query_audit_caller", "caller_id", "created_at"),
        {"schema": "medkb"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[str] = mapped_column(Text, nullable=False)
    caller_id: Mapped[str] = mapped_column(Text, nullable=False)
    corpus_list = mapped_column(ARRAY(Text), nullable=False)
    query_hash: Mapped[str] = mapped_column(Text, nullable=False)
    result_count: Mapped[int | None] = mapped_column(Integer)
    strategy: Mapped[str | None] = mapped_column(Text)
    groundedness_score: Mapped[float | None] = mapped_column(Numeric(4, 3))
    redaction_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
