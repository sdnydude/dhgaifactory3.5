# DHG CME Grant Multi-Agent System
## Master Handoff Brief v1.0

**Date:** January 31, 2026  
**Project Owner:** Stephen Webber, Digital Harmony Group  
**Document Purpose:** Complete project snapshot for seamless continuation across chat sessions  
**Status:** Phase 0 (Pre-Implementation) → Ready to begin Phase 1

---

## Executive Summary

### What We're Building
A production-ready 12-agent AI system that generates pharmaceutical-grade CME (Continuing Medical Education) grant request documentation. The system processes structured intake data through research, analysis, writing, and quality assurance phases to produce compelling narrative documents that:

- Read as professionally written by experienced medical writers (not AI-generated)
- Meet ACCME compliance standards
- Secure funding from pharmaceutical companies
- Include innovative features (AI-powered learning, outcomes measurement)
- Generate complete packages with all required documentation

### Why This Matters
Current CME grant writing is manual, time-intensive, and inconsistent. This system represents an "AI Factory" approach where structured inputs produce high-quality, compliant outputs at scale. Success criteria: grant approval rate >60%, time to draft <5 days, prose quality score >8/10.

### Current State
**Phase:** Pre-Implementation (Phase 0)  
**Completed:** Full specification document (4,247 lines), technical research, architecture decisions  
**Next:** Implement Phase 1 (single high-complexity agent validation)  
**Blockers:** None

---

## Critical Documents

### Primary Specification (READ THIS FIRST)
```
/mnt/project/DHG_CME_Grant_MultiAgent_System_v1.md
```

**What's Inside (7,788 lines):**
- Complete intake form specification (Sections A-J)
- Shared resources used by all agents:
  - Writing Style Guide (prose requirements, banned AI patterns)
  - Moore's Expanded Outcomes Framework (primary taxonomy)
  - Cold Open Framework (narrative hooks)
  - Audience Context (pharmaceutical grant reviewers)
- All 12 agent specifications with:
  - Identity and purpose
  - Input parameters
  - Output format with word count minimums
  - Quality checklists
- LangGraph orchestration design
- Implementation timeline

**How to Use This Document:**
- Don't read it start to finish (too long)
- Jump to specific agent sections as needed
- Refer to shared resources for all writing agents
- Use as authoritative source for requirements

### Supporting Research
```
/mnt/transcripts/2026-01-29-17-04-20-langchain-deployment-reality-check.txt
```

**Key Findings:**
- LangGraph StateGraph is production-ready, well-documented
- Deep Agents are convenience wrappers, not necessary
- LangSmith observability is mature and reliable
- No out-of-box solution for 12-agent orchestration
- Custom integration work required but feasible

### Project Instructions
```
/mnt/project/DHG_CME_Grant_Project_Instructions.md
```

**Contains:**
- Working protocols for chat sessions
- Phased implementation plan
- Quality gates
- Agent implementation template
- File naming conventions
- Communication preferences

---

## Technical Architecture

### Stack Decisions (LOCKED - Don't Revisit)

| Component | Choice | Rationale | Alternatives Rejected |
|-----------|--------|-----------|----------------------|
| **Orchestration** | LangGraph StateGraph | Explicit control flow, battle-tested, best documented | LangChain's Deep Agents (too new, unproven for subagent coordination) |
| **Observability** | LangSmith | Production-ready tracing, evaluation, prompt management | Custom logging (reinventing wheel) |
| **Agent Pattern** | `create_agent()` with tools | Standard, reliable, well-supported | Custom agent classes (unnecessary complexity) |
| **Checkpointing** | MemorySaver → PostgresSaver | Prove locally first, then production | Direct to Postgres (skips validation) |
| **Evaluation** | Offline (datasets + LLM-as-judge) | Stable, documented, enables iteration | Online only (harder to debug) |
| **Model** | Claude Sonnet 4.5 | Balance of capability and cost | GPT-4 (cost), Claude Opus (overkill) |

### State Schema

