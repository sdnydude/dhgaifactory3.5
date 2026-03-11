# Human Review Loop Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire LangGraph `interrupt()` into all 4 CME pipeline recipes, build a text-annotation review UI in the Next.js frontend, and fix the observability stack — enabling end-to-end human-in-the-loop CME document review.

**Architecture:** Vertical slice approach. First prove `needs_package` end-to-end (agent interrupt → frontend annotation review → agent revision with comments → re-interrupt). Then replicate to 3 remaining recipes. Observability and production readiness last.

**Tech Stack:** LangGraph (interrupt/Command), Next.js 16, React 19, assistant-ui, @langchain/langgraph-sdk, CopilotKit, shadcn/ui, Tailwind 4, Prometheus, Grafana, Loki, Tempo.

**Spec:** `docs/superpowers/specs/2026-03-10-p1-human-review-loop-design.md`

---

## File Map

### Files to Modify

| File | What Changes |
|------|-------------|
| `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py` | Add `interrupt()`, `process_review_feedback` node, new state fields, update all 4 graph builders |
| `langgraph_workflows/dhg-agents-cloud/tests/test_orchestrator.py` | Rewrite gate/routing tests for interrupt pattern |
| `langgraph_workflows/dhg-agents-cloud/tests/conftest.py` | Add `review_comments`, `review_round` to `sample_pipeline_state` |
| `frontend/src/lib/inboxApi.ts` | Add `ReviewComment` type, update `resumeThread` to send structured comments, expand `PendingReview` with document/metrics fields |
| `frontend/src/components/agent-inbox/inbox-item.tsx` | Replace textarea with ReviewPanel integration |
| `frontend/src/components/agent-inbox/inbox-list.tsx` | Add expanded review state management |
| `frontend/src/app/layout.tsx` | No change (already correct) |
| `observability/prometheus/alerts.yml` | Replace phantom metrics with real container/host rules |
| `docker-compose.override.yml` | Add `dhg-frontend` service |

### Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/components/review/types.ts` | Shared types: ReviewComment, ReviewPayload, DocumentSection |
| `frontend/src/components/review/review-panel.tsx` | Main review container: document + sidebar + metrics + decision |
| `frontend/src/components/review/document-viewer.tsx` | Renders markdown, wraps in Selection API listener |
| `frontend/src/components/review/use-annotations.ts` | Custom hook: text selection → comments, highlight management |
| `frontend/src/components/review/comments-sidebar.tsx` | Ordered comment list with click-to-scroll |
| `frontend/src/components/review/metrics-bar.tsx` | Quality metrics badges |
| `frontend/src/components/review/decision-bar.tsx` | Approve/revise/reject with comment packaging |
| `frontend/src/app/studio/page.tsx` | CopilotKit studio route with agent selector |
| `observability/grafana/provisioning/dashboards/json/container-health.json` | cAdvisor dashboard |
| `observability/grafana/provisioning/dashboards/json/registry-api.json` | Registry API metrics dashboard |
| `observability/grafana/provisioning/dashboards/json/postgresql.json` | Postgres exporter dashboard |
| `observability/grafana/provisioning/dashboards/json/host-resources.json` | Node exporter dashboard |

---

## Chunk 1: Housekeeping + Agent Interrupt (Phase 0-1)

### Task 1: Commit Existing Work and Create Feature Branch

**Files:** Git operations only

- [ ] **Step 1: Check current git status**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git status
```

- [ ] **Step 2: Stage and commit all uncommitted migration work**

```bash
git add -A
git commit -m "feat(migration): complete Antigravity-to-Claude Code migration (10/10 criteria)

- Frontend: Agent Inbox, CopilotKit runtime, assistant-ui chat
- Observability: OTLP tracing via Tempo, Alertmanager, Promtail
- Testing: 68 unit tests for needs_assessment + orchestrator
- Docs: consolidated to 15 active docs, 7 archived
- Cleanup: removed .agent/, archived planning files"
```

- [ ] **Step 3: Create feature branch**

```bash
git checkout -b feat/human-review-loop
```

- [ ] **Step 4: Verify branch**

```bash
git branch --show-current
```

Expected: `feat/human-review-loop`

---

### Task 2: Verify Checkpointer for interrupt() Support

**Files:**
- Check: `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py:31-37` (PostgresSaver import)
- Check: `langgraph_workflows/dhg-agents-cloud/docker-compose.yml` (env vars)

`interrupt()` requires a checkpointer. LangGraph Server provides one automatically when deployed, but we need to verify local dev works.

- [ ] **Step 1: Check if LangGraph server is running with checkpointer**

```bash
curl -s http://localhost:2026/ok && echo "LangGraph server healthy"
```

- [ ] **Step 2: Test interrupt with a minimal graph via the LangGraph SDK**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
python3 -c "
import asyncio
from langchain_core.runnables import RunnableConfig
from langgraph_sdk import get_client

async def test():
    client = get_client(url='http://localhost:2026')
    # List available assistants to verify connection
    assistants = await client.assistants.search()
    print(f'Connected. {len(assistants)} graphs available.')
    for a in assistants:
        print(f'  - {a[\"graph_id\"]}')

asyncio.run(test())
"
```

Expected: Lists 15 graphs. LangGraph Server handles checkpointing internally — no additional configuration needed for `interrupt()`.

- [ ] **Step 3: Verify LangGraph version supports interrupt()**

```bash
cd langgraph_workflows/dhg-agents-cloud
grep langgraph requirements.txt
```

Expected: `langgraph>=0.2.0`. `interrupt()` requires langgraph >= 0.2.53. If version is too old, update to `langgraph>=0.2.53`.

- [ ] **Step 4: Commit if requirements.txt was updated**

```bash
git add langgraph_workflows/dhg-agents-cloud/requirements.txt
git commit -m "chore: bump langgraph minimum version for interrupt() support"
```

---

### Task 3: Run Existing Tests as Baseline

**Files:**
- Test: `langgraph_workflows/dhg-agents-cloud/tests/test_orchestrator.py`
- Test: `langgraph_workflows/dhg-agents-cloud/tests/test_needs_assessment.py`

- [ ] **Step 1: Run all existing tests**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/langgraph_workflows/dhg-agents-cloud
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: 68 tests pass (38 orchestrator + 30 needs_assessment). Record exact count as baseline.

---

