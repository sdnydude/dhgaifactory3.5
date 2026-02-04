"""
Gap Analysis Agent - Agent #4
==============================
Synthesizes Research and Clinical Practice outputs to identify, quantify,
and prioritize evidence-based educational gaps.

LangGraph Cloud Ready:
- Produces 5-8 prioritized, validated gaps
- Input from: Research Agent, Clinical Practice Agent
- Output to: Needs Assessment Agent, Learning Objectives Agent
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

# Prioritization scoring weights (100 points total)
SCORING_WEIGHTS = {
    "gap_magnitude": 0.25,
    "patient_impact": 0.25,
    "educational_addressability": 0.20,
    "measurability": 0.15,
    "alignment": 0.15
}


# =============================================================================
# STATE DEFINITION
# =============================================================================

class GapAnalysisState(TypedDict):
    # === INPUT (from upstream agents) ===
    # From Research Agent
    research_report: Dict[str, Any]
    
    # From Clinical Practice Agent
    clinical_practice_report: Dict[str, Any]
    
    # From intake form
    known_gaps: Optional[List[str]]
    educational_priorities: Optional[List[str]]
    outcome_goals: Optional[List[str]]
    therapeutic_area: str
    disease_state: str
    target_audience: str
    
    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    
    # Section-specific data
    synthesis_summary: Dict[str, Any]
    raw_gaps: List[Dict[str, Any]]
    validated_gaps: List[Dict[str, Any]]
    prioritized_gaps: List[Dict[str, Any]]
    
    # === OUTPUT ===
    gap_analysis_report: Dict[str, Any]
    gap_analysis_document: str
    
    # === METADATA ===
    gaps_identified: int
    gaps_prioritized: int
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
    
    @traceable(name="gap_analysis_llm_call", run_type="llm")
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

GAP_ANALYSIS_SYSTEM_PROMPT = """You are an educational gap analyst synthesizing research evidence and clinical practice data to identify educational needs for continuing medical education. Your analysis must:

1. SYNTHESIZE: Integrate research findings with practice reality to identify disconnects
2. QUANTIFY: Every gap must have numerical evidence of the practice-guideline delta
3. ROOT CAUSE: Identify WHY the gap exists, categorizing barriers appropriately
4. PATIENT IMPACT: Connect every gap to patient outcomes
5. PRIORITIZE: Rank gaps by educational addressability and potential impact

GAP DEFINITION CRITERIA:
A valid educational gap must meet ALL of these criteria:
- Evidence-based: Supported by research data
- Quantifiable: Practice-guideline delta can be measured
- Addressable: Education can reasonably impact the gap
- Outcome-linked: Gap closure would improve patient outcomes
- Barrier-analyzed: Root cause identified and categorized

BARRIER CATEGORIES:
- KNOWLEDGE: Clinician doesn't know (awareness, familiarity, currency)
- SKILL: Clinician doesn't know how (procedural, communication, implementation)
- ATTITUDE: Clinician doesn't agree or prioritize
- SYSTEM: External factors prevent action (not primarily educational)

OUTPUT REQUIREMENTS:
- Minimum 5 distinct, well-documented gaps
- Maximum 8 gaps (focus over breadth)
- Each gap must have quantified evidence
- Each gap must have barrier categorization
- Each gap must have patient impact statement

PROHIBITED:
- Gaps without quantified evidence
- Gaps that are purely system/policy issues
- Duplicate gaps with different wording
- Vague or generic gap statements"""


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="synthesize_inputs_node", run_type="chain")
async def synthesize_inputs_node(state: GapAnalysisState) -> dict:
    """Synthesize research and clinical practice findings."""
    
    disease = state.get("disease_state", "")
    research = state.get("research_report", {})
    clinical = state.get("clinical_practice_report", {})
    
    system = f"""{GAP_ANALYSIS_SYSTEM_PROMPT}

