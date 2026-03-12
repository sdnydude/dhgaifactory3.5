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
import logging

logger = logging.getLogger(__name__)

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from models import (
    CMEProject, CMEAgentOutput, CMEReviewerConfig, CMEReviewAssignment,
    CMEDocument, CMEIntakeField, CMESourceReference,
)

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


router = APIRouter(prefix="/api/cme", tags=["cme"])


# =============================================================================
# ENUMS
# =============================================================================

class CMEProjectStatus(str, Enum):
    INTAKE = "intake"
    PROCESSING = "processing"
    REVIEW = "review"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# PYDANTIC MODELS - INTAKE SECTIONS
# =============================================================================

class SectionA_ProjectBasics(BaseModel):
    """Section A: Project Basics (6 fields)"""
    project_name: str = Field(..., min_length=5, max_length=200)
    therapeutic_area: str = Field(..., min_length=1, max_length=200)
    disease_state: str = Field(..., min_length=1, max_length=200)
    target_audience_primary: List[str] = Field(..., min_length=1, max_length=5)
    target_audience_secondary: Optional[List[str]] = Field(None, max_length=3)
    target_hcp_types: Optional[List[str]] = Field(None, description="HCP credential types (MD/DO, NP, PA-C)")


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
    target_launch_date: Optional[str] = None
    expiration_date: Optional[str] = None
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

LANGGRAPH_CLOUD_URL = "https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app"


async def trigger_langgraph_pipeline(project_id: str, intake_data: dict) -> str:
    """
    Trigger the LangGraph CME pipeline via the LangGraph Cloud REST API.
    Creates a thread, then starts a run with the needs_package assistant.
    Returns the thread_id for tracking.
    """
    langgraph_url = os.getenv("LANGGRAPH_API_URL", LANGGRAPH_CLOUD_URL)
    langchain_api_key = os.getenv("LANGCHAIN_API_KEY", "")
    headers = {"x-api-key": langchain_api_key}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Create a thread with project metadata
            thread_resp = await client.post(
                f"{langgraph_url}/threads",
                json={"metadata": {"graph_id": "needs_package", "project_id": project_id}},
                headers=headers,
            )
            thread_resp.raise_for_status()
            thread_id = thread_resp.json()["thread_id"]

            # 2. Start a background run on the thread
            run_resp = await client.post(
                f"{langgraph_url}/threads/{thread_id}/runs",
                json={
                    "assistant_id": "needs_package",
                    "input": {
                        "intake_data": intake_data,
                        "project_id": project_id,
                    },
                },
                headers=headers,
            )
            run_resp.raise_for_status()
            logger.info(f"LangGraph pipeline started: thread={thread_id}, project={project_id}")
            return thread_id
    except Exception as e:
        logger.error(f"Failed to start LangGraph pipeline for project {project_id}: {e}")
        raise


def calculate_progress(agents_completed: List[str]) -> int:
    """Calculate progress percentage based on completed agents"""
    total_agents = 12
    return int((len(agents_completed) / total_agents) * 100)


# =============================================================================
# LANGGRAPH CLOUD SYNC (replaces unreachable webhook callbacks)
# =============================================================================

AGENT_OUTPUT_KEYS = [
    "research_output", "clinical_output", "gap_analysis_output",
    "needs_assessment_output", "learning_objectives_output",
    "curriculum_output", "protocol_output", "marketing_output",
    "grant_package_output", "prose_quality_pass_1", "prose_quality_pass_2",
    "compliance_result",
]

THREAD_STATUS_MAP = {
    "busy": "processing",
    "interrupted": "review",
    "error": "failed",
}

# Maps state key → (short agent name, document title for cme_documents)
AGENT_OUTPUT_META = {
    "research_output": ("research", "Research & Literature Review"),
    "clinical_output": ("clinical", "Clinical Practice Analysis"),
    "gap_analysis_output": ("gap_analysis", "Gap Analysis"),
    "needs_assessment_output": ("needs_assessment", "Needs Assessment"),
    "learning_objectives_output": ("learning_objectives", "Learning Objectives"),
    "curriculum_output": ("curriculum", "Curriculum Design"),
    "protocol_output": ("protocol", "Research Protocol"),
    "marketing_output": ("marketing", "Marketing Plan"),
    "grant_package_output": ("grant_package", "Grant Package"),
    "prose_quality_pass_1": ("prose_quality_1", "Prose Quality Pass 1"),
    "prose_quality_pass_2": ("prose_quality_2", "Prose Quality Pass 2"),
    "compliance_result": ("compliance", "Compliance Review"),
}

