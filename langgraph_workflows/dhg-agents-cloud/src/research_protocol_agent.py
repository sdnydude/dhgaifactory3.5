"""
Research Protocol Agent - Agent #8
====================================
Creates IRB-ready educational outcomes research protocol describing how
the educational activity's effectiveness will be measured.

LangGraph Cloud Ready:
- Produces complete outcomes research protocol
- Input from: Learning Objectives Agent, Curriculum Design Agent, Gap Analysis Agent
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

# Measurement methods by Moore level
MEASUREMENT_BY_LEVEL = {
    "level_3": {
        "methods": ["Pre/Post Knowledge Test", "Retention Test"],
        "timing": "Immediate, 30 days",
        "statistical": "Paired t-test or McNemar's test"
    },
    "level_4": {
        "methods": ["Case Vignettes", "Performance Assessment", "Scoring Rubric"],
        "timing": "Immediate, 30 days",
        "statistical": "Paired t-test on performance scores"
    },
    "level_5": {
        "methods": ["Commitment-to-Change", "Follow-up Survey", "Barrier Assessment"],
        "timing": "Immediate, 60-90 days",
        "statistical": "Proportion achieving commitment, qualitative barriers"
    },
    "level_6": {
        "methods": ["Chart Audit", "Registry Data", "Patient-Reported Outcomes"],
        "timing": "6+ months",
        "statistical": "Quality measure comparison, PRO analysis"
    }
}


# =============================================================================
# STATE DEFINITION
# =============================================================================

class ResearchProtocolState(TypedDict):
    # === INPUT (from upstream agents) ===
    learning_objectives_report: Dict[str, Any]
    curriculum_report: Dict[str, Any]
    gap_analysis_report: Dict[str, Any]
    
    # From intake form
    target_audience: str
    estimated_reach: Optional[int]
    outcome_goals: Optional[List[str]]
    moore_level_target: Optional[str]
    measurement_preferences: Optional[str]
    therapeutic_area: str
    disease_state: str
    
    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    
    # Section-specific data
    study_objectives: Dict[str, Any]
    study_design: Dict[str, Any]
    outcome_measures: Dict[str, Any]
    assessment_instruments: List[Dict[str, Any]]
    data_collection_plan: Dict[str, Any]
    statistical_plan: Dict[str, Any]
    ethical_considerations: Dict[str, Any]
    
    # === OUTPUT ===
    protocol_report: Dict[str, Any]
    protocol_document: str
    
    # === METADATA ===
    target_enrollment: int
    study_duration_months: int
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
    
    @traceable(name="research_protocol_llm_call", run_type="llm")
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

RESEARCH_PROTOCOL_SYSTEM_PROMPT = """You are an educational research methodologist designing an outcomes research protocol for a continuing medical education activity. Your protocol must:

1. RIGOROUS: Meet standards expected by pharmaceutical company grant reviewers
2. ALIGNED: Directly measure achievement of stated learning objectives
3. PRACTICAL: Be implementable within typical CME operational constraints
4. MOORE-ALIGNED: Use appropriate measurement methods for each Moore level
5. COMPREHENSIVE: Include all elements of a complete research protocol

STUDY DESIGN CONSIDERATIONS:
- Most CME outcomes studies are single-arm pre-post designs
- Controlled designs are rare but impressive when feasible
- Focus on what can actually be measured
- Be realistic about follow-up response rates (expect 40-60% attrition)

MEASUREMENT BY MOORE LEVEL:
- Level 3 (Learning): Pre/post knowledge assessment
- Level 4 (Competence): Case-based performance assessment
- Level 5 (Performance): Commitment-to-change with follow-up verification
- Level 6 (Patient Outcomes): PROs, chart audit, registry data (rarely achievable)

PROHIBITED:
- Overclaiming ability to measure patient outcomes
- Ignoring attrition/response rate challenges
- Vague outcome definitions
- Unrealistic sample size expectations
- Ignoring ethical considerations"""


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="define_study_objectives_node", run_type="chain")
async def define_study_objectives_node(state: ResearchProtocolState) -> dict:
    """Define primary and secondary study objectives."""
    
    objectives = state.get("learning_objectives_report", {}).get("objectives", [])
    gaps = state.get("gap_analysis_report", {}).get("gaps", [])
    disease = state.get("disease_state", "")
    audience = state.get("target_audience", "")
    
    system = f"""{RESEARCH_PROTOCOL_SYSTEM_PROMPT}

