"""
CME Grant Intake API Endpoints
Handles CME project creation, pipeline execution, and status tracking
Uses /api/v2/ prefix for CME-specific endpoints
"""
import time
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import httpx
import logging

logger = logging.getLogger("uvicorn.error")

from database import get_db
from schemas import (
    PipelineRunRead, RerunRequest, PipelineRunListResponse,
)
from cme_schemas import (
    CMEProjectStatus, IntakeSubmission, PrefillRequest,
    CMEProjectCreateResponse, CMEProjectDetail, ExecutionStatus, AgentOutput,
)
import cme_project_service as project_svc
import cme_pipeline_service as pipeline_svc
import cme_review_service as review_svc
import cme_sync_service as sync_svc
import cme_search_service as search_svc

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/cme", tags=["cme"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

LANGGRAPH_CLOUD_URL = "https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app"


async def trigger_langgraph_pipeline(project_id: str, intake_data: dict) -> dict:
    """
    Trigger the LangGraph CME pipeline via the LangGraph Cloud REST API.
    Creates a thread, then starts a run with the grant_package assistant
    (full 11-agent pipeline with 2 prose QA passes + compliance gate).
    Returns {"thread_id": ..., "run_id": ...} for tracking.
    """
    langgraph_url = os.getenv("LANGGRAPH_API_URL", LANGGRAPH_CLOUD_URL)
    langchain_api_key = os.getenv("LANGCHAIN_API_KEY", "")
    headers = {"x-api-key": langchain_api_key}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            thread_resp = await client.post(
                f"{langgraph_url}/threads",
                json={"metadata": {"graph_id": "grant_package", "project_id": project_id}},
                headers=headers,
            )
            thread_resp.raise_for_status()
            thread_id = thread_resp.json()["thread_id"]

            run_resp = await client.post(
                f"{langgraph_url}/threads/{thread_id}/runs",
                json={
                    "assistant_id": "grant_package",
                    "input": {
                        "intake_data": intake_data,
                        "project_id": project_id,
                    },
                },
                headers=headers,
            )
            run_resp.raise_for_status()
            run_id = run_resp.json()["run_id"]
            logger.info(
                f"LangGraph pipeline started: thread={thread_id}, run={run_id}, project={project_id}"
            )
            return {"thread_id": thread_id, "run_id": run_id}
    except Exception as e:
        logger.error(f"Failed to start LangGraph pipeline for project {project_id}: {e}")
        raise


async def cancel_langgraph_run(thread_id: str, run_id: str) -> bool:
    """
    Cancel a running LangGraph run via the Cloud API.
    Tolerates 404 (run already finished). Returns True if cancel succeeded or
    the run was already gone; False on other failures.
    """
    langgraph_url = os.getenv("LANGGRAPH_API_URL", LANGGRAPH_CLOUD_URL)
    langchain_api_key = os.getenv("LANGCHAIN_API_KEY", "")
    headers = {"x-api-key": langchain_api_key}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{langgraph_url}/threads/{thread_id}/runs/{run_id}/cancel",
                headers=headers,
            )
            if resp.status_code == 404:
                logger.info(f"LangGraph run already finished: thread={thread_id}, run={run_id}")
                return True
            resp.raise_for_status()
            logger.info(f"LangGraph run cancelled: thread={thread_id}, run={run_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to cancel LangGraph run thread={thread_id} run={run_id}: {e}")
        return False


async def trigger_intake_prefill(payload: dict) -> dict:
    """
    Invoke the intake_prefill graph on LangGraph Cloud and wait for result.
    Uses the /runs/wait endpoint to block until completion (90s timeout).
    """
    langgraph_url = os.getenv("LANGGRAPH_API_URL", LANGGRAPH_CLOUD_URL)
    langchain_api_key = os.getenv("LANGCHAIN_API_KEY", "")
    headers = {"x-api-key": langchain_api_key}

    async with httpx.AsyncClient(timeout=90.0) as client:
        # Create a thread
        thread_resp = await client.post(
            f"{langgraph_url}/threads",
            json={"metadata": {"graph_id": "intake_prefill"}},
            headers=headers,
        )
        thread_resp.raise_for_status()
        thread_id = thread_resp.json()["thread_id"]

        # Start a run and wait for completion
        run_resp = await client.post(
            f"{langgraph_url}/threads/{thread_id}/runs/wait",
            json={
                "assistant_id": "intake_prefill",
                "input": payload,
            },
            headers=headers,
            timeout=90.0,
        )
        run_resp.raise_for_status()
        result = run_resp.json()

        return {
            "prefill_sections": result.get("prefill_sections", {}),
            "research_summary": result.get("research_summary", ""),
            "confidence": result.get("confidence", {}),
        }


