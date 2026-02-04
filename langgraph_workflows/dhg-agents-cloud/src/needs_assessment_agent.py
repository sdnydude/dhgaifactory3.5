"""
DHG CME Needs Assessment Agent - LangGraph Cloud
=================================================
Agent #5 in the 12-agent CME grant pipeline.

Produces the flagship 3,100+ word needs assessment narrative with:
- Cold open (50-100 words)
- Character thread (4+ appearances)
- 8 required sections
- Evidence-dense prose (80%+ flowing narrative)
- Zero AI patterns (de-AI-ified)

LANGGRAPH CLOUD READY:
- Pure LangGraph + LangSmith
- Claude Sonnet for complex synthesis
- No Docker/FastAPI dependencies

Author: Digital Harmony Group
Version: 1.0.0
"""

import os
import re
import json
from datetime import datetime
from typing import Annotated, Optional, List, Dict, Any
from typing_extensions import TypedDict
from dataclasses import dataclass, field
from enum import Enum

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langsmith import traceable

# LangChain imports
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig


# =============================================================================
# BANNED PATTERNS (De-AI-ification)
# =============================================================================

BANNED_PATTERNS = [
    r"—",  # Em dash
    r"delve into",
    r"delve deeper",
    r"it's important to note",
    r"it is important to note",
    r"furthermore,",
    r"moreover,",
    r"additionally,",
    r"in today's healthcare landscape",
    r"underscores the importance",
    r"serves as a testament",
    r"navigate the complexities",
    r"robust",
    r"leverage",
    r"holistic",
    r"paradigm",
    r"cutting-edge",
    r"state-of-the-art",
    r"best practices",
    r"moving forward",
    r"at the end of the day",
    r"it goes without saying",
    r"a myriad of",
    r"a plethora of",
    r"multifaceted",
    r"landscape",  # When used metaphorically
    r"navigat",  # navigate, navigating
]

# Prompt injection for ALL section generation - explicit replacements
BANNED_PATTERNS_GUIDANCE = """
CRITICAL - NEVER USE THESE WORDS OR PHRASES (use the alternative instead):
- "robust" → use: "strong", "reliable", "well-established", "effective"
- "paradigm" → use: "approach", "model", "framework", "method"
- "multifaceted" → use: "complex", "varied", "multiple aspects of"
- "navigate/navigating" → use: "manage", "address", "work through", "handle"
- "landscape" (metaphorical) → use: "environment", "field", "current state", "options"
- "holistic" → use: "comprehensive", "integrated", "complete", "whole-patient"
- "leverage" → use: "use", "apply", "employ", "utilize"
- "delve/delving" → use: "examine", "explore", "investigate", "study"
- "cutting-edge" → use: "latest", "newest", "recent", "advanced"
- "state-of-the-art" → use: "modern", "current", "latest"
- "best practices" → use: "recommended approaches", "evidence-based methods"
- "furthermore/moreover/additionally" at start → use: "Also,", "In addition,", or restructure
- Em dashes (—) → use: commas, semicolons, or parentheses
- "It's important to note" → Just state the fact directly
- "underscores the importance" → use: "highlights", "demonstrates", "shows"

SECTION HEADERS - Use these exact titles:
- "Disease State Overview" (not "Disease Landscape")
- "Current Treatment Options" (not "Treatment Landscape")
- "Practice Gaps" (not "Care Landscape")
- "Barriers to Optimal Care"
- "Educational Rationale"
- "Target Audience"
- "Conclusion"
"""



def check_banned_patterns(text: str) -> List[str]:
    """Check text for banned AI patterns. Returns list of found patterns."""
    found = []
    for pattern in BANNED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(pattern)
    return found


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def check_prose_density(text: str) -> float:
    """
    Calculate prose density (0-1).
    Higher = more flowing prose, fewer bullet points.
    """
    lines = text.split('\n')
    prose_lines = 0
    bullet_lines = 0
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(('-', '*', '•', '1.', '2.', '3.')):
            bullet_lines += 1
        elif len(stripped) > 20:  # Substantial prose line
            prose_lines += 1
    
    total = prose_lines + bullet_lines
    if total == 0:
        return 1.0
    return prose_lines / total


# =============================================================================
# COLD OPEN FRAMEWORK
# =============================================================================

