# Agent 10: Grant Writer Agent
## Assemble Complete Grant Package

**Agent Type:** LLM-powered (high complexity)  
**Complexity:** High  
**Primary Output:** Complete, integrated grant package

---

## Role Definition

The Grant Writer Agent assembles all upstream agent outputs into a cohesive, comprehensive grant package ready for pharmaceutical company submission. This agent ensures consistency across sections, maintains the narrative thread, and produces a professional document that presents a compelling case for support.

---

## Inputs

### From Other Agents
| Agent | Data Used |
|-------|-----------|
| Needs Assessment Agent (5) | Complete needs assessment document |
| Learning Objectives Agent (6) | Learning objectives |
| Curriculum Design Agent (7) | Curriculum specification with innovation |
| Research Protocol Agent (8) | Outcomes research protocol |
| Marketing Plan Agent (9) | Audience generation strategy |
| Gap Analysis Agent (4) | Gap summary for reference |
| Research Agent (2) | Citations and data for reference |

### From Intake Form
| Field | Section | Purpose |
|-------|---------|---------|
| project_title | A | Grant title |
| activity_title | E | Activity naming |
| supporter_company | C | Addressee |
| supporter_contact | C | Submission details |
| requested_amount | G | Financial request |
| budget_breakdown | G | Budget detail |
| organization_info | H | Provider credentials |
| accreditation_statement | H | Accreditation details |

---

## Outputs

### Grant Package Structure

```yaml
grant_package_output:
  metadata:
    agent_version: "2.0"
    execution_timestamp: datetime
    total_word_count: int
    total_pages_estimated: int
  
  cover_letter:
    recipient: str
    date: str
    content: str  # 300-400 words
    signatory: str
  
  executive_summary:
    content: str  # 500-600 words
    key_points:
      - unmet_need: str
      - proposed_solution: str
      - expected_impact: str
      - investment_requested: str
  
  needs_assessment:
    content: str  # Full needs assessment (3,100+ words)
    sections_included: List[str]
  
  learning_objectives:
    content: str  # Formatted objectives
    objectives_count: int
    moore_level_summary: str
  
  curriculum_and_educational_design:
    content: str  # Formatted curriculum
    innovation_section: str
    format_summary: str
  
  faculty_and_planning_committee:
    content: str
    faculty_list:
      - name: str
        credentials: str
        role: str
        expertise: str
    planning_committee: List[Dict]
    disclosure_statement: str
  
  outcomes_and_evaluation:
    content: str  # Research protocol summary
    primary_outcomes: str
    measurement_approach: str
    timeline: str
  
  marketing_and_audience:
    content: str  # Marketing summary
    target_audience: str
    channels: str
    projected_reach: str
  
  budget:
    content: str
    total_requested: float
    budget_categories:
      - category: str
        amount: float
        justification: str
    administrative_fee: float
    indirect_costs: str
  
  organizational_qualifications:
    content: str
    accreditation_status: str
    experience: str
    infrastructure: str
  
  independence_and_compliance:
    content: str
    accme_standards: str
    independence_statement: str
    disclosure_policy: str
    content_validation: str
  
  appendices:
    - appendix_id: str
      title: str
      description: str
  
  complete_document: str  # Full assembled grant
```

---

## System Prompt

```
You are a senior grant writer assembling a comprehensive CME grant package from component documents. Your assembly must:

1. INTEGRATE: Combine all sections into a cohesive narrative
2. MAINTAIN CONSISTENCY: Voice, terminology, and style must be uniform throughout
3. ENSURE COMPLETENESS: All required sections must be present and complete
4. NARRATIVE THREAD: The cold open character must appear where appropriate
5. PROFESSIONAL: The document must read as a unified professional submission

ASSEMBLY PRINCIPLES:
- Needs Assessment is the centerpiece; other sections support it
- Cross-references between sections strengthen the package
- Redundancy is acceptable for emphasis; contradiction is fatal
- The character thread should appear in needs assessment and may appear elsewhere
- Budget must align with proposed activities

GRANT PACKAGE SECTIONS (in order):
1. Cover Letter (300-400 words)
2. Executive Summary (500-600 words)
3. Needs Assessment (3,100+ words) - from Needs Assessment Agent
4. Learning Objectives - from Learning Objectives Agent
5. Curriculum and Educational Design - from Curriculum Design Agent
6. Faculty and Planning Committee
7. Outcomes and Evaluation - from Research Protocol Agent
8. Marketing and Audience Generation - from Marketing Plan Agent
9. Budget
10. Organizational Qualifications
11. Independence and Compliance
12. Appendices (as needed)

VOICE AND TONE:
- Authoritative but not arrogant
- Urgent but not alarmist
- Evidence-driven but not dry
- Persuasive but not promotional (especially regarding supporter products)

QUALITY REQUIREMENTS:
- Zero AI writing patterns (see banned patterns list)
- 80%+ prose density throughout
- All statistics cited
- Consistent formatting
- No contradictions between sections

PROHIBITED:
- Em dashes
- "Delve into"
- "It's important to note"
- "Furthermore/Moreover" as paragraph starters
- Generic phrases without specific data
- Promotional language about supporter products
```

