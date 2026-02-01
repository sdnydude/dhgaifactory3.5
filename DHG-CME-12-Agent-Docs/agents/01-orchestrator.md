# Agent 1: Orchestrator Agent
## Workflow Control, State Management, Quality Gates

**Agent Type:** LangGraph StateGraph Controller  
**Complexity:** High  
**Primary Output:** State updates, routing decisions, quality gate enforcement

---

## Role Definition

The Orchestrator Agent is implemented as the LangGraph StateGraph itself—not as a separate LLM-powered agent. It manages workflow execution, state transitions, parallel execution, quality gates, and human review checkpoints. All routing logic is explicit in the graph definition rather than delegated to an LLM.

---

## Core Responsibilities

### 1. Workflow Sequencing
Controls the execution order of all agents according to the defined pipeline:

```
INTAKE → Research (2) + Clinical (3) [parallel]
              ↓
        Gap Analysis (4)
              ↓
        Needs Assessment (5)
              ↓
        Prose Quality (11) ← First pass
              ↓ (if pass)
        Learning Objectives (6)
              ↓
        Curriculum (7) + Protocol (8) + Marketing (9) [parallel]
              ↓
        Grant Writer (10)
              ↓
        Prose Quality (11) ← Second pass
              ↓ (if pass)
        Compliance (12)
              ↓
        HUMAN REVIEW GATE
              ↓
        FINAL OUTPUT
```

### 2. State Management
Maintains the complete project state across all agent executions:
- Intake form data (immutable after validation)
- Agent outputs (accumulated as pipeline progresses)
- Quality scores (prose quality, compliance scores)
- Checkpoint data (for recovery and debugging)
- Human review decisions

### 3. Parallel Execution
Manages concurrent agent execution at two points:
- **Early parallel:** Research Agent (2) + Clinical Practice Agent (3)
- **Late parallel:** Curriculum (7) + Protocol (8) + Marketing (9)

### 4. Quality Gate Enforcement
Implements pass/fail logic at critical checkpoints:
- Prose Quality gates (two passes)
- Compliance Review gate
- Human Review gate

### 5. Error Handling and Recovery
- Captures agent failures with full context
- Enables retry from last successful checkpoint
- Maintains audit trail of all state transitions

---

## State Schema

```python
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ProjectStatus(Enum):
    INTAKE_RECEIVED = "intake_received"
    RESEARCH_IN_PROGRESS = "research_in_progress"
    CLINICAL_IN_PROGRESS = "clinical_in_progress"
    GAP_ANALYSIS_IN_PROGRESS = "gap_analysis_in_progress"
    NEEDS_ASSESSMENT_IN_PROGRESS = "needs_assessment_in_progress"
    PROSE_QUALITY_PASS_1 = "prose_quality_pass_1"
    LEARNING_OBJECTIVES_IN_PROGRESS = "learning_objectives_in_progress"
    PARALLEL_DESIGN_IN_PROGRESS = "parallel_design_in_progress"
    GRANT_ASSEMBLY_IN_PROGRESS = "grant_assembly_in_progress"
    PROSE_QUALITY_PASS_2 = "prose_quality_pass_2"
    COMPLIANCE_REVIEW = "compliance_review"
    HUMAN_REVIEW_PENDING = "human_review_pending"
    REVISION_REQUIRED = "revision_required"
    COMPLETE = "complete"
    FAILED = "failed"

class CMEGrantState(TypedDict):
    # Project metadata
    project_id: str
    project_name: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    
    # Intake data (immutable after validation)
    intake_data: Dict[str, Any]
    intake_validated: bool
    
    # Agent outputs
    research_output: Optional[Dict[str, Any]]
    clinical_output: Optional[Dict[str, Any]]
    gap_analysis_output: Optional[Dict[str, Any]]
    needs_assessment_output: Optional[Dict[str, Any]]
    learning_objectives_output: Optional[Dict[str, Any]]
    curriculum_output: Optional[Dict[str, Any]]
    protocol_output: Optional[Dict[str, Any]]
    marketing_output: Optional[Dict[str, Any]]
    grant_package_output: Optional[Dict[str, Any]]
    
    # Quality tracking
    prose_quality_pass_1: Optional[Dict[str, Any]]
    prose_quality_pass_2: Optional[Dict[str, Any]]
    compliance_result: Optional[Dict[str, Any]]
    
    # Human review
    human_review_status: Optional[str]
    human_review_notes: Optional[str]
    human_reviewer: Optional[str]
    
    # Error tracking
    errors: List[Dict[str, Any]]
    retry_count: int
    
    # Checkpointing
    last_checkpoint: datetime
    checkpoint_agent: str
```