You are defining STUDY OBJECTIVES for an educational outcomes research protocol. Return a JSON object:
{{
    "title": "Outcomes Evaluation of [Disease] CME Program",
    "primary_objective": "To evaluate the effectiveness of [intervention] in improving [primary outcome] among [audience]",
    "secondary_objectives": [
        "To assess change in clinical competence...",
        "To evaluate knowledge retention..."
    ],
    "exploratory_objectives": [
        "To identify barriers to practice change..."
    ],
    "background_rationale": "Brief paragraph on why this study is needed...",
    "expected_contribution": "What this adds to CME outcomes literature..."
}}"""
    
    # Extract primary Moore level from objectives
    level_counts = {"level_5": 0, "level_4": 0, "level_3": 0}
    for obj in objectives:
        level = obj.get("moore_classification", {}).get("level", "").lower()
        if "5" in level:
            level_counts["level_5"] += 1
        elif "4" in level:
            level_counts["level_4"] += 1
        else:
            level_counts["level_3"] += 1
    
    primary_level = max(level_counts, key=level_counts.get)
    
    prompt = f"""Define study objectives for {disease} CME outcomes research.
Target audience: {audience}

LEARNING OBJECTIVES (to be measured):
{json.dumps([{"id": o.get("objective_id"), "text": o.get("objective_text", "")[:150], "level": o.get("moore_classification", {}).get("level")} for o in objectives], indent=2)}

EDUCATIONAL GAPS (context):
{json.dumps([{"title": g.get("title"), "delta": g.get("evidence", {}).get("practice_guideline_delta")} for g in gaps[:3]], indent=2)}

Primary Moore level focus: {primary_level}

Create study objectives that:
1. Are measurable and specific
2. Align to learning objectives
3. Are achievable within CME constraints

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "study_objectives"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            study_objectives = json.loads(json_match.group())
        else:
            study_objectives = {}
    except json.JSONDecodeError:
        study_objectives = {}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "study_objectives": study_objectives,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="design_study_node", run_type="chain")
async def design_study_node(state: ResearchProtocolState) -> dict:
    """Design study type, population, and sample size."""
    
    audience = state.get("target_audience", "")
    estimated_reach = state.get("estimated_reach", 200)
    disease = state.get("disease_state", "")
    
    system = f"""{RESEARCH_PROTOCOL_SYSTEM_PROMPT}

You are designing the STUDY DESIGN section. Return a JSON object:
{{
    "design_type": "Single-arm pre-post with longitudinal follow-up",
    "design_rationale": "Paragraph explaining why this design was chosen...",
    "study_population": {{
        "inclusion_criteria": [
            "Licensed physician (MD/DO) or APP",
            "Currently managing patients with [condition]",
            "Minimum X patients seen per month"
        ],
        "exclusion_criteria": [
            "Participated in similar education in past 6 months",
            "Not in active clinical practice"
        ]
    }},
    "sample_size": {{
        "target_n": 200,
        "power_calculation": "Paragraph on power/sample size rationale...",
        "dropout_assumptions": "40% attrition expected..."
    }},
    "study_duration": {{
        "enrollment_period": "X months",
        "follow_up_duration": "90 days",
        "total_duration": "X months"
    }}
}}"""
    
    target_n = estimated_reach if estimated_reach and estimated_reach > 0 else 200
    
    prompt = f"""Design study for {disease} CME outcomes research.
Target audience: {audience}
Estimated reach: {target_n} participants

Consider:
1. Single-arm pre-post is most common and practical
2. Expect 40% attrition by 60-day follow-up
3. Need ~64 completers for medium effect size (d=0.5)
4. Include realistic inclusion/exclusion criteria

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "study_design"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            study_design = json.loads(json_match.group())
        else:
            study_design = {}
    except json.JSONDecodeError:
        study_design = {}
    
    target_enrollment = study_design.get("sample_size", {}).get("target_n", target_n)
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "study_design": study_design,
        "target_enrollment": target_enrollment,
        "study_duration_months": 6,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="specify_outcomes_node", run_type="chain")
async def specify_outcomes_node(state: ResearchProtocolState) -> dict:
    """Specify primary and secondary outcome measures."""
    
    objectives = state.get("learning_objectives_report", {}).get("objectives", [])
    moore_target = state.get("moore_level_target", "Level 5")
    disease = state.get("disease_state", "")
    
    system = f"""{RESEARCH_PROTOCOL_SYSTEM_PROMPT}

