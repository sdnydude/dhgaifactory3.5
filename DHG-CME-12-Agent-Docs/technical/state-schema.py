"""
DHG CME 12-Agent System - State Schema
======================================
Central state definition for LangGraph StateGraph orchestration.
All agents read from and write to this shared state object.

Usage:
    from state_schema import CMEGrantState, create_initial_state
"""

from typing import TypedDict, Optional, List, Literal
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class ProjectStatus(str, Enum):
    """Pipeline execution status."""
    INTAKE = "intake"
    RESEARCH = "research"
    CLINICAL = "clinical"
    GAP_ANALYSIS = "gap_analysis"
    NEEDS_ASSESSMENT = "needs_assessment"
    PROSE_REVIEW_1 = "prose_review_1"
    LEARNING_OBJECTIVES = "learning_objectives"
    CURRICULUM = "curriculum"
    PROTOCOL = "protocol"
    MARKETING = "marketing"
    GRANT_WRITING = "grant_writing"
    PROSE_REVIEW_2 = "prose_review_2"
    COMPLIANCE = "compliance"
    HUMAN_REVIEW = "human_review"
    COMPLETE = "complete"
    FAILED = "failed"


class HumanReviewStatus(str, Enum):
    """Human review gate status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class MooreLevel(str, Enum):
    """Moore's Expanded Outcomes Framework levels."""
    LEVEL_1 = "1"      # Participation
    LEVEL_2 = "2"      # Satisfaction
    LEVEL_3A = "3a"    # Declarative Knowledge
    LEVEL_3B = "3b"    # Procedural Knowledge
    LEVEL_4 = "4"      # Competence
    LEVEL_5 = "5"      # Performance
    LEVEL_6 = "6"      # Patient Health
    LEVEL_7 = "7"      # Community Health


class BarrierType(str, Enum):
    """CME barrier classification."""
    KNOWLEDGE = "knowledge"
    SKILL = "skill"
    ATTITUDE = "attitude"
    SYSTEM = "system"
    PATIENT = "patient"


# =============================================================================
# INTAKE FORM SECTIONS (47 Fields across 10 Sections)
# =============================================================================

class SectionA_ProjectBasics(TypedDict):
    """Section A: Project Basics (5 fields)"""
    project_name: str
    therapeutic_area: str
    disease_state: str
    target_audience_primary: List[str]
    target_audience_secondary: Optional[List[str]]


class SectionB_EducationalContext(TypedDict):
    """Section B: Educational Context (6 fields)"""
    identified_gaps: List[str]
    gap_evidence_sources: List[str]
    desired_outcomes: List[str]
    moore_level_target: MooreLevel
    practice_change_goals: List[str]
    patient_impact_goals: List[str]


class SectionC_SupporterInfo(TypedDict):
    """Section C: Commercial Supporter Information (4 fields)"""
    supporter_company: str
    supporter_products: List[str]
    supporter_therapeutic_focus: str
    grant_amount_requested: float


class SectionD_ActivityFormat(TypedDict):
    """Section D: Activity Format (5 fields)"""
    format_type: Literal["live", "enduring", "blended", "series"]
    format_details: str
    duration_hours: float
    credits_requested: float
    delivery_platform: Optional[str]


class SectionE_Accreditation(TypedDict):
    """Section E: Accreditation (4 fields)"""
    accreditation_types: List[str]  # ["AMA PRA Category 1", "ANCC", "ACPE", etc.]
    joint_accreditation: bool
    moc_points_requested: bool
    off_label_content: bool


class SectionF_ClinicalContent(TypedDict):
    """Section F: Clinical Content Focus (6 fields)"""
    key_clinical_topics: List[str]
    treatment_focus: List[str]
    competitor_products: List[str]
    guideline_references: List[str]
    emerging_data: Optional[str]
    controversy_areas: Optional[List[str]]


class SectionG_FacultySpecs(TypedDict):
    """Section G: Faculty Specifications (4 fields)"""
    faculty_count: int
    specialty_requirements: List[str]
    geographic_diversity: bool
    kol_level: Literal["national", "regional", "community"]


