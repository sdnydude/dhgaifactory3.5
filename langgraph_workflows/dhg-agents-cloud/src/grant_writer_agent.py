"""
Grant Writer Agent - Agent #10
==============================
Assembles the complete CME grant package from all upstream agent outputs.

LangGraph Cloud Ready:
- Iteratively drafts each section of the grant
- Ensures consistency in voice, terminology, and data
- Produces a comprehensive YAML-structured grant package

Model: Claude Opus 4.5 (claude-opus-4-20250514)
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
    therapeutic_area: str
    target_audience: str
    
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
    complete_document_markdown: str
    
    # Metadata
    agent_version: str
    errors: List[str]
    model_used: str
    total_tokens: int
    total_cost: float


# =============================================================================
# LLM CLIENT - CLAUDE OPUS 4.5
# =============================================================================

class LLMClient:
    """Claude Opus 4.5 LLM client for grant writing."""
    
    def __init__(self):
        self.model = ChatAnthropic(
            model="claude-opus-4-20250514",
            max_tokens=8192
        )
        self.cost_per_1k_input = 0.015
        self.cost_per_1k_output = 0.075
    
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
- Placeholder text or TODO markers
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
    therapeutic_area = state.get("therapeutic_area", "")
    
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
    THERAPEUTIC AREA: {therapeutic_area}
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
        "total_cost": prev_cost + result["cost"],
        "model_used": "claude-opus-4-20250514"
    }


@traceable(name="draft_executive_summary_node", run_type="chain")
async def draft_executive_summary_node(state: GrantWriterState) -> dict:
    """Draft the executive summary."""
    
    needs = state.get("needs_assessment_output", {})
    curriculum = state.get("curriculum_design_output", {})
    marketing = state.get("marketing_plan_output", {})
    project_title = state.get("project_title", "")
    therapeutic_area = state.get("therapeutic_area", "")
    requested_amount = state.get("requested_amount", "")
    
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

    prompt = f"""Draft an executive summary for this CME grant proposal.
    
    PROJECT TITLE: {project_title}
    THERAPEUTIC AREA: {therapeutic_area}
    REQUESTED AMOUNT: {requested_amount}
    
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
    """Integrate the full Needs Assessment from upstream agent."""
    
    needs_output = state.get("needs_assessment_output", {})
    
    return {
        "needs_assessment_section": {
            "content": needs_output.get("full_narrative", json.dumps(needs_output, indent=2)),
            "sections_included": ["educational_need", "professional_practice_gaps", "educational_learning_objectives"],
            "word_count": len(needs_output.get("full_narrative", "").split())
        },
        "sections_completed": state.get("sections_completed", []) + ["needs_assessment"]
    }


@traceable(name="format_learning_objectives_node", run_type="chain")
async def format_learning_objectives_node(state: GrantWriterState) -> dict:
    """Format Learning Objectives section."""
    
    objectives = state.get("learning_objectives_output", {})
    
    objectives_list = objectives.get("objectives", [])
    formatted_objectives = "\n".join([
        f"- {obj.get('text', obj) if isinstance(obj, dict) else obj}"
        for obj in objectives_list
    ]) if objectives_list else json.dumps(objectives, indent=2)
    
    return {
        "learning_objectives_section": {
            "content": formatted_objectives,
            "objectives_count": len(objectives_list) if objectives_list else 0,
            "moore_level_summary": objectives.get("moore_level", "Competence and Performance")
        },
        "sections_completed": state.get("sections_completed", []) + ["learning_objectives"]
    }


@traceable(name="integrate_curriculum_node", run_type="chain")
async def integrate_curriculum_node(state: GrantWriterState) -> dict:
    """Integrate Curriculum Design."""
    
    curriculum = state.get("curriculum_design_output", {})
    
    return {
        "curriculum_section": {
            "content": curriculum.get("curriculum_narrative", json.dumps(curriculum, indent=2)),
            "innovation_section": curriculum.get("innovation_element", ""),
            "format_summary": curriculum.get("activity_format", ""),
            "duration": curriculum.get("duration", ""),
            "modules": curriculum.get("modules", [])
        },
        "sections_completed": state.get("sections_completed", []) + ["curriculum"]
    }


