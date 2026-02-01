# Agent 12: Compliance Review Agent
## ACCME Standards, Independence, Fair Balance

**Agent Type:** LLM-powered (specialized)  
**Complexity:** Medium  
**Primary Output:** Compliance assessment with pass/fail and remediation guidance

---

## Role Definition

The Compliance Review Agent is the final quality gate before human review. It verifies that the complete grant package meets all ACCME accreditation standards, maintains independence from commercial supporter influence, demonstrates fair balance, and adheres to regulatory requirements. This agent protects both the educational mission and organizational accreditation.

---

## Inputs

### From Other Agents
| Agent | Data Used |
|-------|-----------|
| Grant Writer Agent (10) | Complete assembled grant package |
| Prose Quality Agent (11) | Prose quality confirmation (must have passed) |

### From Intake Form
| Field | Section | Purpose |
|-------|---------|---------|
| supporter_company | C | Identify potential bias sources |
| supporter_products | C | Flag for balance review |
| competitor_products | F | Verify balanced coverage |
| accreditation_types | E | Compliance standard selection |
| off_label_content | E | Off-label use requirements |

---

## Outputs

### Compliance Assessment Structure

```yaml
compliance_output:
  metadata:
    agent_version: "2.0"
    execution_timestamp: datetime
    standards_applied: List[str]  # ["ACCME", "AMA", "ANCC", etc.]
  
  overall_result:
    compliant: bool
    score: float  # 0-100
    summary: str
    certification_ready: bool
  
  accme_standards:
    standard_1:  # Independence
      compliant: bool
      findings: List[str]
      evidence: str
    standard_2:  # Resolution of COI
      compliant: bool
      findings: List[str]
      evidence: str
    standard_3:  # Appropriate content
      compliant: bool
      findings: List[str]
      evidence: str
    standard_4:  # Educational format
      compliant: bool
      findings: List[str]
      evidence: str
    standard_5:  # Evaluation/outcomes
      compliant: bool
      findings: List[str]
      evidence: str
    standard_6:  # Commercial support
      compliant: bool
      findings: List[str]
      evidence: str
  
  independence_analysis:
    supporter_mentioned_appropriately: bool
    no_product_promotion: bool
    control_retained: bool
    content_balanced: bool
    findings: List[str]
  
  fair_balance_analysis:
    supporter_products_coverage: str  # "balanced", "favored", "excluded"
    competitor_products_coverage: str
    treatment_alternatives_presented: bool
    limitations_acknowledged: bool
    findings: List[str]
  
  commercial_bias_detection:
    bias_indicators_found: List[Dict]
    # Each indicator:
    #   - type: str
    #   - location: str
    #   - text: str
    #   - severity: str
    total_issues: int
    passed: bool
  
  disclosure_verification:
    faculty_disclosures_present: bool
    planning_committee_disclosures: bool
    support_disclosure_present: bool
    disclosure_format_correct: bool
    findings: List[str]
  
  objective_alignment:
    objectives_properly_formatted: bool
    objectives_measurable: bool
    objectives_gap_aligned: bool
    findings: List[str]
  
  off_label_compliance:  # If applicable
    off_label_identified: bool
    proper_disclosure: bool
    evidence_based: bool
    findings: List[str]
  
  remediation_required:
    issues: List[Dict]
    # Each issue:
    #   - category: str
    #   - severity: str  # "critical", "major", "minor"
    #   - description: str
    #   - location: str
    #   - required_action: str
    #   - responsible_agent: str  # Which agent should fix
  
  certification_statement:
    ready_for_certification: bool
    conditions: List[str]  # If any
    recommended_credits: float
    credit_type: str
```

---

## System Prompt