You are specifying OUTCOME MEASURES. Return a JSON object:
{{
    "primary_outcome": {{
        "measure_name": "Self-reported evidence-based practice change",
        "moore_level": "Level 5 (Performance)",
        "definition": "Proportion of participants reporting implementation of targeted practice changes",
        "measurement_method": "Follow-up survey with specific behavior questions",
        "timing": "60 days post-activity",
        "success_threshold": "≥50% report implementing 2+ changes"
    }},
    "secondary_outcomes": [
        {{
            "measure_name": "Competence assessment score change",
            "moore_level": "Level 4 (Competence)",
            "definition": "Mean change in case-based assessment score",
            "measurement_method": "Validated case vignette assessment",
            "timing": "Pre and immediate post"
        }}
    ],
    "exploratory_outcomes": [
        {{
            "measure_name": "Barriers to practice change",
            "description": "Qualitative analysis of reported barriers"
        }}
    ]
}}

Primary outcome should align to the highest Moore level targeted."""
    
    prompt = f"""Specify outcome measures for {disease} CME research.
Target Moore level: {moore_target}

LEARNING OBJECTIVES TO MEASURE:
{json.dumps([{"id": o.get("objective_id"), "level": o.get("moore_classification", {}).get("level"), "measurement": o.get("measurement", {})} for o in objectives], indent=2)}

Create outcomes that:
1. Are clearly defined and measurable
2. Have specific success thresholds
3. Include appropriate timing
4. Align to Moore levels

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "outcomes"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            outcome_measures = json.loads(json_match.group())
        else:
            outcome_measures = {}
    except json.JSONDecodeError:
        outcome_measures = {}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "outcome_measures": outcome_measures,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="design_instruments_node", run_type="chain")