---

## Routing Logic

### Conditional Edges

```python
def route_after_prose_quality_1(state: CMEGrantState) -> str:
    """Route after first prose quality pass."""
    result = state.get("prose_quality_pass_1", {})
    if result.get("passed", False):
        return "learning_objectives"
    elif result.get("retry_count", 0) < 3:
        return "needs_assessment"  # Retry with feedback
    else:
        return "human_intervention"

def route_after_prose_quality_2(state: CMEGrantState) -> str:
    """Route after second prose quality pass."""
    result = state.get("prose_quality_pass_2", {})
    if result.get("passed", False):
        return "compliance_review"
    elif result.get("retry_count", 0) < 3:
        return "grant_writer"  # Retry with feedback
    else:
        return "human_intervention"

def route_after_compliance(state: CMEGrantState) -> str:
    """Route after compliance review."""
    result = state.get("compliance_result", {})
    if result.get("passed", False):
        return "human_review_gate"
    else:
        return "revision_required"

def route_after_human_review(state: CMEGrantState) -> str:
    """Route after human review gate."""
    status = state.get("human_review_status")
    if status == "approved":
        return "complete"
    elif status == "revision_requested":
        return "revision_required"
    else:
        return "human_review_gate"  # Still pending
```

---

## Quality Gates

### Gate 1: Prose Quality (First Pass)
**Location:** After Needs Assessment, before Learning Objectives  
**Criteria:**
- Prose density ≥80%
- Zero banned AI patterns
- Cold open character present
- Word count ≥3,100 words
- Quality score ≥8/10

**On Failure:**
- Return to Needs Assessment with specific feedback
- Maximum 3 retries before human intervention

### Gate 2: Prose Quality (Second Pass)
**Location:** After Grant Writer, before Compliance  
**Criteria:**
- All sections meet prose density requirement
- Consistent voice throughout
- Cold open character thread maintained (4+ appearances)
- No new AI patterns introduced during assembly
- Quality score ≥8/10

**On Failure:**
- Return to Grant Writer with specific revision instructions
- Maximum 3 retries before human intervention

### Gate 3: Compliance Review
**Location:** After Prose Quality Pass 2, before Human Review  
**Criteria:**
- All ACCME standards met
- Independence criteria verified
- Fair balance confirmed
- No commercial bias detected

**On Failure:**
- Route to revision with compliance-specific feedback
- Flag specific sections requiring attention

### Gate 4: Human Review
**Location:** Final gate before output  
**Criteria:**
- Human reviewer approves complete package
- Any requested revisions addressed

**Options:**
- Approve → Complete
- Request Revision → Route back with notes
- Reject → End pipeline with rejection reason

---

## Checkpoint Strategy

### Automatic Checkpoints
Checkpoint created after each agent completes:

```python
CHECKPOINT_POINTS = [
    "intake_validated",
    "research_complete",
    "clinical_complete",
    "gap_analysis_complete",
    "needs_assessment_complete",
    "prose_quality_1_complete",
    "learning_objectives_complete",
    "curriculum_complete",
    "protocol_complete",
    "marketing_complete",
    "grant_package_complete",
    "prose_quality_2_complete",
    "compliance_complete",
    "human_review_complete"
]
```

### Recovery Strategy
On failure, system can:
1. Identify last successful checkpoint
2. Load state from checkpoint
3. Resume from failed agent
4. Preserve all prior work

---

## Parallel Execution Handling

