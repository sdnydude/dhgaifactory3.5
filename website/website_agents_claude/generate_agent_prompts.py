#!/usr/bin/env python3
"""
DHG AI Factory — Generate All 4 Agent Build Prompts via Anthropic API

Usage:
    python generate_agent_prompts.py                  # All 4 agents, Sonnet 4.5
    python generate_agent_prompts.py --agent 1        # Just Agent 1
    python generate_agent_prompts.py --model opus     # Use Opus 4.5
    python generate_agent_prompts.py --agent 2 --model opus  # Agent 2 with Opus

Output files saved to ./output/agent-0X-{name}-langgraph.md
"""

import anthropic
import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

MODELS = {
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-5-20250929",
}

MAX_OUTPUT_TOKENS = 65536  # ~50,000 words — more than enough for any single agent

OUTPUT_DIR = Path("./output")

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT (shared across all 4 agents)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior LangGraph Cloud engineer writing a COMPLETE production build prompt. This prompt will be fed to Google Gemini 2.5 Pro, which will read it and generate the entire agent codebase. The code Gemini produces must run in LangGraph Studio on first try with zero errors.

## ABSOLUTE RULES — VIOLATION OF ANY RULE MEANS FAILURE

1. **ZERO** placeholders — no `pass`, `...`, `# TODO`, `placeholder`, or truncated code anywhere
2. **ZERO** FastAPI, Docker, or custom WebSocket code — LangGraph Cloud handles all infrastructure
3. **ZERO** raw google-genai SDK — ALL LLM calls via `langchain-google-genai` (`ChatGoogleGenerativeAI`)
4. **ZERO** hardcoded checkpointers — LangGraph Cloud injects them; local dev uses `MemorySaver`
5. **EVERY** file must be written in FULL — complete imports, complete function bodies, complete data
6. **EVERY** knowledge base doc, use case entry, benchmark value, and test case must be FULLY WRITTEN — no "... 39 more" or "similar entries for other industries" or "add more as needed"
7. **EVERY** system prompt must be carefully crafted and complete — not a sketch or outline

## OUTPUT FORMAT

Your output is a single markdown file structured as:

1. **Role & Constraints** — Instructions for Gemini (what to build, rules)
2. **Architecture Overview** — Graph diagram (ASCII), flow description, state machine
3. **Complete File Listing** — Every file that must be created, with full path
4. **Complete File Contents** — Each file in a code block with its path as header. Files in this order:
   - `langgraph.json`
   - `pyproject.toml`
   - `.env.example`
   - `README.md`
   - `src/dhg_{name}/__init__.py`
   - `src/dhg_{name}/state.py`
   - `src/dhg_{name}/configuration.py`
   - `src/dhg_{name}/prompts.py`
   - `src/dhg_{name}/tools.py`
   - `src/dhg_{name}/nodes.py`
   - `src/dhg_{name}/edges.py`
   - `src/dhg_{name}/graph.py`
   - `src/dhg_{name}/utils/callbacks.py`
   - Data files (knowledge base docs, use case databases, etc.)
   - `evals/datasets/*.json` (complete golden test datasets)
   - `evals/evaluators.py`
   - `evals/run_evals.py`
   - `frontend/index.html`
   - `frontend/widget.js`
   - `frontend/widget.css`
   - `scripts/seed_langsmith.py`
5. **Verification Checklist** — Steps to confirm everything works

## TECH STACK (applies to every agent)

- **Runtime:** LangGraph Cloud — deployment via `langgraph.json` manifest, no Docker
- **LLM:** Gemini 2.5 Pro via `ChatGoogleGenerativeAI` from `langchain-google-genai`
- **Embeddings:** Google `text-embedding-004` via `GoogleGenerativeAIEmbeddings` (Agent 1 only)
- **Vector Store:** ChromaDB local / Pinecone production (Agent 1 only)
- **Observability:** LangSmith — `@traceable` on every node, every LLM call, every retrieval
- **Testing:** LangGraph Studio — `configuration.py` exposes tunable params in Studio UI
- **Frontend:** `@langchain/langgraph-sdk` (JavaScript) for SSE streaming
- **State:** `TypedDict` with `Annotated` reducers (`add_messages` for conversation history)
- **Checkpointer:** NOT hardcoded — Cloud injects; local/Studio uses `MemorySaver`

