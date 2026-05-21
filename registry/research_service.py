"""Research Requests service layer — all database operations for research."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models import ResearchRequest

logger = logging.getLogger(__name__)


def create_research_request(
    db: Session, data: dict,
) -> ResearchRequest:
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    row = ResearchRequest(
        request_id=request_id,
        user_id=data["user_id"],
        agent_type=data["agent_type"],
        status="pending",
        input_params=data["input_params"],
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_research_request(db: Session, request_id: str) -> ResearchRequest | None:
    return db.query(ResearchRequest).filter(
        ResearchRequest.request_id == request_id,
    ).first()


def list_research_requests(
    db: Session,
    *,
    user_id: str | None = None,
    status: str | None = None,
    agent_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[ResearchRequest], int]:
    query = db.query(ResearchRequest)
    if user_id:
        query = query.filter(ResearchRequest.user_id == user_id)
    if status:
        query = query.filter(ResearchRequest.status == status)
    if agent_type:
        query = query.filter(ResearchRequest.agent_type == agent_type)

    total = query.count()
    offset = (page - 1) * page_size
    rows = query.order_by(desc(ResearchRequest.created_at)).offset(offset).limit(page_size).all()
    return rows, total


def update_research_request(
    db: Session, request_id: str, update_data: dict,
) -> ResearchRequest | None:
    """Update a research request. Returns None if not found."""
    row = db.query(ResearchRequest).filter(
        ResearchRequest.request_id == request_id,
    ).first()
    if not row:
        return None

    for field, value in update_data.items():
        if field == "output_summary" and value:
            setattr(row, field, value.dict() if hasattr(value, "dict") else value)
        elif field == "processing_metadata" and value:
            setattr(row, field, value.dict() if hasattr(value, "dict") else value)
        else:
            setattr(row, field, value)

    if update_data.get("status") == "running" and not row.started_at:
        row.started_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    return row


def delete_research_request(db: Session, request_id: str) -> ResearchRequest | None:
    row = db.query(ResearchRequest).filter(
        ResearchRequest.request_id == request_id,
    ).first()
    if not row:
        return None
    db.delete(row)
    db.commit()
    return row
