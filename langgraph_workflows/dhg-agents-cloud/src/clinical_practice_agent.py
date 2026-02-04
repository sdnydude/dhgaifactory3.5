"""
Clinical Practice Agent - Agent #3
===================================
Analyzes real-world clinical practice patterns, identifies deviations from 
guideline-recommended care, and characterizes barriers to optimal management.

LangGraph Cloud Ready:
- Produces structured practice analysis + prose document
- Input from: Intake form (runs parallel with Research Agent)
- Output to: Gap Analysis Agent, Needs Assessment Agent
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
# CONFIGURATION
# =============================================================================

class BarrierType(str, Enum):
    """Barrier classification framework."""
    KNOWLEDGE_AWARENESS = "knowledge_awareness"
    KNOWLEDGE_FAMILIARITY = "knowledge_familiarity"
    KNOWLEDGE_CURRENCY = "knowledge_currency"
    SKILL_PROCEDURAL = "skill_procedural"
    SKILL_COMMUNICATION = "skill_communication"
    SKILL_IMPLEMENTATION = "skill_implementation"
    ATTITUDE_DISAGREEMENT = "attitude_disagreement"
    ATTITUDE_INERTIA = "attitude_inertia"
    ATTITUDE_PRIORITY = "attitude_priority"
    SYSTEM_TIME = "system_time"
    SYSTEM_ACCESS = "system_access"
    SYSTEM_COST = "system_cost"
    SYSTEM_WORKFLOW = "system_workflow"
    PATIENT_ADHERENCE = "patient_adherence"
    PATIENT_ACCESS = "patient_access"
    PATIENT_LITERACY = "patient_literacy"
    PATIENT_PREFERENCE = "patient_preference"


# =============================================================================
# STATE DEFINITION
# =============================================================================

class ClinicalPracticeState(TypedDict):
    # === INPUT (from intake form) ===
    therapeutic_area: str
    disease_state: str
    target_audience: str
    practice_settings: Optional[List[str]]
    geographic_focus: str
    known_gaps: Optional[List[str]]
    known_barriers: Optional[List[str]]
    
    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    
    # Section-specific data
    standard_of_care_data: Dict[str, Any]
    real_world_practice_data: Dict[str, Any]
    practice_barriers_data: Dict[str, Any]
    specialty_perspectives_data: Dict[str, Any]
    setting_variations_data: Dict[str, Any]
    
    # Citations
    citations: List[Dict[str, Any]]
    
    # === OUTPUT ===
    clinical_practice_report: Dict[str, Any]
    clinical_practice_document: str
    
    # === METADATA ===
    sources_analyzed: int
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
    
    @traceable(name="clinical_practice_llm_call", run_type="llm")
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
# PERPLEXITY CLIENT
# =============================================================================

class PerplexityClient:
    """Perplexity API for practice data search."""
    
    ACADEMIC_DOMAINS = [
        "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov", "jamanetwork.com",
        "nejm.org", "thelancet.com", "bmj.com", "acc.org", "heart.org",
        "cms.gov", "ahrq.gov", "qualitynet.cms.gov"
    ]
    
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
    
    @traceable(name="perplexity_practice_search", run_type="retriever")
    async def search(self, query: str) -> dict:
        """Search for practice pattern data."""
        if not self.api_key:
            return {"content": "", "citations": []}
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = """You are a clinical practice analyst.
Focus on real-world practice data from:
- Disease registries (PINNACLE, GWTG-HF, NCDR, etc.)
- Claims database analyses
- Physician practice surveys
- Quality measure performance data
Include specific utilization rates, adherence percentages, and outcome data.
Cite sources with author/organization and year."""
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "return_citations": True,
            "search_domain_filter": self.ACADEMIC_DOMAINS
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return {
                "content": data["choices"][0]["message"]["content"],
                "citations": data.get("citations", [])
            }


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

CLINICAL_PRACTICE_SYSTEM_PROMPT = """You are a clinical practice analyst examining real-world care patterns for continuing medical education needs assessment. Your analysis must:

1. GROUND IN REALITY: Focus on what actually happens in practice, not what guidelines recommend
2. QUANTIFY GAPS: Use registry data, claims analyses, and surveys to show practice-guideline gaps
3. IDENTIFY BARRIERS: Categorize barriers as clinician, system, or patient-level
4. ACKNOWLEDGE VARIATION: Recognize that practice varies by setting, specialty, and region
5. REMAIN OBJECTIVE: Present challenges without blame or promotional intent