### Fan-Out Pattern
```python
def fan_out_early_research(state: CMEGrantState) -> List[str]:
    """Fan out to Research and Clinical agents in parallel."""
    return ["research_agent", "clinical_agent"]

def fan_out_design_phase(state: CMEGrantState) -> List[str]:
    """Fan out to Curriculum, Protocol, and Marketing in parallel."""
    return ["curriculum_agent", "protocol_agent", "marketing_agent"]
```

### Fan-In Pattern
```python
def fan_in_early_research(states: List[CMEGrantState]) -> CMEGrantState:
    """Merge Research and Clinical outputs."""
    merged = states[0].copy()
    for state in states[1:]:
        if state.get("research_output"):
            merged["research_output"] = state["research_output"]
        if state.get("clinical_output"):
            merged["clinical_output"] = state["clinical_output"]
    return merged

def fan_in_design_phase(states: List[CMEGrantState]) -> CMEGrantState:
    """Merge Curriculum, Protocol, and Marketing outputs."""
    merged = states[0].copy()
    for state in states[1:]:
        if state.get("curriculum_output"):
            merged["curriculum_output"] = state["curriculum_output"]
        if state.get("protocol_output"):
            merged["protocol_output"] = state["protocol_output"]
        if state.get("marketing_output"):
            merged["marketing_output"] = state["marketing_output"]
    return merged
```

---

## Error Handling

### Error Categories
1. **Agent Failure:** LLM call fails or returns invalid output
2. **Validation Failure:** Output doesn't meet schema requirements
3. **Quality Failure:** Output fails quality gate criteria
4. **Timeout:** Agent exceeds time limit
5. **External Failure:** API or database connectivity issues

### Error Response Matrix

| Error Type | Response | Retry? | Escalate? |
|------------|----------|--------|-----------|
| Agent Failure | Log, retry with backoff | Yes (3x) | After 3 failures |
| Validation Failure | Return to agent with feedback | Yes (2x) | After 2 failures |
| Quality Failure | Return to source agent | Yes (3x) | After 3 failures |
| Timeout | Extend timeout, retry | Yes (1x) | After 1 retry |
| External Failure | Wait, retry with backoff | Yes (5x) | After 5 failures |

---

## Observability Integration

### LangSmith Tracing
Every state transition logs:
- Agent name and version
- Input state hash
- Output state hash
- Execution duration
- Token usage
- Quality scores (where applicable)

### Metrics to Track
- Pipeline completion rate
- Average time per agent
- Retry frequency by agent
- Quality gate pass rates
- Human intervention frequency

---

## Implementation Notes

### Why StateGraph, Not Agent
The Orchestrator is implemented as pure graph logic rather than an LLM-powered agent because:
1. **Deterministic routing:** Workflow paths are known at design time
2. **No reasoning required:** Decisions are based on explicit criteria
3. **Cost efficiency:** No LLM tokens spent on routing decisions
4. **Reliability:** No hallucination risk in critical control flow
5. **Debuggability:** All paths are visible in graph definition

### LangGraph Configuration
```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

# Initialize graph with state schema
workflow = StateGraph(CMEGrantState)

# Add nodes for each agent
workflow.add_node("research_agent", research_agent_node)
workflow.add_node("clinical_agent", clinical_agent_node)
# ... etc

# Add conditional edges for quality gates
workflow.add_conditional_edges(
    "prose_quality_agent",
    route_after_prose_quality_1,
    {
        "learning_objectives": "learning_objectives_agent",
        "needs_assessment": "needs_assessment_agent",
        "human_intervention": "human_intervention_node"
    }
)

# Compile with checkpointing
checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
app = workflow.compile(checkpointer=checkpointer)
```

---

## Testing Strategy

### Unit Tests
- Each routing function with various state inputs
- Checkpoint save/restore operations
- Error handling for each failure type

### Integration Tests
- Complete pipeline with mock agents
- Parallel execution timing
- Quality gate enforcement
- Human review flow

### Load Tests
- Concurrent project execution
- Checkpoint performance under load
- Recovery time from failures

---

*The Orchestrator is the backbone of the system. Its reliability determines overall system reliability.*