class SectionH_AudienceDetails(TypedDict):
    """Section H: Target Audience Details (5 fields)"""
    audience_size_target: int
    practice_settings: List[str]
    experience_level: Literal["early_career", "mid_career", "experienced", "mixed"]
    geographic_focus: Optional[str]
    prior_knowledge_assumed: str


class SectionI_Timeline(TypedDict):
    """Section I: Timeline (4 fields)"""
    submission_deadline: str  # ISO date
    target_launch_date: str   # ISO date
    grant_period_months: int
    milestone_dates: Optional[dict]


class SectionJ_SpecialRequirements(TypedDict):
    """Section J: Special Requirements (4 fields)"""
    health_equity_focus: bool
    health_equity_populations: Optional[List[str]]
    innovation_requirements: Optional[str]
    supporter_restrictions: Optional[str]


class IntakeData(TypedDict):
    """Complete intake form data (47 fields)."""
    section_a: SectionA_ProjectBasics
    section_b: SectionB_EducationalContext
    section_c: SectionC_SupporterInfo
    section_d: SectionD_ActivityFormat
    section_e: SectionE_Accreditation
    section_f: SectionF_ClinicalContent
    section_g: SectionG_FacultySpecs
    section_h: SectionH_AudienceDetails
    section_i: SectionI_Timeline
    section_j: SectionJ_SpecialRequirements


# =============================================================================
# AGENT OUTPUT SCHEMAS
# =============================================================================

class Citation(TypedDict):
    """Standard citation format."""
    id: str
    authors: str
    title: str
    journal: str
    year: int
    doi: Optional[str]
    pmid: Optional[str]
    citation_type: Literal["primary", "guideline", "registry", "meta_analysis"]


class ResearchOutput(TypedDict):
    """Agent 2: Research Agent output."""
    epidemiology: dict
    economic_burden: dict
    treatment_landscape: dict
    market_intelligence: dict
    literature_synthesis: str
    citations: List[Citation]
    metadata: dict


class ClinicalOutput(TypedDict):
    """Agent 3: Clinical Practice Agent output."""
    standard_of_care: dict
    real_world_practice: dict
    practice_barriers: List[dict]
    specialty_perspectives: List[dict]
    setting_variations: dict
    metadata: dict


class Gap(TypedDict):
    """Individual educational gap."""
    gap_id: str
    gap_statement: str
    gap_category: BarrierType
    evidence_summary: str
    quantified_magnitude: str
    patient_impact: str
    educational_addressability: str
    priority_score: int
    supporting_citations: List[str]


class GapAnalysisOutput(TypedDict):
    """Agent 4: Gap Analysis Agent output."""
    gaps: List[Gap]
    prioritization_rationale: str
    gap_interrelationships: str
    educational_opportunity_summary: str
    metadata: dict


class NeedsAssessmentOutput(TypedDict):
    """Agent 5: Needs Assessment Agent output."""
    document_text: str  # Full 3,100+ word document
    cold_open: str
    character_name: str
    character_details: dict
    word_count: int
    section_word_counts: dict
    metadata: dict


class LearningObjective(TypedDict):
    """Individual learning objective."""
    objective_id: str
    objective_text: str
    moore_level: MooreLevel
    action_verb: str
    gap_alignment: List[str]
    measurement_plan: dict
    patient_outcome_link: str


class LearningObjectivesOutput(TypedDict):
    """Agent 6: Learning Objectives Agent output."""
    objectives: List[LearningObjective]
    moore_level_distribution: dict
    gap_coverage_matrix: dict
    metadata: dict


class CurriculumOutput(TypedDict):
    """Agent 7: Curriculum Design Agent output."""
    format_recommendation: dict
    content_outline: List[dict]
    instructional_methods: List[dict]
    case_studies: List[dict]
    faculty_specifications: dict
    innovation_section: str  # 500+ words
    assessment_strategy: dict
    metadata: dict


class ProtocolOutput(TypedDict):
    """Agent 8: Research Protocol Agent output."""
    study_design: dict
    population: dict
    outcomes: dict
    instruments: List[dict]
    data_collection: dict
    statistical_plan: dict
    ethics_considerations: str
    limitations: List[str]
    timeline: dict
    metadata: dict


