# Intake Prefill Agent — Design Spec

**Date:** 2026-04-10
**Status:** Draft
**Author:** Stephen Webber + Claude

## Problem

The CME intake form has 10 sections (A-J, 47 fields). Only Section A is required. Sections B-J are optional and currently require manual entry. For most disease states, a significant portion of B-J content (clinical topics, educational gaps, outcomes, treatment modalities) can be inferred from the therapeutic area + disease state + target audience entered in Section A.

## Solution

An AI-powered prefill agent that takes Section A inputs, researches the disease area via PubMed, and generates draft values for sections B through H. The user reviews, accepts, edits, or clears the suggestions before saving.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Where does the agent live? | LangGraph graph | LangGraph is the sole orchestration platform. All LLM calls belong there. |
| LLM dependency? | LLM-agnostic | Claude is temporary. Agent uses tool-grounded prompts (PubMed context), not parametric knowledge. Swappable to local models (Nemotron on RTX 5090). |
| Response time target? | 30-60 seconds | Multi-node agent: PubMed search + context building + structured generation + validation. Fast enough for a form interaction, thorough enough to be useful. |
| Code reuse? | Shared PubMed client extracted from research_agent | Eliminates duplication. Both research_agent and intake_prefill_agent import from `tools/pubmed.py`. |
| Sections prefilled? | B through H | Section I (Compliance) has sensible defaults already. Section J (Additional) is too subjective. |
| User control? | Accept All / Clear All + per-section + per-field editing | Three levels of granularity for accepting or rejecting AI suggestions. |

## Architecture

### 1. New LangGraph Agent

**File:** `langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py`
**Registration:** `langgraph.json` — `"intake_prefill": "./src/intake_prefill_agent.py:graph"`

#### State

```
IntakePrefillState (TypedDict):
  # INPUT
  therapeutic_area: str
  disease_state: str
  target_audience_primary: list[str]
  target_hcp_types: list[str]          # optional
  project_name: str

  # PROCESSING
  messages: list                        # with add_messages reducer
  pubmed_results: list[dict]
  research_context: str

  # OUTPUT
  prefill_sections: dict                # keys: section_b through section_h
  research_summary: str                 # human-readable summary of what was researched
  confidence: dict                      # per-section: high / medium / low

  # METADATA
  errors: list[dict]
  total_tokens: int
  total_cost: float
```

#### Graph Nodes (4 nodes, linear flow)

```
START -> search_literature -> build_context -> generate_prefill -> validate_output -> END
```

**Node 1 — search_literature (~5-10s)**
- Calls shared PubMed client with disease_state + therapeutic_area
- Fetches ~15-20 recent abstracts
- Stores results in `pubmed_results`

**Node 2 — build_context (< 1s)**
- Parses PubMed results into structured research context string
- Extracts: key findings, treatment landscape, known practice gaps, recent clinical trials
- Template-based formatting: concatenates abstracts, extracts MeSH terms, structures findings into a prompt-ready context string
- No LLM call

**Node 3 — generate_prefill (~15-25s)**
- Single LLM call with structured output
- Prompt provides: Section A inputs + research context from Node 2
- Requests JSON matching sections B-H schemas
- Includes per-section confidence ratings

**Node 4 — validate_output (< 1s)**
- Type-checks returned JSON against section schemas
- Strips invalid fields, coerces types
- No LLM call

**Tracing:** Dual decorators on every node:
- `@traceable(name="intake_prefill.<node>", run_type="chain")` — LangSmith
- `@traced_node("intake_prefill", "<node>")` — OTel/Tempo

**LLM instantiation:** `LLMClient` singleton with `ChatAnthropic` (swappable to `ChatOllama`), same pattern as all other agents.

### 2. Shared PubMed Client Extraction

**New file:** `langgraph_workflows/dhg-agents-cloud/src/tools/__init__.py`
**New file:** `langgraph_workflows/dhg-agents-cloud/src/tools/pubmed.py`

Extract the existing `PubMedClient` class from `research_agent.py` into `tools/pubmed.py`. The class is self-contained: async httpx client, `search()` and `fetch_details()` methods, `@traceable` decorators.

**Changes to existing code:**
- `research_agent.py`: Remove `PubMedClient` class, add `from tools.pubmed import PubMedClient`
- No behavioral changes to the research agent

### 3. Registry API Proxy Endpoint

**Modified file:** `registry/cme_endpoints.py`

```
POST /api/cme/intake/prefill
```

**Request:** Section A payload (project_name, therapeutic_area, disease_state, target_audience_primary, target_hcp_types)

**Behavior:**
1. Validates Section A fields (reuses existing `SectionA` Pydantic model — name >= 5 chars, therapeutic_area and disease_state non-empty, at least 1 audience)
2. Invokes `intake_prefill` graph on LangGraph Cloud via existing LangGraph SDK client
3. Waits for completion (60-second timeout)
4. Returns agent output as JSON

**Response:**
```json
{
  "prefill_sections": {
    "section_b": { "supporter_name": "", ... },
    "section_c": { "learning_format": "...", ... },
    "section_d": { "clinical_topics": [...], ... },
    "section_e": { "knowledge_gaps": [...], ... },
    "section_f": { "primary_outcomes": [...], ... },
    "section_g": { "key_messages": [...], ... },
    "section_h": { "distribution_channels": [...], ... }
  },
  "research_summary": "Reviewed 18 recent publications on heart failure management...",
  "confidence": {
    "section_b": "low",
    "section_c": "medium",
    "section_d": "high",
    "section_e": "high",
    "section_f": "high",
    "section_g": "high",
    "section_h": "medium"
  }
}
```

