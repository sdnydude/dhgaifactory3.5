
"""
Antigravity Chat and File Tracking Endpoints
Tracks all Antigravity conversations and generated files in the central registry
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

# Import get_db from main API
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db

from sqlalchemy import func, desc

from models import AntigravityChat, AntigravityFile
from schemas import (
    AntigravityChatCreate, AntigravityChatUpdate, AntigravityChatResponse,
    AntigravityFileCreate, AntigravityFileResponse
)


router = APIRouter(prefix="/api/v1/antigravity", tags=["antigravity"])


# =============================================================================
# CHAT ENDPOINTS
# =============================================================================

@router.post("/chats", response_model=AntigravityChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(chat: AntigravityChatCreate, db: Session = Depends(get_db)):
    """Create or update an Antigravity chat record"""
    
    # Check if chat already exists
    existing = db.query(AntigravityChat).filter(
        AntigravityChat.conversation_id == chat.conversation_id
    ).first()
    
    if existing:
        # Update existing
        existing.title = chat.title or existing.title
        existing.summary = chat.summary or existing.summary
        existing.user_objective = chat.user_objective or existing.user_objective
        existing.tags = chat.tags or existing.tags
        existing.metadata = chat.metadata or existing.metadata
        existing.last_modified = datetime.utcnow()
        
        db.commit()
        db.refresh(existing)
        
        file_count = db.query(func.count(AntigravityFile.id)).filter(
            AntigravityFile.conversation_id == chat.conversation_id
        ).scalar()
        
        response = AntigravityChatResponse.from_orm(existing)
        response.file_count = file_count
        return response
    
    # Create new
    new_chat = AntigravityChat(
        conversation_id=chat.conversation_id,
        title=chat.title,
        summary=chat.summary,
        user_objective=chat.user_objective,
        tags=chat.tags,
        metadata=chat.metadata
    )
    
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    
    response = AntigravityChatResponse.from_orm(new_chat)
    response.file_count = 0
    return response


@router.get("/chats", response_model=List[AntigravityChatResponse])
async def list_chats(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List Antigravity chats with optional filtering"""
    
    query = db.query(AntigravityChat)
    
    if status:
        query = query.filter(AntigravityChat.status == status)
    
    chats = query.order_by(desc(AntigravityChat.last_modified)).offset(offset).limit(limit).all()
    
    responses = []
    for chat in chats:
        file_count = db.query(func.count(AntigravityFile.id)).filter(
            AntigravityFile.conversation_id == chat.conversation_id
        ).scalar()
        
        response = AntigravityChatResponse.from_orm(chat)
        response.file_count = file_count
        responses.append(response)
    
    return responses


@router.get("/chats/{conversation_id}", response_model=AntigravityChatResponse)
async def get_chat(conversation_id: str, db: Session = Depends(get_db)):
    """Get a specific Antigravity chat"""
    
    chat = db.query(AntigravityChat).filter(
        AntigravityChat.conversation_id == conversation_id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat {conversation_id} not found"
        )
    
    file_count = db.query(func.count(AntigravityFile.id)).filter(
        AntigravityFile.conversation_id == conversation_id
    ).scalar()
    
    response = AntigravityChatResponse.from_orm(chat)
    response.file_count = file_count
    return response


@router.patch("/chats/{conversation_id}", response_model=AntigravityChatResponse)
async def update_chat(
    conversation_id: str,
    update: AntigravityChatUpdate,
    db: Session = Depends(get_db)
):
    """Update an Antigravity chat"""
    
    chat = db.query(AntigravityChat).filter(
        AntigravityChat.conversation_id == conversation_id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat {conversation_id} not found"
        )
    
    # Update fields
    if update.title is not None:
        chat.title = update.title
    if update.summary is not None:
        chat.summary = update.summary
    if update.user_objective is not None:
        chat.user_objective = update.user_objective
    if update.message_count is not None:
        chat.message_count = update.message_count
    if update.total_tokens is not None:
        chat.total_tokens = update.total_tokens
    if update.total_cost_usd is not None:
        chat.total_cost_usd = update.total_cost_usd
    if update.status is not None:
        chat.status = update.status
    if update.tags is not None:
        chat.tags = update.tags
    if update.metadata is not None:
        chat.metadata = update.metadata
    
    chat.last_modified = datetime.utcnow()
    
    db.commit()
    db.refresh(chat)
    
    file_count = db.query(func.count(AntigravityFile.id)).filter(
        AntigravityFile.conversation_id == conversation_id
    ).scalar()
    
    response = AntigravityChatResponse.from_orm(chat)
    response.file_count = file_count
    return response


# =============================================================================
# FILE ENDPOINTS
# =============================================================================

@router.post("/files", response_model=AntigravityFileResponse, status_code=status.HTTP_201_CREATED)
async def create_file(file: AntigravityFileCreate, db: Session = Depends(get_db)):
    """Register an Antigravity-generated file"""
    
    # Verify chat exists
    chat = db.query(AntigravityChat).filter(
        AntigravityChat.conversation_id == file.conversation_id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat {file.conversation_id} not found. Create chat first."
        )
    
    new_file = AntigravityFile(
        conversation_id=file.conversation_id,
        file_path=file.file_path,
        file_type=file.file_type,
        file_size_bytes=file.file_size_bytes,
        artifact_type=file.artifact_type,
        summary=file.summary,
        metadata=file.metadata
    )
    
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    
    return AntigravityFileResponse.from_orm(new_file)


@router.get("/files", response_model=List[AntigravityFileResponse])
async def list_files(
    conversation_id: Optional[str] = None,
    artifact_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List Antigravity files with optional filtering"""
    
    query = db.query(AntigravityFile)
    
    if conversation_id:
        query = query.filter(AntigravityFile.conversation_id == conversation_id)
    if artifact_type:
        query = query.filter(AntigravityFile.artifact_type == artifact_type)
    
    files = query.order_by(desc(AntigravityFile.created_at)).offset(offset).limit(limit).all()
    
    return [AntigravityFileResponse.from_orm(f) for f in files]


@router.get("/files/{file_id}", response_model=AntigravityFileResponse)
async def get_file(file_id: str, db: Session = Depends(get_db)):
    """Get a specific Antigravity file"""
    
    file = db.query(AntigravityFile).filter(AntigravityFile.id == file_id).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {file_id} not found"
        )
    
    return AntigravityFileResponse.from_orm(file)


@router.get("/chats/{conversation_id}/files", response_model=List[AntigravityFileResponse])
async def get_chat_files(conversation_id: str, db: Session = Depends(get_db)):
    """Get all files for a specific chat"""
    
    files = db.query(AntigravityFile).filter(
        AntigravityFile.conversation_id == conversation_id
    ).order_by(desc(AntigravityFile.created_at)).all()
    
    return [AntigravityFileResponse.from_orm(f) for f in files]