# Maps short agent name → JSONB path to the prose document text
DOCUMENT_TEXT_PATHS = {
    "research": "research_document",
    "clinical": "clinical_practice_document",
    "gap_analysis": "gap_analysis_document",
    "needs_assessment": "complete_document",
    "learning_objectives": "learning_objectives_document",
    "curriculum": "curriculum_document",
    "protocol": "protocol_document",
    "marketing": "marketing_document",
    "grant_package": "complete_document_markdown",
    "prose_quality_1": "summary",
    "prose_quality_2": "summary",
    "compliance": None,  # Built from compliance_report
}

# Maps short agent name → JSONB path to the structured report dict
REPORT_PATHS = {
    "research": "research_report",
    "clinical": "clinical_practice_report",
    "gap_analysis": "gap_analysis_report",
    "learning_objectives": "learning_objectives_report",
    "curriculum": "curriculum_report",
    "protocol": "protocol_report",
    "marketing": "marketing_report",
    "compliance": "compliance_report",
}

# Maps short agent name → JSONB path to citations list
CITATION_PATHS = {
    "research": ("research_report", "citations"),
    "clinical": ("clinical_practice_report", "citations"),
}


def _extract_document_text(agent_name: str, content: Dict[str, Any]) -> Optional[str]:
    """Extract the prose document text from an agent's JSONB output."""
    if not isinstance(content, dict):
        return None

    text_path = DOCUMENT_TEXT_PATHS.get(agent_name)
    if text_path is None and agent_name == "compliance":
        report = content.get("compliance_report", {})
        if isinstance(report, dict):
            verdict = report.get("overall_verdict", "")
            checks = report.get("standard_checks", {})
            parts = [f"Compliance Verdict: {verdict}"]
            for std_name, std_data in checks.items():
                if isinstance(std_data, dict):
                    parts.append(f"{std_name}: {std_data.get('status', 'unknown')} — {std_data.get('findings', '')}")
            return "\n\n".join(parts) if parts else None
        return None

    if text_path:
        text = content.get(text_path)
        if isinstance(text, str) and len(text) > 10:
            return text
    return None


def _extract_quality_score(agent_name: str, content: Dict[str, Any]) -> Optional[float]:
    """Extract quality score from an agent's JSONB output. Returns 0.0-1.0 scale."""
    if not isinstance(content, dict):
        return None

    if agent_name in ("prose_quality_1", "prose_quality_2"):
        score = content.get("overall_score")
        if isinstance(score, (int, float)):
            return score / 100.0  # Convert 0-100 to 0-1
    elif agent_name == "needs_assessment":
        if content.get("quality_passed"):
            return 1.0
        word_count = content.get("word_count", 0)
        if isinstance(word_count, (int, float)) and word_count > 0:
            return min(word_count / 3100.0, 1.0)  # Ratio to target
    elif agent_name == "compliance":
        report = content.get("compliance_report", {})
        if isinstance(report, dict):
            verdict = report.get("overall_verdict", "")
            if verdict == "APPROVED":
                return 1.0
            elif verdict == "REQUIRES_REVISION":
                return 0.5
            elif verdict == "REJECTED":
                return 0.0
    return None


