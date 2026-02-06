"""
Curriculum Design Agent - Agent #7
===================================
Creates educational design including format selection, content structure,
faculty specifications, instructional methods, and innovation rationale.

LangGraph Cloud Ready:
- Produces complete curriculum specification
- Input from: Learning Objectives Agent, Gap Analysis Agent
- Output to: Grant Writer Agent
"""

import os
import re
import json
import operator
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional, Annotated

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langsmith import traceable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


# =============================================================================
# CONFIGURATION
# =============================================================================

# Instructional methods by Moore level
METHODS_BY_LEVEL = {
    "level_5": [
        "case-based decision-making", "commitment-to-change", 
        "action planning", "practice simulation"
    ],
    "level_4": [
        "case analysis", "clinical reasoning exercises",
        "skills practice", "OSCE-style scenarios"
    ],
    "level_3b": [
        "skills demonstration", "guided practice",
        "technique videos", "hands-on workshops"
    ],
    "level_3a": [
        "brief didactic", "pre-work", "reference materials"
    ]
}

# Innovation categories
INNOVATION_CATEGORIES = {
    "pedagogical": [
        "Flipped classroom", "Spaced learning", "Deliberate practice",
        "Reflective practice", "Team-based learning"
    ],
    "content": [
        "Patient voice integration", "De-identified real-world data",
        "Guideline evolution comparison", "Cross-specialty perspective"
    ],
    "technology": [
        "Audience response systems", "Virtual patient simulations",
        "AI-powered scenarios", "Decision support integration"
    ],
    "assessment": [
        "Real-time competence verification", "Adaptive questioning",
        "Practice commitment contracts", "Peer comparison benchmarking"
    ]
}


# =============================================================================
# STATE DEFINITION
# =============================================================================

class CurriculumDesignState(TypedDict):
    # === INPUT (from upstream agents) ===
    learning_objectives_report: Dict[str, Any]
    gap_analysis_report: Dict[str, Any]
    needs_assessment_document: Optional[str]
    
    # From intake form
    target_audience: str
    practice_settings: Optional[List[str]]
    educational_format: Optional[str]
    innovation_elements: Optional[List[str]]
    faculty_requirements: Optional[str]
    duration_minutes: Optional[int]
    modality: Optional[str]
    therapeutic_area: str
    disease_state: str
    
    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    
    # Section-specific data
    format_spec: Dict[str, Any]
    content_outline: Dict[str, Any]
    instructional_methods: List[Dict[str, Any]]
    case_design: Dict[str, Any]
    faculty_spec: Dict[str, Any]
    innovation_section: Dict[str, Any]
    assessment_strategy: Dict[str, Any]
    implementation_requirements: Dict[str, Any]
    
    # === OUTPUT ===
    curriculum_report: Dict[str, Any]
    curriculum_document: str
    
    # === METADATA ===
    total_duration_minutes: int
    active_learning_percentage: float
    errors: List[str]
    model_used: str
    total_tokens: int
    total_cost: float


# =============================================================================
# LLM CLIENT
# =============================================================================

class LLMClient:
    """Claude-based LLM client with cost tracking."""
    
    def __init__(self):
        self.model = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            max_tokens=8192
        )
        self.cost_per_1k_input = 0.003
        self.cost_per_1k_output = 0.015
    
    @traceable(name="curriculum_design_llm_call", run_type="llm")
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
        
        cost = (input_tokens / 1000 * self.cost_per_1k_input) + \
               (output_tokens / 1000 * self.cost_per_1k_output)
        
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

