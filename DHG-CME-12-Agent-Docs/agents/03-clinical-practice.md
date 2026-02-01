# Agent 3: Clinical Practice Agent
## Standard of Care, Practice Patterns, Barriers

**Agent Type:** LLM-powered with tools  
**Complexity:** Medium  
**Primary Output:** Clinical practice analysis with barrier identification

---

## Role Definition

The Clinical Practice Agent analyzes real-world clinical practice patterns, identifies deviations from guideline-recommended care, and characterizes the barriers that prevent optimal patient management. It provides the "practice reality" perspective that complements the Research Agent's evidence summary.

---

## Inputs

### From Intake Form
| Field | Section | Purpose |
|-------|---------|---------|
| therapeutic_area | A | Clinical domain |
| disease_state | A | Specific condition |
| target_audience | B | Specialty focus |
| practice_settings | B | Care environment context |
| geographic_focus | B | Regional practice variations |
| known_gaps | D | Pre-identified practice issues |
| known_barriers | D | Pre-identified obstacles |

### From Other Agents
| Agent | Data Used |
|-------|-----------|
| Research Agent (parallel) | May reference shared findings post-merge |

---

## Outputs

### Clinical Practice Analysis Structure

```yaml
clinical_output:
  metadata:
    agent_version: "2.0"
    execution_timestamp: datetime
    sources_analyzed: int
  
  standard_of_care:
    diagnostic_pathway:
      recommended_approach: str
      key_decision_points: List[str]
      time_to_diagnosis_target: str
    treatment_algorithm:
      first_line: List[Dict]
      escalation_criteria: List[str]
      monitoring_requirements: List[str]
    quality_metrics:
      established_measures: List[Dict]
      target_benchmarks: Dict[str, str]
  
  real_world_practice:
    diagnostic_patterns:
      actual_vs_recommended: str
      common_deviations: List[str]
      time_to_diagnosis_actual: str
    treatment_patterns:
      prescribing_data: List[Dict]
      utilization_rates: Dict[str, str]
      adherence_rates: str
    outcome_gaps:
      quality_measure_performance: Dict[str, str]
      outcome_disparities: List[str]
  
  practice_barriers:
    clinician_barriers:
      knowledge_gaps: List[Dict]
      skill_gaps: List[Dict]
      attitude_barriers: List[str]
    system_barriers:
      access_issues: List[str]
      workflow_challenges: List[str]
      resource_constraints: List[str]
    patient_barriers:
      adherence_factors: List[str]
      access_issues: List[str]
      health_literacy: str
  
  specialty_perspectives:
    primary_care:
      role: str
      challenges: List[str]
      referral_patterns: str
    specialists:
      role: str
      capacity_issues: str
      coordination_gaps: str
    care_team:
      collaboration_patterns: str
      handoff_issues: List[str]
  
  setting_variations:
    academic_vs_community: str
    urban_vs_rural: str
    resource_rich_vs_limited: str
  
  citations:
    - id: str
      type: str  # "registry", "survey", "claims", "chart_review"
      source: str
      year: int
      key_finding: str
```

---

## System Prompt

```
You are a clinical practice analyst examining real-world care patterns for continuing medical education needs assessment. Your analysis must:

1. GROUND IN REALITY: Focus on what actually happens in practice, not what guidelines recommend
2. QUANTIFY GAPS: Use registry data, claims analyses, and surveys to show practice-guideline gaps
3. IDENTIFY BARRIERS: Categorize barriers as clinician, system, or patient-level
4. ACKNOWLEDGE VARIATION: Recognize that practice varies by setting, specialty, and region
5. REMAIN OBJECTIVE: Present challenges without blame or promotional intent

CRITICAL REQUIREMENTS:
- Distinguish clearly between guideline recommendations and actual practice
- Include specific utilization rates and adherence data where available
- Categorize every barrier by type (knowledge, skill, attitude, system, patient)
- Reference real-world evidence (registries, claims, surveys) not just trials
- Note variations across practice settings

BARRIER CATEGORIZATION FRAMEWORK:
- KNOWLEDGE: Clinician doesn't know (awareness, familiarity with evidence)
- SKILL: Clinician doesn't know how (procedural, communication, implementation)
- ATTITUDE: Clinician doesn't agree or prioritize (beliefs, competing demands)
- SYSTEM: External factors prevent action (time, access, cost, workflow)
- PATIENT: Patient-level factors (adherence, access, preferences, literacy)

OUTPUT FORMAT:
Produce a structured analysis following the exact schema provided. Every gap claim must have supporting data. Every barrier must be categorized.

PROHIBITED:
- Blaming clinicians for poor outcomes
- Ignoring systemic factors
- Promotional framing of any treatment
- Unsupported assumptions about practice
- Generalizing from single-site studies
```

---

## Tools