COLD_OPEN_SYSTEM_PROMPT = """You are a senior medical writer creating a cold open for a CME grant needs assessment.

COLD OPEN REQUIREMENTS:
- 50-100 words exactly
- Named composite character with age (e.g., "Maria Chen, 58")
- One humanizing detail that makes them real
- Present tense for immediacy
- The turn: connect individual to population at the end
- NO statistics in the cold open itself
- NO medical jargon the reader must translate
- NO hedging with "may" or "might"

STRUCTURE:
1. THE MOMENT (10-20 words): Drop into a specific scene
2. THE PERSON (15-30 words): Name, age, humanizing detail
3. THE STAKES (20-40 words): What's at risk
4. THE TURN (10-20 words): Connect to population ("She is one of X million...")

Return ONLY the cold open narrative text. No headers, no quotes, just the narrative."""


CHARACTER_TYPES = [
    {"type": "patient", "description": "Patient experiencing the gap"},
    {"type": "clinician", "description": "Provider facing the decision point"},
]


# =============================================================================
# SECTION TEMPLATES
# =============================================================================

SECTION_REQUIREMENTS = {
    "cold_open": {"min_words": 50, "max_words": 100, "character_required": True},
    "disease_state_overview": {"min_words": 125, "max_words": 300},
    "treatment_landscape": {"min_words": 200, "max_words": 300},
    "practice_gaps": {"min_words": 300, "max_words": 400, "character_required": True},
    "barriers": {"min_words": 125, "max_words": 200},
    "educational_rationale": {"min_words": 200, "max_words": 300, "character_required": True},
    "target_audience": {"min_words": 125, "max_words": 200},
    "conclusion": {"min_words": 200, "max_words": 300, "character_required": True},
}


# =============================================================================
# STATE DEFINITION
# =============================================================================

class NeedsAssessmentState(TypedDict):
    """State for Needs Assessment Agent."""
    
    # === INPUT ===
    # From intake form
    therapeutic_area: str
    disease_state: str
    target_audience: str
    geographic_focus: Optional[str]
    activity_title: str
    accreditation_types: List[str]
    
    # From upstream agents
    gaps: List[Dict[str, Any]]  # From Gap Analysis Agent
    research_summary: str  # From Research Agent
    clinical_barriers: List[str]  # From Clinical Practice Agent
    epidemiology: Dict[str, Any]  # From Research Agent
    
    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    
    # Character thread
    character_name: str
    character_age: int
    character_type: str  # "patient" or "clinician"
    character_humanizing_detail: str
    character_appearances: int
    
    # Document sections
    cold_open: str
    disease_state_overview: str
    treatment_landscape: str
    practice_gaps_section: str
    barriers_section: str
    educational_rationale: str
    target_audience_section: str
    conclusion: str
    
    # === OUTPUT ===
    complete_document: str
    word_count: int
    prose_density: float
    banned_patterns_found: List[str]
    section_word_counts: Dict[str, int]
    
    # Quality flags
    meets_word_count: bool
    meets_prose_density: bool
    meets_character_thread: bool
    quality_passed: bool
    
    # Metadata
    errors: List[str]
    model_used: str
    total_tokens: int
    total_cost: float


# =============================================================================
# LLM CLIENT
# =============================================================================

class NeedsAssessmentLLM:
    """LLM client for Needs Assessment generation."""
    
    def __init__(self):
        self._sonnet = None
    
    def _get_sonnet(self):
        if self._sonnet is None:
            self._sonnet = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                max_tokens=8192
            )
        return self._sonnet
    
    @traceable(name="needs_assessment_llm", run_type="llm")
    async def generate(self, system: str, prompt: str, metadata: dict = None) -> dict:
        """Generate content with Claude Sonnet."""
        model = self._get_sonnet()
        
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=prompt)
        ]
        
        config = {"metadata": {"agent": "needs_assessment", **(metadata or {})}}
        response = await model.ainvoke(messages, config=config)
        
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            input_tokens = response.usage_metadata.get("input_tokens", 0)
            output_tokens = response.usage_metadata.get("output_tokens", 0)
        
        # Claude Sonnet pricing: $3/M input, $15/M output
        cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000
        
        return {
            "content": response.content,
            "model": "claude-sonnet-4-20250514",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost
        }


