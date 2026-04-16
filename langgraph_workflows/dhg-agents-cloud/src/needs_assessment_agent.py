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
from extract_topic import extract_topic_node
from pubmed_client import PubMedClient, build_references_section
from langchain_core.runnables import RunnableConfig
from vs_client import vs_generate, vs_select, vs_is_available

# OpenTelemetry tracing (dual-export with LangSmith)
from tracing import traced_node


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
=== HIGH PRIORITY FORMATTING RULES ===
NEVER use em dashes (—). Replace with:
  - Use a comma instead: "The treatment — first-line therapy — works" → "The treatment, first-line therapy, works"
  - Use parentheses: "The drug — approved in 2022 — reduces mortality" → "The drug (approved in 2022) reduces mortality"
  - Split into two sentences if needed

NEVER use colons (:) in prose except for citations. Replace with:
  - "The evidence is clear: patients need..." → "The evidence clearly shows that patients need..."
  - "This illustrates the gap: delayed..." → "This illustrates how delays in..."
  - "Consider the challenge: many clinicians..." → "Many clinicians face the challenge of..."

NEVER start a paragraph with: "Furthermore,", "Moreover,", "Additionally,"
  - Instead use: "Also,", "In addition,", or just start with the content

ALWAYS name specific studies - never use generic references:
  - WRONG: "Studies show..." or "Studies indicate..." or "Research suggests..."
  - RIGHT: name the actual trial, registry, or analysis relevant to the disease state being addressed (e.g., "The [TRIAL NAME] trial showed..." or "Registry data from [REGISTRY NAME] indicates...")
  - WRONG: "Population-level studies indicate..."
  - RIGHT: cite the specific cohort, registry, or surveillance program by name
  - Use trials and registries that genuinely exist and are relevant to the therapeutic area in the activity. Do not import examples from unrelated specialties.

=== CITATION FORMAT ===
Use numbered inline references [1], [2], [3] etc. for every factual claim, statistic, or guideline mention.
Number sequentially starting from [1] within your section.
Do NOT include a references list at the end of your section. References will be consolidated separately.
When citing, mentally track what each number refers to (e.g. [1] = Smith et al. 2023 NEJM study) so the citations are consistent and traceable.

=== BANNED WORDS - USE ALTERNATIVES ===
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
- "myriad of" → use: "many", "numerous", "multiple"
- "plethora of" → use: "many", "numerous", "wide range of"
- "It's important to note" → Just state the fact directly
- "underscores the importance" → use: "highlights", "demonstrates", "shows"
- "serves as a testament" → use: "demonstrates", "shows", "illustrates"