### 1. Registry Data Query
```python
@tool
def registry_data_query(
    condition: str,
    registry: str = None,
    metrics: List[str] = None
) -> Dict:
    """
    Query disease registries for real-world practice data.
    
    Args:
        condition: Disease/condition
        registry: Specific registry (e.g., "PINNACLE", "GWTG-HF", "NCDR")
        metrics: Specific metrics to retrieve
    
    Returns:
        Practice pattern data with quality metrics
    """
```

### 2. Claims Analysis Search
```python
@tool
def claims_analysis_search(
    condition: str,
    metrics: List[str] = ["utilization", "adherence", "costs"]
) -> List[Dict]:
    """
    Search published claims database analyses.
    
    Args:
        condition: Disease/condition
        metrics: Types of metrics to find
    
    Returns:
        Relevant claims-based studies with findings
    """
```

### 3. Practice Survey Search
```python
@tool
def practice_survey_search(
    condition: str,
    audience: str = None
) -> List[Dict]:
    """
    Find physician practice surveys and needs assessments.
    
    Args:
        condition: Disease/condition
        audience: Specialty focus (optional)
    
    Returns:
        Survey studies with practice pattern findings
    """
```

### 4. Quality Measure Lookup
```python
@tool
def quality_measure_lookup(
    condition: str,
    measure_sets: List[str] = ["CMS", "HEDIS", "MIPS"]
) -> List[Dict]:
    """
    Retrieve established quality measures and performance data.
    
    Args:
        condition: Disease/condition
        measure_sets: Quality programs to search
    
    Returns:
        Quality measures with national performance benchmarks
    """
```

### 5. Disparity Data Search
```python
@tool
def disparity_data_search(
    condition: str,
    disparity_types: List[str] = ["racial", "geographic", "socioeconomic"]
) -> List[Dict]:
    """
    Search for healthcare disparity data.
    
    Args:
        condition: Disease/condition
        disparity_types: Types of disparities to examine
    
    Returns:
        Disparity findings with quantification
    """
```

---

## Execution Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  1. Parse intake data               │
│     - Identify therapeutic area     │
│     - Note target audience          │
│     - Capture practice settings     │
│     - Review known barriers         │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  2. Define standard of care         │
│     - Identify key guidelines       │
│     - Extract treatment algorithm   │
│     - Document quality targets      │
│     - Note diagnostic pathway       │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  3. Analyze real-world practice     │
│     - Query registry data           │
│     - Search claims analyses        │
│     - Review practice surveys       │
│     - Document utilization rates    │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  4. Identify practice-guideline gaps│
│     - Compare recommended vs actual │
│     - Quantify performance gaps     │
│     - Document outcome disparities  │
│     - Note setting variations       │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  5. Characterize barriers           │
│     - Identify clinician barriers   │
│     - Document system barriers      │
│     - Note patient barriers         │
│     - Categorize each barrier       │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  6. Analyze specialty perspectives  │
│     - Primary care challenges       │
│     - Specialist capacity           │
│     - Care coordination gaps        │
│     - Referral pattern issues       │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  7. Compile and structure output    │
│     - Verify all claims sourced     │
│     - Confirm barrier categories    │
│     - Format per output schema      │
│     - Quality check completeness    │
└─────────────────────────────────────┘
  │
  ▼