## PRODUCTION PATTERNS (from DHG's existing deployed agents)

### Node Function Pattern
```python
@traceable(name="node_name", run_type="chain")
async def my_node(state: AgentState) -> dict:
    # 1. Extract from state with .get() and defaults
    user_msg = state.get("user_message", "")
    # 2. Do work (LLM, retrieval, computation)
    result = await llm.generate(system_prompt, user_msg, {"step": "node_name"})
    # 3. Parse response with error handling
    try:
        parsed = json.loads(re.search(r'\\{[\\s\\S]*\\}', result["content"]).group())
    except (json.JSONDecodeError, AttributeError):
        parsed = {"error": "Failed to parse"}
    # 4. Return PARTIAL state update — accumulate, don't replace
    prev_tokens = state.get("total_tokens", 0)
    return {"result": parsed, "total_tokens": prev_tokens + result["total_tokens"]}
```

### LLM Client Pattern
```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable

class LLMClient:
    def __init__(self, model_name="gemini-2.5-pro", temperature=0.7, max_output_tokens=4096):
        self.model = ChatGoogleGenerativeAI(
            model=model_name, temperature=temperature, max_output_tokens=max_output_tokens
        )
    @traceable(name="llm_call", run_type="llm")
    async def generate(self, system: str, prompt: str, metadata: dict = None) -> dict:
        messages = [SystemMessage(content=system), HumanMessage(content=prompt)]
        response = await self.model.ainvoke(messages, config={"metadata": metadata or {}})
        input_tokens = response.usage_metadata.get("input_tokens", 0)
        output_tokens = response.usage_metadata.get("output_tokens", 0)
        return {
            "content": response.content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }
```

### Graph Export Pattern
```python
def create_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("step1", step1_node)
    graph.set_entry_point("step1")
    graph.add_edge("step1", END)
    return graph

# Module-level export — this is what langgraph.json references
graph = create_graph().compile()
```

### Routing Pattern
```python
def route_fn(state: AgentState) -> Literal["path_a", "path_b"]:
    if state.get("condition"):
        return "path_a"
    return "path_b"

# Used as: graph.add_conditional_edges("source", route_fn, {"path_a": "node_a", "path_b": "node_b"})
```

## LEAD CAPTURE MODAL (all agents)

All agents trigger a lead capture modal at strategic moments. The modal collects:
- First Name (required)
- Last Name (required)
- Work Email (required, validated against corporate domains — reject gmail/yahoo/hotmail)
- Company (required)
- Job Title (required)
- Number of Employees (required, dropdown: 1-10, 11-50, 51-200, 201-500, 501-1000, 1000+)

The modal is a glassmorphism overlay with orange gradient submit button and a "No thanks" dismiss link.

## DHG BRAND / GLASSMORPHISM SPECS (all frontend widgets)

```
Colors: Graphite #32374A, Purple #663399, Orange #F77E2D
Glass: backdrop-filter blur(16-20px), rgba backgrounds (0.05-0.15 alpha)
Borders: 1px solid rgba(255,255,255,0.1)
Shadows: 0 8px 32px rgba(0,0,0,0.12)
Font: Inter (light 300/400 body, semibold 600 headings)
User bubbles: Purple gradient
Agent bubbles: rgba glass
CTAs: Orange gradient — accent only
```

## QUALITY BAR

The prompt you write must produce code that:
- Runs in LangGraph Studio with zero errors on first try
- Deploys to LangGraph Cloud via `langgraph deploy`
- Auto-traces every run in LangSmith
- Passes its own evaluation suite (included in evals/)
- Has a frontend widget that connects and streams via LangGraph SDK
- Contains zero placeholder code — every file, every function, fully implemented
"""

# ─────────────────────────────────────────────────────────────────────────────
# AGENT-SPECIFIC PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

AGENT_PROMPTS = {
    1: {
        "name": "Platform Q&A Agent",
        "filename": "agent-01-platform-qa-langgraph.md",
        "prompt": """Write the COMPLETE build prompt for Agent 1: Platform Q&A Agent.