```python
class CMEGrantState(TypedDict):
    # Project identification
    project_id: str
    status: str  # intake|research|gap_analysis|...
    
    # Intake data (all 10 sections A-J)
    intake_data: dict
    
    # Cold open (narrative thread)
    cold_open: Optional[ColdOpen]
    
    # Agent outputs
    research_report: Optional[str]
    clinical_analysis: Optional[str]
    gap_analysis: Optional[str]
    needs_assessment: Optional[str]
    needs_assessment_revised: Optional[str]
    learning_objectives: Optional[List[dict]]
    curriculum_design: Optional[str]
    research_protocol: Optional[str]
    marketing_plan: Optional[str]
    grant_package: Optional[dict]
    grant_package_revised: Optional[str]
    compliance_report: Optional[dict]
    
    # Quality tracking
    prose_quality_report_1: Optional[dict]
    prose_quality_report_2: Optional[dict]
    quality_scores: dict
    
    # Control flow
    errors: List[str]
    human_review_flags: List[str]
    retry_count: int
```

### Graph Flow (Simplified)

```
INTAKE → RESEARCH → CLINICAL → GAP_ANALYSIS → NEEDS_ASSESSMENT 
    ↓
PROSE_QUALITY_1 (gate: pass → continue, fail → retry or human review)
    ↓
LEARNING_OBJECTIVES → CURRICULUM + PROTOCOL + MARKETING (parallel)
    ↓
GRANT_WRITER → PROSE_QUALITY_2 (gate) → COMPLIANCE → HUMAN_REVIEW → END
```

---

## The 12 Agents

### Quick Reference

| # | Agent | Complexity | Word Count Min | Key Innovation |
|---|-------|------------|----------------|----------------|
| 1 | Orchestrator | High | N/A | State management, QA gates, retry logic |
| 2 | Research | Medium | 2,850 | 30+ primary sources, literature synthesis |
| 3 | Clinical Practice | Medium | 1,900 | Practice reality vs. guidelines analysis |
| 4 | Gap Analysis | Medium | 1,950 | Moore's level classification per gap |
| 5 | **Needs Assessment** | **High** | **3,100** | **Cold open + narrative threading** |
| 6 | Learning Objectives | Medium | N/A | Moore's distribution enforcement |
| 7 | Curriculum Design | Medium | 1,900 | AI features + innovation section |
| 8 | Research Protocol | Medium | Variable | IRB-ready outcomes research |
| 9 | Marketing Plan | Medium | Variable | Channel-level tactics with ROI |
| 10 | Grant Writer | High | Variable | Complete package assembly |
| 11 | Prose Quality | Medium | N/A | De-AI-ification enforcement |
| 12 | Compliance | Low | N/A | ACCME standards verification |

### Critical Agent: Needs Assessment (#5)

**Why This Agent First:**
1. Highest complexity writing agent (3,100+ word narrative)
2. Creates the "cold open" character that threads through entire grant
3. Strict prose requirements (80%+ narrative, zero AI tells)
4. If this works, simpler agents will work

**Special Requirements:**
- Must generate 50-100 word cold open (patient or clinician narrative hook)
- Character must reappear in 4+ sections throughout document
- Word count minimums strictly enforced per section
- No colons in titles (except cognitive dissonance cases)
- Banned AI patterns: em dashes, "furthermore," "delve into," etc.
- Minimum 80% flowing prose (≤20% bullets/tables)

---

## Phased Implementation

### Phase 1: Prove Core (2-3 weeks) ← **YOU ARE HERE**

**Goal:** Validate that a single high-complexity agent works end-to-end

**Specific Deliverables:**
- [ ] Needs Assessment Agent implemented using `create_agent()`
- [ ] Tools integrated:
  - Web search (for clinical data, statistics)
  - Document retrieval (research findings, clinical analysis, gap analysis)
  - Citation formatting (Vancouver style)
- [ ] LangSmith tracing operational (can view full execution trace)
- [ ] Test case: Process sample intake data → produce valid 3,100+ word output
- [ ] Prose Quality Agent validates output:
  - Zero AI patterns detected
  - Prose density ≥80%
  - Word counts met
  - Cold open present
  - Engagement score ≥8/10

**Success Criteria:**
- Single end-to-end run produces compliant output
- LangSmith trace shows all tool calls, reasoning, output
- Prose Quality Agent scores ≥8/10
- Output indistinguishable from human-written grant

**Why Phase 1 Matters:**
If we can't make ONE complex agent work perfectly, we can't make TWELVE work together. This phase proves the fundamental pattern.

### Phase 2: Full Orchestration (2-3 weeks)