You are creating a SYNTHESIS SUMMARY of research and practice findings. Return a JSON object:
{{
    "evidence_base": "2-3 sentence summary of key research findings",
    "practice_reality": "2-3 sentence summary of actual practice patterns",
    "key_disconnects": [
        "disconnect 1: where guidelines say X but practice shows Y",
        "disconnect 2: ...",
        "disconnect 3: ..."
    ]
}}"""
    
    # Truncate inputs to fit context
    research_summary = json.dumps({
        "epidemiology": research.get("epidemiology", {}),
        "treatment_landscape": research.get("treatment_landscape", {}),
        "guidelines": research.get("guidelines", {}),
        "literature_synthesis": research.get("literature_synthesis", {})
    }, indent=2)[:4000]
    
    clinical_summary = json.dumps({
        "standard_of_care": clinical.get("standard_of_care", {}),
        "real_world_practice": clinical.get("real_world_practice", {}),
        "practice_barriers": clinical.get("practice_barriers", {})
    }, indent=2)[:4000]
    
    prompt = f"""Synthesize findings for {disease}.

RESEARCH FINDINGS:
{research_summary}

CLINICAL PRACTICE FINDINGS:
{clinical_summary}

Identify key disconnects between evidence and practice. Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "synthesize_inputs"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            synthesis = json.loads(json_match.group())
        else:
            synthesis = {"error": "Failed to parse synthesis"}
    except json.JSONDecodeError:
        synthesis = {"error": "Invalid JSON in synthesis"}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "synthesis_summary": synthesis,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="identify_gaps_node", run_type="chain")
async def identify_gaps_node(state: GapAnalysisState) -> dict:
    """Identify all potential educational gaps."""
    
    disease = state.get("disease_state", "")
    audience = state.get("target_audience", "")
    synthesis = state.get("synthesis_summary", {})
    research = state.get("research_report", {})
    clinical = state.get("clinical_practice_report", {})
    known_gaps = state.get("known_gaps", [])
    
    system = f"""{GAP_ANALYSIS_SYSTEM_PROMPT}

You are identifying EDUCATIONAL GAPS. Return a JSON array of 5-8 gaps:
{{
    "gaps": [
        {{
            "gap_id": "GAP-001",
            "title": "Concise gap statement (under 10 words)",
            "description": "2-3 sentence elaboration of the gap",
            "evidence": {{
                "guideline_recommendation": "What guidelines say (with citation)",
                "current_practice": "What actually happens (with source)",
                "practice_guideline_delta": "X% gap (100% - actual%)"
            }},
            "root_causes": {{
                "primary_barrier_type": "knowledge|skill|attitude|system",
                "contributing_factors": ["factor 1", "factor 2"],
                "barrier_evidence": "Source for barrier claim"
            }},
            "patient_impact": {{
                "affected_population": "Who is affected and how many",
                "outcome_consequence": "What happens to patients",
                "quantified_impact": "X% increased mortality/hospitalization"
            }}
        }}
    ]
}}"""
    
    # Include known gaps for validation
    known_context = ""
    if known_gaps:
        known_context = f"\nKNOWN GAPS TO VALIDATE:\n- " + "\n- ".join(known_gaps)
    
    # Get barriers from clinical report
    barriers = clinical.get("practice_barriers", {})
    
    prompt = f"""Identify educational gaps for {disease} targeting {audience}.

SYNTHESIS:
{json.dumps(synthesis, indent=2)}

REAL-WORLD PRACTICE DATA:
{json.dumps(clinical.get('real_world_practice', {}), indent=2)[:2000]}

BARRIERS IDENTIFIED:
{json.dumps(barriers, indent=2)[:2000]}
{known_context}

Identify 5-8 distinct, quantified gaps. Each must have evidence and barrier categorization. Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "identify_gaps"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            gaps_data = json.loads(json_match.group())
            raw_gaps = gaps_data.get("gaps", [])
        else:
            raw_gaps = []
    except json.JSONDecodeError:
        raw_gaps = []
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "raw_gaps": raw_gaps,
        "gaps_identified": len(raw_gaps),
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="validate_gaps_node", run_type="chain")
async def validate_gaps_node(state: GapAnalysisState) -> dict:
    """Validate each gap meets all criteria and add addressability assessment."""
    
    raw_gaps = state.get("raw_gaps", [])
    
    system = f"""{GAP_ANALYSIS_SYSTEM_PROMPT}