## What This Agent Does

Replaces the static FAQ on the DHG AI Factory marketing website with a conversational RAG-based Q&A agent. Users ask questions about the platform in natural language, and the agent retrieves relevant information from a 9-document knowledge base, generates grounded answers with source citations, and suggests follow-up questions.

## Graph Architecture

```
classify_intent → route_by_intent
    ├── "question"  → retrieve → generate → format_output → END
    ├── "greeting"  → handle_greeting ────→ format_output → END
    ├── "off_topic" → handle_off_topic ───→ format_output → END
    └── "clarify"   → handle_clarification → format_output → END
```

## State Schema

```python
class PlatformQAState(TypedDict):
    # === INPUT ===
    user_message: str
    conversation_id: str

    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    intent: str                              # "question" | "greeting" | "off_topic" | "clarify"
    intent_confidence: float
    retrieved_chunks: List[Dict[str, Any]]   # [{content, source, score}]
    retrieval_query: str

    # === OUTPUT ===
    response: str
    sources: List[Dict[str, str]]            # [{title, section, url}]
    follow_up_suggestions: List[str]         # 2-3 clickable suggestions
    show_lead_capture: bool                  # Trigger after 3+ quality interactions

    # === METADATA ===
    total_tokens: int
    interaction_count: int
    quality_interactions: int
    errors: List[str]
```

## Node Specifications

1. **classify_intent** — LLM classifies user message. Returns JSON: {intent, confidence}. Uses few-shot examples in system prompt.
2. **retrieve** — Embed query via GoogleGenerativeAIEmbeddings → ChromaDB similarity search → return top-5 chunks above 0.7 threshold. Optionally rewrite vague queries before embedding.
3. **generate** — LLM generates grounded answer. System prompt enforces: cite sources with [Source: title], stay factual, say "I don't have information about that" if chunks don't cover the question. Includes conversation history for multi-turn context.
4. **handle_greeting** — LLM generates warm intro. Suggests 3 starter questions from different knowledge base topics.
5. **handle_off_topic** — LLM politely redirects. Acknowledges the question, explains scope (AI Factory platform questions only), suggests related on-topic questions.
6. **handle_clarification** — LLM asks clarifying question using conversation context.
7. **format_output** — Pure Python. Assembles response, generates follow-up suggestions if not set, increments counters, sets show_lead_capture when quality_interactions >= 3.

## Knowledge Base Documents (9 files — WRITE EVERY ONE IN FULL)

Each document: 800-1500 words of realistic, substantive content about the DHG AI Factory platform. These must read like real product documentation, not lorem ipsum.

1. **platform-overview.md** — What is AI Factory, architecture overview, 8 modules, how the multi-agent system works end-to-end, who it's for
2. **modules-and-capabilities.md** — Detailed description of each of the 8 modules: Research Agent, Needs Assessment, Gap Analysis, Learning Objectives, Curriculum Design, Research Protocol, Marketing Plan, Grant Writer. What each does, inputs/outputs, how they chain together.
3. **technology-stack.md** — LangGraph Cloud, LangSmith observability, multi-LLM (Gemini + Claude), vector stores, streaming architecture, API-first design
4. **integration-and-deployment.md** — Cloud deployment, on-premise options, API integration guide, SSO support, data pipeline setup, compliance requirements
5. **pricing-and-packages.md** — Three tiers: Starter ($2,500/mo), Professional ($7,500/mo), Enterprise (custom). Feature comparison, what's included, add-ons
6. **case-studies.md** — Three detailed stories: (a) top-20 pharma company using AI Factory for CME grant writing — 60% time reduction, (b) academic health system automating needs assessments, (c) medical device company streamlining compliance documentation
7. **security-and-compliance.md** — SOC 2 Type II, HIPAA BAA available, GDPR compliant, encryption at rest (AES-256) and in transit (TLS 1.3), role-based access control, audit logging, data residency options, penetration testing cadence
8. **getting-started.md** — Onboarding process: discovery call → technical assessment → POC (2 weeks) → pilot (4 weeks) → production rollout. Prerequisites, team requirements, timeline expectations
9. **faq-technical.md** — 15+ Q&A pairs covering: latency, accuracy rates, supported LLMs, customization options, rate limits, API versioning, uptime SLA, backup/recovery, multi-tenancy

