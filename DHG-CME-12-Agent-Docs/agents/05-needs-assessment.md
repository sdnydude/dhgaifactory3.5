# Agent 5: Needs Assessment Agent
## Cold Open + 3,100+ Word Narrative Document

**Agent Type:** LLM-powered (high complexity)  
**Complexity:** High  
**Primary Output:** Complete needs assessment with cold open and narrative

---

## Role Definition

The Needs Assessment Agent produces the flagship document of the grant package: a 3,100+ word narrative that opens with a compelling cold open, weaves a character thread throughout, and presents the educational gaps in persuasive, evidence-dense prose. This is the document pharmaceutical grant reviewers read most carefully.

---

## Inputs

### From Other Agents
| Agent | Data Used |
|-------|-----------|
| Gap Analysis Agent (4) | Prioritized gaps with evidence, barriers, patient impact |
| Research Agent (2) | Epidemiology, literature, market context |
| Clinical Practice Agent (3) | Practice patterns, barrier details |

### From Intake Form
| Field | Section | Purpose |
|-------|---------|---------|
| therapeutic_area | A | Context framing |
| disease_state | A | Clinical focus |
| target_audience | B | Audience characterization |
| geographic_focus | B | Regional context |
| activity_title | E | Document titling |
| accreditation_types | E | Compliance framing |

### Required Shared Resources
- **cold-open-framework.md**: Narrative hook specifications
- **writing-style-guide.md**: Prose requirements, banned patterns
- **moores-expanded-framework.md**: Outcomes framework context

---

## Outputs

### Needs Assessment Document Structure

```yaml
needs_assessment_output:
  metadata:
    agent_version: "2.0"
    execution_timestamp: datetime
    word_count: int  # Must be ≥3,100
    prose_density: float  # Target ≥0.80
  
  cold_open:
    character_name: str
    character_age: int
    character_type: str  # "patient" or "clinician"
    humanizing_detail: str
    narrative_text: str  # 50-100 words
    turn_statement: str
  
  document_sections:
    - section_id: str
      section_title: str
      content: str
      word_count: int
      character_appearances: int  # Track narrative thread
      citations_used: List[str]
  
  character_thread:
    total_appearances: int  # Must be ≥4
    appearance_locations: List[str]
  
  complete_document: str  # Full assembled document
  
  quality_metrics:
    total_word_count: int
    prose_density: float
    citation_count: int
    character_thread_count: int
    banned_patterns_found: List[str]  # Should be empty
```

---

## Document Structure (Required Sections)

### Section Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      NEEDS ASSESSMENT DOCUMENT FLOW                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. COLD OPEN (50-100 words)                                                │
│     └─ No header                                                            │
│     └─ Narrative hook with named character                                  │
│     └─ The turn to systemic scope                                           │
│                                                                             │
│  2. DISEASE STATE OVERVIEW (400-500 words)                                  │
│     └─ Epidemiology and burden                                              │
│     └─ First character reference                                            │
│     └─ Economic impact                                                      │
│     └─ Trajectory/projections                                               │
│                                                                             │
│  3. CURRENT TREATMENT LANDSCAPE (400-500 words)                             │
│     └─ Guideline-recommended approach                                       │
│     └─ Available therapies                                                  │
│     └─ Recent advances                                                      │
│     └─ Evidence base summary                                                │
│                                                                             │
│  4. PRACTICE GAPS (600-800 words)                                           │
│     └─ Gap 1: Full narrative with evidence                                  │
│     └─ Gap 2: Full narrative with evidence                                  │
│     └─ Gap 3: Full narrative with evidence                                  │
│     └─ Character reference in gap context                                   │
│     └─ Additional gaps as warranted                                         │
│                                                                             │
│  5. BARRIERS TO OPTIMAL CARE (400-500 words)                                │
│     └─ Clinician barriers (knowledge, skill, attitude)                      │
│     └─ System barriers                                                      │
│     └─ Patient barriers                                                     │
│     └─ How barriers perpetuate gaps                                         │
│                                                                             │
│  6. EDUCATIONAL RATIONALE (400-500 words)                                   │
│     └─ Why education can address these gaps                                 │
│     └─ What education must accomplish                                       │
│     └─ Expected outcomes from education                                     │
│     └─ Character reference in outcome context                               │
│                                                                             │
│  7. TARGET AUDIENCE (300-400 words)                                         │
│     └─ Who needs this education                                             │
│     └─ Why this audience                                                    │
│     └─ Specialty-specific considerations                                    │
│     └─ Practice setting context                                             │
│                                                                             │
│  8. CONCLUSION (200-300 words)                                              │
│     └─ Synthesis of need                                                    │
│     └─ Call to action                                                       │
│     └─ Final character reference                                            │
│                                                                             │
│  TOTAL: 3,100+ words                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## System Prompt

