# Agent 11: Prose Quality Agent
## Writing Quality Enforcement (Two-Pass)

**Agent Type:** LLM-powered (specialized)  
**Complexity:** Medium  
**Primary Output:** Quality score with pass/fail and revision feedback
**Execution Points:** After Needs Assessment (Pass 1), After Grant Writer (Pass 2)

---

## Role Definition

The Prose Quality Agent enforces writing standards across all generated content. It runs at two critical points in the pipeline: after the Needs Assessment to catch issues early, and after Grant Assembly to ensure the complete package meets standards. This agent is the primary guardian against AI writing patterns and ensures pharmaceutical-grade prose quality.

---

## Execution Points

### Pass 1: Post-Needs Assessment
- **Trigger:** After Agent 5 completes
- **Scope:** Needs Assessment document only
- **Purpose:** Catch issues before downstream agents build on flawed foundation

### Pass 2: Post-Grant Assembly
- **Trigger:** After Agent 10 completes
- **Scope:** Complete grant package
- **Purpose:** Final quality check before compliance review

---

## Inputs

### Pass 1
| Source | Data |
|--------|------|
| Needs Assessment Agent (5) | Complete needs assessment document |

### Pass 2
| Source | Data |
|--------|------|
| Grant Writer Agent (10) | Complete assembled grant package |

### Required Shared Resources
- **writing-style-guide.md**: Banned patterns, prose requirements
- **cold-open-framework.md**: Cold open specifications

---

## Outputs

### Quality Assessment Structure

```yaml
prose_quality_output:
  metadata:
    agent_version: "2.0"
    execution_timestamp: datetime
    pass_number: int  # 1 or 2
    scope: str  # "needs_assessment" or "full_package"
  
  overall_result:
    passed: bool
    score: float  # 0-100
    summary: str
  
  prose_density:
    score: float  # Percentage of flowing prose vs lists/bullets
    target: float  # 80%
    passed: bool
    problem_sections: List[str]
  
  word_counts:
    total: int
    by_section:
      - section: str
        count: int
        minimum: int
        passed: bool
    overall_passed: bool
  
  ai_pattern_detection:
    patterns_found: List[Dict]
    # Each pattern:
    #   - pattern_name: str
    #   - instances: List[str]  # Exact text found
    #   - locations: List[str]  # Section where found
    total_violations: int
    passed: bool  # Must be 0
  
  cold_open_analysis:  # Pass 1 only
    present: bool
    word_count: int
    word_count_valid: bool  # 50-100
    has_character: bool
    has_humanizing_detail: bool
    has_turn: bool
    passed: bool
  
  character_thread:
    appearances: int
    minimum_required: int  # 4
    locations: List[str]
    passed: bool
  
  citation_density:
    citations_found: int
    uncited_claims: List[str]
    passed: bool
  
  revision_instructions:
    # Only populated if passed: false
    priority_issues: List[Dict]
    # Each issue:
    #   - issue_type: str
    #   - severity: str  # "critical", "major", "minor"
    #   - description: str
    #   - location: str
    #   - suggested_fix: str
    specific_patterns_to_remove: List[str]
    sections_requiring_expansion: List[str]
```

---

## System Prompt

```
You are a prose quality analyst enforcing pharmaceutical-grade writing standards for continuing medical education grant applications. Your review must be:

1. RIGOROUS: Every banned pattern must be detected
2. QUANTITATIVE: Provide specific counts and percentages
3. ACTIONABLE: Revision instructions must be specific and implementable
4. CONSISTENT: Apply the same standards uniformly

BANNED PATTERNS (Zero Tolerance):
- Em dashes (—) in any context
- "Delve into" or "delve deeper" or "delving"
- "It's important to note that" or variations
- "Furthermore," or "Moreover," or "Additionally," as paragraph starters
- "In today's healthcare landscape" or "In today's [anything] landscape"
- Colons in section titles (e.g., "Overview: The Problem")
- "Robust" used as generic intensifier
- "Leverage" used as a verb
- "Holistic" in any context
- "Paradigm" or "paradigm shift"
- "Cutting-edge" or "state-of-the-art"
- "Myriad" (especially "myriad of")
- "Plethora"
- "Multifaceted"
- "Crucial" or "critical" overuse (more than once per 500 words)
- "Navigate" used metaphorically
- "Landscape" used metaphorically (as in "treatment landscape")
- Generic phrases: "studies show," "research indicates" without naming the study

PROSE DENSITY REQUIREMENTS:
- 80% minimum flowing prose
- Lists/bullets only when truly list-appropriate
- No single-sentence paragraphs
- Minimum 4 sentences per paragraph
- Data woven into sentences, not itemized

COLD OPEN REQUIREMENTS (Pass 1):
- Must be present (no header)
- 50-100 words exactly
- Named character with age
- One humanizing detail
- Present tense
- The turn connecting individual to population

CHARACTER THREAD REQUIREMENTS:
- Minimum 4 appearances across document
- Natural integration, not forced
- Final appearance forward-looking

WORD COUNT REQUIREMENTS:
Pass 1 (Needs Assessment):
- Total: ≥3,100 words
- Cold open: 50-100 words

Pass 2 (Full Package):
- Needs Assessment: ≥3,100 words
- Executive Summary: 500-600 words
- Cover Letter: 300-400 words

OUTPUT:
Provide detailed assessment with specific revision instructions if failing. Be precise about what must change and where.
```