async def _fetch_thread_from_cloud(thread_id: str) -> Optional[Dict[str, Any]]:
    """Fetch thread info and state from LangGraph Cloud."""
    langgraph_url = os.getenv("LANGGRAPH_API_URL", LANGGRAPH_CLOUD_URL)
    langchain_api_key = os.getenv("LANGCHAIN_API_KEY", "")
    headers = {"x-api-key": langchain_api_key}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            thread_resp = await client.get(
                f"{langgraph_url}/threads/{thread_id}",
                headers=headers,
            )
            thread_resp.raise_for_status()
            thread_info = thread_resp.json()

            state_resp = await client.get(
                f"{langgraph_url}/threads/{thread_id}/state",
                headers=headers,
            )
            state_resp.raise_for_status()
            thread_state = state_resp.json()

            return {"thread": thread_info, "state": thread_state}
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching thread {thread_id} from Cloud (15s)")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {e.response.status_code} fetching thread {thread_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch thread {thread_id} from Cloud: {type(e).__name__}: {e}")
        return None


# =============================================================================
# SYNC ENDPOINTS
# =============================================================================

@router.post("/projects/{project_id}/sync")
async def sync_project_from_cloud(project_id: str, db: Session = Depends(get_db)):
    """Poll LangGraph Cloud for thread state and sync to registry database."""
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")

    if not project.pipeline_thread_id:
        raise HTTPException(status_code=400, detail="No pipeline thread ID — pipeline not started")

    thread_data = await _fetch_thread_from_cloud(project.pipeline_thread_id)
    if not thread_data:
        raise HTTPException(status_code=502, detail="Failed to fetch thread from LangGraph Cloud")

    return await sync_svc.sync_project_from_thread(project, thread_data, db)


@router.post("/sync-active")
async def sync_all_active_projects(db: Session = Depends(get_db)):
    """Sync all processing/review projects from LangGraph Cloud. Call on interval or on-demand."""
    projects = project_svc.list_active_syncable(db)

    results = []
    for project in projects:
        try:
            thread_data = await _fetch_thread_from_cloud(project.pipeline_thread_id)
            if thread_data:
                result = await sync_svc.sync_project_from_thread(project, thread_data, db)
                results.append(result)
            else:
                results.append({"project_id": str(project.id), "error": "cloud_unreachable"})
        except Exception as e:
            logger.error(f"sync failed for project {project.id}: {e}")
            results.append({"project_id": str(project.id), "error": str(e)})

    return {"synced": len(results), "results": results}


@router.post("/intake/prefill")
async def prefill_intake(request: PrefillRequest):
    """
    AI-powered prefill for CME intake sections B-H.
    Takes Section A fields, queries PubMed, generates structured drafts.
    """
    payload = {
        "project_name": request.project_name,
        "therapeutic_area": request.therapeutic_area,
        "disease_state": request.disease_state,
        "target_audience_primary": request.target_audience_primary,
        "target_hcp_types": request.target_hcp_types or [],
        "additional_context": request.additional_context or "",
    }
    try:
        result = await trigger_intake_prefill(payload)
        return result
    except Exception as e:
        logger.error("Intake prefill failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Prefill unavailable — the AI agent could not complete the request.",
        )


# =============================================================================
# PROJECT ENDPOINTS
# =============================================================================