```
You are a senior medical writer creating a needs assessment document for a continuing medical education grant application. Your writing must:

1. OPEN WITH IMPACT: Begin with a 50-100 word cold open that humanizes the clinical problem
2. MAINTAIN NARRATIVE: The character introduced must reappear 4+ times throughout
3. EVIDENCE-DENSE: Every claim backed by specific, cited data
4. PERSUASIVE: Build urgency without being alarmist
5. PROFESSIONAL: Read as if written by an experienced CME medical writer, not AI

COLD OPEN REQUIREMENTS:
- 50-100 words exactly
- Named composite character with age
- One humanizing detail
- Present tense for immediacy
- The turn: connect individual to population
- NO statistics in the cold open itself
- NO header before cold open

PROSE REQUIREMENTS:
- 80%+ flowing narrative prose
- Minimum 4-sentence paragraphs
- Data woven into sentences, not bulleted
- Tables/figures supplementary only
- No single-sentence paragraphs

CHARACTER THREAD REQUIREMENTS:
- Character must appear in 4+ sections
- Appearances must be natural, not forced
- Use character to illustrate gaps and outcomes
- Final reference should look toward better future

WORD COUNT REQUIREMENTS:
- Minimum 3,100 words total
- Each section must meet minimum word count
- Do not pad with filler; maintain density

BANNED PATTERNS (will cause rejection):
- Em dashes (—)
- "Delve into" or "delve deeper"
- "It's important to note that"
- "Furthermore," "Moreover," "Additionally" as paragraph starters
- "In today's healthcare landscape"
- Colons in section titles
- "Robust" as generic intensifier
- "Leverage" as verb
- "Holistic" 
- "Paradigm" or "paradigm shift"
- "Cutting-edge" or "state-of-the-art"
- Generic phrases without specific data

CITATION STYLE:
- Embed in prose: "The PARADIGM-HF trial demonstrated a 20% mortality reduction (McMurray et al., NEJM 2014)"
- Include author/source and year
- Never say "studies show" without naming the study

OUTPUT:
Produce a complete needs assessment document ready for grant submission. The document should flow as a single, cohesive narrative that builds urgency and justifies the educational intervention.
```

---

## Cold Open Construction

### Process

1. **Select character type** based on gap analysis
   - Patient-centered: When gaps affect patient experience/outcomes
   - Clinician-centered: When gaps are about provider decision-making

2. **Create character details**
   - Name appropriate to demographics
   - Age relevant to condition
   - One humanizing detail that makes them real

3. **Construct the moment**
   - Drop into specific scene
   - Present tense
   - High stakes implied

4. **Write the turn**
   - Connect individual to population
   - Use specific number ("She is one of 6.7 million...")

### Cold Open Template

```
[THE MOMENT - 10-20 words]
[THE PERSON - 15-30 words with name, age, humanizing detail]
[THE STAKES - 20-40 words showing what's at risk]
[THE TURN - 10-20 words connecting to population]
```

### Example Cold Open

> Maria Chen, 58, sits in her cardiologist's waiting room for the third time this year. Each visit follows the same pattern: shortness of breath, a medication adjustment, a promise to do better with salt. What neither she nor her physician realizes is that her ejection fraction has dropped below 30% and she now qualifies for a device that could cut her mortality risk in half. Across the country, 380,000 patients like Maria are waiting for a conversation that never happens.

---

## Character Thread Management

### Required Appearances (minimum 4)

| Section | How to Reference |
|---------|------------------|
| Disease State Overview | "Maria Chen is one of 6.7 million Americans living with..." |
| Practice Gaps | "In Maria's case, the gap manifested as three missed opportunities..." |
| Educational Rationale | "Had Maria's cardiologist participated in education addressing these gaps..." |
| Conclusion | "For Maria Chen and the millions like her, the window for optimal intervention..." |

### Natural Integration Techniques

**Avoid:** "Let's return to Maria Chen..."
**Use:** "Maria's experience illustrates..." or "Patients like Maria..."

**Avoid:** Forced, awkward insertions
**Use:** Character as natural example of data being discussed

---

## Execution Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  1. Ingest all upstream data        │
│     - Load gap_analysis_output      │
│     - Load research_output          │
│     - Load clinical_output          │
│     - Load intake form data         │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  2. Create cold open character      │
│     - Select character type         │
│     - Generate character details    │
│     - Plan narrative arc            │
│     - Draft cold open (50-100 words)│
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  3. Draft Disease State Overview    │
│     - Integrate epidemiology        │
│     - Include first character ref   │
│     - Weave in economic burden      │
│     - Target 400-500 words          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  4. Draft Treatment Landscape       │
│     - Summarize current standards   │
│     - Note recent advances          │
│     - Present evidence base         │
│     - Target 400-500 words          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  5. Draft Practice Gaps section     │
│     - Present each gap narratively  │
│     - Include quantified evidence   │
│     - Connect to patient outcomes   │
│     - Include character reference   │
│     - Target 600-800 words          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  6. Draft Barriers section          │
│     - Categorize barrier types      │
│     - Explain root causes           │
│     - Connect barriers to gaps      │
│     - Target 400-500 words          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  7. Draft Educational Rationale     │
│     - Make case for education       │
│     - State expected outcomes       │
│     - Include character reference   │
│     - Target 400-500 words          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  8. Draft Target Audience section   │
│     - Define who needs education    │
│     - Justify audience selection    │
│     - Address specialty needs       │
│     - Target 300-400 words          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  9. Draft Conclusion                │
│     - Synthesize the need           │
│     - Final character reference     │
│     - Call to educational action    │
│     - Target 200-300 words          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  10. Quality check and polish       │
│      - Verify word count ≥3,100     │
│      - Check prose density ≥80%     │
│      - Verify character thread ≥4   │
│      - Scan for banned patterns     │
│      - Verify all citations present │
└─────────────────────────────────────┘
  │
  ▼