---

## Detection Algorithms

### AI Pattern Detection

```python
BANNED_PATTERNS = {
    "em_dash": r"—",
    "delve": r"\bdelv(e|ing|ed|es)\b",
    "important_to_note": r"it['']?s important to note",
    "furthermore_starter": r"^Furthermore,",
    "moreover_starter": r"^Moreover,",
    "additionally_starter": r"^Additionally,",
    "today_landscape": r"in today['']?s .* landscape",
    "colon_title": r"^[A-Z][^:]+:\s*[A-Z]",  # Title: Subtitle pattern
    "robust_generic": r"\brobust\b(?! (security|encryption|algorithm))",
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
}

def detect_patterns(text: str) -> List[Dict]:
    """Detect all banned patterns in text."""
    violations = []
    for pattern_name, regex in BANNED_PATTERNS.items():
        matches = re.finditer(regex, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            violations.append({
                "pattern_name": pattern_name,
                "instance": match.group(),
                "position": match.start(),
                "context": text[max(0, match.start()-50):match.end()+50]
            })
    return violations
```

### Prose Density Calculation

```python
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
            re.match(r'^\d+[\.\)]\s', stripped) or
            stripped.startswith('|')  # Table row
        )
        
        if not is_list:
            prose_chars += len(stripped)
    
    return (prose_chars / total_chars * 100) if total_chars > 0 else 0
```

### Cold Open Validation

```python
def validate_cold_open(text: str) -> Dict:
    """Validate cold open meets all requirements."""
    # Cold open is text before first heading
    first_heading_match = re.search(r'^#+\s', text, re.MULTILINE)
    if first_heading_match:
        cold_open = text[:first_heading_match.start()].strip()
    else:
        cold_open = text[:500]  # Fallback
    
    words = cold_open.split()
    word_count = len(words)
    
    # Check for character indicators
    has_name = bool(re.search(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', cold_open))  # Name pattern
    has_age = bool(re.search(r'\b\d{1,3}[,\s-]*(year|years|-year-old)\b', cold_open))
    
    # Check for "the turn" - connection to population
    turn_patterns = [
        r'one of [\d,]+ (million|thousand)',
        r'across the (country|nation|world)',
        r'(million|thousand)s? (of )?(patients|people|Americans)',
        r'like (him|her|them)',
    ]
    has_turn = any(re.search(p, cold_open, re.IGNORECASE) for p in turn_patterns)
    
    return {
        "present": len(cold_open) > 50,
        "word_count": word_count,
        "word_count_valid": 50 <= word_count <= 100,
        "has_character": has_name,
        "has_age": has_age,
        "has_turn": has_turn,
        "passed": all([
            len(cold_open) > 50,
            50 <= word_count <= 100,
            has_name,
            has_turn
        ])
    }
```

---

## Execution Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  1. Receive input document(s)       │
│     - Determine pass number (1 or 2)│
│     - Parse into sections           │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  2. Calculate prose density         │
│     - Per section                   │
│     - Overall                       │
│     - Flag sections below threshold │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  3. Count words                     │
│     - Per section                   │
│     - Compare to minimums           │
│     - Flag deficient sections       │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  4. Detect AI patterns              │
│     - Run all pattern detectors     │
│     - Log every instance            │
│     - Extract context for feedback  │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  5. Validate cold open (Pass 1)     │
│     - Check presence                │
│     - Validate word count           │
│     - Check character elements      │
│     - Verify the turn               │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  6. Track character thread          │
│     - Find all character mentions   │
│     - Count appearances             │
│     - Note locations                │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  7. Check citation density          │
│     - Identify statistical claims   │
│     - Verify citations present      │
│     - Flag uncited claims           │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  8. Calculate overall score         │
│     - Aggregate all metrics         │
│     - Determine pass/fail           │
│     - Weight by severity            │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  9. Generate revision instructions  │
│     (If failed)                     │
│     - Prioritize issues             │
│     - Provide specific fixes        │
│     - Include exact locations       │
└─────────────────────────────────────┘
  │
  ▼
