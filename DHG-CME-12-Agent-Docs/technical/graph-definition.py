"""
DHG CME 12-Agent System - Graph Definition
==========================================
LangGraph StateGraph orchestration for the 12-agent CME grant pipeline.

This module defines:
- Individual agent nodes
- Conditional routing logic
- Parallel execution fan-out/fan-in
- Quality gates
- Human review checkpoints

Usage:
    from graph_definition import create_cme_graph, run_pipeline
    
    graph = create_cme_graph()
    result = await run_pipeline(graph, intake_data)
"""

from typing import Literal, Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from state_schema import (
    CMEGrantState,
    ProjectStatus,
    HumanReviewStatus,
    create_initial_state,
    update_state_status,
    validate_state_for_agent,
)

# Import agent implementations (these would be in separate modules)
# from agents.research import research_agent
# from agents.clinical import clinical_agent
# etc.


# =============================================================================
# AGENT NODE FUNCTIONS
# =============================================================================

async def research_node(state: CMEGrantState) -> CMEGrantState:
    """
    Agent 2: Research Agent
    Executes literature review, epidemiology, market intelligence.
    """
    validate_state_for_agent(state, "research_agent")
    state = update_state_status(state, ProjectStatus.RESEARCH)
    
    # Agent execution would go here
    # state["research_output"] = await research_agent.run(state["intake"])
    
    return state


async def clinical_node(state: CMEGrantState) -> CMEGrantState:
    """
    Agent 3: Clinical Practice Agent
    Analyzes real-world practice patterns and barriers.
    """
    validate_state_for_agent(state, "clinical_agent")
    state = update_state_status(state, ProjectStatus.CLINICAL)
    
    # Agent execution would go here
    # state["clinical_output"] = await clinical_agent.run(state["intake"])
    
    return state


async def gap_analysis_node(state: CMEGrantState) -> CMEGrantState:
    """
    Agent 4: Gap Analysis Agent
    Synthesizes research + clinical into prioritized gaps.
    """
    validate_state_for_agent(state, "gap_analysis_agent")
    state = update_state_status(state, ProjectStatus.GAP_ANALYSIS)
    
    # Agent execution would go here
    # state["gap_analysis_output"] = await gap_analysis_agent.run(
    #     state["research_output"],
    #     state["clinical_output"]
    # )
    
    return state


async def needs_assessment_node(state: CMEGrantState) -> CMEGrantState:
    """
    Agent 5: Needs Assessment Agent
    Generates 3,100+ word narrative with cold open.
    """
    validate_state_for_agent(state, "needs_assessment_agent")
    state = update_state_status(state, ProjectStatus.NEEDS_ASSESSMENT)
    
    # Agent execution would go here
    # state["needs_assessment_output"] = await needs_assessment_agent.run(
    #     state["gap_analysis_output"],
    #     state["intake"]
    # )
    
    return state


async def prose_quality_node(state: CMEGrantState) -> CMEGrantState:
    """
    Agent 11: Prose Quality Agent
    Runs twice: after needs assessment and after grant assembly.
    """
    # Determine which pass this is
    if state["status"] == ProjectStatus.NEEDS_ASSESSMENT:
        state = update_state_status(state, ProjectStatus.PROSE_REVIEW_1)
        pass_number = 1
        content = state["needs_assessment_output"]["document_text"]
    else:
        state = update_state_status(state, ProjectStatus.PROSE_REVIEW_2)
        pass_number = 2
        content = state["grant_package_output"]
    
    # Agent execution would go here
    # score = await prose_quality_agent.run(content, pass_number)
    # state["prose_quality_scores"].append(score)
    
    return state


async def learning_objectives_node(state: CMEGrantState) -> CMEGrantState:
    """
    Agent 6: Learning Objectives Agent
    Creates Moore's Framework-based measurable objectives.
    """
    validate_state_for_agent(state, "learning_objectives_agent")
    state = update_state_status(state, ProjectStatus.LEARNING_OBJECTIVES)
    
    # Agent execution would go here
    # state["learning_objectives_output"] = await learning_objectives_agent.run(
    #     state["needs_assessment_output"],
    #     state["gap_analysis_output"],
    #     state["intake"]
    # )
    
    return state


async def curriculum_node(state: CMEGrantState) -> CMEGrantState:
    """
    Agent 7: Curriculum Design Agent
    Creates educational design + 500w innovation section.
    """
    validate_state_for_agent(state, "curriculum_agent")
    state = update_state_status(state, ProjectStatus.CURRICULUM)
    
    # Agent execution would go here
    # state["curriculum_output"] = await curriculum_agent.run(
    #     state["learning_objectives_output"],
    #     state["needs_assessment_output"],
    #     state["intake"]
    # )
    
    return state