class MarketingOutput(TypedDict):
    """Agent 9: Marketing Plan Agent output."""
    channel_strategies: List[dict]
    budget_allocation: dict
    timeline: dict
    kpis: List[dict]
    compliance_considerations: str
    metadata: dict


class GrantPackageOutput(TypedDict):
    """Agent 10: Grant Writer Agent output."""
    cover_letter: str
    executive_summary: str
    needs_assessment: str
    learning_objectives_section: str
    curriculum_innovation: str
    faculty_section: str
    outcomes_evaluation: str
    marketing_section: str
    budget_narrative: str
    budget_table: dict
    organizational_qualifications: str
    independence_compliance: str
    appendices: List[dict]
    metadata: dict


class ProseQualityScore(TypedDict):
    """Agent 11: Prose Quality Agent output."""
    pass_number: int
    passed: bool
    score: float
    prose_density: dict
    word_counts: dict
    ai_pattern_detection: dict
    cold_open_analysis: Optional[dict]
    character_thread: dict
    revision_instructions: Optional[dict]
    timestamp: str


class ComplianceScore(TypedDict):
    """Agent 12: Compliance Review Agent output."""
    compliant: bool
    score: float
    accme_standards: dict
    independence_analysis: dict
    fair_balance_analysis: dict
    commercial_bias_detection: dict
    disclosure_verification: dict
    remediation_required: Optional[dict]
    certification_ready: bool
    timestamp: str


# =============================================================================
# EXECUTION TRACKING
# =============================================================================

class ExecutionRecord(TypedDict):
    """Record of agent execution."""
    agent_name: str
    started_at: str
    completed_at: Optional[str]
    status: Literal["running", "completed", "failed", "retrying"]
    duration_seconds: Optional[float]
    tokens_used: Optional[int]
    error_message: Optional[str]


class ErrorRecord(TypedDict):
    """Error tracking."""
    timestamp: str
    agent_name: str
    error_type: str
    error_message: str
    recoverable: bool
    retry_attempted: bool


# =============================================================================
# MAIN STATE SCHEMA
# =============================================================================

class CMEGrantState(TypedDict):
    """
    Central state object for the DHG CME 12-Agent system.
    
    This TypedDict is used by LangGraph's StateGraph to manage
    all data flowing through the pipeline. Each agent reads from
    and writes to specific fields.
    """
    
    # -------------------------------------------------------------------------
    # Project Metadata
    # -------------------------------------------------------------------------
    project_id: str
    project_name: str
    created_at: str
    updated_at: str
    status: ProjectStatus
    
    # -------------------------------------------------------------------------
    # Intake Data (47 fields across 10 sections)
    # -------------------------------------------------------------------------
    intake: IntakeData
    
    # -------------------------------------------------------------------------
    # Agent Outputs
    # -------------------------------------------------------------------------
    research_output: Optional[ResearchOutput]
    clinical_output: Optional[ClinicalOutput]
    gap_analysis_output: Optional[GapAnalysisOutput]
    needs_assessment_output: Optional[NeedsAssessmentOutput]
    learning_objectives_output: Optional[LearningObjectivesOutput]
    curriculum_output: Optional[CurriculumOutput]
    protocol_output: Optional[ProtocolOutput]
    marketing_output: Optional[MarketingOutput]
    grant_package_output: Optional[GrantPackageOutput]
    
    # -------------------------------------------------------------------------
    # Quality Tracking
    # -------------------------------------------------------------------------
    prose_quality_scores: List[ProseQualityScore]
    compliance_score: Optional[ComplianceScore]
    
    # -------------------------------------------------------------------------
    # Execution Tracking
    # -------------------------------------------------------------------------
    current_agent: Optional[str]
    execution_history: List[ExecutionRecord]
    errors: List[ErrorRecord]
    retry_count: int
    
    # -------------------------------------------------------------------------
    # Human Review
    # -------------------------------------------------------------------------
    human_review_status: Optional[HumanReviewStatus]
    human_review_notes: Optional[str]
    human_reviewer: Optional[str]
    human_review_timestamp: Optional[str]


