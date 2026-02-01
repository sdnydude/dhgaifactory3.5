# Agent 7: Curriculum Design Agent
## Educational Design + Innovation Section

**Agent Type:** LLM-powered  
**Complexity:** Medium  
**Primary Output:** Complete curriculum specification with innovation rationale

---

## Role Definition

The Curriculum Design Agent creates the educational design for the CME activity, including format selection, content structure, faculty specifications, instructional methods, and the innovation section that justifies the educational approach. The output must demonstrate pedagogical sophistication while remaining practical for implementation.

---

## Inputs

### From Other Agents
| Agent | Data Used |
|-------|-----------|
| Learning Objectives Agent (6) | Objectives with Moore levels and measurement |
| Gap Analysis Agent (4) | Gaps and barriers informing design choices |
| Needs Assessment Agent (5) | Context and audience characteristics |

### From Intake Form
| Field | Section | Purpose |
|-------|---------|---------|
| target_audience | B | Audience-appropriate design |
| practice_settings | B | Setting-appropriate methods |
| educational_format | E | Format constraints/preferences |
| innovation_elements | E | Required innovation features |
| faculty_requirements | F | Faculty specification input |
| duration | E | Time allocation |
| modality | E | Delivery method |

---

## Outputs

### Curriculum Design Structure

```yaml
curriculum_output:
  metadata:
    agent_version: "2.0"
    execution_timestamp: datetime
    total_duration_minutes: int
    format_type: str
  
  executive_summary:
    educational_approach: str  # 2-3 sentence summary
    key_innovations: List[str]
    expected_impact: str
  
  format_specification:
    primary_format: str  # e.g., "Live symposium with case workshops"
    modality: str  # "In-person", "Virtual", "Hybrid"
    duration: str
    session_structure: List[Dict]
    rationale: str
  
  content_outline:
    modules:
      - module_id: str
        title: str
        duration_minutes: int
        objectives_addressed: List[str]
        content_elements:
          - element_type: str  # "didactic", "case", "interactive", etc.
            description: str
            duration_minutes: int
            learning_method: str
        faculty_role: str
        assessment_embedded: str
  
  instructional_methods:
    - method_name: str
      description: str
      objectives_supported: List[str]
      rationale: str
      evidence_base: str
  
  case_design:
    case_count: int
    case_structure:
      - case_id: str
        scenario_type: str
        clinical_presentation: str
        decision_points: List[str]
        teaching_points: List[str]
        connection_to_cold_open: str  # If applicable
    case_progression_rationale: str
  
  faculty_specifications:
    lead_faculty:
      expertise_required: List[str]
      credentials: str
      role: str
    supporting_faculty:
      - role: str
        expertise_required: List[str]
        credentials: str
    faculty_development_needs: str
  
  innovation_section:
    innovation_summary: str  # 500+ word section
    innovations:
      - innovation_name: str
        description: str
        educational_rationale: str
        evidence_supporting: str
        implementation_approach: str
    differentiation_from_existing: str
    technology_integration: str
  
  assessment_strategy:
    formative:
      - method: str
        timing: str
        purpose: str
    summative:
      - method: str
        timing: str
        criteria: str
    practice_change_measurement:
      method: str
      timing: str
      follow_up_mechanism: str
  
  implementation_requirements:
    technology_needs: List[str]
    materials_required: List[str]
    venue_requirements: str
    staffing_needs: str
```

---

## System Prompt

```
You are an instructional designer creating curriculum for continuing medical education. Your design must:

1. OBJECTIVE-ALIGNED: Every content element must trace to a learning objective
2. ADULT LEARNING: Apply adult learning principles (relevance, experience, problem-centered)
3. EVIDENCE-BASED: Use instructional methods with demonstrated efficacy
4. INNOVATIVE: Include genuine innovations that differentiate from standard approaches
5. PRACTICAL: Design must be implementable within stated constraints

CURRICULUM DESIGN PRINCIPLES:
- Active learning should exceed passive lecture by ratio of at least 40:60
- Cases should be central, not supplementary
- Real-world relevance must be explicit
- Assessment should be embedded, not bolted on
- Time allocations must be realistic

INNOVATION REQUIREMENTS:
The innovation section (500+ words) must describe:
- What makes this educational approach novel
- Why these innovations will improve outcomes
- Evidence supporting the innovative methods
- How innovations address identified barriers
- Differentiation from existing CME on this topic

PROHIBITED PATTERNS:
- "Lecture followed by Q&A" as primary method
- Cases as afterthought rather than core
- Innovation claims without substance
- Assessment only at end of activity
- Ignoring identified barriers in design

OUTPUT FORMAT:
Produce a complete curriculum specification that could be handed to a production team for implementation. Be specific about timing, methods, and requirements.
```

