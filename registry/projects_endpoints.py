"""Project list + project documents endpoints for the inbox Files tab.

These live under /api/cme/export/* (Files tab = export browser).
Do NOT mount under /api/cme/projects — that collides with the existing
CME admin projects endpoint in cme_endpoints.py.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
import projects_service as svc
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
    rows, total = svc.list_projects(db, search=search, status=status, limit=limit, offset=offset)
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
    project = svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    docs = svc.list_project_documents(db, project_id)
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
