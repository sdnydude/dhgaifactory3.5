"""
Research Request Endpoints for AI Factory Registry
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from schemas import (
    ResearchRequestCreate,
    ResearchRequestUpdate,
    ResearchRequestResponse,
    ResearchRequestListResponse
)
import research_service as svc

router = APIRouter(prefix="/api/v1/research", tags=["Research Requests"])


@router.post("/requests", response_model=ResearchRequestResponse, status_code=201)
async def create_research_request(
    request: ResearchRequestCreate,
    db: Session = Depends(get_db)
):
    data = {
        "user_id": request.user_id,
        "agent_type": request.agent_type,
        "input_params": request.input_params.dict(),
    }
    return svc.create_research_request(db, data)


@router.get("/requests/{request_id}", response_model=ResearchRequestResponse)
async def get_research_request(
    request_id: str,
    db: Session = Depends(get_db)
):
    row = svc.get_research_request(db, request_id)
    if not row:
        raise HTTPException(status_code=404, detail="Research request not found")
    return row


@router.get("/requests", response_model=ResearchRequestListResponse)
async def list_research_requests(
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    agent_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    rows, total = svc.list_research_requests(
        db, user_id=user_id, status=status, agent_type=agent_type,
        page=page, page_size=page_size,
    )
    return {
        "requests": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.patch("/requests/{request_id}", response_model=ResearchRequestResponse)
async def update_research_request(
    request_id: str,
    update: ResearchRequestUpdate,
    db: Session = Depends(get_db)
):
    update_data = update.dict(exclude_unset=True)
    row = svc.update_research_request(db, request_id, update_data)
    if not row:
        raise HTTPException(status_code=404, detail="Research request not found")
    return row


@router.delete("/requests/{request_id}", status_code=204)
async def delete_research_request(
    request_id: str,
    db: Session = Depends(get_db)
):
    row = svc.delete_research_request(db, request_id)
    if not row:
        raise HTTPException(status_code=404, detail="Research request not found")
    return None