**Goal:** Complete pipeline with all 12 agents

**Deliverables:**
- [ ] LangGraph StateGraph with all agents as nodes
- [ ] State schema implemented per specification
- [ ] Conditional routing (prose quality pass/fail loops)
- [ ] MemorySaver checkpointing for local development
- [ ] End-to-end test with complete intake form
- [ ] Cold open character tracked through narrative thread
- [ ] All quality gates functional

**Quality Gate:**
- Full grant package produced (all documents present)
- Compliance review passes
- Character counts exact on summaries (100, 250, 500, 1000 chars)
- Narrative thread verified (4+ character appearances)

### Phase 3: Production Infrastructure (2-4 weeks)

**Goal:** Production-ready deployment

**Deliverables:**
- [ ] PostgresSaver replaces MemorySaver
- [ ] Human review UI at designated gates
- [ ] Evaluation datasets created (≥10 examples per agent)
- [ ] LLM-as-judge evaluators configured
- [ ] Deployment to LangSmith Cloud or self-hosted
- [ ] Cost tracking and optimization
- [ ] Concurrent session handling

**Quality Gate:**
- Handles 10 concurrent grant requests
- Cost per grant <$X (TBD based on testing)
- 95%+ uptime over test period
- Human review UI functions at all gates

### Phase 4: Optimization (Ongoing)

**Goal:** Improve quality and efficiency

**Deliverables:**
- [ ] Online evaluation on production runs
- [ ] Prompt optimization based on evaluation data
- [ ] Parallel execution where graph topology allows
- [ ] Context eviction strategies for long-running agents
- [ ] A/B testing framework for prompt variations

---

## Immediate Next Steps

### Step 1: Implement Needs Assessment Agent (Start Here)

**What to Build:**

```python
# File: /home/claude/agents/needs_assessment.py

from langchain.agents import create_agent
from langchain.tools import Tool
from langsmith import traceable

# 1. Define tools
tools = [
    Tool(
        name="web_search",
        func=web_search_wrapper,
        description="Search for clinical data, statistics, epidemiology"
    ),
    Tool(
        name="retrieve_research",
        func=retrieve_research_findings,
        description="Get research agent output"
    ),
    Tool(
        name="retrieve_clinical",
        func=retrieve_clinical_analysis,
        description="Get clinical practice agent output"
    ),
    Tool(
        name="retrieve_gaps",
        func=retrieve_gap_analysis,
        description="Get gap analysis output"
    ),
    Tool(
        name="format_citation",
        func=format_vancouver_citation,
        description="Format citation in Vancouver style"
    )
]

# 2. Load system prompt from spec
system_prompt = load_prompt_from_spec("needs_assessment")

# 3. Create agent
needs_assessment_agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=tools,
    prompt=system_prompt,
)

# 4. Define node function
@traceable(name="needs_assessment_node")
def needs_assessment_node(state: CMEGrantState) -> CMEGrantState:
    """
    Generates needs assessment document with cold open.
    
    Inputs from state:
    - intake_data
    - research_report
    - clinical_analysis
    - gap_analysis
    
    Outputs to state:
    - needs_assessment
    - cold_open (extracted)
    """
    # Implementation here
    pass
```

**What to Test:**

```python
# File: /home/claude/tests/test_needs_assessment.py

def test_needs_assessment_basic():
    """Test that agent produces valid output"""
    state = create_test_state()
    result = needs_assessment_node(state)
    
    assert result["needs_assessment"] is not None
    assert len(result["needs_assessment"]) >= 3100 * 5  # ~3100 words × 5 chars/word
    assert result["cold_open"] is not None
    assert len(result["cold_open"]["text"]) >= 50
    
def test_needs_assessment_structure():
    """Test that output has required sections"""
    # Check for all required headers
    # Verify word counts per section
    # Confirm no AI patterns
    pass
```

### Step 2: Implement Prose Quality Agent

**Purpose:** Validate Needs Assessment output before proceeding

**What It Does:**
1. Scans for AI patterns (em dashes, "furthermore," etc.)
2. Calculates prose density (bullets/lists vs. paragraphs)
3. Verifies word counts per section
4. Checks for cold open and narrative thread
5. Scores engagement (1-10 scale)
6. Returns PASS/FAIL with specific feedback

### Step 3: Create Simple Test Harness