### Task 4: Add Review State Fields to CMEPipelineState

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py:100-144`
- Modify: `langgraph_workflows/dhg-agents-cloud/tests/conftest.py:131-176`

- [ ] **Step 1: Write failing test for new state fields**

Add to `tests/test_orchestrator.py` after `TestCreateInitialState`:

```python
class TestReviewStateFields:
    """Tests for review-related state fields."""

    def test_initial_state_has_review_comments(self):
        state = orch.create_initial_state("p1", "P1", {})
        assert state["review_comments"] == []

    def test_initial_state_has_review_round(self):
        state = orch.create_initial_state("p1", "P1", {})
        assert state["review_round"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/langgraph_workflows/dhg-agents-cloud
python -m pytest tests/test_orchestrator.py::TestReviewStateFields -v
```

Expected: FAIL with `KeyError: 'review_comments'`

- [ ] **Step 3: Add fields to CMEPipelineState**

In `orchestrator.py`, add after line 133 (`human_reviewer: Optional[str]`):

```python
    # === REVIEW LOOP ===
    review_comments: List[Dict[str, Any]]  # [{selectedText, comment, startOffset, endOffset, document_id, timestamp}]
    review_round: int  # Tracks revision cycle (max 3)
```

- [ ] **Step 4: Update create_initial_state**

In `orchestrator.py`, in `create_initial_state()` function, add after line 1338 (`human_reviewer=None,`):

```python
        review_comments=[],
        review_round=0,
```

- [ ] **Step 5: Update conftest.py sample_pipeline_state fixture**

In `tests/conftest.py`, add after line 175 (`"checkpoint_agent": "init",`):

```python
        "review_comments": [],
        "review_round": 0,
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
python -m pytest tests/test_orchestrator.py::TestReviewStateFields -v
```

Expected: 2 PASSED

- [ ] **Step 7: Run full test suite to verify no regressions**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -10
```

Expected: All tests pass (baseline + 2 new)

- [ ] **Step 8: Commit**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add langgraph_workflows/dhg-agents-cloud/src/orchestrator.py langgraph_workflows/dhg-agents-cloud/tests/test_orchestrator.py langgraph_workflows/dhg-agents-cloud/tests/conftest.py
git commit -m "feat(orchestrator): add review_comments and review_round to CMEPipelineState"
```

---

### Task 5: Replace human_review_gate with interrupt() in needs_package

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py:675-682` (human_review_gate function)
- Modify: `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py:923-958` (create_needs_package_graph)

- [ ] **Step 1: Write failing test for interrupt behavior**

Add to `tests/test_orchestrator.py`, replacing the `test_human_review_gate_sets_awaiting_review` test in `TestGateNodes`:

```python
class TestHumanReviewInterrupt:
    """Tests for interrupt-based human review."""

    def test_human_review_node_calls_interrupt(self, sample_pipeline_state):
        """The human_review node should call interrupt() with a review payload."""
        # When needs_assessment_output has a complete_document, the interrupt
        # payload should include it along with quality metrics
        sample_pipeline_state["needs_assessment_output"] = {
            "complete_document": "Test document content",
            "word_count": 3200,
            "prose_density": 0.85,
            "quality_passed": True,
            "banned_patterns_found": [],
        }
        sample_pipeline_state["prose_quality_pass_1"] = {
            "overall_passed": True,
            "feedback": "",
        }

        # interrupt() raises GraphInterrupt when called — we verify the payload
        from langgraph.types import interrupt
        from unittest.mock import patch as mock_patch

        with mock_patch("orchestrator.interrupt") as mock_interrupt:
            mock_interrupt.side_effect = lambda payload: payload  # Return payload instead of interrupting
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                orch.human_review_node(sample_pipeline_state)
            )
            mock_interrupt.assert_called_once()
            call_payload = mock_interrupt.call_args[0][0]
            assert "document" in call_payload
            assert "metrics" in call_payload
            assert call_payload["recipe"] == "needs_package"

    def test_route_after_interrupt_approved(self):
        """When interrupt resumes with approved, route to complete/END."""
        resume_value = {"decision": "approved", "comments": []}
        assert orch.route_after_human_review_interrupt(resume_value) == "approved"

    def test_route_after_interrupt_revision(self):
        """When interrupt resumes with revision, route to revision agent."""
        resume_value = {
            "decision": "revision",
            "comments": [{"selectedText": "test", "comment": "fix this"}],
        }
        assert orch.route_after_human_review_interrupt(resume_value) == "revision"

    def test_route_after_interrupt_rejected(self):
        """When interrupt resumes with rejected, route to failed."""
        resume_value = {"decision": "rejected", "comments": []}
        assert orch.route_after_human_review_interrupt(resume_value) == "rejected"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_orchestrator.py::TestHumanReviewInterrupt -v
```

Expected: FAIL (functions don't exist yet)

- [ ] **Step 3: Add interrupt import and new human_review_node**

In `orchestrator.py`, add to imports (after line 28):

```python
from langgraph.types import interrupt, Command
```

Then replace the `human_review_gate` function (lines 675-682) with:

```python
@traceable(name="human_review_node", run_type="chain")
async def human_review_node(state: CMEPipelineState) -> dict:
    """Pause pipeline for human review via LangGraph interrupt().

    Assembles review payload from current state and calls interrupt().
    The graph pauses here until resumed with Command(resume={decision, comments}).
    """
    # Determine which documents to include based on what's available
    documents = {}
    metrics = {}

    if state.get("needs_assessment_output"):
        na = state["needs_assessment_output"]
        documents["needs_assessment"] = na.get("complete_document", "")
        metrics["word_count"] = na.get("word_count", 0)
        metrics["prose_density"] = na.get("prose_density", 0.0)
        metrics["quality_passed"] = na.get("quality_passed", False)
        metrics["banned_patterns_found"] = na.get("banned_patterns_found", [])

    if state.get("curriculum_output"):
        documents["curriculum_design"] = state["curriculum_output"].get("complete_document", "")

    if state.get("protocol_output"):
        documents["research_protocol"] = state["protocol_output"].get("complete_document", "")

    if state.get("marketing_output"):
        documents["marketing_plan"] = state["marketing_output"].get("complete_document", "")

    if state.get("grant_package_output"):
        documents["grant_package"] = state["grant_package_output"].get("complete_document_markdown", "")

    # Include prose quality and compliance results if available
    if state.get("prose_quality_pass_1"):
        metrics["prose_quality_pass_1"] = state["prose_quality_pass_1"]
    if state.get("prose_quality_pass_2"):
        metrics["prose_quality_pass_2"] = state["prose_quality_pass_2"]
    if state.get("compliance_result"):
        metrics["compliance_result"] = state["compliance_result"]

    # Determine recipe name from available outputs
    recipe = "needs_package"
    if state.get("grant_package_output"):
        recipe = "grant_package"
    elif state.get("curriculum_output"):
        recipe = "curriculum_package"

    review_payload = {
        "document": documents,
        "metrics": metrics,
        "recipe": recipe,
        "project_id": state.get("project_id", ""),
        "project_name": state.get("project_name", ""),
        "review_round": state.get("review_round", 0),
        "current_step": state.get("current_step", ""),
    }

    # This pauses the graph. Resumes with Command(resume={decision, comments})
    resume_value = interrupt(review_payload)

    # Process the resume value
    decision = resume_value.get("decision", "rejected")
    comments = resume_value.get("comments", [])

    return {
        "human_review_status": decision,
        "human_review_notes": resume_value.get("feedback", ""),
        "review_comments": state.get("review_comments", []) + comments,
        "status": PipelineStatus.AWAITING_REVIEW.value,
        "current_step": f"human_review_{decision}",
        "updated_at": datetime.now().isoformat(),
    }
```

- [ ] **Step 4: Add new routing function for interrupt-based review**

In `orchestrator.py`, add after `route_after_human_review` (after line 915):

```python
def route_after_human_review_interrupt(state: CMEPipelineState) -> Literal["approved", "revision", "rejected"]:
    """Route after human review interrupt based on human_review_status set by human_review_node."""
    status = state.get("human_review_status", "rejected")
    if status == "approved":
        return "approved"
    elif status == "revision":
        return "revision"
    else:
        return "rejected"
```

- [ ] **Step 5: Update create_needs_package_graph to use interrupt**

Replace `create_needs_package_graph` function (lines 923-958) with:

```python
def create_needs_package_graph():
    """Create the Needs Assessment Package recipe with parallel execution and interrupt-based review."""

    workflow = StateGraph(CMEPipelineState)

    # Add nodes
    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality", run_prose_quality_pass_1)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("complete", mark_complete)
    workflow.add_node("failed", mark_failed)

    # Flow with parallel early research
    workflow.set_entry_point("early_research")
    workflow.add_edge("early_research", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality")

    # Prose quality routing
    workflow.add_conditional_edges(
        "prose_quality",
        route_after_prose_quality_1,
        {
            "continue": "human_review",
            "retry_needs": "needs_assessment",
            "human_intervention": "failed"
        }
    )

    # Human review routing (interrupt-based)
    workflow.add_conditional_edges(
        "human_review",
        route_after_human_review_interrupt,
        {
            "approved": "complete",
            "revision": "needs_assessment",
            "rejected": "failed"
        }
    )

    workflow.add_edge("complete", END)
    workflow.add_edge("failed", END)

    return workflow.compile()
```

- [ ] **Step 6: Run the interrupt tests**

```bash
python -m pytest tests/test_orchestrator.py::TestHumanReviewInterrupt -v
```

Expected: 4 PASSED

- [ ] **Step 7: Update existing TestGateNodes tests**

The old `test_human_review_gate_sets_awaiting_review` test references the deleted function. Update `TestGateNodes`:

```python
class TestGateNodes:
    """Tests for human_review_node, mark_complete, mark_failed nodes."""

    @pytest.mark.asyncio
    async def test_mark_complete_sets_status(self, sample_pipeline_state):
        result = await orch.mark_complete(sample_pipeline_state)
        assert result["status"] == "complete"
        assert result["current_step"] == "complete"

    @pytest.mark.asyncio
    async def test_mark_failed_sets_status(self, sample_pipeline_state):
        result = await orch.mark_failed(sample_pipeline_state)
        assert result["status"] == "failed"
        assert result["current_step"] == "failed_human_intervention_required"

    @pytest.mark.asyncio
    async def test_gate_nodes_include_timestamp(self, sample_pipeline_state):
        result = await orch.mark_complete(sample_pipeline_state)
        datetime.fromisoformat(result["updated_at"])

        result = await orch.mark_failed(sample_pipeline_state)
        datetime.fromisoformat(result["updated_at"])
```

- [ ] **Step 8: Update TestNeedsPackageGraph for new nodes**

```python
class TestNeedsPackageGraph:
    """Tests for create_needs_package_graph / needs_graph."""

    def test_compiles_without_error(self):
        graph = orch.create_needs_package_graph()
        assert graph is not None

    def test_module_level_needs_graph_exists(self):
        assert orch.needs_graph is not None

    def test_has_expected_nodes(self):
        nodes = set(orch.needs_graph.get_graph().nodes.keys())
        expected = {
            "early_research", "gap_analysis", "learning_objectives",
            "needs_assessment", "prose_quality", "human_review",
            "complete", "failed",
            "__start__", "__end__",
        }
        assert expected.issubset(nodes)

    def test_entry_point_is_early_research(self):
        graph_repr = orch.needs_graph.get_graph()
        start_edges = [e for e in graph_repr.edges if e[0] == "__start__"]
        assert any(e[1] == "early_research" for e in start_edges)

    def test_human_review_has_three_way_routing(self):
        """Human review should route to complete, needs_assessment (revision), or failed."""
        graph_repr = orch.needs_graph.get_graph()
        hr_targets = sorted([e[1] for e in graph_repr.edges if e[0] == "human_review"])
        assert "complete" in hr_targets
        assert "needs_assessment" in hr_targets
        assert "failed" in hr_targets
```

- [ ] **Step 9: Update TestRouteAfterHumanReview to test new function**

```python
class TestRouteAfterHumanReview:
    """Tests for route_after_human_review_interrupt routing function."""

    def test_approved(self, sample_pipeline_state):
        sample_pipeline_state["human_review_status"] = "approved"
        assert orch.route_after_human_review_interrupt(sample_pipeline_state) == "approved"

    def test_revision(self, sample_pipeline_state):
        sample_pipeline_state["human_review_status"] = "revision"
        assert orch.route_after_human_review_interrupt(sample_pipeline_state) == "revision"

    def test_rejected_default(self, sample_pipeline_state):
        sample_pipeline_state["human_review_status"] = "pending"
        assert orch.route_after_human_review_interrupt(sample_pipeline_state) == "rejected"

    def test_rejected_when_none(self, sample_pipeline_state):
        sample_pipeline_state["human_review_status"] = None
        assert orch.route_after_human_review_interrupt(sample_pipeline_state) == "rejected"
```

- [ ] **Step 10: Run full test suite**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: All tests pass

- [ ] **Step 11: Commit**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add langgraph_workflows/dhg-agents-cloud/src/orchestrator.py langgraph_workflows/dhg-agents-cloud/tests/test_orchestrator.py
git commit -m "feat(orchestrator): replace human_review_gate with interrupt() in needs_package

- human_review_node assembles review payload and calls interrupt()
- Route function reads decision from resume value (approved/revision/rejected)
- needs_package now has 3-way routing: complete, retry needs, or fail
- Updated all affected tests"
```

---

### Task 6: Add process_review_feedback Node

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py`
- Modify: `langgraph_workflows/dhg-agents-cloud/tests/test_orchestrator.py`

- [ ] **Step 1: Write failing test**

```python
class TestProcessReviewFeedback:
    """Tests for process_review_feedback node."""

    @pytest.mark.asyncio
    async def test_formats_comments_into_message(self, sample_pipeline_state):
        sample_pipeline_state["review_comments"] = [
            {"selectedText": "The prevalence", "comment": "Add CDC data", "startOffset": 0, "endOffset": 14},
            {"selectedText": "guidelines recommend", "comment": "Wrong area", "startOffset": 100, "endOffset": 120},
        ]
        result = await orch.process_review_feedback(sample_pipeline_state)
        # Should append a formatted message to messages
        assert len(result["messages"]) == 1
        msg_content = result["messages"][0].content
        assert "The prevalence" in msg_content
        assert "Add CDC data" in msg_content
        assert "guidelines recommend" in msg_content

    @pytest.mark.asyncio
    async def test_increments_review_round(self, sample_pipeline_state):
        sample_pipeline_state["review_comments"] = [
            {"selectedText": "text", "comment": "fix", "startOffset": 0, "endOffset": 4},
        ]
        sample_pipeline_state["review_round"] = 1
        result = await orch.process_review_feedback(sample_pipeline_state)
        assert result["review_round"] == 2

    @pytest.mark.asyncio
    async def test_empty_comments_still_works(self, sample_pipeline_state):
        sample_pipeline_state["review_comments"] = []
        result = await orch.process_review_feedback(sample_pipeline_state)
        assert result["review_round"] == 1
        assert "General revision requested" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_max_revisions_routes_to_failed(self, sample_pipeline_state):
        sample_pipeline_state["review_round"] = 3
        sample_pipeline_state["review_comments"] = []
        result = await orch.process_review_feedback(sample_pipeline_state)
        assert result["status"] == "failed"
        assert "maximum revision" in result["current_step"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_orchestrator.py::TestProcessReviewFeedback -v
```

Expected: FAIL

- [ ] **Step 3: Implement process_review_feedback**

In `orchestrator.py`, add after `human_review_node`:

```python
MAX_REVIEW_ROUNDS = 3


@traceable(name="process_review_feedback", run_type="chain")
async def process_review_feedback(state: CMEPipelineState) -> dict:
    """Format reviewer comments into a structured message for the revision agent.

    Reads review_comments from state and creates a HumanMessage that the
    revision agent will see as context for targeted edits.
    """
    from langchain_core.messages import HumanMessage

    review_round = state.get("review_round", 0) + 1

    # Enforce max revision cycles
    if review_round > MAX_REVIEW_ROUNDS:
        return {
            "status": PipelineStatus.FAILED.value,
            "current_step": "maximum_revision_cycles_exceeded",
            "updated_at": datetime.now().isoformat(),
        }

    comments = state.get("review_comments", [])

    if comments:
        lines = ["## Reviewer Comments (address each one):\n"]
        for i, c in enumerate(comments, 1):
            selected = c.get("selectedText", "")
            comment = c.get("comment", "")
            doc_id = c.get("document_id", "")
            doc_prefix = f"[{doc_id}] " if doc_id else ""
            lines.append(f'{i}. {doc_prefix}At "{selected}": "{comment}"')
        feedback_text = "\n".join(lines)
    else:
        feedback_text = "## General revision requested\n\nThe reviewer requested revisions but did not provide specific inline comments. Please review the document for quality, accuracy, and completeness."

    return {
        "messages": [HumanMessage(content=feedback_text)],
        "review_round": review_round,
        "current_step": f"processing_review_feedback_round_{review_round}",
        "updated_at": datetime.now().isoformat(),
    }
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_orchestrator.py::TestProcessReviewFeedback -v
```

Expected: 4 PASSED

- [ ] **Step 5: Wire process_review_feedback into needs_package graph**

Update `create_needs_package_graph` to add the feedback node between interrupt and revision:

```python
def create_needs_package_graph():
    """Create the Needs Assessment Package recipe with parallel execution and interrupt-based review."""

    workflow = StateGraph(CMEPipelineState)

    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality", run_prose_quality_pass_1)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("process_feedback", process_review_feedback)
    workflow.add_node("complete", mark_complete)
    workflow.add_node("failed", mark_failed)

    workflow.set_entry_point("early_research")
    workflow.add_edge("early_research", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality")

    workflow.add_conditional_edges(
        "prose_quality",
        route_after_prose_quality_1,
        {
            "continue": "human_review",
            "retry_needs": "needs_assessment",
            "human_intervention": "failed"
        }
    )

    workflow.add_conditional_edges(
        "human_review",
        route_after_human_review_interrupt,
        {
            "approved": "complete",
            "revision": "process_feedback",
            "rejected": "failed"
        }
    )

    # After processing feedback, re-run needs assessment
    workflow.add_edge("process_feedback", "needs_assessment")

    workflow.add_edge("complete", END)
    workflow.add_edge("failed", END)

    return workflow.compile()
```

- [ ] **Step 6: Update TestNeedsPackageGraph test**

Update `test_has_expected_nodes` to include `process_feedback`:

```python
    def test_has_expected_nodes(self):
        nodes = set(orch.needs_graph.get_graph().nodes.keys())
        expected = {
            "early_research", "gap_analysis", "learning_objectives",
            "needs_assessment", "prose_quality", "human_review",
            "process_feedback", "complete", "failed",
            "__start__", "__end__",
        }
        assert expected.issubset(nodes)
```

- [ ] **Step 7: Run full test suite**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add langgraph_workflows/dhg-agents-cloud/src/orchestrator.py langgraph_workflows/dhg-agents-cloud/tests/test_orchestrator.py
git commit -m "feat(orchestrator): add process_review_feedback node with revision loop

- Formats positioned reviewer comments into structured prompt
- Increments review_round, enforces MAX_REVIEW_ROUNDS=3
- Wired into needs_package: human_review → process_feedback → needs_assessment"
```

---

## Chunk 2: Frontend Review UI (Phase 2)

### Task 7: Create Review Types

**Files:**
- Create: `frontend/src/components/review/types.ts`

- [ ] **Step 1: Create the types file**

```typescript
// frontend/src/components/review/types.ts

export interface ReviewComment {
  id: string;
  selectedText: string;
  startOffset: number;
  endOffset: number;
  comment: string;
  timestamp: string;
  documentId?: string; // For multi-document review (curriculum_package)
}

export interface ReviewMetrics {
  word_count?: number;
  prose_density?: number;
  quality_passed?: boolean;
  banned_patterns_found?: string[];
  prose_quality_pass_1?: Record<string, unknown>;
  prose_quality_pass_2?: Record<string, unknown>;
  compliance_result?: Record<string, unknown>;
}

export interface DocumentSection {
  id: string;
  label: string;
  content: string; // Markdown
}

export interface ReviewPayload {
  document: Record<string, string>; // {needs_assessment: "markdown...", ...}
  metrics: ReviewMetrics;
  recipe: string;
  project_id: string;
  project_name: string;
  review_round: number;
  current_step: string;
}

export interface ResumeValue {
  decision: "approved" | "revision" | "rejected";
  comments: ReviewComment[];
  feedback?: string;
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add frontend/src/components/review/types.ts
git commit -m "feat(frontend): add review component type definitions"
```

---

### Task 8: Build useAnnotations Hook

**Files:**
- Create: `frontend/src/components/review/use-annotations.ts`

- [ ] **Step 1: Create the hook**

```typescript
// frontend/src/components/review/use-annotations.ts
"use client";

import { useState, useCallback, useRef } from "react";
import type { ReviewComment } from "./types";

export function useAnnotations(documentId?: string) {
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [pendingSelection, setPendingSelection] = useState<{
    text: string;
    startOffset: number;
    endOffset: number;
    rect: DOMRect;
  } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseUp = useCallback(() => {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !containerRef.current) {
      setPendingSelection(null);
      return;
    }

    const range = selection.getRangeAt(0);

    // Verify selection is within our container
    if (!containerRef.current.contains(range.commonAncestorContainer)) {
      setPendingSelection(null);
      return;
    }

    const text = selection.toString().trim();
    if (!text) {
      setPendingSelection(null);
      return;
    }

    // Calculate offsets relative to container text content
    const preRange = document.createRange();
    preRange.selectNodeContents(containerRef.current);
    preRange.setEnd(range.startContainer, range.startOffset);
    const startOffset = preRange.toString().length;

    const rect = range.getBoundingClientRect();

    setPendingSelection({
      text,
      startOffset,
      endOffset: startOffset + text.length,
      rect,
    });
  }, []);

  const addComment = useCallback(
    (commentText: string) => {
      if (!pendingSelection) return;

      const newComment: ReviewComment = {
        id: crypto.randomUUID(),
        selectedText: pendingSelection.text,
        startOffset: pendingSelection.startOffset,
        endOffset: pendingSelection.endOffset,
        comment: commentText,
        timestamp: new Date().toISOString(),
        documentId,
      };

      setComments((prev) =>
        [...prev, newComment].sort((a, b) => a.startOffset - b.startOffset),
      );
      setPendingSelection(null);
      window.getSelection()?.removeAllRanges();
    },
    [pendingSelection, documentId],
  );

  const removeComment = useCallback((id: string) => {
    setComments((prev) => prev.filter((c) => c.id !== id));
  }, []);

  const updateComment = useCallback((id: string, newText: string) => {
    setComments((prev) =>
      prev.map((c) => (c.id === id ? { ...c, comment: newText } : c)),
    );
  }, []);

  const clearPendingSelection = useCallback(() => {
    setPendingSelection(null);
    window.getSelection()?.removeAllRanges();
  }, []);

  return {
    comments,
    pendingSelection,
    containerRef,
    handleMouseUp,
    addComment,
    removeComment,
    updateComment,
    clearPendingSelection,
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/review/use-annotations.ts
git commit -m "feat(frontend): add useAnnotations hook for text selection commenting"
```

---

### Task 9: Build MetricsBar Component

**Files:**
- Create: `frontend/src/components/review/metrics-bar.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/review/metrics-bar.tsx
"use client";

import { Badge } from "@/components/ui/badge";
import type { ReviewMetrics } from "./types";

interface MetricsBarProps {
  metrics: ReviewMetrics;
  reviewRound: number;
}

export function MetricsBar({ metrics, reviewRound }: MetricsBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 px-4 py-2 border-b border-border bg-muted/50">
      {metrics.word_count != null && (
        <Badge variant="outline" className="text-xs">
          {metrics.word_count.toLocaleString()} words
        </Badge>
      )}
      {metrics.prose_density != null && (
        <Badge variant="outline" className="text-xs">
          {(metrics.prose_density * 100).toFixed(0)}% prose density
        </Badge>
      )}
      {metrics.quality_passed != null && (
        <Badge
          variant={metrics.quality_passed ? "default" : "destructive"}
          className="text-xs"
        >
          QA {metrics.quality_passed ? "Passed" : "Failed"}
        </Badge>
      )}
      {metrics.banned_patterns_found && metrics.banned_patterns_found.length > 0 && (
        <Badge variant="destructive" className="text-xs">
          {metrics.banned_patterns_found.length} banned patterns
        </Badge>
      )}
      {reviewRound > 0 && (
        <Badge variant="secondary" className="text-xs">
          Revision {reviewRound}/3
        </Badge>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/review/metrics-bar.tsx
git commit -m "feat(frontend): add MetricsBar component for review quality badges"
```

---

### Task 10: Build DocumentViewer Component

**Files:**
- Create: `frontend/src/components/review/document-viewer.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/review/document-viewer.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { MarkdownText } from "@/components/assistant-ui/markdown-text";
import { Button } from "@/components/ui/button";
import { MessageCirclePlus } from "lucide-react";
import type { ReviewComment } from "./types";

interface DocumentViewerProps {
  content: string;
  comments: ReviewComment[];
  pendingSelection: {
    text: string;
    startOffset: number;
    endOffset: number;
    rect: DOMRect;
  } | null;
  containerRef: React.RefObject<HTMLDivElement | null>;
  onMouseUp: () => void;
  onAddComment: (comment: string) => void;
  onClearSelection: () => void;
}

export function DocumentViewer({
  content,
  comments,
  pendingSelection,
  containerRef,
  onMouseUp,
  onAddComment,
  onClearSelection,
}: DocumentViewerProps) {
  const [commentInput, setCommentInput] = useState("");
  const [showCommentPopover, setShowCommentPopover] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (pendingSelection) {
      setShowCommentPopover(true);
      setCommentInput("");
    } else {
      setShowCommentPopover(false);
    }
  }, [pendingSelection]);

  const handleSubmitComment = () => {
    if (!commentInput.trim()) return;
    onAddComment(commentInput.trim());
    setCommentInput("");
    setShowCommentPopover(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmitComment();
    }
    if (e.key === "Escape") {
      onClearSelection();
      setShowCommentPopover(false);
    }
  };

  return (
    <div className="relative flex-1 overflow-auto">
      <div
        ref={containerRef}
        onMouseUp={onMouseUp}
        className="prose prose-sm dark:prose-invert max-w-none p-6 select-text cursor-text"
      >
        <MarkdownText content={content} />
      </div>

      {/* Floating "Add Comment" popover */}
      {showCommentPopover && pendingSelection && (
        <div
          ref={popoverRef}
          className="fixed z-50 bg-surface border border-border rounded-lg shadow-lg p-3 w-72"
          style={{
            top: pendingSelection.rect.bottom + 8,
            left: Math.min(
              pendingSelection.rect.left,
              window.innerWidth - 300,
            ),
          }}
        >
          <p className="text-xs text-muted-foreground mb-2 truncate">
            &quot;{pendingSelection.text.slice(0, 60)}
            {pendingSelection.text.length > 60 ? "..." : ""}&quot;
          </p>
          <textarea
            value={commentInput}
            onChange={(e) => setCommentInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Add your comment..."
            className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-dhg-purple resize-none"
            rows={2}
            autoFocus
          />
          <div className="flex gap-2 mt-2">
            <Button size="sm" onClick={handleSubmitComment} disabled={!commentInput.trim()}>
              <MessageCirclePlus className="h-3 w-3 mr-1" />
              Comment
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                onClearSelection();
                setShowCommentPopover(false);
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/review/document-viewer.tsx
git commit -m "feat(frontend): add DocumentViewer with floating comment popover"
```

---

### Task 11: Build CommentsSidebar Component

**Files:**
- Create: `frontend/src/components/review/comments-sidebar.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/review/comments-sidebar.tsx
"use client";

import { Button } from "@/components/ui/button";
import { Trash2, MessageSquare } from "lucide-react";
import type { ReviewComment } from "./types";

interface CommentsSidebarProps {
  comments: ReviewComment[];
  onRemove: (id: string) => void;
  onUpdate: (id: string, newText: string) => void;
  onScrollTo: (comment: ReviewComment) => void;
}

export function CommentsSidebar({
  comments,
  onRemove,
  onUpdate,
  onScrollTo,
}: CommentsSidebarProps) {
  if (comments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <MessageSquare className="h-8 w-8 mb-2 opacity-40" />
        <p className="text-xs">No comments yet</p>
        <p className="text-xs mt-1">Select text in the document to add comments</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 p-3">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
        Comments ({comments.length})
      </h3>
      {comments.map((comment, index) => (
        <div
          key={comment.id}
          className="border border-border rounded-md p-2.5 text-sm hover:border-dhg-purple/50 transition-colors cursor-pointer"
          onClick={() => onScrollTo(comment)}
        >
          <div className="flex items-start justify-between gap-2">
            <span className="text-xs font-medium text-dhg-purple">
              #{index + 1}
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-5 w-5 p-0 text-muted-foreground hover:text-red-500"
              onClick={(e) => {
                e.stopPropagation();
                onRemove(comment.id);
              }}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-1 italic truncate">
            &quot;{comment.selectedText.slice(0, 80)}
            {comment.selectedText.length > 80 ? "..." : ""}&quot;
          </p>
          <textarea
            value={comment.comment}
            onChange={(e) => onUpdate(comment.id, e.target.value)}
            onClick={(e) => e.stopPropagation()}
            className="w-full mt-1.5 rounded border border-border bg-background px-2 py-1 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-dhg-purple resize-none"
            rows={2}
          />
          {comment.documentId && (
            <span className="text-[10px] text-muted-foreground mt-1 block">
              {comment.documentId}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/review/comments-sidebar.tsx
git commit -m "feat(frontend): add CommentsSidebar for ordered comment list"
```

---

### Task 12: Build DecisionBar Component

**Files:**
- Create: `frontend/src/components/review/decision-bar.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/review/decision-bar.tsx
"use client";

import { Button } from "@/components/ui/button";
import { CheckCircle, RotateCcw, XCircle } from "lucide-react";
import type { ReviewComment, ResumeValue } from "./types";

interface DecisionBarProps {
  comments: ReviewComment[];
  onSubmit: (value: ResumeValue) => void;
  isLoading: boolean;
}

export function DecisionBar({ comments, onSubmit, isLoading }: DecisionBarProps) {
  const handleDecision = (decision: ResumeValue["decision"]) => {
    onSubmit({ decision, comments });
  };

  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3 border-t border-border bg-muted/30">
      <span className="text-xs text-muted-foreground">
        {comments.length} comment{comments.length !== 1 ? "s" : ""} attached
      </span>
      <div className="flex gap-2">
        <Button
          size="sm"
          onClick={() => handleDecision("approved")}
          disabled={isLoading}
          className="bg-green-600 hover:bg-green-700 text-white"
        >
          <CheckCircle className="h-4 w-4 mr-1" />
          Approve
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => handleDecision("revision")}
          disabled={isLoading}
        >
          <RotateCcw className="h-4 w-4 mr-1" />
          Request Revision
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => handleDecision("rejected")}
          disabled={isLoading}
          className="border-red-300 text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950"
        >
          <XCircle className="h-4 w-4 mr-1" />
          Reject
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/review/decision-bar.tsx
git commit -m "feat(frontend): add DecisionBar with comment packaging"
```

---

### Task 13: Build ReviewPanel Container

**Files:**
- Create: `frontend/src/components/review/review-panel.tsx`

- [ ] **Step 1: Create the main review panel**

```tsx
// frontend/src/components/review/review-panel.tsx
"use client";

import { useState } from "react";
import { DocumentViewer } from "./document-viewer";
import { CommentsSidebar } from "./comments-sidebar";
import { MetricsBar } from "./metrics-bar";
import { DecisionBar } from "./decision-bar";
import { useAnnotations } from "./use-annotations";
import type { ReviewPayload, ResumeValue, DocumentSection } from "./types";

interface ReviewPanelProps {
  payload: ReviewPayload;
  onSubmit: (value: ResumeValue) => void;
  isLoading: boolean;
}

export function ReviewPanel({ payload, onSubmit, isLoading }: ReviewPanelProps) {
  const documents = buildDocumentSections(payload.document);
  const [activeDocIndex, setActiveDocIndex] = useState(0);
  const activeDoc = documents[activeDocIndex];

  const {
    comments,
    pendingSelection,
    containerRef,
    handleMouseUp,
    addComment,
    removeComment,
    updateComment,
    clearPendingSelection,
  } = useAnnotations(activeDoc?.id);

  const handleScrollToComment = (_comment: typeof comments[number]) => {
    // Scroll the container to approximate position based on offset
    if (containerRef.current) {
      const textLength = containerRef.current.textContent?.length ?? 1;
      const scrollRatio = _comment.startOffset / textLength;
      const scrollTarget = containerRef.current.scrollHeight * scrollRatio;
      containerRef.current.scrollTo({ top: scrollTarget - 100, behavior: "smooth" });
    }
  };

  return (
    <div className="flex flex-col border border-border rounded-lg overflow-hidden bg-background h-[70vh]">
      {/* Metrics bar */}
      <MetricsBar metrics={payload.metrics} reviewRound={payload.review_round} />

      {/* Document tabs (multi-document) */}
      {documents.length > 1 && (
        <div className="flex border-b border-border">
          {documents.map((doc, i) => (
            <button
              key={doc.id}
              onClick={() => setActiveDocIndex(i)}
              className={`px-4 py-2 text-xs font-medium transition-colors ${
                i === activeDocIndex
                  ? "border-b-2 border-dhg-purple text-dhg-purple"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {doc.label}
            </button>
          ))}
        </div>
      )}

      {/* Main content: document + sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {/* Document viewer */}
        <DocumentViewer
          content={activeDoc?.content ?? ""}
          comments={comments.filter((c) => !c.documentId || c.documentId === activeDoc?.id)}
          pendingSelection={pendingSelection}
          containerRef={containerRef}
          onMouseUp={handleMouseUp}
          onAddComment={addComment}
          onClearSelection={clearPendingSelection}
        />

        {/* Comments sidebar (desktop only) */}
        <div className="hidden md:block w-72 border-l border-border overflow-auto">
          <CommentsSidebar
            comments={comments}
            onRemove={removeComment}
            onUpdate={updateComment}
            onScrollTo={handleScrollToComment}
          />
        </div>
      </div>

      {/* Mobile comments (below document) */}
      <div className="md:hidden border-t border-border max-h-48 overflow-auto">
        <CommentsSidebar
          comments={comments}
          onRemove={removeComment}
          onUpdate={updateComment}
          onScrollTo={handleScrollToComment}
        />
      </div>

      {/* Decision bar */}
      <DecisionBar comments={comments} onSubmit={onSubmit} isLoading={isLoading} />
    </div>
  );
}

function buildDocumentSections(
  docs: Record<string, string>,
): DocumentSection[] {
  const LABELS: Record<string, string> = {
    needs_assessment: "Needs Assessment",
    curriculum_design: "Curriculum Design",
    research_protocol: "Research Protocol",
    marketing_plan: "Marketing Plan",
    grant_package: "Grant Package",
  };

  return Object.entries(docs)
    .filter(([, content]) => content && content.trim())
    .map(([id, content]) => ({
      id,
      label: LABELS[id] ?? id,
      content,
    }));
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/review/review-panel.tsx
git commit -m "feat(frontend): add ReviewPanel container with document tabs and annotation"
```

---

### Task 14: Update InboxItem and InboxApi to Use ReviewPanel

**Files:**
- Modify: `frontend/src/lib/inboxApi.ts`
- Modify: `frontend/src/components/agent-inbox/inbox-item.tsx`

- [ ] **Step 1: Update inboxApi.ts types and resumeThread**

Replace entire file content:

```typescript
// frontend/src/lib/inboxApi.ts
import { Client } from "@langchain/langgraph-sdk";
import type { ReviewPayload, ResumeValue } from "@/components/review/types";

const createClient = () => {
  return new Client({
    apiUrl:
      process.env.NEXT_PUBLIC_LANGGRAPH_API_URL || "http://localhost:2026",
  });
};

export interface PendingReview {
  threadId: string;
  graphId: string;
  createdAt: string;
  payload: ReviewPayload | null;
  currentStep: string;
  status: string;
}

export async function listPendingReviews(): Promise<PendingReview[]> {
  const client = createClient();
  const threads = await client.threads.search({
    status: "interrupted",
    limit: 50,
  });

  const reviews: PendingReview[] = [];

  for (const thread of threads) {
    const state = await client.threads.getState(thread.thread_id);
    const values = state.values as Record<string, unknown> | null;
    const tasks = state.tasks ?? [];

    // Extract the interrupt payload (the review_payload from human_review_node)
    let payload: ReviewPayload | null = null;
    for (const task of tasks) {
      if (task.interrupts) {
        for (const interrupt of task.interrupts) {
          // The interrupt value IS the review payload
          const val = interrupt.value as ReviewPayload;
          if (val && val.document) {
            payload = val;
          }
        }
      }
    }

    if (payload || tasks.some((t) => t.interrupts?.length)) {
      reviews.push({
        threadId: thread.thread_id,
        graphId: (thread.metadata?.graph_id as string) ?? "unknown",
        createdAt: thread.created_at,
        payload,
        currentStep: (values?.current_step as string) ?? "unknown",
        status: (values?.status as string) ?? "awaiting_review",
      });
    }
  }

  return reviews;
}

export async function resumeThread(
  threadId: string,
  graphId: string,
  resumeValue: ResumeValue,
) {
  const client = createClient();
  return client.runs.stream(threadId, graphId, {
    input: null,
    command: { resume: resumeValue },
    streamMode: "messages-tuple",
  });
}

export async function getThreadDetails(threadId: string) {
  const client = createClient();
  const state = await client.threads.getState(threadId);
  return state;
}
```

- [ ] **Step 2: Update inbox-item.tsx to integrate ReviewPanel**

Replace entire file content:

```tsx
// frontend/src/components/agent-inbox/inbox-item.tsx
"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronUp, Clock } from "lucide-react";
import { ReviewPanel } from "@/components/review/review-panel";
import type { PendingReview } from "@/lib/inboxApi";
import type { ResumeValue } from "@/components/review/types";

interface InboxItemProps {
  review: PendingReview;
  onAction: (threadId: string, graphId: string, resumeValue: ResumeValue) => void;
  isLoading: boolean;
}

const GRAPH_LABELS: Record<string, string> = {
  needs_package: "Needs Package",
  curriculum_package: "Curriculum Package",
  grant_package: "Grant Package",
  full_pipeline: "Full Pipeline",
  needs_assessment: "Needs Assessment",
  research: "Research",
  clinical_practice: "Clinical Practice",
  gap_analysis: "Gap Analysis",
  learning_objectives: "Learning Objectives",
  curriculum_design: "Curriculum Design",
  research_protocol: "Research Protocol",
  marketing_plan: "Marketing Plan",
  grant_writer: "Grant Writer",
  prose_quality: "Prose Quality",
  compliance_review: "Compliance Review",
};

export function InboxItem({ review, onAction, isLoading }: InboxItemProps) {
  const [expanded, setExpanded] = useState(false);

  const graphLabel = GRAPH_LABELS[review.graphId] ?? review.graphId;
  const timeAgo = formatTimeAgo(review.createdAt);

  const handleSubmit = (resumeValue: ResumeValue) => {
    onAction(review.threadId, review.graphId, resumeValue);
  };

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="border-dhg-purple text-dhg-purple">
              {graphLabel}
            </Badge>
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {timeAgo}
            </span>
          </div>
          <Badge variant="secondary">{review.currentStep}</Badge>
        </div>
        <CardTitle className="text-sm font-medium mt-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 hover:text-dhg-purple transition-colors"
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            Thread {review.threadId.slice(0, 8)}... — {expanded ? "Collapse" : "Open Review"}
          </button>
        </CardTitle>
      </CardHeader>
      {expanded && review.payload && (
        <CardContent>
          <ReviewPanel
            payload={review.payload}
            onSubmit={handleSubmit}
            isLoading={isLoading}
          />
        </CardContent>
      )}
      {expanded && !review.payload && (
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No review payload available. This interrupt may not contain document data.
          </p>
        </CardContent>
      )}
    </Card>
  );
}

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}
```

- [ ] **Step 3: Update inbox-list.tsx handleAction signature**

In `frontend/src/components/agent-inbox/inbox-list.tsx`, update the `handleAction` function:

```tsx
  const handleAction = async (
    threadId: string,
    graphId: string,
    resumeValue: ResumeValue,
  ) => {
    setActionLoading(threadId);
    try {
      await resumeThread(threadId, graphId, resumeValue);
      setReviews((prev) => prev.filter((r) => r.threadId !== threadId));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to process review action",
      );
    } finally {
      setActionLoading(null);
    }
  };
```

And add the import at top:

```tsx
import { listPendingReviews, resumeThread } from "@/lib/inboxApi";
import type { PendingReview } from "@/lib/inboxApi";
import type { ResumeValue } from "@/components/review/types";
```

- [ ] **Step 4: Verify the frontend builds**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/frontend
npx next build 2>&1 | tail -20
```

Expected: Build succeeds with no type errors

- [ ] **Step 5: Commit**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add frontend/src/lib/inboxApi.ts frontend/src/components/agent-inbox/inbox-item.tsx frontend/src/components/agent-inbox/inbox-list.tsx
git commit -m "feat(frontend): wire ReviewPanel into InboxItem with structured comments

- inboxApi extracts ReviewPayload from interrupt value
- InboxItem expands to show ReviewPanel with document + annotation
- InboxList passes ResumeValue (with comments) on resume
- Desktop: side-by-side document + comments sidebar
- Mobile: stacked document + comments below"
```

---

## Chunk 3: Recipe Replication + CopilotKit (Phase 5-6)

### Task 15: Replicate interrupt() to curriculum_package, grant_package, full_pipeline

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py` (3 graph builder functions)
- Modify: `langgraph_workflows/dhg-agents-cloud/tests/test_orchestrator.py`

- [ ] **Step 1: Update create_curriculum_package_graph**

Replace the function (lines 966-1004):

```python
def create_curriculum_package_graph():
    """Create the Curriculum Package recipe with parallel execution and interrupt-based review."""

    workflow = StateGraph(CMEPipelineState)

    # Needs phase
    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality_1", run_prose_quality_pass_1)

    # Curriculum phase
    workflow.add_node("design_phase", run_design_phase_parallel)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("process_feedback", process_review_feedback)
    workflow.add_node("complete", mark_complete)
    workflow.add_node("failed", mark_failed)

    # Flow
    workflow.set_entry_point("early_research")
    workflow.add_edge("early_research", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality_1")

    workflow.add_conditional_edges(
        "prose_quality_1",
        route_after_prose_quality_1,
        {
            "continue": "design_phase",
            "retry_needs": "needs_assessment",
            "human_intervention": "failed"
        }
    )

    workflow.add_edge("design_phase", "human_review")

    workflow.add_conditional_edges(
        "human_review",
        route_after_human_review_interrupt,
        {
            "approved": "complete",
            "revision": "process_feedback",
            "rejected": "failed"
        }
    )

    # Revision routes back to design phase (curriculum has 3 docs)
    workflow.add_edge("process_feedback", "design_phase")

    workflow.add_edge("complete", END)
    workflow.add_edge("failed", END)

    return workflow.compile()
```

- [ ] **Step 2: Update create_grant_package_graph**

Replace the function (lines 1012-1083):

```python
def create_grant_package_graph():
    """Create the Grant Package recipe with interrupt-based review."""

    workflow = StateGraph(CMEPipelineState)

    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality_1", run_prose_quality_pass_1)
    workflow.add_node("design_phase", run_design_phase_parallel)
    workflow.add_node("grant_writer", run_grant_writer_agent)
    workflow.add_node("prose_quality_2", run_prose_quality_pass_2)
    workflow.add_node("compliance", run_compliance_agent)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("process_feedback", process_review_feedback)
    workflow.add_node("complete", mark_complete)
    workflow.add_node("failed", mark_failed)

    workflow.set_entry_point("early_research")
    workflow.add_edge("early_research", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality_1")

    workflow.add_conditional_edges(
        "prose_quality_1",
        route_after_prose_quality_1,
        {
            "continue": "design_phase",
            "retry_needs": "needs_assessment",
            "human_intervention": "failed"
        }
    )

    workflow.add_edge("design_phase", "grant_writer")
    workflow.add_edge("grant_writer", "prose_quality_2")

    workflow.add_conditional_edges(
        "prose_quality_2",
        route_after_prose_quality_2,
        {
            "continue": "compliance",
            "retry_grant": "grant_writer",
            "human_intervention": "failed"
        }
    )

    workflow.add_conditional_edges(
        "compliance",
        route_after_compliance,
        {
            "continue": "human_review",
            "revision_required": "grant_writer"
        }
    )

    workflow.add_conditional_edges(
        "human_review",
        route_after_human_review_interrupt,
        {
            "approved": "complete",
            "revision": "process_feedback",
            "rejected": "failed"
        }
    )

    workflow.add_edge("process_feedback", "grant_writer")

    workflow.add_edge("complete", END)
    workflow.add_edge("failed", END)

    return workflow.compile()
```

- [ ] **Step 3: Update create_full_pipeline_graph**

Replace the function (lines 1091-1169):

```python
def create_full_pipeline_graph():
    """Create the Full Pipeline recipe with interrupt-based human review routing."""

    workflow = StateGraph(CMEPipelineState)

    workflow.add_node("early_research", run_early_research_parallel)
    workflow.add_node("gap_analysis", run_gap_analysis_agent)
    workflow.add_node("learning_objectives", run_learning_objectives_agent)
    workflow.add_node("needs_assessment", run_needs_assessment_agent)
    workflow.add_node("prose_quality_1", run_prose_quality_pass_1)
    workflow.add_node("design_phase", run_design_phase_parallel)
    workflow.add_node("grant_writer", run_grant_writer_agent)
    workflow.add_node("prose_quality_2", run_prose_quality_pass_2)
    workflow.add_node("compliance", run_compliance_agent)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("process_feedback", process_review_feedback)
    workflow.add_node("complete", mark_complete)
    workflow.add_node("failed", mark_failed)

    workflow.set_entry_point("early_research")
    workflow.add_edge("early_research", "gap_analysis")
    workflow.add_edge("gap_analysis", "learning_objectives")
    workflow.add_edge("learning_objectives", "needs_assessment")
    workflow.add_edge("needs_assessment", "prose_quality_1")

    workflow.add_conditional_edges(
        "prose_quality_1",
        route_after_prose_quality_1,
        {
            "continue": "design_phase",
            "retry_needs": "needs_assessment",
            "human_intervention": "failed"
        }
    )

    workflow.add_edge("design_phase", "grant_writer")
    workflow.add_edge("grant_writer", "prose_quality_2")

    workflow.add_conditional_edges(
        "prose_quality_2",
        route_after_prose_quality_2,
        {
            "continue": "compliance",
            "retry_grant": "grant_writer",
            "human_intervention": "failed"
        }
    )

    workflow.add_conditional_edges(
        "compliance",
        route_after_compliance,
        {
            "continue": "human_review",
            "revision_required": "grant_writer"
        }
    )

    workflow.add_conditional_edges(
        "human_review",
        route_after_human_review_interrupt,
        {
            "approved": "complete",
            "revision": "process_feedback",
            "rejected": "failed"
        }
    )

    workflow.add_edge("process_feedback", "grant_writer")

    workflow.add_edge("complete", END)
    workflow.add_edge("failed", END)

    return workflow.compile()
```

- [ ] **Step 4: Update checkpointed graph factories to match**

Update `create_checkpointed_needs_graph` and `create_checkpointed_grant_graph` to use `human_review_node` and `process_review_feedback` instead of `human_review_gate`. Follow the same pattern as the non-checkpointed versions above.

- [ ] **Step 5: Update graph construction tests**

Update `TestCurriculumPackageGraph`, `TestGrantPackageGraph`, `TestFullPipelineGraph` to expect `process_feedback` and `complete` nodes, and 3-way routing from `human_review`:

```python
class TestCurriculumPackageGraph:
    def test_compiles_without_error(self):
        graph = orch.create_curriculum_package_graph()
        assert graph is not None

    def test_has_expected_nodes(self):
        nodes = set(orch.curriculum_graph.get_graph().nodes.keys())
        expected = {
            "early_research", "gap_analysis", "learning_objectives",
            "needs_assessment", "prose_quality_1", "design_phase",
            "human_review", "process_feedback", "complete", "failed",
            "__start__", "__end__",
        }
        assert expected.issubset(nodes)


class TestGrantPackageGraph:
    def test_compiles_without_error(self):
        graph = orch.create_grant_package_graph()
        assert graph is not None

    def test_has_all_phase_nodes(self):
        nodes = set(orch.grant_graph.get_graph().nodes.keys())
        expected = {
            "early_research", "gap_analysis", "learning_objectives",
            "needs_assessment", "prose_quality_1", "design_phase",
            "grant_writer", "prose_quality_2", "compliance",
            "human_review", "process_feedback", "complete", "failed",
            "__start__", "__end__",
        }
        assert expected.issubset(nodes)


class TestFullPipelineGraph:
    def test_compiles_without_error(self):
        graph = orch.create_full_pipeline_graph()
        assert graph is not None

    def test_has_same_nodes_as_grant_graph(self):
        full_nodes = set(orch.full_graph.get_graph().nodes.keys())
        grant_nodes = set(orch.grant_graph.get_graph().nodes.keys())
        assert full_nodes == grant_nodes

    def test_full_graph_has_human_review_routing(self):
        graph_repr = orch.full_graph.get_graph()
        hr_targets = sorted([e[1] for e in graph_repr.edges if e[0] == "human_review"])
        assert "complete" in hr_targets
        assert "process_feedback" in hr_targets
        assert "failed" in hr_targets
```

- [ ] **Step 6: Remove old route_after_human_review function**

Delete the old `route_after_human_review` function (lines 907-915) since all graphs now use `route_after_human_review_interrupt`.

- [ ] **Step 7: Run full test suite**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add langgraph_workflows/dhg-agents-cloud/src/orchestrator.py langgraph_workflows/dhg-agents-cloud/tests/test_orchestrator.py
git commit -m "feat(orchestrator): replicate interrupt() to all 4 recipes

- curriculum_package: interrupt after design phase, revision loops to design_phase
- grant_package: interrupt after compliance, revision loops to grant_writer
- full_pipeline: same as grant but was already the most complete
- All recipes now use human_review_node + process_review_feedback
- Removed legacy human_review_gate and route_after_human_review"
```

---

### Task 16: Build CopilotKit Studio Route

**Files:**
- Create: `frontend/src/app/studio/page.tsx`
- Modify: `frontend/src/components/dhg/header.tsx`

- [ ] **Step 1: Create the studio page**

```tsx
// frontend/src/app/studio/page.tsx
"use client";

import { useState } from "react";
import { Header } from "@/components/dhg/header";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { NeedsAssessmentPanel } from "@/components/generative-ui/needs-assessment-panel";
import { GapAnalysisPanel } from "@/components/generative-ui/gap-analysis-panel";
import "@copilotkit/react-ui/styles.css";

const STUDIO_AGENTS = [
  { id: "needs_assessment", label: "Needs Assessment" },
  { id: "gap_analysis", label: "Gap Analysis" },
  { id: "needs_package", label: "Needs Package" },
  { id: "grant_package", label: "Grant Package" },
];

export default function StudioPage() {
  const [selectedAgent, setSelectedAgent] = useState(STUDIO_AGENTS[0].id);

  return (
    <div className="flex flex-col h-screen bg-background">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        {/* Agent selector sidebar */}
        <div className="w-56 border-r border-border p-4 space-y-2">
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Agent
          </h2>
          {STUDIO_AGENTS.map((agent) => (
            <button
              key={agent.id}
              onClick={() => setSelectedAgent(agent.id)}
              className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                selectedAgent === agent.id
                  ? "bg-dhg-purple text-white"
                  : "text-foreground hover:bg-muted"
              }`}
            >
              {agent.label}
            </button>
          ))}
        </div>

        {/* CopilotKit chat with generative UI */}
        <div className="flex-1">
          <CopilotKit runtimeUrl="/api/copilotkit" agent={selectedAgent}>
            <NeedsAssessmentPanel />
            <GapAnalysisPanel />
            <CopilotChat
              labels={{
                title: `Studio — ${STUDIO_AGENTS.find((a) => a.id === selectedAgent)?.label}`,
                initial: "Run an agent to see generative UI panels inline.",
              }}
            />
          </CopilotKit>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add Studio link to header**

In `frontend/src/components/dhg/header.tsx`, add a "Studio" nav link next to "Review Inbox":

Find the Review Inbox link and add after it:

```tsx
<Link
  href="/studio"
  className={`flex items-center gap-1.5 text-sm font-medium transition-colors ${
    pathname === "/studio"
      ? "text-dhg-purple"
      : "text-muted-foreground hover:text-foreground"
  }`}
>
  <Sparkles className="h-4 w-4" />
  Studio
</Link>
```

Add `Sparkles` to the lucide-react imports.

- [ ] **Step 3: Verify build**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/frontend
npx next build 2>&1 | tail -20
```

Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add frontend/src/app/studio/page.tsx frontend/src/components/dhg/header.tsx
git commit -m "feat(frontend): add /studio route with CopilotKit generative UI

- Agent selector sidebar (4 agents)
- CopilotKit wraps chat with selected agent
- NeedsAssessmentPanel and GapAnalysisPanel render inline
- Studio link added to header nav"
```

---

## Chunk 4: Observability + Production Readiness (Phase 7-9)

### Task 17: Fix Alert Rules

**Files:**
- Modify: `observability/prometheus/alerts.yml`

- [ ] **Step 1: Replace alerts.yml with real metrics**

```yaml
# observability/prometheus/alerts.yml
groups:
  - name: dhg-infrastructure
    rules:
      - alert: ContainerRestarting
        expr: increase(container_last_seen{name=~"dhg-.*"}[15m]) == 0 and container_last_seen{name=~"dhg-.*"} > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Container {{ $labels.name }} may be restarting"

      - alert: RegistryApiDown
        expr: up{job="registry-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Registry API is down"

      - alert: DiskUsageHigh
        expr: (1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Disk usage above 80% ({{ $value | humanizePercentage }})"

      - alert: MemoryUsageHigh
        expr: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Memory usage above 90% ({{ $value | humanizePercentage }})"

      - alert: PrometheusTargetDown
        expr: up == 0
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Prometheus target {{ $labels.job }} is down"

      - alert: ContainerHighCPU
        expr: rate(container_cpu_usage_seconds_total{name=~"dhg-.*"}[5m]) > 0.9
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Container {{ $labels.name }} CPU > 90% for 10m"

      - alert: ContainerHighMemory
        expr: container_memory_usage_bytes{name=~"dhg-.*"} / container_spec_memory_limit_bytes{name=~"dhg-.*"} > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Container {{ $labels.name }} memory > 90% of limit"

      - alert: PostgresConnectionsHigh
        expr: pg_stat_activity_count > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL active connections above 80"
```

- [ ] **Step 2: Verify Prometheus loads the rules**

```bash
curl -s http://localhost:9090/api/v1/rules | python3 -c "import json,sys; rules=json.load(sys.stdin); print(f'{len(rules[\"data\"][\"groups\"])} rule groups loaded')"
```

Expected: 1 rule group loaded (after Prometheus restart)

- [ ] **Step 3: Commit**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add observability/prometheus/alerts.yml
git commit -m "fix(observability): replace phantom alert rules with real infrastructure metrics

- Container restarts, high CPU/memory
- Registry API down, Prometheus target down
- Disk > 80%, memory > 90%, PostgreSQL connections"
```

---

### Task 18: Add Alertmanager Webhook Endpoint

**Files:**
- Modify: `registry/api.py`

- [ ] **Step 1: Find the right insertion point in api.py**

Read `registry/api.py` to find where to add the endpoint. Look for existing route definitions.

- [ ] **Step 2: Add the webhook endpoint**

Add after the existing health/metrics endpoints:

```python
from pydantic import BaseModel
from typing import List, Optional
import json

class AlertmanagerAlert(BaseModel):
    status: str
    labels: dict
    annotations: dict
    startsAt: str
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None

class AlertmanagerPayload(BaseModel):
    version: str
    groupKey: str
    status: str
    receiver: str
    alerts: List[AlertmanagerAlert]

@app.post("/webhooks/alertmanager")
async def alertmanager_webhook(payload: AlertmanagerPayload):
    """Receive and log Alertmanager webhook notifications."""
    logger.info(f"Alertmanager webhook: status={payload.status}, alerts={len(payload.alerts)}")
    for alert in payload.alerts:
        logger.info(
            f"  Alert: {alert.labels.get('alertname', 'unknown')} "
            f"status={alert.status} severity={alert.labels.get('severity', 'unknown')}"
        )
    return {"status": "received", "alerts_processed": len(payload.alerts)}
```

- [ ] **Step 3: Verify endpoint responds**

```bash
curl -s -X POST http://localhost:8011/webhooks/alertmanager \
  -H "Content-Type: application/json" \
  -d '{"version":"4","groupKey":"test","status":"firing","receiver":"webhook","alerts":[{"status":"firing","labels":{"alertname":"test"},"annotations":{"summary":"test alert"},"startsAt":"2026-03-10T00:00:00Z"}]}' | python3 -m json.tool
```

Expected: `{"status": "received", "alerts_processed": 1}`

- [ ] **Step 4: Commit**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add registry/api.py
git commit -m "feat(registry): add POST /webhooks/alertmanager endpoint

- Receives and logs Alertmanager webhook payloads
- Validates payload with Pydantic model
- Logs alert name, status, and severity"
```

---

### Task 19: Verify Loki Log Ingestion

**Files:** No code changes — verification only

- [ ] **Step 1: Check Promtail targets**

```bash
curl -s http://localhost:9080/targets 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for target in data:
        print(f\"  {target.get('labels', {}).get('job', 'unknown')}: {target.get('health', 'unknown')}\")
except: print('Promtail not responding on :9080')
"
```

- [ ] **Step 2: Query Loki for logs**

```bash
curl -s 'http://localhost:3100/loki/api/v1/query?query={job="docker"}&limit=5' | python3 -c "
import json, sys
data = json.load(sys.stdin)
results = data.get('data', {}).get('result', [])
print(f'{len(results)} log streams found')
for r in results[:3]:
    labels = r.get('stream', {})
    print(f'  Stream: {labels}')
"
```

Expected: At least 1 log stream found. If 0, debug the Promtail → Loki pipeline.

- [ ] **Step 3: Verify Tempo receives traces**

```bash
curl -s http://localhost:3200/status 2>/dev/null && echo "Tempo healthy" || echo "Tempo not responding"
```

---

### Task 20: Add dhg-frontend to Docker Compose

**Files:**
- Modify: `docker-compose.override.yml`

- [ ] **Step 1: Add the frontend service**

Add to `docker-compose.override.yml`:

```yaml
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        NEXT_PUBLIC_LANGGRAPH_API_URL: ${NEXT_PUBLIC_LANGGRAPH_API_URL:-http://localhost:2026}
    container_name: dhg-frontend
    ports:
      - "3002:3000"
    environment:
      - NODE_ENV=production
    networks:
      - dhg-network
    restart: unless-stopped
    labels:
      - "prometheus.io/scrape=false"
```

- [ ] **Step 2: Build and start the container**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
docker compose build frontend
docker compose up -d frontend
```

- [ ] **Step 3: Verify frontend is accessible**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3002
```

Expected: `200`

- [ ] **Step 4: Commit**

```bash
git add docker-compose.override.yml
git commit -m "feat(infra): containerize frontend as dhg-frontend on port 3002

- Multi-stage Docker build with standalone Next.js output
- NEXT_PUBLIC_LANGGRAPH_API_URL configurable via .env
- On dhg-network, restart unless-stopped"
```

---

### Task 21: Final Verification and Merge

- [ ] **Step 1: Run all Python tests**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/langgraph_workflows/dhg-agents-cloud
python -m pytest tests/ -v --tb=short
```

Expected: All tests pass

- [ ] **Step 2: Run frontend build**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/frontend
npx next build
```

Expected: Build succeeds

- [ ] **Step 3: Verify all services healthy**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
curl -s http://localhost:2026/ok && echo "LangGraph OK"
curl -s http://localhost:8011/healthz && echo "Registry OK"
curl -s http://localhost:3002 -o /dev/null -w "Frontend: %{http_code}\n"
curl -s http://localhost:9090/-/healthy && echo "Prometheus OK"
curl -s http://localhost:3001/api/health | python3 -c "import json,sys; print('Grafana OK' if json.load(sys.stdin).get('database') == 'ok' else 'Grafana FAIL')"
```

- [ ] **Step 4: Merge to master**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git checkout master
git merge feat/human-review-loop --no-ff -m "feat: human review loop with interrupt(), annotation UI, observability fixes

- All 4 orchestrator recipes use LangGraph interrupt() for human review
- ReviewPanel with text-annotation commenting in Next.js frontend
- process_review_feedback formats comments for targeted agent revision
- Max 3 revision cycles before escalation
- CopilotKit /studio route with generative UI panels
- Alert rules replaced with real infrastructure metrics
- Frontend containerized as dhg-frontend on port 3002"
```

- [ ] **Step 5: Push to trigger LangSmith Cloud deployment**

```bash
git push origin master
```

- [ ] **Step 6: Verify LangSmith Cloud picks up the changes**

Check LangSmith dashboard for new deployment. Verify the 15 graphs are available and `needs_package` shows the `human_review` node with interrupt.

---

## Summary

| Chunk | Tasks | Key Deliverables |
|-------|-------|-----------------|
| 1: Agent Interrupt | Tasks 1-6 | `interrupt()` in needs_package, process_review_feedback node, updated tests |
| 2: Frontend Review UI | Tasks 7-14 | ReviewPanel, DocumentViewer, AnnotationLayer, CommentsSidebar, MetricsBar, DecisionBar |
| 3: Recipe Replication + CopilotKit | Tasks 15-16 | All 4 recipes with interrupt, /studio route |
| 4: Observability + Production | Tasks 17-21 | Fixed alerts, webhook endpoint, Loki verification, containerized frontend, merge |