**Error handling:** LangGraph timeout or failure returns HTTP 502 with message. Frontend handles gracefully — user continues with manual entry.

### 4. Frontend Changes

Three modifications to existing files. No new files.

#### 4a. `frontend/src/lib/registryApi.ts`

New function:
```typescript
prefillIntake(sectionA: SectionA): Promise<PrefillResponse>
```
Calls `POST /api/registry/api/cme/intake/prefill`.

Uses `PrefillResponse` type from `@/types/cme`.

#### 4b. `frontend/src/components/intake/intake-form.tsx`

**Footer bar additions:**
- "Research & Prefill" button appears once Section A is valid (same `canSave` check)
- Disabled while prefill is running
- Shows spinner + "Researching [disease_state]..." during the call

**On success:**
- Applies returned sections B-H to Zustand store via `updateIntake()`
- Shows dismissible banner at top of form panel with two action buttons:
  - **"Accept All Drafts"** — Keeps all values, dismisses banner, marks all prefilled sections as accepted
  - **"Clear All Drafts"** — Resets sections B-H to empty defaults, dismisses banner
- Navigates to Section B automatically

**On failure:**
- Shows error in existing error area: "Prefill unavailable — you can fill sections manually."
- Form unchanged, user continues manually

#### 4c. `frontend/src/components/intake/section-nav.tsx`

- Prefilled sections show a visual "AI Draft" indicator (distinct from the completion checkmark)
- Each prefilled section gets a small accept/clear control in the sidebar
- Three levels of user control:
  1. **Bulk** — Accept All / Clear All in the banner
  2. **Per-section** — Accept / Clear on each section in the sidebar
  3. **Per-field** — User edits any field directly (always available)

#### 4d. `frontend/src/stores/intake-store.ts`

New state fields:
- `prefillStatus: Record<string, "prefilled" | "accepted" | "cleared">` — tracks per-section prefill state (Record, not Map, for localStorage serialization)
- `researchSummary: string | null` — the AI's research summary for display
- Actions: `applyPrefill()`, `acceptSection()`, `clearSection()`, `acceptAll()`, `clearAll()`

On "Save Draft" or "Save & Start Pipeline," remaining `prefilled` sections are treated as accepted — no extra confirmation gate.

Prefill state is included in localStorage persistence so it survives page refreshes.

## Sections Prefilled vs. Skipped

| Section | Prefilled? | What the AI Suggests | Confidence |
|---------|------------|---------------------|------------|
| B. Supporter | Partial | Grant amount ranges typical for the therapeutic area. Supporter name left blank (user-specific). | Low |
| C. Educational Design | Yes | Learning format, duration, pre/post test recommendations based on audience + topic complexity | Medium |
| D. Clinical Focus | Yes | Clinical topics, treatment modalities, patient population, disease stage — derived from PubMed research | High |
| E. Educational Gaps | Yes | Knowledge/competence/performance gaps based on recent literature findings | High |
| F. Outcomes | Yes | Primary/secondary outcomes aligned with Moore's framework, measurement approaches | High |
| G. Content | Yes | Key messages from research, relevant references (actual PMIDs from PubMed search), regulatory notes | High |
| H. Logistics | Partial | Distribution channels based on audience. Dates left blank (user-specific). | Medium |
| I. Compliance | Skip | Already has sensible defaults (ACCME compliant = true, etc.) | N/A |
| J. Additional | Skip | Too subjective — special instructions, internal notes | N/A |

## What Does NOT Change

- Section A form — untouched
- Section I defaults — untouched
- Section J — untouched
- Save Draft / Save & Start Pipeline buttons — same behavior
- Project creation API — same payload
- Pipeline execution — same 14-step flow
- Zustand localStorage persistence key — same (`dhg-intake-draft`)

## Error Handling

| Failure | Behavior |
|---------|----------|
| PubMed API down | Agent returns partial prefill (LLM generates without research grounding), confidence set to "low" for all sections |
| LLM call fails | Agent returns error, registry returns 502, frontend shows "Prefill unavailable" message |
| LangGraph Cloud timeout (> 60s) | Registry returns 502, frontend shows "Prefill unavailable" message |
| Invalid JSON from LLM | validate_output node strips bad fields, returns partial prefill with valid fields only |
| Section A incomplete | "Research & Prefill" button is disabled — cannot trigger |

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `langgraph_workflows/dhg-agents-cloud/src/tools/__init__.py` | New | Empty init for tools package |
| `langgraph_workflows/dhg-agents-cloud/src/tools/pubmed.py` | New | PubMedClient extracted from research_agent |
| `langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py` | New | Intake prefill agent (4 nodes) |
| `langgraph_workflows/dhg-agents-cloud/langgraph.json` | Modified | Register intake_prefill graph |
| `langgraph_workflows/dhg-agents-cloud/src/research_agent.py` | Modified | Import PubMedClient from tools.pubmed instead of inline |
| `registry/cme_endpoints.py` | Modified | Add POST /api/cme/intake/prefill proxy endpoint |
| `frontend/src/lib/registryApi.ts` | Modified | Add prefillIntake() function + PrefillResponse type |
| `frontend/src/types/cme.ts` | Modified | Add PrefillResponse interface (single source of truth for the type) |
| `frontend/src/components/intake/intake-form.tsx` | Modified | Prefill button, loading state, banner with Accept All / Clear All |
| `frontend/src/components/intake/section-nav.tsx` | Modified | AI Draft indicators, per-section accept/clear controls |
| `frontend/src/stores/intake-store.ts` | Modified | Prefill state tracking, accept/clear actions |