CRITICAL REQUIREMENTS:
- Distinguish clearly between guideline recommendations and actual practice
- Include specific utilization rates and adherence data where available
- Categorize every barrier by type (knowledge, skill, attitude, system, patient)
- Reference real-world evidence (registries, claims, surveys) not just trials
- Note variations across practice settings

BARRIER CATEGORIZATION FRAMEWORK:
- KNOWLEDGE: Clinician doesn't know (awareness, familiarity, currency)
- SKILL: Clinician doesn't know how (procedural, communication, implementation)
- ATTITUDE: Clinician doesn't agree or prioritize (disagreement, inertia, priority)
- SYSTEM: External factors prevent action (time, access, cost, workflow)
- PATIENT: Patient-level factors (adherence, access, preferences, literacy)

PROHIBITED:
- Blaming clinicians for poor outcomes
- Ignoring systemic factors
- Promotional framing of any treatment
- Unsupported assumptions about practice
- Generalizing from single-site studies"""


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="analyze_standard_of_care_node", run_type="chain")
async def analyze_standard_of_care_node(state: ClinicalPracticeState) -> dict:
    """Define the guideline-recommended standard of care."""
    
    disease = state.get("disease_state", "")
    audience = state.get("target_audience", "")
    
    perplexity = PerplexityClient()
    soc_result = await perplexity.search(
        f"What are the current guideline-recommended diagnostic pathways and treatment algorithms for {disease}? "
        f"Include key decision points, first-line treatments, escalation criteria, monitoring requirements, "
        f"and established quality measures with target benchmarks. Focus on major society guidelines."
    )
    
    system = f"""{CLINICAL_PRACTICE_SYSTEM_PROMPT}

You are defining STANDARD OF CARE. Return a JSON object:
{{
    "diagnostic_pathway": {{
        "recommended_approach": "description with guideline citation",
        "key_decision_points": ["list of critical decisions"],
        "time_to_diagnosis_target": "target timeframe with source"
    }},
    "treatment_algorithm": {{
        "first_line": [{{"therapy": "name", "indication": "when to use", "source": "guideline"}}],
        "escalation_criteria": ["list of criteria for step-up"],
        "monitoring_requirements": ["list of monitoring parameters"]
    }},
    "quality_metrics": {{
        "established_measures": [{{"measure": "name", "source": "CMS/HEDIS/MIPS", "target": "benchmark"}}],
        "target_benchmarks": {{"metric_name": "target_value"}}
    }}
}}"""
    
    prompt = f"""Define the guideline-recommended standard of care for {disease}.
Target audience: {audience}

GUIDELINE DATA:
{soc_result.get('content', '')}

Return ONLY valid JSON. Be specific about guideline sources and years."""

    result = await llm.generate(system, prompt, {"step": "standard_of_care"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            soc_data = json.loads(json_match.group())
        else:
            soc_data = {"error": "Failed to parse standard of care data"}
    except json.JSONDecodeError:
        soc_data = {"error": "Invalid JSON in standard of care response"}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_sources = state.get("sources_analyzed", 0)
    
    return {
        "standard_of_care_data": soc_data,
        "sources_analyzed": prev_sources + 1,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="analyze_real_world_practice_node", run_type="chain")
async def analyze_real_world_practice_node(state: ClinicalPracticeState) -> dict:
    """Analyze actual real-world practice patterns vs guidelines."""
    
    disease = state.get("disease_state", "")
    soc = state.get("standard_of_care_data", {})
    
    perplexity = PerplexityClient()
    rwp_result = await perplexity.search(
        f"What is the real-world utilization and adherence data for {disease} treatments? "
        f"Include registry data (PINNACLE, GWTG-HF, NCDR), claims analyses, time to diagnosis, "
        f"actual prescribing rates, dose optimization rates, and quality measure performance. "
        f"Focus on gaps between recommended and actual care."
    )
    
    system = f"""{CLINICAL_PRACTICE_SYSTEM_PROMPT}

You are analyzing REAL-WORLD PRACTICE patterns. Return a JSON object:
{{
    "diagnostic_patterns": {{
        "actual_vs_recommended": "description with data",
        "common_deviations": ["list of ways practice differs from guidelines"],
        "time_to_diagnosis_actual": "actual timeframe with source"
    }},
    "treatment_patterns": {{
        "prescribing_data": [{{
            "medication_class": "name",
            "guideline_rec": "what guidelines say",
            "actual_utilization": "percentage with source",
            "gap_magnitude": "how big the gap is"
        }}],
        "utilization_rates": {{"treatment": "rate_with_source"}},
        "adherence_rates": "overall adherence data with source"
    }},
    "outcome_gaps": {{
        "quality_measure_performance": {{"measure": "actual_vs_target"}},
        "outcome_disparities": ["list of disparity findings"]
    }}
}}"""
    
    prompt = f"""Analyze real-world practice patterns for {disease}.