async def protocol_node(state: CMEGrantState) -> CMEGrantState:
    """
    Agent 8: Research Protocol Agent
    Creates IRB-ready outcomes research protocol.
    """
    validate_state_for_agent(state, "protocol_agent")
    state = update_state_status(state, ProjectStatus.PROTOCOL)
    
    # Agent execution would go here
    # state["protocol_output"] = await protocol_agent.run(
    #     state["learning_objectives_output"],
    #     state["intake"]
    # )
    
    return state


async def marketing_node(state: CMEGrantState) -> CMEGrantState:
    """
    Agent 9: Marketing Plan Agent
    Creates multi-channel audience generation strategy.
    """
    validate_state_for_agent(state, "marketing_agent")
    state = update_state_status(state, ProjectStatus.MARKETING)
    
    # Agent execution would go here
    # state["marketing_output"] = await marketing_agent.run(
    #     state["learning_objectives_output"],
    #     state["intake"]
    # )
    
    return state


async def grant_writer_node(state: CMEGrantState) -> CMEGrantState:
    """
    Agent 10: Grant Writer Agent
    Assembles complete grant package from all upstream outputs.
    """
    validate_state_for_agent(state, "grant_writer_agent")
    state = update_state_status(state, ProjectStatus.GRANT_WRITING)
    
    # Agent execution would go here
    # state["grant_package_output"] = await grant_writer_agent.run(
    #     state["curriculum_output"],
    #     state["protocol_output"],
    #     state["marketing_output"],
    #     state["needs_assessment_output"],
    #     state["learning_objectives_output"],
    #     state["intake"]
    # )
    
    return state


async def compliance_node(state: CMEGrantState) -> CMEGrantState:
    """
    Agent 12: Compliance Review Agent
    Verifies ACCME standards, independence, fair balance.
    """
    validate_state_for_agent(state, "compliance_agent")
    state = update_state_status(state, ProjectStatus.COMPLIANCE)
    
    # Agent execution would go here
    # state["compliance_score"] = await compliance_agent.run(
    #     state["grant_package_output"],
    #     state["intake"]
    # )
    
    return state


async def human_review_node(state: CMEGrantState) -> CMEGrantState:
    """
    Human Review Gate
    Pauses execution for human approval.
    """
    state = update_state_status(state, ProjectStatus.HUMAN_REVIEW)
    state["human_review_status"] = HumanReviewStatus.PENDING
    
    # In production, this would:
    # 1. Send notification to reviewer
    # 2. Present package for review
    # 3. Wait for approval/rejection/revision
    
    return state


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def route_after_prose_quality(state: CMEGrantState) -> Literal[
    "learning_objectives",
    "needs_assessment",
    "compliance",
    "grant_writer",
    "human_escalation"
]:
    """
    Route based on prose quality results.
    
    Pass 1 (after needs assessment):
        - Pass → learning_objectives
        - Fail → needs_assessment (retry)
        
    Pass 2 (after grant assembly):
        - Pass → compliance
        - Fail → grant_writer (retry)
    """
    latest_score = state["prose_quality_scores"][-1]
    
    if latest_score["passed"]:
        if state["status"] == ProjectStatus.PROSE_REVIEW_1:
            return "learning_objectives"
        else:  # PROSE_REVIEW_2
            return "compliance"
    else:
        # Failed - check retry count
        if state["retry_count"] >= 3:
            return "human_escalation"
        
        # Route back for revision
        if state["status"] == ProjectStatus.PROSE_REVIEW_1:
            return "needs_assessment"
        else:
            return "grant_writer"


def route_after_compliance(state: CMEGrantState) -> Literal[
    "human_review",
    "grant_writer",
    "learning_objectives",
    "gap_analysis",
    "human_escalation"
]:
    """
    Route based on compliance review results.
    
    Compliant → human_review
    Non-compliant → route to agent that can fix the issue
    """
    if state["compliance_score"]["compliant"]:
        return "human_review"
    
    # Check retry count
    if state["retry_count"] >= 2:
        return "human_escalation"
    
    # Route to appropriate agent based on issue type
    remediation = state["compliance_score"].get("remediation_required", {})
    issues = remediation.get("issues", [])
    
    if not issues:
        return "grant_writer"  # Default
    
    # Find highest severity issue
    critical_issues = [i for i in issues if i["severity"] == "critical"]
    issue = critical_issues[0] if critical_issues else issues[0]
    
    routing_map = {
        "commercial_bias": "grant_writer",
        "missing_disclosure": "grant_writer",
        "objective_format": "learning_objectives",
        "gap_evidence": "gap_analysis",
        "fair_balance": "grant_writer",
    }
    
    return routing_map.get(issue["category"], "grant_writer")


