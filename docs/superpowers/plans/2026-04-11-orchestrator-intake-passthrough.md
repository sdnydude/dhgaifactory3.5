# Orchestrator Intake Data Passthrough Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the orchestrator so all 6 agent wrappers pass complete intake data (especially disease_state) to their target agents, eliminating wrong-disease content generation.

**Architecture:** Single-file change to `orchestrator.py`. Add key aliases to `flatten_intake()`, then expand `agent_input` dicts in 5 wrapper functions. No agent code changes.

**Tech Stack:** Python, LangGraph, pytest

**Spec:** `docs/superpowers/specs/2026-04-11-orchestrator-intake-passthrough-design.md`

---

### Task 1: Add flatten_intake() Alias Tests

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/tests/test_orchestrator.py`

- [ ] **Step 1: Write failing tests for new flatten_intake aliases**

Add this test class at the end of `test_orchestrator.py`:

```python
# ============================================================================
# flatten_intake tests
# ============================================================================


class TestFlattenIntake:
    """Tests for flatten_intake helper — especially new alias keys."""

    SAMPLE_SECTIONED_INTAKE = {
        "section_a": {
            "project_name": "PMR Management Update",
            "therapeutic_area": ["rheumatology"],
            "disease_state": ["polymyalgia rheumatica"],
            "target_audience_primary": ["rheumatologists", "internists"],
        },
        "section_b": {"supporter_name": "Acme Pharma"},
        "section_c": {"learning_format": "webinar", "include_post_test": False, "include_pre_test": False},
        "section_d": {
            "clinical_topics": ["glucocorticoid tapering", "IL-6 inhibitors"],
            "treatment_modalities": ["pharmacologic"],
            "patient_population": "adults over 50",
        },
        "section_e": {
            "knowledge_gaps": ["Optimal tapering protocols"],
            "competence_gaps": ["Distinguishing PMR from RA"],
            "performance_gaps": ["Monitoring for relapse"],
        },
        "section_f": {
            "primary_outcomes": ["Reduced relapse rate"],
            "moore_levels_target": ["Level 5", "Level 4"],
        },
        "section_g": {
            "competitor_products_to_mention": ["tocilizumab", "sarilumab"],
        },
        "section_h": {"geo_restrictions": ["US", "EU"]},
        "section_i": {"accme_compliant": True, "financial_disclosure_required": True,
                      "off_label_discussion": False, "commercial_support_acknowledgment": True},
        "section_j": {},
    }

    def test_disease_state_extracted(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["disease_state"] == ["polymyalgia rheumatica"]

    def test_known_gaps_combines_three_gap_types(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["known_gaps"] == [
            "Optimal tapering protocols",
            "Distinguishing PMR from RA",
            "Monitoring for relapse",
        ]

    def test_outcome_goals_aliases_primary_outcomes(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["outcome_goals"] == ["Reduced relapse rate"]

    def test_moore_level_target_takes_first(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["moore_level_target"] == "Level 5"

    def test_moore_level_target_empty_when_none(self):
        intake = {**self.SAMPLE_SECTIONED_INTAKE, "section_f": {}}
        flat = orch.flatten_intake(intake)
        assert flat["moore_level_target"] == ""

    def test_educational_format_aliases_learning_format(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["educational_format"] == "webinar"

    def test_competitor_products_aliases(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["competitor_products"] == ["tocilizumab", "sarilumab"]

    def test_geographic_focus_joins_list(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["geographic_focus"] == "US, EU"

    def test_already_flat_returns_as_is(self):
        flat_input = {"therapeutic_area": "oncology", "disease_state": "NSCLC"}
        result = orch.flatten_intake(flat_input)
        assert result == flat_input

    def test_supporter_company_maps_from_supporter_name(self):
        flat = orch.flatten_intake(self.SAMPLE_SECTIONED_INTAKE)
        assert flat["supporter_company"] == "Acme Pharma"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_orchestrator.py::TestFlattenIntake -v`

Expected: 4 tests FAIL (known_gaps, outcome_goals, moore_level_target, educational_format, competitor_products — these alias keys don't exist yet). The others (disease_state, geographic_focus, already_flat, supporter_company) should PASS since those already exist.

- [ ] **Step 3: Commit test file**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add langgraph_workflows/dhg-agents-cloud/tests/test_orchestrator.py
git commit -m "test: add flatten_intake alias tests (red — aliases not yet implemented)"
```

---

### Task 2: Add flatten_intake() Aliases

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py:249-363`

- [ ] **Step 1: Add aliases after each relevant section in flatten_intake()**

In `orchestrator.py`, make these 4 insertions:

**After line 297** (end of Section C block, after `flat["faculty_count"]`):
```python
    flat["educational_format"] = flat["learning_format"]  # learning_objectives agent alias
```

**After line 315** (end of Section E block, after `flat["gap_priority"]`):
```python
    # Agents expect a single "known_gaps" list; intake splits into 3 types
    flat["known_gaps"] = flat["knowledge_gaps"] + flat["competence_gaps"] + flat["performance_gaps"]
```

**After line 323** (end of Section F block, after `flat["follow_up_timeline"]`):
```python
    flat["outcome_goals"] = flat["primary_outcomes"]  # gap_analysis / learning_objectives alias
    moore_list = flat["moore_levels_target"]
    flat["moore_level_target"] = moore_list[0] if moore_list else ""  # singular alias
```

**After line 332** (end of Section G block, after `flat["regulatory_considerations"]`):
```python
    flat["competitor_products"] = flat["competitor_products_to_mention"]  # compliance / research alias
```

- [ ] **Step 2: Run flatten_intake tests to verify they pass**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_orchestrator.py::TestFlattenIntake -v`

Expected: All 10 tests PASS.

- [ ] **Step 3: Run full orchestrator test suite to verify no regressions**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_orchestrator.py -v`

Expected: All existing tests + new tests PASS.

- [ ] **Step 4: Commit**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add langgraph_workflows/dhg-agents-cloud/src/orchestrator.py
git commit -m "feat: add known_gaps, outcome_goals, educational_format, competitor_products aliases to flatten_intake"
```

---

### Task 3: Add Wrapper Passthrough Tests

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/tests/test_orchestrator.py`
- Modify: `langgraph_workflows/dhg-agents-cloud/tests/conftest.py`

- [ ] **Step 1: Update sample_pipeline_state fixture with disease-critical fields**

In `conftest.py`, update the `intake_data` dict inside `sample_pipeline_state` (line 145-157) to include the fields that wrappers will now pass:

```python
        "intake_data": {
            "therapeutic_area": "cardiology",
            "disease_state": "heart failure with reduced ejection fraction",
            "target_audience": "primary care physicians",
            "geographic_focus": "United States",
            "research_questions": ["What is current GDMT utilization?"],
            "project_name": "Test CME Project",
            "project_title": "Test Project",
            "activity_title": "Test Activity",
            "supporter_company": "Test Pharma",
            "supporter_products": ["sacubitril/valsartan"],
            "supporter_contact": "contact@test.com",
            "requested_amount": "$50,000",
            "known_gaps": ["Underutilization of GDMT"],
            "competitor_products": ["dapagliflozin"],
            "practice_settings": [],
            "known_barriers": [],
            "educational_priorities": [],
            "outcome_goals": ["Improved GDMT adherence"],
            "educational_format": "webinar",
            "moore_level_target": "Level 5",
            "accreditation_types": ["ACCME"],
            "budget_breakdown": {},
            "organization_info": {},
            "accreditation_statement": "AMA PRA Category 1",
        },
```

- [ ] **Step 2: Write wrapper passthrough tests**

Add this test class to `test_orchestrator.py`:

```python
# ============================================================================
# Wrapper agent_input passthrough tests
# ============================================================================


class TestWrapperPassthrough:
    """Verify that run_*_agent wrappers pass disease-critical intake fields."""

    @pytest.mark.asyncio
    async def test_research_agent_receives_disease_state(self, sample_pipeline_state):
        """run_research_agent must pass disease_state to the agent."""
        captured_input = {}

        async def fake_invoke(agent_input):
            captured_input.update(agent_input)
            return {"research_report": "mocked"}

        mock_graph = MagicMock()
        mock_graph.ainvoke = fake_invoke

        with patch("orchestrator.get_agent_graph", return_value=mock_graph):
            await orch.run_research_agent(sample_pipeline_state)

        assert captured_input["disease_state"] == "heart failure with reduced ejection fraction"
        assert captured_input["therapeutic_area"] == "cardiology"
        assert captured_input["supporter_company"] == "Test Pharma"
        assert captured_input["supporter_products"] == ["sacubitril/valsartan"]
        assert captured_input["known_gaps"] == ["Underutilization of GDMT"]
        assert captured_input["competitor_products"] == ["dapagliflozin"]
        assert captured_input["geographic_focus"] == "United States"

    @pytest.mark.asyncio
    async def test_clinical_agent_receives_disease_state(self, sample_pipeline_state):
        """run_clinical_agent must pass disease_state to the agent."""
        captured_input = {}

        async def fake_invoke(agent_input):
            captured_input.update(agent_input)
            return {"clinical_report": "mocked"}

        mock_graph = MagicMock()
        mock_graph.ainvoke = fake_invoke

        with patch("orchestrator.get_agent_graph", return_value=mock_graph):
            await orch.run_clinical_agent(sample_pipeline_state)

        assert captured_input["disease_state"] == "heart failure with reduced ejection fraction"
        assert captured_input["therapeutic_area"] == "cardiology"
        assert captured_input["geographic_focus"] == "United States"
        assert captured_input["known_gaps"] == ["Underutilization of GDMT"]

    @pytest.mark.asyncio
    async def test_gap_analysis_agent_receives_disease_state(self, sample_pipeline_state):
        """run_gap_analysis_agent must pass disease_state to the agent."""
        captured_input = {}

        async def fake_invoke(agent_input):
            captured_input.update(agent_input)
            return {"gap_report": "mocked"}

        mock_graph = MagicMock()
        mock_graph.ainvoke = fake_invoke

        with patch("orchestrator.get_agent_graph", return_value=mock_graph):
            await orch.run_gap_analysis_agent(sample_pipeline_state)

        assert captured_input["disease_state"] == "heart failure with reduced ejection fraction"
        assert captured_input["target_audience"] == "primary care physicians"
        assert captured_input["known_gaps"] == ["Underutilization of GDMT"]
        assert captured_input["outcome_goals"] == ["Improved GDMT adherence"]

    @pytest.mark.asyncio
    async def test_learning_objectives_agent_receives_disease_state(self, sample_pipeline_state):
        """run_learning_objectives_agent must pass disease_state to the agent."""
        captured_input = {}

        async def fake_invoke(agent_input):
            captured_input.update(agent_input)
            return {"lo_report": "mocked"}

        mock_graph = MagicMock()
        mock_graph.ainvoke = fake_invoke

        with patch("orchestrator.get_agent_graph", return_value=mock_graph):
            await orch.run_learning_objectives_agent(sample_pipeline_state)

        assert captured_input["disease_state"] == "heart failure with reduced ejection fraction"
        assert captured_input["therapeutic_area"] == "cardiology"
        assert captured_input["educational_format"] == "webinar"
        assert captured_input["moore_level_target"] == "Level 5"
        assert captured_input["outcome_goals"] == ["Improved GDMT adherence"]

    @pytest.mark.asyncio
    async def test_compliance_agent_receives_full_context(self, sample_pipeline_state):
        """run_compliance_agent must pass supporter_products and accreditation_types."""
        captured_input = {}
        sample_pipeline_state["grant_package_output"] = {"document": "mocked grant"}

        async def fake_invoke(agent_input):
            captured_input.update(agent_input)
            return {"compliance_report": "mocked"}

        mock_graph = MagicMock()
        mock_graph.ainvoke = fake_invoke

        with patch("orchestrator.get_agent_graph", return_value=mock_graph):
            await orch.run_compliance_agent(sample_pipeline_state)

        assert captured_input["supporter_company"] == "Test Pharma"
        assert captured_input["supporter_products"] == ["sacubitril/valsartan"]
        assert captured_input["competitor_products"] == ["dapagliflozin"]
        assert captured_input["accreditation_types"] == ["ACCME"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_orchestrator.py::TestWrapperPassthrough -v`

Expected: All 5 tests FAIL — wrappers don't yet pass disease_state or the other new fields.

- [ ] **Step 4: Commit test file**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add langgraph_workflows/dhg-agents-cloud/tests/test_orchestrator.py langgraph_workflows/dhg-agents-cloud/tests/conftest.py
git commit -m "test: add wrapper passthrough tests (red — wrappers not yet expanded)"
```

---

### Task 4: Expand Wrapper agent_input Dicts

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py`

- [ ] **Step 1: Expand run_research_agent (line 403)**

Replace the `agent_input` block:

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

- [ ] **Step 2: Expand run_clinical_agent (line 442)**

Replace the `agent_input` block:

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

- [ ] **Step 3: Expand run_gap_analysis_agent (line 480)**

Replace the `agent_input` block:

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

- [ ] **Step 4: Expand run_learning_objectives_agent (line 519)**

Replace the `agent_input` block:

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

- [ ] **Step 5: Expand run_compliance_agent (line 882)**

Replace the `agent_input` block:

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

- [ ] **Step 6: Run wrapper passthrough tests**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_orchestrator.py::TestWrapperPassthrough -v`

Expected: All 5 tests PASS.

- [ ] **Step 7: Run full test suite**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_orchestrator.py -v`

Expected: All tests PASS (existing + new flatten_intake + new wrapper tests).

- [ ] **Step 8: Commit**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add langgraph_workflows/dhg-agents-cloud/src/orchestrator.py
git commit -m "feat: expand 5 agent wrappers to pass disease_state and all intake fields"
```

---

### Task 5: Enhanced Logging + Final Verification

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py:377-382`

- [ ] **Step 1: Add disease_state to initialize_pipeline log line**

In `initialize_pipeline()` at line 377, replace the logger.info call:

```python
    logger.info(
        f"Pipeline initialized: project={flat.get('project_name', 'unknown')}, "
        f"area={flat.get('therapeutic_area', 'unknown')}, "
        f"disease={flat.get('disease_state', 'unknown')}, "
        f"audience={flat.get('target_audience', 'unknown')}, "
        f"fields_flattened={len(flat)}"
    )
```

- [ ] **Step 2: Run full test suites**

Run both test files to confirm no regressions:

```bash
cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/ -v
```

Expected: All tests PASS across test_orchestrator.py, test_needs_assessment.py, and all other test files.

- [ ] **Step 3: Commit**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add langgraph_workflows/dhg-agents-cloud/src/orchestrator.py
git commit -m "feat: add disease_state to pipeline initialization log"
```
