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
"""

import operator
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langsmith import traceable


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


class CMEPipelineState(TypedDict):
    """Unified state for all CME pipeline recipes."""
    
    # === PROJECT IDENTITY ===
    project_id: str
    project_name: str
    status: str
    created_at: str
    
    # === INTAKE DATA ===
    intake_data: Dict[str, Any]
    
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
    human_review_status: Optional[str]
    human_review_notes: Optional[str]
    human_reviewer: Optional[str]
    
    # === CONTROL ===
    current_step: str
    retry_count: int
    messages: Annotated[list, add_messages]
    errors: List[str]


# =============================================================================
# AGENT IMPORTS (lazy loaded to avoid circular imports)
# =============================================================================

def get_agent_graph(agent_name: str):
    """Dynamically import agent graph to avoid circular imports."""
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


# =============================================================================
# WRAPPER NODES
# Each wraps an agent graph, mapping pipeline state to agent state
# =============================================================================

@traceable(name="run_research_agent", run_type="chain")
async def run_research_agent(state: CMEPipelineState) -> dict:
    """Run Research Agent and store output."""
    graph = get_agent_graph("research")
    
    agent_input = {
        "therapeutic_area": state.get("intake_data", {}).get("therapeutic_area", ""),
        "target_audience": state.get("intake_data", {}).get("target_audience", ""),
        "research_questions": state.get("intake_data", {}).get("research_questions", []),
    }
    
    result = await graph.ainvoke(agent_input)
    
    return {
        "research_output": result,
        "current_step": "research_complete"
    }


@traceable(name="run_clinical_agent", run_type="chain")
async def run_clinical_agent(state: CMEPipelineState) -> dict:
    """Run Clinical Practice Agent and store output."""
    graph = get_agent_graph("clinical")
    
    agent_input = {
        "therapeutic_area": state.get("intake_data", {}).get("therapeutic_area", ""),
        "target_audience": state.get("intake_data", {}).get("target_audience", ""),
    }
    
    result = await graph.ainvoke(agent_input)
    
    return {
        "clinical_output": result,
        "current_step": "clinical_complete"
    }


@traceable(name="run_gap_analysis_agent", run_type="chain")
async def run_gap_analysis_agent(state: CMEPipelineState) -> dict:
    """Run Gap Analysis Agent."""
    graph = get_agent_graph("gap_analysis")
    
    agent_input = {
        "research_output": state.get("research_output", {}),
        "clinical_output": state.get("clinical_output", {}),
        "therapeutic_area": state.get("intake_data", {}).get("therapeutic_area", ""),
    }
    
    result = await graph.ainvoke(agent_input)
    
    return {
        "gap_analysis_output": result,
        "current_step": "gap_analysis_complete"
    }


@traceable(name="run_learning_objectives_agent", run_type="chain")
async def run_learning_objectives_agent(state: CMEPipelineState) -> dict:
    """Run Learning Objectives Agent."""
    graph = get_agent_graph("learning_objectives")
    
    agent_input = {
        "gap_analysis_output": state.get("gap_analysis_output", {}),
        "needs_assessment_output": state.get("needs_assessment_output", {}),
        "target_audience": state.get("intake_data", {}).get("target_audience", ""),
    }
    
    result = await graph.ainvoke(agent_input)
    
    return {
        "learning_objectives_output": result,
        "current_step": "learning_objectives_complete"
    }


@traceable(name="run_needs_assessment_agent", run_type="chain")
async def run_needs_assessment_agent(state: CMEPipelineState) -> dict:
    """Run Needs Assessment Agent."""
    graph = get_agent_graph("needs_assessment")
    
    agent_input = {
        "research_output": state.get("research_output", {}),
        "clinical_output": state.get("clinical_output", {}),
        "gap_analysis_output": state.get("gap_analysis_output", {}),
        "learning_objectives_output": state.get("learning_objectives_output", {}),
        "intake_data": state.get("intake_data", {}),
    }
    
    result = await graph.ainvoke(agent_input)
    
    return {
        "needs_assessment_output": result,
        "current_step": "needs_assessment_complete"
    }


@traceable(name="run_curriculum_agent", run_type="chain")
async def run_curriculum_agent(state: CMEPipelineState) -> dict:
    """Run Curriculum Design Agent."""
    graph = get_agent_graph("curriculum")
    
    agent_input = {
        "needs_assessment_output": state.get("needs_assessment_output", {}),
        "learning_objectives_output": state.get("learning_objectives_output", {}),
        "intake_data": state.get("intake_data", {}),
    }
    
    result = await graph.ainvoke(agent_input)
    
    return {
        "curriculum_output": result,
        "current_step": "curriculum_complete"
    }


@traceable(name="run_protocol_agent", run_type="chain")
async def run_protocol_agent(state: CMEPipelineState) -> dict:
    """Run Research Protocol Agent."""
    graph = get_agent_graph("protocol")
    
    agent_input = {
        "needs_assessment_output": state.get("needs_assessment_output", {}),
        "learning_objectives_output": state.get("learning_objectives_output", {}),
        "curriculum_output": state.get("curriculum_output", {}),
    }
    
    result = await graph.ainvoke(agent_input)
    
    return {
        "protocol_output": result,
        "current_step": "protocol_complete"
    }


@traceable(name="run_marketing_agent", run_type="chain")
async def run_marketing_agent(state: CMEPipelineState) -> dict:
    """Run Marketing Plan Agent."""
    graph = get_agent_graph("marketing")
    
    agent_input = {
        "needs_assessment_output": state.get("needs_assessment_output", {}),
        "curriculum_output": state.get("curriculum_output", {}),
        "intake_data": state.get("intake_data", {}),
    }
    
    result = await graph.ainvoke(agent_input)
    
    return {
        "marketing_output": result,
        "current_step": "marketing_complete"
    }


@traceable(name="run_grant_writer_agent", run_type="chain")
async def run_grant_writer_agent(state: CMEPipelineState) -> dict:
    """Run Grant Writer Agent."""
    graph = get_agent_graph("grant_writer")
    
    intake = state.get("intake_data", {})
    
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
    }
    
    result = await graph.ainvoke(agent_input)
    
    return {
        "grant_package_output": result,
        "current_step": "grant_writer_complete"
    }


@traceable(name="run_prose_quality_pass_1", run_type="chain")
async def run_prose_quality_pass_1(state: CMEPipelineState) -> dict:
    """Run Prose Quality Agent (Pass 1 - after Needs Assessment)."""
    graph = get_agent_graph("prose_quality")
    
    needs_output = state.get("needs_assessment_output", {})
    document_text = needs_output.get("full_narrative", "")
    
    agent_input = {
        "document_text": document_text,
        "pass_number": 1,
        "character_name": state.get("intake_data", {}).get("character_name"),
    }
    
    result = await graph.ainvoke(agent_input)
    
    return {
        "prose_quality_pass_1": result,
        "current_step": "prose_quality_1_complete"
    }


@traceable(name="run_prose_quality_pass_2", run_type="chain")
async def run_prose_quality_pass_2(state: CMEPipelineState) -> dict:
    """Run Prose Quality Agent (Pass 2 - after Grant Writer)."""
    graph = get_agent_graph("prose_quality")
    
    grant_output = state.get("grant_package_output", {})
    document_text = grant_output.get("complete_document_markdown", "")
    
    agent_input = {
        "document_text": document_text,
        "pass_number": 2,
        "character_name": state.get("intake_data", {}).get("character_name"),
    }
    
    result = await graph.ainvoke(agent_input)
    
    return {
        "prose_quality_pass_2": result,
        "current_step": "prose_quality_2_complete"
    }


@traceable(name="run_compliance_agent", run_type="chain")
async def run_compliance_agent(state: CMEPipelineState) -> dict:
    """Run Compliance Review Agent."""
    graph = get_agent_graph("compliance")
    
    grant_output = state.get("grant_package_output", {})
    
    agent_input = {
        "grant_package": grant_output,
        "supporter_company": state.get("intake_data", {}).get("supporter_company", ""),
    }
    
    result = await graph.ainvoke(agent_input)
    
    return {
        "compliance_result": result,
        "current_step": "compliance_complete"
    }


@traceable(name="human_review_gate", run_type="chain")
async def human_review_gate(state: CMEPipelineState) -> dict:
    """Human review checkpoint - sets status to awaiting review."""
    return {
        "status": PipelineStatus.AWAITING_REVIEW.value,
        "current_step": "human_review_pending"
    }


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def route_after_prose_quality_1(state: CMEPipelineState) -> str:
    """Route after first prose quality pass."""
    result = state.get("prose_quality_pass_1", {})
    if result.get("overall_passed", False):
        return "continue"
    else:
        retry_count = state.get("retry_count", 0)
        if retry_count < 3:
            return "retry_needs"
        else:
            return "human_intervention"


def route_after_prose_quality_2(state: CMEPipelineState) -> str:
    """Route after second prose quality pass."""
    result = state.get("prose_quality_pass_2", {})
    if result.get("overall_passed", False):
        return "continue"
    else:
        retry_count = state.get("retry_count", 0)
        if retry_count < 3:
            return "retry_grant"
        else:
            return "human_intervention"


def route_after_compliance(state: CMEPipelineState) -> str:
    """Route after compliance review."""
    result = state.get("compliance_result", {})
    if result.get("overall_passed", False):
        return "continue"
    else:
        return "revision_required"


# =============================================================================
# RECIPE 1: NEEDS PACKAGE
# Research → Gap Analysis → Learning Objectives → Needs Assessment → Prose QA → Human Review
# =============================================================================

def create_needs_package_graph():
    """Create the Needs Assessment Package recipe."""
    
    workflow = StateGraph(CMEPipelineState)
    
    # Add nodes
    workflow.add_node("research", run_research_agent)
    workflow.add_node("clinical", run_clinical_agent)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality", run_prose_quality_pass_1)
    workflow.add_node("human_review", human_review_gate)
    
    # Define flow: Research + Clinical parallel, then sequential
    workflow.set_entry_point("research")
    workflow.add_edge("research", "clinical")
    workflow.add_edge("clinical", "gap_analysis")
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
            "human_intervention": "human_review"
        }
    )
    
    workflow.add_edge("human_review", END)
    
    return workflow.compile()


# =============================================================================
# RECIPE 2: CURRICULUM PACKAGE
# Needs Package → Curriculum + Protocol + Marketing → Prose QA → Human Review
# =============================================================================

def create_curriculum_package_graph():
    """Create the Curriculum Package recipe."""
    
    workflow = StateGraph(CMEPipelineState)
    
    # Include needs package agents
    workflow.add_node("research", run_research_agent)
    workflow.add_node("clinical", run_clinical_agent)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality_1", run_prose_quality_pass_1)
    
    # Curriculum phase
    workflow.add_node("curriculum", run_curriculum_agent)
    workflow.add_node("protocol", run_protocol_agent)
    workflow.add_node("marketing", run_marketing_agent)
    workflow.add_node("human_review", human_review_gate)
    
    # Flow
    workflow.set_entry_point("research")
    workflow.add_edge("research", "clinical")
    workflow.add_edge("clinical", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality_1")
    
    workflow.add_conditional_edges(
        "prose_quality_1",
        route_after_prose_quality_1,
        {
            "continue": "curriculum",
            "retry_needs": "needs_assessment",
            "human_intervention": "human_review"
        }
    )
    
    # Sequential curriculum phase (could be parallel with fan-out/fan-in)
    workflow.add_edge("curriculum", "protocol")
    workflow.add_edge("protocol", "marketing")
    workflow.add_edge("marketing", "human_review")
    workflow.add_edge("human_review", END)
    
    return workflow.compile()


# =============================================================================
# RECIPE 3: GRANT PACKAGE
# All 11 agents + Prose QA (2 passes) + Compliance + Human Review
# =============================================================================

def create_grant_package_graph():
    """Create the Grant Package recipe."""
    
    workflow = StateGraph(CMEPipelineState)
    
    # All agents
    workflow.add_node("research", run_research_agent)
    workflow.add_node("clinical", run_clinical_agent)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality_1", run_prose_quality_pass_1)
    workflow.add_node("curriculum", run_curriculum_agent)
    workflow.add_node("protocol", run_protocol_agent)
    workflow.add_node("marketing", run_marketing_agent)
    workflow.add_node("grant_writer", run_grant_writer_agent)
    workflow.add_node("prose_quality_2", run_prose_quality_pass_2)
    workflow.add_node("compliance", run_compliance_agent)
    workflow.add_node("human_review", human_review_gate)
    
    # Flow
    workflow.set_entry_point("research")
    workflow.add_edge("research", "clinical")
    workflow.add_edge("clinical", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality_1")
    
    workflow.add_conditional_edges(
        "prose_quality_1",
        route_after_prose_quality_1,
        {
            "continue": "curriculum",
            "retry_needs": "needs_assessment",
            "human_intervention": "human_review"
        }
    )
    
    workflow.add_edge("curriculum", "protocol")
    workflow.add_edge("protocol", "marketing")
    workflow.add_edge("marketing", "grant_writer")
    workflow.add_edge("grant_writer", "prose_quality_2")
    
    workflow.add_conditional_edges(
        "prose_quality_2",
        route_after_prose_quality_2,
        {
            "continue": "compliance",
            "retry_grant": "grant_writer",
            "human_intervention": "human_review"
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
    
    workflow.add_edge("human_review", END)
    
    return workflow.compile()


# =============================================================================
# RECIPE 4: FULL PIPELINE
# Same as Grant Package (grant_package is the full pipeline)
# =============================================================================

def create_full_pipeline_graph():
    """Create the Full Pipeline recipe (alias for grant_package)."""
    return create_grant_package_graph()


# =============================================================================
# COMPILE AND EXPORT ALL RECIPES
# =============================================================================

needs_graph = create_needs_package_graph()
curriculum_graph = create_curriculum_package_graph()
grant_graph = create_grant_package_graph()
full_graph = create_full_pipeline_graph()


if __name__ == "__main__":
    print("=== NEEDS PACKAGE GRAPH ===")
    print(needs_graph.get_graph().draw_mermaid())
    print("\n=== CURRICULUM PACKAGE GRAPH ===")
    print(curriculum_graph.get_graph().draw_mermaid())
    print("\n=== GRANT PACKAGE GRAPH ===")
    print(grant_graph.get_graph().draw_mermaid())