# =============================================================================
# STATE INITIALIZATION
# =============================================================================

def create_initial_state(
    project_id: str,
    project_name: str,
    intake_data: IntakeData
) -> CMEGrantState:
    """
    Create initial state object for a new grant project.
    
    Args:
        project_id: Unique project identifier
        project_name: Human-readable project name
        intake_data: Validated intake form data
        
    Returns:
        Initialized CMEGrantState ready for pipeline execution
    """
    now = datetime.utcnow().isoformat()
    
    return CMEGrantState(
        # Metadata
        project_id=project_id,
        project_name=project_name,
        created_at=now,
        updated_at=now,
        status=ProjectStatus.INTAKE,
        
        # Intake
        intake=intake_data,
        
        # Agent outputs (all None initially)
        research_output=None,
        clinical_output=None,
        gap_analysis_output=None,
        needs_assessment_output=None,
        learning_objectives_output=None,
        curriculum_output=None,
        protocol_output=None,
        marketing_output=None,
        grant_package_output=None,
        
        # Quality tracking
        prose_quality_scores=[],
        compliance_score=None,
        
        # Execution tracking
        current_agent=None,
        execution_history=[],
        errors=[],
        retry_count=0,
        
        # Human review
        human_review_status=None,
        human_review_notes=None,
        human_reviewer=None,
        human_review_timestamp=None,
    )


# =============================================================================
# STATE VALIDATION
# =============================================================================

def validate_state_for_agent(state: CMEGrantState, agent_name: str) -> bool:
    """
    Validate that state has required data for a specific agent.
    
    Args:
        state: Current state object
        agent_name: Name of agent about to execute
        
    Returns:
        True if state is valid for agent execution
        
    Raises:
        ValueError if required data is missing
    """
    requirements = {
        "research_agent": ["intake"],
        "clinical_agent": ["intake"],
        "gap_analysis_agent": ["research_output", "clinical_output"],
        "needs_assessment_agent": ["gap_analysis_output"],
        "prose_quality_agent": ["needs_assessment_output"],  # or grant_package_output
        "learning_objectives_agent": ["needs_assessment_output", "gap_analysis_output"],
        "curriculum_agent": ["learning_objectives_output"],
        "protocol_agent": ["learning_objectives_output"],
        "marketing_agent": ["learning_objectives_output", "intake"],
        "grant_writer_agent": ["curriculum_output", "protocol_output", "marketing_output"],
        "compliance_agent": ["grant_package_output"],
    }
    
    required = requirements.get(agent_name, [])
    
    for field in required:
        if state.get(field) is None:
            raise ValueError(f"Agent {agent_name} requires {field} but it is None")
    
    return True


# =============================================================================
# STATE UPDATES
# =============================================================================

def update_state_status(state: CMEGrantState, new_status: ProjectStatus) -> CMEGrantState:
    """Update state status and timestamp."""
    state["status"] = new_status
    state["updated_at"] = datetime.utcnow().isoformat()
    return state


def add_execution_record(
    state: CMEGrantState,
    agent_name: str,
    status: str,
    duration: Optional[float] = None,
    tokens: Optional[int] = None,
    error: Optional[str] = None
) -> CMEGrantState:
    """Add execution record to state."""
    record = ExecutionRecord(
        agent_name=agent_name,
        started_at=datetime.utcnow().isoformat(),
        completed_at=datetime.utcnow().isoformat() if status != "running" else None,
        status=status,
        duration_seconds=duration,
        tokens_used=tokens,
        error_message=error,
    )
    state["execution_history"].append(record)
    state["updated_at"] = datetime.utcnow().isoformat()
    return state


def add_error_record(
    state: CMEGrantState,
    agent_name: str,
    error_type: str,
    error_message: str,
    recoverable: bool = True
) -> CMEGrantState:
    """Add error record to state."""
    record = ErrorRecord(
        timestamp=datetime.utcnow().isoformat(),
        agent_name=agent_name,
        error_type=error_type,
        error_message=error_message,
        recoverable=recoverable,
        retry_attempted=False,
    )
    state["errors"].append(record)
    state["updated_at"] = datetime.utcnow().isoformat()
    return state