def route_after_human_review(state: CMEGrantState) -> Literal[
    "complete",
    "rejected",
    "revision_routing"
]:
    """
    Route based on human review decision.
    
    Approved → complete
    Rejected → rejected (terminal)
    Revision requested → route to specified agent
    """
    status = state["human_review_status"]
    
    if status == HumanReviewStatus.APPROVED:
        return "complete"
    elif status == HumanReviewStatus.REJECTED:
        return "rejected"
    else:  # REVISION_REQUESTED
        return "revision_routing"


# =============================================================================
# PARALLEL EXECUTION HELPERS
# =============================================================================

def fan_out_parallel_1(state: CMEGrantState) -> List[str]:
    """
    Fan out to Research and Clinical agents (parallel group 1).
    Both execute simultaneously.
    """
    return ["research", "clinical"]


def fan_in_parallel_1(state: CMEGrantState) -> bool:
    """
    Fan in check for parallel group 1.
    Returns True when both Research and Clinical are complete.
    """
    return (
        state["research_output"] is not None and
        state["clinical_output"] is not None
    )


def fan_out_parallel_2(state: CMEGrantState) -> List[str]:
    """
    Fan out to Curriculum, Protocol, and Marketing agents (parallel group 2).
    All three execute simultaneously.
    """
    return ["curriculum", "protocol", "marketing"]


def fan_in_parallel_2(state: CMEGrantState) -> bool:
    """
    Fan in check for parallel group 2.
    Returns True when Curriculum, Protocol, and Marketing are complete.
    """
    return (
        state["curriculum_output"] is not None and
        state["protocol_output"] is not None and
        state["marketing_output"] is not None
    )


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def create_cme_graph() -> StateGraph:
    """
    Create the complete CME grant generation graph.
    
    Execution Flow:
    ┌─────────────────────────────────────────────────────────────┐
    │                        START                                 │
    └─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              PARALLEL: Research + Clinical                   │
    └─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                      Gap Analysis                            │
    └─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                    Needs Assessment                          │
    └─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              QUALITY GATE 1: Prose Quality                   │
    └─────────────────────────────────────────────────────────────┘
                          │           │
                    Pass  │           │ Fail (retry)
                          ▼           ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                  Learning Objectives                         │
    └─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │       PARALLEL: Curriculum + Protocol + Marketing            │
    └─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                      Grant Writer                            │
    └─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              QUALITY GATE 2: Prose Quality                   │
    └─────────────────────────────────────────────────────────────┘
                          │           │
                    Pass  │           │ Fail (retry)
                          ▼           ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                   Compliance Review                          │
    └─────────────────────────────────────────────────────────────┘
                          │           │
                 Compliant│           │ Non-compliant (route to fix)
                          ▼           ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                     Human Review                             │
    └─────────────────────────────────────────────────────────────┘
                          │           │
                 Approved │           │ Rejected/Revision
                          ▼           ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                         END                                  │
    └─────────────────────────────────────────────────────────────┘
    """
    
    # Initialize graph with state schema
    graph = StateGraph(CMEGrantState)
    
    # -------------------------------------------------------------------------
    # Add nodes
    # -------------------------------------------------------------------------
    
    # Parallel group 1
    graph.add_node("research", research_node)
    graph.add_node("clinical", clinical_node)
    
    # Sequential nodes
    graph.add_node("gap_analysis", gap_analysis_node)
    graph.add_node("needs_assessment", needs_assessment_node)
    graph.add_node("prose_quality", prose_quality_node)
    graph.add_node("learning_objectives", learning_objectives_node)
    
    # Parallel group 2
    graph.add_node("curriculum", curriculum_node)
    graph.add_node("protocol", protocol_node)
    graph.add_node("marketing", marketing_node)
    
    # Final stages
    graph.add_node("grant_writer", grant_writer_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("human_review", human_review_node)
    
    # -------------------------------------------------------------------------
    # Add edges
    # -------------------------------------------------------------------------
    
    # Entry point: fan out to parallel group 1
    graph.set_entry_point("research")
    graph.add_edge("research", "gap_analysis")  # Will wait for clinical
    graph.add_edge("clinical", "gap_analysis")  # Will wait for research
    
    # Note: LangGraph handles fan-in automatically when multiple edges
    # point to the same node. gap_analysis waits for both.
    
    # Sequential flow
    graph.add_edge("gap_analysis", "needs_assessment")
    graph.add_edge("needs_assessment", "prose_quality")
    
    # Conditional after prose quality (pass 1)
    graph.add_conditional_edges(
        "prose_quality",
        route_after_prose_quality,
        {
            "learning_objectives": "learning_objectives",
            "needs_assessment": "needs_assessment",  # Retry
            "compliance": "compliance",  # Pass 2
            "grant_writer": "grant_writer",  # Retry
            "human_escalation": END,
        }
    )
    
    # Fan out to parallel group 2
    graph.add_edge("learning_objectives", "curriculum")
    graph.add_edge("learning_objectives", "protocol")
    graph.add_edge("learning_objectives", "marketing")
    
    # Fan in to grant writer
    graph.add_edge("curriculum", "grant_writer")
    graph.add_edge("protocol", "grant_writer")
    graph.add_edge("marketing", "grant_writer")
    
    # Grant writer to prose quality (pass 2)
    graph.add_edge("grant_writer", "prose_quality")
    
    # Conditional after compliance
    graph.add_conditional_edges(
        "compliance",
        route_after_compliance,
        {
            "human_review": "human_review",
            "grant_writer": "grant_writer",
            "learning_objectives": "learning_objectives",
            "gap_analysis": "gap_analysis",
            "human_escalation": END,
        }
    )
    
    # Conditional after human review
    graph.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "complete": END,
            "rejected": END,
            "revision_routing": "grant_writer",  # Simplified; could be more granular
        }
    )
    
    return graph