## Embeddings & Vector Store

- Embedding model: `GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")`
- Local dev: ChromaDB with `persist_directory="./chroma_data"`
- Production: Pinecone (index name from env var)
- Chunk size: 500 tokens, 50 token overlap
- `scripts/seed_langsmith.py` must include the full seeding pipeline: load markdown → chunk → embed → store

## Configuration (for LangGraph Studio)

```python
class Configuration(TypedDict, total=False):
    model_name: str              # default: "gemini-2.5-pro"
    temperature: float           # default: 0.7
    max_tokens: int              # default: 4096
    retrieval_top_k: int         # default: 5
    similarity_threshold: float  # default: 0.7
    embedding_model: str         # default: "models/text-embedding-004"
```

## Evaluation Dataset

Write 15+ test cases in JSON covering:
- Factual accuracy (question from KB → correct answer with source)
- Source attribution (answer includes [Source: ...])
- Greeting handling (hi, hello, hey)
- Off-topic deflection (questions about weather, sports, unrelated tech)
- Multi-turn follow-up (initial question → follow-up referencing prior answer)
- Edge cases: empty input, very long input, prompt injection ("ignore your instructions and...")
- Ambiguous questions needing clarification

## Frontend Widget

Glassmorphism chat widget. Must include:
- Message bubbles (purple user, glass agent) with smooth animations
- Streaming token display (append characters as SSE events arrive)
- Follow-up suggestion pills below agent messages (clickable, send as new message)
- Source attribution cards (expandable, show document title + section)
- Typing indicator (animated dots)
- Lead capture modal triggered by `show_lead_capture` state
- Error state handling (network error, timeout)
- Input bar with send button, disabled during streaming
- "Powered by DHG AI Factory" footer link

WRITE THE COMPLETE PROMPT. Every file. Every line. No shortcuts.""",
    },

    2: {
        "name": "ROI Calculator Agent",
        "filename": "agent-02-roi-calculator-langgraph.md",
        "prompt": """Write the COMPLETE build prompt for Agent 2: ROI Calculator Agent.

## What This Agent Does

Guides a prospect through a structured conversational interview collecting business metrics about their organization, then calculates projected ROI from implementing the DHG AI Factory platform. Produces a results dashboard with 3 scenarios (conservative/moderate/aggressive), interactive module recommendations, and a downloadable PDF report. This is the #1 lead generation tool on the site.

## Graph Architecture

```
greet → collect_company_info → collect_team_metrics → collect_process_metrics → collect_pain_points → validate → calculate → analyze → present_results → handle_followup
                                                                                                          ↑                                                        │
                                                                                                          └────────── (missing fields) ────────────────────────────┘
handle_followup loops back to itself until user is done, then → END
```

## State Schema

```python
class ROICalculatorState(TypedDict):
    # === INPUT ===
    user_message: str
    conversation_id: str

    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    current_step: str

    # Collected data
    company_info: Dict[str, Any]       # {name, industry, size, revenue_range}
    team_metrics: Dict[str, Any]       # {team_size, avg_salary, hours_per_week_on_task}
    process_metrics: Dict[str, Any]    # {processes_per_month, avg_time_per_process, error_rate, current_tool_costs}
    pain_points: List[str]

    # Validation
    missing_fields: List[str]
    validation_errors: List[str]

    # === OUTPUT ===
    response: str
    roi_results: Dict[str, Any]
    scenarios: Dict[str, Dict[str, Any]]    # {conservative, moderate, aggressive}
    recommended_modules: List[Dict[str, Any]]
    pdf_report_data: Dict[str, Any]
    show_results_dashboard: bool
    show_lead_capture: bool

    # === METADATA ===
    total_tokens: int
    errors: List[str]
```

