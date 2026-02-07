"""
Recipe-Based Orchestrator - CME Grant Pipeline
===============================================
Composable agent chains ("recipes") for different output types.

Recipes:
- needs_graph: Research → Gap → LO → Needs Assessment
- curriculum_graph: Needs → Curriculum + Protocol + Marketing
- grant_graph: All 11 agents + Prose QA
- full_graph: Complete pipeline with Quality Gates + Human Review

LangGraph Cloud Ready:
- Each recipe is a compiled graph exported at module level
- All use CMEPipelineState for unified state management
- PostgresSaver for checkpointing and recovery
- Parallel execution for independent agents

Decision #10: Recipe-Based Orchestrator (confirmed 2026-02-04)
"""

import os
import operator
import asyncio
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional, Annotated, Literal
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# PostgresSaver is optional - fallback to in-memory if not available
try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    POSTGRES_AVAILABLE = True
except ImportError:
    AsyncPostgresSaver = None
    POSTGRES_AVAILABLE = False

from langsmith import traceable
import logging

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

def get_agent_graph(agent_name: str):
    """Dynamically import agent graph to avoid circular imports."""
    try:
        if agent_name == "research":
            from research_agent import graph
            return graph
        elif agent_name == "clinical":
            from clinical_practice_agent import graph
            return graph
        elif agent_name == "gap_analysis":
            from gap_analysis_agent import graph
            return graph
        elif agent_name == "needs_assessment":
            from needs_assessment_agent import graph
            return graph
        elif agent_name == "learning_objectives":
            from learning_objectives_agent import graph
            return graph
        elif agent_name == "curriculum":
            from curriculum_design_agent import graph
            return graph
        elif agent_name == "protocol":
            from research_protocol_agent import graph
            return graph
        elif agent_name == "marketing":
            from marketing_plan_agent import graph
            return graph
        elif agent_name == "grant_writer":
            from grant_writer_agent import graph
            return graph
        elif agent_name == "prose_quality":
            from prose_quality_agent import graph
            return graph
        elif agent_name == "compliance":
            from compliance_review_agent import graph
            return graph
        else:
            raise ValueError(f"Unknown agent: {agent_name}")
    except ImportError as e:
        logger.error(f"Failed to import agent {agent_name}: {e}")
        raise


# =============================================================================
# WRAPPER NODES
# Each wraps an agent graph, mapping pipeline state to agent state
# =============================================================================

@traceable(name="run_research_agent", run_type="chain", metadata={"agent": "research"})
async def run_research_agent(state: CMEPipelineState) -> dict:
    """Run Research Agent and store output."""
    try:
        graph = get_agent_graph("research")
        
        agent_input = {
            "therapeutic_area": state.get("intake_data", {}).get("therapeutic_area", ""),
            "target_audience": state.get("intake_data", {}).get("target_audience", ""),
            "research_questions": state.get("intake_data", {}).get("research_questions", []),
        }
        
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
        
        agent_input = {
            "therapeutic_area": state.get("intake_data", {}).get("therapeutic_area", ""),
            "target_audience": state.get("intake_data", {}).get("target_audience", ""),
        }
        
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
        
        agent_input = {
            "research_output": state.get("research_output", {}),
            "clinical_output": state.get("clinical_output", {}),
            "therapeutic_area": state.get("intake_data", {}).get("therapeutic_area", ""),
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
        
        agent_input = {
            "gap_analysis_output": state.get("gap_analysis_output", {}),
            "needs_assessment_output": state.get("needs_assessment_output", {}),
            "target_audience": state.get("intake_data", {}).get("target_audience", ""),
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
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "learning_objectives")
            ],
            "current_step": "learning_objectives_failed"
        }


