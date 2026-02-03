"""
DHG CME Prose Quality Agent - LangGraph Cloud
==============================================
Agent #11 in the 12-agent CME grant pipeline.

Enforces writing quality standards:
- AI pattern detection (zero tolerance)
- Prose density (80%+ required)
- Word count validation
- Cold open validation
- Character thread tracking
- Citation density

LANGGRAPH CLOUD READY:
- Pure LangGraph + LangSmith
- No Docker/FastAPI dependencies

Author: Digital Harmony Group
Version: 1.0.0
"""

import re
from datetime import datetime
from typing import Annotated, Optional, List, Dict, Any
from typing_extensions import TypedDict

# LangGraph imports
from langgraph.graph import StateGraph, END
from langsmith import traceable


# =============================================================================
# BANNED PATTERNS (Zero Tolerance)
# =============================================================================

BANNED_PATTERNS = {
    "em_dash": r"—",
    "delve": r"\bdelv(e|ing|ed|es)\b",
    "important_to_note": r"it['']?s important to note",
    "furthermore_starter": r"(?m)^Furthermore,",
    "moreover_starter": r"(?m)^Moreover,",
    "additionally_starter": r"(?m)^Additionally,",
    "today_landscape": r"in today['']?s .* landscape",
    "colon_title": r"(?m)^[A-Z][^:\n]+:\s*[A-Z]",
    "robust_generic": r"\brobust\b",
    "leverage_verb": r"\bleverag(e|ing|ed)\b",
    "holistic": r"\bholistic\b",
    "paradigm": r"\bparadigm\b",
    "cutting_edge": r"\bcutting[- ]edge\b",
    "state_of_art": r"\bstate[- ]of[- ]the[- ]art\b",
    "myriad": r"\bmyriad\b",
    "plethora": r"\bplethora\b",
    "multifaceted": r"\bmultifaceted\b",
    "navigate_metaphor": r"\bnavigate\b(?! (the|a|to) (website|page|menu|interface))",
    "landscape_metaphor": r"\b(treatment|healthcare|clinical|therapeutic) landscape\b",
    "studies_show": r"\bstudies (show|indicate|suggest|demonstrate)\b(?! \()",
    "research_indicates": r"\bresearch (shows|indicates|suggests)\b(?! \()",
    "best_practices": r"\bbest practices\b",
    "moving_forward": r"\bmoving forward\b",
    "at_end_of_day": r"\bat the end of the day\b",
    "goes_without_saying": r"\bit goes without saying\b",
    "underscores_importance": r"\bunderscores the importance\b",
    "serves_as_testament": r"\bserves as a testament\b",
}


# =============================================================================
# STATE DEFINITION
# =============================================================================

class ProseQualityState(TypedDict):
    """State for Prose Quality Agent."""
    
    # === INPUT ===
    document_text: str
    pass_number: int  # 1 = after needs assessment, 2 = after full package
    character_name: Optional[str]  # For tracking character thread
    
    # Section word count targets (from calling agent or defaults)
    section_targets: Dict[str, Dict[str, int]]  # {section: {min: x, max: y}}
    
    # === PROCESSING ===
    sections: Dict[str, str]  # Parsed sections
    
    # === OUTPUT ===
    overall_passed: bool
    overall_score: float
    summary: str
    
    # Prose density
    prose_density_score: float
    prose_density_passed: bool
    prose_density_by_section: Dict[str, float]
    problem_sections: List[str]
    
    # Word counts
    word_count_total: int
    word_count_by_section: Dict[str, int]
    word_count_passed: bool
    sections_under_minimum: List[str]
    
    # AI patterns
    ai_patterns_found: List[Dict[str, Any]]
    ai_patterns_count: int
    ai_patterns_passed: bool
    
    # Cold open (Pass 1 only)
    cold_open_present: bool
    cold_open_word_count: int
    cold_open_has_character: bool
    cold_open_has_turn: bool
    cold_open_passed: bool
    
    # Character thread
    character_appearances: int
    character_locations: List[str]
    character_thread_passed: bool
    
    # Revision instructions
    revision_instructions: List[Dict[str, Any]]
    
    # Metadata
    errors: List[str]