CURRICULUM_SYSTEM_PROMPT = """You are an instructional designer creating curriculum for continuing medical education. Your design must:

1. OBJECTIVE-ALIGNED: Every content element must trace to a learning objective
2. ADULT LEARNING: Apply adult learning principles (relevance, experience, problem-centered)
3. EVIDENCE-BASED: Use instructional methods with demonstrated efficacy
4. INNOVATIVE: Include genuine innovations that differentiate from standard approaches
5. PRACTICAL: Design must be implementable within stated constraints

CURRICULUM DESIGN PRINCIPLES:
- Active learning should exceed passive lecture by ratio of at least 40:60
- Cases should be central, not supplementary
- Real-world relevance must be explicit
- Assessment should be embedded, not bolted on
- Time allocations must be realistic

PROHIBITED PATTERNS:
- "Lecture followed by Q&A" as primary method
- Cases as afterthought rather than core
- Innovation claims without substance
- Assessment only at end of activity
- Ignoring identified barriers in design"""


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="design_format_node", run_type="chain")
async def design_format_node(state: CurriculumDesignState) -> dict:
    """Design the format and session structure."""
    
    objectives = state.get("learning_objectives_report", {}).get("objectives", [])
    duration = state.get("duration_minutes", 180)
    modality = state.get("modality", "Hybrid")
    format_pref = state.get("educational_format", "Live symposium")
    audience = state.get("target_audience", "")
    therapeutic_area = state.get("therapeutic_area", "")
    disease = state.get("disease_state", "")
    
    system = f"""{CURRICULUM_SYSTEM_PROMPT}

You are designing the FORMAT SPECIFICATION. Return a JSON object:
{{
    "primary_format": "e.g., Live symposium with case workshops",
    "modality": "In-person|Virtual|Hybrid",
    "duration": "{duration} minutes",
    "session_structure": [
        {{
            "segment": "Segment name",
            "duration": 10,
            "type": "interactive|didactic|case|assessment|break",
            "description": "What happens"
        }}
    ],
    "rationale": "Why this format serves the objectives and audience",
    "active_learning_time": 0,
    "passive_learning_time": 0
}}

Ensure active learning is at least 40% of total time."""
    
    # Count objectives by level
    level_counts = {"level_5": 0, "level_4": 0, "level_3": 0}
    for obj in objectives:
        level = obj.get("moore_classification", {}).get("level", "").lower()
        if "5" in level:
            level_counts["level_5"] += 1
        elif "4" in level:
            level_counts["level_4"] += 1
        else:
            level_counts["level_3"] += 1
    
    prompt = f"""Design the educational format for a {duration}-minute {modality} CME activity.

CLINICAL FOCUS:
- Therapeutic Area: {therapeutic_area}
- Disease State: {disease}
- Target Audience: {audience}

Format preference: {format_pref}

OBJECTIVE LEVEL DISTRIBUTION:
- Level 5 (Performance): {level_counts['level_5']} objectives
- Level 4 (Competence): {level_counts['level_4']} objectives
- Level 3 (Knowledge): {level_counts['level_3']} objectives

Design a session structure that:
1. Is specifically tailored to {disease} education
2. Addresses Level 5/4 objectives with active methods (cases, practice)
3. Minimizes pure lecture time
4. Includes embedded assessment relevant to {therapeutic_area}
5. Has realistic time allocations

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "format_design"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            format_spec = json.loads(json_match.group())
        else:
            format_spec = {"error": "Failed to parse format"}
    except json.JSONDecodeError:
        format_spec = {"error": "Invalid JSON in format"}
    
    # Calculate active learning percentage
    active_time = format_spec.get("active_learning_time", 0)
    total_time = duration
    active_pct = (active_time / total_time * 100) if total_time > 0 else 0
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "format_spec": format_spec,
        "total_duration_minutes": duration,
        "active_learning_percentage": active_pct,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="design_content_outline_node", run_type="chain")
async def design_content_outline_node(state: CurriculumDesignState) -> dict:
    """Design content modules aligned to objectives."""
    
    objectives = state.get("learning_objectives_report", {}).get("objectives", [])
    format_spec = state.get("format_spec", {})
    disease = state.get("disease_state", "")
    
    system = f"""{CURRICULUM_SYSTEM_PROMPT}

You are designing the CONTENT OUTLINE. Return a JSON object:
{{
    "modules": [
        {{
            "module_id": "MOD-01",
            "title": "Module title",
            "duration_minutes": 30,
            "objectives_addressed": ["OBJ-001", "OBJ-002"],
            "content_elements": [
                {{
                    "element_type": "didactic|case|interactive|practice|assessment",
                    "description": "What this element covers",
                    "duration_minutes": 10,
                    "learning_method": "Specific method used"
                }}
            ],
            "faculty_role": "What faculty does in this module",
            "assessment_embedded": "How learning is checked"
        }}
    ]
}}

Every objective must be addressed by at least one module."""
    
    prompt = f"""Design content modules for {disease} CME.

