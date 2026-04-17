# Agent Observatory — Design Spec

**Date:** 2026-04-17
**Status:** Draft
**Author:** Stephen Webber + Claude

## Summary

A visual control plane for multi-agent systems, deployed as a new section within the existing DHG Next.js frontend at `app.digitalharmonyai.com`. The observatory lets users watch a single task decompose across planning, memory, tool use, evals, retries, and human approvals — then compare how different agent architectures handle the same task, with cost, latency, and reliability traces showing why one design wins over another.

Built graph-first using React Flow, with progressive interactivity: observe → configure/simulate → live execution.

## Audiences

1. **Internal (DHG team)** — understand and optimize LangGraph agent behavior
2. **Client demos** — showcase DHG's multi-agent platform capabilities
3. **Broader AI community** — standalone tool for agent architecture comparison

## Architecture Types Compared

| Type | Description | Example |
|------|-------------|---------|
| **Sequential** | Agents execute one after another in a fixed chain | CME needs_package: Research → Clinical → Gap → LO → Needs → Prose QA |
| **Parallel (fan-out/fan-in)** | Multiple agents run simultaneously, results merge at convergence | CME curriculum_package: Curriculum + Protocol + Marketing in parallel |
| **Hierarchical** | Supervisor agent delegates to specialist sub-agents, synthesizes results | Full CME grant_package: orchestrator dispatches to 11 specialist agents |
| **Debate / Adversarial** | Multiple agents argue positions, a judge agent selects or synthesizes | Treatment guideline consensus from competing perspectives |
| **Human-in-the-loop variants** | The sequential or parallel architecture with approval gates inserted at different positions (e.g., after every agent vs. only at the end vs. at quality thresholds) | Same GLP-1 pipeline but with early gating vs. late gating — shows the latency/quality tradeoff of human oversight placement |

---

## Routes & Navigation

### Route structure

```
/observability
  /observatory              Main entry: scenario selector + architecture viewer
  /observatory/compare      Side-by-side architecture comparison (2-3 architectures)
  /observatory/traces       Trace explorer — drill into a specific run (Phase 3)
```

### Sidebar navigation

New "Observe" section in the role-aware sidebar:

- **System Health** → `/dashboards` (existing Prometheus telemetry page)
- **Agent Observatory** → `/observability/observatory` (new)

---

## Page Layouts

### `/observatory` — Main View

```
+-----------------------------------------------------+
|  Scenario Selector  |  Architecture Tabs             |
|  [GLP-1 Report v]   |  Sequential | Parallel | ...  |
+-----------------------------------------------------+
|                                                      |
|              React Flow Graph Canvas                 |
|         (animated agent execution flow)              |
|                                                      |
|  +----------+  +----------+  +----------+            |
|  | Research  |>>| Clinical |>>| Gap      |           |
|  | Agent     |  | Practice |  | Analysis |           |
|  +----------+  +----------+  +----------+            |
|                                                      |
+-----------------------------------------------------+
|  [ |< ] [ > Play ] [ >| ]  ====o============  1x 2x |
+-----------------------------------------------------+
|  Metrics Bar                                         |
|  Cost: $0.42 | Latency: 34s | Reliability: 98.2%    |
|  Tokens: 12.4K | Retries: 1 | Human Gates: 2        |
+-----------------------------------------------------+
|  Detail Panel (click a node to inspect)              |
|  [Prompt] [Output] [Trace] [Cost Breakdown]          |
+-----------------------------------------------------+
```

### `/observatory/compare` — Comparison View

```
+------------------------+------------------------+
|  Sequential            |  Parallel              |
|  +---+ +---+ +---+    |  +---+  +---+          |
|  | R |>| C |>| G |    |  | R |--| G |          |
|  +---+ +---+ +---+    |  | C |--+   |          |
|                        |  +---+  +---+          |
|  $0.42 | 34s | 98%    |  $0.44 | 18s | 97%     |
+------------------------+------------------------+
|  Delta Summary                                   |
|  Parallel is 1.9x faster (+$0.02, -1% rel)      |
|  Winner by: latency Y  cost X  reliability X    |
+--------------------------------------------------+
```

