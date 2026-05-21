
"""
Antigravity Chat and File Tracking Endpoints
Tracks all Antigravity conversations and generated files in the central registry
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from database import get_db
import antigravity_service as svc
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
    chat_obj, file_count, created = svc.create_or_update_chat(db, chat)
    response = AntigravityChatResponse.from_orm(chat_obj)
    response.file_count = file_count
    return response


@router.get("/chats", response_model=List[AntigravityChatResponse])
async def list_chats(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List Antigravity chats with optional filtering"""
    rows = svc.list_chats(db, status=status, limit=limit, offset=offset)
    responses = []
    for chat_obj, file_count in rows:
        response = AntigravityChatResponse.from_orm(chat_obj)
        response.file_count = file_count
        responses.append(response)
    return responses


@router.get("/chats/{conversation_id}", response_model=AntigravityChatResponse)
async def get_chat(conversation_id: str, db: Session = Depends(get_db)):
    """Get a specific Antigravity chat"""
    result = svc.get_chat(db, conversation_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat {conversation_id} not found")
    chat_obj, file_count = result
    response = AntigravityChatResponse.from_orm(chat_obj)
    response.file_count = file_count
    return response


@router.patch("/chats/{conversation_id}", response_model=AntigravityChatResponse)
async def update_chat(
    conversation_id: str,
    update: AntigravityChatUpdate,
    db: Session = Depends(get_db)
):
    """Update an Antigravity chat"""
    updates = {}
    for field in ("title", "summary", "user_objective", "message_count",
                  "total_tokens", "total_cost_usd", "status", "tags", "metadata"):
        value = getattr(update, field, None)
        if value is not None:
            updates[field] = value

    result = svc.update_chat(db, conversation_id, updates)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat {conversation_id} not found")
    chat_obj, file_count = result
    response = AntigravityChatResponse.from_orm(chat_obj)
    response.file_count = file_count
    return response


# =============================================================================
# FILE ENDPOINTS
# =============================================================================

@router.post("/files", response_model=AntigravityFileResponse, status_code=status.HTTP_201_CREATED)
async def create_file(file: AntigravityFileCreate, db: Session = Depends(get_db)):
    """Register an Antigravity-generated file"""
    new_file = svc.create_file(db, file)
    if not new_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat {file.conversation_id} not found. Create chat first."
        )
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
    files = svc.list_files(db, conversation_id=conversation_id, artifact_type=artifact_type, limit=limit, offset=offset)
    return [AntigravityFileResponse.from_orm(f) for f in files]


@router.get("/files/{file_id}", response_model=AntigravityFileResponse)
async def get_file(file_id: str, db: Session = Depends(get_db)):
    """Get a specific Antigravity file"""
    file = svc.get_file(db, file_id)
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File {file_id} not found")
    return AntigravityFileResponse.from_orm(file)


@router.get("/chats/{conversation_id}/files", response_model=List[AntigravityFileResponse])
async def get_chat_files(conversation_id: str, db: Session = Depends(get_db)):
    """Get all files for a specific chat"""
    files = svc.get_chat_files(db, conversation_id)
    return [AntigravityFileResponse.from_orm(f) for f in files]
