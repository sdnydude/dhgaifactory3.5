# Agent 4: Gap Analysis Agent
## Synthesize and Quantify Educational Gaps

**Agent Type:** LLM-powered  
**Complexity:** Medium  
**Primary Output:** 5+ prioritized, evidence-based educational gaps

---

## Role Definition

The Gap Analysis Agent synthesizes inputs from Research and Clinical Practice agents to identify, quantify, and prioritize educational gaps. Each gap must be evidence-based, addressable through education, and connected to patient outcomes. The output directly drives the Needs Assessment narrative.

---

## Inputs

### From Other Agents
| Agent | Data Used |
|-------|-----------|
| Research Agent (2) | Epidemiology, guidelines, treatment landscape, evidence gaps |
| Clinical Practice Agent (3) | Practice patterns, barriers, utilization data, quality metrics |

### From Intake Form
| Field | Section | Purpose |
|-------|---------|---------|
| known_gaps | D | Pre-identified gaps to validate/incorporate |
| educational_priorities | D | Supporter priorities to consider |
| outcome_goals | D | Desired impact areas |

---

## Outputs

### Gap Analysis Structure

```yaml
gap_analysis_output:
  metadata:
    agent_version: "2.0"
    execution_timestamp: datetime
    gaps_identified: int
    gaps_prioritized: int
  
  synthesis_summary:
    evidence_base: str  # Summary of research findings
    practice_reality: str  # Summary of clinical practice findings
    key_disconnects: List[str]  # Where evidence and practice diverge
  
  gaps:
    - gap_id: str  # "GAP-001"
      title: str  # Concise gap statement
      description: str  # 2-3 sentence elaboration
      
      evidence:
        guideline_recommendation: str
        current_practice: str
        practice_guideline_delta: str  # Quantified gap
        supporting_data: List[Dict]
      
      root_causes:
        primary_barrier_type: str  # "knowledge", "skill", "attitude", "system"
        contributing_factors: List[str]
        barrier_evidence: str
      
      patient_impact:
        affected_population: str
        outcome_consequence: str
        quantified_impact: str  # "X% increased mortality" etc.
      
      educational_addressability:
        addressable: bool
        rationale: str
        expected_impact: str
        limitations: str
      
      priority_score:
        score: int  # 1-10
        rationale: str
      
      alignment:
        moore_level_target: str  # "Level 4", "Level 5", etc.
        accme_criteria_addressed: List[str]
        supporter_priority_alignment: str
  
  gap_prioritization:
    methodology: str
    scoring_criteria:
      - criterion: str
        weight: float
    ranked_gaps: List[str]  # Gap IDs in priority order
  
  recommendations:
    primary_focus: List[str]  # Top 3 gaps for deep focus
    secondary_focus: List[str]  # Supporting gaps
    gaps_requiring_system_change: List[str]  # Not primarily educational
```

---

## System Prompt

```
You are an educational gap analyst synthesizing research evidence and clinical practice data to identify educational needs for continuing medical education. Your analysis must:

1. SYNTHESIZE: Integrate research findings with practice reality to identify disconnects
2. QUANTIFY: Every gap must have numerical evidence of the practice-guideline delta
3. ROOT CAUSE: Identify WHY the gap exists, categorizing barriers appropriately
4. PATIENT IMPACT: Connect every gap to patient outcomes
5. PRIORITIZE: Rank gaps by educational addressability and potential impact

GAP DEFINITION CRITERIA:
A valid educational gap must meet ALL of these criteria:
- Evidence-based: Supported by research data
- Quantifiable: Practice-guideline delta can be measured
- Addressable: Education can reasonably impact the gap
- Outcome-linked: Gap closure would improve patient outcomes
- Barrier-analyzed: Root cause identified and categorized

GAP PRIORITIZATION FACTORS:
1. Magnitude of practice-guideline delta (larger = higher priority)
2. Patient outcome impact (more severe = higher priority)
3. Educational addressability (more addressable = higher priority)
4. Alignment with supporter priorities (higher alignment = higher priority)
5. Feasibility of measurement (more measurable = higher priority)

OUTPUT REQUIREMENTS:
- Minimum 5 distinct, well-documented gaps
- Maximum 8 gaps (focus over breadth)
- Each gap must have quantified evidence
- Each gap must have barrier categorization
- Each gap must have patient impact statement
- Gaps must be prioritized with transparent scoring

PROHIBITED:
- Gaps without quantified evidence
- Gaps that are purely system/policy issues
- Duplicate gaps with different wording
- Gaps outside educational addressability
- Vague or generic gap statements
```

---

## Gap Validation Framework

