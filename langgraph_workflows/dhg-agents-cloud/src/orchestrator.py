"""
Recipe-Based Orchestrator - CME Grant Pipeline
===============================================
Composable agent chains ("recipes") for different output types.

Recipes:
- needs_graph: Research → Gap → LO → Needs Assessment
- curriculum_graph: Needs → Curriculum + Protocol + Marketing
- grant_graph: All 11 agents + Prose QA

LangGraph Cloud Ready:
- Each recipe is a compiled graph exported at module level
- All use CMEPipelineState for unified state management
- PostgresSaver for checkpointing and recovery
- Parallel execution for independent agents

Decision #10: Recipe-Based Orchestrator (confirmed 2026-02-04)
"""

import os
import sys
import operator
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Annotated, Literal
from typing_extensions import TypedDict
from enum import Enum
import httpx

# Ensure src/ directory is on Python path for dynamic agent imports
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt, Command

# PostgresSaver is optional - fallback to in-memory if not available
try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    POSTGRES_AVAILABLE = True
except ImportError:
    AsyncPostgresSaver = None
    POSTGRES_AVAILABLE = False

from langsmith import traceable
import logging

# OpenTelemetry tracing (dual-export with LangSmith)
from tracing import get_tracer, traced_node

# Drive sync hook — enqueues drive_sync jobs at pipeline milestones via the
# registry webhook (fire-and-forget; never raises).
from drive_sync_hook import enqueue_drive_sync

_tracer = get_tracer("orchestrator")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not POSTGRES_AVAILABLE:
    logger.warning("langgraph-checkpoint-postgres not installed. Checkpointing will use in-memory storage.")


# =============================================================================
# CONFIGURATION
# =============================================================================

# Database URL for checkpointing (from environment or default)
DATABASE_URL = os.getenv(
    "POSTGRES_CONNECTION_STRING",
    os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/langgraph")
)

# Retry configuration
MAX_RETRIES = {
    "agent_failure": 3,
    "validation_failure": 2,
    "quality_failure": 3,
    "timeout": 1,
    "external_failure": 5
}

# Timeout configuration (seconds)
AGENT_TIMEOUT = 300  # 5 minutes default

# Human review toggle — set SKIP_HUMAN_REVIEW=true to auto-approve and run end-to-end
SKIP_HUMAN_REVIEW = os.getenv("SKIP_HUMAN_REVIEW", "true").lower() in ("true", "1", "yes")

if SKIP_HUMAN_REVIEW:
    logger.warning("SKIP_HUMAN_REVIEW=true — all pipelines will auto-approve without human review")


# =============================================================================
# STATE SCHEMA
# =============================================================================

class PipelineStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_REVIEW = "awaiting_review"
    REVISION_REQUIRED = "revision_required"
    APPROVED = "approved"
    COMPLETE = "complete"
    FAILED = "failed"


class ErrorCategory(Enum):
    AGENT_FAILURE = "agent_failure"
    VALIDATION_FAILURE = "validation_failure"
    QUALITY_FAILURE = "quality_failure"
    TIMEOUT = "timeout"
    EXTERNAL_FAILURE = "external_failure"


class CMEPipelineState(TypedDict):
    """Unified state for all CME pipeline recipes."""
    
    # === PROJECT IDENTITY ===
    project_id: str
    project_name: str
    status: str
    created_at: str
    updated_at: str
    
    # === INTAKE DATA ===
    intake_data: Dict[str, Any]
    intake_validated: bool
    
    # === AGENT OUTPUTS (accumulated as pipeline progresses) ===
    research_output: Optional[Dict[str, Any]]
    clinical_output: Optional[Dict[str, Any]]
    gap_analysis_output: Optional[Dict[str, Any]]
    needs_assessment_output: Optional[Dict[str, Any]]
    learning_objectives_output: Optional[Dict[str, Any]]
    curriculum_output: Optional[Dict[str, Any]]
    protocol_output: Optional[Dict[str, Any]]
    marketing_output: Optional[Dict[str, Any]]
    grant_package_output: Optional[Dict[str, Any]]
    
    # === QUALITY RESULTS ===
    prose_quality_pass_1: Optional[Dict[str, Any]]
    prose_quality_pass_2: Optional[Dict[str, Any]]
    compliance_result: Optional[Dict[str, Any]]
    
    # === HUMAN REVIEW ===
    human_review_status: Optional[str]  # pending, approved, revision_requested, rejected
    human_review_notes: Optional[str]
    human_reviewer: Optional[str]

    # === REVIEW LOOP ===
    review_comments: List[Dict[str, Any]]  # [{selectedText, comment, startOffset, endOffset, document_id, timestamp}]
    review_round: int  # Tracks revision cycle (max 3)
    
    # === CONTROL ===
    current_step: str
    retry_count: int
    messages: Annotated[list, add_messages]
    errors: List[Dict[str, Any]]  # [{error_type, message, agent, timestamp}]
    
    # === CHECKPOINTING ===
    last_checkpoint: str
    checkpoint_agent: str


# =============================================================================
# ERROR HANDLING
# =============================================================================

def create_error_record(
    error_type: str,
    message: str,
    agent: str,
    context: Optional[Dict] = None
) -> Dict[str, Any]:
    """Create a standardized error record."""
    return {
        "error_type": error_type,
        "message": str(message)[:500],  # Truncate long messages
        "agent": agent,
        "timestamp": datetime.now().isoformat(),
        "context": context or {}
    }


def should_retry(state: CMEPipelineState, error_type: str, agent_name: str) -> bool:
    """Determine if we should retry based on error type and retry count."""
    # Count retries for this specific agent and error type
    agent_errors = [e for e in state.get("errors", []) 
                    if e.get("agent") == agent_name and e.get("error_type") == error_type]
    
    max_retries = MAX_RETRIES.get(error_type, 3)
    return len(agent_errors) < max_retries


# =============================================================================
# AGENT IMPORTS (lazy loaded to avoid circular imports)
# =============================================================================

_AGENT_MODULE_MAP = {
    "research": "research_agent",
    "clinical": "clinical_practice_agent",
    "gap_analysis": "gap_analysis_agent",
    "needs_assessment": "needs_assessment_agent",
    "learning_objectives": "learning_objectives_agent",
    "curriculum": "curriculum_design_agent",
    "protocol": "research_protocol_agent",
    "marketing": "marketing_plan_agent",
    "grant_writer": "grant_writer_agent",
    "prose_quality": "prose_quality_agent",
    "compliance": "compliance_review_agent",
}


def get_agent_graph(agent_name: str):
    """Dynamically import agent graph. Uses importlib with explicit file path
    to work reliably in LangGraph Cloud where sys.path may differ at runtime."""
    import importlib
    import importlib.util

    module_name = _AGENT_MODULE_MAP.get(agent_name)
    if not module_name:
        raise ValueError(f"Unknown agent: {agent_name}")

    # Try standard import first (works if sys.path includes src/)
    try:
        mod = importlib.import_module(module_name)
        return mod.graph
    except ModuleNotFoundError:
        pass

    # Fallback: load from explicit file path
    src_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(src_dir, f"{module_name}.py")
    if not os.path.exists(module_path):
        raise ImportError(f"Agent module not found: {module_path}")

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    logger.info(f"Loaded agent {agent_name} from {module_path}")
    return mod.graph


# =============================================================================
# INTAKE FLATTENING — Transform sectioned form data to flat agent keys
# =============================================================================

# Type-coercion helpers used by flatten_intake.
#
# The frontend sends optional fields as JSON null rather than omitting them,
# which means dict.get(key, default) returns None (the default is NOT applied
# when the key exists with a None value). These helpers enforce type-correct
# empty defaults at every field boundary so downstream list()/join()/+ calls
# can never crash on None. Regression: project defeca67-… / run 019d8802-…
# crashed with TypeError at line 342 on list(None) for a field the frontend
# sent as explicit null. Fixed 2026-04-13.


def _section(intake: Dict[str, Any], key: str) -> Dict[str, Any]:
    """Read a section dict, coercing missing / None / wrong-type to {}."""
    value = intake.get(key)
    return value if isinstance(value, dict) else {}


def _list(section: Dict[str, Any], key: str) -> List[Any]:
    """Read a list field, coercing missing / None / wrong-type to []."""
    value = section.get(key)
    return value if isinstance(value, list) else []


def _str(section: Dict[str, Any], key: str, default: str = "") -> str:
    """Read a string field, coercing missing / None / wrong-type to default."""
    value = section.get(key)
    return value if isinstance(value, str) else default