llm = NeedsAssessmentLLM()


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="create_character_node", run_type="chain")
async def create_character_node(state: NeedsAssessmentState) -> dict:
    """Create the cold open character based on gap analysis."""
    
    gaps = state.get("gaps", [])
    therapeutic_area = state.get("therapeutic_area", "")
    disease_state = state.get("disease_state", "")
    
    # Determine character type based on gaps
    # Patient-centered if gaps affect patient outcomes
    # Clinician-centered if gaps are about decision-making
    patient_keywords = ["diagnosis", "treatment", "outcomes", "mortality", "morbidity"]
    clinician_keywords = ["awareness", "knowledge", "guideline", "prescribing"]
    
    gap_text = " ".join([g.get("gap_statement", "") for g in gaps])
    
    patient_score = sum(1 for k in patient_keywords if k in gap_text.lower())
    clinician_score = sum(1 for k in clinician_keywords if k in gap_text.lower())
    
    character_type = "patient" if patient_score >= clinician_score else "clinician"
    
    # Generate character details with LLM
    prompt = f"""Create a composite character for a CME needs assessment about {disease_state} in {therapeutic_area}.

Character type: {character_type}

Clinical gaps being addressed:
{chr(10).join([f"- {g.get('gap_statement', '')}" for g in gaps[:3]])}

Provide a JSON response with:
{{
    "name": "Full name appropriate to demographics",
    "age": integer age relevant to condition,
    "humanizing_detail": "One specific, concrete detail that makes them real",
    "clinical_situation": "Brief description of how they represent the gap"
}}

Return ONLY the JSON, no other text."""

    result = await llm.generate(
        "You create realistic composite characters for medical education.",
        prompt,
        {"step": "character_creation"}
    )
    
    try:
        # Parse JSON from response
        match = re.search(r'\{[\s\S]*\}', result["content"])
        if match:
            data = json.loads(match.group())
            return {
                "character_name": data.get("name", "Maria Chen"),
                "character_age": data.get("age", 58),
                "character_type": character_type,
                "character_humanizing_detail": data.get("humanizing_detail", ""),
                "character_appearances": 0,
                "model_used": result["model"],
                "total_tokens": result["total_tokens"],
                "total_cost": result["cost"],
                "errors": []
            }
    except Exception as e:
        return {
            "character_name": "Maria Chen",
            "character_age": 58,
            "character_type": "patient",
            "character_humanizing_detail": "visits her doctor for the third time this year",
            "character_appearances": 0,
            "errors": [f"Character creation fallback: {str(e)}"]
        }


@traceable(name="generate_cold_open_node", run_type="chain")
async def generate_cold_open_node(state: NeedsAssessmentState) -> dict:
    """Generate the cold open narrative."""
    
    character_name = state.get("character_name", "Maria Chen")
    character_age = state.get("character_age", 58)
    character_type = state.get("character_type", "patient")
    character_detail = state.get("character_humanizing_detail", "")
    disease_state = state.get("disease_state", "")
    gaps = state.get("gaps", [])
    epidemiology = state.get("epidemiology", {})
    
    population_stat = epidemiology.get("prevalence", "millions of patients")
    
    prompt = f"""Write a cold open for a needs assessment about {disease_state}.

CHARACTER:
- Name: {character_name}
- Age: {character_age}
- Type: {character_type}
- Humanizing detail: {character_detail}

CLINICAL GAP TO ILLUSTRATE:
{gaps[0].get('gap_statement', 'Gap in optimal care') if gaps else 'Gap in optimal care'}

POPULATION STATISTIC FOR THE TURN:
{population_stat}

Write a 50-100 word cold open following the structure:
1. THE MOMENT: Drop into specific scene
2. THE PERSON: Name, age, humanizing detail
3. THE STAKES: What's at risk
4. THE TURN: Connect to population

Return ONLY the narrative text. No headers. No quotes."""

    result = await llm.generate(
        COLD_OPEN_SYSTEM_PROMPT,
        prompt,
        {"step": "cold_open"}
    )
    
    cold_open = result["content"].strip()
    word_count = count_words(cold_open)
    
    # Track token usage
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "cold_open": cold_open,
        "character_appearances": 1,  # First appearance in cold open
        "section_word_counts": {"cold_open": word_count},
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"],
        "errors": []
    }


