"""
Grant Writer Agent - Agent #10
==============================
Assembles the complete CME grant package from all upstream agent outputs.

LangGraph Cloud Ready:
- Iteratively drafts each section of the grant
- Ensures consistency in voice, terminology, and data
- Produces a comprehensive YAML-structured grant package
"""

import os
import re
import json
import operator
import httpx
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langsmith import traceable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


# =============================================================================
# STATE DEFINITION
# =============================================================================

class GrantWriterState(TypedDict):
    # === INPUTS (from upstream agents & intake) ===
    project_title: str
    activity_title: str
    supporter_company: str
    supporter_contact: str
    requested_amount: str
    budget_breakdown: Dict[str, Any]
    organization_info: Dict[str, Any]
    accreditation_statement: str
    
    # Needs Assessment Agent Output
    needs_assessment_output: Dict[str, Any]
    
    # Learning Objectives Agent Output
    learning_objectives_output: Dict[str, Any]
    
    # Curriculum Design Agent Output
    curriculum_design_output: Dict[str, Any]
    
    # Research Protocol Agent Output
    research_protocol_output: Dict[str, Any]
    
    # Marketing Plan Agent Output
    marketing_plan_output: Dict[str, Any]
    
    # Gap Analysis Output (for reference)
    gap_analysis_output: Dict[str, Any]
    
    # Research Output (for reference)
    research_output: Dict[str, Any]
    
    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    current_section: str
    sections_completed: List[str]
    
    # === OUTPUTS (Draft Sections) ===
    cover_letter: Dict[str, Any]
    executive_summary: Dict[str, Any]
    needs_assessment_section: Dict[str, Any]
    learning_objectives_section: Dict[str, Any]
    curriculum_section: Dict[str, Any]
    faculty_section: Dict[str, Any]
    outcomes_section: Dict[str, Any]
    marketing_section: Dict[str, Any]
    budget_section: Dict[str, Any]
    org_qualifications_section: Dict[str, Any]
    independence_section: Dict[str, Any]
    appendices: List[Dict[str, Any]]
    
    # Final Output
    grant_package_output: Dict[str, Any]
    
    # Metadata
    agent_version: str
    errors: List[str]
    model_used: str
    total_tokens: int
    total_cost: float


# =============================================================================
# LLM CLIENT
# =============================================================================

class LLMClient:
    """Claude-based LLM client for grant writing."""
    
    def __init__(self):
        self.model = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            max_tokens=8192
        )
        self.cost_per_1k_input = 0.003
        self.cost_per_1k_output = 0.015
    
    @traceable(name="grant_writer_llm_call", run_type="llm")
    async def generate(self, system: str, prompt: str, metadata: dict = None) -> dict:
        """Generate response with cost tracking."""
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=prompt)
        ]
        
        response = await self.model.ainvoke(
            messages,
            config={"metadata": metadata or {}}
        )
        
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            input_tokens = response.usage_metadata.get("input_tokens", 0)
            output_tokens = response.usage_metadata.get("output_tokens", 0)
        
        cost = (input_tokens / 1000 * self.cost_per_1k_input) + (output_tokens / 1000 * self.cost_per_1k_output)
        
        return {
            "content": response.content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost
        }


llm = LLMClient()


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