# =============================================================================
# DETECTION FUNCTIONS
# =============================================================================

def detect_ai_patterns(text: str) -> List[Dict[str, Any]]:
    """Detect all banned AI patterns in text."""
    violations = []
    for pattern_name, regex in BANNED_PATTERNS.items():
        try:
            matches = re.finditer(regex, text, re.IGNORECASE)
            for match in matches:
                start = max(0, match.start() - 40)
                end = min(len(text), match.end() + 40)
                violations.append({
                    "pattern_name": pattern_name,
                    "instance": match.group(),
                    "position": match.start(),
                    "context": f"...{text[start:end]}..."
                })
        except re.error:
            continue
    return violations


def calculate_prose_density(text: str) -> float:
    """Calculate percentage of text that is flowing prose vs lists/bullets."""
    lines = text.split('\n')
    prose_chars = 0
    total_chars = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        total_chars += len(stripped)
        
        # Detect list items
        is_list = (
            stripped.startswith(('-', '*', '•', '–')) or
            re.match(r'^\d+[\.)\]]\s', stripped) or
            stripped.startswith('|')  # Table row
        )
        
        if not is_list:
            prose_chars += len(stripped)
    
    return (prose_chars / total_chars * 100) if total_chars > 0 else 100.0


def calculate_prose_density_by_section(sections: Dict[str, str]) -> Dict[str, float]:
    """Calculate prose density for each section."""
    densities = {}
    for section_name, content in sections.items():
        densities[section_name] = calculate_prose_density(content)
    return densities


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def parse_sections(text: str) -> Dict[str, str]:
    """Parse document into sections by headers."""
    sections = {}
    current_section = "cold_open"
    current_content = []
    
    lines = text.split('\n')
    for line in lines:
        # Check for markdown headers
        header_match = re.match(r'^#+\s+(.+)$', line)
        if header_match:
            # Save previous section
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            
            # Start new section
            header_text = header_match.group(1).lower()
            # Normalize section names
            if 'disease' in header_text or 'overview' in header_text:
                current_section = "disease_state_overview"
            elif 'treatment' in header_text or 'landscape' in header_text:
                current_section = "treatment_landscape"
            elif 'gap' in header_text:
                current_section = "practice_gaps"
            elif 'barrier' in header_text:
                current_section = "barriers"
            elif 'education' in header_text or 'rationale' in header_text:
                current_section = "educational_rationale"
            elif 'audience' in header_text or 'target' in header_text:
                current_section = "target_audience"
            elif 'conclusion' in header_text:
                current_section = "conclusion"
            else:
                current_section = header_text.replace(' ', '_')[:30]
            
            current_content = []
        else:
            current_content.append(line)
    
    # Save last section
    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections


