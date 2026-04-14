"""Project list + project documents endpoints for the inbox Files tab.

These live under /api/cme/export/* (Files tab = export browser).
Do NOT mount under /api/cme/projects — that collides with the existing
CME admin projects endpoint in cme_endpoints.py.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import CMEDocument, CMEProject
from project_schemas import (
    ProjectDocumentItem,
    ProjectDocumentsResponse,
    ProjectListItem,
    ProjectListResponse,
)

router = APIRouter(prefix="/api/cme/export/projects", tags=["cme-export"])


@router.get("", response_model=ProjectListResponse)
def list_projects(
    search: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> ProjectListResponse:
    doc_count_sq = (
        db.query(
            CMEDocument.project_id.label("pid"),
            func.count(CMEDocument.id).label("cnt"),
            func.max(CMEDocument.created_at).label("last_activity"),
        )
        .filter(CMEDocument.is_current.is_(True))
        .group_by(CMEDocument.project_id)
        .subquery()
    )

    q = db.query(
        CMEProject,
        func.coalesce(doc_count_sq.c.cnt, 0).label("cnt"),
        doc_count_sq.c.last_activity,
    ).outerjoin(doc_count_sq, CMEProject.id == doc_count_sq.c.pid)

    if search:
        term = f"%{search.strip()}%"
        q = q.filter(CMEProject.name.ilike(term))
    if status:
        q = q.filter(CMEProject.status == status)

    total = q.count()
    rows = (
        q.order_by(CMEProject.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    projects = [
        ProjectListItem(
            id=row[0].id,
            name=row[0].name,
            status=row[0].status,
            kind=getattr(row[0], "kind", None),
            document_count=int(row[1]),
            last_activity_at=row[2],
            drive_folder_id=row[0].drive_folder_id,
        )
        for row in rows
    ]
    return ProjectListResponse(
        projects=projects, total=total, limit=limit, offset=offset
    )


@router.get("/{project_id}/documents", response_model=ProjectDocumentsResponse)
def list_project_documents(
    project_id: UUID,
    db: Session = Depends(get_db),
) -> ProjectDocumentsResponse:
    project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    docs = (
        db.query(CMEDocument)
        .filter(
            CMEDocument.project_id == project_id,
            CMEDocument.is_current.is_(True),
        )
        .order_by(CMEDocument.document_type, CMEDocument.version.desc())
        .all()
    )

    items = [
        ProjectDocumentItem(
            id=d.id,
            document_type=d.document_type,
            title=d.title,
            word_count=d.word_count,
            version=d.version,
            is_current=d.is_current,
            created_at=d.created_at,
            drive_file_id=d.drive_file_id,
        )
        for d in docs
    ]
    return ProjectDocumentsResponse(project_id=project_id, documents=items)
