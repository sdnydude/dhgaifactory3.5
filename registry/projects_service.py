"""CME project list service — DB operations for the inbox Files tab."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import CMEDocument, CMEProject


def list_projects(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[tuple], int]:
    """Return (rows, total) where each row is (CMEProject, doc_count, last_activity)."""
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
    return rows, total


def get_project(db: Session, project_id: UUID) -> CMEProject | None:
    return db.query(CMEProject).filter(CMEProject.id == project_id).first()


def list_project_documents(db: Session, project_id: UUID) -> list[CMEDocument]:
    """Return current documents for a project, ordered by type then version desc."""
    return (
        db.query(CMEDocument)
        .filter(
            CMEDocument.project_id == project_id,
            CMEDocument.is_current.is_(True),
        )
        .order_by(CMEDocument.document_type, CMEDocument.version.desc())
        .all()
    )