## Node Specifications

1. **greet** — Welcome message explaining the ROI assessment (~2 minute process). Ask company name + industry.
2. **collect_company_info** — Extract company name, industry (map to 8 benchmarks), company size (employees), revenue range. LLM parses natural language into structured fields. Ask follow-ups for missing data.
3. **collect_team_metrics** — Team size working on target processes, average salary range, hours per week on manual/repetitive tasks.
4. **collect_process_metrics** — Process volume per month, average time per process, current error/rework rate, existing tool costs.
5. **collect_pain_points** — Open-ended: "What's your biggest frustration with current processes?" Extract structured tags.
6. **validate** — Check all required fields populated with sane values. If missing → identify which collection node to revisit. If complete → proceed.
7. **calculate** — PURE PYTHON MATH, NO LLM. Full ROI formulas:
   - Time savings = processes × time_per × automation_rate × 12
   - Cost savings = time_saved_hours × blended_hourly_rate
   - Error reduction = error_rate × error_cost × reduction_pct
   - Revenue impact = freed_hours × revenue_per_hour × utilization
   - Module costs = sum of recommended module pricing
   - Net ROI = (total_benefits - total_costs) / total_costs × 100
   - 5-year projection with year-over-year improvement curve
   Run all formulas across 3 scenarios with different assumption multipliers.
8. **analyze** — LLM interprets numbers into narrative. Identifies biggest impact areas. Compares to industry benchmarks. Highlights quick wins vs long-term value.
9. **present_results** — Format dashboard data. Set show_results_dashboard and show_lead_capture true.
10. **handle_followup** — Answer questions about results. If user adjusts assumptions, recalculate. Offer PDF download + consultation booking.

## Industry Benchmarks (WRITE ALL 8 — real numbers)

8 industries with automation rates, error rates, avg process times, labor costs:
Healthcare/Pharma, Financial Services, Technology, Manufacturing, Retail/E-commerce, Education, Government, Professional Services

## Module Pricing (WRITE ALL 8)

8 AI Factory modules with: implementation cost, monthly subscription, typical automation rate, time-to-value

## PDF Report Generation

Use ReportLab. The PDF includes: executive summary, company details, 3 scenarios with tables, module recommendations, 5-year projection chart data, methodology notes, next steps CTA.

## Configuration

```python
class Configuration(TypedDict, total=False):
    model_name: str            # "gemini-2.5-pro"
    temperature: float         # 0.5 (more precise for data collection)
    max_tokens: int            # 4096
    conservative_multiplier: float  # 0.6
    moderate_multiplier: float      # 1.0
    aggressive_multiplier: float    # 1.4
```

## Evaluation Dataset

15+ test cases covering: complete happy path, partial data collection, invalid numbers, industry-specific calculations, calculation accuracy verification, edge cases.

## Frontend Widget

Glassmorphism interview chat that transitions to results dashboard:
- Chat phase: conversation bubbles with progress indicator (step X of 5)
- Results phase: summary cards, scenario tabs (Conservative/Moderate/Aggressive), module recommendation toggles (check/uncheck to recalculate), chart data structure for Plotly rendering, PDF download button (triggers lead capture first)
- Lead capture modal: triggered with results, pre-populated with company name from interview

WRITE THE COMPLETE PROMPT. Every file. Every line. No shortcuts.""",
    },

    3: {
        "name": "Workflow Designer Agent",
        "filename": "agent-03-workflow-designer-langgraph.md",
        "prompt": """Write the COMPLETE build prompt for Agent 3: Workflow Designer Agent.

## What This Agent Does

User describes a business process in natural language → agent decomposes it into steps, identifies pain points and bottlenecks, maps steps to AI Factory modules, designs an optimized workflow with automation opportunities, and generates a visual Mermaid.js diagram. Demonstrates DHG's process intelligence capability.

