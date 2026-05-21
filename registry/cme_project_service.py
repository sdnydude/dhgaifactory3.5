"""CME project service — CRUD and status operations for CME projects."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session
from sqlalchemy import select

from models import CMEProject, CMEDocument, CMEIntakeField

logger = logging.getLogger(__name__)

INITIAL_AGENTS_PENDING = [
    "research", "clinical", "gap_analysis", "needs_assessment",
    "learning_objectives", "curriculum", "protocol", "marketing",
    "grant_writer", "prose_quality", "compliance", "package_assembly",
]


def create_project(db: Session, name: str, intake_dict: dict) -> CMEProject:
    project = CMEProject(
        name=name,
        status="intake",
        intake=intake_dict,
        current_agent=None,
        progress_percent=0,
        outputs={},
        errors=[],
        human_review_status=None,
        pipeline_thread_id=None,
        agents_completed=[],
        agents_pending=list(INITIAL_AGENTS_PENDING),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_projects(
    db: Session,
    *,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[CMEProject]:
    query = db.query(CMEProject)
    if status_filter:
        query = query.filter(CMEProject.status == status_filter)
    else:
        query = query.filter(CMEProject.status != "archived")
    return query.order_by(CMEProject.created_at.desc()).offset(skip).limit(limit).all()


def get_project(db: Session, project_id: str) -> CMEProject | None:
    return db.query(CMEProject).filter(CMEProject.id == project_id).first()


def update_project_intake(
    db: Session,
    project: CMEProject,
    name: str,
    intake_dict: dict,
    extract_intake_fields_fn=None,
) -> CMEProject:
    """Update intake data. Caller must validate status beforehand."""
    project.name = name
    project.intake = intake_dict
    if project.status != "intake":
        project.intake_version = (project.intake_version or 1) + 1

    if extract_intake_fields_fn:
        db.query(CMEIntakeField).filter(
            CMEIntakeField.project_id == project.id,
        ).delete()
        extract_intake_fields_fn(project.id, intake_dict, db)

    db.commit()
    db.refresh(project)
    return project


def archive_project(db: Session, project: CMEProject) -> CMEProject:
    project.status = "archived"
    db.commit()
    db.refresh(project)
    return project


def set_project_status(db: Session, project: CMEProject, new_status: str) -> CMEProject:
    project.status = new_status
    db.commit()
    db.refresh(project)
    return project


def fetch_latest_document_for_thread(thread_id: str) -> dict | None:
    """Return the latest CMEDocument for a pipeline thread.

    Creates its own session — used by export endpoints outside request context.
    """
    from database import SessionLocal

    with SessionLocal() as session:
        stmt = (
            select(CMEDocument, CMEProject)
            .join(CMEProject, CMEDocument.project_id == CMEProject.id)
            .where(CMEProject.pipeline_thread_id == thread_id)
            .order_by(CMEDocument.created_at.desc())
            .limit(1)
        )
        row = session.execute(stmt).first()
        if not row:
            return None
        doc, project = row
        quality_details = doc.quality_details or {}
        review_round = 0
        if isinstance(quality_details, dict):
            try:
                review_round = int(quality_details.get("review_round", 0) or 0)
            except (TypeError, ValueError):
                review_round = 0
        return {
            "title": project.name,
            "graph_label": doc.document_type or "CME Document",
            "review_round": review_round,
            "document_text": doc.content_text or "",
        }
