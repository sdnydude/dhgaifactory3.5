"""
Learning Objectives Agent - Agent #6
=====================================
Creates measurable learning objectives using Moore's Expanded Outcomes Framework.
Each objective traces to identified gaps and includes measurement methodology.

LangGraph Cloud Ready:
- Produces 6-10 objectives aligned to gaps
- Input from: Gap Analysis Agent, Needs Assessment Agent
- Output to: Curriculum Design Agent, Research Protocol Agent
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

# Moore's Level verb lists
MOORE_VERBS = {
    "level_5": [
        "prescribe", "order", "initiate", "discontinue", "adjust", "monitor",
        "refer", "screen", "counsel", "document", "implement", "integrate", "incorporate"
    ],
    "level_4": [
        "select", "determine", "differentiate", "assess", "evaluate", "calculate",
        "interpret", "formulate", "develop", "design"
    ],
    "level_3b": [
        "perform", "execute", "demonstrate", "apply", "use", "administer", "conduct"
    ],
    "level_3a": [
        "identify", "recognize", "describe", "explain"
    ]
}

# Target distribution percentages
DISTRIBUTION_TARGETS = {
    "level_5_target": {"level_5": 0.50, "level_4": 0.35, "level_3": 0.15},
    "level_4_target": {"level_4": 0.70, "level_3b": 0.15, "level_3a": 0.15}
}


# =============================================================================
# STATE DEFINITION
# =============================================================================

class LearningObjectivesState(TypedDict):
    # === INPUT (from upstream agents) ===
    # From Gap Analysis Agent
    gap_analysis_report: Dict[str, Any]
    
    # From Needs Assessment (for context)
    needs_assessment_document: Optional[str]
    
    # From intake form
    target_audience: str
    educational_format: Optional[str]
    outcome_goals: Optional[List[str]]
    moore_level_target: Optional[str]  # "Level 4", "Level 5"
    therapeutic_area: str
    disease_state: str
    
    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    
    # Section-specific data
    distribution_plan: Dict[str, Any]
    level_5_objectives: List[Dict[str, Any]]
    level_4_objectives: List[Dict[str, Any]]
    level_3_objectives: List[Dict[str, Any]]
    all_objectives: List[Dict[str, Any]]
    gap_coverage_matrix: List[Dict[str, Any]]
    
    # === OUTPUT ===
    learning_objectives_report: Dict[str, Any]
    learning_objectives_document: str
    
    # === METADATA ===
    objectives_count: int
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
    
    @traceable(name="learning_objectives_llm_call", run_type="llm")
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

LEARNING_OBJECTIVES_SYSTEM_PROMPT = """You are a learning objectives specialist creating objectives for continuing medical education using Moore's Expanded Outcomes Framework. Your objectives must:

1. ALIGN TO GAPS: Every objective must address an identified educational gap
2. USE MOORE'S: Moore's Framework is PRIMARY; Bloom's is secondary only
3. BE MEASURABLE: Every objective must have clear measurement methodology
4. LINK TO OUTCOMES: Every objective must connect to patient outcomes
5. USE CORRECT VERBS: Action verbs must match the Moore level exactly

MOORE'S FRAMEWORK LEVELS:
- Level 5 (Performance): Actual behavior change in practice
  VERBS: prescribe, order, initiate, discontinue, adjust, monitor, refer, screen, counsel, document, implement, integrate, incorporate
  
- Level 4 (Competence): Ability to apply in simulated setting
  VERBS: select, determine, differentiate, assess, evaluate, calculate, interpret, formulate, develop, design
  
- Level 3B (Procedural Knowledge): Can demonstrate skill
  VERBS: perform, execute, demonstrate, apply, use, administer, conduct
  
- Level 3A (Declarative Knowledge): Can recall/explain
  VERBS: identify, recognize, describe, explain (USE SPARINGLY)

OBJECTIVE CONSTRUCTION FORMAT:
"Upon completion of this activity, participants will be able to [ACTION VERB at Moore Level] [SPECIFIC CLINICAL BEHAVIOR] for [PATIENT POPULATION] to [INTENDED OUTCOME]."