---

## Data Model

### Scenario

A selectable example task with pre-computed traces for each architecture type.

```typescript
interface Scenario {
  id: string                        // "glp1-report"
  name: string                      // "GLP-1 Agonist Literature Review"
  description: string               // One-line summary for the selector
  complexity: "simple" | "moderate" | "complex"
  domain: string                    // "medical-education", "research", etc.
  inputPrompt: string               // The actual task prompt submitted
  architectures: ArchitectureTrace[]
}
```

### ArchitectureTrace

One architecture's complete execution of a scenario.

```typescript
interface ArchitectureTrace {
  architectureType: "sequential" | "parallel" | "hierarchical" | "debate" | "hitl"
  architectureName: string          // "CME Sequential Pipeline"

  // Graph structure
  nodes: AgentNode[]
  edges: AgentEdge[]

  // Aggregate metrics
  totalCostUsd: number
  totalLatencyMs: number
  totalTokens: number
  reliabilityScore: number          // 0-100
  qualityScore: number              // 0-100
  retryCount: number
  humanGateCount: number

  // Timeline data for animated playback
  timeline: TimelineEvent[]
}
```

### AgentNode

A single agent or control-flow node in the graph.

```typescript
interface AgentNode {
  id: string
  label: string                     // "Research Agent"
  type: "agent" | "gate" | "merge" | "split" | "human_review"

  // Per-node metrics
  costUsd: number
  latencyMs: number
  tokens: { input: number; output: number }
  model: string                     // "claude-sonnet-4-20250514"

  // Content for the detail panel
  prompt: string
  output: string
  qualityScore: number

  // State for animation
  status: "pending" | "running" | "completed" | "failed" | "retrying"
  startedAt: number                 // ms offset from trace start
  completedAt: number
  retries: { attempt: number; error: string; costUsd: number }[]
}
```

### AgentEdge

Connection between nodes in the graph.

```typescript
interface AgentEdge {
  source: string
  target: string
  type: "data" | "conditional" | "parallel" | "retry"
  label?: string                    // "quality_score >= 80"
}
```

### TimelineEvent

Drives animated playback — each event transitions a node's visual state.

```typescript
interface TimelineEvent {
  timestamp: number                 // ms offset from trace start
  nodeId: string
  event: "start" | "complete" | "fail" | "retry" | "human_approve" | "human_reject"
  metadata?: Record<string, unknown>
}
```

### ModelPricing (Phase 2)

Used by the configure/simulate mode to re-project costs when swapping models.

```typescript
interface ModelPricing {
  modelId: string                   // "claude-sonnet-4-20250514"
  displayName: string               // "Claude Sonnet"
  inputPer1kTokens: number          // $0.003
  outputPer1kTokens: number         // $0.015
  avgLatencyMs: number              // baseline latency per call
  qualityMultiplier: number         // 1.0 = baseline, 0.85 = 15% quality drop
}
```

---

## Example Scenarios

Five selectable scenarios. Four are medical/CME domain (authentic to DHG), one is domain-neutral for broader audience appeal. Each highlights a different architecture's strength.

| Scenario | Complexity | Domain | Best Architecture | Rationale |
|----------|-----------|--------|-------------------|-----------|
| Drug interaction lookup | Simple | Medical | Sequential | Linear pipeline, no parallelism benefit, low agent count |
| GLP-1 literature review | Moderate | Medical | Parallel | Research + Clinical can run simultaneously, clear fan-out/fan-in |
| Full CME grant package | Complex | Medical | Hierarchical | 11 agents, orchestrator delegates to specialist teams, complex dependencies |
| Treatment guideline consensus | Moderate | Medical | Debate | Multiple perspectives needed, judge synthesizes competing views |
| Market research report | Moderate | General | Parallel | Industry analysis + competitor profiling + trend research in parallel — accessible to any audience without medical domain knowledge |

Each scenario ships with all 5 architecture traces pre-computed, so users can see how each architecture handles the same task — even when the architecture isn't optimal for it.

---

## Component Architecture

### Component Tree