@traceable(name="create_faculty_section_node", run_type="chain")
async def create_faculty_section_node(state: GrantWriterState) -> dict:
    """Create Faculty and Planning Committee section using LLM."""
    
    therapeutic_area = state.get("therapeutic_area", "")
    curriculum = state.get("curriculum_design_output", {})
    org_info = state.get("organization_info", {})
    
    system = f"""{GRANT_WRITER_SYSTEM_PROMPT}

You are drafting the FACULTY AND PLANNING COMMITTEE section. Return a JSON object:
{{
    "content": "Full narrative text (200-300 words) describing faculty selection criteria and planning committee composition",
    "faculty_selection_criteria": ["criterion 1", "criterion 2"],
    "planning_committee_roles": ["role 1", "role 2"],
    "disclosure_statement": "Statement about COI identification and resolution"
}}"""

    prompt = f"""Draft the Faculty and Planning Committee section for a CME grant.

THERAPEUTIC AREA: {therapeutic_area}

CURRICULUM OVERVIEW:
{json.dumps(curriculum, indent=2)[:1500]}

ORGANIZATION INFO:
{json.dumps(org_info, indent=2)[:500]}

Requirements:
1. Describe criteria for selecting faculty with relevant expertise
2. Outline planning committee composition and roles
3. Include statement on conflict of interest identification and resolution
4. Reference ACCME requirements for independence"""

    result = await llm.generate(system, prompt, {"step": "faculty_section"})
    
    try:
        match = re.search(r'\{[\s\S]*\}', result["content"])
        data = json.loads(match.group()) if match else {"content": result["content"]}
    except:
        data = {"content": result["content"]}
        
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "faculty_section": data,
        "sections_completed": state.get("sections_completed", []) + ["faculty"],
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="integrate_outcomes_node", run_type="chain")
async def integrate_outcomes_node(state: GrantWriterState) -> dict:
    """Integrate Outcomes and Evaluation Plan from Research Protocol."""
    
    protocol = state.get("research_protocol_output", {})
    
    return {
        "outcomes_section": {
            "content": protocol.get("protocol_narrative", json.dumps(protocol, indent=2)),
            "primary_outcomes": protocol.get("primary_outcomes", ["Knowledge", "Competence", "Performance"]),
            "measurement_instruments": protocol.get("instruments", []),
            "timeline": protocol.get("timeline", "Pre, Post, 60-day Follow-up"),
            "sample_size": protocol.get("sample_size", "")
        },
        "sections_completed": state.get("sections_completed", []) + ["outcomes"]
    }


@traceable(name="integrate_marketing_node", run_type="chain")
async def integrate_marketing_node(state: GrantWriterState) -> dict:
    """Integrate Marketing and Audience Generation Plan."""
    
    marketing = state.get("marketing_plan_output", {})
    
    return {
        "marketing_section": {
            "content": marketing.get("narrative_plan", json.dumps(marketing, indent=2)),
            "target_audience": marketing.get("target_audience_definition", ""),
            "channels": marketing.get("channels", []),
            "projected_reach": str(marketing.get("total_reach_estimate", 0)),
            "timeline": marketing.get("timeline", "")
        },
        "sections_completed": state.get("sections_completed", []) + ["marketing"]
    }