PROHIBITED OBJECTIVE PATTERNS:
- "Understand the mechanism of..." (passive, unmeasurable)
- "Appreciate the importance of..." (attitudinal, unmeasurable)
- "Be aware of..." (passive, no action)
- "Learn about..." (process-focused)
- "Review the guidelines for..." (no clinical action)
- "Discuss options with patients" (too vague)

OUTPUT REQUIREMENTS:
- Minimum 6 distinct objectives
- Maximum 10 objectives (focus over breadth)
- 60%+ of objectives at Level 4 or higher
- Every identified gap addressed by ≥1 objective
- Every objective has measurement methodology
- Every objective explicitly links to patient outcome"""


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="plan_distribution_node", run_type="chain")
async def plan_distribution_node(state: LearningObjectivesState) -> dict:
    """Plan objective distribution based on target Moore level."""
    
    target_level = state.get("moore_level_target", "Level 5")
    gap_report = state.get("gap_analysis_report", {})
    gaps = gap_report.get("gaps", [])
    audience = state.get("target_audience", "")
    
    # Determine distribution based on target
    if "5" in target_level:
        distribution = {
            "primary_level": "Level 5",
            "level_5_target": "40-60%",
            "level_4_target": "30-40%",
            "level_3_target": "10-20%"
        }
    else:
        distribution = {
            "primary_level": "Level 4",
            "level_4_target": "60-80%",
            "level_3b_target": "10-20%",
            "level_3a_target": "10-20%"
        }
    
    # Map gaps to objectives needed
    gap_objectives_map = []
    priority_gaps = gap_report.get("recommendations", {}).get("primary_focus", [])
    
    for gap in gaps:
        gap_id = gap.get("gap_id", "")
        barrier_type = gap.get("root_causes", {}).get("primary_barrier_type", "knowledge")
        is_priority = gap_id in priority_gaps
        
        # Suggest Moore level based on barrier type
        if barrier_type == "knowledge":
            suggested_level = "Level 3A or Level 4"
        elif barrier_type == "skill":
            suggested_level = "Level 3B or Level 4"
        elif barrier_type == "attitude":
            suggested_level = "Level 4 or Level 5"
        else:  # system or mixed
            suggested_level = "Level 5"
        
        gap_objectives_map.append({
            "gap_id": gap_id,
            "gap_title": gap.get("title", ""),
            "barrier_type": barrier_type,
            "suggested_level": suggested_level,
            "is_priority": is_priority,
            "objectives_needed": 2 if is_priority else 1
        })
    
    distribution_plan = {
        **distribution,
        "gap_objectives_map": gap_objectives_map,
        "total_objectives_planned": sum(g["objectives_needed"] for g in gap_objectives_map),
        "rationale": f"Targeting {target_level} for {audience} based on gap barrier analysis"
    }
    
    return {
        "distribution_plan": distribution_plan,
        "total_tokens": state.get("total_tokens", 0),
        "total_cost": state.get("total_cost", 0.0)
    }


@traceable(name="draft_level_5_objectives_node", run_type="chain")
async def draft_level_5_objectives_node(state: LearningObjectivesState) -> dict:
    """Draft Level 5 (Performance) objectives."""
    
    disease = state.get("disease_state", "")
    audience = state.get("target_audience", "")
    gap_report = state.get("gap_analysis_report", {})
    gaps = gap_report.get("gaps", [])
    distribution = state.get("distribution_plan", {})
    
    system = f"""{LEARNING_OBJECTIVES_SYSTEM_PROMPT}

You are drafting LEVEL 5 (Performance) objectives. These target actual behavior change in practice.

LEVEL 5 VERBS (must use one): prescribe, order, initiate, discontinue, adjust, monitor, refer, screen, counsel, document, implement, integrate, incorporate

