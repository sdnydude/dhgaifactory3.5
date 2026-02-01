# Agent 6: Learning Objectives Agent
## Moore's Framework Objectives

**Agent Type:** LLM-powered  
**Complexity:** Medium  
**Primary Output:** 6+ measurable learning objectives aligned to gaps

---

## Role Definition

The Learning Objectives Agent creates measurable learning objectives using Moore's Expanded Outcomes Framework as the primary taxonomy. Each objective must trace to an identified gap, specify a target Moore level, use appropriate action verbs, and include measurement methodology.

---

## Inputs

### From Other Agents
| Agent | Data Used |
|-------|-----------|
| Needs Assessment Agent (5) | Revised needs assessment (post-prose quality) |
| Gap Analysis Agent (4) | Prioritized gaps with barrier categorization |

### From Intake Form
| Field | Section | Purpose |
|-------|---------|---------|
| target_audience | B | Audience-appropriate objectives |
| educational_format | E | Format-appropriate objectives |
| outcome_goals | D | Alignment verification |
| moore_level_target | D | Target outcome level |

### Required Shared Resources
- **moores-expanded-framework.md**: Complete framework with verb lists

---

## Outputs

### Learning Objectives Structure

```yaml
learning_objectives_output:
  metadata:
    agent_version: "2.0"
    execution_timestamp: datetime
    objectives_count: int  # Minimum 6
    primary_moore_level: str
  
  framework_application:
    target_level: str  # "Level 4", "Level 5", "Level 6"
    level_distribution:
      level_3a: int
      level_3b: int
      level_4: int
      level_5: int
      level_6: int
    distribution_rationale: str
  
  objectives:
    - objective_id: str  # "OBJ-001"
      objective_text: str  # Full objective statement
      
      moore_classification:
        level: str  # "Level 5"
        level_name: str  # "Performance"
        action_verb: str  # "Initiate"
        verb_rationale: str
      
      gap_alignment:
        gap_id: str  # "GAP-001"
        gap_title: str
        alignment_explanation: str
      
      measurement:
        primary_method: str
        timing: str
        success_criteria: str
        data_source: str
      
      patient_outcome_link:
        linked_outcome: str
        mechanism: str
      
      blooms_secondary:  # Optional, only if adds clarity
        level: str
        rationale: str
  
  gap_coverage_matrix:
    # Shows which objectives address which gaps
    - gap_id: str
      objectives_addressing: List[str]
      coverage_completeness: str
  
  measurement_plan_summary:
    immediate_assessment: List[str]
    thirty_day_followup: List[str]
    sixty_to_ninety_day_followup: List[str]
    outcome_tracking: List[str]  # If Level 6
```

---

## System Prompt

```
You are a learning objectives specialist creating objectives for continuing medical education using Moore's Expanded Outcomes Framework. Your objectives must:

1. ALIGN TO GAPS: Every objective must address an identified educational gap
2. USE MOORE'S: Moore's Framework is PRIMARY; Bloom's is secondary only
3. BE MEASURABLE: Every objective must have clear measurement methodology
4. LINK TO OUTCOMES: Every objective must connect to patient outcomes
5. USE CORRECT VERBS: Action verbs must match the Moore level exactly

MOORE'S FRAMEWORK REQUIREMENTS:
- Level 5 (Performance) objectives should dominate when targeting practice change
- Level 4 (Competence) objectives support Level 5 when skill building is needed
- Level 3 objectives should be <20% of total unless foundational knowledge is primary gap
- Never use Level 1 or Level 2 as targets (participation/satisfaction are automatic)

OBJECTIVE CONSTRUCTION FORMAT:
"Upon completion of this activity, participants will be able to [ACTION VERB at Moore Level] [SPECIFIC CLINICAL BEHAVIOR] for [PATIENT POPULATION] to [INTENDED OUTCOME]."

ACTION VERB REQUIREMENTS BY LEVEL:
- Level 5: prescribe, order, initiate, discontinue, adjust, monitor, refer, screen, counsel, document, implement, integrate, incorporate
- Level 4: select, determine, differentiate, assess, evaluate, calculate, interpret, formulate, develop, design
- Level 3B: perform, execute, demonstrate, apply, use, administer, conduct
- Level 3A: identify, recognize, describe, explain (USE SPARINGLY)

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
- Every objective has measurement at ≥2 timepoints
- Every objective explicitly links to patient outcome
```