---

## Instructional Method Selection

### Methods by Objective Level

| Moore Level | Recommended Methods | Rationale |
|-------------|---------------------|-----------|
| Level 5 (Performance) | Case-based decision-making, commitment-to-change, action planning, practice simulation | Requires real-world application focus |
| Level 4 (Competence) | Case analysis, clinical reasoning exercises, skills practice, OSCE-style scenarios | Requires demonstrated capability |
| Level 3B (Procedural) | Skills demonstration, guided practice, technique videos, hands-on workshops | Requires procedural repetition |
| Level 3A (Declarative) | Brief didactic, pre-work, reference materials | Foundation only, minimize time |

### Innovation Categories

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       INNOVATION CATEGORIES                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PEDAGOGICAL INNOVATIONS                                                    │
│  └─ Flipped classroom approaches                                            │
│  └─ Spaced learning with reinforcement                                      │
│  └─ Deliberate practice with feedback                                       │
│  └─ Reflective practice integration                                         │
│  └─ Team-based learning structures                                          │
│                                                                             │
│  CONTENT INNOVATIONS                                                        │
│  └─ Patient voice integration (video, audio)                                │
│  └─ De-identified real-world data                                           │
│  └─ Guideline evolution comparison                                          │
│  └─ Cross-specialty perspective inclusion                                   │
│                                                                             │
│  TECHNOLOGY INNOVATIONS                                                     │
│  └─ Audience response with aggregation                                      │
│  └─ Virtual patient simulations                                             │
│  └─ AI-powered practice scenarios                                           │
│  └─ Point-of-care decision support integration                              │
│                                                                             │
│  ASSESSMENT INNOVATIONS                                                     │
│  └─ Real-time competence verification                                       │
│  └─ Adaptive questioning                                                    │
│  └─ Practice commitment micro-contracts                                     │
│  └─ Peer comparison benchmarking                                            │
│                                                                             │
│  IMPLEMENTATION INNOVATIONS                                                 │
│  └─ Workflow integration tools                                              │
│  └─ EHR-compatible resources                                                │
│  └─ Post-activity nudge systems                                             │
│  └─ Community of practice formation                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Execution Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  1. Analyze learning objectives     │
│     - Map objectives by Moore level │
│     - Identify method requirements  │
│     - Note measurement needs        │
│     - Review gap/barrier context    │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  2. Design format structure         │
│     - Select primary format         │
│     - Determine session flow        │
│     - Allocate time by objective    │
│     - Balance active/passive        │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  3. Develop content outline         │
│     - Structure modules             │
│     - Map content to objectives     │
│     - Design transitions            │
│     - Embed assessment points       │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  4. Design case scenarios           │
│     - Create case structure         │
│     - Define decision points        │
│     - Connect to cold open char     │
│     - Plan case progression         │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  5. Select instructional methods    │
│     - Match methods to objectives   │
│     - Cite evidence base            │
│     - Justify selections            │
│     - Note implementation needs     │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  6. Specify faculty requirements    │
│     - Define expertise needs        │
│     - Describe roles                │
│     - Note development needs        │
│     - Plan faculty coordination     │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  7. Write innovation section        │
│     - Describe innovations (500+ w) │
│     - Cite supporting evidence      │
│     - Explain rationale             │
│     - Differentiate from existing   │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  8. Design assessment strategy      │
│     - Formative assessment plan     │
│     - Summative assessment plan     │
│     - Practice change measurement   │
│     - Follow-up mechanism           │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  9. Document implementation needs   │
│     - Technology requirements       │
│     - Materials list                │
│     - Venue specifications          │
│     - Staffing requirements         │
└─────────────────────────────────────┘
  │
  ▼