Return a JSON array:
{{
    "level_5_objectives": [
        {{
            "objective_id": "OBJ-001",
            "objective_text": "Upon completion of this activity, participants will be able to [VERB] [specific behavior] for [population] to [outcome].",
            "moore_classification": {{
                "level": "Level 5",
                "level_name": "Performance",
                "action_verb": "initiate",
                "verb_rationale": "Why this verb is appropriate"
            }},
            "gap_alignment": {{
                "gap_id": "GAP-001",
                "gap_title": "Title of gap",
                "alignment_explanation": "How this addresses the gap"
            }},
            "measurement": {{
                "primary_method": "Commitment-to-change with follow-up",
                "timing": "Immediately + 60 days post-activity",
                "success_criteria": "≥70% report implementing change",
                "data_source": "Self-reported practice change survey"
            }},
            "patient_outcome_link": {{
                "linked_outcome": "Specific patient outcome",
                "mechanism": "How behavior change leads to outcome"
            }}
        }}
    ]
}}"""
    
    # Get priority gaps that need Level 5 objectives
    priority_gaps = [g for g in gaps if g.get("gap_id") in 
                     gap_report.get("recommendations", {}).get("primary_focus", [])]
    
    prompt = f"""Draft 3-5 Level 5 (Performance) objectives for {disease} CME targeting {audience}.

PRIORITY GAPS TO ADDRESS:
{json.dumps(priority_gaps, indent=2)[:4000]}

Create objectives that target actual practice behavior change. Each must:
- Use a Level 5 verb (prescribe, order, initiate, etc.)
- Specify a concrete clinical action
- Define the patient population
- Link to patient outcomes
- Include measurement at immediate + 60 days

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "level_5_objectives"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            level_5 = data.get("level_5_objectives", [])
        else:
            level_5 = []
    except json.JSONDecodeError:
        level_5 = []
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "level_5_objectives": level_5,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="draft_level_4_objectives_node", run_type="chain")
async def draft_level_4_objectives_node(state: LearningObjectivesState) -> dict:
    """Draft Level 4 (Competence) objectives."""
    
    disease = state.get("disease_state", "")
    audience = state.get("target_audience", "")
    gap_report = state.get("gap_analysis_report", {})
    gaps = gap_report.get("gaps", [])
    level_5_objectives = state.get("level_5_objectives", [])
    
    # Find gaps not yet covered
    covered_gaps = {obj.get("gap_alignment", {}).get("gap_id") for obj in level_5_objectives}
    uncovered_gaps = [g for g in gaps if g.get("gap_id") not in covered_gaps]
    
    system = f"""{LEARNING_OBJECTIVES_SYSTEM_PROMPT}

You are drafting LEVEL 4 (Competence) objectives. These target clinical reasoning ability.

LEVEL 4 VERBS (must use one): select, determine, differentiate, assess, evaluate, calculate, interpret, formulate, develop, design

Return a JSON array:
{{
    "level_4_objectives": [
        {{
            "objective_id": "OBJ-004",
            "objective_text": "Upon completion of this activity, participants will be able to [VERB] [clinical decision/reasoning] for [population] to [outcome].",
            "moore_classification": {{
                "level": "Level 4",
                "level_name": "Competence",
                "action_verb": "differentiate",
                "verb_rationale": "Why this verb is appropriate"
            }},
            "gap_alignment": {{
                "gap_id": "GAP-002",
                "gap_title": "Title of gap",
                "alignment_explanation": "How this addresses the gap"
            }},
            "measurement": {{
                "primary_method": "Case-based assessment",
                "timing": "Pre/post assessment + 30-day retention",
                "success_criteria": "≥80% correct on case scenarios",
                "data_source": "Embedded case vignettes"
            }},
            "patient_outcome_link": {{
                "linked_outcome": "Specific patient outcome",
                "mechanism": "How competence leads to outcome"
            }}
        }}
    ]
}}"""
    
    prompt = f"""Draft 2-4 Level 4 (Competence) objectives for {disease} CME targeting {audience}.

GAPS NEEDING COVERAGE (not yet addressed by Level 5):
{json.dumps(uncovered_gaps, indent=2)[:3000]}

ALL GAPS FOR REFERENCE:
{json.dumps([{"gap_id": g.get("gap_id"), "title": g.get("title"), "barrier": g.get("root_causes", {}).get("primary_barrier_type")} for g in gaps], indent=2)}

Create objectives that target clinical reasoning and decision-making. Each must:
- Use a Level 4 verb (select, determine, differentiate, etc.)
- Focus on decision-making ability
- Include case-based measurement
- Link to patient outcomes

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "level_4_objectives"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            level_4 = data.get("level_4_objectives", [])
        else:
            level_4 = []
    except json.JSONDecodeError:
        level_4 = []
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "level_4_objectives": level_4,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="draft_level_3_objectives_node", run_type="chain")
async def draft_level_3_objectives_node(state: LearningObjectivesState) -> dict:
    """Draft Level 3 objectives only if gaps remain uncovered."""
    
    disease = state.get("disease_state", "")
    audience = state.get("target_audience", "")
    gap_report = state.get("gap_analysis_report", {})
    gaps = gap_report.get("gaps", [])
    level_5_objectives = state.get("level_5_objectives", [])
    level_4_objectives = state.get("level_4_objectives", [])
    
    # Find still-uncovered gaps
    covered_gaps = set()
    for obj in level_5_objectives + level_4_objectives:
        covered_gaps.add(obj.get("gap_alignment", {}).get("gap_id"))
    
    uncovered_gaps = [g for g in gaps if g.get("gap_id") not in covered_gaps]
    
    # Only create Level 3 if there are uncovered gaps with knowledge barriers
    knowledge_gaps = [g for g in uncovered_gaps 
                      if g.get("root_causes", {}).get("primary_barrier_type") == "knowledge"]
    
    if not knowledge_gaps:
        return {
            "level_3_objectives": [],
            "total_tokens": state.get("total_tokens", 0),
            "total_cost": state.get("total_cost", 0.0)
        }
    
    system = f"""{LEARNING_OBJECTIVES_SYSTEM_PROMPT}