You are VALIDATING and ENRICHING gaps. For each gap, add:
1. Educational addressability assessment
2. Moore's level target
3. ACCME criteria addressed

Return a JSON array:
{{
    "validated_gaps": [
        {{
            ...existing gap fields...,
            "educational_addressability": {{
                "addressable": true|false,
                "rationale": "Why education can/cannot address this",
                "expected_impact": "What education could achieve",
                "limitations": "What education cannot fix"
            }},
            "alignment": {{
                "moore_level_target": "Level 3|4|5|6|7",
                "accme_criteria_addressed": ["Practice Gap", "Educational Need", "Desired Outcome"],
                "measurement_approach": "How to measure impact"
            }}
        }}
    ]
}}"""
    
    prompt = f"""Validate and enrich these gaps.

GAPS TO VALIDATE:
{json.dumps(raw_gaps, indent=2)}

For each gap:
1. Verify it has quantified evidence
2. Confirm barrier is categorized
3. Add educational addressability assessment
4. Add Moore's level target
5. Filter out any that are purely system issues

Return ONLY valid JSON with validated_gaps array."""

    result = await llm.generate(system, prompt, {"step": "validate_gaps"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            validated = data.get("validated_gaps", raw_gaps)
        else:
            validated = raw_gaps
    except json.JSONDecodeError:
        validated = raw_gaps
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "validated_gaps": validated,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="prioritize_gaps_node", run_type="chain")
async def prioritize_gaps_node(state: GapAnalysisState) -> dict:
    """Score and prioritize gaps."""
    
    validated_gaps = state.get("validated_gaps", [])
    educational_priorities = state.get("educational_priorities", [])
    outcome_goals = state.get("outcome_goals", [])
    
    system = f"""{GAP_ANALYSIS_SYSTEM_PROMPT}

You are SCORING and PRIORITIZING gaps using this rubric (100 points total):

GAP MAGNITUDE (25 points):
- 25: Delta >50% of target
- 20: Delta 30-50%
- 15: Delta 15-30%
- 10: Delta <15%

PATIENT IMPACT (25 points):
- 25: Mortality/major morbidity
- 20: Hospitalization/significant morbidity
- 15: Quality of life impact
- 10: Efficiency/convenience

EDUCATIONAL ADDRESSABILITY (20 points):
- 20: Primarily knowledge/skill gap
- 15: Mixed knowledge/attitude
- 10: Significant system component
- 5: Primarily system/policy

MEASURABILITY (15 points):
- 15: Established quality metrics exist
- 10: Can measure with commitment-to-change
- 5: Measurement challenging

ALIGNMENT (15 points):
- 15: Directly addresses stated priorities
- 10: Related to priorities
- 5: Tangentially connected

Return JSON:
{{
    "prioritized_gaps": [
        {{
            ...all existing fields...,
            "priority_score": {{
                "total": 85,
                "breakdown": {{
                    "gap_magnitude": 25,
                    "patient_impact": 20,
                    "educational_addressability": 20,
                    "measurability": 10,
                    "alignment": 10
                }},
                "rationale": "Brief explanation of scoring"
            }}
        }}
    ],
    "ranked_order": ["GAP-001", "GAP-003", "GAP-002", ...]
}}"""
    
    priorities_context = ""
    if educational_priorities:
        priorities_context = f"\nEDUCATIONAL PRIORITIES: {', '.join(educational_priorities)}"
    if outcome_goals:
        priorities_context += f"\nOUTCOME GOALS: {', '.join(outcome_goals)}"
    
    prompt = f"""Score and prioritize these validated gaps.
{priorities_context}