@traceable(name="create_budget_section_node", run_type="chain")
async def create_budget_section_node(state: GrantWriterState) -> dict:
    """Create Budget section with LLM-generated justification."""
    
    budget_breakdown = state.get("budget_breakdown", {})
    total = state.get("requested_amount", "0")
    project_title = state.get("project_title", "")
    curriculum = state.get("curriculum_design_output", {})
    marketing = state.get("marketing_plan_output", {})
    
    system = f"""{GRANT_WRITER_SYSTEM_PROMPT}

You are drafting the BUDGET JUSTIFICATION section. Return a JSON object:
{{
    "content": "Full narrative budget justification (300-400 words)",
    "total_requested": "amount",
    "budget_categories": {{
        "category_name": {{"amount": "X", "justification": "text"}}
    }},
    "cost_effectiveness_statement": "Brief statement on value"
}}"""

    prompt = f"""Draft the Budget Justification section for a CME grant.

PROJECT TITLE: {project_title}
TOTAL REQUESTED: {total}

BUDGET BREAKDOWN PROVIDED:
{json.dumps(budget_breakdown, indent=2)}

CURRICULUM (for context):
{json.dumps(curriculum, indent=2)[:1000]}

MARKETING (for context):
{json.dumps(marketing, indent=2)[:500]}

Requirements:
1. Justify each budget category with educational rationale
2. Connect costs to educational outcomes
3. Demonstrate cost-effectiveness
4. Align with industry standards for CME activities"""

    result = await llm.generate(system, prompt, {"step": "budget_section"})
    
    try:
        match = re.search(r'\{[\s\S]*\}', result["content"])
        data = json.loads(match.group()) if match else {"content": result["content"], "total_requested": total, "budget_categories": budget_breakdown}
    except:
        data = {"content": result["content"], "total_requested": total, "budget_categories": budget_breakdown}
        
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "budget_section": data,
        "sections_completed": state.get("sections_completed", []) + ["budget"],
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="draft_org_qualifications_node", run_type="chain")
async def draft_org_qualifications_node(state: GrantWriterState) -> dict:
    """Draft Organizational Qualifications."""
    
    org_info = state.get("organization_info", {})
    therapeutic_area = state.get("therapeutic_area", "")
    
    system = f"""{GRANT_WRITER_SYSTEM_PROMPT}

You are drafting the ORGANIZATIONAL QUALIFICATIONS section. Return a JSON object:
{{
    "content": "Text describing org capabilities (200-300 words)",
    "accreditation_status": "Status",
    "experience": "Relevant experience summary",
    "track_record": "Prior educational outcomes"
}}"""

    prompt = f"""Describe the organization's qualifications for executing this CME program.
    
THERAPEUTIC AREA: {therapeutic_area}

ORG INFO:
{json.dumps(org_info, indent=2)}
    
Emphasize:
1. Accreditation status and compliance history
2. Experience in this therapeutic area
3. Track record of successful educational outcomes
4. Infrastructure and capabilities"""

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
    """Draft Independence and Compliance section using LLM."""
    
    accreditation_statement = state.get("accreditation_statement", "")
    supporter_company = state.get("supporter_company", "")
    org_info = state.get("organization_info", {})
    
    system = f"""{GRANT_WRITER_SYSTEM_PROMPT}

You are drafting the INDEPENDENCE AND COMPLIANCE section. Return a JSON object:
{{
    "content": "Full narrative (250-350 words) on independence from commercial interest",
    "accme_standards": "Statement of compliance with specific ACCME standards",
    "disclosure_policy": "COI disclosure and mitigation policy",
    "content_validation": "Process for ensuring fair balance",
    "separation_of_promotion": "Statement on separation from promotional activities"
}}"""

    prompt = f"""Draft the Independence and Compliance section for a CME grant.

COMMERCIAL SUPPORTER: {supporter_company}
ACCREDITATION STATEMENT: {accreditation_statement}

ORGANIZATION INFO:
{json.dumps(org_info, indent=2)[:500]}

Requirements (ACCME Standards for Integrity and Independence):
1. Provider maintains control over all content decisions
2. All relevant financial relationships identified and resolved
3. Content is fair, balanced, and free of commercial bias
4. Promotion separated from education
5. Disclosure provided to learners"""

    result = await llm.generate(system, prompt, {"step": "independence_section"})

    try:
        match = re.search(r'\{[\s\S]*\}', result["content"])
        data = json.loads(match.group()) if match else {"content": result["content"]}
    except:
        data = {"content": result["content"]}
        
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "independence_section": data,
        "sections_completed": state.get("sections_completed", []) + ["independence"],
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