You are drafting LEVEL 3 objectives. These should be used sparingly (<20% of total).

LEVEL 3B VERBS: perform, execute, demonstrate, apply, use, administer, conduct
LEVEL 3A VERBS: identify, recognize, describe, explain

Return a JSON array:
{{
    "level_3_objectives": [
        {{
            "objective_id": "OBJ-007",
            "objective_text": "Upon completion of this activity, participants will be able to [VERB] [knowledge/skill] for [population] to [outcome].",
            "moore_classification": {{
                "level": "Level 3A or 3B",
                "level_name": "Declarative or Procedural Knowledge",
                "action_verb": "identify",
                "verb_rationale": "Why this foundational objective is needed"
            }},
            "gap_alignment": {{ ... }},
            "measurement": {{ ... }},
            "patient_outcome_link": {{ ... }}
        }}
    ]
}}"""
    
    prompt = f"""Draft 1-2 Level 3 objectives for {disease} CME targeting {audience}.
These are for foundational knowledge gaps only. Keep to <20% of total objectives.

KNOWLEDGE GAPS NEEDING COVERAGE:
{json.dumps(knowledge_gaps, indent=2)[:2000]}

Create objectives that build foundational knowledge/skill. Each must:
- Use appropriate Level 3 verb
- Be foundational to higher-level objectives
- Still link to patient outcomes

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "level_3_objectives"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            level_3 = data.get("level_3_objectives", [])
        else:
            level_3 = []
    except json.JSONDecodeError:
        level_3 = []
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "level_3_objectives": level_3,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="build_coverage_matrix_node", run_type="chain")
async def build_coverage_matrix_node(state: LearningObjectivesState) -> dict:
    """Build gap coverage matrix and compile all objectives."""
    
    gap_report = state.get("gap_analysis_report", {})
    gaps = gap_report.get("gaps", [])
    
    # Compile all objectives
    all_objectives = (
        state.get("level_5_objectives", []) +
        state.get("level_4_objectives", []) +
        state.get("level_3_objectives", [])
    )
    
    # Renumber objectives sequentially
    for i, obj in enumerate(all_objectives, 1):
        obj["objective_id"] = f"OBJ-{i:03d}"
    
    # Build coverage matrix
    coverage_matrix = []
    for gap in gaps:
        gap_id = gap.get("gap_id", "")
        addressing_objectives = [
            obj["objective_id"]
            for obj in all_objectives
            if obj.get("gap_alignment", {}).get("gap_id") == gap_id
        ]
        
        if len(addressing_objectives) == 0:
            completeness = "NOT COVERED"
        elif len(addressing_objectives) == 1:
            completeness = "Minimally covered"
        else:
            completeness = "Well covered"
        
        coverage_matrix.append({
            "gap_id": gap_id,
            "gap_title": gap.get("title", ""),
            "objectives_addressing": addressing_objectives,
            "coverage_completeness": completeness
        })
    
    return {
        "all_objectives": all_objectives,
        "gap_coverage_matrix": coverage_matrix,
        "objectives_count": len(all_objectives),
        "total_tokens": state.get("total_tokens", 0),
        "total_cost": state.get("total_cost", 0.0)
    }