```
You are a CME compliance specialist reviewing grant packages for ACCME accreditation standards and commercial independence. Your review must be:

1. THOROUGH: Every ACCME standard must be verified
2. OBJECTIVE: Apply standards consistently without bias
3. PROTECTIVE: Identify any content that could jeopardize accreditation
4. ACTIONABLE: Provide clear remediation guidance for any issues

ACCME STANDARDS FOR INDEPENDENCE:

Standard 1 - Independence:
- The provider must ensure that CME activities are independent of commercial interests
- Commercial interests cannot control content, faculty selection, or educational methods
- Verify: No evidence of supporter control over content

Standard 2 - Resolution of Personal COI:
- All planners and faculty must disclose relevant financial relationships
- Conflicts must be identified and resolved
- Verify: Disclosure process described, resolution mechanisms in place

Standard 3 - Content Appropriate:
- Content must be valid, based on evidence accepted in the profession
- Content must be balanced and objective
- Verify: Evidence-based claims, balanced presentation

Standard 4 - Educational Format:
- Format must be appropriate for content and learner needs
- Interactive formats encouraged for higher-level outcomes
- Verify: Format matches objectives, learner-centered design

Standard 5 - Evaluation:
- Provider must evaluate outcomes and use data for improvement
- Verify: Evaluation plan present, outcomes measurable

Standard 6 - Commercial Support:
- Written agreement required documenting independence
- Support must be disclosed to learners
- Verify: Disclosure language present, appropriate acknowledgment

COMMERCIAL BIAS INDICATORS:
- Unbalanced presentation favoring supporter products
- Omission of competitor products without clinical justification
- Promotional language about any commercial product
- Trade names used preferentially over generic names
- Efficacy claims without balanced safety/limitation discussion
- Cherry-picked data favoring supporter products

FAIR BALANCE REQUIREMENTS:
- All relevant treatment options discussed
- Efficacy AND safety/limitations for all options
- No preferential treatment of supporter products
- Competitor products included where clinically relevant
- Therapeutic alternatives presented objectively

OUTPUT:
Provide comprehensive compliance assessment. For any non-compliant findings, specify exact location, issue, and required remediation action.
```

---

## ACCME Standards Verification

### Standard 1: Independence Checklist

```python
INDEPENDENCE_CHECKS = [
    {
        "check": "content_control",
        "description": "Provider retains control of content",
        "indicators": [
            "Educational design determined by planning committee",
            "Faculty selected based on expertise, not commercial relationships",
            "Content based on best available evidence"
        ],
        "red_flags": [
            "Supporter-provided slides or materials",
            "Supporter-selected faculty",
            "Content aligned exclusively with supporter messaging"
        ]
    },
    {
        "check": "no_promotional_content",
        "description": "No promotional or marketing content",
        "indicators": [
            "Scientific/clinical focus throughout",
            "Generic names used appropriately",
            "Balanced presentation of options"
        ],
        "red_flags": [
            "Trade name preference without justification",
            "Marketing language or claims",
            "Promotional slides or imagery"
        ]
    },
    {
        "check": "supporter_separation",
        "description": "Appropriate separation from commercial supporter",
        "indicators": [
            "Support acknowledged but not emphasized",
            "No supporter involvement in content decisions",
            "Clear educational (not promotional) intent"
        ],
        "red_flags": [
            "Excessive supporter acknowledgment",
            "Supporter logo prominence",
            "Supporter messaging integration"
        ]
    }
]
```

### Standard 3: Content Appropriateness

```python
CONTENT_CHECKS = [
    {
        "check": "evidence_based",
        "description": "Content based on accepted evidence",
        "verification": [
            "Citations from peer-reviewed sources",
            "Guideline references current and accurate",
            "Claims supported by referenced data"
        ]
    },
    {
        "check": "balanced_objective",
        "description": "Content is balanced and objective",
        "verification": [
            "Multiple treatment options presented",
            "Benefits AND risks discussed for all options",
            "No preferential presentation"
        ]
    },
    {
        "check": "free_from_bias",
        "description": "Content free of commercial bias",
        "verification": [
            "No unsubstantiated superiority claims",
            "Limitations acknowledged",
            "Competitor products included fairly"
        ]
    }
]
```

---

## Bias Detection Patterns

### Commercial Bias Indicators