OUTPUT: needs_assessment_output
```

---

## Quality Criteria

### Word Count Minimums (Strictly Enforced)

| Section | Minimum Words |
|---------|---------------|
| Cold Open | 50-100 (exact) |
| Disease State Overview | 400 |
| Treatment Landscape | 400 |
| Practice Gaps | 600 |
| Barriers | 400 |
| Educational Rationale | 400 |
| Target Audience | 300 |
| Conclusion | 200 |
| **TOTAL** | **3,100** |

### Prose Density
- Target: ≥80% flowing prose
- Tables: Maximum 1 per section
- Bullets: Only for truly list-appropriate content
- Single-sentence paragraphs: Zero

### Character Thread
- Minimum 4 appearances
- Appearances must be natural
- Final appearance looks forward

### Citation Density
- Every statistic cited
- Every guideline referenced
- Every claim supported
- Named studies, not "research shows"

### Banned Pattern Check
Zero tolerance for:
- Em dashes (—)
- "Delve into"
- "It's important to note"
- "Furthermore," as paragraph starter
- "In today's healthcare landscape"
- Colons in titles
- All patterns listed in writing-style-guide.md

---

## Example Document Excerpt

```markdown
Maria Chen, 58, sits in her cardiologist's waiting room for the third time 
this year. Each visit follows the same pattern: shortness of breath, a 
medication adjustment, a promise to do better with salt. What neither she 
nor her physician realizes is that her ejection fraction has dropped below 
30% and she now qualifies for a device that could cut her mortality risk in 
half. Across the country, 380,000 patients like Maria are waiting for a 
conversation that never happens.

Maria Chen is one of 6.7 million Americans living with heart failure, a 
number the American Heart Association projects will exceed 8 million by 2030. 
The condition claims one American life every 33 seconds and generates more 
Medicare expenditure than any other single diagnosis. Despite three decades 
of therapeutic advances, including neurohormonal modulators that have 
transformed survival expectations, the five-year mortality rate remains a 
sobering 50%, comparable to many metastatic cancers. For patients like Maria, 
who present with gradually worsening symptoms, the trajectory often includes 
multiple hospitalizations, progressive functional decline, and a quality of 
life that deteriorates in ways that standard clinic metrics fail to capture.

The economic burden of heart failure extends far beyond direct medical costs. 
The American Heart Association estimates total annual costs at $43.6 billion, 
a figure projected to reach $69.7 billion by 2030. Hospital readmissions 
account for a disproportionate share: heart failure remains the leading cause 
of 30-day readmission among Medicare beneficiaries, with rates hovering near 
23% despite a decade of quality improvement initiatives. Indirect costs, 
including lost productivity and caregiver burden, add an estimated $12 billion 
annually. These numbers represent not abstract economics but real families 
facing impossible choices between medications and groceries, between clinic 
appointments and lost wages.

[Document continues with Treatment Landscape, Practice Gaps, Barriers, 
Educational Rationale, Target Audience, and Conclusion sections, each 
maintaining the same prose density, citation style, and narrative thread...]
```

---

## Error Handling

| Error | Response |
|-------|----------|
| Word count below minimum | Expand sections with additional evidence, not filler |
| Prose density below 80% | Convert lists to narrative prose |
| Character thread < 4 | Add natural character references to sections |
| Banned patterns detected | Rewrite affected passages |
| Missing citations | Add specific source references |
| Sections feel disconnected | Add transitional sentences between sections |

---

## Dependencies

### Upstream
- Gap Analysis Agent output (required)
- Research Agent output (required)
- Clinical Practice Agent output (required)
- Intake form data (required)

### Downstream
- Prose Quality Agent (immediate quality check)
- Learning Objectives Agent (after prose quality pass)
- Grant Writer Agent (final assembly)

---

## Testing Scenarios

### Test Case 1: Cardiology (Data-Rich)
- Expected: Abundant data, clear gaps, strong narrative
- Verify: Word count, character thread, citation density

### Test Case 2: Rare Disease (Data-Limited)
- Expected: Handles sparse data gracefully
- Verify: Maintains quality despite limited statistics

### Test Case 3: Complex Multi-Specialty Topic
- Expected: Balances multiple audience perspectives
- Verify: Target audience section addresses complexity

---

*The Needs Assessment is the heart of the grant application. It must be flawless.*
