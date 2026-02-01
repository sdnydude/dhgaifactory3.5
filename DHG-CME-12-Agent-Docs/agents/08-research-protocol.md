# Agent 8: Research Protocol Agent
## IRB-Ready Outcomes Research Protocol

**Agent Type:** LLM-powered  
**Complexity:** Medium  
**Primary Output:** Complete outcomes research protocol

---

## Role Definition

The Research Protocol Agent creates an outcomes research protocol that describes how the educational activity's effectiveness will be measured. This is not clinical research but educational outcomes research, focusing on knowledge, competence, performance, and (where applicable) patient outcomes. The protocol should be detailed enough to satisfy pharmaceutical grant reviewers' expectations for rigorous evaluation.

---

## Inputs

### From Other Agents
| Agent | Data Used |
|-------|-----------|
| Learning Objectives Agent (6) | Objectives with measurement specifications |
| Gap Analysis Agent (4) | Baseline gap data for comparison |
| Curriculum Design Agent (7) | Assessment strategy from curriculum |

### From Intake Form
| Field | Section | Purpose |
|-------|---------|---------|
| target_audience | B | Study population definition |
| estimated_reach | G | Sample size context |
| outcome_goals | D | Outcome prioritization |
| moore_level_target | D | Measurement level focus |
| measurement_preferences | G | Sponsor evaluation preferences |

---

## Outputs

### Research Protocol Structure

```yaml
protocol_output:
  metadata:
    agent_version: "2.0"
    execution_timestamp: datetime
    protocol_type: str  # "Educational Outcomes Research"
  
  protocol_summary:
    title: str
    study_type: str
    primary_endpoint: str
    secondary_endpoints: List[str]
    study_duration: str
    target_enrollment: int
  
  background_and_rationale:
    educational_gap_summary: str
    rationale_for_study: str
    expected_contribution: str
  
  study_objectives:
    primary_objective: str
    secondary_objectives: List[str]
    exploratory_objectives: List[str]
  
  study_design:
    design_type: str  # "Single-arm pre-post", "Controlled", etc.
    design_rationale: str
    study_population:
      inclusion_criteria: List[str]
      exclusion_criteria: List[str]
    sample_size:
      target_n: int
      power_calculation: str  # If applicable
      dropout_assumptions: str
    study_duration:
      enrollment_period: str
      follow_up_duration: str
      total_study_duration: str
  
  outcome_measures:
    primary_outcome:
      measure_name: str
      moore_level: str
      definition: str
      measurement_method: str
      timing: str
      success_threshold: str
    secondary_outcomes:
      - measure_name: str
        moore_level: str
        definition: str
        measurement_method: str
        timing: str
    exploratory_outcomes:
      - measure_name: str
        description: str
  
  assessment_instruments:
    - instrument_name: str
      purpose: str
      description: str
      validation_status: str
      administration_timing: str
      scoring_method: str
  
  data_collection_plan:
    timepoints:
      - timepoint_name: str
        timing: str
        assessments_administered: List[str]
        data_collected: List[str]
    data_management:
      collection_method: str
      storage: str
      quality_assurance: str
  
  statistical_analysis_plan:
    primary_analysis:
      method: str
      description: str
    secondary_analyses:
      - analysis: str
        method: str
    handling_missing_data: str
    subgroup_analyses: List[str]
  
  ethical_considerations:
    irb_requirements: str
    informed_consent: str
    data_privacy: str
    participant_rights: str
  
  limitations:
    design_limitations: List[str]
    measurement_limitations: List[str]
    generalizability_considerations: str
  
  timeline:
    phases:
      - phase_name: str
        duration: str
        activities: List[str]
  
  references:
    - citation: str
```

---

## System Prompt

```
You are an educational research methodologist designing an outcomes research protocol for a continuing medical education activity. Your protocol must:

1. RIGOROUS: Meet standards expected by pharmaceutical company grant reviewers
2. ALIGNED: Directly measure achievement of stated learning objectives
3. PRACTICAL: Be implementable within typical CME operational constraints
4. MOORE-ALIGNED: Use appropriate measurement methods for each Moore level
5. COMPREHENSIVE: Include all elements of a complete research protocol

STUDY DESIGN CONSIDERATIONS:
- Most CME outcomes studies are single-arm pre-post designs
- Controlled designs are rare but impressive when feasible
- Focus on what can actually be measured
- Be realistic about follow-up response rates

MEASUREMENT BY MOORE LEVEL:
- Level 3 (Learning): Pre/post knowledge assessment
- Level 4 (Competence): Case-based performance assessment
- Level 5 (Performance): Commitment-to-change with follow-up verification
- Level 6 (Patient Outcomes): PROs, chart audit, registry data (rare)

PROTOCOL QUALITY MARKERS:
- Clear primary endpoint
- Appropriate statistical methods
- Realistic timeline
- Acknowledged limitations
- Practical implementation approach

PROHIBITED:
- Overclaiming ability to measure patient outcomes
- Ignoring attrition/response rate challenges
- Vague outcome definitions
- Unrealistic sample size expectations
- Ignoring ethical considerations
```