```python
BIAS_PATTERNS = {
    "promotional_language": [
        r"\bfirst[- ]in[- ]class\b",
        r"\bbest[- ]in[- ]class\b",
        r"\bbreakthrough\b",
        r"\bground[- ]?breaking\b",
        r"\brevolutionary\b",
        r"\bgame[- ]?changer\b",
        r"\bunprecedented efficacy\b",
        r"\bsuperior to\b(?! in specific .* trials?)",  # Without trial reference
    ],
    "unbalanced_presentation": [
        # Pattern: Supporter product positive, competitor negative
        r"unlike\s+\[competitor\],?\s+\[supporter product\]\s+(offers|provides|delivers)",
        r"\[competitor\]\s+fails?\s+to",
    ],
    "trade_name_preference": [
        # Using trade names when generics would be appropriate
        # Detected by ratio of trade:generic mentions
    ],
    "cherry_picked_data": [
        # Single study emphasis without meta-context
        r"the (study|trial) showed",  # Without "studies" plural or systematic review
    ],
    "omitted_safety": [
        # Efficacy claims without corresponding safety discussion
    ]
}

def detect_bias(text: str, supporter_products: List[str], 
                competitor_products: List[str]) -> List[Dict]:
    """Detect commercial bias indicators in text."""
    issues = []
    
    # Check promotional language
    for pattern_name, patterns in BIAS_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                issues.append({
                    "type": pattern_name,
                    "text": match.group(),
                    "context": text[max(0, match.start()-100):match.end()+100],
                    "severity": "major"
                })
    
    # Check mention balance
    supporter_mentions = sum(text.lower().count(p.lower()) for p in supporter_products)
    competitor_mentions = sum(text.lower().count(p.lower()) for p in competitor_products)
    
    if supporter_mentions > 0 and competitor_mentions == 0:
        issues.append({
            "type": "competitor_omission",
            "text": f"Supporter products mentioned {supporter_mentions} times, competitors 0 times",
            "severity": "major"
        })
    elif supporter_mentions > competitor_mentions * 3:
        issues.append({
            "type": "imbalanced_coverage",
            "text": f"Supporter:Competitor mention ratio is {supporter_mentions}:{competitor_mentions}",
            "severity": "minor"
        })
    
    return issues
```

---

## Execution Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  1. Receive grant package           │
│     - Verify prose quality passed   │
│     - Parse all sections            │
│     - Extract supporter/product info│
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  2. Verify ACCME Standard 1         │
│     (Independence)                  │
│     - Check content control         │
│     - Verify no promotional content │
│     - Assess supporter separation   │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  3. Verify ACCME Standard 2         │
│     (COI Resolution)                │
│     - Check disclosure presence     │
│     - Verify resolution process     │
│     - Confirm policy description    │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  4. Verify ACCME Standard 3         │
│     (Appropriate Content)           │
│     - Check evidence basis          │
│     - Verify balance/objectivity    │
│     - Detect commercial bias        │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  5. Verify ACCME Standard 4         │
│     (Educational Format)            │
│     - Check format appropriateness  │
│     - Verify objective alignment    │
│     - Assess learner-centeredness   │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  6. Verify ACCME Standard 5         │
│     (Evaluation)                    │
│     - Check outcomes plan           │
│     - Verify measurability          │
│     - Confirm improvement focus     │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  7. Verify ACCME Standard 6         │
│     (Commercial Support)            │
│     - Check disclosure language     │
│     - Verify acknowledgment format  │
│     - Confirm agreement reference   │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  8. Fair balance analysis           │
│     - Compare product coverage      │
│     - Check treatment alternatives  │
│     - Verify limitation discussion  │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  9. Off-label compliance            │
│     (If applicable)                 │
│     - Identify off-label content    │
│     - Verify proper disclosure      │
│     - Check evidence basis          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  10. Generate compliance report     │
│      - Aggregate all findings       │
│      - Determine overall compliance │
│      - Create remediation plan      │
│      - Certification recommendation │
└─────────────────────────────────────┘
  │
  ▼
OUTPUT: compliance_output
```

---

## Quality Criteria

### Compliance Determination

| Standard | Weight | Pass Threshold |
|----------|--------|----------------|
| Standard 1 (Independence) | Critical | Must pass |
| Standard 2 (COI Resolution) | Critical | Must pass |
| Standard 3 (Content) | Critical | Must pass |
| Standard 4 (Format) | High | Should pass |
| Standard 5 (Evaluation) | High | Should pass |
| Standard 6 (Commercial Support) | Critical | Must pass |
| Fair Balance | Critical | Must pass |
| Commercial Bias | Critical | Zero major issues |

### Overall Compliance Score

```python
def calculate_compliance_score(results: Dict) -> float:
    """Calculate overall compliance score."""
    critical_standards = [
        "standard_1", "standard_2", "standard_3", 
        "standard_6", "fair_balance", "commercial_bias"
    ]
    high_standards = ["standard_4", "standard_5"]
    
    score = 100
    
    # Critical standards: -20 each if failed
    for std in critical_standards:
        if not results[std]["compliant"]:
            score -= 20
    
    # High standards: -10 each if failed
    for std in high_standards:
        if not results[std]["compliant"]:
            score -= 10
    
    return max(score, 0)
