"""CME pipeline service — pipeline run DB operations and progress tracking."""
from __future__ import annotations

import uuid
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from sqlalchemy import text

from models import CMEProject, CMEPipelineRun, CMEAgentOutput, CMEDocument, CMESourceReference
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


def list_outputs(db: Session, project_id: str) -> list[CMEAgentOutput]:
    return db.query(CMEAgentOutput).filter(CMEAgentOutput.project_id == project_id).all()


def get_output(db: Session, project_id: str, agent_name: str) -> CMEAgentOutput | None:
    return db.query(CMEAgentOutput).filter(
        CMEAgentOutput.project_id == project_id,
        CMEAgentOutput.agent_name == agent_name,
    ).first()


def handle_agent_complete(
    db: Session,
    project: CMEProject,
    agent_name: str,
    output: dict,
    quality_score: float | None,
    calculate_progress_fn,
) -> dict:
    """Process agent-complete webhook: create output, update project state."""
    now = datetime.utcnow()

    db_output = CMEAgentOutput(
        project_id=project.id,
        agent_name=agent_name,
        output_type=output.get("type", "document"),
        content=output,
        quality_score=quality_score,
    )
    db.add(db_output)

    agents_pending = list(project.agents_pending or [])
    agents_completed = list(project.agents_completed or [])

    if agent_name in agents_pending:
        agents_pending.remove(agent_name)
        agents_completed.append(agent_name)

    project.agents_pending = agents_pending
    project.agents_completed = agents_completed
    project.progress_percent = calculate_progress_fn(agents_completed)

    if agents_pending:
        project.current_agent = agents_pending[0]
    else:
        project.current_agent = None
        project.status = "complete"
        project.completed_at = now

    db.commit()
    return {
        "status": "received",
        "project_id": str(project.id),
        "agent": agent_name,
        "progress": project.progress_percent,
    }


def handle_pipeline_status(
    db: Session,
    project: CMEProject,
    pipeline_status: str,
    error_summary: str | None = None,
) -> dict:
    """Process pipeline-status webhook: update project status."""
    now = datetime.utcnow()

    if pipeline_status == "complete":
        project.status = "complete"
        project.completed_at = now
        project.current_agent = None
        project.progress_percent = 100
    elif pipeline_status == "failed":
        project.status = "failed"
        project.current_agent = None
        if error_summary:
            existing_errors = list(project.errors or [])
            existing_errors.append({"source": "pipeline", "message": error_summary, "timestamp": now.isoformat()})
            project.errors = existing_errors
    elif pipeline_status == "awaiting_review":
        project.status = "awaiting_review"
        project.current_agent = "human_review"
    else:
        project.status = pipeline_status
    db.commit()

    return {
        "status": "updated",
        "project_id": str(project.id),
        "pipeline_status": pipeline_status,
    }


def create_source_reference(
    db: Session,
    project: CMEProject,
    ref_data: dict,
    pub_date,
) -> tuple[str, str]:
    """Create source reference. Returns (id, status) — 'created' or 'already_exists'."""
    if ref_data.get("ref_id"):
        existing = db.query(CMESourceReference).filter(
            CMESourceReference.project_id == project.id,
            CMESourceReference.ref_id == ref_data["ref_id"],
        ).first()
        if existing:
            return str(existing.id), "already_exists"

    new_ref = CMESourceReference(
        project_id=project.id,
        document_id=uuid.UUID(ref_data["document_id"]) if ref_data.get("document_id") else None,
        ref_type=ref_data.get("ref_type", "pubmed"),
        ref_id=ref_data.get("ref_id"),
        title=ref_data.get("title", ""),
        authors=ref_data.get("authors", ""),
        journal=ref_data.get("journal", ""),
        publication_date=pub_date,
        url=ref_data.get("url", ""),
        abstract=ref_data.get("abstract", ""),
        cached_content=ref_data.get("cached_content"),
        verification_status=ref_data.get("verification_status"),
        verified_at=datetime.utcnow() if ref_data.get("verification_status") else None,
        verified_by=ref_data.get("verified_by"),
    )
    db.add(new_ref)
    db.flush()
    return str(new_ref.id), "created"


def create_agent_output(
    db: Session,
    project: CMEProject,
    req_data: dict,
) -> tuple[str, str]:
    """Create agent output. Returns (id, status) — 'created' or 'already_exists'."""
    existing = db.query(CMEAgentOutput).filter(
        CMEAgentOutput.project_id == project.id,
        CMEAgentOutput.agent_name == req_data["agent_name"],
    ).first()
    if existing:
        return str(existing.id), "already_exists"

    new_output = CMEAgentOutput(
        project_id=project.id,
        agent_name=req_data["agent_name"],
        output_type=req_data.get("output_type", "document"),
        content=req_data.get("content"),
        quality_score=req_data.get("quality_score"),
        document_text=req_data.get("document_text"),
        langsmith_trace_id=req_data.get("langsmith_trace_id"),
    )
    db.add(new_output)
    db.flush()
    return str(new_output.id), "created"


def create_document(
    db: Session,
    project: CMEProject,
    req_data: dict,
) -> tuple[str, int, str]:
    """Create immutable document version. Returns (id, version, status)."""
    current = db.query(CMEDocument).filter(
        CMEDocument.project_id == project.id,
        CMEDocument.document_type == req_data["document_type"],
        CMEDocument.is_current == True,
    ).first()

    new_version: int = 1
    if current:
        new_version = int(current.version) + 1
        current.is_current = False

    now = datetime.utcnow()
    new_doc = CMEDocument(
        project_id=project.id,
        agent_output_id=uuid.UUID(req_data["agent_output_id"]) if req_data.get("agent_output_id") else None,
        document_type=req_data["document_type"],
        version=new_version,
        is_current=True,
        title=req_data.get("title", ""),
        content_text=req_data["content_text"],
        content_html=req_data.get("content_html"),
        content_json=req_data.get("content_json"),
        word_count=req_data.get("word_count") or len(req_data["content_text"].split()),
        quality_score=req_data.get("quality_score"),
        quality_passed=req_data.get("quality_passed"),
        quality_details=req_data.get("quality_details"),
        source_references=req_data.get("source_references", []),
        created_by=req_data.get("created_by", "registry_agent"),
        retention_until=datetime(now.year + 7, now.month, now.day),
    )
    db.add(new_doc)
    db.flush()
    return str(new_doc.id), new_version, "created"


def save_embedding(table_name: str, record_id, embedding: list[float]) -> None:
    """Save embedding to a record. Uses its own session (for background tasks)."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        db.execute(
            text(f"UPDATE {table_name} SET embedding = CAST(:emb AS vector) WHERE id = :rid"),
            {"emb": f"[{','.join(str(v) for v in embedding)}]", "rid": str(record_id)},
        )
        db.commit()
    except Exception as exc:
        logger.error("Failed to save embedding for %s/%s: %s", table_name, record_id, exc)
        db.rollback()
    finally:
        db.close()