---

## Study Design Options

### Option 1: Single-Arm Pre-Post (Most Common)

```
Baseline Assessment → Educational Intervention → Post Assessment → Follow-up
      (Pre-test)                                    (Immediate)     (30-90 days)
```

**Strengths:** Simple, practical, standard for CME
**Limitations:** No control group, cannot establish causation

### Option 2: Wait-List Control (When Feasible)

```
Group A: Assessment → Intervention → Assessment → Follow-up
Group B: Assessment → Wait Period → Assessment → Intervention → Assessment
```

**Strengths:** Control comparison, stronger evidence
**Limitations:** Logistically complex, ethical considerations

### Option 3: Multi-Activity Longitudinal (Series)

```
Activity 1 → Assessment → Activity 2 → Assessment → Activity 3 → Final Assessment
```

**Strengths:** Tracks learning trajectory, reinforcement effects
**Limitations:** Requires multi-activity commitment

---

## Execution Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  1. Analyze objectives/measurement  │
│     - Review learning objectives    │
│     - Note Moore levels targeted    │
│     - Extract assessment strategy   │
│     - Identify measurement needs    │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  2. Define study objectives         │
│     - Primary research question     │
│     - Secondary questions           │
│     - Exploratory questions         │
│     - Align to learning objectives  │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  3. Select study design             │
│     - Choose appropriate design     │
│     - Document rationale            │
│     - Address limitations           │
│     - Consider feasibility          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  4. Define study population         │
│     - Inclusion criteria            │
│     - Exclusion criteria            │
│     - Target enrollment             │
│     - Dropout assumptions           │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  5. Specify outcome measures        │
│     - Primary endpoint              │
│     - Secondary endpoints           │
│     - Measurement methods           │
│     - Success thresholds            │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  6. Design assessment instruments   │
│     - Knowledge assessments         │
│     - Case-based assessments        │
│     - Commitment-to-change forms    │
│     - Follow-up surveys             │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  7. Create data collection plan     │
│     - Define timepoints             │
│     - Specify collection methods    │
│     - Plan data management          │
│     - Quality assurance procedures  │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  8. Develop statistical plan        │
│     - Primary analysis method       │
│     - Secondary analyses            │
│     - Missing data handling         │
│     - Subgroup analyses             │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  9. Address ethical considerations  │
│     - IRB requirements              │
│     - Consent process               │
│     - Data privacy                  │
│     - Participant protections       │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  10. Document limitations/timeline  │
│      - Acknowledge design limits    │
│      - Measurement limitations      │
│      - Create implementation timeline│
│      - Finalize protocol            │
└─────────────────────────────────────┘
  │
  ▼
OUTPUT: protocol_output
```

---

## Measurement Methods by Moore Level

### Level 3 (Learning) Measurement

| Method | Description | Timing |
|--------|-------------|--------|
| Pre/Post Knowledge Test | MCQ assessing factual knowledge | Immediate |
| Retention Test | Same/similar items | 30 days |

**Statistical Approach:** Paired t-test or McNemar's test for improvement

### Level 4 (Competence) Measurement

| Method | Description | Timing |
|--------|-------------|--------|
| Case Vignettes | Clinical scenarios with decision points | Immediate |
| Performance Assessment | Scoring rubric for case analysis | Immediate |
| Retention Cases | Similar cases, different details | 30 days |

**Statistical Approach:** Paired t-test on performance scores

### Level 5 (Performance) Measurement

| Method | Description | Timing |
|--------|-------------|--------|
| Commitment-to-Change | Specific, measurable commitments | Immediate |
| Follow-up Survey | Self-reported practice change | 60-90 days |
| Barrier Assessment | Obstacles encountered | 60-90 days |

**Statistical Approach:** Proportion achieving commitment, qualitative barriers

### Level 6 (Patient Outcomes) Measurement

| Method | Description | Timing |
|--------|-------------|--------|
| Chart Audit | Chart review for quality metrics | 6+ months |
| Registry Data | Quality measure performance | 6+ months |
| Patient-Reported Outcomes | PRO measures | 6+ months |

**Note:** Level 6 measurement is rarely achievable for single activities; include only when feasible.

---

## Quality Criteria

### Protocol Completeness
- [ ] Background and rationale clearly stated
- [ ] Study objectives aligned to learning objectives
- [ ] Study design appropriate and justified
- [ ] Population clearly defined with inclusion/exclusion
- [ ] Primary outcome clearly specified
- [ ] Secondary outcomes listed and defined
- [ ] Assessment instruments described
- [ ] Data collection plan complete
- [ ] Statistical analysis plan appropriate
- [ ] Ethical considerations addressed
- [ ] Limitations acknowledged
- [ ] Timeline realistic

### Methodological Quality
- [ ] Design appropriate for research questions
- [ ] Outcomes measurable and defined
- [ ] Timeline allows adequate follow-up
- [ ] Attrition/response rates addressed
- [ ] Statistical methods appropriate
- [ ] Practical implementation feasible

### Alignment
- [ ] Every learning objective has measurement
- [ ] Measurement methods match Moore levels
- [ ] Timepoints align with curriculum design
- [ ] Protocol integrates with grant package

---

## Example Output Excerpt

```yaml
protocol_summary:
  title: "Outcomes Evaluation of Heart Failure Management CME Program"
  study_type: "Prospective single-arm educational outcomes study"
  primary_endpoint: "Change in evidence-based prescribing behaviors at 60 days"
  secondary_endpoints:
    - "Improvement in case-based competence assessment scores"
    - "Knowledge retention at 30 days"
    - "Barriers to practice change implementation"
  study_duration: "6 months (enrollment through final follow-up)"
  target_enrollment: 200