def validate_cold_open(text: str, character_name: Optional[str] = None) -> Dict[str, Any]:
    """Validate cold open meets all requirements."""
    # Cold open is text before first heading
    first_heading_match = re.search(r'^#+\s', text, re.MULTILINE)
    if first_heading_match:
        cold_open = text[:first_heading_match.start()].strip()
    else:
        cold_open = text[:500].strip()
    
    words = cold_open.split()
    word_count = len(words)
    
    # Check for character name if provided
    has_character = False
    if character_name:
        has_character = character_name in cold_open or character_name.split()[0] in cold_open
    else:
        # Check for name pattern (First Last)
        has_character = bool(re.search(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', cold_open))
    
    # Check for age
    has_age = bool(re.search(r'\b\d{1,3}[,\s-]*(year|years|-year-old)?\b', cold_open))
    
    # Check for "the turn" - connection to population
    turn_patterns = [
        r'one of [\d,]+ (million|thousand)',
        r'across the (country|nation|world)',
        r'(million|thousand)s? (of )?(patients|people|Americans)',
        r'like (him|her|them)',
        r'she is one of',
        r'he is one of',
    ]
    has_turn = any(re.search(p, cold_open, re.IGNORECASE) for p in turn_patterns)
    
    passed = all([
        len(cold_open) > 50,
        50 <= word_count <= 100,
        has_character,
        has_turn
    ])
    
    return {
        "present": len(cold_open) > 50,
        "word_count": word_count,
        "word_count_valid": 50 <= word_count <= 100,
        "has_character": has_character,
        "has_age": has_age,
        "has_turn": has_turn,
        "passed": passed
    }


def track_character_thread(text: str, character_name: str) -> Dict[str, Any]:
    """Track character appearances throughout document."""
    if not character_name:
        return {"appearances": 0, "locations": [], "passed": False}
    
    sections = parse_sections(text)
    appearances = 0
    locations = []
    
    first_name = character_name.split()[0] if character_name else ""
    
    for section_name, content in sections.items():
        if character_name in content or first_name in content:
            appearances += 1
            locations.append(section_name)
    
    return {
        "appearances": appearances,
        "locations": locations,
        "passed": appearances >= 4
    }


def calculate_overall_score(
    ai_patterns_count: int,
    prose_density: float,
    word_count_passed: bool,
    cold_open_passed: bool,
    character_thread_passed: bool,
    pass_number: int
) -> float:
    """Calculate weighted overall score (0-100)."""
    score = 100.0
    
    # AI patterns: -30 if any found
    if ai_patterns_count > 0:
        score -= 30
    
    # Prose density: proportional (25 points)
    density_score = min((prose_density / 80) * 25, 25)
    score -= (25 - density_score)
    
    # Word count: -20 if failed
    if not word_count_passed:
        score -= 20
    
    # Cold open (Pass 1 only): -15 if failed
    if pass_number == 1 and not cold_open_passed:
        score -= 15
    
    # Character thread: -10 if failed
    if not character_thread_passed:
        score -= 10
    
    return max(score, 0)


def generate_revision_instructions(
    ai_patterns: List[Dict],
    prose_density: float,
    problem_sections: List[str],
    sections_under_minimum: List[str],
    cold_open_result: Dict,
    character_result: Dict,
    pass_number: int
) -> List[Dict[str, Any]]:
    """Generate actionable revision instructions."""
    instructions = []
    
    # AI patterns (critical)
    for pattern in ai_patterns:
        instructions.append({
            "issue_type": "ai_pattern",
            "severity": "critical",
            "description": f"Found banned pattern: '{pattern['pattern_name']}'",
            "location": f"Position {pattern['position']}",
            "instance": pattern['instance'],
            "context": pattern['context'],
            "suggested_fix": f"Remove or replace '{pattern['instance']}' with appropriate alternative"
        })
    
    # Prose density issues (major)
    if prose_density < 80:
        for section in problem_sections:
            instructions.append({
                "issue_type": "prose_density",
                "severity": "major",
                "description": f"Section '{section}' has low prose density",
                "location": section,
                "suggested_fix": "Convert bullet points and lists to flowing narrative paragraphs"
            })
    
    # Word count issues (major)
    for section in sections_under_minimum:
        instructions.append({
            "issue_type": "word_count",
            "severity": "major",
            "description": f"Section '{section}' is under minimum word count",
            "location": section,
            "suggested_fix": "Expand section with additional detail and evidence"
        })
    
    # Cold open issues (Pass 1)
    if pass_number == 1 and not cold_open_result.get("passed", True):
        issues = []
        if not cold_open_result.get("word_count_valid"):
            issues.append(f"word count is {cold_open_result.get('word_count', 0)} (need 50-100)")
        if not cold_open_result.get("has_character"):
            issues.append("missing named character")
        if not cold_open_result.get("has_turn"):
            issues.append("missing 'the turn' connecting to population")
        
        instructions.append({
            "issue_type": "cold_open",
            "severity": "critical",
            "description": f"Cold open issues: {'; '.join(issues)}",
            "location": "Opening paragraph",
            "suggested_fix": "Revise cold open to include named character with age, humanizing detail, and population connection"
        })
    
    # Character thread (minor)
    if not character_result.get("passed", True):
        instructions.append({
            "issue_type": "character_thread",
            "severity": "minor",
            "description": f"Character appears {character_result.get('appearances', 0)} times (need 4+)",
            "location": "Throughout document",
            "suggested_fix": "Add character references in Disease Overview, Practice Gaps, Educational Rationale, and Conclusion"
        })
    
    return instructions


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="parse_document_node", run_type="chain")
async def parse_document_node(state: ProseQualityState) -> dict:
    """Parse document into sections."""
    text = state.get("document_text", "")
    sections = parse_sections(text)
    
    return {
        "sections": sections,
        "errors": []
    }


@traceable(name="check_ai_patterns_node", run_type="chain")
async def check_ai_patterns_node(state: ProseQualityState) -> dict:
    """Detect AI patterns in document."""
    text = state.get("document_text", "")
    patterns = detect_ai_patterns(text)
    
    return {
        "ai_patterns_found": patterns,
        "ai_patterns_count": len(patterns),
        "ai_patterns_passed": len(patterns) == 0
    }


@traceable(name="check_prose_density_node", run_type="chain")
async def check_prose_density_node(state: ProseQualityState) -> dict:
    """Calculate prose density."""
    text = state.get("document_text", "")
    sections = state.get("sections", {})
    
    overall_density = calculate_prose_density(text)
    density_by_section = calculate_prose_density_by_section(sections)
    
    # Find problem sections (below 80%)
    problem_sections = [
        section for section, density in density_by_section.items()
        if density < 80
    ]
    
    return {
        "prose_density_score": overall_density,
        "prose_density_passed": overall_density >= 80,
        "prose_density_by_section": density_by_section,
        "problem_sections": problem_sections
    }


@traceable(name="check_word_counts_node", run_type="chain")
async def check_word_counts_node(state: ProseQualityState) -> dict:
    """Check word counts against targets."""
    text = state.get("document_text", "")
    sections = state.get("sections", {})
    targets = state.get("section_targets", {})
    
    total_words = count_words(text)
    word_counts = {section: count_words(content) for section, content in sections.items()}
    
    # Check against targets
    sections_under = []
    for section, count in word_counts.items():
        if section in targets:
            min_words = targets[section].get("min", 0)
            if count < min_words:
                sections_under.append(section)
    
    # Default minimum total (varies by pass)
    pass_number = state.get("pass_number", 1)
    min_total = 3100 if pass_number == 1 else 4000
    
    # Consider passed if total meets minimum or all sections meet targets
    passed = total_words >= min_total or len(sections_under) == 0
    
    return {
        "word_count_total": total_words,
        "word_count_by_section": word_counts,
        "word_count_passed": passed,
        "sections_under_minimum": sections_under
    }


@traceable(name="check_cold_open_node", run_type="chain")
async def check_cold_open_node(state: ProseQualityState) -> dict:
    """Validate cold open (Pass 1 only)."""
    pass_number = state.get("pass_number", 1)
    
    if pass_number != 1:
        return {
            "cold_open_present": True,
            "cold_open_word_count": 0,
            "cold_open_has_character": True,
            "cold_open_has_turn": True,
            "cold_open_passed": True
        }
    
    text = state.get("document_text", "")
    character_name = state.get("character_name")
    
    result = validate_cold_open(text, character_name)
    
    return {
        "cold_open_present": result["present"],
        "cold_open_word_count": result["word_count"],
        "cold_open_has_character": result["has_character"],
        "cold_open_has_turn": result["has_turn"],
        "cold_open_passed": result["passed"]
    }


@traceable(name="check_character_thread_node", run_type="chain")
async def check_character_thread_node(state: ProseQualityState) -> dict:
    """Track character appearances."""
    text = state.get("document_text", "")
    character_name = state.get("character_name", "")
    
    if not character_name:
        return {
            "character_appearances": 0,
            "character_locations": [],
            "character_thread_passed": True  # Skip if no character provided
        }
    
    result = track_character_thread(text, character_name)
    
    return {
        "character_appearances": result["appearances"],
        "character_locations": result["locations"],
        "character_thread_passed": result["passed"]
    }


@traceable(name="calculate_score_node", run_type="chain")
async def calculate_score_node(state: ProseQualityState) -> dict:
    """Calculate overall score and generate instructions."""
    pass_number = state.get("pass_number", 1)
    
    # Calculate score
    score = calculate_overall_score(
        ai_patterns_count=state.get("ai_patterns_count", 0),
        prose_density=state.get("prose_density_score", 0),
        word_count_passed=state.get("word_count_passed", False),
        cold_open_passed=state.get("cold_open_passed", True),
        character_thread_passed=state.get("character_thread_passed", True),
        pass_number=pass_number
    )
    
    # Determine pass/fail
    passed = (
        state.get("ai_patterns_passed", False) and
        state.get("prose_density_passed", False) and
        state.get("word_count_passed", False) and
        (pass_number != 1 or state.get("cold_open_passed", True))
    )
    
    # Generate revision instructions if failed
    instructions = []
    if not passed:
        cold_open_result = {
            "passed": state.get("cold_open_passed", True),
            "word_count": state.get("cold_open_word_count", 0),
            "word_count_valid": 50 <= state.get("cold_open_word_count", 0) <= 100,
            "has_character": state.get("cold_open_has_character", True),
            "has_turn": state.get("cold_open_has_turn", True)
        }
        
        character_result = {
            "passed": state.get("character_thread_passed", True),
            "appearances": state.get("character_appearances", 0)
        }
        
        instructions = generate_revision_instructions(
            ai_patterns=state.get("ai_patterns_found", []),
            prose_density=state.get("prose_density_score", 0),
            problem_sections=state.get("problem_sections", []),
            sections_under_minimum=state.get("sections_under_minimum", []),
            cold_open_result=cold_open_result,
            character_result=character_result,
            pass_number=pass_number
        )
    
    # Generate summary
    issues = []
    if not state.get("ai_patterns_passed"):
        issues.append(f"{state.get('ai_patterns_count', 0)} AI patterns detected")
    if not state.get("prose_density_passed"):
        issues.append(f"prose density {state.get('prose_density_score', 0):.1f}% (need 80%+)")
    if not state.get("word_count_passed"):
        issues.append("word count below minimum")
    if pass_number == 1 and not state.get("cold_open_passed"):
        issues.append("cold open issues")
    if not state.get("character_thread_passed"):
        issues.append(f"character appears {state.get('character_appearances', 0)} times (need 4+)")
    
    if passed:
        summary = f"PASSED with score {score:.1f}/100. Document meets all quality standards."
    else:
        summary = f"FAILED with score {score:.1f}/100. Issues: {'; '.join(issues)}"
    
    return {
        "overall_passed": passed,
        "overall_score": score,
        "summary": summary,
        "revision_instructions": instructions
    }


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def create_prose_quality_graph() -> StateGraph:
    """Create the Prose Quality Agent graph."""
    
    graph = StateGraph(ProseQualityState)
    
    # Add nodes
    graph.add_node("parse_document", parse_document_node)
    graph.add_node("check_ai_patterns", check_ai_patterns_node)
    graph.add_node("check_prose_density", check_prose_density_node)
    graph.add_node("check_word_counts", check_word_counts_node)
    graph.add_node("check_cold_open", check_cold_open_node)
    graph.add_node("check_character_thread", check_character_thread_node)
    graph.add_node("calculate_score", calculate_score_node)
    
    # Define flow
    graph.set_entry_point("parse_document")
    graph.add_edge("parse_document", "check_ai_patterns")
    graph.add_edge("check_ai_patterns", "check_prose_density")
    graph.add_edge("check_prose_density", "check_word_counts")
    graph.add_edge("check_word_counts", "check_cold_open")
    graph.add_edge("check_cold_open", "check_character_thread")
    graph.add_edge("check_character_thread", "calculate_score")
    graph.add_edge("calculate_score", END)
    
    return graph


# Create compiled graph for LangGraph Cloud
graph = create_prose_quality_graph().compile()