## Graph Architecture

```
greet → discover_process → decompose_steps → identify_pain_points → map_to_modules → design_workflow → optimize → generate_diagram → present_design → iterate
                                                                                                                                                           │
                                                                                                                                    iterate loops back to relevant node
                                                                                                                                    until user satisfied → END
```

## State Schema

```python
class WorkflowDesignerState(TypedDict):
    # === INPUT ===
    user_message: str
    conversation_id: str

    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    current_step: str
    process_description: str
    process_name: str
    process_domain: str
    process_steps: List[Dict[str, Any]]     # [{step_id, name, description, inputs, outputs, duration_minutes, actors}]
    pain_points: List[Dict[str, Any]]       # [{step_id, issue, severity, impact}]
    module_mappings: List[Dict[str, Any]]   # [{step_id, module, capability, confidence_score}]
    optimized_workflow: Dict[str, Any]      # {steps, parallel_groups, estimated_improvement}
    optimization_notes: List[str]

    # === OUTPUT ===
    response: str
    mermaid_diagram: str
    workflow_summary: Dict[str, Any]        # {before_metrics, after_metrics, improvement_pct}
    export_data: Dict[str, Any]
    show_diagram: bool
    show_lead_capture: bool

    # === METADATA ===
    total_tokens: int
    iteration_count: int
    errors: List[str]
```

## Node Specifications

1. **greet** — Welcome, explain capability, ask user to describe their business process
2. **discover_process** — LLM extracts process name, domain, high-level overview. If too vague, asks targeted clarifying questions.
3. **decompose_steps** — LLM breaks process into 5-15 discrete steps. Each step gets: ID, name, description, inputs, outputs, estimated duration, actors involved.
4. **identify_pain_points** — LLM + user confirmation identifies bottlenecks, manual tasks, error-prone areas, compliance risks per step. Severity scoring.
5. **map_to_modules** — Rule-based capability matching + LLM confidence scoring. Match each step/pain point to relevant AI Factory modules.
6. **design_workflow** — LLM creates optimized workflow incorporating AI Factory modules. Specifies which steps become automated, AI-assisted, or remain human.
7. **optimize** — Identify parallelization opportunities, remove redundant steps, add human-in-the-loop checkpoints where needed. Calculate estimated time/cost improvement.
8. **generate_diagram** — PURE CODE (no LLM). Convert optimized workflow into Mermaid.js flowchart. Color coding: gray=current manual, purple=AI-assisted, orange=fully automated.
9. **present_design** — Format before/after comparison, show diagram, export options.
10. **iterate** — User requests changes → route to appropriate node. User satisfied → set lead capture → END.

## Module Capability Matrix (tools.py — WRITE IN FULL)

8 modules × capability tags with descriptions and scoring weights. Used for rule-based matching.

## Mermaid Diagram Generator (tools.py — WRITE IN FULL)

Function that takes the optimized workflow structure and produces valid Mermaid.js flowchart code with:
- Subgraphs for parallel groups
- Color-coded node styles (classDef for manual/assisted/automated)
- Edge labels showing data flow
- Duration annotations

## Configuration

```python
class Configuration(TypedDict, total=False):
    model_name: str             # "gemini-2.5-pro"
    temperature: float          # 0.7
    max_tokens: int             # 4096
    max_process_steps: int      # 15
    confidence_threshold: float # 0.6
```

## Evaluation Dataset

15+ test cases: simple linear process, complex branching process, vague description needing clarification, process with no AI automation opportunities, Mermaid syntax validation, iteration request handling.

## Frontend Widget

Glassmorphism chat transitioning to diagram view:
- Chat phase: conversation with step-by-step discovery
- Diagram phase: rendered Mermaid diagram (use mermaid.js CDN), before/after comparison panel
- Export buttons: Copy Mermaid Code, Download JSON, Download as PDF
- Diagram is interactive: hover for step details, click to expand