# =============================================================================
# CHECKPOINTING
# =============================================================================

def create_checkpointer(connection_string: str) -> PostgresSaver:
    """
    Create PostgreSQL checkpointer for state persistence.
    
    Args:
        connection_string: PostgreSQL connection string
        
    Returns:
        Configured PostgresSaver instance
    """
    return PostgresSaver.from_conn_string(connection_string)


# =============================================================================
# PIPELINE EXECUTION
# =============================================================================

async def run_pipeline(
    intake_data: Dict[str, Any],
    project_id: str,
    project_name: str,
    db_connection: str,
    config: Dict[str, Any] = None
) -> CMEGrantState:
    """
    Execute the complete CME grant generation pipeline.
    
    Args:
        intake_data: Validated intake form data
        project_id: Unique project identifier
        project_name: Human-readable project name
        db_connection: PostgreSQL connection string
        config: Optional LangGraph config overrides
        
    Returns:
        Final state with complete grant package
    """
    # Create initial state
    initial_state = create_initial_state(
        project_id=project_id,
        project_name=project_name,
        intake_data=intake_data
    )
    
    # Create graph and checkpointer
    graph = create_cme_graph()
    checkpointer = create_checkpointer(db_connection)
    
    # Compile graph with checkpointing
    compiled = graph.compile(checkpointer=checkpointer)
    
    # Default config
    run_config = {
        "configurable": {
            "thread_id": project_id,
        },
        "recursion_limit": 50,  # Max steps before forced termination
    }
    
    if config:
        run_config.update(config)
    
    # Execute pipeline
    final_state = await compiled.ainvoke(initial_state, config=run_config)
    
    return final_state


async def resume_pipeline(
    project_id: str,
    db_connection: str,
    updates: Dict[str, Any] = None
) -> CMEGrantState:
    """
    Resume a paused pipeline (e.g., after human review).
    
    Args:
        project_id: Project identifier (thread_id)
        db_connection: PostgreSQL connection string
        updates: State updates to apply before resuming
        
    Returns:
        Final state after resumed execution
    """
    graph = create_cme_graph()
    checkpointer = create_checkpointer(db_connection)
    compiled = graph.compile(checkpointer=checkpointer)
    
    config = {
        "configurable": {
            "thread_id": project_id,
        }
    }
    
    # Apply updates if provided (e.g., human review decision)
    if updates:
        # Get current state
        current_state = await compiled.aget_state(config)
        current_state.values.update(updates)
        await compiled.aupdate_state(config, current_state.values)
    
    # Resume execution
    final_state = await compiled.ainvoke(None, config=config)
    
    return final_state


# =============================================================================
# OBSERVABILITY
# =============================================================================

def get_pipeline_status(project_id: str, db_connection: str) -> Dict[str, Any]:
    """
    Get current status of a pipeline execution.
    
    Args:
        project_id: Project identifier
        db_connection: PostgreSQL connection string
        
    Returns:
        Status information including current node, progress, errors
    """
    graph = create_cme_graph()
    checkpointer = create_checkpointer(db_connection)
    compiled = graph.compile(checkpointer=checkpointer)
    
    config = {"configurable": {"thread_id": project_id}}
    
    # Get state snapshot
    state = compiled.get_state(config)
    
    return {
        "project_id": project_id,
        "status": state.values.get("status"),
        "current_agent": state.values.get("current_agent"),
        "execution_history": state.values.get("execution_history", []),
        "errors": state.values.get("errors", []),
        "human_review_status": state.values.get("human_review_status"),
        "next_nodes": state.next,  # What would execute next
    }


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    # Visualize graph structure
    graph = create_cme_graph()
    print("Graph nodes:", graph.nodes.keys())
    print("\nGraph created successfully!")
    
    # In production, you would:
    # 1. Load intake data from form submission
    # 2. Call run_pipeline() with the data
    # 3. Monitor progress via get_pipeline_status()
    # 4. Handle human review via resume_pipeline()