### Mandatory Elements for Each Gap

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GAP VALIDATION CHECKLIST                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  □ EVIDENCE-BASED                                                           │
│    └─ Guideline recommendation clearly stated                               │
│    └─ Current practice data from credible source                            │
│    └─ Delta quantified with specific numbers                                │
│                                                                             │
│  □ BARRIER-ANALYZED                                                         │
│    └─ Primary barrier type identified (knowledge/skill/attitude/system)     │
│    └─ Root cause explanation provided                                       │
│    └─ Barrier evidence cited                                                │
│                                                                             │
│  □ OUTCOME-LINKED                                                           │
│    └─ Affected patient population defined                                   │
│    └─ Clinical consequence stated                                           │
│    └─ Impact quantified where possible                                      │
│                                                                             │
│  □ EDUCATIONALLY ADDRESSABLE                                                │
│    └─ Education can reasonably impact this gap                              │
│    └─ Expected educational impact stated                                    │
│    └─ Limitations acknowledged                                              │
│                                                                             │
│  □ MEASURABLE                                                               │
│    └─ Baseline can be established                                           │
│    └─ Change can be measured post-education                                 │
│    └─ Moore's level target identified                                       │
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
│  1. Ingest upstream outputs         │
│     - Load research_output          │
│     - Load clinical_output          │
│     - Extract intake known_gaps     │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  2. Identify evidence-practice      │
│     disconnects                     │
│     - Compare guidelines to practice│
│     - Quantify deltas               │
│     - Note areas of alignment       │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  3. Analyze root causes             │
│     - Map barriers from clinical    │
│     - Categorize barrier types      │
│     - Identify primary vs secondary │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  4. Connect to patient outcomes     │
│     - Link gaps to outcome data     │
│     - Quantify patient impact       │
│     - Identify affected populations │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  5. Assess educational              │
│     addressability                  │
│     - Filter system-only gaps       │
│     - Evaluate education potential  │
│     - Note limitations              │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  6. Prioritize gaps                 │
│     - Apply scoring criteria        │
│     - Rank by composite score       │
│     - Validate against intake       │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  7. Structure final output          │
│     - Format each gap fully         │
│     - Include prioritization logic  │
│     - Add recommendations           │
└─────────────────────────────────────┘
  │
  ▼
OUTPUT: gap_analysis_output
```

---

## Prioritization Scoring

### Scoring Criteria (100 points total)

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Gap Magnitude | 25 | Size of practice-guideline delta |
| Patient Impact | 25 | Severity of outcome consequences |
| Educational Addressability | 20 | Likelihood education can close gap |
| Measurability | 15 | Ability to measure change |
| Alignment | 15 | Fit with supporter/program priorities |

### Scoring Rubric

**Gap Magnitude (25 points)**
- 25: Delta >50% of target
- 20: Delta 30-50% of target
- 15: Delta 15-30% of target
- 10: Delta <15% of target

**Patient Impact (25 points)**
- 25: Mortality/major morbidity impact
- 20: Significant morbidity/hospitalization
- 15: Quality of life/symptom impact
- 10: Efficiency/convenience impact

**Educational Addressability (20 points)**
- 20: Primarily knowledge/skill gap
- 15: Mixed knowledge/attitude gap
- 10: Significant system component
- 5: Primarily system/policy gap

**Measurability (15 points)**
- 15: Established quality metrics exist
- 10: Can measure with commitment-to-change
- 5: Measurement challenging

**Alignment (15 points)**
- 15: Directly addresses supporter priority
- 10: Related to supporter interest
- 5: Tangentially connected

---

## Quality Criteria

### Gap Quality Checklist
- [ ] Minimum 5 gaps identified
- [ ] Maximum 8 gaps (maintains focus)
- [ ] Each gap has quantified practice-guideline delta
- [ ] Each gap has categorized barrier (knowledge/skill/attitude/system)
- [ ] Each gap has patient outcome connection
- [ ] Each gap has educational addressability assessment
- [ ] Gaps are ranked with transparent scoring
- [ ] Top 3 gaps clearly identified for primary focus

### Evidence Quality
- [ ] All guideline references are specific and dated
- [ ] All practice data cites source (registry, claims, survey)
- [ ] All delta calculations show numerator and denominator
- [ ] Barrier evidence comes from clinical practice output

### Synthesis Quality
- [ ] Research and clinical findings are integrated
- [ ] Contradictions are acknowledged and resolved
- [ ] Gaps build logically from evidence base
- [ ] No gaps are redundant or overlapping

---

## Example Output Excerpt

```yaml
gaps:
  - gap_id: "GAP-001"
    title: "Suboptimal SGLT2 Inhibitor Initiation in Heart Failure"
    description: "Despite Class I guideline recommendations, fewer than one-quarter of eligible HFrEF patients receive SGLT2 inhibitor therapy, with median time to initiation exceeding 8 months after diagnosis."
    
    evidence:
      guideline_recommendation: "2022 AHA/ACC/HFSA Guidelines: SGLT2i recommended for all HFrEF patients (Class I, Level A)"
      current_practice: "23% of eligible patients prescribed SGLT2i (PINNACLE Registry 2023)"
      practice_guideline_delta: "77% gap between guideline recommendation (100%) and actual prescribing (23%)"
      supporting_data:
        - source: "PINNACLE Registry Q3 2023"
          finding: "SGLT2i prescribed in 23% of eligible HFrEF"
        - source: "GWTG-HF 2023"
          finding: "Median time to SGLT2i initiation: 8.2 months"
        - source: "Claims analysis, Greene et al. JACC 2024"
          finding: "Only 12% initiated within 30 days of diagnosis"
    
    root_causes:
      primary_barrier_type: "knowledge"
      contributing_factors:
        - "Lack of awareness that SGLT2i recommended regardless of diabetes status"
        - "Unfamiliarity with initiation protocols and monitoring"
        - "Uncertainty about safety in volume-depleted patients"
      barrier_evidence: "Survey of 500 PCPs: 62% unaware of HF indication for SGLT2i (Smith et al., JGIM 2023); 78% report concerns about hypotension (CME needs assessment)"
    
    patient_impact:
      affected_population: "Approximately 5.2 million Americans with HFrEF"
      outcome_consequence: "Delayed or absent SGLT2i therapy increases hospitalization and mortality risk"
      quantified_impact: "SGLT2i reduces HF hospitalization by 31% (EMPEROR-Reduced); 77% of patients not receiving this benefit"
    
    educational_addressability:
      addressable: true
      rationale: "Primary barriers are knowledge and skill gaps, both directly addressable through education"
      expected_impact: "Education can increase awareness to >90% and improve initiation confidence"
      limitations: "System barriers (prior auth) will persist; education can include workflow strategies"
    
    priority_score:
      score: 92
      rationale: "Large gap magnitude (25/25), major patient impact (25/25), highly addressable (20/20), measurable via registry (12/15), strong supporter alignment (10/15)"
    
    alignment:
      moore_level_target: "Level 5 (Performance)"
      accme_criteria_addressed: ["Practice Gap", "Educational Need", "Desired Outcome"]
      supporter_priority_alignment: "Direct alignment with dapagliflozin portfolio"

  - gap_id: "GAP-002"
    title: "Inadequate Dose Optimization of Foundational HF Therapies"
    description: "Among patients initiated on guideline-directed medical therapy, fewer than 20% achieve target doses, with dose titration often abandoned after initial response."
    
    # ... similar structure continues ...

