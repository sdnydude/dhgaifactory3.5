# ANTIGRAVITY EXECUTION PROMPT
## DHG CME Grant Multi-Agent System - Full Implementation

**Project:** 12-Agent Pipeline for Pharmaceutical-Grade CME Grant Generation  
**Client:** Digital Harmony Group  
**Implementation Agent:** Antigravity  
**Start Date:** January 31, 2026

---

## MISSION

Build a production-ready 12-agent AI system using LangGraph that transforms intake form data into complete, ACCME-compliant CME grant request packages. The system must produce documentation that reads as professionally written by experienced medical writers, not AI-generated content.

**Success Criteria:**
1. End-to-end pipeline processes intake form → produces complete grant package
2. Output passes prose quality checks (no AI writing patterns, 80%+ flowing prose)
3. Documents meet ACCME compliance standards
4. System is observable via LangSmith, debuggable, and improvable
5. Human review gates function at critical checkpoints
6. Cost per grant generation is predictable and acceptable

---

## PRIMARY SPECIFICATION DOCUMENTS

### 1. Master Handoff Brief (READ FIRST)
**Location:** `/mnt/project/DHG_CME_Grant_Master_Handoff_Brief.md`
**Size:** 13,500 words
**Contains:**
- Executive summary and business context
- Complete system architecture overview
- All 12 agent descriptions (condensed)
- Technology stack decisions (LangGraph, LangSmith, Claude Sonnet 4.5)
- Quality standards and success metrics
- Phased implementation roadmap

**ACTION:** Read this document completely before starting any implementation.

### 2. Full Technical Specification
**Location:** `/mnt/project/DHG_CME_Grant_MultiAgent_System_v1.md`
**Size:** 7,788 lines (153 KB)
**Contains:**
- Complete intake form specification (Sections A-J)
- Shared resources: DHG Writing Style Guide, Moore's Expanded Framework, Cold Open Framework, Audience Context
- All 12 agent prompts with detailed input/output specifications
- LangGraph orchestration design with state schema
- Quality gate definitions
- Word count minimums for each section
- Narrative thread tracking (cold open character)

**ACTION:** Reference specific agent sections as you implement each one.

### 3. Project Instructions & Working Protocols
**Location:** `/mnt/project/DHG_CME_Grant_Project_Instructions.md`
**Size:** ~8,000 words
**Contains:**
- Project overview and success criteria
- Technical decisions (locked)
- Agent implementation template
- Phased implementation plan with deliverables
- Quality gates for each phase
- Working protocols for collaboration
- File naming conventions
- Code deliverables protocol

**ACTION:** Follow the phased approach and quality gates defined here.

---

## THE 12 AGENTS (In Execution Order)

| # | Agent Name | Purpose | Complexity | Output |
|---|------------|---------|------------|--------|
| 1 | **Orchestrator** | Workflow control, state management, QA gates | High | State transitions, routing decisions |
| 2 | **Research** | Literature review, epidemiology, market intel | Medium | Research summary (2,000+ words, 30+ citations) |
| 3 | **Clinical Practice** | Standard of care, practice patterns, barriers | Medium | Clinical analysis (1,900+ words) |
| 4 | **Gap Analysis** | Synthesize gaps, quantify, prioritize | Medium | Gap document (2,600+ words) |
| 5 | **Needs Assessment** | Cold open + narrative document | **High** | 3,100+ word document with cold open |
| 6 | **Learning Objectives** | Moore's Framework objectives | Medium | 8-12 objectives (Levels 4-6) |
| 7 | **Curriculum Design** | Educational design + innovation | Medium | Curriculum document (2,400+ words) |
| 8 | **Research Protocol** | IRB-ready outcomes research protocol | Medium | Protocol document (2,100+ words) |
| 9 | **Marketing Plan** | Audience generation strategy + budget | Medium | Marketing plan (1,500+ words) |
| 10 | **Grant Writer** | Assemble complete grant package | **High** | Final grant proposal + summaries |
| 11 | **Prose Quality** | De-AI-ification, style enforcement | Medium | Quality score + revision instructions |
| 12 | **Compliance Review** | ACCME standards verification | Low | Compliance checklist (pass/fail) |

---

## PHASED IMPLEMENTATION PLAN

### PHASE 1: Prove Core Pattern (Weeks 1-3)
**Goal:** Validate that a single high-complexity agent works with tools and LangSmith tracing