SESSION STRUCTURE:
{json.dumps(format_spec.get('session_structure', []), indent=2)}

LEARNING OBJECTIVES TO ADDRESS:
{json.dumps([{"id": o.get("objective_id"), "text": o.get("objective_text", "")[:200], "level": o.get("moore_classification", {}).get("level")} for o in objectives], indent=2)}

Create modules that:
1. Map to the session structure segments
2. Address all objectives
3. Use appropriate methods for each objective's Moore level
4. Include embedded assessment

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "content_outline"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            content_outline = json.loads(json_match.group())
        else:
            content_outline = {"modules": []}
    except json.JSONDecodeError:
        content_outline = {"modules": []}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "content_outline": content_outline,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="design_cases_node", run_type="chain")
async def design_cases_node(state: CurriculumDesignState) -> dict:
    """Design case scenarios for the activity."""
    
    gaps = state.get("gap_analysis_report", {}).get("gaps", [])
    objectives = state.get("learning_objectives_report", {}).get("objectives", [])
    disease = state.get("disease_state", "")
    audience = state.get("target_audience", "")
    
    system = f"""{CURRICULUM_SYSTEM_PROMPT}

You are designing CASE SCENARIOS. Cases should be central, not supplementary. Return a JSON object:
{{
    "case_count": 2,
    "case_structure": [
        {{
            "case_id": "CASE-01",
            "scenario_type": "recognition|management|complex decision",
            "clinical_presentation": "Brief patient description",
            "decision_points": [
                "Decision 1: What to do about X",
                "Decision 2: How to handle Y"
            ],
            "teaching_points": [
                "Key learning point 1",
                "Key learning point 2"
            ],
            "barriers_addressed": ["Time constraint", "Competing priorities"],
            "objectives_supported": ["OBJ-001", "OBJ-002"]
        }}
    ],
    "case_progression_rationale": "Why cases are structured this way"
}}

Cases must incorporate real-world barriers (not idealized scenarios)."""
    
    # Get barriers from gaps
    barriers = []
    for gap in gaps:
        barrier_type = gap.get("root_causes", {}).get("primary_barrier_type", "")
        factors = gap.get("root_causes", {}).get("contributing_factors", [])
        barriers.extend(factors)
    barriers = list(set(barriers))[:8]  # Unique, limit to 8
    
    prompt = f"""Design case scenarios for {disease} CME targeting {audience}.

GAPS TO ADDRESS:
{json.dumps([{"id": g.get("gap_id"), "title": g.get("title")} for g in gaps[:5]], indent=2)}

BARRIERS TO INCORPORATE (make cases realistic):
{json.dumps(barriers, indent=2)}

OBJECTIVES TO SUPPORT:
{json.dumps([{"id": o.get("objective_id"), "level": o.get("moore_classification", {}).get("level")} for o in objectives], indent=2)}

Design 2-3 cases that:
1. Progress from simpler to more complex
2. Include real-world constraints (time, system barriers)
3. Have clear decision points for discussion
4. Connect to identified gaps

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "case_design"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            case_design = json.loads(json_match.group())
        else:
            case_design = {"case_count": 0, "case_structure": []}
    except json.JSONDecodeError:
        case_design = {"case_count": 0, "case_structure": []}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "case_design": case_design,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="specify_faculty_node", run_type="chain")
async def specify_faculty_node(state: CurriculumDesignState) -> dict:
    """Specify faculty requirements."""
    
    content_outline = state.get("content_outline", {})
    disease = state.get("disease_state", "")
    audience = state.get("target_audience", "")
    
    system = f"""{CURRICULUM_SYSTEM_PROMPT}

You are specifying FACULTY REQUIREMENTS. Return a JSON object:
{{
    "lead_faculty": {{
        "expertise_required": ["Area 1", "Area 2"],
        "credentials": "MD, Board Certification, etc.",
        "role": "What lead faculty does"
    }},
    "supporting_faculty": [
        {{
            "role": "Specific role",
            "expertise_required": ["Area"],
            "credentials": "Required credentials"
        }}
    ],
    "faculty_development_needs": "What faculty need to be briefed on"
}}"""
    
    prompt = f"""Specify faculty requirements for {disease} CME targeting {audience}.