async def design_instruments_node(state: ResearchProtocolState) -> dict:
    """Design assessment instruments."""
    
    outcomes = state.get("outcome_measures", {})
    disease = state.get("disease_state", "")
    
    system = f"""{RESEARCH_PROTOCOL_SYSTEM_PROMPT}

You are designing ASSESSMENT INSTRUMENTS. Return a JSON array:
{{
    "instruments": [
        {{
            "instrument_name": "Pre-Activity Knowledge Assessment",
            "purpose": "Establish baseline knowledge",
            "description": "10-item MCQ covering key content areas",
            "validation_status": "Content-validated by expert panel",
            "administration_timing": "Before activity",
            "scoring_method": "Percentage correct"
        }},
        {{
            "instrument_name": "Case-Based Competence Assessment",
            "purpose": "Assess clinical decision-making",
            "description": "3 clinical vignettes with scoring rubric",
            "validation_status": "Based on validated case methodology",
            "administration_timing": "Pre and immediate post",
            "scoring_method": "Rubric scoring 0-100"
        }},
        {{
            "instrument_name": "Commitment-to-Change Survey",
            "purpose": "Capture intended practice changes",
            "description": "Specific, measurable commitment statements",
            "validation_status": "Standard CME methodology",
            "administration_timing": "Immediate post-activity",
            "scoring_method": "Number and specificity of commitments"
        }},
        {{
            "instrument_name": "60-Day Follow-up Survey",
            "purpose": "Assess practice change implementation",
            "description": "Survey on implementation of committed changes",
            "validation_status": "Standard follow-up methodology",
            "administration_timing": "60 days post",
            "scoring_method": "Proportion implementing changes"
        }}
    ]
}}"""
    
    prompt = f"""Design assessment instruments for {disease} CME outcomes research.

OUTCOMES TO MEASURE:
Primary: {json.dumps(outcomes.get('primary_outcome', {}), indent=2)}
Secondary: {json.dumps(outcomes.get('secondary_outcomes', []), indent=2)[:1500]}

Design instruments that:
1. Align to each outcome measure
2. Are practical to administer
3. Have clear scoring methods
4. Cover all assessment timepoints

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "instruments"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            instruments = data.get("instruments", [])
        else:
            instruments = []
    except json.JSONDecodeError:
        instruments = []
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "assessment_instruments": instruments,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="create_data_collection_plan_node", run_type="chain")
async def create_data_collection_plan_node(state: ResearchProtocolState) -> dict:
    """Create the data collection plan."""
    
    instruments = state.get("assessment_instruments", [])
    
    # Build timepoints from instruments
    timepoints = []
    
    # Pre-activity
    pre_instruments = [i["instrument_name"] for i in instruments 
                       if "pre" in i.get("administration_timing", "").lower() or "before" in i.get("administration_timing", "").lower()]
    if pre_instruments:
        timepoints.append({
            "timepoint_name": "Baseline (Pre-Activity)",
            "timing": "Immediately before educational activity",
            "assessments_administered": pre_instruments,
            "data_collected": ["Baseline knowledge", "Demographics", "Practice characteristics"]
        })
    
    # Immediate post
    post_instruments = [i["instrument_name"] for i in instruments 
                        if "immediate" in i.get("administration_timing", "").lower() or "post" in i.get("administration_timing", "").lower()]
    if post_instruments:
        timepoints.append({
            "timepoint_name": "Immediate Post-Activity",
            "timing": "Within 30 minutes of activity completion",
            "assessments_administered": post_instruments,
            "data_collected": ["Post-activity knowledge/competence", "Satisfaction", "Commitments to change"]
        })
    
    # 30-day
    timepoints.append({
        "timepoint_name": "30-Day Follow-up",
        "timing": "30 days +/- 7 days post-activity",
        "assessments_administered": ["Knowledge Retention Assessment"],
        "data_collected": ["Knowledge retention", "Initial practice change"]
    })
    
    # 60-day
    timepoints.append({
        "timepoint_name": "60-Day Follow-up",
        "timing": "60 days +/- 14 days post-activity",
        "assessments_administered": ["Practice Change Survey", "Barrier Assessment"],
        "data_collected": ["Commitment implementation", "Barriers encountered", "Practice changes made"]
    })
    
    data_collection_plan = {
        "timepoints": timepoints,
        "data_management": {
            "collection_method": "Electronic survey platform (e.g., REDCap, SurveyMonkey)",
            "storage": "Secure, HIPAA-compliant server with restricted access",
            "quality_assurance": "Range checks, logic checks, double data entry for key variables"
        }
    }
    
    return {
        "data_collection_plan": data_collection_plan,
        "total_tokens": state.get("total_tokens", 0),
        "total_cost": state.get("total_cost", 0.0)
    }


@traceable(name="develop_statistical_plan_node", run_type="chain")
async def develop_statistical_plan_node(state: ResearchProtocolState) -> dict:
    """Develop the statistical analysis plan."""
    
    outcomes = state.get("outcome_measures", {})
    target_n = state.get("target_enrollment", 200)
    
    system = f"""{RESEARCH_PROTOCOL_SYSTEM_PROMPT}

You are developing a STATISTICAL ANALYSIS PLAN. Return a JSON object:
{{
    "primary_analysis": {{
        "method": "Descriptive statistics with 95% confidence intervals",
        "description": "Paragraph describing primary analysis approach..."
    }},
    "secondary_analyses": [
        {{
            "analysis": "Competence score change",
            "method": "Paired t-test comparing pre and post scores"
        }}
    ],
    "subgroup_analyses": [
        "Specialty (cardiology vs internal medicine vs primary care)",
        "Practice setting (academic vs community)"
    ],
    "handling_missing_data": "Paragraph describing missing data approach..."
}}"""
    
    prompt = f"""Develop statistical plan for CME outcomes research.
Target enrollment: {target_n}
Expected completers: ~{int(target_n * 0.6)} (40% attrition)

PRIMARY OUTCOME:
{json.dumps(outcomes.get('primary_outcome', {}), indent=2)}

SECONDARY OUTCOMES:
{json.dumps(outcomes.get('secondary_outcomes', [])[:3], indent=2)}