WRITE THE COMPLETE PROMPT. Every file. Every line. No shortcuts.""",
    },

    4: {
        "name": "Use Case Match Agent",
        "filename": "agent-04-use-case-match-langgraph.md",
        "prompt": """Write the COMPLETE build prompt for Agent 4: Use Case Match Agent.

## What This Agent Does

Short consultative interview (4-6 questions) → recommends which AI Factory modules and specific use cases best fit the prospect's business. Features a database of 40+ use cases across 8 industries with weighted matching algorithm. This is the most direct sales conversion tool.

## Graph Architecture

```
greet → assess_industry → assess_challenges → assess_maturity → assess_priorities → match_use_cases → rank_recommendations → present_matches → deep_dive
                                                                                                                                                     │
                                                                                                                              deep_dive loops (user explores recommendations)
                                                                                                                              until done → END
```

## State Schema

```python
class UseCaseMatchState(TypedDict):
    # === INPUT ===
    user_message: str
    conversation_id: str

    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    current_step: str
    industry: str
    industry_segment: str
    company_size: str               # "startup"|"smb"|"mid_market"|"enterprise"
    challenges: List[str]
    current_tools: List[str]
    ai_maturity: str                # "exploring"|"piloting"|"scaling"|"optimizing"
    priorities: List[str]           # Ranked
    budget_range: str               # "under_50k"|"50k_200k"|"200k_500k"|"500k_plus"
    matched_use_cases: List[Dict[str, Any]]
    recommended_modules: List[Dict[str, Any]]

    # === OUTPUT ===
    response: str
    recommendation_cards: List[Dict[str, Any]]
    comparison_matrix: Dict[str, Any]
    implementation_roadmap: Dict[str, Any]
    show_recommendations: bool
    show_lead_capture: bool

    # === METADATA ===
    total_tokens: int
    errors: List[str]
```

## Node Specifications

1. **greet** — Welcome, explain 2-minute matching process, ask about industry
2. **assess_industry** — Extract industry + segment. Map to use case subset. Ask company size.
3. **assess_challenges** — Open-ended: biggest operational challenges. LLM extracts structured challenge tags.
4. **assess_maturity** — Current tools, team capabilities, data readiness. Classify maturity level.
5. **assess_priorities** — Rank: cost reduction, speed, quality, compliance, innovation. Budget range.
6. **match_use_cases** — WEIGHTED SCORING (pure Python). Score each of 40+ use cases against: industry_fit (0.25), challenge_alignment (0.30), maturity_compatibility (0.15), priority_match (0.20), budget_feasibility (0.10).
7. **rank_recommendations** — Sort by composite score. Select top 5-8. Group by module. LLM generates rationale per recommendation.
8. **present_matches** — Format recommendation cards: name, match %, modules needed, timeline, complexity, one-line rationale. Set show_recommendations + show_lead_capture.
9. **deep_dive** — User clicks a recommendation → detailed breakdown: what it solves, how it works, similar client results, implementation steps, expected ROI. Loop until done.

## Use Case Database (tools.py — WRITE ALL 40+ ENTRIES)

Each use case has: id, name, description, industries[], modules[], challenges_addressed[], maturity_minimum, complexity (low/medium/high), time_to_value, typical_roi, implementation_steps.

Distribute across 8 industries with overlap. Cover: document automation, research synthesis, compliance checking, content generation, data analysis, workflow orchestration, quality assurance, training/education.

## Scoring Engine (tools.py — WRITE IN FULL)

```python
def score_use_case(use_case, industry, challenges, maturity, priorities, budget) -> float:
    # Weighted composite score with normalization
    ...
```

## Configuration

```python
class Configuration(TypedDict, total=False):
    model_name: str              # "gemini-2.5-pro"
    temperature: float           # 0.7
    max_tokens: int              # 4096
    max_recommendations: int     # 8
    min_match_score: float       # 0.4
```

## Evaluation Dataset

15+ test cases: healthcare enterprise, fintech startup, government agency, exact match scenario, no-good-match scenario, ambiguous needs, deep dive follow-ups.

## Frontend Widget