CONTENT MODULES:
{json.dumps(content_outline.get('modules', [])[:3], indent=2)[:2000]}

Specify faculty who can:
1. Deliver expert content authentically
2. Facilitate case discussions
3. Handle audience questions
4. Model clinical reasoning

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "faculty_spec"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            faculty_spec = json.loads(json_match.group())
        else:
            faculty_spec = {}
    except json.JSONDecodeError:
        faculty_spec = {}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "faculty_spec": faculty_spec,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="write_innovation_section_node", run_type="chain")
async def write_innovation_section_node(state: CurriculumDesignState) -> dict:
    """Write the innovation section (500+ words)."""
    
    gaps = state.get("gap_analysis_report", {}).get("gaps", [])
    case_design = state.get("case_design", {})
    format_spec = state.get("format_spec", {})
    disease = state.get("disease_state", "")
    innovation_reqs = state.get("innovation_elements", [])
    
    system = f"""{CURRICULUM_SYSTEM_PROMPT}

You are writing the INNOVATION SECTION. This must be 500+ words and substantive.

Return a JSON object:
{{
    "innovation_summary": "500+ word narrative describing innovations...",
    "innovations": [
        {{
            "innovation_name": "Name of innovation",
            "description": "What it is",
            "educational_rationale": "Why it improves learning",
            "evidence_supporting": "Research/theory supporting this",
            "implementation_approach": "How it will be implemented"
        }}
    ],
    "differentiation_from_existing": "How this differs from standard CME",
    "technology_integration": "Technology used"
}}

INNOVATION CATEGORIES TO DRAW FROM:
- Pedagogical: Flipped classroom, spaced learning, deliberate practice
- Content: Patient voice, real-world data, cross-specialty perspectives
- Technology: Audience response, simulations, AI scenarios
- Assessment: Real-time verification, adaptive questioning, commitment contracts"""
    
    # Get barriers for innovation alignment
    barriers = []
    for gap in gaps:
        factors = gap.get("root_causes", {}).get("contributing_factors", [])
        barriers.extend(factors)
    
    prompt = f"""Write a 500+ word innovation section for {disease} CME.

BARRIERS THAT INNOVATIONS SHOULD ADDRESS:
{json.dumps(barriers[:5], indent=2)}

CASE DESIGN ELEMENTS:
{json.dumps(case_design, indent=2)[:1500]}

FORMAT:
{json.dumps(format_spec.get('session_structure', [])[:3], indent=2)[:1000]}

{f"REQUIRED INNOVATIONS: {', '.join(innovation_reqs)}" if innovation_reqs else ""}

Write a substantive innovation section that:
1. Describes 3-5 genuine innovations (not generic features)
2. Explains how each addresses identified barriers
3. Cites educational theory/evidence
4. Differentiates from standard CME lecture + Q&A

The innovation_summary should be at least 500 words of flowing prose.

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "innovation_section"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            innovation_section = json.loads(json_match.group())
        else:
            innovation_section = {}
    except json.JSONDecodeError:
        innovation_section = {}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "innovation_section": innovation_section,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="design_assessment_strategy_node", run_type="chain")
async def design_assessment_strategy_node(state: CurriculumDesignState) -> dict:
    """Design the assessment strategy."""
    
    objectives = state.get("learning_objectives_report", {}).get("objectives", [])
    therapeutic_area = state.get("therapeutic_area", "")
    disease = state.get("disease_state", "")
    
    system = f"""{CURRICULUM_SYSTEM_PROMPT}

You are designing the ASSESSMENT STRATEGY. Return a JSON object:
{{
    "formative": [
        {{
            "method": "Assessment method",
            "timing": "When during activity",
            "purpose": "What it measures"
        }}
    ],
    "summative": [
        {{
            "method": "Assessment method",
            "timing": "End of activity",
            "criteria": "Success criteria"
        }}
    ],
    "practice_change_measurement": {{
        "method": "How practice change will be measured",
        "timing": "30-60-90 day follow-up",
        "follow_up_mechanism": "Email survey, etc."
    }}
}}"""
    
    # Get measurement from objectives
    measurements = [
        {
            "id": o.get("objective_id"),
            "method": o.get("measurement", {}).get("primary_method"),
            "timing": o.get("measurement", {}).get("timing")
        }
        for o in objectives
    ]
    
    prompt = f"""Design assessment strategy for {disease} CME activity in {therapeutic_area}.

