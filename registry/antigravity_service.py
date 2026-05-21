"""Antigravity service — DB operations for chat and file tracking."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from models import AntigravityChat, AntigravityFile


def create_or_update_chat(db: Session, chat_data) -> tuple:
    """Create or update a chat. Returns (AntigravityChat, file_count, created)."""
    existing = db.query(AntigravityChat).filter(
        AntigravityChat.conversation_id == chat_data.conversation_id,
    ).first()

    if existing:
        existing.title = chat_data.title or existing.title
        existing.summary = chat_data.summary or existing.summary
        existing.user_objective = chat_data.user_objective or existing.user_objective
        existing.tags = chat_data.tags or existing.tags
        existing.metadata = chat_data.metadata or existing.metadata
        existing.last_modified = datetime.utcnow()

        db.commit()
        db.refresh(existing)

        file_count = db.query(func.count(AntigravityFile.id)).filter(
            AntigravityFile.conversation_id == chat_data.conversation_id,
        ).scalar()

        return existing, file_count, False

    new_chat = AntigravityChat(
        conversation_id=chat_data.conversation_id,
        title=chat_data.title,
        summary=chat_data.summary,
        user_objective=chat_data.user_objective,
        tags=chat_data.tags,
        metadata=chat_data.metadata,
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return new_chat, 0, True


def list_chats(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[tuple]:
    """Return list of (AntigravityChat, file_count) tuples."""
    query = db.query(AntigravityChat)
    if status:
        query = query.filter(AntigravityChat.status == status)

    chats = query.order_by(desc(AntigravityChat.last_modified)).offset(offset).limit(limit).all()

    result = []
    for chat in chats:
        file_count = db.query(func.count(AntigravityFile.id)).filter(
            AntigravityFile.conversation_id == chat.conversation_id,
        ).scalar()
        result.append((chat, file_count))
    return result


def get_chat(db: Session, conversation_id: str) -> tuple | None:
    """Return (AntigravityChat, file_count) or None."""
    chat = db.query(AntigravityChat).filter(
        AntigravityChat.conversation_id == conversation_id,
    ).first()
    if not chat:
        return None

    file_count = db.query(func.count(AntigravityFile.id)).filter(
        AntigravityFile.conversation_id == conversation_id,
    ).scalar()

    return chat, file_count


def update_chat(db: Session, conversation_id: str, updates: dict) -> tuple | None:
    """Update chat fields. Returns (AntigravityChat, file_count) or None."""
    chat = db.query(AntigravityChat).filter(
        AntigravityChat.conversation_id == conversation_id,
    ).first()
    if not chat:
        return None

    for field, value in updates.items():
        setattr(chat, field, value)

    chat.last_modified = datetime.utcnow()
    db.commit()
    db.refresh(chat)

    file_count = db.query(func.count(AntigravityFile.id)).filter(
        AntigravityFile.conversation_id == conversation_id,
    ).scalar()

    return chat, file_count


def create_file(db: Session, file_data) -> AntigravityFile | None:
    """Create a file record. Returns None if parent chat not found."""
    chat = db.query(AntigravityChat).filter(
        AntigravityChat.conversation_id == file_data.conversation_id,
    ).first()
    if not chat:
        return None

    new_file = AntigravityFile(
        conversation_id=file_data.conversation_id,
        file_path=file_data.file_path,
        file_type=file_data.file_type,
        file_size_bytes=file_data.file_size_bytes,
        artifact_type=file_data.artifact_type,
        summary=file_data.summary,
        metadata=file_data.metadata,
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    return new_file


def list_files(
    db: Session,
    *,
    conversation_id: str | None = None,
    artifact_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AntigravityFile]:
    query = db.query(AntigravityFile)
    if conversation_id:
        query = query.filter(AntigravityFile.conversation_id == conversation_id)
    if artifact_type:
        query = query.filter(AntigravityFile.artifact_type == artifact_type)
    return query.order_by(desc(AntigravityFile.created_at)).offset(offset).limit(limit).all()


def get_file(db: Session, file_id: str) -> AntigravityFile | None:
    return db.query(AntigravityFile).filter(AntigravityFile.id == file_id).first()


def get_chat_files(db: Session, conversation_id: str) -> list[AntigravityFile]:
    return (
        db.query(AntigravityFile)
        .filter(AntigravityFile.conversation_id == conversation_id)
        .order_by(desc(AntigravityFile.created_at))
        .all()
    )
