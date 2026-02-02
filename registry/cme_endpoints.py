"""
CME Grant Intake API Endpoints
Handles CME project creation, pipeline execution, and status tracking
Uses /api/v2/ prefix for CME-specific endpoints
"""
import time
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pydantic import BaseModel, Field
import httpx

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from models import CMEProject, CMEAgentOutput

# Import metrics from main API
try:
    from api import (
        registry_read_latency, registry_read_operations, registry_errors,
        registry_write_latency, registry_write_operations
    )
except ImportError:
    from prometheus_client import Counter, Histogram
    registry_read_latency = Histogram('registry_read_latency', 'Read latency', buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000])
    registry_read_operations = Counter('registry_read_operations', 'Read operations', ['operation'])
    registry_write_latency = Histogram('registry_write_latency', 'Write latency', buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000])
    registry_write_operations = Counter('registry_write_operations', 'Write operations', ['operation'])
    registry_errors = Counter('registry_errors', 'Registry errors', ['error_type'])


router = APIRouter(prefix="/api/v2", tags=["cme"])


# =============================================================================
# ENUMS
# =============================================================================

class CMEProjectStatus(str, Enum):
    INTAKE = "intake"
    PROCESSING = "processing"
    REVIEW = "review"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TherapeuticArea(str, Enum):
    CARDIOLOGY = "Cardiology"
    ONCOLOGY = "Oncology"
    NEUROLOGY = "Neurology"
    ENDOCRINOLOGY = "Endocrinology"
    IMMUNOLOGY = "Immunology"
    INFECTIOUS_DISEASE = "Infectious Disease"
    PULMONOLOGY = "Pulmonology"
    GASTROENTEROLOGY = "Gastroenterology"
    NEPHROLOGY = "Nephrology"
    HEMATOLOGY = "Hematology"
    DERMATOLOGY = "Dermatology"
    RHEUMATOLOGY = "Rheumatology"
    PSYCHIATRY = "Psychiatry"
    OTHER = "Other"


# =============================================================================
# PYDANTIC MODELS - INTAKE SECTIONS
# =============================================================================

class SectionA_ProjectBasics(BaseModel):
    """Section A: Project Basics (5 fields)"""
    project_name: str = Field(..., min_length=5, max_length=200)
    therapeutic_area: TherapeuticArea
    disease_state: str = Field(..., min_length=3, max_length=200)
    target_audience_primary: List[str] = Field(..., min_length=1, max_length=5)
    target_audience_secondary: Optional[List[str]] = Field(None, max_length=3)


class SectionB_Supporter(BaseModel):
    """Section B: Supporter Information (5 fields)"""
    supporter_name: str
    supporter_contact_name: Optional[str] = None
    supporter_contact_email: Optional[str] = None
    grant_amount_requested: Optional[float] = None
    grant_submission_deadline: Optional[datetime] = None


class SectionC_Educational(BaseModel):
    """Section C: Educational Design (5 fields)"""
    learning_format: str
    duration_minutes: Optional[int] = None
    include_post_test: bool = False
    include_pre_test: bool = False
    faculty_count: Optional[int] = None


class SectionD_Clinical(BaseModel):
    """Section D: Clinical Focus (5 fields)"""
    clinical_topics: List[str]
    treatment_modalities: Optional[List[str]] = None
    patient_population: Optional[str] = None
    stage_of_disease: Optional[str] = None
    comorbidities: Optional[List[str]] = None


class SectionE_Gaps(BaseModel):
    """Section E: Educational Gaps (5 fields)"""
    knowledge_gaps: Optional[List[str]] = None
    competence_gaps: Optional[List[str]] = None
    performance_gaps: Optional[List[str]] = None
    gap_evidence_sources: Optional[List[str]] = None
    gap_priority: Optional[str] = None


class SectionF_Outcomes(BaseModel):
    """Section F: Outcomes & Measurement (5 fields)"""
    primary_outcomes: Optional[List[str]] = None
    secondary_outcomes: Optional[List[str]] = None
    measurement_approach: Optional[str] = None
    moore_levels_target: Optional[List[int]] = None
    follow_up_timeline: Optional[str] = None


class SectionG_Content(BaseModel):
    """Section G: Content Requirements (5 fields)"""
    key_messages: Optional[List[str]] = None
    required_references: Optional[List[str]] = None
    excluded_topics: Optional[List[str]] = None
    competitor_products_to_mention: Optional[List[str]] = None
    regulatory_considerations: Optional[str] = None


class SectionH_Logistics(BaseModel):
    """Section H: Logistics (5 fields)"""
    target_launch_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    distribution_channels: Optional[List[str]] = None
    geo_restrictions: Optional[List[str]] = None
    language_requirements: Optional[List[str]] = None