Create a statistical plan that:
1. Is appropriate for pre-post educational outcomes
2. Addresses missing data realistically
3. Includes relevant subgroup analyses
4. Uses appropriate methods for data types

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "statistical_plan"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            statistical_plan = json.loads(json_match.group())
        else:
            statistical_plan = {}
    except json.JSONDecodeError:
        statistical_plan = {}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "statistical_plan": statistical_plan,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="address_ethics_node", run_type="chain")
async def address_ethics_node(state: ResearchProtocolState) -> dict:
    """Address ethical considerations."""
    
    ethical_considerations = {
        "irb_requirements": "Protocol will be submitted for IRB review. Educational outcomes research with minimal risk typically qualifies for expedited review or exemption under 45 CFR 46.104(d)(1) as research on educational practices.",
        "informed_consent": "Participants will be informed of the research component and provide consent by completing the pre-activity assessment. Consent will explain data use, confidentiality, and voluntary nature.",
        "data_privacy": "All data will be collected and stored in HIPAA-compliant systems. Identifying information will be separated from responses and linked only by study ID. Data will be reported only in aggregate.",
        "participant_rights": "Participation in research component is voluntary. Participants may complete the educational activity without contributing data to the study. No incentives contingent on research participation."
    }
    
    return {
        "ethical_considerations": ethical_considerations,
        "total_tokens": state.get("total_tokens", 0),
        "total_cost": state.get("total_cost", 0.0)
    }


@traceable(name="assemble_protocol_report_node", run_type="chain")
async def assemble_protocol_report_node(state: ResearchProtocolState) -> dict:
    """Assemble the final protocol report."""
    
    study_objectives = state.get("study_objectives", {})
    outcomes = state.get("outcome_measures", {})
    
    report = {
        "metadata": {
            "agent_version": "2.0",
            "execution_timestamp": datetime.now().isoformat(),
            "protocol_type": "Educational Outcomes Research",
            "model_used": "claude-sonnet-4",
            "total_tokens": state.get("total_tokens", 0),
            "total_cost": state.get("total_cost", 0.0)
        },
        "protocol_summary": {
            "title": study_objectives.get("title", "CME Outcomes Evaluation"),
            "study_type": "Prospective single-arm educational outcomes study",
            "primary_endpoint": outcomes.get("primary_outcome", {}).get("measure_name", ""),
            "secondary_endpoints": [o.get("measure_name") for o in outcomes.get("secondary_outcomes", [])],
            "study_duration": f"{state.get('study_duration_months', 6)} months",
            "target_enrollment": state.get("target_enrollment", 200)
        },
        "background_and_rationale": {
            "educational_gap_summary": study_objectives.get("background_rationale", ""),
            "rationale_for_study": "Educational outcomes research is essential for demonstrating CME effectiveness and continuous quality improvement.",
            "expected_contribution": study_objectives.get("expected_contribution", "")
        },
        "study_objectives": study_objectives,
        "study_design": state.get("study_design", {}),
        "outcome_measures": outcomes,
        "assessment_instruments": state.get("assessment_instruments", []),
        "data_collection_plan": state.get("data_collection_plan", {}),
        "statistical_analysis_plan": state.get("statistical_plan", {}),
        "ethical_considerations": state.get("ethical_considerations", {}),
        "limitations": {
            "design_limitations": [
                "Single-arm design cannot establish causation",
                "Self-reported practice change may not reflect actual behavior",
                "Volunteer bias in follow-up responders"
            ],
            "measurement_limitations": [
                "Knowledge assessment may not predict clinical performance",
                "60-day follow-up may not capture sustained change"
            ],
            "generalizability_considerations": "Participants who complete CME may differ from broader target population"
        },
        "timeline": {
            "phases": [
                {"phase_name": "Protocol Finalization", "duration": "1 month", "activities": ["IRB submission", "Instrument development", "Platform setup"]},
                {"phase_name": "Enrollment", "duration": "3 months", "activities": ["Educational activity delivery", "Baseline and post-activity assessment"]},
                {"phase_name": "Follow-up", "duration": "2 months", "activities": ["30-day and 60-day surveys", "Reminder protocols"]},
                {"phase_name": "Analysis and Reporting", "duration": "1 month", "activities": ["Data cleaning", "Statistical analysis", "Report writing"]}
            ]
        }
    }
    
    return {
        "protocol_report": report,
        "messages": [HumanMessage(content=f"Research protocol complete: {state.get('target_enrollment', 200)} target enrollment, {state.get('study_duration_months', 6)}-month study")]
    }