STANDARD OF CARE (for comparison):
{json.dumps(soc, indent=2)[:2000]}

REAL-WORLD DATA:
{rwp_result.get('content', '')}

Return ONLY valid JSON. Quantify all gaps with specific percentages and sources."""

    result = await llm.generate(system, prompt, {"step": "real_world_practice"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            rwp_data = json.loads(json_match.group())
        else:
            rwp_data = {"error": "Failed to parse real-world practice data"}
    except json.JSONDecodeError:
        rwp_data = {"error": "Invalid JSON in practice response"}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_sources = state.get("sources_analyzed", 0)
    
    return {
        "real_world_practice_data": rwp_data,
        "sources_analyzed": prev_sources + 1,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="identify_barriers_node", run_type="chain")
async def identify_barriers_node(state: ClinicalPracticeState) -> dict:
    """Identify and categorize barriers to optimal care."""
    
    disease = state.get("disease_state", "")
    audience = state.get("target_audience", "")
    known_barriers = state.get("known_barriers", [])
    
    perplexity = PerplexityClient()
    barriers_result = await perplexity.search(
        f"What are the barriers to optimal {disease} care for {audience}? "
        f"Include clinician barriers (knowledge, skill, attitude), system barriers "
        f"(time, access, cost, workflow), and patient barriers (adherence, access, literacy). "
        f"Reference physician surveys, needs assessments, and barrier studies."
    )
    
    system = f"""{CLINICAL_PRACTICE_SYSTEM_PROMPT}

You are identifying PRACTICE BARRIERS. Use this categorization framework:
- KNOWLEDGE: awareness, familiarity, currency (education-addressable)
- SKILL: procedural, communication, implementation (education+practice addressable)
- ATTITUDE: disagreement, inertia, priority (partially education-addressable)
- SYSTEM: time, access, cost, workflow (not education-addressable)
- PATIENT: adherence, access, literacy, preference (variable)

Return a JSON object:
{{
    "clinician_barriers": {{
        "knowledge_gaps": [{{
            "barrier": "specific gap",
            "category": "KNOWLEDGE - Awareness|Familiarity|Currency",
            "evidence": "source and data",
            "education_addressable": true
        }}],
        "skill_gaps": [{{
            "barrier": "specific gap",
            "category": "SKILL - Procedural|Communication|Implementation",
            "evidence": "source and data",
            "education_addressable": true
        }}],
        "attitude_barriers": [{{
            "barrier": "specific barrier",
            "category": "ATTITUDE - Disagreement|Inertia|Priority",
            "evidence": "source and data",
            "education_addressable": "partially"
        }}]
    }},
    "system_barriers": [{{
        "barrier": "specific barrier",
        "category": "SYSTEM - Time|Access|Cost|Workflow",
        "evidence": "source and data",
        "education_addressable": false
    }}],
    "patient_barriers": [{{
        "barrier": "specific barrier",
        "category": "PATIENT - Adherence|Access|Literacy|Preference",
        "evidence": "source and data"
    }}]
}}"""
    
    known_context = f"\nKNOWN BARRIERS TO CONSIDER:\n- " + "\n- ".join(known_barriers) if known_barriers else ""
    
    prompt = f"""Identify barriers to optimal {disease} care for {audience}.
{known_context}

BARRIER RESEARCH:
{barriers_result.get('content', '')}

Return ONLY valid JSON. Every barrier must be categorized and have evidence."""

    result = await llm.generate(system, prompt, {"step": "barriers"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            barriers_data = json.loads(json_match.group())
        else:
            barriers_data = {"error": "Failed to parse barriers data"}
    except json.JSONDecodeError:
        barriers_data = {"error": "Invalid JSON in barriers response"}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_sources = state.get("sources_analyzed", 0)
    
    return {
        "practice_barriers_data": barriers_data,
        "sources_analyzed": prev_sources + 1,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="analyze_specialty_perspectives_node", run_type="chain")
async def analyze_specialty_perspectives_node(state: ClinicalPracticeState) -> dict:
    """Analyze specialty-specific perspectives and care coordination."""
    
    disease = state.get("disease_state", "")
    audience = state.get("target_audience", "")
    
    perplexity = PerplexityClient()
    specialty_result = await perplexity.search(
        f"How do different specialties (primary care, specialists) manage {disease}? "
        f"Include referral patterns, care coordination gaps, specialist capacity issues, "
        f"and handoff challenges between care settings."
    )
    
    system = f"""{CLINICAL_PRACTICE_SYSTEM_PROMPT}

