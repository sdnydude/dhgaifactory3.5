"""
Claude AI Data Endpoints
Handles Claude projects, conversations, messages, and artifacts
"""
import time
import uuid
from typing import List, Optional, Union
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, UUID4

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from models import Project, Conversation, Message, Artifact

# Import metrics from main API
try:
    from api import registry_read_latency, registry_read_operations, registry_errors
except ImportError:
    # Fallback if running standalone
    from prometheus_client import Counter, Histogram
    registry_read_latency = Histogram('registry_read_latency', 'Read latency', buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000])
    registry_read_operations = Counter('registry_read_operations', 'Read operations', ['operation'])
    registry_errors = Counter('registry_errors', 'Registry errors', ['error_type'])


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


# =============================================================================
# PROJECT ENDPOINTS
# =============================================================================

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all Claude projects"""
    start = time.time()
    try:
        projects = db.query(Project).offset(skip).limit(limit).all()
        
        # Add conversation count
        result = []
        for project in projects:
            conv_count = db.query(Conversation).filter(Conversation.project_id == project.id).count()
            proj_dict = {
                'id': project.id,
                'name': project.name,
                'project_id': project.project_id,
                'description': project.description,
                'custom_instructions': project.custom_instructions,
                'knowledge_files': project.knowledge_files,
                'created_at': project.created_at,
                'updated_at': project.updated_at,
                'conversation_count': conv_count
            }
            result.append(ProjectResponse(**proj_dict))
        
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
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        conv_count = db.query(Conversation).filter(Conversation.project_id == project.id).count()
        proj_dict = {
            'id': project.id,
            'name': project.name,
            'project_id': project.project_id,
            'description': project.description,
            'custom_instructions': project.custom_instructions,
            'knowledge_files': project.knowledge_files,
            'created_at': project.created_at,
            'updated_at': project.updated_at,
            'conversation_count': conv_count
        }
        
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="get_project").inc()
        return ProjectResponse(**proj_dict)
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
        query = db.query(Conversation)
        
        if project_id:
            query = query.filter(Conversation.project_id == project_id)
        if export_source:
            query = query.filter(Conversation.export_source == export_source)
        
        conversations = query.order_by(Conversation.created_at.desc()).offset(skip).limit(limit).all()
        
        # Add counts
        result = []
        for conv in conversations:
            msg_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
            art_count = db.query(Artifact).filter(Artifact.conversation_id == conv.id).count()
            conv_dict = {
                'id': conv.id,
                'title': conv.title,
                'conversation_id': conv.conversation_id,
                'export_source': conv.export_source,
                'model_name': conv.model_name,
                'project_id': conv.project_id,
                'created_at': conv.created_at,
                'updated_at': conv.updated_at,
                'message_count': msg_count,
                'artifact_count': art_count
            }
            result.append(ConversationResponse(**conv_dict))
        
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
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        msg_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
        art_count = db.query(Artifact).filter(Artifact.conversation_id == conv.id).count()
        conv_dict = {
            'id': conv.id,
            'title': conv.title,
            'conversation_id': conv.conversation_id,
            'export_source': conv.export_source,
            'model_name': conv.model_name,
            'project_id': conv.project_id,
            'created_at': conv.created_at,
            'updated_at': conv.updated_at,
            'message_count': msg_count,
            'artifact_count': art_count
        }
        
        registry_read_latency.observe((time.time() - start) * 1000)
        registry_read_operations.labels(operation="get_conversation").inc()
        return ConversationResponse(**conv_dict)
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
        # Search in conversation titles
        conversations = db.query(Conversation).filter(
            Conversation.title.ilike(f'%{q}%')
        ).order_by(Conversation.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for conv in conversations:
            msg_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
            art_count = db.query(Artifact).filter(Artifact.conversation_id == conv.id).count()
            conv_dict = {
                'id': conv.id,
                'title': conv.title,
                'conversation_id': conv.conversation_id,
                'export_source': conv.export_source,
                'model_name': conv.model_name,
                'project_id': conv.project_id,
                'created_at': conv.created_at,
                'updated_at': conv.updated_at,
                'message_count': msg_count,
                'artifact_count': art_count
            }
            result.append(conv_dict)
        
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
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.message_index).all()
        
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
        query = db.query(Artifact)
        
        if artifact_type:
            query = query.filter(Artifact.artifact_type == artifact_type)
        
        artifacts = query.order_by(Artifact.created_at.desc()).offset(skip).limit(limit).all()
        
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
        artifacts = db.query(Artifact).filter(
            Artifact.conversation_id == conversation_id
        ).order_by(Artifact.created_at).all()
        
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
        artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
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
