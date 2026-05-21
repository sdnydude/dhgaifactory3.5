"""Claude AI data service — DB operations for projects, conversations, messages, artifacts."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Project, Conversation, Message, Artifact


def list_projects(
    db: Session, *, skip: int = 0, limit: int = 100,
) -> list[tuple]:
    """Return list of (Project, conversation_count) tuples."""
    return (
        db.query(Project, func.count(Conversation.id))
        .outerjoin(Conversation, Conversation.project_id == Project.id)
        .group_by(Project.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_project(db: Session, project_id: UUID) -> tuple | None:
    """Return (Project, conversation_count) or None."""
    result = (
        db.query(Project, func.count(Conversation.id))
        .outerjoin(Conversation, Conversation.project_id == Project.id)
        .filter(Project.id == project_id)
        .group_by(Project.id)
        .first()
    )
    return result


def _conversations_with_counts(query):
    """Subquery-based conversation listing with message + artifact counts."""
    msg_counts = (
        func.count(Message.id).label("msg_count")
    )
    art_counts = (
        func.count(Artifact.id).label("art_count")
    )
    return (
        query
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .outerjoin(Artifact, Artifact.conversation_id == Conversation.id)
        .group_by(Conversation.id)
        .with_entities(Conversation, msg_counts, art_counts)
    )


def list_conversations(
    db: Session,
    *,
    project_id: UUID | None = None,
    export_source: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[tuple]:
    """Return list of (Conversation, message_count, artifact_count) tuples."""
    query = db.query(Conversation)
    if project_id:
        query = query.filter(Conversation.project_id == project_id)
    if export_source:
        query = query.filter(Conversation.export_source == export_source)

    query = query.order_by(Conversation.created_at.desc()).offset(skip).limit(limit)
    return _conversations_with_counts(query).all()


def get_conversation(db: Session, conversation_id: UUID) -> tuple | None:
    """Return (Conversation, message_count, artifact_count) or None."""
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    return _conversations_with_counts(query).first()


def search_conversations(
    db: Session, q: str, *, skip: int = 0, limit: int = 50,
) -> list[tuple]:
    """Search conversations by title. Returns list of (Conversation, msg_count, art_count)."""
    query = (
        db.query(Conversation)
        .filter(Conversation.title.ilike(f"%{q}%"))
        .order_by(Conversation.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return _conversations_with_counts(query).all()


def list_messages(db: Session, conversation_id: UUID) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.message_index)
        .all()
    )


def list_artifacts(
    db: Session,
    *,
    artifact_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Artifact]:
    query = db.query(Artifact)
    if artifact_type:
        query = query.filter(Artifact.artifact_type == artifact_type)
    return query.order_by(Artifact.created_at.desc()).offset(skip).limit(limit).all()


def list_artifacts_by_conversation(db: Session, conversation_id: UUID) -> list[Artifact]:
    return (
        db.query(Artifact)
        .filter(Artifact.conversation_id == conversation_id)
        .order_by(Artifact.created_at)
        .all()
    )


def get_artifact(db: Session, artifact_id: UUID) -> Artifact | None:
    return db.query(Artifact).filter(Artifact.id == artifact_id).first()