You are analyzing SPECIALTY PERSPECTIVES. Return a JSON object:
{{
    "primary_care": {{
        "role": "description of PCP role",
        "challenges": ["list of challenges"],
        "referral_patterns": "when and how often referrals happen"
    }},
    "specialists": {{
        "role": "description of specialist role",
        "capacity_issues": "access and availability data",
        "coordination_gaps": "gaps in communication/handoff"
    }},
    "care_team": {{
        "collaboration_patterns": "how team works together",
        "handoff_issues": ["list of handoff problems"]
    }}
}}"""
    
    prompt = f"""Analyze specialty perspectives for {disease} care.
Target audience focus: {audience}

SPECIALTY DATA:
{specialty_result.get('content', '')}

Return ONLY valid JSON. Include specific data on referral rates and coordination."""

    result = await llm.generate(system, prompt, {"step": "specialty_perspectives"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            specialty_data = json.loads(json_match.group())
        else:
            specialty_data = {"error": "Failed to parse specialty data"}
    except json.JSONDecodeError:
        specialty_data = {"error": "Invalid JSON in specialty response"}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_sources = state.get("sources_analyzed", 0)
    
    return {
        "specialty_perspectives_data": specialty_data,
        "sources_analyzed": prev_sources + 1,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="analyze_setting_variations_node", run_type="chain")
async def analyze_setting_variations_node(state: ClinicalPracticeState) -> dict:
    """Analyze practice variations by setting."""
    
    disease = state.get("disease_state", "")
    settings = state.get("practice_settings", [])
    geographic = state.get("geographic_focus", "United States")
    
    perplexity = PerplexityClient()
    settings_result = await perplexity.search(
        f"How does {disease} care vary between academic and community settings, "
        f"urban and rural areas, and resource-rich vs resource-limited environments? "
        f"Include specific data on outcome differences and access disparities in {geographic}."
    )
    
    system = f"""{CLINICAL_PRACTICE_SYSTEM_PROMPT}

You are analyzing SETTING VARIATIONS. Return a JSON object:
{{
    "academic_vs_community": "comparison with specific data",
    "urban_vs_rural": "comparison with specific data on access and outcomes",
    "resource_rich_vs_limited": "comparison with specific data"
}}"""
    
    settings_context = f"\nPRACTICE SETTINGS OF INTEREST: {', '.join(settings)}" if settings else ""
    
    prompt = f"""Analyze practice setting variations for {disease} in {geographic}.
{settings_context}

SETTING DATA:
{settings_result.get('content', '')}

Return ONLY valid JSON with specific comparative data."""

    result = await llm.generate(system, prompt, {"step": "setting_variations"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            settings_data = json.loads(json_match.group())
        else:
            settings_data = {"error": "Failed to parse settings data"}
    except json.JSONDecodeError:
        settings_data = {"error": "Invalid JSON in settings response"}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_sources = state.get("sources_analyzed", 0)
    
    return {
        "setting_variations_data": settings_data,
        "sources_analyzed": prev_sources + 1,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="assemble_clinical_report_node", run_type="chain")
async def assemble_clinical_report_node(state: ClinicalPracticeState) -> dict:
    """Assemble the final clinical practice report."""
    
    report = {
        "metadata": {
            "agent_version": "2.0",
            "execution_timestamp": datetime.now().isoformat(),
            "sources_analyzed": state.get("sources_analyzed", 0),
            "model_used": "claude-sonnet-4",
            "total_tokens": state.get("total_tokens", 0),
            "total_cost": state.get("total_cost", 0.0)
        },
        "standard_of_care": state.get("standard_of_care_data", {}),
        "real_world_practice": state.get("real_world_practice_data", {}),
        "practice_barriers": state.get("practice_barriers_data", {}),
        "specialty_perspectives": state.get("specialty_perspectives_data", {}),
        "setting_variations": state.get("setting_variations_data", {}),
        "citations": state.get("citations", [])
    }
    
    return {
        "clinical_practice_report": report,
        "messages": [HumanMessage(content=f"Clinical practice analysis complete: {state.get('sources_analyzed', 0)} sources analyzed")]
    }


@traceable(name="render_clinical_document_node", run_type="chain")
async def render_clinical_document_node(state: ClinicalPracticeState) -> dict:
    """Render the report as a readable prose document."""
    
    disease = state.get("disease_state", "")
    report = state.get("clinical_practice_report", {})
    
    system = """You are a medical writer converting structured clinical practice data into a cohesive, readable report.