OUTPUT: prose_quality_output
```

---

## Scoring Rubric

### Pass/Fail Determination

| Criterion | Weight | Pass Threshold |
|-----------|--------|----------------|
| AI Pattern Count | Critical | Must be 0 |
| Prose Density | High | ≥80% |
| Word Count | High | Meet all minimums |
| Cold Open (Pass 1) | High | All criteria met |
| Character Thread | Medium | ≥4 appearances |
| Citation Density | Medium | No uncited statistics |

### Overall Score Calculation

```python
def calculate_overall_score(metrics: Dict) -> float:
    """Calculate weighted overall score (0-100)."""
    weights = {
        "ai_patterns": 30,  # -30 if any found
        "prose_density": 25,
        "word_count": 20,
        "cold_open": 15,  # Pass 1 only
        "character_thread": 10,
    }
    
    score = 100
    
    # AI patterns: binary (pass or heavy penalty)
    if metrics["ai_patterns"]["total_violations"] > 0:
        score -= weights["ai_patterns"]
    
    # Prose density: proportional
    density_score = min(metrics["prose_density"]["score"] / 80 * weights["prose_density"], 
                        weights["prose_density"])
    score -= (weights["prose_density"] - density_score)
    
    # Word count: binary per section
    if not metrics["word_counts"]["overall_passed"]:
        score -= weights["word_count"]
    
    # Cold open (Pass 1)
    if metrics.get("cold_open") and not metrics["cold_open"]["passed"]:
        score -= weights["cold_open"]
    
    # Character thread
    if not metrics["character_thread"]["passed"]:
        score -= weights["character_thread"]
    
    return max(score, 0)
```

---

## Revision Instruction Generation

### Priority Classification

| Severity | Description | Examples |
|----------|-------------|----------|
| Critical | Must fix to pass | AI patterns, missing cold open |
| Major | Significantly impacts quality | Low prose density, missing word count |
| Minor | Should fix but not blocking | Character thread at 3 instead of 4 |

### Instruction Template

```yaml
revision_instructions:
  priority_issues:
    - issue_type: "ai_pattern"
      severity: "critical"
      description: "Found 'delve into' pattern"
      location: "Disease State Overview, paragraph 3"
      instance: "...we must delve into the complexities..."
      suggested_fix: "Replace with: 'examine', 'explore', 'investigate', or restructure sentence"
    
    - issue_type: "prose_density"
      severity: "major"
      description: "Practice Gaps section is 62% prose (below 80% threshold)"
      location: "Practice Gaps section"
      suggested_fix: "Convert bullet list of gaps into flowing narrative paragraphs"
    
    - issue_type: "word_count"
      severity: "major"
      description: "Barriers section is 320 words (minimum 400)"
      location: "Barriers to Optimal Care"
      suggested_fix: "Expand with additional barrier evidence and connection to gaps"
```

---

## Quality Criteria

### Agent Performance
- [ ] All banned patterns detected (zero false negatives)
- [ ] Prose density calculated accurately
- [ ] Word counts exact
- [ ] Cold open validation comprehensive
- [ ] Character thread tracking complete
- [ ] Revision instructions are actionable

### Output Quality
- [ ] Pass/fail determination is correct
- [ ] Score reflects actual quality
- [ ] Revision instructions are specific
- [ ] Locations are precise
- [ ] Suggested fixes are appropriate

---

## Error Handling

| Error | Response |
|-------|----------|
| Document parsing failure | Return error, request resubmission |
| Section boundaries unclear | Use best-effort parsing, note in output |
| Character name ambiguous | Flag for human verification |
| Edge case pattern | Include in output, note uncertainty |

---

## Dependencies

### Upstream
- Pass 1: Needs Assessment Agent (5)
- Pass 2: Grant Writer Agent (10)

### Downstream
- Pass 1: Learning Objectives Agent (6) — if pass
- Pass 2: Compliance Review Agent (12) — if pass
- Return to source agent — if fail

---

## Testing Scenarios

### Test Case 1: Clean Document
- Input: Document with no violations
- Expected: Pass with score ≥95

### Test Case 2: Multiple AI Patterns
- Input: Document with 5+ banned patterns
- Expected: Fail, all patterns identified with locations

### Test Case 3: Low Prose Density
- Input: Document with excessive bullets
- Expected: Fail, sections flagged for conversion

### Test Case 4: Borderline Word Count
- Input: Document at exactly minimum word counts
- Expected: Pass (meets threshold)

---

*The Prose Quality Agent is the guardian of writing standards. Its rigor determines the professionalism of the final output.*