OUTPUT: curriculum_output
```

---

## Quality Criteria

### Objective Alignment
- [ ] Every module addresses at least 1 objective
- [ ] Every objective addressed by at least 1 module
- [ ] Time allocation proportional to objective priority
- [ ] Assessment aligned with objective Moore level

### Adult Learning Principles
- [ ] Active learning ≥40% of time
- [ ] Cases are central to design
- [ ] Real-world relevance explicit
- [ ] Experience of learners leveraged
- [ ] Problem-centered rather than content-centered

### Innovation Quality
- [ ] Innovation section ≥500 words
- [ ] Innovations are substantive, not superficial
- [ ] Evidence cited for innovative methods
- [ ] Clear differentiation from standard approaches
- [ ] Innovations address identified barriers

### Practicality
- [ ] Time allocations are realistic
- [ ] Faculty requirements are achievable
- [ ] Technology needs are reasonable
- [ ] Materials requirements are specific
- [ ] Implementation is feasible

---

## Example Output Excerpt

```yaml
format_specification:
  primary_format: "Live symposium with integrated case workshops"
  modality: "Hybrid (in-person with virtual participation option)"
  duration: "3 hours (180 minutes)"
  session_structure:
    - segment: "Opening and Baseline Assessment"
      duration: 10
      type: "interactive"
    - segment: "Evidence Foundation"
      duration: 25
      type: "didactic with polling"
    - segment: "Case Workshop 1: Recognition"
      duration: 35
      type: "small group case analysis"
    - segment: "Break"
      duration: 10
      type: "break"
    - segment: "Treatment Algorithm Deep Dive"
      duration: 30
      type: "interactive didactic"
    - segment: "Case Workshop 2: Management Decisions"
      duration: 40
      type: "small group case analysis"
    - segment: "Implementation Strategies"
      duration: 20
      type: "action planning"
    - segment: "Commitment to Change + Close"
      duration: 10
      type: "assessment"
  rationale: "Format balances knowledge foundation with application practice, achieving 42% active learning time. Case workshops address Level 4-5 objectives while didactic segments efficiently deliver foundational content."

innovation_section:
  innovation_summary: |
    This educational activity incorporates five distinct innovations designed 
    to overcome the barriers identified in the needs assessment and maximize 
    the likelihood of practice change.
    
    First, we employ a 'patient voice' integration strategy that extends 
    beyond traditional case presentations. Each case workshop includes 
    90-second video segments featuring de-identified patient narratives 
    recorded with consent. These narratives humanize the clinical scenarios 
    and reinforce the stakes of optimal care, mirroring the cold open approach 
    of the needs assessment. Research by Kumagai et al. (2008) demonstrates 
    that patient narrative exposure increases empathic engagement and 
    retention of clinical concepts.
    
    Second, we implement a 'barrier-aware' case design methodology. Rather 
    than presenting idealized clinical scenarios, cases explicitly incorporate 
    the system and workflow barriers identified in the gap analysis. 
    Participants must navigate time constraints, competing priorities, and 
    imperfect information, reflecting actual practice conditions. This 
    approach draws on situated learning theory (Lave & Wenger, 1991) and 
    addresses the common critique that CME case scenarios fail to translate 
    to real-world practice.
    
    [Innovation section continues for 500+ total words...]
  
  innovations:
    - innovation_name: "Patient Voice Integration"
      description: "90-second patient narrative videos in each case"
      educational_rationale: "Humanizes cases, increases engagement and retention"
      evidence_supporting: "Kumagai et al., Patient narratives in medical education"
      implementation_approach: "Pre-recorded segments with discussion prompts"
    
    - innovation_name: "Barrier-Aware Case Design"
      description: "Cases incorporate real workflow constraints"
      educational_rationale: "Increases transfer to actual practice"
      evidence_supporting: "Situated learning theory, transfer research"
      implementation_approach: "Case scenarios include time pressure, system constraints"
```

---

## Error Handling

| Error | Response |
|-------|----------|
| Objective not addressed | Add content element or redistribute time |
| Innovation section too brief | Expand with additional evidence and detail |
| Time allocation unrealistic | Adjust duration or reduce content |
| Faculty requirements unclear | Add specificity to expertise and credentials |
| Cases don't connect to gaps | Redesign cases to address identified gaps |

---

## Dependencies

### Upstream
- Learning Objectives Agent output (required)
- Gap Analysis Agent output (barriers context)
- Needs Assessment Agent output (character for cases)

### Downstream
- Grant Writer Agent (curriculum section of grant)

---

## Testing Scenarios

### Test Case 1: Traditional Symposium Format
- Expected: Clear innovation differentiation from standard lecture
- Verify: Active learning ≥40%, innovation section substantive

### Test Case 2: Virtual-Only Activity
- Expected: Technology-appropriate design
- Verify: Engagement methods adapted for virtual delivery

### Test Case 3: Skills-Focused Activity
- Expected: Hands-on components central
- Verify: Procedural objectives have practice opportunities

---

*Curriculum design translates objectives into actionable educational experiences.*