**START HERE:** Implement Needs Assessment Agent (Agent #5)

**Why This Agent First:**
- Highest complexity writing task
- Requires cold open generation (tests creativity)
- Has strict word count requirements (tests compliance)
- Uses multiple tools (web search, citation formatting)
- If this works, simpler agents will definitely work

**Deliverables:**
- [ ] `agents/needs_assessment.py` - Agent implementation using `create_agent()`
- [ ] Tools configured: web search, document retrieval, citation formatting
- [ ] LangSmith tracing working (can see full execution in LangSmith UI)
- [ ] Single test case produces valid 3,100+ word output
- [ ] `agents/prose_quality.py` - Prose Quality Agent validates output (score ≥8/10)
- [ ] Test output saved to `outputs/test_needs_assessment_01.md`

**Quality Gates (Must Pass Before Phase 2):**
- [ ] Agent produces output matching spec format exactly
- [ ] Word count ≥3,100 words
- [ ] Cold open present (4-act structure: Moment, Person, Stakes, Turn)
- [ ] LangSmith trace shows complete execution without errors
- [ ] Prose Quality Agent scores ≥8/10 (no AI tells, flowing prose)
- [ ] No banned phrases from Style Guide present
- [ ] Character count exact on executive summary (200 chars)

**Implementation Template:**
```python
# agents/needs_assessment.py

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langsmith import traceable
from typing import TypedDict

# 1. Define state subset needed by this agent
class NeedsAssessmentInput(TypedDict):
    therapeutic_area: str
    target_specialties: list[str]
    research_summary: str
    clinical_analysis: str
    gap_analysis: str
    cold_open_character: dict

# 2. Define tools
tools = [
    web_search_tool,
    citation_formatter_tool,
    word_counter_tool
]

# 3. Load system prompt from spec (verbatim)
with open('prompts/needs_assessment_prompt.txt', 'r') as f:
    system_prompt = f.read()

# 4. Create agent
model = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0.7)
agent = create_agent(
    model=model,
    tools=tools,
    prompt=system_prompt
)

# 5. Define node function for LangGraph
@traceable(name="needs_assessment_node")
def needs_assessment_node(state: CMEGrantState) -> CMEGrantState:
    """Generate needs assessment document with cold open."""
    
    # Extract relevant state
    input_data = {
        "therapeutic_area": state["therapeutic_area"],
        "target_specialties": state["target_specialties"],
        "research_summary": state["research_summary"],
        "clinical_analysis": state["clinical_analysis"],
        "gap_analysis": state["gap_analysis"],
        "cold_open_character": state.get("cold_open_character", {})
    }
    
    # Invoke agent
    result = agent.invoke(input_data)
    
    # Update state
    state["needs_assessment"] = result["output"]
    state["cold_open_character"] = result.get("cold_open_character", {})
    state["agent_status"]["needs_assessment"] = "complete"
    
    return state
```

**File Structure for Phase 1:**
```
/project-root/
├── agents/
│   ├── __init__.py
│   ├── needs_assessment.py
│   └── prose_quality.py
├── prompts/
│   ├── needs_assessment_prompt.txt  (from spec, verbatim)
│   └── prose_quality_prompt.txt
├── tools/
│   ├── __init__.py
│   ├── web_search.py
│   ├── citation_formatter.py
│   └── word_counter.py
├── config/
│   ├── state_schema.py
│   └── langsmith_config.py
├── tests/
│   ├── test_needs_assessment.py
│   └── fixtures/
│       └── sample_intake.json
├── outputs/
│   └── (generated documents go here)
├── requirements.txt
└── README.md
```

**Testing Phase 1:**
```python
# tests/test_needs_assessment.py

import pytest
from agents.needs_assessment import needs_assessment_node
from config.state_schema import CMEGrantState

def test_needs_assessment_basic():
    """Test basic needs assessment generation."""
    
    # Load sample state
    state = {
        "therapeutic_area": "Type 2 Diabetes",
        "target_specialties": ["Endocrinology", "Primary Care"],
        "research_summary": "...",  # From fixture
        "clinical_analysis": "...",
        "gap_analysis": "...",
        "agent_status": {}
    }
    
    # Run agent
    result = needs_assessment_node(state)
    
    # Assertions
    assert "needs_assessment" in result
    assert len(result["needs_assessment"]) >= 3100 * 5  # ~3100 words = ~15,500 chars
    assert "cold_open_character" in result
    assert result["agent_status"]["needs_assessment"] == "complete"
    
    # Check for cold open structure
    output = result["needs_assessment"]
    assert "The Moment" in output or any narrative indicator present
    
    # Save output for manual review
    with open('outputs/test_needs_assessment_01.md', 'w') as f:
        f.write(result["needs_assessment"])

def test_prose_quality_check():
    """Test that prose quality agent validates output."""
    
    # Load generated needs assessment
    with open('outputs/test_needs_assessment_01.md', 'r') as f:
        needs_assessment = f.read()
    
    # Run prose quality check
    from agents.prose_quality import prose_quality_node
    state = {"needs_assessment": needs_assessment}
    result = prose_quality_node(state)
    
    # Assertions
    assert result["prose_quality_score"] >= 8
    assert "AI writing patterns detected" not in result.get("quality_notes", "")
```

---

### PHASE 2: Full Orchestration (Weeks 4-6)
**Goal:** Complete pipeline with all 12 agents orchestrated by LangGraph

**Deliverables:**
- [ ] All 12 agents implemented in `agents/` directory
- [ ] LangGraph StateGraph defined in `workflow/graph.py`
- [ ] State schema implemented in `config/state_schema.py`
- [ ] Conditional routing (prose quality pass/fail loops)
- [ ] MemorySaver checkpointing for local development
- [ ] End-to-end test with sample intake form
- [ ] Cold open character tracked through entire narrative thread
- [ ] All quality gates pass

**LangGraph Workflow Structure:**
```python
# workflow/graph.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from config.state_schema import CMEGrantState
from agents import *

# Create graph
workflow = StateGraph(CMEGrantState)

# Add nodes
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("research", research_node)
workflow.add_node("clinical_practice", clinical_practice_node)
workflow.add_node("gap_analysis", gap_analysis_node)
workflow.add_node("needs_assessment", needs_assessment_node)
workflow.add_node("learning_objectives", learning_objectives_node)
workflow.add_node("curriculum_design", curriculum_design_node)
workflow.add_node("research_protocol", research_protocol_node)
workflow.add_node("marketing_plan", marketing_plan_node)
workflow.add_node("grant_writer", grant_writer_node)
workflow.add_node("prose_quality", prose_quality_node)
workflow.add_node("compliance_review", compliance_review_node)

# Define edges (sequential flow)
workflow.add_edge("orchestrator", "research")
workflow.add_edge("research", "clinical_practice")
workflow.add_edge("clinical_practice", "gap_analysis")
workflow.add_edge("gap_analysis", "needs_assessment")
workflow.add_edge("needs_assessment", "prose_quality")

# Conditional routing for prose quality
def should_retry_prose(state):
    """Route based on prose quality score."""
    if state.get("prose_quality_score", 0) < 8:
        return "needs_assessment"  # Retry with feedback
    else:
        return "learning_objectives"  # Continue

workflow.add_conditional_edges(
    "prose_quality",
    should_retry_prose,
    {
        "needs_assessment": "needs_assessment",
        "learning_objectives": "learning_objectives"
    }
)

workflow.add_edge("learning_objectives", "curriculum_design")
workflow.add_edge("curriculum_design", "research_protocol")
workflow.add_edge("research_protocol", "marketing_plan")
workflow.add_edge("marketing_plan", "grant_writer")
workflow.add_edge("grant_writer", "compliance_review")
workflow.add_edge("compliance_review", END)

# Set entry point
workflow.set_entry_point("orchestrator")

# Compile with checkpointing
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
```

**State Schema:**
```python
# config/state_schema.py

from typing import TypedDict, Optional, List, Dict

class CMEGrantState(TypedDict):
    # Intake form data (Section A-J)
    program_title: str
    therapeutic_area: str
    target_specialties: List[str]
    target_audience_size: int
    program_format: str
    duration_minutes: int
    budget_request: float
    supporter_info: Dict
    # ... (all intake fields)
    
    # Agent outputs
    research_summary: str
    clinical_analysis: str
    gap_analysis: str
    needs_assessment: str
    learning_objectives: List[Dict]
    curriculum_design: str
    research_protocol: str
    marketing_plan: str
    grant_proposal: str
    
    # Quality checks
    prose_quality_score: float
    quality_notes: str
    compliance_checklist: Dict[str, bool]
    
    # Narrative thread
    cold_open_character: Dict[str, any]
    character_appearances: List[Dict]
    
    # Status tracking
    agent_status: Dict[str, str]
    retry_count: Dict[str, int]
    
    # Metadata
    created_at: str
    updated_at: str
```

**Quality Gates (Must Pass Before Phase 3):**
- [ ] Full graph executes without errors
- [ ] State persists correctly across all nodes
- [ ] Retry logic works (prose quality fail → feedback → retry → pass)
- [ ] Output package contains all required documents
- [ ] Character counts exact on all summaries
- [ ] Cold open character appears consistently throughout all documents
- [ ] Word counts meet minimums for all sections
- [ ] No AI writing patterns in final output

---

### PHASE 3: Production Infrastructure (Weeks 7-10)
**Goal:** Production-ready deployment with PostgreSQL, human review UI, evaluation

**Deliverables:**
- [ ] PostgresSaver replaces MemorySaver
- [ ] Human review UI at designated gates (Needs Assessment, Grant Proposal)
- [ ] Evaluation datasets created for each agent (10+ examples each)
- [ ] LLM-as-judge evaluators configured
- [ ] Deployment to LangGraph Cloud or self-hosted
- [ ] Cost tracking and optimization
- [ ] Documentation for operators

**PostgreSQL Checkpointing:**
```python
from langgraph.checkpoint.postgres import PostgresSaver

# Production checkpoint configuration
checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost:5432/cme_grants"
)

app = workflow.compile(checkpointer=checkpointer)
```

**Human Review Integration:**
```python
def needs_assessment_review_gate(state):
    """Pause for human review of needs assessment."""
    
    # Save state
    checkpoint_id = save_checkpoint(state)
    
    # Trigger UI notification
    notify_reviewer(
        checkpoint_id=checkpoint_id,
        document_type="needs_assessment",
        content=state["needs_assessment"]
    )
    
    # Wait for approval
    # (Implementation depends on UI framework)
    return state

workflow.add_node("needs_review_gate", needs_assessment_review_gate)
```

---

## TECHNOLOGY STACK (Locked Decisions)

### Core Framework
- **LangGraph** StateGraph for orchestration
- **LangSmith** for observability, tracing, evaluation
- **Claude Sonnet 4.5** (`claude-sonnet-4-20250514`) for all agents
- **Python 3.11+** with type hints

### Agent Pattern
```python
from langchain.agents import create_agent

agent = create_agent(
    model=ChatAnthropic(model="claude-sonnet-4-20250514"),
    tools=[...],
    prompt=system_prompt
)
```

### Checkpointing
- **Phase 1-2:** MemorySaver (local development)
- **Phase 3:** PostgresSaver (production)

### Evaluation
- **Offline first:** Datasets + LLM-as-judge
- **Online later:** Production run evaluation

### Key Libraries
```
langgraph>=0.2.0
langchain>=0.3.0
langchain-anthropic>=0.2.0
langsmith>=0.2.0
psycopg2-binary>=2.9.0  (Phase 3)
pydantic>=2.0.0
python-dotenv>=1.0.0
```

---

## CRITICAL REQUIREMENTS

### 1. Prose Quality (Non-Negotiable)
**Goal:** 80%+ flowing prose density, zero AI tells

**Banned Phrases (from DHG Writing Style Guide):**
- "delve into", "dive into", "realm of", "navigate the landscape"
- Excessive em dashes (—)
- "Furthermore", "Moreover", "Additionally" as paragraph starters
- "It's important to note", "It's worth mentioning"
- Overuse of "various", "myriad", "plethora"

**Required Patterns:**
- Narrative cold opens (4-act structure)
- Active voice ≥70% of sentences
- Short sentences mixed with longer ones (rhythm variation)
- Specific clinical examples, not generic placeholders
- Character-driven narrative threads

### 2. Moore's Framework Compliance
All learning objectives must use Moore's Expanded Outcomes Framework:
- Target: Levels 4-6 (40-60% at Level 5)
- Verbs must match framework levels exactly
- Distribution: 40-60% L5, 30-40% L4, 10-20% L3

### 3. Word Count Minimums
Every section has strict minimums (see spec). System must:
- Track word counts per section
- Warn if below minimums
- Retry if significantly under

### 4. Cold Open Narrative Thread
Character introduced in Needs Assessment must:
- Reappear in Gap Analysis
- Inform curriculum case studies
- Resurface in outcomes measures
- Be tracked in state: `cold_open_character` dict

### 5. ACCME Compliance
- No product mentions (commercial bias)
- Balanced references (no single sponsor dominance)
- Outcomes research methodology sound
- Disclosure statements present

---

## LANGSMITH CONFIGURATION

### Environment Setup
```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=<your-key>
export LANGCHAIN_PROJECT="cme-grant-pipeline"
```

### Tagging Strategy
```python
@traceable(
    name="needs_assessment_agent",
    tags=["agent:needs_assessment", "phase:writing", "priority:high"],
    metadata={
        "therapeutic_area": state["therapeutic_area"],
        "target_word_count": 3100
    }
)
def needs_assessment_node(state):
    # ...
```

### Evaluation Setup (Phase 3)
```python
from langsmith import Client

client = Client()

# Create evaluation dataset
dataset = client.create_dataset(
    dataset_name="needs-assessment-examples",
    description="Gold standard needs assessment documents"
)

# Add examples
client.create_examples(
    inputs=[{"intake_form": {...}}],
    outputs=[{"needs_assessment": "..."}],
    dataset_id=dataset.id
)

# Define evaluator
def prose_quality_evaluator(run, example):
    """LLM-as-judge for prose quality."""
    output = run.outputs["needs_assessment"]
    
    # Check for AI patterns
    banned = ["delve into", "furthermore", "it's important to note"]
    score = 10.0
    for phrase in banned:
        if phrase.lower() in output.lower():
            score -= 1.0
    
    return {"key": "prose_quality", "score": max(score, 0)}
```

---

## TESTING STRATEGY

### Unit Tests
Each agent must have:
- Basic generation test
- Word count validation test
- Format compliance test
- Error handling test

### Integration Tests
- Full pipeline end-to-end
- State persistence across checkpoints
- Retry logic (prose quality failures)
- Human review gate simulation

### Evaluation Tests (Phase 3)
- Run against gold standard dataset
- LLM-as-judge scoring
- Automated compliance checks

---

## DELIVERABLES CHECKLIST

### Phase 1 Complete When:
- [ ] Needs Assessment Agent generates valid 3,100+ word output
- [ ] Prose Quality Agent validates with score ≥8/10
- [ ] LangSmith traces show complete execution
- [ ] Test output saved and manually reviewed
- [ ] Code follows template pattern
- [ ] Documentation complete for these 2 agents

### Phase 2 Complete When:
- [ ] All 12 agents implemented
- [ ] LangGraph workflow executes end-to-end
- [ ] Sample intake form → complete grant package
- [ ] All word counts meet minimums
- [ ] Cold open character tracked throughout
- [ ] Retry loops function correctly
- [ ] State persists across checkpoints
- [ ] No errors in execution

### Phase 3 Complete When:
- [ ] PostgreSQL checkpointing works
- [ ] Human review UI functional
- [ ] Evaluation datasets created
- [ ] LLM-as-judge evaluators running
- [ ] Deployed to production environment
- [ ] Cost tracking implemented
- [ ] Operator documentation complete

---

## FILE STRUCTURE (Final)

```
cme-grant-pipeline/
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── research.py
│   ├── clinical_practice.py
│   ├── gap_analysis.py
│   ├── needs_assessment.py
│   ├── learning_objectives.py
│   ├── curriculum_design.py
│   ├── research_protocol.py
│   ├── marketing_plan.py
│   ├── grant_writer.py
│   ├── prose_quality.py
│   └── compliance_review.py
├── prompts/
│   ├── orchestrator_prompt.txt
│   ├── research_prompt.txt
│   └── ... (12 prompt files, verbatim from spec)
├── tools/
│   ├── __init__.py
│   ├── web_search.py
│   ├── citation_formatter.py
│   ├── word_counter.py
│   ├── moores_framework_validator.py
│   └── accme_checker.py
├── workflow/
│   ├── __init__.py
│   ├── graph.py
│   └── routing.py
├── config/
│   ├── __init__.py
│   ├── state_schema.py
│   ├── langsmith_config.py
│   └── settings.py
├── tests/
│   ├── unit/
│   │   ├── test_needs_assessment.py
│   │   └── ... (12 agent tests)
│   ├── integration/
│   │   └── test_full_pipeline.py
│   ├── evaluation/
│   │   └── test_prose_quality.py
│   └── fixtures/
│       ├── sample_intake_diabetes.json
│       └── gold_needs_assessment.md
├── ui/  (Phase 3)
│   ├── review_dashboard.py
│   └── templates/
├── outputs/
│   └── (generated grant packages)
├── docs/
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── OPERATOR_GUIDE.md
├── .env.example
├── requirements.txt
├── setup.py
├── README.md
└── pyproject.toml
```

---

## QUALITY GATES SUMMARY

### Phase 1 Gates (Before Phase 2)
✓ Single agent (Needs Assessment) produces spec-compliant output
✓ Word count ≥3,100 words
✓ Prose quality score ≥8/10
✓ LangSmith trace complete and error-free
✓ Cold open present and well-formed

### Phase 2 Gates (Before Phase 3)
✓ All 12 agents implemented
✓ Full pipeline executes without errors
✓ All word counts meet minimums
✓ Character counts exact on summaries
✓ Cold open character tracked throughout
✓ Retry logic functions correctly
✓ State persists across checkpoints

### Phase 3 Gates (Before Production)
✓ PostgreSQL checkpointing functional
✓ Human review UI working
✓ Evaluation datasets complete (10+ examples per agent)
✓ LLM-as-judge evaluators configured
✓ Cost per run predictable and acceptable
✓ Documentation complete

---

## COST TRACKING

### Per-Agent Cost Estimation
Track input/output tokens for each agent:
```python
@traceable
def needs_assessment_node(state):
    start_time = time.time()
    
    result = agent.invoke(state)
    
    duration = time.time() - start_time
    log_cost(
        agent="needs_assessment",
        input_tokens=result["usage"]["input_tokens"],
        output_tokens=result["usage"]["output_tokens"],
        duration=duration
    )
    
    return state
```

### Target: <$50/grant

---

## SUPPORT RESOURCES

### Documentation to Reference
1. **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
2. **LangSmith Docs:** https://docs.smith.langchain.com/
3. **Claude API Docs:** https://docs.anthropic.com/

### Spec Documents (Read These)
1. `/mnt/project/DHG_CME_Grant_Master_Handoff_Brief.md` - Start here
2. `/mnt/project/DHG_CME_Grant_MultiAgent_System_v1.md` - Full spec
3. `/mnt/project/DHG_CME_Grant_Project_Instructions.md` - Working protocols

### Communication
- Log all decisions in decisions log
- Track blockers and open questions
- Request clarification when spec is ambiguous
- Provide progress updates at phase milestones

---

## EXECUTION CHECKLIST

### Before Starting
- [ ] Read Master Handoff Brief completely
- [ ] Review Phase 1 requirements and quality gates
- [ ] Set up development environment (Python 3.11+, virtualenv)
- [ ] Install dependencies: `pip install langgraph langchain langchain-anthropic langsmith`
- [ ] Configure LangSmith API key
- [ ] Create project directory structure

### Phase 1 Execution
- [ ] Implement Needs Assessment Agent
- [ ] Implement Prose Quality Agent
- [ ] Create test fixtures (sample intake data)
- [ ] Write unit tests
- [ ] Run tests, verify quality gates
- [ ] Manual review of generated output
- [ ] LangSmith trace review
- [ ] Document any deviations from spec

### Phase 2 Execution
- [ ] Implement remaining 10 agents
- [ ] Build LangGraph workflow
- [ ] Implement state schema
- [ ] Add conditional routing
- [ ] Configure MemorySaver
- [ ] End-to-end integration test
- [ ] Verify all quality gates
- [ ] Performance optimization

### Phase 3 Execution
- [ ] Set up PostgreSQL database
- [ ] Configure PostgresSaver
- [ ] Build human review UI
- [ ] Create evaluation datasets
- [ ] Configure LLM-as-judge evaluators
- [ ] Deploy to production environment
- [ ] Implement cost tracking
- [ ] Write operator documentation

---

## START HERE

**Your first task:**

1. Read `/mnt/project/DHG_CME_Grant_Master_Handoff_Brief.md` completely
2. Read Phase 1 section of `/mnt/project/DHG_CME_Grant_Project_Instructions.md`
3. Review Needs Assessment Agent spec in `/mnt/project/DHG_CME_Grant_MultiAgent_System_v1.md` (search for "## Agent 5: Needs Assessment Agent")
4. Create project directory structure
5. Implement Needs Assessment Agent following the template above
6. Run tests and verify Phase 1 quality gates

**When Phase 1 is complete and all quality gates pass, report back for Phase 2 instructions.**

---

*This is a complex, high-value system. Take your time, follow the spec precisely, and verify quality gates at each phase. The phased approach ensures we validate core patterns before building the full system.*

**Good luck! Let's build something excellent.**

---

**Document Version:** 1.0  
**Created:** January 31, 2026  
**For:** Antigravity (Coding Agent)  
**Project:** DHG CME Grant Multi-Agent System