@traceable(name="generate_disease_overview_node", run_type="chain")
async def generate_disease_overview_node(state: NeedsAssessmentState) -> dict:
    """Generate Disease State Overview section (125-300 words)."""
    
    disease_state = state.get("disease_state", "")
    therapeutic_area = state.get("therapeutic_area", "")
    character_name = state.get("character_name", "Maria Chen")
    epidemiology = state.get("epidemiology", {})
    research_summary = state.get("research_summary", "")
    
    system = f"""You are a senior medical writer creating a disease state overview for a CME grant.

REQUIREMENTS:
- 125-300 words
- Start with connecting the cold open character to the population
- Include specific epidemiology data with citations
- Include economic burden with citations
- Include disease trajectory/projections
- 80%+ flowing prose (no bullet points)
- Embed data in prose, don't list it
- Use active voice
- Include specific numbers, not "many" or "significant"

{BANNED_PATTERNS_GUIDANCE}

Return ONLY the section content. No section header."""

    prompt = f"""Write the Disease State Overview section for {disease_state} in {therapeutic_area}.

CHARACTER TO REFERENCE:
{character_name} is one of [population number] Americans living with {disease_state}...

EPIDEMIOLOGY DATA:
{json.dumps(epidemiology, indent=2) if epidemiology else "Use standard epidemiology for this condition"}

RESEARCH CONTEXT:
{research_summary[:1000] if research_summary else "Include current prevalence, mortality, and economic data"}

Write 125-300 words of flowing prose. Start by connecting the character to the population."""

    result = await llm.generate(system, prompt, {"step": "disease_overview"})
    
    content = result["content"].strip()
    word_count = count_words(content)
    
    # Check if character is mentioned
    appearances = state.get("character_appearances", 0)
    if character_name.split()[0] in content or character_name in content:
        appearances += 1
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    section_counts = state.get("section_word_counts", {})
    section_counts["disease_state_overview"] = word_count
    
    return {
        "disease_state_overview": content,
        "character_appearances": appearances,
        "section_word_counts": section_counts,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="generate_treatment_options_node", run_type="chain")
async def generate_treatment_options_node(state: NeedsAssessmentState) -> dict:
    """Generate Current Treatment Options section (200-300 words)."""
    
    disease_state = state.get("disease_state", "")
    research_summary = state.get("research_summary", "")
    
    system = f"""You are a senior medical writer creating a treatment options section for a CME grant.

REQUIREMENTS:
- 200-300 words
- Guideline-recommended approaches with specific named guidelines
- Available therapies with drug classes/names
- Recent advances (specific drugs, trials)
- Evidence base summary with named trials
- 80%+ flowing prose
- Active voice
- All claims backed by specific citations

{BANNED_PATTERNS_GUIDANCE}

Return ONLY the section content. No header."""

    prompt = f"""Write the Current Treatment Options section for {disease_state}.

Cover:
1. Guideline-recommended approach (name specific guidelines like ACC/AHA)
2. Available therapies (name drug classes)
3. Recent advances (specific trials like PARADIGM-HF)
4. Evidence base summary

Research context:
{research_summary[:1500] if research_summary else "Use current standard of care for this condition"}

Write 200-300 words of flowing prose."""

    result = await llm.generate(system, prompt, {"step": "treatment_landscape"})
    
    content = result["content"].strip()
    word_count = count_words(content)
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    section_counts = state.get("section_word_counts", {})
    section_counts["treatment_landscape"] = word_count
    
    return {
        "treatment_landscape": content,
        "section_word_counts": section_counts,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="generate_practice_gaps_node", run_type="chain")