GAPS TO PRIORITIZE:
{json.dumps(validated_gaps, indent=2)}

Apply the scoring rubric to each gap. Return ranked by total score (highest first). Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "prioritize_gaps"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            prioritized = data.get("prioritized_gaps", validated_gaps)
        else:
            prioritized = validated_gaps
    except json.JSONDecodeError:
        prioritized = validated_gaps
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "prioritized_gaps": prioritized,
        "gaps_prioritized": len(prioritized),
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="assemble_gap_report_node", run_type="chain")
async def assemble_gap_report_node(state: GapAnalysisState) -> dict:
    """Assemble the final gap analysis report."""
    
    prioritized_gaps = state.get("prioritized_gaps", [])
    synthesis = state.get("synthesis_summary", {})
    
    # Sort gaps by priority score
    sorted_gaps = sorted(
        prioritized_gaps,
        key=lambda g: g.get("priority_score", {}).get("total", 0) if isinstance(g.get("priority_score"), dict) else 0,
        reverse=True
    )
    
    # Split into primary and secondary
    primary_focus = [g.get("gap_id", f"GAP-{i+1}") for i, g in enumerate(sorted_gaps[:3])]
    secondary_focus = [g.get("gap_id", f"GAP-{i+4}") for i, g in enumerate(sorted_gaps[3:6])]
    
    # Identify system-heavy gaps
    system_gaps = [
        g.get("gap_id")
        for g in sorted_gaps
        if g.get("root_causes", {}).get("primary_barrier_type") == "system"
    ]
    
    report = {
        "metadata": {
            "agent_version": "2.0",
            "execution_timestamp": datetime.now().isoformat(),
            "gaps_identified": state.get("gaps_identified", 0),
            "gaps_prioritized": len(sorted_gaps),
            "model_used": "claude-sonnet-4",
            "total_tokens": state.get("total_tokens", 0),
            "total_cost": state.get("total_cost", 0.0)
        },
        "synthesis_summary": synthesis,
        "gaps": sorted_gaps,
        "gap_prioritization": {
            "methodology": "Weighted multi-criteria scoring",
            "scoring_criteria": [
                {"criterion": "Gap Magnitude", "weight": 0.25},
                {"criterion": "Patient Impact", "weight": 0.25},
                {"criterion": "Educational Addressability", "weight": 0.20},
                {"criterion": "Measurability", "weight": 0.15},
                {"criterion": "Alignment", "weight": 0.15}
            ],
            "ranked_gaps": [g.get("gap_id", f"GAP-{i+1}") for i, g in enumerate(sorted_gaps)]
        },
        "recommendations": {
            "primary_focus": primary_focus,
            "secondary_focus": secondary_focus,
            "gaps_requiring_system_change": system_gaps
        }
    }
    
    return {
        "gap_analysis_report": report,
        "messages": [HumanMessage(content=f"Gap analysis complete: {len(sorted_gaps)} gaps prioritized, top 3 identified for primary focus")]
    }


@traceable(name="render_gap_document_node", run_type="chain")
async def render_gap_document_node(state: GapAnalysisState) -> dict:
    """Render the gap report as a readable prose document."""
    
    disease = state.get("disease_state", "")
    report = state.get("gap_analysis_report", {})
    
    system = """You are a medical writer converting gap analysis data into a cohesive, readable report.

FORMATTING RULES:
- Use markdown headers (## for main sections)
- Write flowing prose paragraphs, not bullet points
- Include inline citations
- 80%+ prose density
- Active voice

STRUCTURE:
1. Executive Summary (key gaps and priorities)
2. Evidence-Practice Synthesis
3. Gap Analysis (for each gap):
   - Gap statement and description
   - Evidence of the gap (quantified)
   - Root causes and barriers
   - Patient impact
   - Educational addressability
   - Priority score rationale
4. Prioritization and Recommendations
5. Implementation Considerations

Do NOT use:
- Em dashes (—)
- "It's important to note"
- Bullet points in prose sections
- Colons in prose (except citations)
"""
    
    prompt = f"""Convert this gap analysis for {disease} into a cohesive report.

GAP ANALYSIS DATA:
{json.dumps(report, indent=2)[:12000]}

Write a complete, readable gap analysis report. Emphasize quantified deltas and barrier categorization for each gap."""

    result = await llm.generate(system, prompt, {"step": "render_document"})
    
    document = result["content"]
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "gap_analysis_document": document,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