```
ObservatoryPage
|-- ScenarioSelector              Dropdown + description card
|-- ArchitectureTabs              Tab bar: Sequential | Parallel | Hierarchical | Debate | HITL
|-- GraphCanvas                   React Flow wrapper
|   |-- AgentNode                 Custom node: rounded rect, purple border
|   |   |-- NodeStatusBadge       Pulsing/solid indicator
|   |   |-- NodeMetrics           Inline cost, latency, tokens
|   |   +-- ModelBadge            Which LLM
|   |-- GateNode                  Diamond shape, orange border
|   |-- MergeNode                 Trapezoid, graphite
|   +-- SplitNode                 Inverted trapezoid, graphite
|-- PlaybackControls              Play/pause/scrub/speed
|-- MetricsBar                    6 aggregate metrics
|   +-- MetricCard                Single metric with directional indicator
|-- DetailPanel                   Expandable bottom panel
|   |-- PromptTab                 Full prompt text
|   |-- OutputTab                 Agent output with quality highlights
|   |-- TraceTab                  Timeline waterfall for this node
|   |-- CostTab                   Token breakdown, model pricing
|   +-- RetriesTab                Retry history with errors
+-- CompareView                   Used on /compare route
    |-- GraphCanvas x 2-3         Side by side
    +-- DeltaMetricsBar           Differences with winner indicators
```

### Custom React Flow Node Types