async def generate_practice_gaps_node(state: NeedsAssessmentState) -> dict:
    """Generate Practice Gaps section (300-400 words)."""
    
    gaps = state.get("gaps", [])
    character_name = state.get("character_name", "Maria Chen")
    disease_state = state.get("disease_state", "")
    
    system = f"""You are a senior medical writer creating a practice gaps section for a CME grant.

REQUIREMENTS:
- 300-400 words
- Present each gap as a narrative with evidence
- Include quantified evidence for each gap
- Connect gaps to patient outcomes
- Include character reference to illustrate at least one gap
- 80%+ flowing prose
- Name specific studies supporting each gap

{BANNED_PATTERNS_GUIDANCE}

Return ONLY the section content. No header."""

    gaps_text = "\n".join([
        f"Gap {i+1}: {g.get('gap_statement', '')}\nEvidence: {g.get('evidence_summary', '')}\nPatient Impact: {g.get('patient_impact', '')}"
        for i, g in enumerate(gaps[:5])
    ]) if gaps else "Gaps to be identified based on clinical practice"

    prompt = f"""Write the Practice Gaps section for {disease_state}.

GAPS TO ADDRESS:
{gaps_text}

CHARACTER TO INCLUDE:
{character_name} - use to illustrate one of the gaps naturally
Example: "In {character_name.split()[0]}'s case, the gap manifested as..."

Write 300-400 words. Each gap should be a narrative paragraph with evidence."""

    result = await llm.generate(system, prompt, {"step": "practice_gaps"})
    
    content = result["content"].strip()
    word_count = count_words(content)
    
    appearances = state.get("character_appearances", 0)
    if character_name.split()[0] in content or character_name in content:
        appearances += 1
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    section_counts = state.get("section_word_counts", {})
    section_counts["practice_gaps"] = word_count
    
    return {
        "practice_gaps_section": content,
        "character_appearances": appearances,
        "section_word_counts": section_counts,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="generate_barriers_node", run_type="chain")
async def generate_barriers_node(state: NeedsAssessmentState) -> dict:
    """Generate Barriers to Optimal Care section (125-200 words)."""
    
    clinical_barriers = state.get("clinical_barriers", [])
    disease_state = state.get("disease_state", "")
    
    system = f"""You are a senior medical writer creating a barriers section for a CME grant.

REQUIREMENTS:
- 125-200 words
- Categorize barriers: Clinician (knowledge, skill, attitude), System, Patient
- Explain root causes
- Connect barriers to gaps
- 80%+ flowing prose

{BANNED_PATTERNS_GUIDANCE}

Return ONLY the section content. No header."""

    barriers_text = "\n".join([f"- {b}" for b in clinical_barriers]) if clinical_barriers else "Barriers to be identified"

    prompt = f"""Write the Barriers to Optimal Care section for {disease_state}.

IDENTIFIED BARRIERS:
{barriers_text}

Categorize into:
1. Clinician barriers (knowledge gaps, skill deficits, attitudinal issues)
2. System barriers (time, resources, workflow)
3. Patient barriers (access, adherence, health literacy)

Write 125-200 words explaining how each barrier perpetuates the practice gaps."""

    result = await llm.generate(system, prompt, {"step": "barriers"})
    
    content = result["content"].strip()
    word_count = count_words(content)
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    section_counts = state.get("section_word_counts", {})
    section_counts["barriers"] = word_count
    
    return {
        "barriers_section": content,
        "section_word_counts": section_counts,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="generate_educational_rationale_node", run_type="chain")
async def generate_educational_rationale_node(state: NeedsAssessmentState) -> dict:
    """Generate Educational Rationale section (200-300 words)."""
    
    character_name = state.get("character_name", "Maria Chen")
    disease_state = state.get("disease_state", "")
    gaps = state.get("gaps", [])
    
    system = f"""You are a senior medical writer creating an educational rationale for a CME grant.

REQUIREMENTS:
- 200-300 words
- Why education can address these gaps
- What education must accomplish
- Expected outcomes from education
- Include character reference in outcome context
- 80%+ flowing prose

{BANNED_PATTERNS_GUIDANCE}

Return ONLY the section content. No header."""

    prompt = f"""Write the Educational Rationale section for {disease_state}.

GAPS EDUCATION WILL ADDRESS:
{chr(10).join([g.get('gap_statement', '') for g in gaps[:3]]) if gaps else "Practice gaps identified above"}

CHARACTER TO INCLUDE:
"Had {character_name.split()[0]}'s physician participated in education addressing these gaps..."

Write 200-300 words making the case for why education can improve outcomes."""

    result = await llm.generate(system, prompt, {"step": "educational_rationale"})
    
    content = result["content"].strip()
    word_count = count_words(content)
    
    appearances = state.get("character_appearances", 0)
    if character_name.split()[0] in content or character_name in content:
        appearances += 1
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    section_counts = state.get("section_word_counts", {})
    section_counts["educational_rationale"] = word_count
    
    return {
        "educational_rationale": content,
        "character_appearances": appearances,
        "section_word_counts": section_counts,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="generate_target_audience_node", run_type="chain")
