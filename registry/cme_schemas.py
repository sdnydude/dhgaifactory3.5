"""CME Pydantic schemas — intake sections, response models, and enums."""
from typing import List, Literal, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


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
    ARCHIVED = "archived"


# =============================================================================
# INTAKE SECTIONS
# =============================================================================

class SectionA_ProjectBasics(BaseModel):
    """Section A: Project Basics (7 fields)"""
    project_name: str = Field(..., min_length=5, max_length=200)
    therapeutic_area: List[str] = Field(..., min_length=1, max_length=5)
    disease_state: List[str] = Field(..., min_length=1, max_length=10)
    target_audience_primary: List[str] = Field(..., min_length=1, max_length=5)
    target_audience_secondary: Optional[List[str]] = Field(None, max_length=3)
    target_hcp_types: Optional[List[str]] = Field(None, description="HCP credential types (MD/DO, NP, PA-C)")
    additional_context: Optional[str] = Field(None, max_length=5000)


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


class CharacterConfig(BaseModel):
    """Cold open character configuration: auto-generate or provide guided attributes."""
    mode: Literal["auto", "guided"] = "auto"
    name: Optional[str] = Field(None, max_length=100, description="Character name")
    age: Optional[int] = Field(None, ge=1, le=120, description="Character age")
    gender: Optional[str] = Field(None, description="Male, Female, Non-binary, Not specified")
    ethnicity: Optional[str] = Field(None, max_length=100, description="e.g., Nigerian-American")
    occupation: Optional[str] = Field(None, max_length=200, description="e.g., Long-haul truck driver")
    presenting_complaint: Optional[str] = Field(None, max_length=1000, description="What brought them in")
    clinical_history: Optional[str] = Field(None, max_length=2000, description="Prior diagnoses, treatments, timeline")


class SectionJ_Additional(BaseModel):
    """Section J: Additional Information (3 fields + character config)"""
    special_instructions: Optional[str] = None
    reference_materials: Optional[List[str]] = None
    internal_notes: Optional[str] = None
    character: Optional[CharacterConfig] = None


# =============================================================================
# INTAKE SUBMISSION
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


class PrefillRequest(BaseModel):
    """Section A fields needed to trigger intake prefill."""
    project_name: str = Field(..., min_length=5, max_length=200)
    therapeutic_area: List[str] = Field(..., min_length=1, max_length=5)
    disease_state: List[str] = Field(..., min_length=1, max_length=10)
    target_audience_primary: List[str] = Field(..., min_length=1, max_length=5)
    target_hcp_types: Optional[List[str]] = Field(None)
    additional_context: Optional[str] = Field(None, max_length=5000)


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
    intake_version: int
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
    document_text: Optional[str] = None


# =============================================================================
# STATS RESPONSE MODELS
# =============================================================================

class AgentCompletionItem(BaseModel):
    agent: str
    count: int
    avg_quality: Optional[float] = None


class DocumentThroughputItem(BaseModel):
    type: str
    count: int
    avg_words: int = 0
    avg_quality: Optional[float] = None


class ActivePipelineItem(BaseModel):
    project_id: str
    name: str
    status: str
    current_agent: Optional[str] = None
    progress_percent: int = 0


class PipelineStatsResponse(BaseModel):
    projects_by_status: Dict[str, int]
    total_projects: int
    total_runs: int
    total_documents: int
    total_references: int
    agent_completion: List[AgentCompletionItem]
    document_throughput: List[DocumentThroughputItem]
    avg_run_duration_sec: Optional[float] = None
    active_pipelines: List[ActivePipelineItem]


class ServiceItem(BaseModel):
    name: str
    domain: str


class ServiceHealthResponse(BaseModel):
    service_count: int
    services: List[ServiceItem]
    db_active_connections: int
    table_counts: Dict[str, int]