def _extract_quality_details(agent_name: str, content: Dict[str, Any]) -> Optional[Dict]:
    """Extract structured quality details for cme_documents.quality_details."""
    if not isinstance(content, dict):
        return None

    if agent_name in ("prose_quality_1", "prose_quality_2"):
        return {
            "overall_score": content.get("overall_score"),
            "overall_passed": content.get("overall_passed"),
            "prose_density_score": content.get("prose_density_score"),
            "ai_patterns_count": content.get("ai_patterns_count"),
            "word_count_total": content.get("word_count_total"),
            "revision_instructions": content.get("revision_instructions"),
        }
    elif agent_name == "needs_assessment":
        return {
            "word_count": content.get("word_count"),
            "meets_word_count": content.get("meets_word_count"),
            "prose_density": content.get("prose_density"),
            "quality_passed": content.get("quality_passed"),
            "section_word_counts": content.get("section_word_counts"),
            "character_appearances": content.get("character_appearances"),
        }
    elif agent_name == "compliance":
        report = content.get("compliance_report", {})
        if isinstance(report, dict):
            return {
                "overall_verdict": report.get("overall_verdict"),
                "remediation_required": report.get("remediation_required"),
                "standard_checks": report.get("standard_checks"),
                "bias_issues": report.get("bias_issues"),
            }
    return None


def _extract_word_count(agent_name: str, content: Dict[str, Any]) -> Optional[int]:
    """Extract word count from output or count from document text."""
    if not isinstance(content, dict):
        return None

    if agent_name == "needs_assessment":
        wc = content.get("word_count")
        if isinstance(wc, int):
            return wc
    elif agent_name in ("prose_quality_1", "prose_quality_2"):
        wc = content.get("word_count_total")
        if isinstance(wc, int):
            return wc

    doc_text = _extract_document_text(agent_name, content)
    if doc_text:
        return len(doc_text.split())
    return None