GRANT_WRITER_SYSTEM_PROMPT = """You are a senior grant writer assembling a comprehensive CME grant package. Your goal is to integrate component sections into a cohesive, professional, and persuasive narrative.

PRINCIPLES:
1. INTEGRATE: Combine all sections into a cohesive narrative line.
2. CONSISTENCY: Ensure uniform voice, terminology, and style throughout.
3. COMPLETENESS: All required fields and sections must be present.
4. NARRATIVE THREAD: Maintain the 'cold open' character/patient thread where appropriate.
5. PROFESSIONALISM: Use authoritative, urgent, evidence-driven, but fair-balanced tone.

PROHIBITED:
- "Delve into", "It's important to note", "In conclusion"
- Promotional language about supporter products
- Inconsistencies or contradictions between sections
- Placeholder text
"""


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="draft_cover_letter_node", run_type="chain")
async def draft_cover_letter_node(state: GrantWriterState) -> dict:
    """Draft the cover letter."""
    
    project_title = state.get("project_title", "")
    supporter_company = state.get("supporter_company", "")
    supporter_contact = state.get("supporter_contact", "")
    amount = state.get("requested_amount", "")
    
    gap_summary = json.dumps(state.get("gap_analysis_output", {}).get("gap_summary", ""), indent=2)
    objectives = json.dumps(state.get("learning_objectives_output", {}), indent=2)
    
    system = f"""{GRANT_WRITER_SYSTEM_PROMPT}

You are drafting the COVER LETTER. Return a JSON object:
{{
    "recipient": "Name, Title, Company",
    "date": "Month Day, Year",
    "content": "Full text of letter (300-400 words)",
    "signatory": "Name, Title, Organization"
}}"""

    prompt = f"""Draft a cover letter for a CME grant proposal.
    
    PROJECT TITLE: {project_title}
    SUPPORTER: {supporter_company} (Contact: {supporter_contact})
    REQUESTED AMOUNT: {amount}
    
    GAP SUMMARY:
    {gap_summary}
    
    OBJECTIVES:
    {objectives}
    
    Focus on the unmet need and the value of this educational intervention."""

    result = await llm.generate(system, prompt, {"step": "cover_letter"})
    
    try:
        match = re.search(r'\{[\s\S]*\}', result["content"])
        data = json.loads(match.group()) if match else {"content": result["content"]}
    except:
        data = {"content": result["content"]}
        
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "cover_letter": data,
        "sections_completed": state.get("sections_completed", []) + ["cover_letter"],
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="draft_executive_summary_node", run_type="chain")
async def draft_executive_summary_node(state: GrantWriterState) -> dict:
    """Draft the executive summary."""
    
    needs = state.get("needs_assessment_output", {})
    curriculum = state.get("curriculum_design_output", {})
    marketing = state.get("marketing_plan_output", {})
    
    system = f"""{GRANT_WRITER_SYSTEM_PROMPT}

You are drafting the EXECUTIVE SUMMARY. Return a JSON object:
{{
    "content": "Full text (500-600 words)",
    "key_points": [
        {{"unmet_need": "text"}},
        {{"proposed_solution": "text"}},
        {{"expected_impact": "text"}},
        {{"investment_requested": "text"}}
    ]
}}"""

    prompt = f"""Draft an executive summary.
    
    NEEDS ASSESSMENT HIGHLIGHTS:
    {json.dumps(needs, indent=2)[:2000]}
    
    PROPOSED SOLUTION (Curriculum):
    {json.dumps(curriculum, indent=2)[:1000]}
    
    REACH (Marketing):
    {json.dumps(marketing, indent=2)[:500]}
    
    Make a compelling case for support."""

    result = await llm.generate(system, prompt, {"step": "executive_summary"})
    
    try:
        match = re.search(r'\{[\s\S]*\}', result["content"])
        data = json.loads(match.group()) if match else {"content": result["content"]}
    except:
        data = {"content": result["content"]}
        
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "executive_summary": data,
        "sections_completed": state.get("sections_completed", []) + ["executive_summary"],
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="integrate_needs_assessment_node", run_type="chain")
async def integrate_needs_assessment_node(state: GrantWriterState) -> dict:
    """Integrate the full Needs Assessment."""
    
    # Primarily a pass-through of the upstream agent's output, potentially with formatting
    needs_output = state.get("needs_assessment_output", {})
    
    # In a real scenario, LLM might check consistency or format it
    
    return {
        "needs_assessment_section": {
            "content": needs_output.get("full_narrative", ""),
            "sections_included": ["educational_need", "professional_practice_gaps", "educational_learning_objectives"]
        },
        "sections_completed": state.get("sections_completed", []) + ["needs_assessment"]
    }


@traceable(name="format_learning_objectives_node", run_type="chain")
async def format_learning_objectives_node(state: GrantWriterState) -> dict:
    """Format Learning Objectives section."""
    
    objectives = state.get("learning_objectives_output", {})
    
    return {
        "learning_objectives_section": {
            "content": json.dumps(objectives, indent=2), # Placeholder formatting
            "objectives_count": len(objectives.get("objectives", [])),
            "moore_level_summary": "Competence and Performance" 
        },
        "sections_completed": state.get("sections_completed", []) + ["learning_objectives"]
    }