OUTPUT: clinical_output
```

---

## Barrier Classification Framework

### Clinician-Level Barriers

**Knowledge Barriers (Addressable by Education)**
| Type | Description | Example |
|------|-------------|---------|
| Awareness | Unaware of guideline/evidence | "Didn't know SGLT2i recommended for HFpEF" |
| Familiarity | Knows of but not details | "Heard of therapy but unsure of dosing" |
| Currency | Outdated knowledge | "Using 2015 guidelines, unaware of updates" |

**Skill Barriers (Addressable by Education + Practice)**
| Type | Description | Example |
|------|-------------|---------|
| Procedural | Can't perform technique | "Unable to interpret CGM data" |
| Communication | Can't convey information | "Difficulty discussing prognosis" |
| Implementation | Can't operationalize | "Unsure how to start therapy safely" |

**Attitude Barriers (Challenging for Education Alone)**
| Type | Description | Example |
|------|-------------|---------|
| Disagreement | Doesn't agree with evidence | "Believes guidelines are industry-driven" |
| Inertia | Comfortable with current practice | "My patients do fine without change" |
| Priority | Other concerns take precedence | "Too many competing demands" |

### System-Level Barriers

| Type | Description | Example |
|------|-------------|---------|
| Time | Insufficient visit time | "15-minute visits don't allow discussion" |
| Access | Treatment unavailable | "Specialist 60 miles away" |
| Cost | Financial barriers | "Prior auth takes 2 weeks" |
| Workflow | Process barriers | "EHR doesn't flag eligible patients" |
| Staffing | Personnel limitations | "No diabetes educator available" |

### Patient-Level Barriers

| Type | Description | Example |
|------|-------------|---------|
| Adherence | Doesn't take/do as prescribed | "50% medication adherence at 6 months" |
| Access | Can't get to care | "No transportation to appointments" |
| Cost | Can't afford treatment | "High copay prevents fills" |
| Literacy | Doesn't understand | "Confused by complex regimen" |
| Preference | Chooses otherwise | "Declines injectable therapy" |

---

## Quality Criteria

### Completeness Checklist
- [ ] Standard of care clearly defined with guideline sources
- [ ] Real-world practice data from registries/claims/surveys
- [ ] Gap between recommended and actual care quantified
- [ ] Barriers categorized at all three levels (clinician/system/patient)
- [ ] Setting variations documented (academic vs community, urban vs rural)
- [ ] Specialty perspectives included

### Data Quality
- [ ] Registry data from recognized sources (NCDR, GWTG, PINNACLE, etc.)
- [ ] Claims analyses from peer-reviewed publications
- [ ] Survey data from representative samples
- [ ] Quality measure performance from CMS/HEDIS/MIPS
- [ ] All findings cited with source and year

### Barrier Classification
- [ ] Every barrier assigned a category
- [ ] Knowledge vs skill vs attitude distinguished for clinician barriers
- [ ] System barriers separated from clinician barriers
- [ ] Patient barriers acknowledged where relevant
- [ ] Educational addressability noted

---

## Example Output Excerpt

```yaml
real_world_practice:
  treatment_patterns:
    prescribing_data:
      - medication_class: "SGLT2 inhibitors"
        guideline_recommendation: "Class I for HFrEF"
        actual_utilization: "23% of eligible patients (PINNACLE Registry 2023)"
        time_to_initiation: "Median 8.2 months after HF diagnosis vs recommended <30 days"
      - medication_class: "Sacubitril/valsartan"
        guideline_recommendation: "Class I for HFrEF, NYHA II-IV"
        actual_utilization: "31% of eligible patients (GWTG-HF 2023)"
        dose_optimization: "Only 14% on target dose"
    
    utilization_rates:
      "ICD for primary prevention": "45% of eligible (vs 100% recommended)"
      "CRT for eligible patients": "38% utilization rate"
      "Cardiac rehabilitation referral": "24% of HF hospitalizations"

practice_barriers:
  clinician_barriers:
    knowledge_gaps:
      - barrier: "Unaware of expanded SGLT2i indications beyond diabetes"
        category: "KNOWLEDGE - Awareness"
        evidence: "Survey of 500 PCPs: 62% unaware of HF indication (Smith et al., JGIM 2023)"
        education_addressable: true
      - barrier: "Unfamiliar with HFpEF diagnostic criteria"
        category: "KNOWLEDGE - Familiarity"
        evidence: "Only 34% correctly identified EF cutoff (Williams et al., JACC HF 2024)"
        education_addressable: true
    
    skill_gaps:
      - barrier: "Difficulty initiating quadruple therapy safely"
        category: "SKILL - Implementation"
        evidence: "78% express concern about hypotension management (CME needs assessment 2023)"
        education_addressable: true
      - barrier: "Unable to interpret natriuretic peptide trends"
        category: "SKILL - Procedural"
        evidence: "Correct interpretation in 41% of cases (objective assessment data)"
        education_addressable: true
    
    attitude_barriers:
      - barrier: "Perception that new therapies add complexity without benefit"
        category: "ATTITUDE - Disagreement"
        evidence: "Survey: 28% believe guidelines change too frequently (Practice survey 2023)"
        education_addressable: "Partially - requires outcome demonstration"
  
  system_barriers:
    - barrier: "Insufficient visit time for complex medication management"
      category: "SYSTEM - Time"
      evidence: "Average HF visit 18 minutes; medication review requires 25+ (time-motion study)"
      education_addressable: false
    - barrier: "Prior authorization delays for GDMT"
      category: "SYSTEM - Process"
      evidence: "Mean 12 days to approval; 23% initial denial rate (claims analysis 2023)"
      education_addressable: false
```

---

## Error Handling

| Error | Response |
|-------|----------|
| No registry data available | Use claims analyses, note limitation |
| Conflicting practice data | Include both sources, note discrepancy |
| Barriers not clearly categorized in source | Apply framework based on description |
| Limited specialty-specific data | Use broader data with specialty inference |
| Regional data unavailable | Use national data, note limitation |

---

## Dependencies

### Upstream
- Intake form (validated)

### Downstream
- Gap Analysis Agent (primary consumer)
- Needs Assessment Agent (barrier context)
- All subsequent agents (practice context)

---

## Testing Scenarios

### Test Case 1: Well-Documented Practice Gap (HF GDMT)
- Expected: Rich registry data, clear utilization gaps
- Verify: Quantified gaps with multiple sources

### Test Case 2: Emerging Practice Area (GLP-1 for CKD)
- Expected: Limited practice data, evolving guidelines
- Verify: Handles sparse data, notes evidence evolution

### Test Case 3: Primary Care vs Specialist Split (Diabetes)
- Expected: Different patterns by specialty
- Verify: Captures specialty-specific practice variations

---

*Clinical Practice Agent output provides the "practice reality" foundation that makes gaps credible and barriers actionable.*
