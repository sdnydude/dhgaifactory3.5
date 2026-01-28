"""
Research Request Endpoints for AI Factory Registry
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
import uuid

from database import get_db
from models import ResearchRequest
from schemas import (
    ResearchRequestCreate,
    ResearchRequestUpdate,
    ResearchRequestResponse,
    ResearchRequestListResponse
)

router = APIRouter(prefix="/api/v1/research", tags=["Research Requests"])


@router.post("/requests", response_model=ResearchRequestResponse, status_code=201)
async def create_research_request(
    request: ResearchRequestCreate,
    db: Session = Depends(get_db)
):
    """Create a new research request"""
    
    # Generate request ID
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    
    # Create database record
    db_request = ResearchRequest(
        request_id=request_id,
        user_id=request.user_id,
        agent_type=request.agent_type,
        status="pending",
        input_params=request.input_params.dict(),
        created_at=datetime.utcnow()
    )
    
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    
    return db_request


@router.get("/requests/{request_id}", response_model=ResearchRequestResponse)
async def get_research_request(
    request_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific research request"""
    
    db_request = db.query(ResearchRequest).filter(
        ResearchRequest.request_id == request_id
    ).first()
    
    if not db_request:
        raise HTTPException(status_code=404, detail="Research request not found")
    
    return db_request


@router.get("/requests", response_model=ResearchRequestListResponse)
async def list_research_requests(
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    agent_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List research requests with filtering and pagination"""
    
    # Build query
    query = db.query(ResearchRequest)
    
    if user_id:
        query = query.filter(ResearchRequest.user_id == user_id)
    if status:
        query = query.filter(ResearchRequest.status == status)
    if agent_type:
        query = query.filter(ResearchRequest.agent_type == agent_type)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    requests = query.order_by(desc(ResearchRequest.created_at)).offset(offset).limit(page_size).all()
    
    return {
        "requests": requests,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.patch("/requests/{request_id}", response_model=ResearchRequestResponse)
async def update_research_request(
    request_id: str,
    update: ResearchRequestUpdate,
    db: Session = Depends(get_db)
):
    """Update a research request (status, results, metadata)"""
    
    db_request = db.query(ResearchRequest).filter(
        ResearchRequest.request_id == request_id
    ).first()
    
    if not db_request:
        raise HTTPException(status_code=404, detail="Research request not found")
    
    # Update fields
    update_data = update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "output_summary" and value:
            setattr(db_request, field, value.dict())
        elif field == "processing_metadata" and value:
            setattr(db_request, field, value.dict())
        else:
            setattr(db_request, field, value)
    
    # Set started_at if status changed to running
    if update.status == "running" and not db_request.started_at:
        db_request.started_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_request)
    
    return db_request


@router.delete("/requests/{request_id}", status_code=204)
async def delete_research_request(
    request_id: str,
    db: Session = Depends(get_db)
):
    """Delete a research request"""
    
    db_request = db.query(ResearchRequest).filter(
        ResearchRequest.request_id == request_id
    ).first()
    
    if not db_request:
        raise HTTPException(status_code=404, detail="Research request not found")
    
    db.delete(db_request)
    db.commit()
    
    return None