def _bool(section: Dict[str, Any], key: str, default: bool = False) -> bool:
    """Read a bool field, coercing missing / None / wrong-type to default."""
    value = section.get(key)
    return value if isinstance(value, bool) else default


def _optional_int(section: Dict[str, Any], key: str) -> Optional[int]:
    """Read an int field, coercing missing / None / wrong-type to None."""
    value = section.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _joined(section: Dict[str, Any], key: str) -> str:
    """Read a field and render it as a comma-joined string.

    Handles lists (joined), strings (passed through), and None / missing
    (empty string). Regression-protects geographic_focus from becoming the
    literal string "None" when geo_restrictions is sent as JSON null.
    """
    value = section.get(key)
    if isinstance(value, list):
        return ", ".join(str(x) for x in value)
    if isinstance(value, str):
        return value
    return ""


def flatten_intake(intake: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten sectioned intake data into a flat dict for agent consumption.

    The frontend/registry stores intake as nested sections:
        {"section_a": {"project_name": ..., "therapeutic_area": ...}, "section_b": {...}, ...}

    Agents expect flat keys:
        {"therapeutic_area": ..., "target_audience": ..., "supporter_company": ...}

    Every field read goes through a type-coercion helper so explicit None
    values from the frontend (common for unfilled optional fields) never
    leak into downstream list()/join()/+ operations. If intake is already
    flat (no section_a key), it is returned as-is for backward compatibility.
    """
    # Already flat — nothing to do
    if "section_a" not in intake:
        return intake

    flat: Dict[str, Any] = {}

    # --- Section A: Project Basics ---
    a = _section(intake, "section_a")
    project_name = _str(a, "project_name")
    flat["project_name"] = project_name
    flat["project_title"] = project_name  # grant_writer uses project_title
    flat["activity_title"] = project_name  # needs_assessment uses activity_title
    flat["therapeutic_area"] = _joined(a, "therapeutic_area")
    flat["disease_state"] = _joined(a, "disease_state")
    primary_audience = _list(a, "target_audience_primary")
    flat["target_audience"] = ", ".join(str(x) for x in primary_audience)
    flat["target_audience_primary"] = primary_audience
    flat["target_audience_secondary"] = _list(a, "target_audience_secondary")
    flat["target_hcp_types"] = _list(a, "target_hcp_types")

    # --- Section B: Supporter Information ---
    b = _section(intake, "section_b")
    flat["supporter_company"] = _str(b, "supporter_name")  # agents use supporter_company
    flat["supporter_contact"] = _str(b, "supporter_contact_name")
    flat["supporter_contact_email"] = _str(b, "supporter_contact_email")
    amount = b.get("grant_amount_requested")
    flat["requested_amount"] = str(amount) if amount is not None else ""
    flat["grant_submission_deadline"] = _str(b, "grant_submission_deadline")

    # --- Section C: Educational Design ---
    c = _section(intake, "section_c")
    flat["learning_format"] = _str(c, "learning_format")
    flat["duration_minutes"] = _optional_int(c, "duration_minutes")
    flat["include_post_test"] = _bool(c, "include_post_test")
    flat["include_pre_test"] = _bool(c, "include_pre_test")
    flat["faculty_count"] = _optional_int(c, "faculty_count")
    flat["educational_format"] = flat["learning_format"]  # learning_objectives agent alias

    # --- Section D: Clinical Focus ---
    d = _section(intake, "section_d")
    clinical_topics = _list(d, "clinical_topics")
    flat["clinical_topics"] = clinical_topics
    flat["research_questions"] = clinical_topics  # research agent reads research_questions
    flat["treatment_modalities"] = _list(d, "treatment_modalities")
    flat["patient_population"] = _str(d, "patient_population")
    flat["stage_of_disease"] = _str(d, "stage_of_disease")
    flat["comorbidities"] = _list(d, "comorbidities")

    # --- Section E: Practice Gaps ---
    e = _section(intake, "section_e")
    flat["knowledge_gaps"] = _list(e, "knowledge_gaps")
    flat["competence_gaps"] = _list(e, "competence_gaps")
    flat["performance_gaps"] = _list(e, "performance_gaps")
    flat["gap_evidence_sources"] = _list(e, "gap_evidence_sources")
    flat["gap_priority"] = _str(e, "gap_priority")
    # Agents expect a single "known_gaps" list; intake splits into 3 types
    flat["known_gaps"] = flat["knowledge_gaps"] + flat["competence_gaps"] + flat["performance_gaps"]

    # --- Section F: Outcomes ---
    f = _section(intake, "section_f")
    flat["primary_outcomes"] = _list(f, "primary_outcomes")
    flat["secondary_outcomes"] = _list(f, "secondary_outcomes")
    flat["measurement_approach"] = _str(f, "measurement_approach")
    flat["moore_levels_target"] = _list(f, "moore_levels_target")
    flat["follow_up_timeline"] = _str(f, "follow_up_timeline")
    flat["outcome_goals"] = list(flat["primary_outcomes"])  # gap_analysis / learning_objectives alias
    moore_list = flat["moore_levels_target"]
    flat["moore_level_target"] = f"Level {moore_list[0]}" if moore_list else "Level 5"  # singular alias

    # --- Section G: Content Requirements ---
    g = _section(intake, "section_g")
    flat["key_messages"] = _list(g, "key_messages")
    flat["required_references"] = _list(g, "required_references")
    flat["excluded_topics"] = _list(g, "excluded_topics")
    competitor_products = _list(g, "competitor_products_to_mention")
    flat["competitor_products_to_mention"] = competitor_products
    flat["supporter_products"] = list(competitor_products)  # research agent alias
    flat["regulatory_considerations"] = _str(g, "regulatory_considerations")
    flat["competitor_products"] = list(competitor_products)  # compliance / research alias

    # --- Section H: Logistics ---
    h = _section(intake, "section_h")
    flat["target_launch_date"] = _str(h, "target_launch_date")
    flat["expiration_date"] = _str(h, "expiration_date")
    flat["distribution_channels"] = _list(h, "distribution_channels")
    flat["geo_restrictions"] = _list(h, "geo_restrictions")
    flat["geographic_focus"] = _joined(h, "geo_restrictions")
    flat["language_requirements"] = _list(h, "language_requirements")

    # --- Section I: Compliance ---
    i = _section(intake, "section_i")
    flat["accme_compliant"] = _bool(i, "accme_compliant")
    flat["financial_disclosure_required"] = _bool(i, "financial_disclosure_required")
    flat["off_label_discussion"] = _bool(i, "off_label_discussion")
    flat["commercial_support_acknowledgment"] = _bool(i, "commercial_support_acknowledgment")
    accreditation = ["ACCME"] if flat["accme_compliant"] else []
    flat["accreditation_types"] = accreditation
    flat["accreditation_statement"] = "ACCME-accredited" if flat["accme_compliant"] else ""

    # --- Section J: Additional ---
    j = _section(intake, "section_j")
    flat["special_instructions"] = _str(j, "special_instructions")
    flat["reference_materials"] = _list(j, "reference_materials")
    flat["internal_notes"] = _str(j, "internal_notes")

    # --- Character Config (nested in Section J) ---
    char = j.get("character") if isinstance(j, dict) else None
    if isinstance(char, dict) and char.get("mode") == "guided":
        flat["character_mode"] = "guided"
        flat["character_name"] = char.get("name") or ""
        flat["character_age"] = char.get("age")
        flat["character_gender"] = char.get("gender") or ""
        flat["character_ethnicity"] = char.get("ethnicity") or ""
        flat["character_occupation"] = char.get("occupation") or ""
        flat["character_presenting_complaint"] = char.get("presenting_complaint") or ""
        flat["character_clinical_history"] = char.get("clinical_history") or ""
    else:
        flat["character_mode"] = "auto"

    return flat


@traceable(name="initialize_pipeline", run_type="chain")
async def initialize_pipeline(state: CMEPipelineState) -> dict:
    """Flatten sectioned intake data into agent-compatible flat keys.

    This is the first node in every recipe graph. It transforms the nested
    section format from the registry into the flat key format that all
    downstream agent wrapper nodes expect.
    """
    raw_intake = state.get("intake_data", {})
    flat = flatten_intake(raw_intake)

    logger.info(
        f"Pipeline initialized: project={flat.get('project_name', 'unknown')}, "
        f"area={flat.get('therapeutic_area', 'unknown')}, "
        f"disease={flat.get('disease_state', 'unknown')}, "
        f"audience={flat.get('target_audience', 'unknown')}, "
        f"fields_flattened={len(flat)}"
    )

    return {
        "intake_data": flat,
        "status": PipelineStatus.IN_PROGRESS.value,
        "current_step": "initialized",
        "updated_at": datetime.now().isoformat(),
    }


# =============================================================================
# WRAPPER NODES
# Each wraps an agent graph, mapping pipeline state to agent state
# =============================================================================

# Single source of truth for the input shape each agent expects from intake.
# Both single-invoke wrappers and parallel composers MUST use these helpers so
# the field set never drifts again. (See: April 2026 disease_state drop bug.)

def _build_research_input(intake: dict) -> dict:
    """Build the research_agent input dict from flattened intake."""
    return {
        "therapeutic_area": intake.get("therapeutic_area", ""),
        "disease_state": intake.get("disease_state", ""),
        "target_audience": intake.get("target_audience", ""),
        "geographic_focus": intake.get("geographic_focus", ""),
        "supporter_company": intake.get("supporter_company", ""),
        "supporter_products": intake.get("supporter_products", []),
        "known_gaps": intake.get("known_gaps", []),
        "competitor_products": intake.get("competitor_products", []),
        "research_questions": intake.get("research_questions", []),
    }


def _build_clinical_input(intake: dict) -> dict:
    """Build the clinical_practice_agent input dict from flattened intake."""
    return {
        "therapeutic_area": intake.get("therapeutic_area", ""),
        "disease_state": intake.get("disease_state", ""),
        "target_audience": intake.get("target_audience", ""),
        "geographic_focus": intake.get("geographic_focus", ""),
        "practice_settings": intake.get("practice_settings", []),
        "known_gaps": intake.get("known_gaps", []),
        "known_barriers": intake.get("known_barriers", []),
    }


@traceable(name="run_research_agent", run_type="chain", metadata={"agent": "research"})
async def run_research_agent(state: CMEPipelineState) -> dict:
    """Run Research Agent and store output."""
    try:
        graph = get_agent_graph("research")

        intake = state.get("intake_data", {})
        agent_input = _build_research_input(intake)

        result = await asyncio.wait_for(
            graph.ainvoke(agent_input),
            timeout=AGENT_TIMEOUT
        )

        return {
            "research_output": result,
            "current_step": "research_complete",
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "research"
        }
    except asyncio.TimeoutError:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("timeout", "Research agent timed out", "research")
            ],
            "current_step": "research_timeout"
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "research")
            ],
            "current_step": "research_failed"
        }


@traceable(name="run_clinical_agent", run_type="chain", metadata={"agent": "clinical"})
async def run_clinical_agent(state: CMEPipelineState) -> dict:
    """Run Clinical Practice Agent and store output."""
    try:
        graph = get_agent_graph("clinical")

        intake = state.get("intake_data", {})
        agent_input = _build_clinical_input(intake)

        result = await asyncio.wait_for(
            graph.ainvoke(agent_input),
            timeout=AGENT_TIMEOUT
        )

        return {
            "clinical_output": result,
            "current_step": "clinical_complete",
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "clinical"
        }
    except asyncio.TimeoutError:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("timeout", "Clinical agent timed out", "clinical")
            ],
            "current_step": "clinical_timeout"
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "clinical")
            ],
            "current_step": "clinical_failed"
        }


@traceable(name="run_gap_analysis_agent", run_type="chain", metadata={"agent": "gap_analysis"})
async def run_gap_analysis_agent(state: CMEPipelineState) -> dict:
    """Run Gap Analysis Agent."""
    try:
        graph = get_agent_graph("gap_analysis")

        intake = state.get("intake_data", {})
        research_out = state.get("research_output") or {}
        clinical_out = state.get("clinical_output") or {}
        agent_input = {
            "research_report": research_out.get("research_report", {}),
            "clinical_practice_report": clinical_out.get("clinical_practice_report", {}),
            "therapeutic_area": intake.get("therapeutic_area", ""),
            "disease_state": intake.get("disease_state", ""),
            "target_audience": intake.get("target_audience", ""),
            "known_gaps": intake.get("known_gaps", []),
            "educational_priorities": intake.get("educational_priorities", []),
            "outcome_goals": intake.get("outcome_goals", []),
        }

        result = await asyncio.wait_for(
            graph.ainvoke(agent_input),
            timeout=AGENT_TIMEOUT
        )

        return {
            "gap_analysis_output": result,
            "current_step": "gap_analysis_complete",
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "gap_analysis"
        }
    except asyncio.TimeoutError:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("timeout", "Gap Analysis agent timed out", "gap_analysis")
            ],
            "current_step": "gap_analysis_timeout"
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "gap_analysis")
            ],
            "current_step": "gap_analysis_failed"
        }


@traceable(name="run_learning_objectives_agent", run_type="chain", metadata={"agent": "learning_objectives"})
async def run_learning_objectives_agent(state: CMEPipelineState) -> dict:
    """Run Learning Objectives Agent."""
    try:
        graph = get_agent_graph("learning_objectives")
        
        intake = state.get("intake_data", {})
        agent_input = {
            "gap_analysis_report": state.get("gap_analysis_output", {}),
            "needs_assessment_document": (state.get("needs_assessment_output") or {}).get("needs_assessment_document", ""),
            "target_audience": intake.get("target_audience", ""),
            "disease_state": intake.get("disease_state", ""),
            "therapeutic_area": intake.get("therapeutic_area", ""),
            "educational_format": intake.get("educational_format", ""),
            "outcome_goals": intake.get("outcome_goals", []),
            "moore_level_target": str(intake.get("moore_level_target", "Level 5")),
        }

        result = await asyncio.wait_for(
            graph.ainvoke(agent_input),
            timeout=AGENT_TIMEOUT
        )

        return {
            "learning_objectives_output": result,
            "current_step": "learning_objectives_complete",
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "learning_objectives"
        }
    except asyncio.TimeoutError:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("timeout", "Learning Objectives agent timed out", "learning_objectives")
            ],
            "current_step": "learning_objectives_timeout"
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "learning_objectives")
            ],
            "current_step": "learning_objectives_failed"
        }


@traceable(name="run_needs_assessment_agent", run_type="chain", metadata={"agent": "needs_assessment"})
@traced_node("orchestrator", "run_needs_assessment_agent")
async def run_needs_assessment_agent(state: CMEPipelineState) -> dict:
    """Run Needs Assessment Agent."""
    try:
        graph = get_agent_graph("needs_assessment")
        
        # Include feedback from prose quality if retrying
        prose_feedback = None
        if state.get("prose_quality_pass_1") and not state["prose_quality_pass_1"].get("overall_passed"):
            prose_feedback = state["prose_quality_pass_1"].get("feedback", "")
        
        intake = state.get("intake_data", {})
        research_out = state.get("research_output") or {}
        clinical_out = state.get("clinical_output") or {}
        gap_out = state.get("gap_analysis_output") or {}

        agent_input = {
            # Top-level fields the agent reads directly
            "therapeutic_area": intake.get("therapeutic_area", ""),
            "disease_state": intake.get("disease_state", ""),
            "target_audience": intake.get("target_audience", ""),
            "geographic_focus": intake.get("geographic_focus", ""),
            "activity_title": intake.get("project_name", ""),
            "accreditation_types": intake.get("accreditation_types", []),
            "intake_data": intake,
            # Extracted from upstream agent outputs
            "gaps": gap_out.get("prioritized_gaps") or gap_out.get("validated_gaps") or gap_out.get("raw_gaps", []),
            "research_summary": research_out.get("research_document", ""),
            "clinical_barriers": (clinical_out.get("clinical_practice_report") or {}).get("barriers", []),
            "epidemiology": research_out.get("epidemiology_data", {}),
            # Prose revision feedback
            "revision_feedback": prose_feedback,
        }

        result = await asyncio.wait_for(
            graph.ainvoke(agent_input),
            timeout=AGENT_TIMEOUT
        )

        return {
            "needs_assessment_output": result,
            "current_step": "needs_assessment_complete",
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "needs_assessment"
        }
    except asyncio.TimeoutError:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("timeout", "Needs Assessment agent timed out", "needs_assessment")
            ],
            "current_step": "needs_assessment_timeout"
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "needs_assessment")
            ],
            "current_step": "needs_assessment_failed"
        }


@traceable(name="run_curriculum_agent", run_type="chain", metadata={"agent": "curriculum"})
async def run_curriculum_agent(state: CMEPipelineState) -> dict:
    """Run Curriculum Design Agent."""
    try:
        graph = get_agent_graph("curriculum")
        
        intake = state.get("intake_data", {})
        needs_out = state.get("needs_assessment_output") or {}
        lo_out = state.get("learning_objectives_output") or {}
        gap_out = state.get("gap_analysis_output") or {}

        agent_input = {
            # From upstream agents — extracted to expected key names
            "learning_objectives_report": lo_out.get("learning_objectives_report", {}),
            "gap_analysis_report": gap_out.get("gap_analysis_report", {}),
            "needs_assessment_document": needs_out.get("complete_document", ""),
            # From intake form
            "target_audience": intake.get("target_audience", ""),
            "practice_settings": intake.get("practice_settings", []),
            "educational_format": intake.get("educational_format", ""),
            "innovation_elements": intake.get("innovation_elements", []),
            "faculty_requirements": intake.get("faculty_requirements", ""),
            "duration_minutes": intake.get("duration_minutes"),
            "modality": intake.get("learning_format", ""),
            "therapeutic_area": intake.get("therapeutic_area", ""),
            "disease_state": intake.get("disease_state", ""),
        }

        result = await asyncio.wait_for(
            graph.ainvoke(agent_input),
            timeout=AGENT_TIMEOUT
        )

        return {
            "curriculum_output": result,
            "current_step": "curriculum_complete",
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "curriculum"
        }
    except asyncio.TimeoutError:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("timeout", "Curriculum agent timed out", "curriculum")
            ],
            "current_step": "curriculum_timeout"
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "curriculum")
            ],
            "current_step": "curriculum_failed"
        }


@traceable(name="run_protocol_agent", run_type="chain", metadata={"agent": "protocol"})
async def run_protocol_agent(state: CMEPipelineState) -> dict:
    """Run Research Protocol Agent."""
    try:
        graph = get_agent_graph("protocol")
        
        intake = state.get("intake_data", {})
        lo_out = state.get("learning_objectives_output") or {}
        curriculum_out = state.get("curriculum_output") or {}
        gap_out = state.get("gap_analysis_output") or {}

        agent_input = {
            # From upstream agents
            "learning_objectives_report": lo_out.get("learning_objectives_report", {}),
            "curriculum_report": curriculum_out.get("curriculum_report", {}),
            "gap_analysis_report": gap_out.get("gap_analysis_report", {}),
            # From intake form
            "target_audience": intake.get("target_audience", ""),
            "estimated_reach": intake.get("estimated_reach"),
            "outcome_goals": intake.get("outcome_goals", []),
            "moore_level_target": str(intake.get("moore_level_target", "Level 5")),
            "measurement_preferences": intake.get("measurement_approach", ""),
            "therapeutic_area": intake.get("therapeutic_area", ""),
            "disease_state": intake.get("disease_state", ""),
        }

        result = await asyncio.wait_for(
            graph.ainvoke(agent_input),
            timeout=AGENT_TIMEOUT
        )

        return {
            "protocol_output": result,
            "current_step": "protocol_complete",
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "protocol"
        }
    except asyncio.TimeoutError:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("timeout", "Protocol agent timed out", "protocol")
            ],
            "current_step": "protocol_timeout"
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "protocol")
            ],
            "current_step": "protocol_failed"
        }


@traceable(name="run_marketing_agent", run_type="chain", metadata={"agent": "marketing"})
async def run_marketing_agent(state: CMEPipelineState) -> dict:
    """Run Marketing Plan Agent."""
    try:
        graph = get_agent_graph("marketing")
        
        intake = state.get("intake_data", {})
        lo_out = state.get("learning_objectives_output") or {}
        needs_out = state.get("needs_assessment_output") or {}

        agent_input = {
            # From upstream agents
            "learning_objectives_report": lo_out.get("learning_objectives_report", {}),
            "needs_assessment_document": needs_out.get("complete_document", ""),
            # From intake form
            "target_audience": intake.get("target_audience", ""),
            "practice_settings": intake.get("practice_settings", []),
            "geographic_focus": intake.get("geographic_focus", ""),
            "estimated_reach": intake.get("estimated_reach", 0),
            "marketing_budget": intake.get("grant_amount_requested"),
            "marketing_channels": intake.get("distribution_channels", []),
            "launch_date": intake.get("target_launch_date", ""),
            "therapeutic_area": intake.get("therapeutic_area", ""),
            "disease_state": intake.get("disease_state", ""),
            "educational_format": intake.get("educational_format", ""),
        }

        result = await asyncio.wait_for(
            graph.ainvoke(agent_input),
            timeout=AGENT_TIMEOUT
        )

        return {
            "marketing_output": result,
            "current_step": "marketing_complete",
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "marketing"
        }
    except asyncio.TimeoutError:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("timeout", "Marketing agent timed out", "marketing")
            ],
            "current_step": "marketing_timeout"
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "marketing")
            ],
            "current_step": "marketing_failed"
        }


@traceable(name="run_grant_writer_agent", run_type="chain", metadata={"agent": "grant_writer"})
async def run_grant_writer_agent(state: CMEPipelineState) -> dict:
    """Run Grant Writer Agent."""
    try:
        graph = get_agent_graph("grant_writer")
        
        intake = state.get("intake_data", {})
        
        # Include feedback from prose quality if retrying
        prose_feedback = None
        if state.get("prose_quality_pass_2") and not state["prose_quality_pass_2"].get("overall_passed"):
            prose_feedback = state["prose_quality_pass_2"].get("feedback", "")
        
        agent_input = {
            "project_title": intake.get("project_title", ""),
            "activity_title": intake.get("activity_title", ""),
            "supporter_company": intake.get("supporter_company", ""),
            "supporter_contact": intake.get("supporter_contact", ""),
            "requested_amount": intake.get("requested_amount", ""),
            "budget_breakdown": intake.get("budget_breakdown", {}),
            "organization_info": intake.get("organization_info", {}),
            "accreditation_statement": intake.get("accreditation_statement", ""),
            "therapeutic_area": intake.get("therapeutic_area", ""),
            "target_audience": intake.get("target_audience", ""),
            "needs_assessment_output": state.get("needs_assessment_output", {}),
            "learning_objectives_output": state.get("learning_objectives_output", {}),
            "curriculum_design_output": state.get("curriculum_output", {}),
            "research_protocol_output": state.get("protocol_output", {}),
            "marketing_plan_output": state.get("marketing_output", {}),
            "gap_analysis_output": state.get("gap_analysis_output", {}),
            "research_output": state.get("research_output", {}),
            "revision_feedback": prose_feedback,
        }
        
        result = await asyncio.wait_for(
            graph.ainvoke(agent_input),
            timeout=AGENT_TIMEOUT * 2  # Grant writer may take longer
        )
        
        return {
            "grant_package_output": result,
            "current_step": "grant_writer_complete",
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "grant_writer"
        }
    except asyncio.TimeoutError:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("timeout", "Grant Writer agent timed out", "grant_writer")
            ],
            "current_step": "grant_writer_timeout"
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "grant_writer")
            ],
            "current_step": "grant_writer_failed"
        }


@traceable(name="run_prose_quality_pass_1", run_type="chain", metadata={"agent": "prose_quality", "pass": 1})
async def run_prose_quality_pass_1(state: CMEPipelineState) -> dict:
    """Run Prose Quality Agent (Pass 1 - after Needs Assessment)."""
    try:
        graph = get_agent_graph("prose_quality")
        
        needs_output = state.get("needs_assessment_output", {})
        document_text = needs_output.get("complete_document", "")
        
        agent_input = {
            "document_text": document_text,
            "pass_number": 1,
            "character_name": state.get("intake_data", {}).get("character_name"),
        }
        
        result = await asyncio.wait_for(
            graph.ainvoke(agent_input),
            timeout=AGENT_TIMEOUT
        )
        
        # Increment retry count if failed
        new_retry_count = state.get("retry_count", 0)
        if not result.get("overall_passed", False):
            new_retry_count += 1
        
        return {
            "prose_quality_pass_1": result,
            "current_step": "prose_quality_1_complete",
            "retry_count": new_retry_count,
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "prose_quality_1"
        }
    except asyncio.TimeoutError:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("timeout", "Prose Quality (Pass 1) agent timed out", "prose_quality_1")
            ],
            "current_step": "prose_quality_1_timeout"
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "prose_quality_1")
            ],
            "current_step": "prose_quality_1_failed"
        }


@traceable(name="run_prose_quality_pass_2", run_type="chain", metadata={"agent": "prose_quality", "pass": 2})
async def run_prose_quality_pass_2(state: CMEPipelineState) -> dict:
    """Run Prose Quality Agent (Pass 2 - after Grant Writer)."""
    try:
        graph = get_agent_graph("prose_quality")
        
        grant_output = state.get("grant_package_output", {})
        document_text = grant_output.get("complete_document_markdown", "")
        
        agent_input = {
            "document_text": document_text,
            "pass_number": 2,
            "character_name": state.get("intake_data", {}).get("character_name"),
        }
        
        result = await asyncio.wait_for(
            graph.ainvoke(agent_input),
            timeout=AGENT_TIMEOUT
        )
        
        # Increment retry count if failed
        new_retry_count = state.get("retry_count", 0)
        if not result.get("overall_passed", False):
            new_retry_count += 1
        
        return {
            "prose_quality_pass_2": result,
            "current_step": "prose_quality_2_complete",
            "retry_count": new_retry_count,
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "prose_quality_2"
        }
    except asyncio.TimeoutError:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("timeout", "Prose Quality (Pass 2) agent timed out", "prose_quality_2")
            ],
            "current_step": "prose_quality_2_timeout"
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "prose_quality_2")
            ],
            "current_step": "prose_quality_2_failed"
        }


@traceable(name="run_compliance_agent", run_type="chain", metadata={"agent": "compliance"})
async def run_compliance_agent(state: CMEPipelineState) -> dict:
    """Run Compliance Review Agent."""
    try:
        graph = get_agent_graph("compliance")
        
        grant_output = state.get("grant_package_output", {})
        
        intake = state.get("intake_data", {})
        agent_input = {
            "grant_package": grant_output,
            "supporter_company": intake.get("supporter_company", ""),
            "supporter_products": intake.get("supporter_products", []),
            "competitor_products": intake.get("competitor_products", []),
            "accreditation_types": intake.get("accreditation_types", []),
        }
        
        result = await asyncio.wait_for(
            graph.ainvoke(agent_input),
            timeout=AGENT_TIMEOUT
        )
        
        return {
            "compliance_result": result,
            "current_step": "compliance_complete",
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "compliance"
        }
    except asyncio.TimeoutError:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("timeout", "Compliance agent timed out", "compliance")
            ],
            "current_step": "compliance_timeout"
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "compliance")
            ],
            "current_step": "compliance_failed"
        }


@traceable(name="human_review_node", run_type="chain")
async def human_review_node(state: CMEPipelineState) -> dict:
    """Pause pipeline for human review via LangGraph interrupt().

    Assembles review payload from current state and calls interrupt().
    The graph pauses here until resumed with Command(resume={decision, comments}).
    """
    documents = {}
    metrics = {}

    if state.get("needs_assessment_output"):
        na = state["needs_assessment_output"]
        documents["needs_assessment"] = na.get("complete_document", "")
        metrics["word_count"] = na.get("word_count", 0)
        metrics["prose_density"] = na.get("prose_density", 0.0)
        metrics["quality_passed"] = na.get("quality_passed", False)
        metrics["banned_patterns_found"] = na.get("banned_patterns_found", [])

    if state.get("curriculum_output"):
        documents["curriculum_design"] = state["curriculum_output"].get("complete_document", "")

    if state.get("protocol_output"):
        documents["research_protocol"] = state["protocol_output"].get("complete_document", "")

    if state.get("marketing_output"):
        documents["marketing_plan"] = state["marketing_output"].get("complete_document", "")

    if state.get("grant_package_output"):
        documents["grant_package"] = state["grant_package_output"].get("complete_document_markdown", "")

    if state.get("prose_quality_pass_1"):
        metrics["prose_quality_pass_1"] = state["prose_quality_pass_1"]
    if state.get("prose_quality_pass_2"):
        metrics["prose_quality_pass_2"] = state["prose_quality_pass_2"]
    if state.get("compliance_result"):
        metrics["compliance_result"] = state["compliance_result"]

    recipe = "needs_package"
    if state.get("grant_package_output"):
        recipe = "grant_package"
    elif state.get("curriculum_output"):
        recipe = "curriculum_package"

    # Include VS distributions for alternative rendering in inbox.
    # Each agent stores vs_distributions (dict keyed by step name) in its output.
    # We merge them all here so the frontend can render alternatives per agent/node.
    vs_distributions = {}
    agent_output_keys = [
        ("gap_analysis_output", "gap_analysis"),
        ("needs_assessment_output", "needs_assessment"),
        ("research_output", "research"),
        ("clinical_practice_output", "clinical_practice"),
        ("learning_objectives_output", "learning_objectives"),
        ("curriculum_design_output", "curriculum_design"),
        ("research_protocol_output", "research_protocol"),
        ("marketing_plan_output", "marketing_plan"),
        ("grant_writer_output", "grant_writer"),
    ]
    for output_key, agent_name in agent_output_keys:
        agent_out = state.get(output_key) or {}
        if isinstance(agent_out, dict) and agent_out.get("vs_distributions"):
            for step_name, dist in agent_out["vs_distributions"].items():
                vs_distributions[f"{agent_name}.{step_name}"] = dist

    review_payload = {
        "document": documents,
        "metrics": metrics,
        "recipe": recipe,
        "project_id": state.get("project_id", ""),
        "project_name": state.get("project_name", ""),
        "review_round": state.get("review_round", 0),
        "current_step": state.get("current_step", ""),
        "vs_distributions": vs_distributions,
    }

    # Notify registry that pipeline is paused for human review
    await _notify_registry_status(
        project_id=state.get("project_id", ""),
        pipeline_status="awaiting_review",
        current_step="human_review_pending",
    )
    # Milestone: package ready for review → enqueue Drive sync
    await enqueue_drive_sync(
        state.get("project_id", ""),
        milestone=f"review_ready:{state.get('current_step', 'unknown')}",
    )

    resume_value = interrupt(review_payload)

    decision = resume_value.get("decision", "rejected")
    comments = resume_value.get("comments", [])

    return {
        "human_review_status": decision,
        "human_review_notes": resume_value.get("feedback", ""),
        "review_comments": state.get("review_comments", []) + comments,
        "status": PipelineStatus.AWAITING_REVIEW.value,
        "current_step": f"human_review_{decision}",
        "updated_at": datetime.now().isoformat(),
    }


@traceable(name="auto_approve_node", run_type="chain", metadata={"skip_human_review": True})
async def auto_approve_node(state: CMEPipelineState) -> dict:
    """Auto-approve pipeline when SKIP_HUMAN_REVIEW is enabled.

    Mirrors the human_review_node contract — sets human_review_status, logs VS
    distributions and document metrics to LangSmith via @traceable, and notifies
    the registry so the audit trail shows the review was intentionally skipped.
    """
    documents = {}
    metrics = {}

    if state.get("needs_assessment_output"):
        na = state["needs_assessment_output"]
        documents["needs_assessment"] = na.get("complete_document", "")
        metrics["word_count"] = na.get("word_count", 0)
        metrics["prose_density"] = na.get("prose_density", 0.0)
        metrics["quality_passed"] = na.get("quality_passed", False)
        metrics["banned_patterns_found"] = na.get("banned_patterns_found", [])

    if state.get("curriculum_output"):
        documents["curriculum_design"] = state["curriculum_output"].get("complete_document", "")
    if state.get("protocol_output"):
        documents["research_protocol"] = state["protocol_output"].get("complete_document", "")
    if state.get("marketing_output"):
        documents["marketing_plan"] = state["marketing_output"].get("complete_document", "")
    if state.get("grant_package_output"):
        documents["grant_package"] = state["grant_package_output"].get("complete_document_markdown", "")

    if state.get("prose_quality_pass_1"):
        metrics["prose_quality_pass_1"] = state["prose_quality_pass_1"]
    if state.get("prose_quality_pass_2"):
        metrics["prose_quality_pass_2"] = state["prose_quality_pass_2"]
    if state.get("compliance_result"):
        metrics["compliance_result"] = state["compliance_result"]

    vs_distributions = {}
    agent_output_keys = [
        ("gap_analysis_output", "gap_analysis"),
        ("needs_assessment_output", "needs_assessment"),
        ("research_output", "research"),
        ("clinical_practice_output", "clinical_practice"),
        ("learning_objectives_output", "learning_objectives"),
        ("curriculum_design_output", "curriculum_design"),
        ("research_protocol_output", "research_protocol"),
        ("marketing_plan_output", "marketing_plan"),
        ("grant_writer_output", "grant_writer"),
    ]
    for output_key, agent_name in agent_output_keys:
        agent_out = state.get(output_key) or {}
        if isinstance(agent_out, dict) and agent_out.get("vs_distributions"):
            for step_name, dist in agent_out["vs_distributions"].items():
                vs_distributions[f"{agent_name}.{step_name}"] = dist

    logger.info(
        "Auto-approve: SKIP_HUMAN_REVIEW=true | project=%s | documents=%d | vs_distributions=%d",
        state.get("project_id", ""),
        len(documents),
        len(vs_distributions),
    )
    logger.info("Auto-approve metrics: %s", {k: v for k, v in metrics.items() if k != "compliance_result"})

    await _notify_registry_status(
        project_id=state.get("project_id", ""),
        pipeline_status="auto_approved",
        current_step="human_review_auto_approved",
    )
    # Milestone: package auto-approved → enqueue Drive sync
    await enqueue_drive_sync(
        state.get("project_id", ""),
        milestone=f"auto_approved:{state.get('current_step', 'unknown')}",
    )

    return {
        "human_review_status": "approved",
        "human_review_notes": "Auto-approved (SKIP_HUMAN_REVIEW=true)",
        "status": PipelineStatus.APPROVED.value,
        "current_step": "human_review_auto_approved",
        "updated_at": datetime.now().isoformat(),
    }


MAX_REVIEW_ROUNDS = 10


@traceable(name="process_review_feedback", run_type="chain")
async def process_review_feedback(state: CMEPipelineState) -> dict:
    """Format reviewer comments into a structured message for the revision agent.

    Reads review_comments from state and creates a HumanMessage that the
    revision agent will see as context for targeted edits.
    """
    from langchain_core.messages import HumanMessage

    review_round = state.get("review_round", 0) + 1

    if review_round > MAX_REVIEW_ROUNDS:
        return {
            "status": PipelineStatus.FAILED.value,
            "current_step": "maximum_revision_cycles_exceeded",
            "updated_at": datetime.now().isoformat(),
        }

    comments = state.get("review_comments", [])

    if comments:
        lines = ["## Reviewer Comments (address each one):\n"]
        for i, c in enumerate(comments, 1):
            selected = c.get("selectedText", "")
            comment = c.get("comment", "")
            doc_id = c.get("document_id", "")
            doc_prefix = f"[{doc_id}] " if doc_id else ""
            lines.append(f'{i}. {doc_prefix}At "{selected}": "{comment}"')
        feedback_text = "\n".join(lines)
    else:
        feedback_text = "## General revision requested\n\nThe reviewer requested revisions but did not provide specific inline comments. Please review the document for quality, accuracy, and completeness."

    return {
        "messages": [HumanMessage(content=feedback_text)],
        "review_round": review_round,
        "current_step": f"processing_review_feedback_round_{review_round}",
        "updated_at": datetime.now().isoformat(),
    }


REGISTRY_URL = os.getenv("AI_FACTORY_REGISTRY_URL", "http://dhg-registry-api:8000")


async def _notify_registry_status(project_id: str, pipeline_status: str, current_step: str, error_summary: str = "") -> None:
    """Fire-and-forget notification to registry API about pipeline terminal state."""
    if not project_id:
        logger.warning("Cannot notify registry: no project_id in state")
        return
    url = f"{REGISTRY_URL}/api/cme/webhook/pipeline-status"
    params = {
        "project_id": project_id,
        "pipeline_status": pipeline_status,
        "current_step": current_step,
    }
    if error_summary:
        params["error_summary"] = error_summary
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, params=params)
            resp.raise_for_status()
            logger.info(f"Registry notified: project={project_id}, status={pipeline_status}")
    except Exception as e:
        logger.error(f"Failed to notify registry: {e}")


@traceable(name="mark_complete", run_type="chain")
async def mark_complete(state: CMEPipelineState) -> dict:
    """Mark pipeline as complete and notify registry."""
    await _notify_registry_status(
        project_id=state.get("project_id", ""),
        pipeline_status="complete",
        current_step="complete",
    )
    # Milestone: pipeline terminal → final Drive sync
    await enqueue_drive_sync(
        state.get("project_id", ""),
        milestone="complete",
    )
    return {
        "status": PipelineStatus.COMPLETE.value,
        "current_step": "complete",
        "updated_at": datetime.now().isoformat()
    }


@traceable(name="mark_failed", run_type="chain")
async def mark_failed(state: CMEPipelineState) -> dict:
    """Mark pipeline as failed, notify registry, and escalate to human intervention."""
    errors = state.get("errors", [])
    error_summary = "; ".join(e.get("message", "unknown") for e in errors[-3:]) if errors else "Pipeline failed"
    await _notify_registry_status(
        project_id=state.get("project_id", ""),
        pipeline_status="failed",
        current_step="failed_human_intervention_required",
        error_summary=error_summary,
    )
    return {
        "status": PipelineStatus.FAILED.value,
        "current_step": "failed_human_intervention_required",
        "updated_at": datetime.now().isoformat()
    }


# =============================================================================
# PARALLEL EXECUTION: FAN-OUT / FAN-IN
# =============================================================================

@traceable(name="early_research_parallel", run_type="chain")
@traced_node("orchestrator", "early_research_parallel")
async def run_early_research_parallel(state: CMEPipelineState) -> dict:
    """
    Run Research and Clinical agents in parallel.
    Fan-out pattern: executes both concurrently, then merges results.
    """
    try:
        research_graph = get_agent_graph("research")
        clinical_graph = get_agent_graph("clinical")
        
        intake = state.get("intake_data", {})

        research_input = _build_research_input(intake)
        clinical_input = _build_clinical_input(intake)
        
        # Execute both in parallel
        research_task = asyncio.create_task(
            asyncio.wait_for(research_graph.ainvoke(research_input), timeout=AGENT_TIMEOUT)
        )
        clinical_task = asyncio.create_task(
            asyncio.wait_for(clinical_graph.ainvoke(clinical_input), timeout=AGENT_TIMEOUT)
        )
        
        # Wait for both to complete
        results = await asyncio.gather(research_task, clinical_task, return_exceptions=True)
        
        # Process results
        research_result, clinical_result = results
        errors = state.get("errors", [])
        
        update = {
            "current_step": "early_research_complete",
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "early_research_parallel"
        }
        
        if isinstance(research_result, Exception):
            errors.append(create_error_record("agent_failure", str(research_result), "research"))
        else:
            update["research_output"] = research_result
            
        if isinstance(clinical_result, Exception):
            errors.append(create_error_record("agent_failure", str(clinical_result), "clinical"))
        else:
            update["clinical_output"] = clinical_result
        
        if errors != state.get("errors", []):
            update["errors"] = errors
            
        return update
        
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "early_research_parallel")
            ],
            "current_step": "early_research_failed"
        }


@traceable(name="design_phase_parallel", run_type="chain")
@traced_node("orchestrator", "design_phase_parallel")
async def run_design_phase_parallel(state: CMEPipelineState) -> dict:
    """
    Run Curriculum, Protocol, and Marketing agents in parallel.
    Fan-out pattern: executes all three concurrently, then merges results.
    """
    try:
        curriculum_graph = get_agent_graph("curriculum")
        protocol_graph = get_agent_graph("protocol")
        marketing_graph = get_agent_graph("marketing")
        
        intake = state.get("intake_data", {})
        needs = state.get("needs_assessment_output", {})
        lo = state.get("learning_objectives_output", {})
        
        curriculum_input = {
            "needs_assessment_output": needs,
            "learning_objectives_output": lo,
            "intake_data": intake,
        }
        
        protocol_input = {
            "needs_assessment_output": needs,
            "learning_objectives_output": lo,
            "curriculum_output": {},  # Will be empty since running parallel
        }
        
        marketing_input = {
            "needs_assessment_output": needs,
            "curriculum_output": {},  # Will be empty since running parallel
            "intake_data": intake,
        }
        
        # Execute all three in parallel
        curriculum_task = asyncio.create_task(
            asyncio.wait_for(curriculum_graph.ainvoke(curriculum_input), timeout=AGENT_TIMEOUT)
        )
        protocol_task = asyncio.create_task(
            asyncio.wait_for(protocol_graph.ainvoke(protocol_input), timeout=AGENT_TIMEOUT)
        )
        marketing_task = asyncio.create_task(
            asyncio.wait_for(marketing_graph.ainvoke(marketing_input), timeout=AGENT_TIMEOUT)
        )
        
        # Wait for all to complete
        results = await asyncio.gather(
            curriculum_task, protocol_task, marketing_task, 
            return_exceptions=True
        )
        
        # Process results
        curriculum_result, protocol_result, marketing_result = results
        errors = state.get("errors", [])
        
        update = {
            "current_step": "design_phase_complete",
            "last_checkpoint": datetime.now().isoformat(),
            "checkpoint_agent": "design_phase_parallel"
        }
        
        if isinstance(curriculum_result, Exception):
            errors.append(create_error_record("agent_failure", str(curriculum_result), "curriculum"))
        else:
            update["curriculum_output"] = curriculum_result
            
        if isinstance(protocol_result, Exception):
            errors.append(create_error_record("agent_failure", str(protocol_result), "protocol"))
        else:
            update["protocol_output"] = protocol_result
            
        if isinstance(marketing_result, Exception):
            errors.append(create_error_record("agent_failure", str(marketing_result), "marketing"))
        else:
            update["marketing_output"] = marketing_result
        
        if errors != state.get("errors", []):
            update["errors"] = errors
            
        return update
        
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "design_phase_parallel")
            ],
            "current_step": "design_phase_failed"
        }


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def route_after_prose_quality_1(state: CMEPipelineState) -> Literal["continue", "retry_needs", "human_intervention"]:
    """Route after first prose quality pass."""
    result = state.get("prose_quality_pass_1") or {}
    if result.get("overall_passed", False):
        return "continue"
    else:
        retry_count = state.get("retry_count", 0)
        if retry_count < MAX_RETRIES["quality_failure"]:
            return "retry_needs"
        else:
            return "human_intervention"


def route_after_prose_quality_2(state: CMEPipelineState) -> Literal["continue", "retry_grant", "human_intervention"]:
    """Route after second prose quality pass."""
    result = state.get("prose_quality_pass_2", {})
    if result.get("overall_passed", False):
        return "continue"
    else:
        retry_count = state.get("retry_count", 0)
        if retry_count < MAX_RETRIES["quality_failure"]:
            return "retry_grant"
        else:
            return "human_intervention"


def route_after_compliance(state: CMEPipelineState) -> Literal["continue", "revision_required"]:
    """Route after compliance review."""
    result = state.get("compliance_result") or {}
    if result.get("overall_passed", False):
        return "continue"
    else:
        return "revision_required"


def route_after_review_feedback(state: CMEPipelineState) -> Literal["continue", "max_rounds_exceeded"]:
    """Route after process_review_feedback — fail if max review rounds exceeded."""
    if state.get("status") == PipelineStatus.FAILED.value:
        return "max_rounds_exceeded"
    return "continue"


def route_after_human_review_interrupt(state: CMEPipelineState) -> Literal["approved", "revision", "rejected"]:
    """Route after human review interrupt based on human_review_status set by human_review_node."""
    status = state.get("human_review_status", "rejected")
    if status == "approved":
        return "approved"
    elif status == "revision":
        return "revision"
    else:
        return "rejected"


# =============================================================================
# REVIEW WIRING HELPER
# =============================================================================

def _add_review_nodes_and_edges(workflow: StateGraph, revision_target: str):
    """Add review-related nodes and their downstream edges based on SKIP_HUMAN_REVIEW.

    When SKIP_HUMAN_REVIEW is false (default), adds:
        human_review node → approved:complete / revision:process_feedback / rejected:failed
        process_feedback node → continue:revision_target / max_rounds_exceeded:failed

    When SKIP_HUMAN_REVIEW is true, adds:
        auto_approve node → complete

    The caller is responsible for wiring the incoming edge to either
    "human_review" or "auto_approve" (use REVIEW_ENTRY_NODE for the name).

    Args:
        workflow: The StateGraph being built.
        revision_target: Node to loop back to on revision (e.g. "grant_writer", "needs_assessment").
    """
    if SKIP_HUMAN_REVIEW:
        workflow.add_node("auto_approve", auto_approve_node)
        workflow.add_edge("auto_approve", "complete")
    else:
        workflow.add_node("human_review", human_review_node)
        workflow.add_node("process_feedback", process_review_feedback)
        workflow.add_conditional_edges(
            "human_review",
            route_after_human_review_interrupt,
            {
                "approved": "complete",
                "revision": "process_feedback",
                "rejected": "failed"
            }
        )
        workflow.add_conditional_edges(
            "process_feedback",
            route_after_review_feedback,
            {
                "continue": revision_target,
                "max_rounds_exceeded": "failed",
            }
        )


REVIEW_ENTRY_NODE = "auto_approve" if SKIP_HUMAN_REVIEW else "human_review"


# =============================================================================
# RECIPE 1: NEEDS PACKAGE (with parallel execution)
# Research + Clinical [parallel] → Gap Analysis → LO → Needs → Prose QA → Human Review
# =============================================================================

def create_needs_package_graph():
    """Create the Needs Assessment Package recipe with parallel execution and interrupt-based review."""

    workflow = StateGraph(CMEPipelineState)

    workflow.add_node("initialize", initialize_pipeline)
    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality", run_prose_quality_pass_1)
    workflow.add_node("complete", mark_complete)
    workflow.add_node("failed", mark_failed)

    workflow.set_entry_point("initialize")
    workflow.add_edge("initialize", "early_research")
    workflow.add_edge("early_research", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality")

    workflow.add_conditional_edges(
        "prose_quality",
        route_after_prose_quality_1,
        {
            "continue": REVIEW_ENTRY_NODE,
            "retry_needs": "needs_assessment",
            "human_intervention": REVIEW_ENTRY_NODE
        }
    )

    _add_review_nodes_and_edges(workflow, revision_target="needs_assessment")

    workflow.add_edge("complete", END)
    workflow.add_edge("failed", END)

    return workflow.compile()


# =============================================================================
# RECIPE 2: CURRICULUM PACKAGE (with parallel execution)
# Needs Package → Curriculum + Protocol + Marketing [parallel] → Prose QA → Human Review
# =============================================================================

def create_curriculum_package_graph():
    """Create the Curriculum Package recipe with parallel execution and interrupt-based review."""

    workflow = StateGraph(CMEPipelineState)

    workflow.add_node("initialize", initialize_pipeline)
    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality_1", run_prose_quality_pass_1)
    workflow.add_node("design_phase", run_design_phase_parallel)
    workflow.add_node("complete", mark_complete)
    workflow.add_node("failed", mark_failed)

    workflow.set_entry_point("initialize")
    workflow.add_edge("initialize", "early_research")
    workflow.add_edge("early_research", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality_1")

    workflow.add_conditional_edges(
        "prose_quality_1",
        route_after_prose_quality_1,
        {
            "continue": "design_phase",
            "retry_needs": "needs_assessment",
            "human_intervention": "design_phase" if SKIP_HUMAN_REVIEW else "human_review"
        }
    )

    workflow.add_edge("design_phase", REVIEW_ENTRY_NODE)

    _add_review_nodes_and_edges(workflow, revision_target="design_phase")

    workflow.add_edge("complete", END)
    workflow.add_edge("failed", END)

    return workflow.compile()


# =============================================================================
# RECIPE 3: GRANT PACKAGE (Full 11 agents with parallel execution)
# All agents + Prose QA (2 passes) + Compliance + Human Review
# =============================================================================

def create_grant_package_graph():
    """Create the Grant Package recipe with interrupt-based review."""

    workflow = StateGraph(CMEPipelineState)

    workflow.add_node("initialize", initialize_pipeline)
    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality_1", run_prose_quality_pass_1)
    workflow.add_node("design_phase", run_design_phase_parallel)
    workflow.add_node("grant_writer", run_grant_writer_agent)
    workflow.add_node("prose_quality_2", run_prose_quality_pass_2)
    workflow.add_node("compliance", run_compliance_agent)
    workflow.add_node("complete", mark_complete)
    workflow.add_node("failed", mark_failed)

    workflow.set_entry_point("initialize")
    workflow.add_edge("initialize", "early_research")
    workflow.add_edge("early_research", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality_1")

    workflow.add_conditional_edges(
        "prose_quality_1",
        route_after_prose_quality_1,
        {
            "continue": "design_phase",
            "retry_needs": "needs_assessment",
            "human_intervention": "design_phase" if SKIP_HUMAN_REVIEW else "human_review"
        }
    )

    workflow.add_edge("design_phase", "grant_writer")
    workflow.add_edge("grant_writer", "prose_quality_2")

    workflow.add_conditional_edges(
        "prose_quality_2",
        route_after_prose_quality_2,
        {
            "continue": "compliance",
            "retry_grant": "grant_writer",
            "human_intervention": "compliance" if SKIP_HUMAN_REVIEW else "human_review"
        }
    )

    workflow.add_conditional_edges(
        "compliance",
        route_after_compliance,
        {
            "continue": REVIEW_ENTRY_NODE,
            "revision_required": "grant_writer"
        }
    )

    _add_review_nodes_and_edges(workflow, revision_target="grant_writer")

    workflow.add_edge("complete", END)
    workflow.add_edge("failed", END)

    return workflow.compile()


# =============================================================================
# CHECKPOINTER FACTORY
# =============================================================================

async def get_checkpointer():
    """Create and return a PostgresSaver checkpointer."""
    if not POSTGRES_AVAILABLE:
        logger.info("PostgresSaver not available, using in-memory checkpointing")
        return None
    try:
        checkpointer = await AsyncPostgresSaver.from_conn_string(DATABASE_URL)
        await checkpointer.setup()  # Create tables if needed
        return checkpointer
    except Exception as e:
        logger.warning(f"Failed to create PostgresSaver, using in-memory: {e}")
        return None


# =============================================================================
# COMPILE AND EXPORT ALL RECIPES
# =============================================================================

# Basic compiled graphs (without checkpointing)
needs_graph = create_needs_package_graph()
curriculum_graph = create_curriculum_package_graph()
grant_graph = create_grant_package_graph()


# =============================================================================
# FACTORY FUNCTIONS FOR CHECKPOINTED GRAPHS
# =============================================================================

async def create_checkpointed_needs_graph():
    """Create needs graph with PostgresSaver checkpointing and interrupt-based review."""
    checkpointer = await get_checkpointer()
    workflow = StateGraph(CMEPipelineState)

    workflow.add_node("initialize", initialize_pipeline)
    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality", run_prose_quality_pass_1)
    workflow.add_node("complete", mark_complete)
    workflow.add_node("failed", mark_failed)

    workflow.set_entry_point("initialize")
    workflow.add_edge("initialize", "early_research")
    workflow.add_edge("early_research", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality")

    workflow.add_conditional_edges(
        "prose_quality",
        route_after_prose_quality_1,
        {
            "continue": REVIEW_ENTRY_NODE,
            "retry_needs": "needs_assessment",
            "human_intervention": REVIEW_ENTRY_NODE
        }
    )

    _add_review_nodes_and_edges(workflow, revision_target="needs_assessment")

    workflow.add_edge("complete", END)
    workflow.add_edge("failed", END)

    return workflow.compile(checkpointer=checkpointer)


async def create_checkpointed_grant_graph():
    """Create grant graph with PostgresSaver checkpointing and interrupt-based review."""
    checkpointer = await get_checkpointer()
    workflow = StateGraph(CMEPipelineState)

    workflow.add_node("initialize", initialize_pipeline)
    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality_1", run_prose_quality_pass_1)
    workflow.add_node("design_phase", run_design_phase_parallel)
    workflow.add_node("grant_writer", run_grant_writer_agent)
    workflow.add_node("prose_quality_2", run_prose_quality_pass_2)
    workflow.add_node("compliance", run_compliance_agent)
    workflow.add_node("complete", mark_complete)
    workflow.add_node("failed", mark_failed)

    workflow.set_entry_point("initialize")
    workflow.add_edge("initialize", "early_research")
    workflow.add_edge("early_research", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality_1")

    workflow.add_conditional_edges(
        "prose_quality_1",
        route_after_prose_quality_1,
        {
            "continue": "design_phase",
            "retry_needs": "needs_assessment",
            "human_intervention": "design_phase" if SKIP_HUMAN_REVIEW else "human_review"
        }
    )

    workflow.add_edge("design_phase", "grant_writer")
    workflow.add_edge("grant_writer", "prose_quality_2")

    workflow.add_conditional_edges(
        "prose_quality_2",
        route_after_prose_quality_2,
        {
            "continue": "compliance",
            "retry_grant": "grant_writer",
            "human_intervention": "compliance" if SKIP_HUMAN_REVIEW else "human_review"
        }
    )

    workflow.add_conditional_edges(
        "compliance",
        route_after_compliance,
        {
            "continue": REVIEW_ENTRY_NODE,
            "revision_required": "grant_writer"
        }
    )

    _add_review_nodes_and_edges(workflow, revision_target="grant_writer")

    workflow.add_edge("complete", END)
    workflow.add_edge("failed", END)

    return workflow.compile(checkpointer=checkpointer)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_initial_state(
    project_id: str,
    project_name: str,
    intake_data: Dict[str, Any]
) -> CMEPipelineState:
    """Create initial state for a new pipeline run."""
    now = datetime.now().isoformat()
    return CMEPipelineState(
        project_id=project_id,
        project_name=project_name,
        status=PipelineStatus.PENDING.value,
        created_at=now,
        updated_at=now,
        intake_data=intake_data,
        intake_validated=True,
        research_output=None,
        clinical_output=None,
        gap_analysis_output=None,
        needs_assessment_output=None,
        learning_objectives_output=None,
        curriculum_output=None,
        protocol_output=None,
        marketing_output=None,
        grant_package_output=None,
        prose_quality_pass_1=None,
        prose_quality_pass_2=None,
        compliance_result=None,
        human_review_status=None,
        human_review_notes=None,
        human_reviewer=None,
        review_comments=[],
        review_round=0,
        current_step="started",
        retry_count=0,
        messages=[],
        errors=[],
        last_checkpoint=now,
        checkpoint_agent="init"
    )


async def run_pipeline(
    recipe: str,
    project_id: str,
    project_name: str,
    intake_data: Dict[str, Any],
    use_checkpointing: bool = True
) -> CMEPipelineState:
    """
    Run a pipeline recipe with the given intake data.

    Args:
        recipe: One of "needs", "curriculum", "grant", "full"
        project_id: Unique project identifier
        project_name: Human-readable project name
        intake_data: Complete intake form data
        use_checkpointing: Whether to use PostgresSaver (default True)

    Returns:
        Final pipeline state
    """
    with _tracer.start_as_current_span(
        "run_pipeline",
        attributes={
            "agent": "orchestrator",
            "recipe": recipe,
            "project_id": project_id,
            "project_name": project_name,
        },
    ):
        return await _run_pipeline_inner(
            recipe, project_id, project_name, intake_data, use_checkpointing
        )


async def _run_pipeline_inner(
    recipe: str,
    project_id: str,
    project_name: str,
    intake_data: Dict[str, Any],
    use_checkpointing: bool = True,
) -> CMEPipelineState:
    """Inner implementation for run_pipeline, wrapped by OTel span."""
    initial_state = create_initial_state(project_id, project_name, intake_data)

    if recipe == "needs":
        if use_checkpointing:
            graph = await create_checkpointed_needs_graph()
        else:
            graph = needs_graph
    elif recipe == "curriculum":
        graph = curriculum_graph  # Add checkpointed version if needed
    elif recipe == "grant":
        if use_checkpointing:
            graph = await create_checkpointed_grant_graph()
        else:
            graph = grant_graph
    else:
        raise ValueError(f"Unknown recipe: {recipe}")
    
    config = {"configurable": {"thread_id": project_id}}
    result = await graph.ainvoke(initial_state, config=config)
    
    return result


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("RECIPE-BASED ORCHESTRATOR - CME GRANT PIPELINE")
    print("=" * 60)
    
    print("\n=== NEEDS PACKAGE GRAPH ===")
    print(needs_graph.get_graph().draw_mermaid())
    
    print("\n=== CURRICULUM PACKAGE GRAPH ===")
    print(curriculum_graph.get_graph().draw_mermaid())
    
    print("\n=== GRANT PACKAGE GRAPH ===")
    print(grant_graph.get_graph().draw_mermaid())

    print("\n" + "=" * 60)
    print("All graphs compiled successfully!")
    print("=" * 60)
