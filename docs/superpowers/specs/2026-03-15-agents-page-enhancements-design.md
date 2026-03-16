# Agents Page Enhancements — Design Spec

**Date:** 2026-03-15
**Status:** Approved
**Scope:** 8 features transforming the agents page from metadata-only to a full operational dashboard

---

## Overview

The agents page (`/agents`) currently shows thread metadata: status, pipeline progress, IDs, and errors. This spec adds live streaming, output viewing, VS distribution display, timeline visualization, token/cost tracking, individual agent retry, and cross-run diff comparison.

## Architectural Approach

**Hybrid SSE + Polling (Approach B):**
- Live threads: SSE via LangGraph SDK `client.runs.stream()` through existing proxy SSE passthrough
- Historical threads: Polling `client.threads.getState()` as today
- Stream events buffered in Zustand store (ephemeral — lost on refresh)
- LangSmith remains the authoritative trace history

**No new infrastructure required.** Uses existing LangGraph proxy, SDK streaming, and SSE passthrough.

**Deployment note:** The frontend runs as a long-lived Node.js server in a Docker container (`dhg-frontend`), not as edge/serverless. The proxy route has no response timeout concern — Node.js keeps the SSE connection open for the full pipeline duration (up to 5 minutes per agent timeout). No `maxDuration` export needed.

---

## Tab Architecture

The current `AgentDetail` component is replaced with a tabbed container.

### Tabs

**Stream | Detail | VS | Outputs | Timeline**

### Persistent Elements (Above Tabs)

- Header: graph ID, project name, status badges, human review status
- Pipeline progress bar (always visible)
- Stream tab gets a pulsing dot indicator when thread is actively running

### Auto-Selection Logic

| Thread Status | Auto-Selected Tab |
|---------------|-------------------|
| `busy` | Stream |
| `interrupted` | Detail |
| `error` / `failed` | Detail |
| `idle` (completed) | Outputs |

Tab state is local to the component. Switching threads resets to auto-selected tab. Manual tab selection sticks until thread switch.

---

## Feature 1: Stream Tab

### Connection