class SectionI_Compliance(BaseModel):
    """Section I: Compliance & Disclosure (4 fields)"""
    accme_compliant: bool = True
    financial_disclosure_required: bool = True
    off_label_discussion: bool = False
    commercial_support_acknowledgment: bool = True


class SectionJ_Additional(BaseModel):
    """Section J: Additional Information (3 fields)"""
    special_instructions: Optional[str] = None
    reference_materials: Optional[List[str]] = None
    internal_notes: Optional[str] = None


# =============================================================================
# INTAKE SUBMISSION MODEL
# =============================================================================

class IntakeSubmission(BaseModel):
    """Complete 47-field intake form across 10 sections"""
    section_a: SectionA_ProjectBasics
    section_b: SectionB_Supporter
    section_c: SectionC_Educational
    section_d: SectionD_Clinical
    section_e: SectionE_Gaps
    section_f: SectionF_Outcomes
    section_g: SectionG_Content
    section_h: SectionH_Logistics
    section_i: SectionI_Compliance
    section_j: SectionJ_Additional


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class CMEProjectCreateResponse(BaseModel):
    project_id: str
    status: CMEProjectStatus
    message: str
    created_at: datetime


class CMEProjectDetail(BaseModel):
    id: str
    name: str
    status: CMEProjectStatus
    current_agent: Optional[str]
    progress_percent: int
    intake: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    outputs_available: List[str]
    human_review_status: Optional[str]


class ExecutionStatus(BaseModel):
    project_id: str
    status: CMEProjectStatus
    current_agent: Optional[str]
    progress_percent: int
    agents_completed: List[str]
    agents_pending: List[str]
    errors: List[Dict[str, Any]]
    started_at: Optional[datetime]
    estimated_completion: Optional[datetime]


class AgentOutput(BaseModel):
    agent_name: str
    output_type: str
    content: Dict[str, Any]
    created_at: datetime
    quality_score: Optional[float]


# =============================================================================
# DATABASE MODEL (for reference - actual migration needed)
# =============================================================================
# Note: This model definition is for documentation. 
# A proper Alembic migration should be created to add this table.
#
# class CMEProject(Base):
#     __tablename__ = "cme_projects"
#     
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     name = Column(String(255), nullable=False)
#     status = Column(String(50), nullable=False, default="intake")
#     intake = Column(JSONB, nullable=False)
#     current_agent = Column(String(100))
#     progress_percent = Column(Integer, default=0)
#     outputs = Column(JSONB)
#     errors = Column(JSONB)
#     human_review_status = Column(String(50))
#     pipeline_thread_id = Column(String(100))  # LangGraph thread ID
#     created_at = Column(DateTime, default=datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
#     started_at = Column(DateTime)
#     completed_at = Column(DateTime)