---

## Moore Level Distribution Guidelines

### When Target = Level 5 (Performance)

```
┌────────────────────────────────────────┐
│         OBJECTIVE DISTRIBUTION          │
│         Target: Level 5 (40-60%)        │
├────────────────────────────────────────┤
│                                        │
│  Level 5 ████████████████████ 40-60%   │
│          (Primary focus)               │
│                                        │
│  Level 4 ████████████ 30-40%           │
│          (Enabling competence)         │
│                                        │
│  Level 3 ████ 10-20%                   │
│          (Foundation only)             │
│                                        │
└────────────────────────────────────────┘
```

### When Target = Level 4 (Competence)

```
┌────────────────────────────────────────┐
│         OBJECTIVE DISTRIBUTION          │
│         Target: Level 4 (60-80%)        │
├────────────────────────────────────────┤
│                                        │
│  Level 4 ████████████████████████ 60-80│
│          (Primary focus)               │
│                                        │
│  Level 3B ████████ 10-20%              │
│           (Supporting skills)          │
│                                        │
│  Level 3A ████ 10-20%                  │
│           (Foundation knowledge)       │
│                                        │
└────────────────────────────────────────┘
```

---

## Execution Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  1. Analyze inputs                  │
│     - Review gap analysis           │
│     - Note barrier types per gap    │
│     - Identify target Moore level   │
│     - Review intake outcome goals   │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  2. Plan objective distribution     │
│     - Determine primary level       │
│     - Calculate level percentages   │
│     - Map gaps to level targets     │
│     - Plan coverage strategy        │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  3. Draft Level 5 objectives        │
│     - Use performance verbs         │
│     - Specify clinical behaviors    │
│     - Define patient population     │
│     - State intended outcome        │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  4. Draft Level 4 objectives        │
│     - Use competence verbs          │
│     - Focus on decision-making      │
│     - Include case application      │
│     - Connect to performance goals  │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  5. Draft Level 3 objectives        │
│     - Only if foundational gap      │
│     - Use sparingly (<20%)          │
│     - Bridge to higher levels       │
│     - Avoid standalone knowledge    │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  6. Verify gap coverage             │
│     - Every gap has ≥1 objective    │
│     - Priority gaps have multiple   │
│     - No orphan objectives          │
│     - Coverage matrix complete      │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  7. Define measurement plan         │
│     - Immediate assessment          │
│     - 30-day follow-up              │
│     - 60-90 day follow-up           │
│     - Outcome tracking if Level 6   │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  8. Quality check                   │
│     - Verify verb-level alignment   │
│     - Check measurability           │
│     - Confirm outcome links         │
│     - Validate distribution         │
└─────────────────────────────────────┘
  │
  ▼
OUTPUT: learning_objectives_output
```

---

## Objective Construction Examples

### Level 5 (Performance) Example

```yaml
objective_id: "OBJ-001"
objective_text: "Upon completion of this activity, participants will be able to INITIATE guideline-concordant SGLT2 inhibitor therapy within 30 days of HFrEF diagnosis for patients with eGFR ≥20 mL/min/1.73m² to reduce hospitalization risk."

moore_classification:
  level: "Level 5"
  level_name: "Performance"
  action_verb: "Initiate"
  verb_rationale: "Initiate is a Level 5 verb indicating action in clinical practice"

gap_alignment:
  gap_id: "GAP-001"
  gap_title: "Suboptimal SGLT2 Inhibitor Initiation in Heart Failure"
  alignment_explanation: "Directly addresses 77% practice-guideline gap in SGLT2i initiation"

measurement:
  primary_method: "Commitment-to-change with 60-day follow-up"
  timing: "Immediately post-activity + 60 days"
  success_criteria: "≥70% report initiating SGLT2i in eligible patients"
  data_source: "Self-reported practice change survey"

patient_outcome_link:
  linked_outcome: "Reduced heart failure hospitalization"
  mechanism: "SGLT2i therapy demonstrated 31% hospitalization reduction (EMPEROR-Reduced)"