| Node Type | Shape | Border Color | Fill | Use |
|-----------|-------|-------------|------|-----|
| `AgentNode` | Rounded rectangle | `--dhg-purple` (#663399) | `--dhg-surface` | Agent execution step |
| `GateNode` | Diamond | `--dhg-orange` (#F77E2D) | `--dhg-surface` | Quality gate, conditional branch |
| `MergeNode` | Trapezoid | `--dhg-graphite` (#32374A) | `--dhg-surface` | Fan-in convergence |
| `SplitNode` | Inverted trapezoid | `--dhg-graphite` (#32374A) | `--dhg-surface` | Fan-out divergence |

### Node Status Animations

| Status | Visual |
|--------|--------|
| `pending` | Grey fill, dashed border |
| `running` | Pulsing purple glow animation |
| `completed` | Solid green check icon, full opacity |
| `failed` | Red border, X icon |
| `retrying` | Orange pulse, retry counter badge |

### Edge Animations

During playback, edges animate to show data flow between nodes:
- **Idle**: Solid line, muted color
- **Active** (source running → target pending): Animated dashes traveling source→target, purple color
- **Complete** (both nodes done): Solid line, full opacity
- **Failed**: Red dashed line, no animation

Edge animation uses React Flow's `animated` prop combined with CSS `stroke-dasharray` + `stroke-dashoffset` keyframes for the traveling-dash effect.

### State Management

Single Zustand store, following existing patterns (`review-store.ts`, `files-tab-store.ts`).

```typescript
interface ObservatoryStore {
  // Selection state
  activeScenarioId: string | null
  activeArchitecture: ArchitectureType
  selectedNodeId: string | null

  // Playback state
  isPlaying: boolean
  playbackPosition: number          // 0-1 normalized
  playbackSpeed: number             // 1, 2, or 4

  // Compare mode
  compareArchitectures: ArchitectureType[]

  // Data
  scenarios: Scenario[]

  // Actions
  selectScenario: (id: string) => void
  selectArchitecture: (type: ArchitectureType) => void
  selectNode: (id: string | null) => void
  togglePlayback: () => void
  setPlaybackPosition: (pos: number) => void
  setPlaybackSpeed: (speed: number) => void
  setCompareArchitectures: (types: ArchitectureType[]) => void
}
```

---

## Metrics & Comparison

### Metrics Bar — 6 Key Metrics

| Metric | Computation | Format | Higher/Lower = Better |
|--------|------------|--------|----------------------|
| **Total Cost** | Sum of all node `costUsd` | `$0.42` | Lower |
| **Total Latency** | Wall-clock: last `completedAt` minus first `startedAt` | `34.2s` | Lower |
| **Reliability** | `(successful_nodes / total_nodes) x 100`, penalized by retry count | `98.2%` | Higher |
| **Token Efficiency** | `totalTokens / qualityScore` | `142 tok/pt` | Lower |
| **Retry Count** | Sum of all node retry arrays | `1 retry` | Lower |
| **Human Gates** | Count of `human_review` type nodes | `2 gates` | Contextual |

### Delta Metrics (Compare View)

When comparing architectures, each metric shows a directional delta:
- Green arrow down for cost/latency/retries (lower is better)
- Green arrow up for reliability/quality (higher is better)
- One-line verdict: "Parallel is 1.9x faster (+$0.02, -1% reliability)"

### Cost Model for Model Swapping (Phase 2)

When users swap models, every node's metrics re-project:
- **Cost**: `(node.tokens.input * newModel.inputPer1kTokens / 1000) + (node.tokens.output * newModel.outputPer1kTokens / 1000)`
- **Latency**: `node.latencyMs * (newModel.avgLatencyMs / baselineModel.avgLatencyMs)`
- **Quality**: `node.qualityScore * newModel.qualityMultiplier`

Projections are labeled as "Projected" with a tooltip explaining the approximation.

### Failure Policy Visualization (Phase 2)

When a node's failure policy is changed, the graph updates to show the policy in action:
- **Retry(n)**: Node pulses orange, retry counter increments, edge flashes
- **Fallback(model)**: Secondary node fades in below showing fallback path
- **Escalate**: Human review gate node appears, pipeline pauses
- **Fail-fast**: Downstream nodes grey out, error propagates visually

---

## Progressive Delivery Phases

### Phase 1: Observe & Explore (Initial Launch)

**Scope**: Pure frontend. No backend changes. All data is static bundled JSON.

| Deliverable | Details |
|-------------|---------|
| Static scenario data | 5 JSON trace files in `frontend/src/data/observatory/`, lazy-loaded per scenario (not bundled upfront — each file may be 400-600KB with full prompt/output text) |
| React Flow graph canvas | 4 custom node types, animated playback, zoom/pan/minimap |
| Playback controls | Play/pause, scrub bar, 1x/2x/4x speed |
| Metrics bar | 6 metrics, per-node and aggregate |
| Detail panel | Prompt, output, cost breakdown, retry history per node |
| Architecture tabs | Switch between 5 architectures for same scenario |
| Compare view | 2-up side-by-side with synchronized playback and delta metrics |
| Routes | `/observability/observatory` + `/observability/observatory/compare` |
| Sidebar nav | "Agent Observatory" under Observe section |

### Phase 2: Configure & Simulate

**Scope**: Mostly frontend. One new backend endpoint for pricing data.

| Deliverable | Details |
|-------------|---------|
| Model swapper | Per-node or global dropdown: Claude Sonnet / Haiku / Opus / Qwen3. Costs, latency, quality re-project. |
| Failure policy editor | Per-node selector: retry(n), fallback(model), escalate, fail-fast. Graph re-simulates with new policy. |
| Scenario parameter tuning | Adjust complexity, source count, quality threshold — trace re-computes projections |
| What-if snapshots | Save a configuration, name it, compare snapshots side by side |
| Pricing API | `GET /api/v1/observatory/pricing` — serves model pricing table, updatable without frontend redeploy |

### Phase 3: Live Execution

**Scope**: Significant backend. New DB tables, WebSocket infrastructure, LangGraph Cloud integration.

| Deliverable | Details |
|-------------|---------|
| Live trace ingestion | Registry API endpoint receives trace events from LangGraph runs, persists to Postgres |
| Real-time graph updates | WebSocket or SSE from registry to frontend. Nodes transition as real agents execute. |
| Run launcher | "Run this scenario" button fires a real LangGraph thread via LangGraph Cloud API |
| Human approval integration | Gate nodes become interactive — approve/reject wired to LangGraph interrupt/resume |
| Historical run browser | Select from past runs, replay their traces in the graph |
| Trace explorer route | `/observatory/traces` — searchable list of historical runs with filtering by scenario, architecture, date, cost range |
| A/B architecture testing | Run same prompt through two architectures simultaneously, compare real results |

### Phase Boundaries

Each phase is fully shippable and independently useful:
- **Phase 1** = compelling demo, architecture education tool
- **Phase 2** = decision-making tool for architecture and model selection
- **Phase 3** = live operational control plane

No phase requires the next to deliver value. Phase boundaries are strict — complete one before starting the next.

### Estimated Complexity

| Phase | New Files | New Components | Backend Changes | Relative Effort |
|-------|-----------|----------------|-----------------|-----------------|
| Phase 1 | ~15 | ~12 | None | 1x |
| Phase 2 | ~8 | ~6 | 1 endpoint | 0.7x |
| Phase 3 | ~12 | ~5 | 4+ endpoints, DB tables, WebSocket | 2x |

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Graph visualization | React Flow | Planned in frontend strategy, maps naturally to LangGraph StateGraph model |
| Graph layout | Dagre (@dagrejs/dagre) | Automatic directed-graph layout; native React Flow integration. Sequential → LR rank, Hierarchical → TB tree, Parallel → swim lanes, Debate → diamond arrangement |
| Charts / sparklines | Recharts | Already installed in frontend |
| UI components | shadcn/ui | Existing design system |
| State management | Zustand | Matches existing stores (review-store, files-tab-store) |
| Styling | Tailwind + DHG brand tokens | Existing pattern, light/dark mode support. React Flow's own theming (background dots, selection box, minimap, controls) inherits from DHG dark-mode CSS variables via the `dark` class on `<ReactFlow>` wrapper. |
| Data (Phase 1) | Static JSON | Zero backend dependencies, ships immediately |
| Data (Phase 2) | Static JSON + 1 API endpoint | Pricing table from registry |
| Data (Phase 3) | Postgres + WebSocket | Full live infrastructure |

---

## File Structure (Phase 1)

```
frontend/src/
  app/
    observability/
      observatory/
        page.tsx                    Main observatory page
        compare/
          page.tsx                  Side-by-side comparison view
  components/
    observatory/
      scenario-selector.tsx         Dropdown + description card
      architecture-tabs.tsx         Tab bar for architecture switching
      graph-canvas.tsx              React Flow wrapper + layout engine
      nodes/
        agent-node.tsx              Custom AgentNode
        gate-node.tsx               Custom GateNode (diamond)
        merge-node.tsx              Custom MergeNode (trapezoid)
        split-node.tsx              Custom SplitNode (inverted trapezoid)
      playback-controls.tsx         Play/pause/scrub/speed
      metrics-bar.tsx               6-metric summary bar
      metric-card.tsx               Single metric with indicator
      detail-panel.tsx              Tabbed detail view
      compare-view.tsx              Multi-graph comparison layout
      delta-metrics-bar.tsx         Difference indicators
  stores/
    observatory-store.ts            Zustand store
  data/
    observatory/
      scenarios.ts                  Scenario index + types
      drug-interaction.json         Simple scenario traces
      glp1-review.json              Moderate scenario traces
      cme-grant-package.json        Complex scenario traces
      guideline-consensus.json      Debate scenario traces
      market-research.json          General-domain scenario traces
  lib/
    observatory/
      layout.ts                     Dagre-based graph layout per architecture type (LR/TB/custom)
      playback.ts                   Timeline animation engine
      metrics.ts                    Metric computation helpers
      cost-model.ts                 Model pricing + projection logic (Phase 2 prep)
```

---

## Open Questions (Resolved During Brainstorming)

| Question | Resolution |
|----------|-----------|
| Separate site or integrated? | Integrated — lives in existing Next.js frontend under `/observability` |
| Data source for launch? | Simulation-first (bundled JSON), live hooks layered in Phase 3 |
| Which architectures? | Sequential, Parallel, Hierarchical, Debate, HITL variants |
| Audience? | All three: internal, client demos, broader AI community |
| Interactivity level? | Progressive: observe (P1) → configure (P2) → live (P3) |
| Visualization approach? | Graph-first (React Flow), with metrics bar and timeline as secondary views |