=== SECTION HEADERS (Use Exactly) ===
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
- Named composite character with age
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
    intake_data: Dict[str, Any]  # Full flattened intake — includes character_mode, character_* fields

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

    # === VS (Verbalized Sampling) ===
    vs_distributions: Dict[str, Dict[str, Any]]  # keyed by step name
    vs_used: bool


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
@traced_node("needs_assessment_agent", "create_character_node")
async def create_character_node(state: NeedsAssessmentState) -> dict:
    """Create the cold open character — guided from intake or auto-generated from gaps."""

    intake = state.get("intake_data") or {}
    character_mode = intake.get("character_mode", "auto")

    # ── Guided mode: user provided character attributes via intake form ──
    if character_mode == "guided":
        guided_name = intake.get("character_name", "")
        guided_age = intake.get("character_age")
        guided_detail = intake.get("character_presenting_complaint", "")
        if intake.get("character_clinical_history"):
            guided_detail = f"{guided_detail}; {intake['character_clinical_history']}" if guided_detail else intake["character_clinical_history"]

        char_type = "patient"
        if intake.get("character_occupation") and any(
            kw in (intake.get("character_occupation") or "").lower()
            for kw in ("doctor", "physician", "nurse", "clinician", "pharmacist", "provider")
        ):
            char_type = "clinician"

        return {
            "character_name": guided_name,
            "character_age": guided_age or 55,
            "character_type": char_type,
            "character_humanizing_detail": guided_detail,
            "character_appearances": 0,
            "errors": []
        }

    # ── Auto mode: generate character from gap analysis via LLM ──
    gaps = state.get("gaps", [])
    therapeutic_area = state.get("therapeutic_area", "")
    disease_state = state.get("disease_state", "")

    patient_keywords = ["diagnosis", "treatment", "outcomes", "mortality", "morbidity"]
    clinician_keywords = ["awareness", "knowledge", "guideline", "prescribing"]

    gap_text = " ".join([g.get("gap_statement", "") for g in gaps])

    patient_score = sum(1 for k in patient_keywords if k in gap_text.lower())
    clinician_score = sum(1 for k in clinician_keywords if k in gap_text.lower())

    character_type = "patient" if patient_score >= clinician_score else "clinician"

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

    try:
        system = "You create realistic composite characters for medical education."
        vs_result = None
        if await vs_is_available():
            vs_result = await vs_generate(
                prompt=prompt, phase="needs_assessment", k=5, system_prompt=system,
            )
        if vs_result and vs_result.get("items"):
            selected = await vs_select(vs_result["distribution_id"], strategy="argmax")
            content = (selected["selected"]["content"] if selected and selected.get("selected")
                       else vs_result["items"][0]["content"])
            result = {"content": content, "model": "vs-engine", "total_tokens": 0, "cost": 0.0}
        else:
            result = await llm.generate(system, prompt, {"step": "character_creation"})
            vs_result = None

        prev_dists = state.get("vs_distributions", {})

        match = re.search(r'\{[\s\S]*\}', result["content"])
        if match:
            data = json.loads(match.group())
            return {
                "character_name": data.get("name", f"Patient with {disease_state}"),
                "character_age": data.get("age", 55),
                "character_type": character_type,
                "character_humanizing_detail": data.get("humanizing_detail", ""),
                "character_appearances": 0,
                "model_used": result["model"],
                "total_tokens": result["total_tokens"],
                "total_cost": result["cost"],
                "vs_distributions": {**prev_dists, "character_creation": vs_result} if vs_result else prev_dists,
                "vs_used": state.get("vs_used", False) or (vs_result is not None),
                "errors": []
            }
        return {
            "character_name": f"Patient with {disease_state or 'this condition'}",
            "character_age": 55,
            "character_type": character_type,
            "character_humanizing_detail": "seeks answers after months of worsening symptoms",
            "character_appearances": 0,
            "errors": ["Character JSON parsing failed, using dynamic fallback"]
        }
    except Exception as e:
        return {
            "character_name": f"Patient with {disease_state or 'this condition'}",
            "character_age": 55,
            "character_type": "patient",
            "character_humanizing_detail": "seeks answers after months of worsening symptoms",
            "character_appearances": 0,
            "errors": [f"Character creation fallback: {str(e)}"]
        }


@traceable(name="generate_cold_open_node", run_type="chain")
async def generate_cold_open_node(state: NeedsAssessmentState) -> dict:
    """Generate the cold open narrative."""
    
    character_name = state.get("character_name", "the patient")
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

    vs_result = None
    if await vs_is_available():
        vs_result = await vs_generate(
            prompt=prompt, phase="needs_assessment", k=5, system_prompt=COLD_OPEN_SYSTEM_PROMPT,
        )
    if vs_result and vs_result.get("items"):
        selected = await vs_select(vs_result["distribution_id"], strategy="argmax")
        content = (selected["selected"]["content"] if selected and selected.get("selected")
                   else vs_result["items"][0]["content"])
        result = {"content": content, "total_tokens": 0, "cost": 0.0}
    else:
        result = await llm.generate(COLD_OPEN_SYSTEM_PROMPT, prompt, {"step": "cold_open"})
        vs_result = None

    cold_open = result["content"].strip()
    word_count = count_words(cold_open)

    # Track token usage
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_dists = state.get("vs_distributions", {})

    return {
        "cold_open": cold_open,
        "character_appearances": 1,  # First appearance in cold open
        "section_word_counts": {"cold_open": word_count},
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"],
        "vs_distributions": {**prev_dists, "cold_open": vs_result} if vs_result else prev_dists,
        "vs_used": state.get("vs_used", False) or (vs_result is not None),
        "errors": []
    }