gap_prioritization:
  methodology: "Weighted multi-criteria scoring with validation against supporter priorities and ACCME requirements"
  scoring_criteria:
    - criterion: "Gap Magnitude"
      weight: 0.25
    - criterion: "Patient Impact"
      weight: 0.25
    - criterion: "Educational Addressability"
      weight: 0.20
    - criterion: "Measurability"
      weight: 0.15
    - criterion: "Alignment"
      weight: 0.15
  ranked_gaps:
    - "GAP-001"  # Score: 92
    - "GAP-003"  # Score: 87
    - "GAP-002"  # Score: 84
    - "GAP-004"  # Score: 78
    - "GAP-005"  # Score: 71

recommendations:
  primary_focus:
    - "GAP-001: SGLT2i initiation"
    - "GAP-003: HFpEF recognition and management"
    - "GAP-002: GDMT dose optimization"
  secondary_focus:
    - "GAP-004: Remote monitoring utilization"
    - "GAP-005: Cardiac rehab referral"
  gaps_requiring_system_change:
    - "Prior authorization delays (identified but not primary focus)"
    - "Specialist access in rural areas (acknowledged limitation)"
```

---

## Error Handling

| Error | Response |
|-------|----------|
| Insufficient research data | Flag gap as "limited evidence," lower priority score |
| Conflicting practice data | Use most recent/largest source, note discrepancy |
| Gap not educationally addressable | Include in "system change required" section, not main gaps |
| Too many potential gaps | Apply strict prioritization, focus top 5-6 |
| Gaps don't align with supporter | Include but note alignment limitation |

---

## Dependencies

### Upstream
- Research Agent output (required)
- Clinical Practice Agent output (required)
- Intake form known_gaps (optional enhancement)

### Downstream
- Needs Assessment Agent (primary consumer)
- Learning Objectives Agent (gap-to-objective mapping)
- All subsequent agents (gap context)

---

## Testing Scenarios

### Test Case 1: Clear Evidence-Practice Gaps (HF GDMT)
- Expected: Multiple well-documented gaps with registry data
- Verify: 5+ gaps, all with quantified deltas

### Test Case 2: Emerging Evidence Area
- Expected: Gaps based on newer data, less registry support
- Verify: Handles limited practice data, appropriate uncertainty

### Test Case 3: Primarily System Barriers
- Expected: Many gaps have system root causes
- Verify: Correctly identifies educational limitations, suggests hybrid approaches

---

*Gap Analysis output is the critical bridge between evidence and educational design. Each gap must be bulletproof.*