# =============================================================================
# DATABASE OPERATIONS HELPERS
# =============================================================================


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def trigger_langgraph_pipeline(project_id: str, intake_data: dict) -> str:
    """
    Trigger the 12-agent LangGraph pipeline.
    Returns the thread_id for tracking.
    """
    # LangGraph Cloud endpoint (configure via env)
    langgraph_url = os.getenv("LANGGRAPH_API_URL", "http://localhost:8011/langgraph/run")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                langgraph_url,
                json={
                    "project_id": project_id,
                    "intake": intake_data,
                    "task_type": "cme_grant_pipeline"
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("thread_id", project_id)
    except Exception as e:
        # Log error but don't fail - pipeline may be started manually
        print(f"Warning: Could not auto-start LangGraph pipeline: {e}")
        return project_id


def calculate_progress(agents_completed: List[str]) -> int:
    """Calculate progress percentage based on completed agents"""
    total_agents = 12
    return int((len(agents_completed) / total_agents) * 100)


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
        # Convert intake to dict for storage (mode='json' serializes datetimes to ISO strings)
        intake_dict = intake.model_dump(mode='json')
        
        # Create project in database
        db_project = CMEProject(
            name=intake.section_a.project_name,
            status="intake",
            intake=intake_dict,
            current_agent=None,
            progress_percent=0,
            outputs={},
            errors=[],
            human_review_status=None,
            pipeline_thread_id=None,
            agents_completed=[],
            agents_pending=[
                "research", "clinical", "gap_analysis", "needs_assessment",
                "learning_objectives", "curriculum", "protocol", "marketing",
                "grant_writer", "prose_quality", "compliance", "package_assembly"
            ]
        )
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        
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
        raise HTTPException(status_code=500, detail=str(e))


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
        query = db.query(CMEProject)
        
        # Filter by status if provided
        if status:
            query = query.filter(CMEProject.status == status.value)
        
        # Pagination
        projects = query.order_by(CMEProject.created_at.desc()).offset(skip).limit(limit).all()
        
        result = [
            CMEProjectDetail(
                id=str(p.id),
                name=p.name,
                status=CMEProjectStatus(p.status),
                current_agent=p.current_agent,
                progress_percent=p.progress_percent or 0,
                intake=p.intake,
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}", response_model=CMEProjectDetail)
async def get_cme_project(project_id: str, db: Session = Depends(get_db)):
    """Get details for a specific CME project"""
    start = time.time()
    try:
        p = db.query(CMEProject).filter(CMEProject.id == project_id).first()
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
            created_at=p.created_at,
            updated_at=p.updated_at,
            outputs_available=list(p.outputs.keys()) if p.outputs else [],
            human_review_status=p.human_review_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        registry_errors.labels(error_type="get_cme_project").inc()
        raise HTTPException(status_code=500, detail=str(e))


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
        project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="CME project not found")
        
        if project.status not in ["intake", "failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot start pipeline: project status is {project.status}"
            )
        
        # Update project status
        now = datetime.utcnow()
        project.status = "processing"
        project.started_at = now
        project.current_agent = "research"  # First agent
        
        # Trigger LangGraph pipeline in background
        thread_id = await trigger_langgraph_pipeline(str(project.id), project.intake)
        project.pipeline_thread_id = thread_id
        
        db.commit()
        db.refresh(project)
        
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/status", response_model=ExecutionStatus)
async def get_cme_pipeline_status(project_id: str, db: Session = Depends(get_db)):
    """Get current execution status of the CME pipeline"""
    start = time.time()
    try:
        project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="CME project not found")
        
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/pause")
async def pause_cme_pipeline(project_id: str, db: Session = Depends(get_db)):
    """Pause pipeline execution (for human review gates)"""
    project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")
    
    if project.status != "processing":
        raise HTTPException(status_code=400, detail="Pipeline is not running")
    
    project.status = "review"
    db.commit()
    
    return {"status": "paused", "project_id": str(project.id)}


@router.post("/projects/{project_id}/resume")
async def resume_cme_pipeline(project_id: str, db: Session = Depends(get_db)):
    """Resume pipeline execution after human review"""
    project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")
    
    if project.status != "review":
        raise HTTPException(status_code=400, detail="Pipeline is not paused")
    
    project.status = "processing"
    db.commit()
    
    return {"status": "resumed", "project_id": str(project.id)}


@router.post("/projects/{project_id}/cancel")
async def cancel_cme_pipeline(project_id: str, db: Session = Depends(get_db)):
    """Cancel pipeline execution"""
    project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")
    
    project.status = "cancelled"
    db.commit()
    
    return {"status": "cancelled", "project_id": str(project.id)}


# =============================================================================
# OUTPUT ENDPOINTS
# =============================================================================

@router.get("/projects/{project_id}/outputs", response_model=List[AgentOutput])
async def list_cme_outputs(project_id: str, db: Session = Depends(get_db)):
    """List all agent outputs for a CME project"""
    project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")
    
    # Query outputs from cme_agent_outputs table
    outputs = db.query(CMEAgentOutput).filter(CMEAgentOutput.project_id == project_id).all()
    
    return [
        AgentOutput(
            agent_name=o.agent_name,
            output_type=o.output_type,
            content=o.content,
            created_at=o.created_at,
            quality_score=o.quality_score
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
    project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")
    
    output = db.query(CMEAgentOutput).filter(
        CMEAgentOutput.project_id == project_id,
        CMEAgentOutput.agent_name == agent_name
    ).first()
    
    if not output:
        raise HTTPException(status_code=404, detail=f"No output from agent: {agent_name}")
    
    return AgentOutput(
        agent_name=output.agent_name,
        output_type=output.output_type,
        content=output.content,
        created_at=output.created_at,
        quality_score=output.quality_score
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
    project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")
    
    now = datetime.utcnow()
    
    # Store output in cme_agent_outputs table
    db_output = CMEAgentOutput(
        project_id=project.id,
        agent_name=agent_name,
        output_type=output.get("type", "document"),
        content=output,
        quality_score=quality_score
    )
    db.add(db_output)
    
    # Update project progress
    agents_pending = list(project.agents_pending or [])
    agents_completed = list(project.agents_completed or [])
    
    if agent_name in agents_pending:
        agents_pending.remove(agent_name)
        agents_completed.append(agent_name)
    
    project.agents_pending = agents_pending
    project.agents_completed = agents_completed
    project.progress_percent = calculate_progress(agents_completed)
    
    # Set next agent
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
        "progress": project.progress_percent
    }