study_design:
  design_type: "Single-arm pre-post with longitudinal follow-up"
  design_rationale: |
    A single-arm pre-post design is selected as the most practical approach 
    for evaluating this educational intervention. While a randomized 
    controlled design would provide stronger causal inference, the logistics 
    of CME delivery and ethical considerations of withholding education from 
    a control group make this impractical. The pre-post design allows 
    measurement of change while acknowledging the inherent limitations.
  
  study_population:
    inclusion_criteria:
      - "Licensed physician (MD/DO) or advanced practice provider (NP/PA)"
      - "Currently managing patients with heart failure"
      - "Minimum 5 HF patients seen per month"
      - "Able to complete follow-up assessments"
    exclusion_criteria:
      - "Participated in similar HF education in past 6 months"
      - "Retired or not in active clinical practice"
      - "Unable to provide informed consent"
  
  sample_size:
    target_n: 200
    power_calculation: |
      Based on prior CME outcomes research, we anticipate a medium effect 
      size (d=0.5) for practice change outcomes. With α=0.05 and power=0.80, 
      64 participants would be needed for paired comparison. Assuming 40% 
      attrition by 60-day follow-up (typical for CME studies), we target 
      200 initial participants to achieve 120 completers.
    dropout_assumptions: "40% attrition expected between baseline and 60-day follow-up"

outcome_measures:
  primary_outcome:
    measure_name: "Self-reported evidence-based prescribing change"
    moore_level: "Level 5 (Performance)"
    definition: "Proportion of participants reporting implementation of at least 2 of 3 targeted practice changes"
    measurement_method: "Follow-up survey with specific prescribing behavior questions"
    timing: "60 days post-activity"
    success_threshold: "≥50% of respondents report implementing 2+ changes"
  
  secondary_outcomes:
    - measure_name: "Competence assessment score change"
      moore_level: "Level 4 (Competence)"
      definition: "Mean change in case-based assessment score (0-100 scale)"
      measurement_method: "Validated case vignette assessment"
      timing: "Pre-activity and immediate post-activity"
    
    - measure_name: "Knowledge retention"
      moore_level: "Level 3 (Learning)"
      definition: "Knowledge assessment score at 30 days"
      measurement_method: "10-item knowledge assessment"
      timing: "30 days post-activity"

statistical_analysis_plan:
  primary_analysis:
    method: "Descriptive statistics with 95% confidence intervals"
    description: |
      The primary analysis will calculate the proportion of respondents 
      reporting implementation of 2+ targeted practice changes at 60-day 
      follow-up, with 95% confidence interval. Success will be defined as 
      achieving the pre-specified threshold of ≥50%.
  
  secondary_analyses:
    - analysis: "Competence score change"
      method: "Paired t-test comparing pre and immediate post scores"
    - analysis: "Knowledge retention"
      method: "Descriptive comparison of immediate post to 30-day scores"
    - analysis: "Barrier analysis"
      method: "Qualitative coding of free-text barriers reported"
  
  handling_missing_data: |
    Missing data will be handled as follows: participants who do not 
    complete follow-up will be excluded from the primary analysis (complete 
    case analysis). Sensitivity analyses will include: (1) worst-case 
    imputation assuming non-responders did not change practice, and 
    (2) multiple imputation if missing data exceeds 30%.
```

---

## Error Handling

| Error | Response |
|-------|----------|
| Objective lacks measurement | Design appropriate assessment instrument |
| Timeline unrealistic | Adjust follow-up duration or expectations |
| Sample size insufficient | Adjust power expectations or increase target |
| Level 6 not feasible | Focus on Level 5 with acknowledgment |
| Statistical method inappropriate | Select method appropriate to data type |

---

## Dependencies

### Upstream
- Learning Objectives Agent output (required)
- Curriculum Design Agent output (assessment strategy)
- Gap Analysis Agent output (baseline context)

### Downstream
- Grant Writer Agent (protocol section)

---

## Testing Scenarios

### Test Case 1: Level 5-Focused Activity
- Expected: Commitment-to-change methodology prominent
- Verify: Follow-up mechanism well-specified

### Test Case 2: Level 4-Focused Activity
- Expected: Case-based assessment methodology
- Verify: Scoring rubric included

### Test Case 3: Multi-Activity Series
- Expected: Longitudinal design consideration
- Verify: Cross-activity measurement addressed

---

*The research protocol demonstrates rigor and sets expectations for evaluation.*