- Uses LangGraph SDK `client.runs.stream(threadId, latestRunId)` with `streamMode: "events"`
- The SDK's `runs.stream()` returns an `AsyncGenerator` — consumed via `for await` loop in a client-side async function
- The SDK routes through the existing `/api/langgraph/[...path]` proxy (SDK's `apiUrl` points there), which adds the `x-api-key` header and passes through the SSE response body
- **Not a browser `EventSource`** — the SDK handles the SSE parsing internally and yields typed event objects
- Connection opens when user clicks a `busy` thread (auto-selected)
- Connection closes when: run completes, user switches threads, or component unmounts (via `AbortController`)

### Run ID Resolution

The stream requires a valid `runId`. Rather than relying on the potentially stale `selectedAgent.runId` from the store, `agentsStreamApi.ts` resolves the current run ID at connection time by calling `client.runs.list(threadId, { limit: 1 })`. This handles:
- Initial connection (gets the active run)
- After retry (gets the newly created run)
- Stale store data (always fresh lookup)

### Display

- Terminal-style dark panel (extends existing `log-stream.tsx` component)
- Each event becomes a log line: `[timestamp] [agent_name] message`
- Agent names color-coded per existing status color scheme

### Event Type Mapping

| SDK Event | Display |
|-----------|---------|
| `on_chain_start` | `[agent] Starting...` |
| `on_chain_end` | `[agent] ✓ Complete` |
| `on_llm_stream` | Token output (batched every 200ms to avoid flooding) |
| `on_tool_start` | `[agent] Calling [tool_name]...` |
| `on_tool_end` | `[agent] Tool result received` |
| `on_llm_end` | (Not displayed — used internally for token count extraction) |

### Scroll Behavior

- Auto-scroll to bottom by default
- Scroll lock toggle: if user scrolls up, auto-scroll pauses; click to re-lock
- Run completion: shows "Stream ended at [time]" footer

### State Management

- Events buffer into Zustand store array (`streamEvents[]`)
- Ephemeral — lost on page refresh
- Completed threads show "No active stream" message

---

## Feature 2: Output Viewer (Outputs Tab + Slide-Over)

### Outputs Tab

- Grid of cards, one per completed agent output
- Cards ordered by pipeline sequence
- Each card shows: agent label, word count, 2-line text preview (~150 chars)

### Slide-Over Panel

- Triggered by clicking an output card
- Slides in from right, ~60% viewport width
- Header: agent name, word count, completion timestamp
- Body: full scrollable text, Inter font, readable line height and paragraph spacing
- Close: X button or click outside

### Data Source

- Agent outputs live in thread state under various key patterns
- The existing `_output` suffix filter misses three keys: `prose_quality_pass_1`, `prose_quality_pass_2`, `compliance_result`
- Replace the suffix-based heuristic with an exhaustive key set matching `OUTPUT_LABELS` in `agent-detail.tsx`:
  ```
  research_output, clinical_output, gap_analysis_output, learning_objectives_output,
  needs_assessment_output, curriculum_output, protocol_output, marketing_output,
  grant_package_output, prose_quality_pass_1, prose_quality_pass_2, compliance_result
  ```
- `completedOutputs: string[]` remains unchanged (used by `pipeline-progress.tsx` for step-completion logic via `OUTPUT_MAP`) — updated to use the exhaustive key set
- Add a **new** field `outputContents: Record<string, string>` mapping output key → full text content
- Both fields populated from the same state parse — `completedOutputs` gets the key names, `outputContents` gets the text

---

## Feature 3: VS Distributions (VS Tab)

### Table Layout

| Column | Content |
|--------|---------|
| Agent | Agent name (human-readable label) |
| Selected Approach | Name/description of the winning candidate |
| Confidence | Score of selected approach |
| Runner-Up | Score of second-place candidate |
| Spread | Difference between top two |
| Distribution | Inline sparkline showing all candidate scores |

### Sparklines

- CSS-only mini bar charts (percentage-width divs)
- No charting library dependency
- Shows relative confidence scores across all candidates

### Row Expansion

- Click a row to expand: shows all candidates with full descriptions and scores

### Data Source

- Each agent stores `vs_distributions` in thread state
- Extend `getThreadState()` to extract `vs_distributions` keys

### Empty State

- "No VS distributions available" for pre-VS threads or threads with no completed agents

---

## Feature 4: Detail Tab

### Retained from Current AgentDetail

- Metric cards: Duration, Current Step, Retries, Review Round
- Thread/Run/Project IDs
- Last Checkpoint info

### Added: Token/Cost Summary

- New metric cards: Total Tokens (input + output), Estimated Cost
- **Data source: stream events only.** `on_llm_end` events include `usage_metadata` with `input_tokens` and `output_tokens`. These are accumulated in the Zustand store as events arrive. LangSmith trace data is NOT accessible through the LangGraph Cloud REST API — no separate LangSmith proxy is added.
- For historical threads where no stream was captured: token cards show "—" (data unavailable). LangSmith has the full trace for detailed token analysis.
- Cost estimate: calculated as `(input_tokens * $3 + output_tokens * $15) / 1M` (Claude Sonnet pricing)

### Added: Retry Button (Feature 7)

- Appears next to each error in the errors section
- Calls `client.runs.create()` on the same thread to restart from failed node
- Shows "Retrying..." state while run starts
- Retry response returns new run ID — store updates `selectedAgent.runId`
- Thread returns to `busy`, Stream tab auto-activates (stream connects using fresh run ID via `runs.list()` resolution)

---

## Feature 5: Timeline Tab

### Visualization

- Horizontal Gantt-style bars
- Y-axis: agent names in pipeline order
- X-axis: relative time (0:00 → pipeline end)
- Parallel agents show as overlapping rows at same time range

### Bar Styling

| Status | Color |
|--------|-------|
| Complete | Green |
| Running | Orange (animated) |
| Failed | Red |
| Pending | Gray |

### Token/Cost Annotations (Feature 6)

- Token count right-aligned inside each bar (e.g., "12.4k tokens")
- Click/hover a bar: duration, token breakdown (input/output), estimated cost
- Summary row at bottom: total pipeline duration, total tokens, total estimated cost

### Data Source

- Primary: stream event timestamps (precise, if available)
- Fallback: thread state checkpoint timestamps (less precise)
- No data: "Timeline unavailable — view in LangSmith"

### Implementation

- CSS grid with percentage-width divs
- No charting library — plain HTML/CSS

---

## Feature 8: Diff View (In Outputs Slide-Over)

### Trigger

- "Compare with previous run" toggle in slide-over header

### Behavior

- Panel splits vertically: current run (left), previous run (right)
- Previous run found via `getPreviousRunOutput()` in `agentsApi.ts` (REST call, not SSE): queries `client.threads.search({ limit: 20 })`, then filters client-side by checking each thread's state for matching `project_id` (note: `project_id` is in thread state values, NOT thread metadata — cannot filter server-side). Filters to threads created before current, gets state of most recent match. Performance is acceptable for current scale (single user, ~50 total threads).
- Line-level diff highlighting: added text green, removed text red
- If no previous run exists: toggle disabled with tooltip "No previous run to compare"

### Implementation

- Simple line-level diff algorithm (split by paragraphs, compare)
- No external diff library needed for line-level comparison

---

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `components/agents/agent-tabs.tsx` | Tab container with auto-selection logic; renders persistent header (graph ID, status badges) and PipelineProgress above tab row — these are extracted from current `agent-detail.tsx` |
| `components/agents/stream-tab.tsx` | SSE stream panel |
| `components/agents/detail-tab.tsx` | Refactored detail content |
| `components/agents/vs-tab.tsx` | VS distribution table + sparklines |
| `components/agents/outputs-tab.tsx` | Output cards grid |
| `components/agents/output-slide-over.tsx` | Slide-over panel with diff toggle |
| `components/agents/timeline-tab.tsx` | Gantt visualization |
| `components/agents/vs-sparkline.tsx` | CSS sparkline component |
| `lib/agentsStreamApi.ts` | SSE streaming functions |

### Modified Files

| File | Changes |
|------|---------|
| `app/agents/page.tsx` | Replace `AgentDetail` with `AgentTabs` |
| `lib/agentsApi.ts` | Extend `getThreadState()` for output text (`outputContents`), VS data, timing data; add `getPreviousRunOutput(projectId, beforeDate)` for diff view; add `retryAgent(threadId)` for retry button |
| `stores/agents-store.ts` | Add stream events, output text, VS data to state |
| `components/agents/agent-detail.tsx` | Refactor into `detail-tab.tsx` (original removed) |
| `components/agents/log-stream.tsx` | Extend for SSE event rendering |
| `components/agents/pipeline-progress.tsx` | No internal changes; render location moves from inside `agent-detail.tsx` to inside `agent-tabs.tsx` (above tab row) |

### Untouched Files

- `agent-tree.tsx`, `agent-tree-item.tsx`, `stats-bar.tsx`, `assistants-registry.tsx`, `subagent-card.tsx` — no changes needed

---

## Data Flow

```
LangGraph Cloud API
  │
  ├─ SSE: /threads/{id}/runs/{id}/stream (streamMode: "events")
  │   └─→ proxy /api/langgraph (adds x-api-key) → SDK AsyncGenerator
  │       └─→ agentsStreamApi.ts (for await loop) → Zustand store (streamEvents[])
  │           └─→ stream-tab.tsx (renders log lines)
  │           └─→ timeline-tab.tsx (extracts timing from events)
  │           └─→ detail-tab.tsx (token counts from events)
  │
  └─ REST: /threads/{id}/state (existing polling)
      └─→ agentsApi.ts → Zustand store
          └─→ detail-tab.tsx (metrics, errors, retry)
          └─→ vs-tab.tsx (vs_distributions from state)
          └─→ outputs-tab.tsx (output text from state)
          └─→ timeline-tab.tsx (fallback checkpoint timestamps)
```

---

## Dependencies

- **LangGraph SDK** `client.runs.stream()` — already available
- **Proxy SSE passthrough** — already built in `/api/langgraph/[...path]/route.ts`
- **shadcn/ui** — Tabs, Sheet (slide-over), Badge, Button components
- **No new npm packages required**

---

## Out of Scope

- Stream replay after page refresh (LangSmith is the permanent record)
- Multi-user broadcast (single-user system)
- Word-level diff (line-level is sufficient for prose comparison)
- Custom WebSocket infrastructure
- Agent output markdown rendering (outputs are prose, plain text with paragraph breaks)