def _extract_citations(agent_name: str, content: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract citation list from agent output for cme_source_references."""
    if agent_name not in CITATION_PATHS or not isinstance(content, dict):
        return []

    report_key, citations_key = CITATION_PATHS[agent_name]
    report = content.get(report_key, {})
    if not isinstance(report, dict):
        return []

    citations = report.get(citations_key, [])
    if not isinstance(citations, list):
        return []

    return citations


def _extract_intake_fields(project_id, intake_jsonb: Dict[str, Any], db: Session) -> int:
    """Explode JSONB intake blob into individual cme_intake_fields rows.

    Returns the number of fields inserted/updated.
    """
    if not isinstance(intake_jsonb, dict):
        return 0

    FIELD_LABELS = {
        "section_a": {
            "project_name": "Project Name",
            "therapeutic_area": "Therapeutic Area",
            "disease_state": "Disease State",
            "target_audience_primary": "Primary Target Audience",
            "target_audience_secondary": "Secondary Target Audience",
            "target_hcp_types": "Target HCP Types",
        },
        "section_b": {
            "supporter_name": "Supporter Name",
            "supporter_contact_name": "Supporter Contact Name",
            "supporter_contact_email": "Supporter Contact Email",
            "grant_amount_requested": "Grant Amount Requested",
            "grant_submission_deadline": "Grant Submission Deadline",
        },
        "section_c": {
            "learning_format": "Learning Format",
            "duration_minutes": "Duration (minutes)",
            "faculty_count": "Faculty Count",
            "include_pre_test": "Include Pre-Test",
            "include_post_test": "Include Post-Test",
        },
        "section_d": {
            "clinical_topics": "Clinical Topics",
            "treatment_modalities": "Treatment Modalities",
            "patient_population": "Patient Population",
            "stage_of_disease": "Stage of Disease",
            "comorbidities": "Comorbidities",
        },
        "section_e": {
            "knowledge_gaps": "Knowledge Gaps",
            "competence_gaps": "Competence Gaps",
            "performance_gaps": "Performance Gaps",
            "gap_evidence_sources": "Gap Evidence Sources",
            "gap_priority": "Gap Priority",
        },
        "section_f": {
            "primary_outcomes": "Primary Outcomes",
            "secondary_outcomes": "Secondary Outcomes",
            "measurement_approach": "Measurement Approach",
            "moore_levels_target": "Moore Levels Target",
            "follow_up_timeline": "Follow-Up Timeline",
        },
        "section_g": {
            "key_messages": "Key Messages",
            "required_references": "Required References",
            "excluded_topics": "Excluded Topics",
            "competitor_products_to_mention": "Competitor Products",
            "regulatory_considerations": "Regulatory Considerations",
        },
        "section_h": {
            "target_launch_date": "Target Launch Date",
            "expiration_date": "Expiration Date",
            "distribution_channels": "Distribution Channels",
            "geo_restrictions": "Geographic Restrictions",
            "language_requirements": "Language Requirements",
        },
        "section_i": {
            "accme_compliant": "ACCME Compliant",
            "financial_disclosure_required": "Financial Disclosure Required",
            "off_label_discussion": "Off-Label Discussion",
            "commercial_support_acknowledgment": "Commercial Support Acknowledgment",
        },
        "section_j": {
            "special_instructions": "Special Instructions",
            "reference_materials": "Reference Materials",
            "internal_notes": "Internal Notes",
        },
    }

    count = 0
    for section_key, section_data in intake_jsonb.items():
        if not isinstance(section_data, dict):
            continue
        labels = FIELD_LABELS.get(section_key, {})

        for field_name, value in section_data.items():
            label = labels.get(field_name, field_name.replace("_", " ").title())

            # Determine text vs json storage
            if isinstance(value, (list, dict)):
                value_text = str(value) if value else None
                value_json = value
            elif isinstance(value, bool):
                value_text = "Yes" if value else "No"
                value_json = None
            elif value is not None:
                value_text = str(value)
                value_json = None
            else:
                value_text = None
                value_json = None

            existing = db.query(CMEIntakeField).filter(
                CMEIntakeField.project_id == project_id,
                CMEIntakeField.section == section_key,
                CMEIntakeField.field_name == field_name,
            ).first()

            if existing:
                existing.value_text = value_text
                existing.value_json = value_json
                existing.field_label = label
            else:
                db.add(CMEIntakeField(
                    project_id=project_id,
                    section=section_key,
                    field_name=field_name,
                    field_label=label,
                    value_text=value_text,
                    value_json=value_json,
                ))
            count += 1

    return count


async def _generate_embedding(text: str) -> Optional[List[float]]:
    """Generate a 768-dim embedding via Ollama nomic-embed-text.

    Truncates to ~8000 tokens (~32000 chars) to stay within model context.
    Returns None on failure (non-blocking).
    """
    if not text or len(text.strip()) < 10:
        return None

    truncated = text[:32000]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{os.getenv('OLLAMA_URL', 'http://dhg-ollama:11434')}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": truncated},
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding")
            if isinstance(embedding, list) and len(embedding) == 768:
                return embedding
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")
    return None


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
    except Exception as e:
        logger.error(f"Failed to fetch thread {thread_id} from Cloud: {e}")
        return None


async def _sync_project_from_thread(project: "CMEProject", thread_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Sync a CMEProject from LangGraph Cloud thread data.

    Populates: cme_agent_outputs, cme_documents, cme_source_references.
    Updates: project status, agents_completed, progress.
    Generates embeddings asynchronously.
    Returns a summary dict.
    """
    thread_info = thread_data["thread"]
    thread_state = thread_data["state"]
    values = thread_state.get("values") or {}
    thread_status = thread_info.get("status", "idle")

    # Map thread status to project status
    if thread_status == "idle":
        pipeline_status = values.get("status", "complete")
        if pipeline_status in ("complete", "approved"):
            new_status = "complete"
        elif pipeline_status == "failed":
            new_status = "failed"
        else:
            new_status = project.status
    else:
        new_status = THREAD_STATUS_MAP.get(thread_status, project.status)

    old_status = project.status
    project.status = new_status
    project.current_agent = values.get("current_step", project.current_agent)
    project.human_review_status = values.get("human_review_status", project.human_review_status)
    project.human_review_notes = values.get("human_review_notes", project.human_review_notes)

    # Extract agent outputs → cme_agent_outputs + cme_documents + cme_source_references
    agents_completed = []
    documents_created = 0
    references_created = 0

    for state_key in AGENT_OUTPUT_KEYS:
        output = values.get(state_key)
        if not output or not isinstance(output, dict):
            continue

        meta = AGENT_OUTPUT_META.get(state_key)
        if not meta:
            continue
        agent_name, doc_title = meta

        agents_completed.append(agent_name)
        doc_text = _extract_document_text(agent_name, output)
        quality_score = _extract_quality_score(agent_name, output)

        # --- cme_agent_outputs ---
        existing_output = db.query(CMEAgentOutput).filter(
            CMEAgentOutput.project_id == project.id,
            CMEAgentOutput.agent_name == agent_name,
        ).first()

        if existing_output:
            if doc_text and not existing_output.document_text:
                existing_output.document_text = doc_text
            if quality_score is not None and existing_output.quality_score is None:
                existing_output.quality_score = quality_score
            agent_output_id = existing_output.id
        else:
            new_output = CMEAgentOutput(
                project_id=project.id,
                agent_name=agent_name,
                output_type="document",
                content=output,
                quality_score=quality_score,
                document_text=doc_text,
            )
            db.add(new_output)
            db.flush()
            agent_output_id = new_output.id

        # --- cme_documents (immutable, versioned) ---
        if doc_text:
            existing_doc = db.query(CMEDocument).filter(
                CMEDocument.project_id == project.id,
                CMEDocument.document_type == agent_name,
                CMEDocument.is_current == True,
            ).first()

            if not existing_doc:
                now = datetime.utcnow()
                doc = CMEDocument(
                    project_id=project.id,
                    agent_output_id=agent_output_id,
                    document_type=agent_name,
                    version=1,
                    is_current=True,
                    title=doc_title,
                    content_text=doc_text,
                    content_json=output,
                    word_count=_extract_word_count(agent_name, output),
                    quality_score=quality_score,
                    quality_passed=output.get("quality_passed") or output.get("overall_passed"),
                    quality_details=_extract_quality_details(agent_name, output),
                    created_by="langgraph_pipeline",
                    retention_until=datetime(now.year + 7, now.month, now.day),
                )
                db.add(doc)
                documents_created += 1

        # --- cme_source_references ---
        citations = _extract_citations(agent_name, output)
        for cit in citations:
            if not isinstance(cit, dict):
                continue
            ref_id = str(cit.get("pmid", cit.get("doi", "")))
            if not ref_id:
                continue

            existing_ref = db.query(CMESourceReference).filter(
                CMESourceReference.project_id == project.id,
                CMESourceReference.ref_id == ref_id,
            ).first()

            if not existing_ref:
                db.add(CMESourceReference(
                    project_id=project.id,
                    ref_type="pubmed" if cit.get("pmid") else "doi",
                    ref_id=ref_id,
                    title=cit.get("title", "Untitled"),
                    authors=cit.get("authors", ""),
                    journal=cit.get("journal", ""),
                    url=cit.get("url", ""),
                    abstract=cit.get("abstract", ""),
                    cached_content=cit,
                ))
                references_created += 1

    if agents_completed:
        project.agents_completed = agents_completed
        remaining = [a for a in (project.agents_pending or []) if a not in agents_completed]
        project.agents_pending = remaining
        project.progress_percent = calculate_progress(agents_completed)

    if new_status == "complete" and not project.completed_at:
        project.completed_at = datetime.utcnow()

    # Sync errors
    cloud_errors = values.get("errors")
    if cloud_errors:
        project.errors = cloud_errors

    # Extract intake fields (only once — skip if already done)
    existing_intake_count = db.query(CMEIntakeField).filter(
        CMEIntakeField.project_id == project.id,
    ).count()
    intake_fields_created = 0
    if existing_intake_count == 0 and project.intake:
        intake_fields_created = _extract_intake_fields(project.id, project.intake, db)

    db.commit()
    db.refresh(project)

    # Generate embeddings in background (non-blocking)
    try:
        outputs_needing_embeddings = db.query(CMEAgentOutput).filter(
            CMEAgentOutput.project_id == project.id,
            CMEAgentOutput.document_text.isnot(None),
            CMEAgentOutput.embedding.is_(None),
        ).all()

        for ao in outputs_needing_embeddings:
            emb = await _generate_embedding(ao.document_text)
            if emb:
                db.execute(
                    CMEAgentOutput.__table__.update()
                    .where(CMEAgentOutput.id == ao.id)
                    .values(embedding=emb)
                )

        docs_needing_embeddings = db.query(CMEDocument).filter(
            CMEDocument.project_id == project.id,
            CMEDocument.embedding.is_(None),
        ).all()

        for doc in docs_needing_embeddings:
            emb = await _generate_embedding(doc.content_text)
            if emb:
                db.execute(
                    CMEDocument.__table__.update()
                    .where(CMEDocument.id == doc.id)
                    .values(embedding=emb)
                )

        refs_needing_embeddings = db.query(CMESourceReference).filter(
            CMESourceReference.project_id == project.id,
            CMESourceReference.embedding.is_(None),
            CMESourceReference.abstract.isnot(None),
        ).all()

        for ref in refs_needing_embeddings:
            ref_text = f"{ref.title} {ref.authors or ''} {ref.abstract or ''}"
            emb = await _generate_embedding(ref_text)
            if emb:
                db.execute(
                    CMESourceReference.__table__.update()
                    .where(CMESourceReference.id == ref.id)
                    .values(embedding=emb)
                )

        db.commit()
    except Exception as e:
        logger.warning(f"Embedding generation failed (non-blocking): {e}")

    return {
        "project_id": str(project.id),
        "old_status": old_status,
        "new_status": new_status,
        "thread_status": thread_status,
        "agents_completed": agents_completed,
        "documents_created": documents_created,
        "references_created": references_created,
        "intake_fields_created": intake_fields_created,
        "progress_percent": project.progress_percent,
    }


@router.post("/projects/{project_id}/sync")
async def sync_project_from_cloud(project_id: str, db: Session = Depends(get_db)):
    """Poll LangGraph Cloud for thread state and sync to registry database."""
    project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")

    if not project.pipeline_thread_id:
        raise HTTPException(status_code=400, detail="No pipeline thread ID — pipeline not started")

    thread_data = await _fetch_thread_from_cloud(project.pipeline_thread_id)
    if not thread_data:
        raise HTTPException(status_code=502, detail="Failed to fetch thread from LangGraph Cloud")

    result = await _sync_project_from_thread(project, thread_data, db)
    return result


@router.post("/sync-active")
async def sync_all_active_projects(db: Session = Depends(get_db)):
    """Sync all processing/review projects from LangGraph Cloud. Call on interval or on-demand."""
    projects = db.query(CMEProject).filter(
        CMEProject.status.in_(["processing", "review", "awaiting_review"]),
        CMEProject.pipeline_thread_id.isnot(None),
    ).all()

    results = []
    for project in projects:
        thread_data = await _fetch_thread_from_cloud(project.pipeline_thread_id)
        if thread_data:
            result = await _sync_project_from_thread(project, thread_data, db)
            results.append(result)
        else:
            results.append({"project_id": str(project.id), "error": "cloud_unreachable"})

    return {"synced": len(results), "results": results}


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
    """Get current execution status of the CME pipeline.

    Auto-syncs from LangGraph Cloud when project is processing/review.
    """
    start = time.time()
    try:
        project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="CME project not found")

        # Auto-sync from Cloud when project is actively running
        if project.status in ("processing", "review") and project.pipeline_thread_id:
            try:
                thread_data = await _fetch_thread_from_cloud(project.pipeline_thread_id)
                if thread_data:
                    await _sync_project_from_thread(project, thread_data, db)
            except Exception as sync_err:
                logger.warning(f"Cloud sync failed during status poll: {sync_err}")

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
    project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="CME project not found")

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
        "current_step": current_step
    }


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
    query = db.query(CMEReviewerConfig)
    if active_only:
        query = query.filter(CMEReviewerConfig.is_active == True)
    reviewers = query.all()
    
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
    existing = db.query(CMEReviewerConfig).filter(CMEReviewerConfig.email == reviewer.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Reviewer with this email already exists")
    
    db_reviewer = CMEReviewerConfig(
        email=reviewer.email,
        display_name=reviewer.display_name,
        notify_email=reviewer.notify_email,
        notify_google_chat=reviewer.notify_google_chat,
        google_chat_webhook_url=reviewer.google_chat_webhook_url,
        max_concurrent_reviews=reviewer.max_concurrent_reviews
    )
    db.add(db_reviewer)
    db.commit()
    db.refresh(db_reviewer)
    
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
    reviewer = db.query(CMEReviewerConfig).filter(CMEReviewerConfig.id == reviewer_id).first()
    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer not found")
    
    reviewer.is_active = False
    db.commit()


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
    project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if len(request.reviewer_emails) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 reviewers allowed (R2)")
    
    # Validate all reviewers exist and are active
    assignments = []
    for order, email in enumerate(request.reviewer_emails, start=1):
        reviewer = db.query(CMEReviewerConfig).filter(
            CMEReviewerConfig.email == email,
            CMEReviewerConfig.is_active == True
        ).first()
        if not reviewer:
            raise HTTPException(status_code=400, detail=f"Reviewer not found or inactive: {email}")
        
        # Create assignment
        now = datetime.utcnow()
        sla_hours = 24  # Decision R3
        
        assignment = CMEReviewAssignment(
            project_id=project.id,
            reviewer_id=reviewer.id,
            reviewer_order=order,
            status="active" if order == 1 else "pending",
            assigned_at=now if order == 1 else None,
            sla_deadline=datetime.utcnow().replace(hour=now.hour + sla_hours) if order == 1 else None
        )
        db.add(assignment)
        assignments.append({
            "email": email,
            "order": order,
            "status": assignment.status
        })
    
    # Update project status
    project.status = "review"
    project.human_review_status = "pending"
    db.commit()
    
    return {
        "project_id": project_id,
        "status": "submitted_for_review",
        "assignments": assignments
    }


@router.get("/projects/{project_id}/review-status")
async def get_review_status(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Get current review status for a project"""
    project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    assignments = db.query(CMEReviewAssignment).filter(
        CMEReviewAssignment.project_id == project_id
    ).order_by(CMEReviewAssignment.reviewer_order).all()
    
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
    # Find the active assignment for this reviewer
    assignment = db.query(CMEReviewAssignment).join(CMEReviewerConfig).filter(
        CMEReviewAssignment.project_id == project_id,
        CMEReviewerConfig.email == reviewer_email,
        CMEReviewAssignment.status == "active"
    ).first()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="No active review assignment found for this reviewer")
    
    now = datetime.utcnow()
    
    # Update assignment
    assignment.status = request.decision
    assignment.decision = request.decision
    assignment.notes = request.notes
    assignment.annotations = request.annotations or []
    assignment.completed_at = now
    
    project = db.query(CMEProject).filter(CMEProject.id == project_id).first()
    
    if request.decision == "approved":
        # Check if this is the final reviewer
        next_assignment = db.query(CMEReviewAssignment).filter(
            CMEReviewAssignment.project_id == project_id,
            CMEReviewAssignment.status == "pending"
        ).order_by(CMEReviewAssignment.reviewer_order).first()
        
        if next_assignment:
            # Activate next reviewer
            next_assignment.status = "active"
            next_assignment.assigned_at = now
            from datetime import timedelta
            next_assignment.sla_deadline = now + timedelta(hours=24)
        else:
            # All reviewers approved
            project.human_review_status = "approved"
            project.status = "complete"
            project.reviewed_at = now
            project.completed_at = now
    else:
        # Revision requested
        project.human_review_status = "revision_requested"
        project.human_review_notes = request.notes
    
    db.commit()
    
    return {
        "project_id": project_id,
        "decision": request.decision,
        "assignment_id": str(assignment.id),
        "project_status": project.status
    }


@router.get("/my-reviews")
async def get_my_reviews(
    reviewer_email: str,  # In production, get from auth token
    status_filter: Optional[str] = "active",
    db: Session = Depends(get_db)
):
    """Get pending reviews for current user"""
    query = db.query(CMEReviewAssignment).join(CMEReviewerConfig).filter(
        CMEReviewerConfig.email == reviewer_email
    )
    
    if status_filter:
        query = query.filter(CMEReviewAssignment.status == status_filter)
    
    assignments = query.order_by(CMEReviewAssignment.assigned_at).all()
    
    result = []
    for a in assignments:
        project = db.query(CMEProject).filter(CMEProject.id == a.project_id).first()
        result.append({
            "assignment_id": str(a.id),
            "project_id": str(a.project_id),
            "project_name": project.name if project else "Unknown",
            "order": a.reviewer_order,
            "status": a.status,
            "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
            "sla_deadline": a.sla_deadline.isoformat() if a.sla_deadline else None,
            "hours_remaining": ((a.sla_deadline - datetime.utcnow()).total_seconds() / 3600) if a.sla_deadline else None
        })
    
    return {"reviews": result, "count": len(result)}