@traceable(name="run_needs_assessment_agent", run_type="chain", metadata={"agent": "needs_assessment"})
async def run_needs_assessment_agent(state: CMEPipelineState) -> dict:
    """Run Needs Assessment Agent."""
    try:
        graph = get_agent_graph("needs_assessment")
        
        # Include feedback from prose quality if retrying
        prose_feedback = None
        if state.get("prose_quality_pass_1") and not state["prose_quality_pass_1"].get("overall_passed"):
            prose_feedback = state["prose_quality_pass_1"].get("feedback", "")
        
        agent_input = {
            "research_output": state.get("research_output", {}),
            "clinical_output": state.get("clinical_output", {}),
            "gap_analysis_output": state.get("gap_analysis_output", {}),
            "learning_objectives_output": state.get("learning_objectives_output", {}),
            "intake_data": state.get("intake_data", {}),
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
        
        agent_input = {
            "needs_assessment_output": state.get("needs_assessment_output", {}),
            "learning_objectives_output": state.get("learning_objectives_output", {}),
            "intake_data": state.get("intake_data", {}),
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
        
        agent_input = {
            "needs_assessment_output": state.get("needs_assessment_output", {}),
            "learning_objectives_output": state.get("learning_objectives_output", {}),
            "curriculum_output": state.get("curriculum_output", {}),
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
        
        agent_input = {
            "needs_assessment_output": state.get("needs_assessment_output", {}),
            "curriculum_output": state.get("curriculum_output", {}),
            "intake_data": state.get("intake_data", {}),
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
        document_text = needs_output.get("full_narrative", "")
        
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
        
        agent_input = {
            "grant_package": grant_output,
            "supporter_company": state.get("intake_data", {}).get("supporter_company", ""),
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
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [
                create_error_record("agent_failure", str(e), "compliance")
            ],
            "current_step": "compliance_failed"
        }


@traceable(name="human_review_gate", run_type="chain")
async def human_review_gate(state: CMEPipelineState) -> dict:
    """Human review checkpoint - sets status to awaiting review."""
    return {
        "status": PipelineStatus.AWAITING_REVIEW.value,
        "current_step": "human_review_pending",
        "updated_at": datetime.now().isoformat()
    }


@traceable(name="mark_complete", run_type="chain")
async def mark_complete(state: CMEPipelineState) -> dict:
    """Mark pipeline as complete."""
    return {
        "status": PipelineStatus.COMPLETE.value,
        "current_step": "complete",
        "updated_at": datetime.now().isoformat()
    }


@traceable(name="mark_failed", run_type="chain")
async def mark_failed(state: CMEPipelineState) -> dict:
    """Mark pipeline as failed and escalate to human intervention."""
    return {
        "status": PipelineStatus.FAILED.value,
        "current_step": "failed_human_intervention_required",
        "updated_at": datetime.now().isoformat()
    }


# =============================================================================
# PARALLEL EXECUTION: FAN-OUT / FAN-IN
# =============================================================================

@traceable(name="early_research_parallel", run_type="chain")
async def run_early_research_parallel(state: CMEPipelineState) -> dict:
    """
    Run Research and Clinical agents in parallel.
    Fan-out pattern: executes both concurrently, then merges results.
    """
    try:
        research_graph = get_agent_graph("research")
        clinical_graph = get_agent_graph("clinical")
        
        intake = state.get("intake_data", {})
        
        research_input = {
            "therapeutic_area": intake.get("therapeutic_area", ""),
            "target_audience": intake.get("target_audience", ""),
            "research_questions": intake.get("research_questions", []),
        }
        
        clinical_input = {
            "therapeutic_area": intake.get("therapeutic_area", ""),
            "target_audience": intake.get("target_audience", ""),
        }
        
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
    result = state.get("prose_quality_pass_1", {})
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
    result = state.get("compliance_result", {})
    if result.get("overall_passed", False):
        return "continue"
    else:
        return "revision_required"


def route_after_human_review(state: CMEPipelineState) -> Literal["approved", "revision_requested", "rejected"]:
    """Route after human review gate."""
    status = state.get("human_review_status", "pending")
    if status == "approved":
        return "approved"
    elif status == "revision_requested":
        return "revision_requested"
    else:
        return "rejected"  # Default to rejected for unknown status


# =============================================================================
# RECIPE 1: NEEDS PACKAGE (with parallel execution)
# Research + Clinical [parallel] → Gap Analysis → LO → Needs → Prose QA → Human Review
# =============================================================================

def create_needs_package_graph():
    """Create the Needs Assessment Package recipe with parallel execution."""
    
    workflow = StateGraph(CMEPipelineState)
    
    # Add nodes
    workflow.add_node("early_research", run_early_research_parallel)  # Parallel!
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality", run_prose_quality_pass_1)
    workflow.add_node("human_review", human_review_gate)
    workflow.add_node("failed", mark_failed)
    
    # Flow with parallel early research
    workflow.set_entry_point("early_research")
    workflow.add_edge("early_research", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality")
    
    # Prose quality routing
    workflow.add_conditional_edges(
        "prose_quality",
        route_after_prose_quality_1,
        {
            "continue": "human_review",
            "retry_needs": "needs_assessment",
            "human_intervention": "failed"
        }
    )
    
    workflow.add_edge("human_review", END)
    workflow.add_edge("failed", END)
    
    return workflow.compile()


# =============================================================================
# RECIPE 2: CURRICULUM PACKAGE (with parallel execution)
# Needs Package → Curriculum + Protocol + Marketing [parallel] → Prose QA → Human Review
# =============================================================================

def create_curriculum_package_graph():
    """Create the Curriculum Package recipe with parallel execution."""
    
    workflow = StateGraph(CMEPipelineState)
    
    # Needs phase (with parallel research)
    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality_1", run_prose_quality_pass_1)
    
    # Curriculum phase (parallel)
    workflow.add_node("design_phase", run_design_phase_parallel)  # Parallel!
    workflow.add_node("human_review", human_review_gate)
    workflow.add_node("failed", mark_failed)
    
    # Flow
    workflow.set_entry_point("early_research")
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
            "human_intervention": "failed"
        }
    )
    
    workflow.add_edge("design_phase", "human_review")
    workflow.add_edge("human_review", END)
    workflow.add_edge("failed", END)
    
    return workflow.compile()


# =============================================================================
# RECIPE 3: GRANT PACKAGE (Full 11 agents with parallel execution)
# All agents + Prose QA (2 passes) + Compliance + Human Review
# =============================================================================

def create_grant_package_graph():
    """Create the Grant Package recipe with full parallel execution."""
    
    workflow = StateGraph(CMEPipelineState)
    
    # Early phase (parallel research)
    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality_1", run_prose_quality_pass_1)
    
    # Design phase (parallel curriculum, protocol, marketing)
    workflow.add_node("design_phase", run_design_phase_parallel)
    
    # Grant assembly
    workflow.add_node("grant_writer", run_grant_writer_agent)
    workflow.add_node("prose_quality_2", run_prose_quality_pass_2)
    workflow.add_node("compliance", run_compliance_agent)
    
    # Final gates
    workflow.add_node("human_review", human_review_gate)
    workflow.add_node("complete", mark_complete)
    workflow.add_node("failed", mark_failed)
    
    # Flow
    workflow.set_entry_point("early_research")
    workflow.add_edge("early_research", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality_1")
    
    # First prose quality gate
    workflow.add_conditional_edges(
        "prose_quality_1",
        route_after_prose_quality_1,
        {
            "continue": "design_phase",
            "retry_needs": "needs_assessment",
            "human_intervention": "failed"
        }
    )
    
    workflow.add_edge("design_phase", "grant_writer")
    workflow.add_edge("grant_writer", "prose_quality_2")
    
    # Second prose quality gate
    workflow.add_conditional_edges(
        "prose_quality_2",
        route_after_prose_quality_2,
        {
            "continue": "compliance",
            "retry_grant": "grant_writer",
            "human_intervention": "failed"
        }
    )
    
    # Compliance gate
    workflow.add_conditional_edges(
        "compliance",
        route_after_compliance,
        {
            "continue": "human_review",
            "revision_required": "grant_writer"
        }
    )
    
    workflow.add_edge("human_review", "complete")
    workflow.add_edge("complete", END)
    workflow.add_edge("failed", END)
    
    return workflow.compile()


# =============================================================================
# RECIPE 4: FULL PIPELINE WITH HUMAN REVIEW ROUTING
# Same as Grant Package but with human review routing
# =============================================================================

def create_full_pipeline_graph():
    """Create the Full Pipeline recipe with human review routing."""
    
    workflow = StateGraph(CMEPipelineState)
    
    # Early phase (parallel research)
    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality_1", run_prose_quality_pass_1)
    
    # Design phase (parallel)
    workflow.add_node("design_phase", run_design_phase_parallel)
    
    # Grant assembly
    workflow.add_node("grant_writer", run_grant_writer_agent)
    workflow.add_node("prose_quality_2", run_prose_quality_pass_2)
    workflow.add_node("compliance", run_compliance_agent)
    
    # Human review with routing
    workflow.add_node("human_review", human_review_gate)
    workflow.add_node("complete", mark_complete)
    workflow.add_node("failed", mark_failed)
    
    # Flow
    workflow.set_entry_point("early_research")
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
            "human_intervention": "failed"
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
            "human_intervention": "failed"
        }
    )
    
    workflow.add_conditional_edges(
        "compliance",
        route_after_compliance,
        {
            "continue": "human_review",
            "revision_required": "grant_writer"
        }
    )
    
    # Human review routing
    workflow.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "approved": "complete",
            "revision_requested": "grant_writer",
            "rejected": "failed"
        }
    )
    
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
full_graph = create_full_pipeline_graph()