@traceable(name="integrate_curriculum_node", run_type="chain")
async def integrate_curriculum_node(state: GrantWriterState) -> dict:
    """Integrate Curriculum Design."""
    
    curriculum = state.get("curriculum_design_output", {})
    
    return {
        "curriculum_section": {
            "content": json.dumps(curriculum, indent=2),
            "innovation_section": curriculum.get("innovation_element", ""),
            "format_summary": curriculum.get("activity_format", "")
        },
        "sections_completed": state.get("sections_completed", []) + ["curriculum"]
    }


@traceable(name="create_faculty_section_node", run_type="chain")
async def create_faculty_section_node(state: GrantWriterState) -> dict:
    """Create Faculty and Planning Committee section."""
    
    # This might require generation if not fully provided upstream, 
    # but often is derived from curriculum or intake.
    
    # Placeholder implementation
    return {
        "faculty_section": {
            "content": "Proposed Faculty and Planning Committee...",
            "faculty_list": [],
            "disclosure_statement": "All relevant financial relationships will be disclosed..."
        },
        "sections_completed": state.get("sections_completed", []) + ["faculty"]
    }


@traceable(name="integrate_outcomes_node", run_type="chain")
async def integrate_outcomes_node(state: GrantWriterState) -> dict:
    """Integrate Outcomes and Evaluation Plan."""
    
    protocol = state.get("research_protocol_output", {})
    
    return {
        "outcomes_section": {
            "content": protocol.get("protocol_narrative", ""),
            "primary_outcomes": "Knowledge, Competence, Performance",
            "timeline": "Pre, Post, 60-day Follow-up"
        },
        "sections_completed": state.get("sections_completed", []) + ["outcomes"]
    }


@traceable(name="integrate_marketing_node", run_type="chain")
async def integrate_marketing_node(state: GrantWriterState) -> dict:
    """Integrate Marketing and Audience Generation Plan."""
    
    marketing = state.get("marketing_plan_output", {})
    
    return {
        "marketing_section": {
            "content": marketing.get("narrative_plan", ""),
            "target_audience": marketing.get("target_audience_definition", ""),
            "projected_reach": str(marketing.get("total_reach_estimate", 0))
        },
        "sections_completed": state.get("sections_completed", []) + ["marketing"]
    }


@traceable(name="create_budget_section_node", run_type="chain")
async def create_budget_section_node(state: GrantWriterState) -> dict:
    """Create Budget section."""
    
    budget_breakdown = state.get("budget_breakdown", {})
    total = state.get("requested_amount", "0")
    
    # In a full impl, LLM might justify costs or format a table
    
    return {
        "budget_section": {
            "content": "Detailed Budget Explanation...",
            "total_requested": total,
            "budget_categories": budget_breakdown
        },
        "sections_completed": state.get("sections_completed", []) + ["budget"]
    }


@traceable(name="draft_org_qualifications_node", run_type="chain")
async def draft_org_qualifications_node(state: GrantWriterState) -> dict:
    """Draft Organizational Qualifications."""
    
    org_info = state.get("organization_info", {})
    
    system = f"""{GRANT_WRITER_SYSTEM_PROMPT}

You are drafting the ORGANIZATIONAL QUALIFICATIONS section. Return a JSON object:
{{
    "content": "Text describing org capabilities",
    "accreditation_status": "Status",
    "experience": "Relevant experience summary"
}}"""

    prompt = f"""Describe the organization's qualifications.
    
    ORG INFO:
    {json.dumps(org_info, indent=2)}
    
    Emphasize experience in this therapeutic area and accreditation status."""

    result = await llm.generate(system, prompt, {"step": "org_qualifications"})

    try:
        match = re.search(r'\{[\s\S]*\}', result["content"])
        data = json.loads(match.group()) if match else {"content": result["content"]}
    except:
        data = {"content": result["content"]}
        
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "org_qualifications_section": data,
        "sections_completed": state.get("sections_completed", []) + ["org_qualifications"],
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="draft_independence_node", run_type="chain")
async def draft_independence_node(state: GrantWriterState) -> dict:
    """Draft Independence and Compliance section."""
    
    statement = state.get("accreditation_statement", "")
    
    return {
        "independence_section": {
            "content": "Statement on independence from commercial interest...",
            "accme_standards": "Fully compliant with ACCME Standards for Integrity and Independence",
            "disclosure_policy": "All relevant financial relationships will be mitigated..."
        },
        "sections_completed": state.get("sections_completed", []) + ["independence"]
    }


