"""CME pipeline service — pipeline run DB operations and progress tracking."""
from __future__ import annotations

import uuid
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import CMEProject, CMEPipelineRun
from schemas import PipelineRunRead

logger = logging.getLogger(__name__)


def pipeline_run_to_read(run: CMEPipelineRun) -> PipelineRunRead:
    duration: float | None = None
    if run.completed_at and run.triggered_at:
        duration = (run.completed_at - run.triggered_at).total_seconds()
    return PipelineRunRead(
        run_id=run.run_id,
        project_id=run.project_id,
        run_number=run.run_number,
        thread_id=run.thread_id,
        langgraph_run_id=run.langgraph_run_id,
        intake_version_used=run.intake_version_used,
        triggered_by=run.triggered_by,
        trigger_reason=run.trigger_reason,
        triggered_at=run.triggered_at,
        completed_at=run.completed_at,
        status=run.status,
        error_message=run.error_message,
        final_agent=run.final_agent,
        reason=run.reason,
        duration_seconds=duration,
    )


def start_pipeline(
    db: Session,
    project: CMEProject,
    thread_id: str,
    run_id: str,
) -> CMEPipelineRun:
    now = datetime.utcnow()
    project.status = "processing"
    project.started_at = now
    project.current_agent = "research"
    project.pipeline_thread_id = thread_id

    last_run_number = (
        db.query(func.max(CMEPipelineRun.run_number))
        .filter(CMEPipelineRun.project_id == project.id)
        .scalar()
        or 0
    )
    run = CMEPipelineRun(
        run_id=uuid.uuid4(),
        project_id=project.id,
        run_number=last_run_number + 1,
        thread_id=thread_id,
        langgraph_run_id=run_id,
        intake_version_used=project.intake_version or 1,
        trigger_reason="initial" if last_run_number == 0 else "retry",
        triggered_at=now,
        status="processing",
    )
    db.add(run)
    db.flush()
    project.current_run_id = run.run_id

    db.commit()
    db.refresh(project)
    db.refresh(run)
    return run


def cancel_pipeline(
    db: Session,
    project: CMEProject,
    run: CMEPipelineRun,
) -> CMEPipelineRun:
    now = datetime.utcnow()
    run.status = "cancelled"
    run.completed_at = now
    run.final_agent = project.current_agent
    project.status = "cancelled"
    project.completed_at = now
    db.commit()
    db.refresh(run)
    return run


def rerun_pipeline(
    db: Session,
    project: CMEProject,
    thread_id: str,
    run_id: str,
    reason: str | None = None,
    prev_run: CMEPipelineRun | None = None,
) -> CMEPipelineRun:
    if prev_run and prev_run.status == "processing":
        prev_run.status = "cancelled"
        prev_run.completed_at = datetime.utcnow()
        prev_run.reason = "superseded by rerun"

    last_run_number = (
        db.query(func.max(CMEPipelineRun.run_number))
        .filter(CMEPipelineRun.project_id == project.id)
        .scalar()
        or 0
    )
    now = datetime.utcnow()
    run = CMEPipelineRun(
        run_id=uuid.uuid4(),
        project_id=project.id,
        run_number=last_run_number + 1,
        thread_id=thread_id,
        langgraph_run_id=run_id,
        intake_version_used=project.intake_version or 1,
        trigger_reason="manual",
        triggered_at=now,
        status="processing",
        reason=reason,
    )
    db.add(run)
    db.flush()

    project.status = "processing"
    project.started_at = now
    project.completed_at = None
    project.current_agent = "research"
    project.pipeline_thread_id = thread_id
    project.current_run_id = run.run_id
    project.agents_completed = []
    project.errors = []

    db.commit()
    db.refresh(run)
    return run


def get_active_run(db: Session, project: CMEProject) -> CMEPipelineRun | None:
    if not project.current_run_id:
        return None
    return db.query(CMEPipelineRun).filter(
        CMEPipelineRun.run_id == project.current_run_id,
    ).first()


def list_runs(db: Session, project_id: str) -> list[CMEPipelineRun]:
    return (
        db.query(CMEPipelineRun)
        .filter(CMEPipelineRun.project_id == project_id)
        .order_by(CMEPipelineRun.run_number.desc())
        .all()
    )