**Purpose:** Run agent + validator in loop

```python
# File: /home/claude/tests/integration_test.py

def test_needs_assessment_with_quality_check():
    """End-to-end test with quality validation"""
    
    # 1. Create test state
    state = create_test_state()
    
    # 2. Run needs assessment
    result = needs_assessment_node(state)
    
    # 3. Run prose quality check
    quality_result = prose_quality_node(result)
    
    # 4. Assert quality pass
    assert quality_result["prose_quality_report_1"]["overall_status"] == "PASS"
    assert quality_result["prose_quality_report_1"]["quality_scores"]["engagement"] >= 8
```

---

## Key Concepts to Understand

### 1. Cold Open (Narrative Hook)

**What:** 50-100 word opening scene that humanizes the clinical gap before statistics appear

**Example (Heart Failure):**
> Maria Chen, 58, sits in her cardiologist's waiting room for the third time this year. Each visit follows the same pattern: shortness of breath, a medication adjustment, a promise to do better with salt. What neither she nor her physician realizes is that her ejection fraction has dropped below 30% and she now qualifies for a device that could cut her mortality risk in half. Across the country, 380,000 patients like Maria are waiting for a conversation that never happens.

**Structure:**
1. The Moment (10-20 words): Drop into specific scene
2. The Person (15-30 words): Name, age, one humanizing detail
3. The Stakes (20-40 words): What's at risk
4. The Turn (10-20 words): Pivot to systemic scope

**Why It Matters:**
- Engages pharmaceutical grant reviewers emotionally
- Differentiates from academic/AI writing
- Character becomes narrative thread through entire grant

### 2. Moore's Expanded Outcomes Framework