@traceable(name="assemble_objectives_report_node", run_type="chain")
async def assemble_objectives_report_node(state: LearningObjectivesState) -> dict:
    """Assemble the final learning objectives report."""
    
    all_objectives = state.get("all_objectives", [])
    coverage_matrix = state.get("gap_coverage_matrix", [])
    distribution = state.get("distribution_plan", {})
    
    # Calculate level distribution
    level_counts = {"level_3a": 0, "level_3b": 0, "level_4": 0, "level_5": 0, "level_6": 0}
    for obj in all_objectives:
        level = obj.get("moore_classification", {}).get("level", "").lower().replace(" ", "_")
        if "5" in level:
            level_counts["level_5"] += 1
        elif "4" in level:
            level_counts["level_4"] += 1
        elif "3b" in level:
            level_counts["level_3b"] += 1
        elif "3a" in level or "3" in level:
            level_counts["level_3a"] += 1
    
    # Determine primary level
    primary_level = max(level_counts, key=level_counts.get)
    
    # Build measurement plan summary
    measurement_plan = {
        "immediate_assessment": [],
        "thirty_day_followup": [],
        "sixty_to_ninety_day_followup": [],
        "outcome_tracking": []
    }
    
    for obj in all_objectives:
        obj_id = obj.get("objective_id", "")
        timing = obj.get("measurement", {}).get("timing", "").lower()
        
        if "immediate" in timing or "pre/post" in timing:
            measurement_plan["immediate_assessment"].append(obj_id)
        if "30" in timing or "thirty" in timing:
            measurement_plan["thirty_day_followup"].append(obj_id)
        if "60" in timing or "90" in timing or "sixty" in timing:
            measurement_plan["sixty_to_ninety_day_followup"].append(obj_id)
    
    report = {
        "metadata": {
            "agent_version": "2.0",
            "execution_timestamp": datetime.now().isoformat(),
            "objectives_count": len(all_objectives),
            "primary_moore_level": primary_level.replace("_", " ").title(),
            "model_used": "claude-sonnet-4",
            "total_tokens": state.get("total_tokens", 0),
            "total_cost": state.get("total_cost", 0.0)
        },
        "framework_application": {
            "target_level": distribution.get("primary_level", "Level 5"),
            "level_distribution": level_counts,
            "distribution_rationale": distribution.get("rationale", "")
        },
        "objectives": all_objectives,
        "gap_coverage_matrix": coverage_matrix,
        "measurement_plan_summary": measurement_plan
    }
    
    return {
        "learning_objectives_report": report,
        "messages": [HumanMessage(content=f"Learning objectives complete: {len(all_objectives)} objectives created, {level_counts['level_5'] + level_counts['level_4']} at Level 4+")]
    }