FORMATTING RULES:
- Use markdown headers (## for main sections)
- Write flowing prose paragraphs, not bullet points
- Include inline citations in format (Source, Year)
- 80%+ prose density
- Active voice
- Specific numbers throughout

STRUCTURE:
1. Executive Summary (key practice gaps)
2. Standard of Care (guideline recommendations)
3. Real-World Practice Patterns
4. Practice-Guideline Gaps
5. Barriers to Optimal Care
   - Clinician Barriers (Knowledge, Skill, Attitude)
   - System Barriers
   - Patient Barriers
6. Specialty Perspectives
7. Setting Variations
8. Implications for Education

Do NOT use:
- Em dashes (—)
- "It's important to note"
- "Studies show" without naming the study
- Bullet points in the main text
- Colons in prose (except citations)
"""
    
    prompt = f"""Convert this clinical practice data on {disease} into a cohesive report.

CLINICAL PRACTICE DATA:
{json.dumps(report, indent=2)[:12000]}

Write a complete, readable report following the structure above. Emphasize the gaps between guidelines and practice, and clearly categorize all barriers."""

    result = await llm.generate(system, prompt, {"step": "render_document"})
    
    document = result["content"]
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "clinical_practice_document": document,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


# =============================================================================
# BUILD GRAPH
# =============================================================================

def create_clinical_practice_graph() -> StateGraph:
    """Create the Clinical Practice Agent graph."""
    
    graph = StateGraph(ClinicalPracticeState)
    
    # Add nodes
    graph.add_node("analyze_standard_of_care", analyze_standard_of_care_node)
    graph.add_node("analyze_real_world_practice", analyze_real_world_practice_node)
    graph.add_node("identify_barriers", identify_barriers_node)
    graph.add_node("analyze_specialty_perspectives", analyze_specialty_perspectives_node)
    graph.add_node("analyze_setting_variations", analyze_setting_variations_node)
    graph.add_node("assemble_report", assemble_clinical_report_node)
    graph.add_node("render_document", render_clinical_document_node)
    
    # Flow: sequential analysis -> assembly -> render
    graph.set_entry_point("analyze_standard_of_care")
    
    graph.add_edge("analyze_standard_of_care", "analyze_real_world_practice")
    graph.add_edge("analyze_real_world_practice", "identify_barriers")
    graph.add_edge("identify_barriers", "analyze_specialty_perspectives")
    graph.add_edge("analyze_specialty_perspectives", "analyze_setting_variations")
    graph.add_edge("analyze_setting_variations", "assemble_report")
    graph.add_edge("assemble_report", "render_document")
    graph.add_edge("render_document", END)
    
    return graph


# Compile for LangGraph Cloud
graph = create_clinical_practice_graph().compile()


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        test_state = {
            "therapeutic_area": "cardiology",
            "disease_state": "heart failure with preserved ejection fraction",
            "target_audience": "cardiologists",
            "practice_settings": ["community hospital", "academic medical center"],
            "geographic_focus": "United States",
            "known_gaps": ["Underuse of SGLT2 inhibitors"],
            "known_barriers": ["Time constraints", "Lack of familiarity with new evidence"],
            "messages": [],
            "citations": [],
            "errors": [],
            "sources_analyzed": 0,
            "total_tokens": 0,
            "total_cost": 0.0
        }
        
        result = await graph.ainvoke(test_state)
        
        print(f"\n=== CLINICAL PRACTICE ANALYSIS ===")
        print(f"Sources analyzed: {result.get('sources_analyzed', 0)}")
        print(f"Total tokens: {result.get('total_tokens', 0)}")
        print(f"Total cost: ${result.get('total_cost', 0):.4f}")
        
        report = result.get("clinical_practice_report", {})
        print(f"\n=== SECTIONS ===")
        for section in ["standard_of_care", "real_world_practice", "practice_barriers", "specialty_perspectives", "setting_variations"]:
            data = report.get(section, {})
            print(f"- {section}: {'✓' if data and 'error' not in data else '✗'}")
        
        print(f"\n=== DOCUMENT PREVIEW ===")
        doc = result.get("clinical_practice_document", "")
        print(doc[:500] + "..." if len(doc) > 500 else doc)
    
    asyncio.run(test())