def _extract_section_content(section: Dict[str, Any]) -> str:
    """Extract the main content from a section dictionary."""
    if isinstance(section, str):
        return section
    if isinstance(section, dict):
        return section.get("content", json.dumps(section, indent=2))
    return str(section)


@traceable(name="assemble_package_node", run_type="chain")
async def assemble_package_node(state: GrantWriterState) -> dict:
    """Assemble the final Grant Package Output with actual document generation."""
    
    project_title = state.get("project_title", "CME Grant Proposal")
    activity_title = state.get("activity_title", "")
    supporter_company = state.get("supporter_company", "")
    
    # Build the complete Markdown document
    sections = []
    
    # Title Page
    sections.append(f"# {project_title}")
    if activity_title:
        sections.append(f"## {activity_title}")
    sections.append(f"\n**Submitted to:** {supporter_company}")
    sections.append(f"**Date:** {datetime.now().strftime('%B %d, %Y')}")
    sections.append(f"**Requested Amount:** {state.get('requested_amount', 'TBD')}")
    sections.append("\n---\n")
    
    # Cover Letter
    sections.append("## Cover Letter")
    sections.append(_extract_section_content(state.get("cover_letter", {})))
    sections.append("\n---\n")
    
    # Executive Summary
    sections.append("## Executive Summary")
    sections.append(_extract_section_content(state.get("executive_summary", {})))
    sections.append("\n---\n")
    
    # Needs Assessment
    sections.append("## Needs Assessment")
    sections.append(_extract_section_content(state.get("needs_assessment_section", {})))
    sections.append("\n---\n")
    
    # Learning Objectives
    sections.append("## Learning Objectives")
    sections.append(_extract_section_content(state.get("learning_objectives_section", {})))
    sections.append("\n---\n")
    
    # Curriculum and Educational Design
    sections.append("## Curriculum and Educational Design")
    sections.append(_extract_section_content(state.get("curriculum_section", {})))
    sections.append("\n---\n")
    
    # Faculty and Planning Committee
    sections.append("## Faculty and Planning Committee")
    sections.append(_extract_section_content(state.get("faculty_section", {})))
    sections.append("\n---\n")
    
    # Outcomes and Evaluation
    sections.append("## Outcomes and Evaluation Plan")
    sections.append(_extract_section_content(state.get("outcomes_section", {})))
    sections.append("\n---\n")
    
    # Marketing and Audience Generation
    sections.append("## Marketing and Audience Generation")
    sections.append(_extract_section_content(state.get("marketing_section", {})))
    sections.append("\n---\n")
    
    # Budget
    sections.append("## Budget Justification")
    sections.append(_extract_section_content(state.get("budget_section", {})))
    sections.append("\n---\n")
    
    # Organizational Qualifications
    sections.append("## Organizational Qualifications")
    sections.append(_extract_section_content(state.get("org_qualifications_section", {})))
    sections.append("\n---\n")
    
    # Independence and Compliance
    sections.append("## Independence and Compliance Statement")
    sections.append(_extract_section_content(state.get("independence_section", {})))
    sections.append("\n---\n")
    
    # Appendices
    appendices = state.get("appendices", [])
    if appendices:
        sections.append("## Appendices")
        for i, appendix in enumerate(appendices, 1):
            sections.append(f"### Appendix {i}: {appendix.get('title', 'Untitled')}")
            sections.append(_extract_section_content(appendix))
    
    # Join all sections
    complete_document = "\n\n".join(sections)
    
    # Count words
    word_count = len(complete_document.split())
    
    # Estimate pages (approx 500 words per page)
    page_estimate = (word_count // 500) + 1
    
    package = {
        "metadata": {
            "agent_version": "2.1-opus",
            "execution_timestamp": datetime.now().isoformat(),
            "model_used": "claude-opus-4-20250514",
            "total_word_count": word_count,
            "total_pages_estimated": page_estimate,
            "sections_completed": state.get("sections_completed", []),
            "total_tokens_used": state.get("total_tokens", 0),
            "total_cost": state.get("total_cost", 0.0)
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
        "appendices": appendices
    }
    
    return {
        "grant_package_output": package,
        "complete_document_markdown": complete_document,
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