# =============================================================================
# FACTORY FUNCTIONS FOR CHECKPOINTED GRAPHS
# =============================================================================

async def create_checkpointed_needs_graph():
    """Create needs graph with PostgresSaver checkpointing."""
    checkpointer = await get_checkpointer()
    workflow = StateGraph(CMEPipelineState)
    
    # Add nodes (same as create_needs_package_graph)
    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality", run_prose_quality_pass_1)
    workflow.add_node("human_review", human_review_gate)
    workflow.add_node("failed", mark_failed)
    
    workflow.set_entry_point("early_research")
    workflow.add_edge("early_research", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality")
    
    workflow.add_conditional_edges(
        "prose_quality",
        route_after_prose_quality_1,
        {
            "continue": "human_review",
            "retry_needs": "needs_assessment",
            "human_intervention": "failed"
        }
    )
    
    workflow.add_edge("human_review", END)
    workflow.add_edge("failed", END)
    
    return workflow.compile(checkpointer=checkpointer)


async def create_checkpointed_grant_graph():
    """Create grant graph with PostgresSaver checkpointing."""
    checkpointer = await get_checkpointer()
    workflow = StateGraph(CMEPipelineState)
    
    # Add all nodes
    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality_1", run_prose_quality_pass_1)
    workflow.add_node("design_phase", run_design_phase_parallel)
    workflow.add_node("grant_writer", run_grant_writer_agent)
    workflow.add_node("prose_quality_2", run_prose_quality_pass_2)
    workflow.add_node("compliance", run_compliance_agent)
    workflow.add_node("human_review", human_review_gate)
    workflow.add_node("complete", mark_complete)
    workflow.add_node("failed", mark_failed)
    
    workflow.set_entry_point("early_research")
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
            "human_intervention": "failed"
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
            "human_intervention": "failed"
        }
    )
    
    workflow.add_conditional_edges(
        "compliance",
        route_after_compliance,
        {
            "continue": "human_review",
            "revision_required": "grant_writer"
        }
    )
    
    workflow.add_edge("human_review", "complete")
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
    elif recipe == "full":
        graph = full_graph  # Add checkpointed version if needed
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
    
    print("\n=== FULL PIPELINE GRAPH ===")
    print(full_graph.get_graph().draw_mermaid())
    
    print("\n" + "=" * 60)
    print("All graphs compiled successfully!")
    print("=" * 60)