```

### Level 4 (Competence) Example

```yaml
objective_id: "OBJ-002"
objective_text: "Upon completion of this activity, participants will be able to DIFFERENTIATE between HFrEF and HFpEF using echocardiographic and clinical criteria to SELECT appropriate evidence-based therapy for each phenotype."

moore_classification:
  level: "Level 4"
  level_name: "Competence"
  action_verb: "Differentiate"
  verb_rationale: "Differentiate is a Level 4 verb indicating clinical reasoning ability"

gap_alignment:
  gap_id: "GAP-003"
  gap_title: "HFpEF Recognition and Management Gap"
  alignment_explanation: "Addresses diagnostic confusion that leads to inappropriate therapy selection"

measurement:
  primary_method: "Case-based assessment"
  timing: "Pre/post assessment + 30-day retention"
  success_criteria: "≥80% correct phenotype classification and therapy selection"
  data_source: "Embedded case vignettes with clinical decision points"

patient_outcome_link:
  linked_outcome: "Appropriate therapy selection improving outcomes"
  mechanism: "Phenotype-specific therapy improves functional status and reduces events"
```

### Level 3B (Procedural) Example — Use Sparingly

```yaml
objective_id: "OBJ-006"
objective_text: "Upon completion of this activity, participants will be able to PERFORM a comprehensive volume assessment using jugular venous pressure examination and point-of-care ultrasound to GUIDE diuretic dosing."

moore_classification:
  level: "Level 3B"
  level_name: "Procedural Knowledge"
  action_verb: "Perform"
  verb_rationale: "Perform indicates procedural skill application"

gap_alignment:
  gap_id: "GAP-005"
  gap_title: "Inadequate Volume Assessment Skills"
  alignment_explanation: "Foundational skill required for safe diuretic management"

measurement:
  primary_method: "Skills demonstration or confidence assessment"
  timing: "Post-activity assessment"
  success_criteria: "≥70% demonstrate correct technique or report high confidence"
  data_source: "Objective skills assessment or self-efficacy scale"

patient_outcome_link:
  linked_outcome: "Optimized volume status reducing readmission"
  mechanism: "Accurate volume assessment enables appropriate diuretic titration"
```

---

## Quality Criteria

### Objective Quality Checklist
- [ ] 6-10 objectives total
- [ ] 60%+ at Level 4 or higher
- [ ] Every identified gap addressed by ≥1 objective
- [ ] Every objective has measurement at ≥2 timepoints
- [ ] Every objective explicitly links to patient outcome
- [ ] No passive verbs (understand, appreciate, be aware)
- [ ] No unmeasurable outcomes
- [ ] Action verbs match stated Moore level
- [ ] Point-of-care action is explicit in Level 5 objectives

### Gap Coverage Matrix
- [ ] All priority gaps (top 3) have multiple objectives
- [ ] Secondary gaps have at least 1 objective
- [ ] No objectives exist without gap alignment
- [ ] Coverage is documented in matrix format

### Measurement Plan
- [ ] Immediate assessment method defined for all
- [ ] 30-day follow-up defined for retention
- [ ] 60-90 day follow-up defined for practice change
- [ ] Data collection method specified
- [ ] Success criteria quantified

---

## Error Handling

| Error | Response |
|-------|----------|
| Gap not covered by objective | Create additional objective for uncovered gap |
| Verb doesn't match Moore level | Substitute correct level verb |
| Objective not measurable | Add specific measurement criteria |
| Too many Level 3 objectives | Elevate to Level 4 or combine |
| Outcome link missing | Add explicit patient outcome connection |
| Duplicate objectives | Combine or differentiate scope |

---

## Dependencies

### Upstream
- Needs Assessment Agent output (post-prose quality pass)
- Gap Analysis Agent output

### Downstream
- Curriculum Design Agent
- Research Protocol Agent
- Marketing Plan Agent

---

## Testing Scenarios

### Test Case 1: Performance-Focused Activity
- Expected: 50%+ Level 5 objectives
- Verify: Commitment-to-change measurement included

### Test Case 2: Competence-Building Activity
- Expected: 70%+ Level 4 objectives
- Verify: Case-based assessment methodology

### Test Case 3: Complex Multi-Gap Activity
- Expected: 8-10 objectives covering all gaps
- Verify: Complete gap coverage matrix

---

*Learning objectives drive the entire educational design. Every subsequent agent depends on their quality.*