@traceable(name="assemble_package_node", run_type="chain")
async def assemble_package_node(state: GrantWriterState) -> dict:
    """Assemble the final Grant Package Output."""
    
    package = {
        "metadata": {
            "agent_version": "2.0",
            "execution_timestamp": datetime.now().isoformat(),
            # Placeholder counts
            "total_word_count": 0,
            "total_pages_estimated": 0
        },
        "cover_letter": state.get("cover_letter"),
        "executive_summary": state.get("executive_summary"),
        "needs_assessment": state.get("needs_assessment_section"),
        "learning_objectives": state.get("learning_objectives_section"),
        "curriculum_and_educational_design": state.get("curriculum_section"),
        "faculty_and_planning_committee": state.get("faculty_section"),
        "outcomes_and_evaluation": state.get("outcomes_section"),
        "marketing_and_audience": state.get("marketing_section"),
        "budget": state.get("budget_section"),
        "organizational_qualifications": state.get("org_qualifications_section"),
        "independence_and_compliance": state.get("independence_section"),
        "appendices": [],
        # In a real system, we'd join all contents into a single markdown string here
        "complete_document": "Full compiled document text..."
    }
    
    return {
        "grant_package_output": package,
        "sections_completed": state.get("sections_completed", []) + ["package_assembly"]
    }


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def create_grant_writer_graph():
    """Create the Grant Writer graph."""
    
    workflow = StateGraph(GrantWriterState)
    
    # Add nodes
    workflow.add_node("draft_cover_letter", draft_cover_letter_node)
    workflow.add_node("draft_executive_summary", draft_executive_summary_node)
    workflow.add_node("integrate_needs", integrate_needs_assessment_node)
    workflow.add_node("format_objectives", format_learning_objectives_node)
    workflow.add_node("integrate_curriculum", integrate_curriculum_node)
    workflow.add_node("create_faculty", create_faculty_section_node)
    workflow.add_node("integrate_outcomes", integrate_outcomes_node)
    workflow.add_node("integrate_marketing", integrate_marketing_node)
    workflow.add_node("create_budget", create_budget_section_node)
    workflow.add_node("draft_org_qualifications", draft_org_qualifications_node)
    workflow.add_node("draft_independence", draft_independence_node)
    workflow.add_node("assemble_package", assemble_package_node)
    
    # Define limits - sequential flow
    workflow.set_entry_point("draft_cover_letter")
    
    workflow.add_edge("draft_cover_letter", "draft_executive_summary")
    workflow.add_edge("draft_executive_summary", "integrate_needs")
    workflow.add_edge("integrate_needs", "format_objectives")
    workflow.add_edge("format_objectives", "integrate_curriculum")
    workflow.add_edge("integrate_curriculum", "create_faculty")
    workflow.add_edge("create_faculty", "integrate_outcomes")
    workflow.add_edge("integrate_outcomes", "integrate_marketing")
    workflow.add_edge("integrate_marketing", "create_budget")
    workflow.add_edge("create_budget", "draft_org_qualifications")
    workflow.add_edge("draft_org_qualifications", "draft_independence")
    workflow.add_edge("draft_independence", "assemble_package")
    workflow.add_edge("assemble_package", END)
    
    return workflow.compile()


# Compile for LangGraph Cloud
graph = create_grant_writer_graph()


if __name__ == "__main__":
    graph = create_grant_writer_graph()
    
    # Generate visualization
    print("=== MERMAID DIAGRAM ===")
    print(graph.get_graph().draw_mermaid())
