# Orchestrator Intake Data Passthrough Fix — Design Spec

## Problem

When a CME project specifies a disease state (e.g., "Polymyalgia Rheumatica"), the generated documents contain content about unrelated conditions (heart failure, psoriatic arthritis, Adult-Onset Still's Disease). Zero mentions of the actual disease appear in any output.

**Root cause:** The orchestrator's `run_*_agent()` wrapper functions strip most intake fields when constructing each agent's input. Every content agent declares `disease_state: str` in its TypedDict state but receives an empty string because the wrapper never passes it.

**Scope of data loss:** `flatten_intake()` correctly extracts 50+ fields from the sectioned intake form. The wrappers pass only 2-3 fields each — discarding disease_state, project_name, clinical_topics, supporter information, practice gaps, outcomes, compliance flags, and all other intake data.

## Solution

Expand each wrapper's `agent_input` dict to include all fields that the target agent's TypedDict declares as inputs. Add a handful of key aliases to `flatten_intake()` for fields where the intake form naming doesn't match what agents expect.

**File changed:** `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py` (single file)

**No agent code changes.** All 6 agents already declare these fields in their TypedDicts and reference them in their system prompts. The agents are designed to receive this data; the orchestrator just wasn't sending it.

## Detailed Changes

### 1. `flatten_intake()` — Add Missing Aliases (lines 249-363)

Several agent TypedDict fields don't have matching keys in the current `flatten_intake()` output. Add these aliases:

```python
# After Section E (Practice Gaps) — line ~315
# Agents expect a single "known_gaps" list; intake has 3 separate gap types
all_gaps = flat["knowledge_gaps"] + flat["competence_gaps"] + flat["performance_gaps"]
flat["known_gaps"] = all_gaps

# After Section F (Outcomes) — line ~323
# Learning Objectives and Gap Analysis agents expect "outcome_goals"
flat["outcome_goals"] = flat["primary_outcomes"]
# Learning Objectives agent expects singular "moore_level_target"
moore_list = flat["moore_levels_target"]
flat["moore_level_target"] = moore_list[0] if moore_list else ""

# After Section C (Educational Design) — line ~297
# Learning Objectives agent expects "educational_format"
flat["educational_format"] = flat["learning_format"]

# After Section G (Content Requirements) — line ~332
# Research and Compliance agents expect "competitor_products"
flat["competitor_products"] = flat["competitor_products_to_mention"]
```

Fields with no intake source (`practice_settings`, `known_barriers`, `educational_priorities`) are not added — agents already handle these as `Optional` with default empty values.

### 2. `run_research_agent()` — Expand Input (line 403)

**Current:**
```python
agent_input = {
    "therapeutic_area": state.get("intake_data", {}).get("therapeutic_area", ""),
    "target_audience": state.get("intake_data", {}).get("target_audience", ""),
    "research_questions": state.get("intake_data", {}).get("research_questions", []),
}
```

**New:**
```python
intake = state.get("intake_data", {})
agent_input = {
    "therapeutic_area": intake.get("therapeutic_area", ""),
    "disease_state": intake.get("disease_state", ""),
    "target_audience": intake.get("target_audience", ""),
    "geographic_focus": intake.get("geographic_focus", ""),
    "supporter_company": intake.get("supporter_company", ""),
    "supporter_products": intake.get("supporter_products", []),
    "known_gaps": intake.get("known_gaps", []),
    "competitor_products": intake.get("competitor_products", []),
    "research_questions": intake.get("research_questions", []),
}
```

Maps to `ResearchState` TypedDict (research_agent.py:63-72).

### 3. `run_clinical_agent()` — Expand Input (line 442)

**Current:**
```python
agent_input = {
    "therapeutic_area": state.get("intake_data", {}).get("therapeutic_area", ""),
    "target_audience": state.get("intake_data", {}).get("target_audience", ""),
}
```

**New:**
```python
intake = state.get("intake_data", {})
agent_input = {
    "therapeutic_area": intake.get("therapeutic_area", ""),
    "disease_state": intake.get("disease_state", ""),
    "target_audience": intake.get("target_audience", ""),
    "geographic_focus": intake.get("geographic_focus", ""),
    "practice_settings": intake.get("practice_settings", []),
    "known_gaps": intake.get("known_gaps", []),
    "known_barriers": intake.get("known_barriers", []),
}
```

Maps to `ClinicalPracticeState` TypedDict (clinical_practice_agent.py:66-74).

### 4. `run_gap_analysis_agent()` — Expand Input (line 480)

**Current:**
```python
agent_input = {
    "research_output": state.get("research_output", {}),
    "clinical_output": state.get("clinical_output", {}),
    "therapeutic_area": state.get("intake_data", {}).get("therapeutic_area", ""),
}
```

**New:**
```python
intake = state.get("intake_data", {})
agent_input = {
    "research_output": state.get("research_output", {}),
    "clinical_output": state.get("clinical_output", {}),
    "therapeutic_area": intake.get("therapeutic_area", ""),
    "disease_state": intake.get("disease_state", ""),
    "target_audience": intake.get("target_audience", ""),
    "known_gaps": intake.get("known_gaps", []),
    "educational_priorities": intake.get("educational_priorities", []),
    "outcome_goals": intake.get("outcome_goals", []),
}
```

Maps to `GapAnalysisState` TypedDict (gap_analysis_agent.py:53-67).

**Note:** GapAnalysisState declares `research_report` and `clinical_practice_report` as field names, but the orchestrator passes `research_output` and `clinical_output`. This is pre-existing behavior and out of scope for this fix — the agent's graph nodes may read from the actual input keys regardless of TypedDict field names.

### 5. `run_learning_objectives_agent()` — Expand Input (line 519)

**Current:**
```python
agent_input = {
    "gap_analysis_output": state.get("gap_analysis_output", {}),
    "needs_assessment_output": state.get("needs_assessment_output", {}),
    "target_audience": state.get("intake_data", {}).get("target_audience", ""),
}
```

**New:**
```python
intake = state.get("intake_data", {})
agent_input = {
    "gap_analysis_output": state.get("gap_analysis_output", {}),
    "needs_assessment_output": state.get("needs_assessment_output", {}),
    "target_audience": intake.get("target_audience", ""),
    "disease_state": intake.get("disease_state", ""),
    "therapeutic_area": intake.get("therapeutic_area", ""),
    "educational_format": intake.get("educational_format", ""),
    "outcome_goals": intake.get("outcome_goals", []),
    "moore_level_target": intake.get("moore_level_target", ""),
}
```

Maps to `LearningObjectivesState` TypedDict (learning_objectives_agent.py:68-82).

### 6. `run_needs_assessment_agent()` — No Changes Needed (line 564)

Already receives `intake_data` (full flattened dict). The upstream data contamination is fixed by correcting Research and Clinical agents. Once those produce correct-disease content, Needs Assessment inherits correct data.

### 7. `run_compliance_agent()` — Expand Input (line 882)

**Current:**
```python
agent_input = {
    "grant_package": grant_output,
    "supporter_company": state.get("intake_data", {}).get("supporter_company", ""),
}
```

**New:**
```python
intake = state.get("intake_data", {})
agent_input = {
    "grant_package": grant_output,
    "supporter_company": intake.get("supporter_company", ""),
    "supporter_products": intake.get("supporter_products", []),
    "competitor_products": intake.get("competitor_products", []),
    "accreditation_types": intake.get("accreditation_types", []),
}
```

Maps to `ComplianceState` TypedDict (compliance_review_agent.py:62-68).

**Note:** ComplianceState does not declare `disease_state` or `therapeutic_area`. Adding disease-content cross-validation to compliance is a separate enhancement (would require agent code + prompt changes). Not in scope here.

### 8. Enhanced Initialization Logging (line 377)

Add disease_state to the `initialize_pipeline` log line:

```python
logger.info(
    f"Pipeline initialized: project={flat.get('project_name', 'unknown')}, "
    f"area={flat.get('therapeutic_area', 'unknown')}, "
    f"disease={flat.get('disease_state', 'unknown')}, "
    f"audience={flat.get('target_audience', 'unknown')}, "
    f"fields_flattened={len(flat)}"
)
```

## What Does NOT Change

- **Agent source code** (0 of 6 agents modified)
- **Agent system prompts** (already reference disease_state)
- **Agent TypedDicts** (already declare all needed fields)
- **`flatten_intake()` structure** (only adding aliases, no restructuring)
- **Database schema** (no changes)
- **Frontend** (no changes)
- **Registry API** (no changes)
- **Pipeline graph topology** (same nodes, same edges)

## Verification Plan

1. **Unit test:** Verify `flatten_intake()` produces the new alias keys with correct values
2. **Integration test:** Run the PMR project ("Advances in the Management of Patients with PMR") through the pipeline after the fix
3. **Content audit:** Confirm all 6 generated documents reference polymyalgia rheumatica, NOT heart failure or psoriatic arthritis
4. **Regression:** Run an existing cardiology project to confirm it still produces correct output

## Known Issues Out of Scope

**Key name mismatches between orchestrator and agent TypedDicts:**
- Orchestrator passes `research_output` / `clinical_output` → GapAnalysisState declares `research_report` / `clinical_practice_report`
- Orchestrator passes `gap_analysis_output` / `needs_assessment_output` → LearningObjectivesState declares `gap_analysis_report` / `needs_assessment_document`

These are pre-existing and agents apparently handle them (their graph nodes may use the actual input key names). Investigating and fixing these is a separate concern.

**Compliance disease cross-validation:**
Adding `disease_state` to ComplianceState for content-disease mismatch detection would require agent code + prompt changes. Valuable safety net but separate scope.

## Risk Assessment

**Low risk.** Changes are additive — we're passing more data to agents that already expect it. Agents receiving additional fields they don't use simply ignore them (TypedDict is not enforced at runtime). Agents receiving fields they DO use will produce better-targeted content.

**No breaking changes.** Empty-string and empty-list defaults mean the behavior for projects with minimal intake data is unchanged.