@router.post("/projects", response_model=CMEProjectCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_cme_project(
    intake: IntakeSubmission,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new CME project by submitting the 47-field intake form.
    This stores the project and prepares it for pipeline execution.
    """
    start = time.time()
    try:
        intake_dict = intake.model_dump(mode='json')
        db_project = project_svc.create_project(db, intake.section_a.project_name, intake_dict)

        registry_write_operations.labels(operation="create_cme_project").inc()
        registry_write_latency.observe((time.time() - start) * 1000)

        return CMEProjectCreateResponse(
            project_id=str(db_project.id),
            status=CMEProjectStatus.INTAKE,
            message=f"CME project '{intake.section_a.project_name}' created successfully",
            created_at=db_project.created_at
        )

    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_cme_project").inc()
        logger.exception("create_cme_project failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/projects", response_model=List[CMEProjectDetail])
async def list_cme_projects(
    skip: int = 0,
    limit: int = 100,
    status: Optional[CMEProjectStatus] = None,
    db: Session = Depends(get_db)
):
    """List all CME projects with optional status filtering"""
    start = time.time()
    try:
        projects = project_svc.list_projects(
            db,
            status_filter=status.value if status else None,
            skip=skip,
            limit=limit,
        )

        result = [
            CMEProjectDetail(
                id=str(p.id),
                name=p.name,
                status=CMEProjectStatus(p.status),
                current_agent=p.current_agent,
                progress_percent=p.progress_percent or 0,
                intake=p.intake,
                intake_version=p.intake_version or 1,
                created_at=p.created_at,
                updated_at=p.updated_at,
                outputs_available=list(p.outputs.keys()) if p.outputs else [],
                human_review_status=p.human_review_status
            )
            for p in projects
        ]

        registry_read_operations.labels(operation="list_cme_projects").inc()
        registry_read_latency.observe((time.time() - start) * 1000)

        return result

    except Exception as e:
        registry_errors.labels(error_type="list_cme_projects").inc()
        logger.exception("list_cme_projects failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/projects/{project_id}", response_model=CMEProjectDetail)
async def get_cme_project(project_id: str, db: Session = Depends(get_db)):
    """Get details for a specific CME project"""
    start = time.time()
    try:
        p = project_svc.get_project(db, project_id)
        if not p:
            raise HTTPException(status_code=404, detail="CME project not found")

        registry_read_operations.labels(operation="get_cme_project").inc()
        registry_read_latency.observe((time.time() - start) * 1000)

        return CMEProjectDetail(
            id=str(p.id),
            name=p.name,
            status=CMEProjectStatus(p.status),
            current_agent=p.current_agent,
            progress_percent=p.progress_percent or 0,
            intake=p.intake,
            intake_version=p.intake_version or 1,
            created_at=p.created_at,
            updated_at=p.updated_at,
            outputs_available=list(p.outputs.keys()) if p.outputs else [],
            human_review_status=p.human_review_status
        )

    except HTTPException:
        raise
    except Exception as e:
        registry_errors.labels(error_type="get_cme_project").inc()
        logger.exception("get_cme_project failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/projects/{project_id}", response_model=CMEProjectDetail)
async def update_cme_project(
    project_id: str,
    intake: IntakeSubmission,
    db: Session = Depends(get_db),
):
    """Update the intake data for a CME project.

    Allowed in any status except 'processing' (run in flight — would race with
    the running pipeline) and 'archived' (read-only). For projects that have
    already been run (complete/cancelled/failed), saving bumps intake_version
    so the next /rerun starts from the new intake while existing run history
    keeps its intake_version_used snapshot.
    """
    start = time.time()
    try:
        project = project_svc.get_project(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="CME project not found")

        if project.status in ("processing", "archived"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot edit: project status is '{project.status}'. Cancel the run or unarchive the project first.",
            )

        intake_dict = intake.model_dump(mode="json")
        project = project_svc.update_project_intake(
            db, project, intake.section_a.project_name, intake_dict,
            extract_intake_fields_fn=sync_svc.extract_intake_fields,
        )

        registry_write_operations.labels(operation="update_cme_project").inc()
        registry_write_latency.observe((time.time() - start) * 1000)

        return CMEProjectDetail(
            id=str(project.id),
            name=project.name,
            status=CMEProjectStatus(project.status),
            current_agent=project.current_agent,
            progress_percent=project.progress_percent or 0,
            intake=project.intake,
            intake_version=project.intake_version or 1,
            created_at=project.created_at,
            updated_at=project.updated_at,
            outputs_available=list(project.outputs.keys()) if project.outputs else [],
            human_review_status=project.human_review_status,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="update_cme_project").inc()
        logger.exception("update_cme_project failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/projects/{project_id}/archive")
async def archive_cme_project(project_id: str, db: Session = Depends(get_db)):
    """Archive a CME project (soft delete). Can be called on any non-archived project."""
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")

    if project.status == "archived":
        raise HTTPException(status_code=400, detail="Project is already archived")

    project_svc.archive_project(db, project)
    return {"status": "archived", "project_id": str(project.id)}


# =============================================================================
# PIPELINE CONTROL ENDPOINTS
# =============================================================================

@router.post("/projects/{project_id}/start", response_model=ExecutionStatus)
async def start_cme_pipeline(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start the 12-agent LangGraph pipeline for a CME project"""
    start = time.time()
    try:
        project = project_svc.get_project(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="CME project not found")

        if project.status not in ["intake", "failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot start pipeline: project status is {project.status}"
            )

        lg = await trigger_langgraph_pipeline(str(project.id), project.intake)
        pipeline_svc.start_pipeline(db, project, lg["thread_id"], lg["run_id"])

        registry_write_operations.labels(operation="start_cme_pipeline").inc()
        registry_write_latency.observe((time.time() - start) * 1000)

        return ExecutionStatus(
            project_id=str(project.id),
            status=CMEProjectStatus(project.status),
            current_agent=project.current_agent,
            progress_percent=project.progress_percent or 0,
            agents_completed=project.agents_completed or [],
            agents_pending=project.agents_pending or [],
            errors=project.errors or [],
            started_at=project.started_at,
            estimated_completion=None
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="start_cme_pipeline").inc()
        logger.exception("start_cme_pipeline failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/projects/{project_id}/status", response_model=ExecutionStatus)
async def get_cme_pipeline_status(project_id: str, db: Session = Depends(get_db)):
    """Get current execution status of the CME pipeline.

    Auto-syncs from LangGraph Cloud when project is processing/review.
    """
    start = time.time()
    try:
        project = project_svc.get_project(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="CME project not found")

        if project.status in ("processing", "review") and project.pipeline_thread_id:
            try:
                thread_data = await _fetch_thread_from_cloud(project.pipeline_thread_id)
                if thread_data:
                    await sync_svc.sync_project_from_thread(project, thread_data, db)
            except Exception as sync_err:
                logger.warning(f"Cloud sync failed during status poll: {sync_err}")
        else:
            logger.info(
                "auto-sync skipped for %s: status=%s thread_id=%s",
                project_id, project.status, project.pipeline_thread_id,
            )

        registry_read_operations.labels(operation="get_cme_pipeline_status").inc()
        registry_read_latency.observe((time.time() - start) * 1000)

        return ExecutionStatus(
            project_id=str(project.id),
            status=CMEProjectStatus(project.status),
            current_agent=project.current_agent,
            progress_percent=project.progress_percent or 0,
            agents_completed=project.agents_completed or [],
            agents_pending=project.agents_pending or [],
            errors=project.errors or [],
            started_at=project.started_at,
            estimated_completion=None
        )

    except HTTPException:
        raise
    except Exception as e:
        registry_errors.labels(error_type="get_cme_pipeline_status").inc()
        logger.exception("get_cme_pipeline_status failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/projects/{project_id}/pause")
async def pause_cme_pipeline(project_id: str, db: Session = Depends(get_db)):
    """Pause pipeline execution (for human review gates)"""
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")

    if project.status != "processing":
        raise HTTPException(status_code=400, detail="Pipeline is not running")

    project_svc.set_project_status(db, project, "review")
    return {"status": "paused", "project_id": str(project.id)}


@router.post("/projects/{project_id}/resume")
async def resume_cme_pipeline(project_id: str, db: Session = Depends(get_db)):
    """Resume pipeline execution after human review"""
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")

    if project.status != "review":
        raise HTTPException(status_code=400, detail="Pipeline is not paused")

    project_svc.set_project_status(db, project, "processing")
    return {"status": "resumed", "project_id": str(project.id)}


@router.post("/projects/{project_id}/cancel", response_model=PipelineRunRead)
async def cancel_cme_pipeline(project_id: str, db: Session = Depends(get_db)):
    """Cancel the active pipeline run.

    Calls LangGraph Cloud to cancel the underlying run, then marks the
    pipeline_runs row and project as cancelled. Tolerates a missing/finished
    run on the Cloud side (still marks the DB rows cancelled).
    """
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")

    if project.status not in ("processing", "review"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel: project status is {project.status}",
        )

    run = pipeline_svc.get_active_run(db, project)
    if run is None:
        raise HTTPException(
            status_code=409,
            detail="No active pipeline run associated with this project",
        )

    cancelled = await cancel_langgraph_run(run.thread_id, run.langgraph_run_id)
    if not cancelled:
        logger.warning(f"Cloud cancel failed for thread={run.thread_id} run={run.langgraph_run_id}, marking DB cancelled anyway")
    run = pipeline_svc.cancel_pipeline(db, project, run)

    registry_write_operations.labels(operation="cancel_cme_pipeline").inc()
    return pipeline_svc.pipeline_run_to_read(run)


@router.post("/projects/{project_id}/rerun", response_model=PipelineRunRead)
async def rerun_cme_pipeline(
    project_id: str,
    body: RerunRequest,
    db: Session = Depends(get_db),
):
    """Rerun the pipeline for a project using its current intake.

    Allowed when the project is in a terminal state (complete, failed,
    cancelled) OR in review. Creates a new pipeline_runs row with
    run_number = max+1, points current_run_id at it, and flips the project
    status back to processing.
    """
    start = time.time()
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")

    if project.status not in ("complete", "failed", "cancelled", "review"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot rerun: project status is {project.status}",
        )

    prev_run = None
    if project.status == "review" and project.current_run_id:
        prev_run = pipeline_svc.get_active_run(db, project)
        if prev_run and prev_run.status == "processing":
            cancelled = await cancel_langgraph_run(prev_run.thread_id, prev_run.langgraph_run_id)
            if not cancelled:
                logger.warning(f"Cloud cancel failed for prev run {prev_run.langgraph_run_id} during rerun")

    try:
        lg = await trigger_langgraph_pipeline(str(project.id), project.intake)
    except Exception as e:
        registry_errors.labels(error_type="rerun_cme_pipeline").inc()
        logger.exception("rerun_cme_pipeline LangGraph trigger failed")
        raise HTTPException(status_code=502, detail="Pipeline trigger failed")

    run = pipeline_svc.rerun_pipeline(
        db, project, lg["thread_id"], lg["run_id"],
        reason=body.reason, prev_run=prev_run,
    )

    registry_write_operations.labels(operation="rerun_cme_pipeline").inc()
    registry_write_latency.observe((time.time() - start) * 1000)
    return pipeline_svc.pipeline_run_to_read(run)


@router.get("/projects/{project_id}/runs", response_model=PipelineRunListResponse)
async def list_cme_pipeline_runs(project_id: str, db: Session = Depends(get_db)):
    """List all pipeline runs for a project, newest first."""
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")

    runs = pipeline_svc.list_runs(db, project_id)

    registry_read_operations.labels(operation="list_cme_pipeline_runs").inc()
    return PipelineRunListResponse(
        runs=[pipeline_svc.pipeline_run_to_read(r) for r in runs],
        total=len(runs),
    )


# =============================================================================
# OUTPUT ENDPOINTS
# =============================================================================

@router.get("/projects/{project_id}/outputs", response_model=List[AgentOutput])
async def list_cme_outputs(project_id: str, db: Session = Depends(get_db)):
    """List all agent outputs for a CME project"""
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")

    outputs = pipeline_svc.list_outputs(db, project_id)

    return [
        AgentOutput(
            agent_name=o.agent_name,
            output_type=o.output_type,
            content=o.content,
            created_at=o.created_at,
            quality_score=o.quality_score,
            document_text=o.document_text,
        )
        for o in outputs
    ]


@router.get("/projects/{project_id}/outputs/{agent_name}", response_model=AgentOutput)
async def get_cme_agent_output(
    project_id: str,
    agent_name: str,
    db: Session = Depends(get_db)
):
    """Get output from a specific agent"""
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")

    output = pipeline_svc.get_output(db, project_id, agent_name)

    if not output:
        raise HTTPException(status_code=404, detail=f"No output from agent: {agent_name}")

    return AgentOutput(
        agent_name=output.agent_name,
        output_type=output.output_type,
        content=output.content,
        created_at=output.created_at,
        quality_score=output.quality_score,
        document_text=output.document_text,
    )


# =============================================================================
# WEBHOOK FOR LANGGRAPH CALLBACKS
# =============================================================================

@router.post("/webhook/agent-complete")
async def agent_complete_webhook(
    project_id: str,
    agent_name: str,
    output: Dict[str, Any],
    quality_score: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Webhook called by LangGraph when an agent completes.
    Updates project state with agent output.
    """
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")

    return pipeline_svc.handle_agent_complete(
        db, project, agent_name, output, quality_score,
        calculate_progress_fn=sync_svc.calculate_progress,
    )


@router.post("/webhook/pipeline-status")
async def pipeline_status_webhook(
    project_id: str,
    pipeline_status: str,
    current_step: str = "",
    error_summary: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Webhook called by LangGraph orchestrator when a pipeline reaches a terminal state
    (complete or failed). Updates the project status in the registry database.
    """
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")

    result = pipeline_svc.handle_pipeline_status(db, project, pipeline_status, error_summary)
    result["current_step"] = current_step
    return result


# =============================================================================
# REVIEWER CONFIGURATION ENDPOINTS (Decision R1)
# =============================================================================

class ReviewerCreate(BaseModel):
    """Schema for creating a reviewer"""
    email: str = Field(..., description="Reviewer email address")
    display_name: str = Field(..., description="Display name")
    notify_email: bool = Field(default=True)
    notify_google_chat: bool = Field(default=False)
    google_chat_webhook_url: Optional[str] = None
    max_concurrent_reviews: int = Field(default=5)


class ReviewerResponse(BaseModel):
    """Schema for reviewer response"""
    id: str
    email: str
    display_name: str
    is_active: bool
    max_concurrent_reviews: int
    notify_email: bool
    notify_google_chat: bool
    total_reviews: int
    avg_review_time_hours: Optional[float]


@router.get("/reviewers", response_model=List[ReviewerResponse])
async def list_reviewers(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all configured reviewers"""
    reviewers = review_svc.list_reviewers(db, active_only=active_only)

    return [
        ReviewerResponse(
            id=str(r.id),
            email=r.email,
            display_name=r.display_name,
            is_active=r.is_active,
            max_concurrent_reviews=r.max_concurrent_reviews,
            notify_email=r.notify_email,
            notify_google_chat=r.notify_google_chat,
            total_reviews=r.total_reviews or 0,
            avg_review_time_hours=r.avg_review_time_hours
        )
        for r in reviewers
    ]


@router.post("/reviewers", response_model=ReviewerResponse, status_code=status.HTTP_201_CREATED)
async def create_reviewer(
    reviewer: ReviewerCreate,
    db: Session = Depends(get_db)
):
    """Add a new reviewer to the configuration"""
    db_reviewer = review_svc.create_reviewer(
        db,
        email=reviewer.email,
        display_name=reviewer.display_name,
        notify_email=reviewer.notify_email,
        notify_google_chat=reviewer.notify_google_chat,
        google_chat_webhook_url=reviewer.google_chat_webhook_url,
        max_concurrent_reviews=reviewer.max_concurrent_reviews,
    )
    if db_reviewer is None:
        raise HTTPException(status_code=400, detail="Reviewer with this email already exists")

    return ReviewerResponse(
        id=str(db_reviewer.id),
        email=db_reviewer.email,
        display_name=db_reviewer.display_name,
        is_active=db_reviewer.is_active,
        max_concurrent_reviews=db_reviewer.max_concurrent_reviews,
        notify_email=db_reviewer.notify_email,
        notify_google_chat=db_reviewer.notify_google_chat,
        total_reviews=0,
        avg_review_time_hours=None
    )


@router.delete("/reviewers/{reviewer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_reviewer(
    reviewer_id: str,
    db: Session = Depends(get_db)
):
    """Deactivate a reviewer (soft delete)"""
    reviewer = review_svc.deactivate_reviewer(db, reviewer_id)
    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer not found")


# =============================================================================
# REVIEW ASSIGNMENT ENDPOINTS (Decisions R2-R5)
# =============================================================================

class SubmitForReviewRequest(BaseModel):
    """Schema for submitting a project for review"""
    reviewer_emails: List[str] = Field(..., max_length=3, description="Up to 3 reviewer emails in order")


class ReviewAssignmentResponse(BaseModel):
    """Schema for review assignment response"""
    id: str
    project_id: str
    reviewer_email: str
    reviewer_name: str
    reviewer_order: int
    status: str
    assigned_at: Optional[datetime]
    sla_deadline: Optional[datetime]
    completed_at: Optional[datetime]


@router.post("/projects/{project_id}/submit-for-review")
async def submit_for_review(
    project_id: str,
    request: SubmitForReviewRequest,
    db: Session = Depends(get_db)
):
    """Submit a project for human review (Decision R2: up to 3 reviewers)"""
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if len(request.reviewer_emails) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 reviewers allowed (R2)")

    try:
        result = review_svc.submit_for_review(db, project, request.reviewer_emails)
    except ValueError as e:
        logger.warning("submit_for_review rejected for project %s: %s", project_id, e)
        raise HTTPException(status_code=400, detail="One or more reviewers not found or inactive")

    return {
        "project_id": project_id,
        "status": "submitted_for_review",
        "assignments": result
    }


@router.get("/projects/{project_id}/review-status")
async def get_review_status(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Get current review status for a project"""
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    assignments = review_svc.get_review_status(db, project_id)

    return {
        "project_id": project_id,
        "project_status": project.status,
        "review_status": project.human_review_status,
        "assignments": [
            {
                "id": str(a.id),
                "order": a.reviewer_order,
                "status": a.status,
                "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
                "sla_deadline": a.sla_deadline.isoformat() if a.sla_deadline else None,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                "decision": a.decision,
                "notes": a.notes
            }
            for a in assignments
        ]
    }


class SubmitReviewRequest(BaseModel):
    """Schema for submitting a review decision"""
    decision: str = Field(..., pattern="^(approved|revision_requested)$")
    notes: Optional[str] = None
    annotations: Optional[List[Dict[str, Any]]] = None


@router.post("/projects/{project_id}/review")
async def submit_review(
    project_id: str,
    request: SubmitReviewRequest,
    reviewer_email: str,  # In production, get from auth token
    db: Session = Depends(get_db)
):
    """Submit a review decision with optional Plate JS annotations"""
    project = project_svc.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = review_svc.submit_review(
        db, project, reviewer_email,
        decision=request.decision,
        notes=request.notes,
        annotations=request.annotations,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="No active review assignment found for this reviewer")

    return {
        "project_id": project_id,
        "decision": request.decision,
        "assignment_id": result["assignment_id"],
        "project_status": result["project_status"],
    }


@router.get("/my-reviews")
async def get_my_reviews(
    reviewer_email: str,  # In production, get from auth token
    status_filter: Optional[str] = "active",
    db: Session = Depends(get_db)
):
    """Get pending reviews for current user"""
    result = review_svc.get_my_reviews(db, reviewer_email, status_filter=status_filter)
    return {"reviews": result, "count": len(result)}


# =============================================================================
# SEARCH & RAG ENDPOINTS (Phase 4)
# =============================================================================

class SearchResultItem(BaseModel):
    id: str
    source_table: str  # cme_documents, cme_intake_fields, cme_source_references
    project_id: str
    title: str
    snippet: str
    score: float
    metadata: Dict[str, Any] = {}


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    total: int


class SimilarSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Text to find similar content for")
    project_id: Optional[str] = Field(None, description="Scope to a specific project")
    source_tables: List[str] = Field(
        default=["cme_documents", "cme_source_references"],
        description="Tables to search (cme_documents, cme_source_references)"
    )
    limit: int = Field(default=20, ge=1, le=100)


class HybridSearchRequest(BaseModel):
    query: str = Field(..., min_length=3)
    project_id: Optional[str] = None
    source_tables: List[str] = Field(
        default=["cme_documents", "cme_intake_fields", "cme_source_references"]
    )
    limit: int = Field(default=20, ge=1, le=100)
    fulltext_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    vector_weight: float = Field(default=0.6, ge=0.0, le=1.0)


class RAGContextRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Query for context retrieval")
    project_id: Optional[str] = Field(None, description="Scope to a specific project")
    max_chunks: int = Field(default=10, ge=1, le=50)
    max_tokens: int = Field(default=8000, ge=100, le=32000, description="Approx max token budget for returned context")
    include_citations: bool = Field(default=True)


class RAGChunk(BaseModel):
    source_table: str
    document_id: str
    title: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}


class RAGContextResponse(BaseModel):
    query: str
    chunks: List[RAGChunk]
    total_chunks: int
    estimated_tokens: int
    project_scope: Optional[str] = None


@router.get("/search", response_model=SearchResponse)
async def fulltext_search(
    q: str,
    project_id: Optional[str] = None,
    source_type: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Full-text search across CME documents, intake fields, and source references."""
    start = time.time()

    results_data = search_svc.fulltext_search(
        db, q, project_id=project_id, source_type=source_type, limit=limit,
    )

    elapsed = (time.time() - start) * 1000
    registry_read_latency.observe(elapsed)
    registry_read_operations.labels(operation="cme_fulltext_search").inc()

    results = [SearchResultItem(**r) for r in results_data]
    return SearchResponse(query=q, results=results, total=len(results))


@router.post("/search/similar", response_model=SearchResponse)
async def vector_similarity_search(
    req: SimilarSearchRequest,
    db: Session = Depends(get_db),
):
    """Vector similarity search using pgvector cosine distance."""
    start = time.time()

    query_embedding = await sync_svc.generate_embedding(req.query)
    if query_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service unavailable — could not embed query",
        )

    results_data = search_svc.vector_similarity_search(
        db, query_embedding,
        project_id=req.project_id, source_tables=req.source_tables, limit=req.limit,
    )

    elapsed = (time.time() - start) * 1000
    registry_read_latency.observe(elapsed)
    registry_read_operations.labels(operation="cme_vector_search").inc()

    results = [SearchResultItem(**r) for r in results_data]
    return SearchResponse(query=req.query, results=results, total=len(results))


@router.post("/search/hybrid", response_model=SearchResponse)
async def hybrid_search(
    req: HybridSearchRequest,
    db: Session = Depends(get_db),
):
    """Hybrid search combining full-text and vector similarity with reciprocal rank fusion."""
    start = time.time()

    query_embedding = await sync_svc.generate_embedding(req.query)

    results_data = search_svc.hybrid_search(
        db, req.query, query_embedding,
        project_id=req.project_id, source_tables=req.source_tables, limit=req.limit,
    )

    elapsed = (time.time() - start) * 1000
    registry_read_latency.observe(elapsed)
    registry_read_operations.labels(operation="cme_hybrid_search").inc()

    results = [SearchResultItem(**r) for r in results_data]
    return SearchResponse(query=req.query, results=results, total=len(results))


@router.post("/rag/context", response_model=RAGContextResponse)
async def get_rag_context(
    req: RAGContextRequest,
    db: Session = Depends(get_db),
):
    """Retrieve relevant context chunks for LLM RAG augmentation."""
    start = time.time()

    query_embedding = await sync_svc.generate_embedding(req.query)

    result = search_svc.get_rag_context(
        db, req.query, query_embedding,
        project_id=req.project_id,
        max_chunks=req.max_chunks,
        max_tokens=req.max_tokens,
        include_citations=req.include_citations,
    )

    elapsed = (time.time() - start) * 1000
    registry_read_latency.observe(elapsed)
    registry_read_operations.labels(operation="cme_rag_context").inc()

    chunks = [RAGChunk(**c) for c in result["chunks"]]
    return RAGContextResponse(
        query=result["query"],
        chunks=chunks,
        total_chunks=result["total_chunks"],
        estimated_tokens=result["estimated_tokens"],
        project_scope=result["project_scope"],
    )


# =============================================================================
# CRUD ENDPOINTS — Registry Agent Gateway
# =============================================================================

class SourceReferenceCreate(BaseModel):
    """Create a source reference (citation) for a project."""
    project_id: str
    ref_type: str = Field(..., description="pubmed, doi, url, journal, guideline")
    ref_id: Optional[str] = Field(None, description="PubMed ID or DOI")
    title: str
    authors: Optional[str] = None
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    cached_content: Optional[Dict[str, Any]] = None
    document_id: Optional[str] = None
    verification_status: Optional[str] = Field(None, description="verified, not_found, retracted, outdated, landmark")
    verified_by: Optional[str] = None


class AgentOutputCreate(BaseModel):
    """Create an agent output record."""
    project_id: str
    agent_name: str
    output_type: str = "document"
    content: Dict[str, Any]
    quality_score: Optional[float] = None
    document_text: Optional[str] = None
    langsmith_trace_id: Optional[str] = None


class DocumentCreate(BaseModel):
    """Create an immutable CME document version."""
    project_id: str
    agent_output_id: Optional[str] = None
    document_type: str
    title: str
    content_text: str
    content_html: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    word_count: Optional[int] = None
    quality_score: Optional[float] = None
    quality_passed: Optional[bool] = None
    quality_details: Optional[Dict[str, Any]] = None
    source_references: Optional[List[Dict[str, Any]]] = None
    created_by: str = "registry_agent"


@router.post("/source-references", status_code=status.HTTP_201_CREATED)
async def create_source_reference(
    ref: SourceReferenceCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create a source reference. Returns 409 if project_id + ref_id already exists."""
    start = time.time()

    project = project_svc.get_project(db, str(ref.project_id))
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {ref.project_id} not found")

    pub_date = None
    if ref.publication_date:
        try:
            pub_date = datetime.fromisoformat(ref.publication_date).date()
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid publication_date '{ref.publication_date}': {e}")
            pub_date = None

    ref_id, ref_status = pipeline_svc.create_source_reference(db, project, ref.model_dump(), pub_date)

    if ref_status == "created":
        ref_text = f"{ref.title} {ref.authors or ''} {ref.abstract or ''}"
        background_tasks.add_task(_generate_embedding_and_save, "cme_source_references", ref_id, ref_text)
        db.commit()

    elapsed = (time.time() - start) * 1000
    registry_write_latency.observe(elapsed)
    registry_write_operations.labels(operation="create_source_reference").inc()

    return {"id": ref_id, "status": ref_status}


@router.post("/agent-outputs", status_code=status.HTTP_201_CREATED)
async def create_agent_output(
    req: AgentOutputCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create an agent output. Returns 409 if project_id + agent_name already exists."""
    start = time.time()

    project = project_svc.get_project(db, str(req.project_id))
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {req.project_id} not found")

    output_id, output_status = pipeline_svc.create_agent_output(db, project, req.model_dump())

    if output_status == "created":
        if req.document_text:
            background_tasks.add_task(_generate_embedding_and_save, "cme_agent_outputs", output_id, req.document_text)
        db.commit()

    elapsed = (time.time() - start) * 1000
    registry_write_latency.observe(elapsed)
    registry_write_operations.labels(operation="create_agent_output").inc()

    return {"id": output_id, "status": output_status}


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def create_document(
    req: DocumentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create an immutable document version. Auto-increments version if one exists."""
    start = time.time()

    project = project_svc.get_project(db, str(req.project_id))
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {req.project_id} not found")

    doc_id, version, doc_status = pipeline_svc.create_document(db, project, req.model_dump())

    background_tasks.add_task(_generate_embedding_and_save, "cme_documents", doc_id, req.content_text)
    db.commit()

    elapsed = (time.time() - start) * 1000
    registry_write_latency.observe(elapsed)
    registry_write_operations.labels(operation="create_document").inc()

    return {"id": doc_id, "version": version, "status": doc_status}


async def _generate_embedding_and_save(table_name: str, record_id, text_content: str):
    """Background task: generate embedding and update the record."""
    emb = await sync_svc.generate_embedding(text_content)
    if emb is None:
        return
    pipeline_svc.save_embedding(table_name, record_id, emb)


async def fetch_latest_document_for_thread(thread_id: str) -> dict | None:
    """Return the latest CMEDocument for a given pipeline thread, as dict.

    Used by the /api/cme/export/* endpoints to hydrate the print route and
    the sync download endpoint. Returns None if no project/document matches.

    Note on field mapping (drift from Phase 1.9 plan):
      plan `agent_source`  -> actual column `document_type`
      plan `meta`          -> actual column `quality_details` (JSONB), used
                              only to surface an optional `review_round`
      plan `content`       -> actual column `content_text`

    Phase 1 note: this function is async def for test monkey-patching, but the
    body uses sync SessionLocal() — it blocks the event loop during the query.
    Acceptable at current registry QPS; revisit when the registry moves to an
    async session.
    """
    return project_svc.fetch_latest_document_for_thread(thread_id)