# =============================================================================
# BUILD GRAPH
# =============================================================================

def create_gap_analysis_graph() -> StateGraph:
    """Create the Gap Analysis Agent graph."""
    
    graph = StateGraph(GapAnalysisState)
    
    # Add nodes
    graph.add_node("synthesize_inputs", synthesize_inputs_node)
    graph.add_node("identify_gaps", identify_gaps_node)
    graph.add_node("validate_gaps", validate_gaps_node)
    graph.add_node("prioritize_gaps", prioritize_gaps_node)
    graph.add_node("assemble_report", assemble_gap_report_node)
    graph.add_node("render_document", render_gap_document_node)
    
    # Flow: sequential analysis
    graph.set_entry_point("synthesize_inputs")
    
    graph.add_edge("synthesize_inputs", "identify_gaps")
    graph.add_edge("identify_gaps", "validate_gaps")
    graph.add_edge("validate_gaps", "prioritize_gaps")
    graph.add_edge("prioritize_gaps", "assemble_report")
    graph.add_edge("assemble_report", "render_document")
    graph.add_edge("render_document", END)
    
    return graph


# Compile for LangGraph Cloud
graph = create_gap_analysis_graph().compile()


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        # Mock upstream data
        mock_research = {
            "epidemiology": {"prevalence": {"us": "6.7 million Americans"}},
            "treatment_landscape": {"current_standards": {"first_line": ["SGLT2i", "ARNi"]}},
            "guidelines": {"major_guidelines": [{"society": "ACC/AHA", "year": 2022}]},
            "literature_synthesis": {"evidence_gaps": ["Limited HFpEF data"]}
        }
        
        mock_clinical = {
            "standard_of_care": {"treatment_algorithm": {"first_line": ["SGLT2i"]}},
            "real_world_practice": {"treatment_patterns": {"utilization_rates": {"SGLT2i": "23%"}}},
            "practice_barriers": {
                "clinician_barriers": {"knowledge_gaps": [{"barrier": "Unaware of HF indication"}]}
            }
        }
        
        test_state = {
            "research_report": mock_research,
            "clinical_practice_report": mock_clinical,
            "therapeutic_area": "cardiology",
            "disease_state": "heart failure with preserved ejection fraction",
            "target_audience": "cardiologists",
            "known_gaps": ["Underuse of SGLT2 inhibitors"],
            "educational_priorities": ["Improve GDMT initiation"],
            "outcome_goals": ["Reduce HF hospitalizations"],
            "messages": [],
            "errors": [],
            "total_tokens": 0,
            "total_cost": 0.0
        }
        
        result = await graph.ainvoke(test_state)
        
        print(f"\n=== GAP ANALYSIS RESULT ===")
        print(f"Gaps identified: {result.get('gaps_identified', 0)}")
        print(f"Gaps prioritized: {result.get('gaps_prioritized', 0)}")
        print(f"Total tokens: {result.get('total_tokens', 0)}")
        print(f"Total cost: ${result.get('total_cost', 0):.4f}")
        
        report = result.get("gap_analysis_report", {})
        recs = report.get("recommendations", {})
        print(f"\n=== RECOMMENDATIONS ===")
        print(f"Primary focus: {recs.get('primary_focus', [])}")
        print(f"Secondary focus: {recs.get('secondary_focus', [])}")
    
    asyncio.run(test())
