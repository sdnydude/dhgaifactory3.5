"""
Claude AI Data Endpoints
Handles Claude projects, conversations, messages, and artifacts
"""
import time
from typing import List, Optional, Union
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, UUID4

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
import claude_service as svc

from metrics import registry_read_latency, registry_read_operations, registry_errors


router = APIRouter(prefix="/api/v1", tags=["claude"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

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


def _conv_response(conv, msg_count: int, art_count: int) -> ConversationResponse:
    return ConversationResponse(
        id=conv.id, title=conv.title, conversation_id=conv.conversation_id,
        export_source=conv.export_source, model_name=conv.model_name,
        project_id=conv.project_id, created_at=conv.created_at,
        updated_at=conv.updated_at, message_count=msg_count, artifact_count=art_count,
    )


# =============================================================================
# PROJECT ENDPOINTS
# =============================================================================

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all Claude projects"""
    start = time.time()
    try:
        rows = svc.list_projects(db, skip=skip, limit=limit)
        result = []
        for project, conv_count in rows:
            result.append(ProjectResponse(
                id=project.id, name=project.name, project_id=project.project_id,
                description=project.description, custom_instructions=project.custom_instructions,
                knowledge_files=project.knowledge_files, created_at=project.created_at,
                updated_at=project.updated_at, conversation_count=conv_count,
            ))

        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="list_projects").inc()
        return result
    except Exception as e:
        registry_errors.labels(error_type="list_projects").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID4, db: Session = Depends(get_db)):
    """Get a specific Claude project"""
    start = time.time()
    try:
        result = svc.get_project(db, project_id)
        if not result:
            raise HTTPException(status_code=404, detail="Project not found")

        project, conv_count = result
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="get_project").inc()
        return ProjectResponse(
            id=project.id, name=project.name, project_id=project.project_id,
            description=project.description, custom_instructions=project.custom_instructions,
            knowledge_files=project.knowledge_files, created_at=project.created_at,
            updated_at=project.updated_at, conversation_count=conv_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        registry_errors.labels(error_type="get_project").inc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CONVERSATION ENDPOINTS
# =============================================================================

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[UUID4] = None,
    export_source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List Claude conversations with optional filtering"""
    start = time.time()
    try:
        rows = svc.list_conversations(
            db, project_id=project_id, export_source=export_source,
            skip=skip, limit=limit,
        )
        result = [_conv_response(conv, msg_count, art_count) for conv, msg_count, art_count in rows]

        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="list_conversations").inc()
        return result
    except Exception as e:
        registry_errors.labels(error_type="list_conversations").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: UUID4, db: Session = Depends(get_db)):
    """Get a specific Claude conversation"""
    start = time.time()
    try:
        result = svc.get_conversation(db, conversation_id)
        if not result:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conv, msg_count, art_count = result
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="get_conversation").inc()
        return _conv_response(conv, msg_count, art_count)
    except HTTPException:
        raise
    except Exception as e:
        registry_errors.labels(error_type="get_conversation").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/search")
async def search_conversations(
    q: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Search Claude conversations by title or content"""
    start = time.time()
    try:
        rows = svc.search_conversations(db, q, skip=skip, limit=limit)
        result = [_conv_response(conv, msg_count, art_count) for conv, msg_count, art_count in rows]

        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="search_conversations").inc()
        return result
    except Exception as e:
        registry_errors.labels(error_type="search_conversations").inc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MESSAGE ENDPOINTS
# =============================================================================

@router.get("/messages/conversation/{conversation_id}", response_model=List[MessageResponse])
async def list_messages(conversation_id: UUID4, db: Session = Depends(get_db)):
    """List messages for a Claude conversation"""
    start = time.time()
    try:
        messages = svc.list_messages(db, conversation_id)
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="list_messages").inc()
        return messages
    except Exception as e:
        registry_errors.labels(error_type="list_messages").inc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ARTIFACT ENDPOINTS
# =============================================================================

@router.get("/artifacts", response_model=List[ArtifactResponse])
async def list_artifacts(
    skip: int = 0,
    limit: int = 100,
    artifact_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List Claude artifacts with optional filtering"""
    start = time.time()
    try:
        artifacts = svc.list_artifacts(db, artifact_type=artifact_type, skip=skip, limit=limit)
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="list_artifacts").inc()
        return artifacts
    except Exception as e:
        registry_errors.labels(error_type="list_artifacts").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/conversation/{conversation_id}", response_model=List[ArtifactResponse])
async def list_artifacts_by_conversation(conversation_id: UUID4, db: Session = Depends(get_db)):
    """List artifacts for a specific Claude conversation"""
    start = time.time()
    try:
        artifacts = svc.list_artifacts_by_conversation(db, conversation_id)
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="list_artifacts_by_conversation").inc()
        return artifacts
    except Exception as e:
        registry_errors.labels(error_type="list_artifacts_by_conversation").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: UUID4, db: Session = Depends(get_db)):
    """Get a specific Claude artifact"""
    start = time.time()
    try:
        artifact = svc.get_artifact(db, artifact_id)
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