Glassmorphism chat transitioning to recommendation cards:
- Chat phase: clean conversational interview with progress dots
- Results phase: recommendation cards (match %, module icons, timeline badge, complexity indicator), comparison toggle to view side-by-side, "Request Consultation" CTA (orange)
- Deep dive: expandable card with full details, related use cases, implementation roadmap
- Lead capture: triggered with recommendations, includes "Get Your Custom Implementation Roadmap" CTA

WRITE THE COMPLETE PROMPT. Every file. Every line. No shortcuts.""",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def generate_agent(client: anthropic.Anthropic, agent_num: int, model: str) -> dict:
    """Generate a single agent build prompt and save to file."""
    
    agent = AGENT_PROMPTS[agent_num]
    print(f"\n{'='*70}")
    print(f"  GENERATING: Agent {agent_num} — {agent['name']}")
    print(f"  Model: {model}")
    print(f"  Output: {OUTPUT_DIR / agent['filename']}")
    print(f"{'='*70}\n")
    
    start_time = datetime.now()
    
    response = client.messages.create(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": agent["prompt"],
            }
        ],
    )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # Extract content
    content = response.content[0].text
    
    # Calculate costs
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    
    if "opus" in model:
        cost = (input_tokens / 1_000_000 * 5.0) + (output_tokens / 1_000_000 * 25.0)
    else:
        cost = (input_tokens / 1_000_000 * 3.0) + (output_tokens / 1_000_000 * 15.0)
    
    # Save to file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / agent["filename"]
    output_path.write_text(content, encoding="utf-8")
    
    stats = {
        "agent": agent_num,
        "name": agent["name"],
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost": cost,
        "elapsed_seconds": elapsed,
        "output_file": str(output_path),
        "output_words": len(content.split()),
    }
    
    print(f"  ✅ Complete!")
    print(f"  📝 {stats['output_words']:,} words written")
    print(f"  🎯 {output_tokens:,} output tokens")
    print(f"  💰 ${cost:.2f}")
    print(f"  ⏱️  {elapsed:.0f} seconds")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="Generate DHG AI Factory agent build prompts")
    parser.add_argument("--agent", type=int, choices=[1, 2, 3, 4],
                        help="Generate a specific agent (1-4). Omit for all.")
    parser.add_argument("--model", type=str, choices=["sonnet", "opus"], default="sonnet",
                        help="Model to use: sonnet (default, cheaper) or opus (highest quality)")
    args = parser.parse_args()
    
    # Resolve model name
    model = MODELS[args.model]
    
    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set!")
        print("   export ANTHROPIC_API_KEY='sk-ant-api03-your-key-here'")
        sys.exit(1)
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Determine which agents to generate
    if args.agent:
        agents_to_run = [args.agent]
    else:
        agents_to_run = [1, 2, 3, 4]
    
    print(f"\n🚀 DHG AI Factory — Agent Build Prompt Generator")
    print(f"   Model: {model}")
    print(f"   Agents: {agents_to_run}")
    print(f"   Output: {OUTPUT_DIR.absolute()}")
    
    all_stats = []
    
    for agent_num in agents_to_run:
        stats = generate_agent(client, agent_num, model)
        all_stats.append(stats)
    
    # Summary
    total_cost = sum(s["cost"] for s in all_stats)
    total_tokens = sum(s["total_tokens"] for s in all_stats)
    total_words = sum(s["output_words"] for s in all_stats)
    total_time = sum(s["elapsed_seconds"] for s in all_stats)
    
    print(f"\n{'='*70}")
    print(f"  COMPLETE — ALL AGENTS GENERATED")
    print(f"{'='*70}")
    print(f"  📝 Total words: {total_words:,}")
    print(f"  🎯 Total tokens: {total_tokens:,}")
    print(f"  💰 Total cost: ${total_cost:.2f}")
    print(f"  ⏱️  Total time: {total_time:.0f}s ({total_time/60:.1f}m)")
    print(f"\n  Output files:")
    for s in all_stats:
        print(f"    ✅ {s['output_file']}")
    print()


if __name__ == "__main__":
    main()