OBJECTIVE MEASUREMENT PLANS:
{json.dumps(measurements, indent=2)}

Design assessments that:
1. Are specific to {disease} clinical practice
2. Are embedded throughout (not just at end)
3. Align with Moore levels (cases for Level 4-5, knowledge checks for Level 3)
4. Include practice change follow-up relevant to {therapeutic_area}
5. Have realistic implementation

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "assessment_strategy"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            assessment = json.loads(json_match.group())
        else:
            assessment = {}
    except json.JSONDecodeError:
        assessment = {}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "assessment_strategy": assessment,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="document_implementation_node", run_type="chain")
async def document_implementation_node(state: CurriculumDesignState) -> dict:
    """Document implementation requirements."""
    
    format_spec = state.get("format_spec", {})
    modality = state.get("modality", "Hybrid")
    innovation_section = state.get("innovation_section", {})
    
    # Extract technology from innovations
    tech_innovations = [
        i.get("innovation_name")
        for i in innovation_section.get("innovations", [])
        if "tech" in i.get("innovation_name", "").lower() or 
           "virtual" in i.get("description", "").lower() or
           "audience response" in i.get("description", "").lower()
    ]
    
    implementation = {
        "technology_needs": [
            "Presentation system with audience response capability",
            "Video playback for patient narratives",
            "Case display system for small groups"
        ],
        "materials_required": [
            "Case workbooks for participants",
            "Quick reference guides",
            "Commitment-to-change worksheets"
        ],
        "venue_requirements": f"Room setup for {modality} delivery with breakout capability",
        "staffing_needs": "Moderator, AV technician, CME coordinator"
    }
    
    if tech_innovations:
        implementation["technology_needs"].extend(tech_innovations)
    
    return {
        "implementation_requirements": implementation,
        "total_tokens": state.get("total_tokens", 0),
        "total_cost": state.get("total_cost", 0.0)
    }


@traceable(name="assemble_curriculum_report_node", run_type="chain")
async def assemble_curriculum_report_node(state: CurriculumDesignState) -> dict:
    """Assemble the final curriculum report."""
    
    innovation = state.get("innovation_section", {})
    
    report = {
        "metadata": {
            "agent_version": "2.0",
            "execution_timestamp": datetime.now().isoformat(),
            "total_duration_minutes": state.get("total_duration_minutes", 0),
            "format_type": state.get("format_spec", {}).get("primary_format", ""),
            "active_learning_percentage": state.get("active_learning_percentage", 0),
            "model_used": "claude-sonnet-4",
            "total_tokens": state.get("total_tokens", 0),
            "total_cost": state.get("total_cost", 0.0)
        },
        "executive_summary": {
            "educational_approach": f"Interactive {state.get('format_spec', {}).get('modality', 'hybrid')} activity with case-based learning",
            "key_innovations": [i.get("innovation_name") for i in innovation.get("innovations", [])[:3]],
            "expected_impact": "Practice change in targeted clinical behaviors"
        },
        "format_specification": state.get("format_spec", {}),
        "content_outline": state.get("content_outline", {}),
        "case_design": state.get("case_design", {}),
        "instructional_methods": state.get("instructional_methods", []),
        "faculty_specifications": state.get("faculty_spec", {}),
        "innovation_section": innovation,
        "assessment_strategy": state.get("assessment_strategy", {}),
        "implementation_requirements": state.get("implementation_requirements", {})
    }
    
    return {
        "curriculum_report": report,
        "messages": [HumanMessage(content=f"Curriculum design complete: {state.get('total_duration_minutes', 0)} min activity with {len(innovation.get('innovations', []))} innovations")]
    }


