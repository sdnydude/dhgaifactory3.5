"""Webhook service layer — database operations for CME webhook endpoints."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from models import CMEProject, DownloadJob

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = ("pending", "running")


def get_project(db: Session, project_id: UUID) -> CMEProject | None:
    return db.query(CMEProject).filter(CMEProject.id == project_id).first()


def find_active_drive_sync(db: Session, project_id: UUID) -> DownloadJob | None:
    return (
        db.query(DownloadJob)
        .filter(
            DownloadJob.project_id == project_id,
            DownloadJob.scope == "drive_sync",
            DownloadJob.status.in_(_ACTIVE_STATUSES),
        )
        .order_by(DownloadJob.created_at.desc())
        .first()
    )


def enqueue_drive_sync_job(
    db: Session, project: CMEProject, milestone: str,
) -> DownloadJob:
    job = DownloadJob(
        thread_id=project.pipeline_thread_id or "",
        graph_id="drive_sync",
        scope="drive_sync",
        status="pending",
        project_id=project.id,
        created_by=f"webhook:{milestone}",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