@traceable(name="render_protocol_document_node", run_type="chain")
async def render_protocol_document_node(state: ResearchProtocolState) -> dict:
    """Render the protocol as a readable document."""
    
    disease = state.get("disease_state", "")
    report = state.get("protocol_report", {})
    
    system = """You are a research methodologist writing an IRB-ready outcomes research protocol.

FORMATTING RULES:
- Use formal research protocol structure
- Use markdown headers
- Include numbered sections
- Be specific and precise

STRUCTURE:
1. Protocol Summary
2. Background and Rationale
3. Study Objectives
4. Study Design and Methods
5. Study Population
6. Outcome Measures
7. Assessment Instruments
8. Data Collection Plan
9. Statistical Analysis Plan
10. Ethical Considerations
11. Limitations
12. Timeline
13. References

Write in formal scientific style suitable for IRB review."""
    
    prompt = f"""Create an IRB-ready research protocol document for {disease} CME outcomes research.

PROTOCOL DATA:
{json.dumps(report, indent=2)[:15000]}

Format as a complete, formal research protocol document."""

    result = await llm.generate(system, prompt, {"step": "render_document"})
    
    document = result["content"]
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "protocol_document": document,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


# =============================================================================
# BUILD GRAPH
# =============================================================================

def create_research_protocol_graph() -> StateGraph:
    """Create the Research Protocol Agent graph."""
    
    graph = StateGraph(ResearchProtocolState)
    
    # Add nodes
    graph.add_node("define_objectives", define_study_objectives_node)
    graph.add_node("design_study", design_study_node)
    graph.add_node("specify_outcomes", specify_outcomes_node)
    graph.add_node("design_instruments", design_instruments_node)
    graph.add_node("create_data_plan", create_data_collection_plan_node)
    graph.add_node("develop_stats", develop_statistical_plan_node)
    graph.add_node("address_ethics", address_ethics_node)
    graph.add_node("assemble_report", assemble_protocol_report_node)
    graph.add_node("render_document", render_protocol_document_node)
    
    # Flow: sequential protocol development
    graph.set_entry_point("define_objectives")
    
    graph.add_edge("define_objectives", "design_study")
    graph.add_edge("design_study", "specify_outcomes")
    graph.add_edge("specify_outcomes", "design_instruments")
    graph.add_edge("design_instruments", "create_data_plan")
    graph.add_edge("create_data_plan", "develop_stats")
    graph.add_edge("develop_stats", "address_ethics")
    graph.add_edge("address_ethics", "assemble_report")
    graph.add_edge("assemble_report", "render_document")
    graph.add_edge("render_document", END)
    
    return graph


# Compile for LangGraph Cloud
graph = create_research_protocol_graph().compile()


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
                }
            ]
        }
        
        mock_gaps = {
            "gaps": [
                {
                    "gap_id": "GAP-001",
                    "title": "SGLT2i Initiation Gap",
                    "evidence": {"practice_guideline_delta": "77%"}
                }
            ]
        }
        
        test_state = {
            "learning_objectives_report": mock_objectives,
            "gap_analysis_report": mock_gaps,
            "curriculum_report": {},
            "therapeutic_area": "cardiology",
            "disease_state": "heart failure",
            "target_audience": "cardiologists",
            "estimated_reach": 200,
            "moore_level_target": "Level 5",
            "messages": [],
            "errors": [],
            "total_tokens": 0,
            "total_cost": 0.0
        }
        
        result = await graph.ainvoke(test_state)
        
        print(f"\n=== RESEARCH PROTOCOL RESULT ===")
        print(f"Target enrollment: {result.get('target_enrollment', 0)}")
        print(f"Study duration: {result.get('study_duration_months', 0)} months")
        print(f"Total tokens: {result.get('total_tokens', 0)}")
        print(f"Total cost: ${result.get('total_cost', 0):.4f}")
        
        report = result.get("protocol_report", {})
        summary = report.get("protocol_summary", {})
        print(f"\n=== PROTOCOL SUMMARY ===")
        print(f"Title: {summary.get('title', 'Unknown')}")
        print(f"Primary endpoint: {summary.get('primary_endpoint', 'Unknown')}")
    
    asyncio.run(test())
