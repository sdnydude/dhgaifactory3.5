# DHG AI Factory — LLManager Review Inbox

**Route:** `/inbox`
**Added:** April 2026 (Phase 3)
**Purpose:** Human-in-the-loop review workflow for LangGraph agent outputs

---

## Overview

The LLManager Review Inbox is where human reviewers approve, revise, or reject documents produced by the LangGraph agent pipeline. When an orchestrator recipe (needs_package, curriculum_package, grant_package, or full_pipeline) reaches a human review gate, the LangGraph thread is **interrupted** — it pauses execution and waits for a human decision.

The inbox queries LangGraph for all interrupted threads and presents them in a master-detail layout with AI-assisted quality assessment.

---

## How It Works

```
LangGraph Orchestrator
  │
  ├── Agent produces document
  ├── Prose Quality agent scores it
  ├── Compliance agent verifies ACCME rules
  │
  ▼
  Human Review Gate (thread.interrupt())
  │
  ├── Thread status becomes "interrupted"
  ├── Interrupt payload contains: document, metrics, recipe, review_round
  │
  ▼
  Inbox polls for interrupted threads (every 30s)
  │
  ├── Reviewer selects thread from master list
  ├── AI Reflection panel shows quality signals + recommendation
  ├── Document Viewer renders content with inline commenting
  ├── VS Alternatives panel shows divergent options (when available)
  │
  ▼
  Reviewer decides: Approve / Request Revision / Reject
  │
  ├── Decision sent as Command({ resume: { decision, comments } })
  ├── Thread resumes in LangGraph with the decision
  └── On revision: agent re-runs with feedback, increments review_round (max 3)
```

---

## Quality Signals

The AI Reflection panel (`ReflectionPanel`) evaluates three quality gates from the agent pipeline metrics:

| Signal | Source | Pass Condition |
|--------|--------|---------------|
| Prose Quality | `prose_quality_agent` | `quality_passed === true` |
| Banned Patterns | `prose_quality_agent` | `banned_patterns_found` is empty |
| ACCME Compliance | `compliance_review_agent` | `compliance_result.passed === true` |

**Recommendation logic** (`buildRecommendation` in `reflection-panel.tsx`):
- **Approve** — All gates passed. Shows word count and prose density.
- **Suggest Revision** — Exactly 1 issue found.
- **Needs Attention** — 2+ issues found.

Additional metrics displayed in the MetricsBar:
- Word count
- Prose density (percentage)
- QA pass/fail badge
- Banned pattern count
- Review round indicator (e.g., "Revision 2/3")

---

## Verbalized Sampling (VS) Alternatives

When the agent pipeline uses Verbalized Sampling, the review payload includes `vs_distributions` — a map of alternative outputs per document section. The `VSAlternatives` component:

- Shows the number of alternatives available per section
- Shuffles display order (deterministic, seeded by distribution_id) to eliminate positional bias
- Labels each alternative: **conventional**, **novel**, or **exploratory** (DHG brand-colored badges)
- Shows confidence percentage and auto-selected indicator
- Displays VS parameters: model, phase, k (sample count), tau (threshold)

---

## Inline Commenting

Reviewers can select text in the document and attach comments. Comments are:
- Captured with text selection offsets for positional reference
- Listed in a collapsible sidebar (desktop) or bottom panel (mobile)
- Included in the resume payload sent back to LangGraph
- Available for agents to incorporate during revision rounds

---

## Component Map

```
frontend/src/
  app/inbox/page.tsx                        — Route entry point
  components/review/
    inbox-master-detail.tsx                  — Master list + detail layout, polling logic
    review-panel.tsx                         — Document viewer + comments + VS + decision bar
    reflection-panel.tsx                     — AI quality signals + recommendation
    metrics-bar.tsx                          — Compact metrics badges bar
    decision-bar.tsx                         — Approve / Revise / Reject buttons
    document-viewer.tsx                      — Markdown renderer with text selection
    comments-sidebar.tsx                     — Comment list with scroll-to
    use-annotations.ts                       — Text selection + comment state hook
    vs-alternatives.tsx                      — Verbalized Sampling alternatives display
    types.ts                                 — TypeScript interfaces for all review data
  stores/review-store.ts                     — Zustand store for inbox state
  lib/inboxApi.ts                            — LangGraph SDK client for thread queries
```

---

## State Management

**Review Store** (`stores/review-store.ts`) — Zustand store managing:
- `reviews` — Array of `PendingReview` objects
- `selectedReviewId` — Currently selected thread ID
- `loading` / `error` — Fetch state
- `actionLoading` — Thread ID currently being processed (prevents double-submit)
- `removeReview(threadId)` — Optimistically removes from list after action

**Inbox API** (`lib/inboxApi.ts`) — LangGraph SDK wrapper:
- `listPendingReviews()` — Searches for interrupted threads (limit 50), fetches state for each, extracts interrupt payloads
- `resumeThread(threadId, graphId, resumeValue)` — Resumes with `Command({ resume: { decision, comments } })`
- `getThreadDetails(threadId)` — Fetches full thread state

---

## LangGraph Integration

The inbox connects to LangGraph via `@langchain/langgraph-sdk`:

```typescript
const client = new Client({
  apiUrl: process.env.NEXT_PUBLIC_LANGGRAPH_API_URL || "/api/langgraph"
});

// Find paused threads
const threads = await client.threads.search({ status: "interrupted", limit: 50 });

// Resume with reviewer decision
await client.runs.stream(threadId, graphId, {
  input: null,
  command: { resume: { decision: "approved", comments: [...] } },
  streamMode: "messages-tuple",
});
```

**Production URL:** LangGraph Cloud (see MEMORY.md)
**Dev URL:** `http://localhost:2026`

---

## Auto-Refresh

The inbox polls every 30 seconds (`setInterval(fetchReviews, 30_000)` in `inbox-master-detail.tsx`). Manual refresh is available via the refresh button in the master list header.

---

## Supported Graphs

All 15 registered graphs can produce review items. The master list shows human-friendly labels:

| Graph ID | Display Label |
|----------|--------------|
| needs_package | Needs Package |
| curriculum_package | Curriculum Package |
| grant_package | Grant Package |
| full_pipeline | Full Pipeline |
| needs_assessment | Needs Assessment |
| research | Research |
| clinical_practice | Clinical Practice |
| gap_analysis | Gap Analysis |
| learning_objectives | Learning Objectives |
| curriculum_design | Curriculum Design |
| research_protocol | Research Protocol |
| marketing_plan | Marketing Plan |
| grant_writer | Grant Writer |
| prose_quality | Prose Quality |
| compliance_review | Compliance Review |

---

## Decision Flow

| Decision | Resume Value | What Happens in LangGraph |
|----------|-------------|---------------------------|
| Approve | `{ decision: "approved", comments }` | Pipeline continues to next stage or completes |
| Request Revision | `{ decision: "revision", comments }` | Agent re-runs with feedback, review_round increments |
| Reject | `{ decision: "rejected", comments }` | Pipeline terminates, document archived |

**Revision cap:** After 3 revision rounds, the orchestrator escalates to human review without further auto-retry.