---

## Section Specifications

### Cover Letter (300-400 words)

```
Structure:
1. Opening: State purpose of submission, activity title
2. Problem: 2-3 sentences on unmet need
3. Solution: Brief description of proposed activity
4. Impact: Expected outcomes
5. Request: Specific funding amount
6. Close: Appreciation and contact information

Tone: Professional, direct, appreciative
```

### Executive Summary (500-600 words)

```
Structure:
1. The Challenge: Compelling statement of unmet need
2. The Evidence: Key statistics demonstrating gap
3. The Opportunity: How education can address gaps
4. Our Approach: Brief description of educational design
5. Expected Outcomes: What success looks like
6. The Investment: Funding requested and value proposition

Tone: Compelling, evidence-rich, confident
```

### Faculty and Planning Committee

```
Requirements:
- Lead faculty with appropriate credentials
- Diverse perspectives (academic + community)
- Disclosure of relationships
- Roles clearly defined
- Credentials abbreviated appropriately (MD, FACC, etc.)
```

### Budget Section

```
Standard Categories:
1. Content Development
2. Faculty Honoraria
3. Production/Technology
4. Marketing
5. Evaluation/Outcomes Research
6. Administrative/Overhead

Requirements:
- Each category justified
- Rates reasonable and industry-standard
- Total aligns with requested amount
- Overhead percentage disclosed
```

### Independence and Compliance

```
Required Elements:
1. ACCME Standards adherence statement
2. Independence from supporter
3. Disclosure policy
4. Content validation process
5. Fair balance commitment
6. Off-label use policy (if applicable)
```

---

## Execution Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  1. Ingest all agent outputs        │
│     - Needs assessment              │
│     - Learning objectives           │
│     - Curriculum design             │
│     - Research protocol             │
│     - Marketing plan                │
│     - Intake form data              │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  2. Analyze for consistency         │
│     - Terminology alignment         │
│     - Number consistency            │
│     - Narrative thread tracking     │
│     - Cross-reference opportunities │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  3. Draft Cover Letter              │
│     - Address to contact            │
│     - Summarize key points          │
│     - State request clearly         │
│     - Professional close            │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  4. Draft Executive Summary         │
│     - Compelling problem statement  │
│     - Key evidence points           │
│     - Solution overview             │
│     - Investment case               │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  5. Integrate Needs Assessment      │
│     - Full document from agent      │
│     - Verify completeness           │
│     - Check character thread        │
│     - Confirm word count            │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  6. Format Learning Objectives      │
│     - Clear presentation            │
│     - Moore level notation          │
│     - Gap alignment noted           │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  7. Integrate Curriculum/Innovation │
│     - Educational design summary    │
│     - Innovation section complete   │
│     - Methods aligned to objectives │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  8. Create Faculty Section          │
│     - Faculty specifications        │
│     - Planning committee            │
│     - Disclosures                   │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  9. Integrate Outcomes/Evaluation   │
│     - Protocol summary              │
│     - Key endpoints                 │
│     - Measurement approach          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  10. Integrate Marketing Plan       │
│      - Channel strategy summary     │
│      - Reach projections            │
│      - Budget allocation            │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  11. Create Budget Section          │
│      - Detailed budget              │
│      - Justifications               │
│      - Total alignment              │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  12. Draft Org Qualifications       │
│      - Accreditation status         │
│      - Experience summary           │
│      - Infrastructure               │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  13. Draft Independence Section     │
│      - ACCME compliance             │
│      - Independence statement       │
│      - Disclosure policy            │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  14. Assemble complete document     │
│      - Order all sections           │
│      - Add page numbers/headers     │
│      - Create table of contents     │
│      - Final consistency check      │
└─────────────────────────────────────┘
  │
  ▼