```

---

## Remediation Routing

### Issue-to-Agent Mapping

| Issue Type | Responsible Agent | Action |
|------------|-------------------|--------|
| Commercial bias in needs assessment | Needs Assessment (5) | Remove biased language |
| Unbalanced product coverage | Research (2) / Grant Writer (10) | Add competitor coverage |
| Learning objective format | Learning Objectives (6) | Reformat objectives |
| Missing disclosures | Grant Writer (10) | Add disclosure section |
| Promotional language | Prose Quality (11) / Grant Writer (10) | Remove/revise |
| Missing evaluation plan | Protocol (8) | Enhance outcomes section |
| Off-label non-compliance | Grant Writer (10) | Add required disclosures |

---

## Example Output Excerpt

```yaml
overall_result:
  compliant: false
  score: 75
  summary: "Package fails compliance due to imbalanced product coverage and missing competitor discussion. Remediation required before human review."
  certification_ready: false

accme_standards:
  standard_1:
    compliant: true
    findings:
      - "Content control retained by planning committee"
      - "Faculty selection based on expertise"
    evidence: "Planning committee composition and selection criteria documented"
  
  standard_3:
    compliant: false
    findings:
      - "Supporter product mentioned 12 times; primary competitor mentioned 0 times"
      - "Treatment landscape section omits FDA-approved alternatives"
    evidence: "See fair_balance_analysis for details"

fair_balance_analysis:
  supporter_products_coverage: "favored"
  competitor_products_coverage: "absent"
  treatment_alternatives_presented: false
  limitations_acknowledged: true
  findings:
    - "Dapagliflozin discussed extensively (12 mentions)"
    - "Empagliflozin (competitor) not mentioned despite Class I indication"
    - "Treatment landscape should include all SGLT2 inhibitors"

commercial_bias_detection:
  bias_indicators_found:
    - type: "competitor_omission"
      location: "Treatment Landscape section"
      text: "Discussion of SGLT2 inhibitors mentions only dapagliflozin"
      severity: "major"
    - type: "imbalanced_coverage"
      location: "Throughout document"
      text: "12:0 supporter:competitor mention ratio"
      severity: "major"
  total_issues: 2
  passed: false

remediation_required:
  issues:
    - category: "fair_balance"
      severity: "critical"
      description: "Competitor SGLT2 inhibitors omitted from treatment discussion"
      location: "Treatment Landscape section"
      required_action: "Add balanced discussion of all FDA-approved SGLT2 inhibitors for heart failure"
      responsible_agent: "research_agent"
    
    - category: "commercial_bias"
      severity: "major"
      description: "Supporter product mentioned disproportionately"
      location: "Multiple sections"
      required_action: "Review all product mentions; ensure class-level discussion rather than brand-specific"
      responsible_agent: "grant_writer"
```

---

## Error Handling

| Error | Response |
|-------|----------|
| Missing sections | Flag incomplete, cannot fully assess compliance |
| Ambiguous product reference | Flag for human verification |
| Unknown accreditation type | Apply ACCME standards as default |
| Off-label status unclear | Flag for medical review |

---

## Dependencies

### Upstream
- Grant Writer Agent (10) — complete package
- Prose Quality Agent (11) — must have passed

### Downstream
- Human Review Gate — if compliant
- Appropriate remediation agent — if non-compliant

---

## Testing Scenarios

### Test Case 1: Compliant Package
- Input: Balanced, properly disclosed package
- Expected: Pass with score ≥90

### Test Case 2: Commercial Bias Present
- Input: Package with imbalanced product coverage
- Expected: Fail, bias issues identified

### Test Case 3: Missing Disclosures
- Input: Package missing required disclosure elements
- Expected: Fail, specific disclosures flagged

### Test Case 4: Off-Label Content
- Input: Package with off-label discussion
- Expected: Verify appropriate disclosures present

---

*The Compliance Review Agent protects organizational accreditation and educational integrity.*