async def generate_target_audience_node(state: NeedsAssessmentState) -> dict:
    """Generate Target Audience section (125-200 words)."""
    
    target_audience = state.get("target_audience", "primary care physicians")
    disease_state = state.get("disease_state", "")
    geographic_focus = state.get("geographic_focus", "")
    
    system = f"""You are a senior medical writer creating a target audience section for a CME grant.

REQUIREMENTS:
- 125-200 words
- Who needs this education
- Why this audience
- Specialty-specific considerations
- Practice setting context
- 80%+ flowing prose

{BANNED_PATTERNS_GUIDANCE}

Return ONLY the section content. No header."""

    prompt = f"""Write the Target Audience section for {disease_state} education.

PRIMARY TARGET: {target_audience}
GEOGRAPHIC FOCUS: {geographic_focus or "National"}

Address:
1. Who specifically needs this education (specialties, practice settings)
2. Why this audience (who sees these patients most)
3. Specialty-specific knowledge needs
4. Practice setting variations (academic, community, rural)

Write 125-200 words."""

    result = await llm.generate(system, prompt, {"step": "target_audience"})
    
    content = result["content"].strip()
    word_count = count_words(content)
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    section_counts = state.get("section_word_counts", {})
    section_counts["target_audience"] = word_count
    
    return {
        "target_audience_section": content,
        "section_word_counts": section_counts,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="generate_conclusion_node", run_type="chain")
async def generate_conclusion_node(state: NeedsAssessmentState) -> dict:
    """Generate Conclusion section (200-300 words)."""
    
    character_name = state.get("character_name", "Maria Chen")
    disease_state = state.get("disease_state", "")
    
    system = f"""You are a senior medical writer creating a conclusion for a CME needs assessment.

REQUIREMENTS:
- 200-300 words
- Synthesis of need
- Call to action
- Final character reference looking forward
- 80%+ flowing prose
- End on an aspirational note

{BANNED_PATTERNS_GUIDANCE}

Return ONLY the section content. No header."""

    prompt = f"""Write the Conclusion section for {disease_state} needs assessment.

CHARACTER TO INCLUDE:
"For {character_name} and the millions like her, the window for optimal intervention..."
OR
"Success means the next {character_name.split()[0]} receives timely intervention."

Write 200-300 words synthesizing the need and calling for educational action."""

    result = await llm.generate(system, prompt, {"step": "conclusion"})
    
    content = result["content"].strip()
    word_count = count_words(content)
    
    appearances = state.get("character_appearances", 0)
    if character_name.split()[0] in content or character_name in content:
        appearances += 1
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    section_counts = state.get("section_word_counts", {})
    section_counts["conclusion"] = word_count
    
    return {
        "conclusion": content,
        "character_appearances": appearances,
        "section_word_counts": section_counts,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="assemble_document_node", run_type="chain")