@traceable(name="render_objectives_document_node", run_type="chain")
async def render_objectives_document_node(state: LearningObjectivesState) -> dict:
    """Render the objectives as a readable document."""
    
    disease = state.get("disease_state", "")
    report = state.get("learning_objectives_report", {})
    
    system = """You are a medical education writer creating a learning objectives document.

FORMATTING RULES:
- Use markdown headers
- Present each objective clearly numbered
- Include Moore level and verb for each
- Show gap alignment
- Include measurement plan
- Write in professional CME format

STRUCTURE:
1. Executive Summary (target level, distribution)
2. Learning Objectives (numbered list with full details)
3. Gap Coverage Matrix
4. Measurement Plan

Do NOT use:
- Em dashes (—)
- Bullet points for the objectives themselves (use numbered)
- Vague language
"""
    
    prompt = f"""Create a learning objectives document for {disease} CME.

LEARNING OBJECTIVES DATA:
{json.dumps(report, indent=2)[:12000]}

Present objectives professionally with:
- Clear numbering
- Moore level designation
- Gap alignment
- Measurement methodology"""

    result = await llm.generate(system, prompt, {"step": "render_document"})
    
    document = result["content"]
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "learning_objectives_document": document,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


# =============================================================================
# BUILD GRAPH
# =============================================================================

def create_learning_objectives_graph() -> StateGraph:
    """Create the Learning Objectives Agent graph."""
    
    graph = StateGraph(LearningObjectivesState)
    
    # Add nodes
    graph.add_node("plan_distribution", plan_distribution_node)
    graph.add_node("draft_level_5", draft_level_5_objectives_node)
    graph.add_node("draft_level_4", draft_level_4_objectives_node)
    graph.add_node("draft_level_3", draft_level_3_objectives_node)
    graph.add_node("build_coverage_matrix", build_coverage_matrix_node)
    graph.add_node("assemble_report", assemble_objectives_report_node)
    graph.add_node("render_document", render_objectives_document_node)
    
    # Flow: sequential drafting by level
    graph.set_entry_point("plan_distribution")
    
    graph.add_edge("plan_distribution", "draft_level_5")
    graph.add_edge("draft_level_5", "draft_level_4")
    graph.add_edge("draft_level_4", "draft_level_3")
    graph.add_edge("draft_level_3", "build_coverage_matrix")
    graph.add_edge("build_coverage_matrix", "assemble_report")
    graph.add_edge("assemble_report", "render_document")
    graph.add_edge("render_document", END)
    
    return graph


# Compile for LangGraph Cloud
graph = create_learning_objectives_graph().compile()


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        # Mock gap analysis data
        mock_gap_report = {
            "gaps": [
                {
                    "gap_id": "GAP-001",
                    "title": "Suboptimal SGLT2 Inhibitor Initiation",
                    "root_causes": {"primary_barrier_type": "knowledge"},
                    "evidence": {"practice_guideline_delta": "77%"}
                },
                {
                    "gap_id": "GAP-002",
                    "title": "HFpEF Recognition Gap",
                    "root_causes": {"primary_barrier_type": "skill"},
                    "evidence": {"practice_guideline_delta": "45%"}
                },
                {
                    "gap_id": "GAP-003",
                    "title": "Inadequate Dose Optimization",
                    "root_causes": {"primary_barrier_type": "attitude"},
                    "evidence": {"practice_guideline_delta": "60%"}
                }
            ],
            "recommendations": {
                "primary_focus": ["GAP-001", "GAP-003"],
                "secondary_focus": ["GAP-002"]
            }
        }
        
        test_state = {
            "gap_analysis_report": mock_gap_report,
            "therapeutic_area": "cardiology",
            "disease_state": "heart failure",
            "target_audience": "cardiologists",
            "educational_format": "live symposium",
            "moore_level_target": "Level 5",
            "outcome_goals": ["Improve GDMT initiation rates"],
            "messages": [],
            "errors": [],
            "total_tokens": 0,
            "total_cost": 0.0
        }
        
        result = await graph.ainvoke(test_state)
        
        print(f"\n=== LEARNING OBJECTIVES RESULT ===")
        print(f"Objectives created: {result.get('objectives_count', 0)}")
        print(f"Total tokens: {result.get('total_tokens', 0)}")
        print(f"Total cost: ${result.get('total_cost', 0):.4f}")
        
        report = result.get("learning_objectives_report", {})
        dist = report.get("framework_application", {}).get("level_distribution", {})
        print(f"\n=== LEVEL DISTRIBUTION ===")
        for level, count in dist.items():
            print(f"- {level}: {count}")
    
    asyncio.run(test())