@traceable(name="generate_disease_overview_node", run_type="chain")
async def generate_disease_overview_node(state: NeedsAssessmentState) -> dict:
    """Generate Disease State Overview section (125-300 words)."""
    
    disease_state = state.get("disease_state", "")
    therapeutic_area = state.get("therapeutic_area", "")
    character_name = state.get("character_name", "the patient")
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

    vs_result = None
    if await vs_is_available():
        vs_result = await vs_generate(
            prompt=prompt, phase="needs_assessment", k=5, system_prompt=system,
        )
    if vs_result and vs_result.get("items"):
        selected = await vs_select(vs_result["distribution_id"], strategy="argmax")
        content_text = (selected["selected"]["content"] if selected and selected.get("selected")
                        else vs_result["items"][0]["content"])
        result = {"content": content_text, "total_tokens": 0, "cost": 0.0}
    else:
        result = await llm.generate(system, prompt, {"step": "disease_overview"})
        vs_result = None

    content = result["content"].strip()
    word_count = count_words(content)

    # Check if character is mentioned
    appearances = state.get("character_appearances", 0)
    if character_name.split()[0] in content or character_name in content:
        appearances += 1

    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_dists = state.get("vs_distributions", {})
    section_counts = state.get("section_word_counts", {})
    section_counts["disease_state_overview"] = word_count

    return {
        "disease_state_overview": content,
        "character_appearances": appearances,
        "section_word_counts": section_counts,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"],
        "vs_distributions": {**prev_dists, "disease_overview": vs_result} if vs_result else prev_dists,
        "vs_used": state.get("vs_used", False) or (vs_result is not None),
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

    vs_result = None
    if await vs_is_available():
        vs_result = await vs_generate(
            prompt=prompt, phase="needs_assessment", k=5, system_prompt=system,
        )
    if vs_result and vs_result.get("items"):
        selected = await vs_select(vs_result["distribution_id"], strategy="argmax")
        content_text = (selected["selected"]["content"] if selected and selected.get("selected")
                        else vs_result["items"][0]["content"])
        result = {"content": content_text, "total_tokens": 0, "cost": 0.0}
    else:
        result = await llm.generate(system, prompt, {"step": "treatment_landscape"})
        vs_result = None

    content = result["content"].strip()
    word_count = count_words(content)

    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_dists = state.get("vs_distributions", {})
    section_counts = state.get("section_word_counts", {})
    section_counts["treatment_landscape"] = word_count

    return {
        "treatment_landscape": content,
        "section_word_counts": section_counts,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"],
        "vs_distributions": {**prev_dists, "treatment_landscape": vs_result} if vs_result else prev_dists,
        "vs_used": state.get("vs_used", False) or (vs_result is not None),
    }


@traceable(name="generate_practice_gaps_node", run_type="chain")
async def generate_practice_gaps_node(state: NeedsAssessmentState) -> dict:
    """Generate Practice Gaps section (300-400 words)."""
    
    gaps = state.get("gaps", [])
    character_name = state.get("character_name", "the patient")
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

    vs_result = None
    if await vs_is_available():
        vs_result = await vs_generate(
            prompt=prompt, phase="needs_assessment", k=5, system_prompt=system,
        )
    if vs_result and vs_result.get("items"):
        selected = await vs_select(vs_result["distribution_id"], strategy="argmax")
        content_text = (selected["selected"]["content"] if selected and selected.get("selected")
                        else vs_result["items"][0]["content"])
        result = {"content": content_text, "total_tokens": 0, "cost": 0.0}
    else:
        result = await llm.generate(system, prompt, {"step": "practice_gaps"})
        vs_result = None

    content = result["content"].strip()
    word_count = count_words(content)

    appearances = state.get("character_appearances", 0)
    if character_name.split()[0] in content or character_name in content:
        appearances += 1

    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_dists = state.get("vs_distributions", {})
    section_counts = state.get("section_word_counts", {})
    section_counts["practice_gaps"] = word_count

    return {
        "practice_gaps_section": content,
        "character_appearances": appearances,
        "section_word_counts": section_counts,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"],
        "vs_distributions": {**prev_dists, "practice_gaps": vs_result} if vs_result else prev_dists,
        "vs_used": state.get("vs_used", False) or (vs_result is not None),
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
    
    character_name = state.get("character_name", "the patient")
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
    
    character_name = state.get("character_name", "the patient")
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
@traced_node("needs_assessment_agent", "assemble_document_node")
async def assemble_document_node(state: NeedsAssessmentState) -> dict:
    """Assemble complete document body (without references) and run quality checks."""

    sections = [
        state.get("cold_open", ""),
        "",
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


@traceable(name="generate_references_node", run_type="chain")
@traced_node("needs_assessment_agent", "generate_references_node")
async def generate_references_node(state: NeedsAssessmentState) -> dict:
    """Generate PubMed-verified AMA references for the full document."""
    document = state.get("complete_document", "")
    disease_state = state.get("disease_state", "")

    refs_text, _, _ = await build_references_section(document, disease_state)
    final_document = document + refs_text

    return {
        "complete_document": final_document,
        "messages": [HumanMessage(content=f"---\n\n# Complete Needs Assessment Document\n\n{final_document}")],
    }


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def create_needs_assessment_graph() -> StateGraph:
    """Create the Needs Assessment Agent graph."""
    
    graph = StateGraph(NeedsAssessmentState)
    
    # Add nodes
    graph.add_node("extract_topic", extract_topic_node)
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
    graph.add_node("generate_references", generate_references_node)

    # Add edges (sequential flow)
    graph.set_entry_point("extract_topic")
    graph.add_edge("extract_topic", "create_character")
    graph.add_edge("create_character", "generate_cold_open")
    graph.add_edge("generate_cold_open", "generate_disease_overview")
    graph.add_edge("generate_disease_overview", "generate_treatment_options")
    graph.add_edge("generate_treatment_options", "generate_practice_gaps")
    graph.add_edge("generate_practice_gaps", "generate_barriers")
    graph.add_edge("generate_barriers", "generate_educational_rationale")
    graph.add_edge("generate_educational_rationale", "generate_target_audience")
    graph.add_edge("generate_target_audience", "generate_conclusion")
    graph.add_edge("generate_conclusion", "assemble_document")
    graph.add_edge("assemble_document", "generate_references")
    graph.add_edge("generate_references", END)
    
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
            "therapeutic_area": "pulmonology",
            "disease_state": "chronic obstructive pulmonary disease (COPD)",
            "target_audience": "primary care physicians and pulmonologists",
            "geographic_focus": "United States",
            "activity_title": "Optimizing COPD Management in Primary Care",
            "accreditation_types": ["AMA PRA Category 1"],
            "gaps": [
                {
                    "gap_statement": "Underutilization of triple inhaled therapy in eligible GOLD group E patients",
                    "evidence_summary": "Only 31% of eligible patients receive triple therapy",
                    "patient_impact": "Increased exacerbations and hospitalizations"
                },
                {
                    "gap_statement": "Delayed referral for pulmonary rehabilitation",
                    "evidence_summary": "Fewer than 4% of eligible patients are referred within 90 days of an exacerbation",
                    "patient_impact": "Preventable functional decline and readmission"
                }
            ],
            "research_summary": "COPD affects approximately 16 million diagnosed Americans and remains the fourth leading cause of death in the United States.",
            "clinical_barriers": ["Time constraints", "Complex guidelines", "Competing priorities"],
            "epidemiology": {
                "prevalence": "16 million diagnosed Americans",
                "mortality": "fourth leading cause of US death",
                "cost": "approximately $50 billion annually"
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