async def assemble_document_node(state: NeedsAssessmentState) -> dict:
    """Assemble complete document and run quality checks."""
    
    # Assemble sections
    sections = [
        state.get("cold_open", ""),
        "",  # Blank line after cold open
        "## Disease State Overview",
        state.get("disease_state_overview", ""),
        "",
        "## Current Treatment Options",
        state.get("treatment_landscape", ""),
        "",
        "## Practice Gaps",
        state.get("practice_gaps_section", ""),
        "",
        "## Barriers to Optimal Care",
        state.get("barriers_section", ""),
        "",
        "## Educational Rationale",
        state.get("educational_rationale", ""),
        "",
        "## Target Audience",
        state.get("target_audience_section", ""),
        "",
        "## Conclusion",
        state.get("conclusion", ""),
    ]
    
    complete_document = "\n".join(sections)
    
    # Quality checks
    word_count = count_words(complete_document)
    prose_density = check_prose_density(complete_document)
    banned_found = check_banned_patterns(complete_document)
    character_appearances = state.get("character_appearances", 0)
    
    # Pass/fail checks
    meets_word_count = word_count >= 3100
    meets_prose_density = prose_density >= 0.80
    meets_character_thread = character_appearances >= 4
    quality_passed = meets_word_count and meets_prose_density and meets_character_thread and len(banned_found) == 0
    
    return {
        "complete_document": complete_document,
        "word_count": word_count,
        "prose_density": prose_density,
        "banned_patterns_found": banned_found,
        "meets_word_count": meets_word_count,
        "meets_prose_density": meets_prose_density,
        "meets_character_thread": meets_character_thread,
        "quality_passed": quality_passed
    }


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def create_needs_assessment_graph() -> StateGraph:
    """Create the Needs Assessment Agent graph."""
    
    graph = StateGraph(NeedsAssessmentState)
    
    # Add nodes
    graph.add_node("create_character", create_character_node)
    graph.add_node("generate_cold_open", generate_cold_open_node)
    graph.add_node("generate_disease_overview", generate_disease_overview_node)
    graph.add_node("generate_treatment_options", generate_treatment_options_node)
    graph.add_node("generate_practice_gaps", generate_practice_gaps_node)
    graph.add_node("generate_barriers", generate_barriers_node)
    graph.add_node("generate_educational_rationale", generate_educational_rationale_node)
    graph.add_node("generate_target_audience", generate_target_audience_node)
    graph.add_node("generate_conclusion", generate_conclusion_node)
    graph.add_node("assemble_document", assemble_document_node)
    
    # Add edges (sequential flow)
    graph.set_entry_point("create_character")
    graph.add_edge("create_character", "generate_cold_open")
    graph.add_edge("generate_cold_open", "generate_disease_overview")
    graph.add_edge("generate_disease_overview", "generate_treatment_options")
    graph.add_edge("generate_treatment_options", "generate_practice_gaps")
    graph.add_edge("generate_practice_gaps", "generate_barriers")
    graph.add_edge("generate_barriers", "generate_educational_rationale")
    graph.add_edge("generate_educational_rationale", "generate_target_audience")
    graph.add_edge("generate_target_audience", "generate_conclusion")
    graph.add_edge("generate_conclusion", "assemble_document")
    graph.add_edge("assemble_document", END)
    
    return graph


# Compile the graph for LangGraph Cloud
graph = create_needs_assessment_graph().compile()


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        # Test input
        test_state = {
            "therapeutic_area": "cardiology",
            "disease_state": "heart failure with reduced ejection fraction",
            "target_audience": "primary care physicians",
            "geographic_focus": "United States",
            "activity_title": "Optimizing HFrEF Management in Primary Care",
            "accreditation_types": ["AMA PRA Category 1"],
            "gaps": [
                {
                    "gap_statement": "Underutilization of guideline-directed medical therapy",
                    "evidence_summary": "Only 25% of eligible patients receive GDMT",
                    "patient_impact": "Increased mortality and hospitalizations"
                },
                {
                    "gap_statement": "Delayed referral for device therapy",
                    "evidence_summary": "Average delay of 18 months for ICD evaluation",
                    "patient_impact": "Preventable sudden cardiac death"
                }
            ],
            "research_summary": "Heart failure affects 6.7 million Americans with mortality remaining high at 50% within 5 years.",
            "clinical_barriers": ["Time constraints", "Complex guidelines", "Competing priorities"],
            "epidemiology": {
                "prevalence": "6.7 million Americans",
                "mortality": "50% 5-year mortality",
                "cost": "$43.6 billion annually"
            },
            "messages": [],
            "errors": []
        }
        
        result = await graph.ainvoke(test_state)
        
        print(f"\n=== NEEDS ASSESSMENT OUTPUT ===")
        print(f"Word count: {result['word_count']} (target: 3100+)")
        print(f"Prose density: {result['prose_density']:.1%} (target: 80%+)")
        print(f"Character appearances: {result['character_appearances']} (target: 4+)")
        print(f"Banned patterns: {result['banned_patterns_found']}")
        print(f"Quality passed: {result['quality_passed']}")
        print(f"\nTotal tokens: {result['total_tokens']}")
        print(f"Total cost: ${result['total_cost']:.4f}")
        print(f"\n=== DOCUMENT PREVIEW ===")
        print(result['complete_document'][:2000])
    
    asyncio.run(test())