@traceable(name="render_curriculum_document_node", run_type="chain")
async def render_curriculum_document_node(state: CurriculumDesignState) -> dict:
    """Render the curriculum as a readable document."""
    
    disease = state.get("disease_state", "")
    report = state.get("curriculum_report", {})
    
    system = """You are a medical education writer creating a curriculum specification document.

FORMATTING RULES:
- Use markdown headers
- Present session structure as a clear timeline
- Include the full innovation section (500+ words)
- Show faculty requirements
- Document implementation needs

STRUCTURE:
1. Executive Summary
2. Format and Session Structure
3. Content Outline by Module
4. Case Scenarios
5. Faculty Requirements
6. Innovation Section (full prose)
7. Assessment Strategy
8. Implementation Requirements

Do NOT use:
- Em dashes (—)
- Generic descriptions
"""
    
    prompt = f"""Create a curriculum specification document for {disease} CME.

CURRICULUM DATA:
{json.dumps(report, indent=2)[:15000]}

Present as a production-ready specification document."""

    result = await llm.generate(system, prompt, {"step": "render_document"})
    
    document = result["content"]
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "curriculum_document": document,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


# =============================================================================
# BUILD GRAPH
# =============================================================================

def create_curriculum_design_graph() -> StateGraph:
    """Create the Curriculum Design Agent graph."""
    
    graph = StateGraph(CurriculumDesignState)
    
    # Add nodes
    graph.add_node("design_format", design_format_node)
    graph.add_node("design_content", design_content_outline_node)
    graph.add_node("design_cases", design_cases_node)
    graph.add_node("specify_faculty", specify_faculty_node)
    graph.add_node("write_innovation", write_innovation_section_node)
    graph.add_node("design_assessment", design_assessment_strategy_node)
    graph.add_node("document_implementation", document_implementation_node)
    graph.add_node("assemble_report", assemble_curriculum_report_node)
    graph.add_node("render_document", render_curriculum_document_node)
    
    # Flow: sequential design process
    graph.set_entry_point("design_format")
    
    graph.add_edge("design_format", "design_content")
    graph.add_edge("design_content", "design_cases")
    graph.add_edge("design_cases", "specify_faculty")
    graph.add_edge("specify_faculty", "write_innovation")
    graph.add_edge("write_innovation", "design_assessment")
    graph.add_edge("design_assessment", "document_implementation")
    graph.add_edge("document_implementation", "assemble_report")
    graph.add_edge("assemble_report", "render_document")
    graph.add_edge("render_document", END)
    
    return graph


# Compile for LangGraph Cloud
graph = create_curriculum_design_graph().compile()


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        # Mock upstream data
        mock_objectives = {
            "objectives": [
                {
                    "objective_id": "OBJ-001",
                    "objective_text": "Initiate SGLT2 inhibitor therapy...",
                    "moore_classification": {"level": "Level 5"},
                    "measurement": {"primary_method": "Commitment-to-change", "timing": "60 days"}
                },
                {
                    "objective_id": "OBJ-002",
                    "objective_text": "Differentiate HFrEF and HFpEF...",
                    "moore_classification": {"level": "Level 4"},
                    "measurement": {"primary_method": "Case assessment", "timing": "Post-activity"}
                }
            ]
        }
        
        mock_gaps = {
            "gaps": [
                {
                    "gap_id": "GAP-001",
                    "title": "SGLT2i Initiation Gap",
                    "root_causes": {
                        "primary_barrier_type": "knowledge",
                        "contributing_factors": ["Unaware of indication", "Concern about side effects"]
                    }
                }
            ]
        }
        
        test_state = {
            "learning_objectives_report": mock_objectives,
            "gap_analysis_report": mock_gaps,
            "therapeutic_area": "cardiology",
            "disease_state": "heart failure",
            "target_audience": "cardiologists",
            "educational_format": "Live symposium",
            "duration_minutes": 180,
            "modality": "Hybrid",
            "messages": [],
            "errors": [],
            "total_tokens": 0,
            "total_cost": 0.0
        }
        
        result = await graph.ainvoke(test_state)
        
        print(f"\n=== CURRICULUM DESIGN RESULT ===")
        print(f"Duration: {result.get('total_duration_minutes', 0)} minutes")
        print(f"Active learning: {result.get('active_learning_percentage', 0):.1f}%")
        print(f"Total tokens: {result.get('total_tokens', 0)}")
        print(f"Total cost: ${result.get('total_cost', 0):.4f}")
        
        report = result.get("curriculum_report", {})
        innovations = report.get("innovation_section", {}).get("innovations", [])
        print(f"\n=== INNOVATIONS ===")
        for i in innovations:
            print(f"- {i.get('innovation_name', 'Unknown')}")
    
    asyncio.run(test())