**What:** Primary taxonomy for CME learning objectives (replaces Bloom's)

**Levels:**
- **Level 7:** Community/Population Health (rare for single activities)
- **Level 6:** Patient Health Outcomes
- **Level 5:** Performance (clinicians DO in practice)
- **Level 4:** Competence (clinicians CAN DO)
- **Level 3B:** Procedural Learning (HOW to do)
- **Level 3A:** Declarative Learning (WHAT - facts)
- **Level 2:** Satisfaction
- **Level 1:** Participation

**Distribution Example (Level 5 activity):**
- Level 5: 40-60% (Prescribe, Order, Initiate, Counsel)
- Level 4: 30-40% (Select, Differentiate, Assess)
- Level 3A/3B: 10-20% (Identify, Perform)

**Why It Matters:**
- CME accreditation requires outcome measurement
- Different levels = different measurement methods
- Target level drives entire curriculum design

### 3. Prose Density Requirement

**Rule:** Minimum 80% flowing prose, maximum 20% structural elements

**What Counts as Structural:**
- Bullet points
- Numbered lists
- Tables (data can stay, but narrative must surround it)
- Single-sentence paragraphs

**What Counts as Prose:**
- Paragraphs of 4+ sentences
- Data integrated into sentences
- Narrative transitions between sections

**Why It Matters:**
- AI defaults to bullets/lists (tells)
- Professional medical writing is narrative
- Grant reviewers skim; prose flows better

### 4. Banned AI Patterns

**Zero Tolerance List:**
- Em dashes (—) → use commas, colons, parentheses
- "Furthermore," "Moreover," "Additionally" as paragraph starters
- "Delve into" or "delve deeper"
- "In today's healthcare landscape"
- "It's important to note that"
- "It is worth noting"
- "This is particularly relevant because"
- Colons in titles (except true cognitive dissonance)
- Starting consecutive sentences with same word
- Rhetorical questions followed by immediate answers

**Why It Matters:**
- Grant reviewers read 50-100 grants per cycle
- They can spot AI writing instantly
- AI writing = rejected grant

---

## Critical Success Factors

### Factor 1: Prose Quality is Non-Negotiable

**The Standard:** Output must be indistinguishable from experienced medical writer

**How to Verify:**
1. Run through Prose Quality Agent (automated)
2. Human review of first paragraph (engagement test)
3. Word count verification (minimums strictly enforced)
4. AI pattern scan (zero tolerance)

**What Failure Looks Like:**
- Grant reviewer says "this reads like ChatGPT"
- Bullet points dominate narrative sections
- Em dashes, "furthermore," "delve into" present
- Generic colons in titles ("Topic: Subtitle")
- Passive voice >30%

### Factor 2: Cold Open Must Work

**The Standard:** Character introduced in cold open appears 4+ times throughout grant

**Checkpoints:**
1. Cold open itself (50-100 words, no statistics)
2. Disease State Overview: "Maria Chen is one of..."
3. Gap descriptions: "In Maria's case..."
4. Educational Rationale: "Had Maria's cardiologist..."
5. Expected Outcomes: "Success means patients like Maria..."

**What Failure Looks Like:**
- Character introduced but never mentioned again
- Forced/awkward character references
- Character appears in cold open only
- Multiple different characters introduced (should be ONE)

### Factor 3: Moore's Framework Must Be Primary

**The Standard:** All learning objectives use Moore's levels, distribution matches target

**Verification:**
- Target Level 5 activity has 40-60% Level 5 objectives
- Every objective has measurement method aligned with level
- No objectives use only Bloom's taxonomy
- Action verbs match Moore's level

**What Failure Looks Like:**
- "Understand the mechanism..." (passive, unmeasurable)
- "Appreciate the importance..." (not an action)
- Level 5 activity with all Level 3 objectives (knowledge only)
- Measurement methods don't match claimed levels

### Factor 4: LangSmith Tracing Must Be Complete

**The Standard:** Every agent execution fully traceable in LangSmith

**What to Trace:**
- All tool calls (web search, document retrieval, citations)
- Reasoning steps
- Input state
- Output state
- Errors/retries
- Token usage
- Latency

**What Failure Looks Like:**
- Agent succeeds but no trace visible
- Trace shows "black box" (no intermediate steps)
- Tool calls not logged
- Can't debug failures

---

## Common Pitfalls to Avoid

### Pitfall 1: Reading the Entire Spec Start-to-Finish

**Problem:** 7,788 lines is too long to digest sequentially

**Solution:**
- Jump to specific agent section when implementing that agent
- Read shared resources (Style Guide, Moore's Framework) for all writing agents
- Use spec as reference, not tutorial

### Pitfall 2: Skipping LangSmith Setup

**Problem:** Can't debug agent failures without tracing

**Solution:**
- Set up LangSmith API key first
- Decorate all agent functions with `@traceable`
- Verify traces appear in LangSmith UI before proceeding
- Use tracing to validate tool calls

### Pitfall 3: Implementing All 12 Agents Before Testing

**Problem:** If pattern is wrong, you have to fix 12 agents

**Solution:**
- Implement ONE agent completely (Needs Assessment)
- Test until it works perfectly
- Use proven pattern for remaining 11 agents

### Pitfall 4: Ignoring Prose Quality Requirements

**Problem:** Output reads like AI, grant gets rejected

**Solution:**
- Prose Quality Agent is not optional
- Run it on every writing agent output
- Don't proceed to next phase if quality fails
- Human review the "hooks" (first paragraphs)

### Pitfall 5: Treating Moore's Framework as Optional

**Problem:** Objectives don't match target outcome level

**Solution:**
- Moore's is PRIMARY taxonomy (not Bloom's)
- Distribution percentages are requirements, not suggestions
- Every objective must be measurable at stated level
- Measurement methods must align with Moore's level

---

## Tools and Resources

### Development Tools

| Tool | Purpose | Setup Required |
|------|---------|----------------|
| **LangGraph** | Agent orchestration | `pip install langgraph` |
| **LangSmith** | Observability, tracing | API key, environment vars |
| **LangChain** | Agent creation, tools | `pip install langchain` |
| **Anthropic SDK** | Claude API access | API key |
| **PostgreSQL** | State persistence (Phase 3) | Docker container or cloud |

### Reference Materials

| Resource | Location | Purpose |
|----------|----------|---------|
| LangGraph Docs | https://langchain-ai.github.io/langgraph/ | Orchestration patterns |
| LangSmith Docs | https://docs.smith.langchain.com/ | Tracing, evaluation |
| ACCME Standards | https://www.accme.org/accreditation-rules | Compliance verification |
| Moore's Framework | Spec Section: Shared Resources | Objective design |
| Style Guide | Spec Section: Shared Resources | Prose requirements |

### Sample Data for Testing

**Minimal Intake Form (for testing):**
```yaml
A_Topic:
  topic_title: "Optimizing Heart Failure Management in Primary Care"
  topic_description: "Primary care physicians face unprecedented complexity..."

B_Therapeutic_Area:
  therapeutic_areas: ["Cardiovascular"]

C_Target_Audience:
  specialties: ["Internal Medicine (IM)", "Family Medicine (FM)"]
  professions: ["Physician (MD/DO)", "Nurse Practitioner (NP)"]

D_Research_Parameters:
  date_range_start: 2021
  date_range_end: 2025
  geographic_scope: "US Only"

E_Product_Configuration:
  product_type: "On-demand Online Webcast"
  product_quantity: 1
  credit_hours: 1.0
  curriculum_start: "2026-04-01"
  curriculum_end: "2027-03-31"

F_Funding:
  budget_range: "$100,000 - $250,000"

H_Compliance:
  accreditor: "ACCME (Physician)"
  commercial_support: true

I_Outcomes_Framework:
  target_moore_level: 5
  follow_up_intervals: ["Immediate", "30-day", "90-day"]
```

---

## Repository Structure (Planned)

```
dhg-cme-grants/
├── docker-compose.yml
├── .env
├── README.md
│
├── shared/                          # Shared resources for all agents
│   ├── style_guide.md
│   ├── moores_framework.md
│   ├── cold_open_framework.md
│   ├── audience_context.md
│   └── schemas/
│       ├── intake_form.yaml
│       └── state_schema.py
│
├── agents/                          # Individual agent implementations
│   ├── orchestrator/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── agent.py
│   │   └── prompts.py
│   ├── needs_assessment/            ← START HERE
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── agent.py
│   │   ├── prompts.py
│   │   └── tools.py
│   ├── prose_quality/               ← SECOND
│   │   └── ...
│   └── [10 more agents]/
│
├── graph/                           # LangGraph orchestration
│   ├── state.py                     # State schema definition
│   ├── workflow.py                  # Graph definition
│   └── checkpointer.py              # State persistence
│
├── tests/                           # Test suite
│   ├── unit/
│   │   └── test_needs_assessment.py
│   ├── integration/
│   │   └── test_full_pipeline.py
│   ├── fixtures/
│   │   └── sample_intake.yaml
│   └── evaluations/
│       └── needs_assessment_eval.py
│
├── api/                             # API gateway
│   ├── Dockerfile
│   ├── requirements.txt
│   └── gateway.py
│
├── web/                             # Intake form UI
│   ├── Dockerfile
│   └── intake_form/
│
└── data/                            # Reference data, templates
    ├── templates/
    └── reference/
```

---

## Quick Start Commands (Phase 1)

**Set Up Environment:**
```bash
# Clone or create repository
mkdir dhg-cme-grants && cd dhg-cme-grants

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install langgraph langsmith langchain anthropic

# Set environment variables
export ANTHROPIC_API_KEY="your-key-here"
export LANGSMITH_API_KEY="your-key-here"
export LANGSMITH_PROJECT="dhg-cme-grants-dev"
```

**Create First Agent:**
```bash
# Create directory structure
mkdir -p agents/needs_assessment
cd agents/needs_assessment

# Create agent file (use template from spec)
touch agent.py prompts.py tools.py

# Create test
mkdir -p ../../tests/unit
touch ../../tests/unit/test_needs_assessment.py
```

**Run First Test:**
```bash
# From repository root
python -m pytest tests/unit/test_needs_assessment.py -v

# View trace in LangSmith
# Visit https://smith.langchain.com/
```

---

## Decision Log

| Date | Decision | Rationale | Status |
|------|----------|-----------|--------|
| 2026-01-29 | Use LangGraph StateGraph | Explicit control, production-ready | Locked |
| 2026-01-29 | Start with Needs Assessment Agent | Highest complexity, proves pattern | Locked |
| 2026-01-29 | LangSmith for observability | Best-in-class tracing, evaluation | Locked |
| 2026-01-29 | Skip Deep Agents initially | Convenience only, not proven at scale | Locked |
| 2026-01-29 | Offline evaluation first | Easier to debug, iterate | Locked |
| 2026-01-29 | MemorySaver → PostgresSaver | Validate locally, then production | Locked |
| 2026-01-31 | Moore's Framework is primary | CME standard, better than Bloom's | Locked |
| 2026-01-31 | 80% prose density minimum | Professional writing standard | Locked |
| 2026-01-31 | Zero tolerance for AI patterns | Grant reviewer detection avoidance | Locked |

---

## Open Questions

| Question | Status | Priority | Notes |
|----------|--------|----------|-------|
| Best RAG approach for research agent | Open | Medium | Options: vector DB, structured retrieval |
| Citation management tool | Open | Medium | Vancouver style formatting |
| Human review UI framework | Open | Low | Phase 3 concern |
| Cost estimation per grant | Open | High | Test in Phase 1 with single agent |
| Parallel execution strategy | Open | Low | Phase 4 optimization |
| LangGraph Assistants API applicability | Open | Medium | Research when available |

---

## Success Metrics

### Phase 1 Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Single agent execution success | 100% | Test passes |
| Prose quality score | ≥8/10 | Prose Quality Agent |
| Word count compliance | 100% | Automated check |
| LangSmith trace completeness | 100% | Visual verification |
| AI pattern count | 0 | Prose Quality Agent |
| Cold open generation | 100% | Present + thread verified |

### Phase 2 Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| End-to-end pipeline success | 100% | Full grant package produced |
| Compliance pass rate | 100% | Compliance Agent |
| Narrative thread completeness | 100% | 4+ character appearances |
| Character count accuracy | 100% | Exact matches on summaries |

### Phase 3 Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Concurrent session handling | 10+ | Load testing |
| Cost per grant | TBD | Token tracking |
| Time to draft | <5 days | End-to-end timing |
| Human revision rate | <20% | Manual review needed |

### Production Metrics (Phase 4)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Grant approval rate | >60% | Funded/submitted |
| Prose quality (production) | >8/10 | Prose Quality Agent |
| Compliance pass (production) | >95% | First-pass approval |
| User satisfaction | >4/5 | Survey |

---

## For Your Next Chat Session

### What to Say to Claude:

```
I'm continuing work on the DHG CME Grant Multi-Agent System.

CONTEXT:
- Project spec: /mnt/project/DHG_CME_Grant_MultiAgent_System_v1.md
- Handoff brief: /mnt/user-data/outputs/DHG_CME_Grant_Master_Handoff_Brief.md
- Current phase: Phase 1 (single agent validation)
- Current task: Implement Needs Assessment Agent

WHAT I NEED:
[State your specific task]

Before we start, please:
1. Confirm you've read the handoff brief
2. Identify which section of the spec is relevant
3. Outline your approach
```

### What Claude Should Do:

1. **Read the Handoff Brief** (this document)
2. **Read relevant spec section** (don't read all 7,788 lines)
3. **Confirm understanding** of requirements
4. **Propose approach** before coding
5. **Create deliverables** in working directory
6. **Move to outputs** when ready
7. **Update handoff brief** if decisions made

---

## Stephen's Preferences (Refresher)

### Communication Style
- Teaching-oriented explanations with depth
- Business context for technical decisions
- Clear rationale for recommendations
- Structured responses with clear sections
- Prose over bullet points (unless listing)

### Technical Approach
- Modular, scalable solutions
- Comprehensive documentation
- Research-driven decisions
- Persistent task management
- Quality gates at each phase

### Working Style
- Slash commands for task management: `/plan`, `/research`, `/status`, `/done`
- Detailed project instruction documents
- Eliminate session overhead
- Systematic, research-driven workflows

---

## Contact & Support

**Project Owner:** Stephen Webber  
**Organization:** Digital Harmony Group  
**Collaboration Partner:** Claude (Anthropic)  
**Coding Agent:** Antigravity (planned)

**Key Resources:**
- GitHub Repository: dhgaifactory3.5 (sdnydude/dhgaifactory3.5)
- LangSmith Project: dhg-cme-grants-dev
- Specification: /mnt/project/DHG_CME_Grant_MultiAgent_System_v1.md

---

## Document Control

**Version:** 1.0  
**Created:** January 31, 2026  
**Last Updated:** January 31, 2026  
**Status:** Active

**Revision History:**
- v1.0 (2026-01-31): Initial handoff brief created

**Next Review:** After Phase 1 completion

---

*End of Master Handoff Brief*

**Quick Reference:** Phase 1 Start → Implement Needs Assessment Agent → Test with Prose Quality → Verify in LangSmith → Proceed to Phase 2