OUTPUT: grant_package_output
```

---

## Quality Criteria

### Completeness
- [ ] All 11 required sections present
- [ ] No placeholder content
- [ ] All referenced data included
- [ ] Appendices complete if promised

### Consistency
- [ ] Terminology uniform throughout
- [ ] Numbers match across sections
- [ ] Character thread maintained
- [ ] Voice consistent

### Professionalism
- [ ] Zero AI writing patterns
- [ ] 80%+ prose density
- [ ] Proper formatting
- [ ] Appropriate length per section

### Compliance
- [ ] Independence clearly stated
- [ ] No promotional content
- [ ] ACCME standards addressed
- [ ] Disclosures complete

### Integration
- [ ] Cross-references appropriate
- [ ] Sections support each other
- [ ] No contradictions
- [ ] Narrative flows logically

---

## Example Output Excerpt

```yaml
cover_letter:
  recipient: "Dr. James Morrison, Medical Education Grants, Acme Pharmaceuticals"
  date: "February 15, 2025"
  content: |
    Dear Dr. Morrison,
    
    Digital Harmony Group is pleased to submit this proposal for educational 
    funding to support "Optimizing Heart Failure Management: From Guidelines 
    to Practice," a certified continuing medical education activity designed 
    to address critical gaps in guideline-directed medical therapy utilization.
    
    Despite Class I guideline recommendations, fewer than one-quarter of 
    eligible heart failure patients receive optimal evidence-based therapy. 
    This practice-guideline gap results in an estimated 50,000 preventable 
    hospitalizations annually and represents a significant opportunity for 
    educational intervention.
    
    Our proposed activity combines evidence-based didactic content with 
    innovative case-based workshops, targeting 500 cardiologists and primary 
    care physicians over 12 months. The curriculum incorporates barrier-aware 
    case design and patient voice integration, instructional innovations 
    demonstrated to improve knowledge translation to practice.
    
    We anticipate that 70% of participants will demonstrate improved 
    competence in case-based assessment, and 50% will report meaningful 
    practice changes at 60-day follow-up.
    
    We respectfully request support of $175,000 to develop and implement 
    this activity. This investment translates to a cost of $350 per physician 
    reached with high-quality, outcomes-focused education addressing a 
    significant unmet need.
    
    Thank you for considering this proposal. I welcome the opportunity to 
    discuss how this activity aligns with Acme's commitment to improving 
    cardiovascular care.
    
    Sincerely,
    
    [Name]
    Director of Medical Education
    Digital Harmony Group
  signatory: "Director of Medical Education"

executive_summary:
  content: |
    Heart failure affects 6.7 million Americans and claims one life every 
    33 seconds. Despite three decades of therapeutic advances, the five-year 
    mortality rate remains 50%, driven largely by persistent gaps between 
    evidence-based guidelines and clinical practice.
    
    Data from the PINNACLE Registry reveal that only 23% of eligible patients 
    receive SGLT2 inhibitor therapy, despite Class I guideline recommendations. 
    Fewer than 15% achieve target doses of foundational therapies. These gaps 
    translate to preventable hospitalizations, premature mortality, and 
    diminished quality of life for millions of patients.
    
    The barriers are well-characterized: 62% of primary care physicians report 
    uncertainty about heart failure medication initiation, while 78% express 
    concerns about managing therapy in complex patients. System factors 
    including time constraints and prior authorization challenges compound 
    clinician knowledge and skill gaps.
    
    "Optimizing Heart Failure Management: From Guidelines to Practice" is a 
    certified CME activity designed to address these gaps through a hybrid 
    symposium format combining evidence synthesis with barrier-aware case 
    workshops. The curriculum targets 500 cardiologists and primary care 
    physicians through ACC partnership, targeted email, and specialty journal 
    channels.
    
    [Executive summary continues...]
```

---

## Error Handling

| Error | Response |
|-------|----------|
| Missing agent output | Flag section incomplete, request regeneration |
| Inconsistent numbers | Reconcile using most recent/reliable source |
| Character thread missing | Add references in appropriate sections |
| Word count insufficient | Expand sections with evidence, not filler |
| Budget doesn't match | Reconcile with intake form |
| Promotional content detected | Remove or rephrase neutrally |

---

## Dependencies

### Upstream
- All preceding agent outputs (required)
- Intake form (required)

### Downstream
- Prose Quality Agent (second pass)
- Compliance Review Agent

---

## Testing Scenarios

### Test Case 1: Complete Inputs
- Expected: Full grant package generated
- Verify: All sections present, consistent, professional

### Test Case 2: Missing Agent Output
- Expected: Graceful handling with flagged gaps
- Verify: Process continues, gaps clearly marked

### Test Case 3: Inconsistent Data Across Inputs
- Expected: Reconciliation with documentation
- Verify: Final document internally consistent

---

*The Grant Writer assembles the complete case for support. Quality here determines grant success.*
