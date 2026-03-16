# Agents Page Enhancements Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the agents page from metadata-only to a full operational dashboard with live streaming, output viewing, VS distributions, timeline, token tracking, retry, and diff.

**Architecture:** Tabbed detail panel replacing current `AgentDetail`. Five tabs: Stream, Detail, VS, Outputs, Timeline. Live threads use SDK `AsyncGenerator` streaming via existing proxy SSE passthrough. Historical threads use polling as today. New `outputContents` and `vsDistributions` fields added to `ThreadState`.

**Tech Stack:** Next.js, React, Zustand, LangGraph SDK (`@langchain/langgraph-sdk`), shadcn/ui (Tabs, Sheet, Badge, Button, Tooltip — all already installed), Tailwind CSS.

**Spec:** `docs/superpowers/specs/2026-03-15-agents-page-enhancements-design.md`

---

## File Structure

### New Files (all under `frontend/src/`)

| File | Responsibility |
|------|---------------|
| `components/agents/agent-tabs.tsx` | Tab container, persistent header + pipeline progress above tabs, auto-tab selection logic |
| `components/agents/stream-tab.tsx` | Live stream display using extended `LogStream`, stream connection lifecycle |
| `components/agents/detail-tab.tsx` | Metrics, IDs, token/cost cards, errors with retry buttons (extracted from `agent-detail.tsx`) |
| `components/agents/vs-tab.tsx` | VS distribution table with expandable rows |
| `components/agents/vs-sparkline.tsx` | CSS-only sparkline bar component |
| `components/agents/outputs-tab.tsx` | Output card grid |
| `components/agents/output-slide-over.tsx` | Sheet slide-over for full output text + diff toggle |
| `components/agents/timeline-tab.tsx` | Gantt-style CSS grid timeline with token annotations |
| `lib/agentsStreamApi.ts` | `connectStream()`, `resolveRunId()` functions using SDK `runs.stream()` |

### Modified Files

| File | What Changes |
|------|-------------|
| `lib/agentsApi.ts` | Add `projectName` to `RunningAgent`, add `OUTPUT_KEYS` constant, `outputContents` + `vsDistributions` to `ThreadState`, add `getPreviousRunOutput()`, `retryAgent()` |
| `stores/agents-store.ts` | Add `streamEvents`, `streamStatus`, `tokenUsage` to state; add `addStreamEvent()`, `clearStream()`, `startStream()`, `retryRun()` actions |
| `components/agents/log-stream.tsx` | Add scroll-lock toggle, stream-ended footer, remove `max-h` (parent controls height) |
| `components/agents/agent-tree-item.tsx` | Show project name below graph ID |
| `app/agents/page.tsx` | Replace `<AgentDetail>` with `<AgentTabs>`, remove `selectedState` polling (tabs manage their own) |

### Untouched Files

`agent-tree.tsx`, `stats-bar.tsx`, `assistants-registry.tsx`, `subagent-card.tsx`, `pipeline-progress.tsx` (component unchanged; render location moves)

---

## Chunk 1: Foundation — Types, API, Store

### Task 1: Extend ThreadState and agentsApi

**Files:**
- Modify: `frontend/src/lib/agentsApi.ts`

- [ ] **Step 1: Add projectName to RunningAgent and OUTPUT_KEYS constant**

In `frontend/src/lib/agentsApi.ts`, add `projectName` to `RunningAgent` interface:

```typescript
export interface RunningAgent {
  threadId: string;
  runId: string;
  graphId: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  metadata: Record<string, unknown>;
  projectName: string;
}
```

Then add after the `AgentStats` interface (line 47):

```typescript
export const OUTPUT_KEYS = [
  "research_output",
  "clinical_output",
  "gap_analysis_output",
  "learning_objectives_output",
  "needs_assessment_output",
  "curriculum_output",
  "protocol_output",
  "marketing_output",
  "grant_package_output",
  "prose_quality_pass_1",
  "prose_quality_pass_2",
  "compliance_result",
] as const;
```

Add new fields to `ThreadState` interface (after `reviewRound: number`):

```typescript
  outputContents: Record<string, string>;
  vsDistributions: Record<string, VsDistribution>;
  timingData: Record<string, { startedAt: string; completedAt: string }>;
```

Add `VsDistribution` interface before `ThreadState`:

```typescript
export interface VsCandidate {
  name: string;
  description: string;
  score: number;
}

export interface VsDistribution {
  agentName: string;
  selected: VsCandidate;
  candidates: VsCandidate[];
}
```

- [ ] **Step 2: Update getThreadState() to use OUTPUT_KEYS and populate new fields**

Replace the `outputKeys` filter logic (lines 117-119) and extend the return object:

```typescript
export async function getThreadState(threadId: string): Promise<ThreadState> {
  const client = createClient();
  const state = await client.threads.getState(threadId);
  const vals = (state.values as Record<string, unknown>) ?? {};

  const completedOutputs: string[] = [];
  const outputContents: Record<string, string> = {};
  for (const key of OUTPUT_KEYS) {
    if (vals[key] != null) {
      completedOutputs.push(key);
      const content = vals[key];
      outputContents[key] = typeof content === "string" ? content : JSON.stringify(content);
    }
  }

  const vsDistributions: Record<string, VsDistribution> = {};
  if (vals.vs_distributions && typeof vals.vs_distributions === "object") {
    const raw = vals.vs_distributions as Record<string, unknown>;
    for (const [agentName, dist] of Object.entries(raw)) {
      if (dist && typeof dist === "object") {
        const d = dist as Record<string, unknown>;
        const candidates = Array.isArray(d.candidates)
          ? (d.candidates as VsCandidate[])
          : [];
        const selected = candidates.length > 0
          ? candidates.reduce((a, b) => (a.score > b.score ? a : b))
          : { name: "", description: "", score: 0 };
        vsDistributions[agentName] = { agentName, selected, candidates };
      }
    }
  }

  const timingData: Record<string, { startedAt: string; completedAt: string }> = {};
  if (vals.agent_timing && typeof vals.agent_timing === "object") {
    const raw = vals.agent_timing as Record<string, { started_at?: string; completed_at?: string }>;
    for (const [agent, timing] of Object.entries(raw)) {
      if (timing?.started_at) {
        timingData[agent] = {
          startedAt: timing.started_at,
          completedAt: timing.completed_at ?? "",
        };
      }
    }
  }

  return {
    projectId: (vals.project_id as string) ?? "",
    projectName: (vals.project_name as string) ?? "",
    status: (vals.status as string) ?? "unknown",
    currentStep: (vals.current_step as string) ?? "",
    errors: (vals.errors as Array<Record<string, unknown>>) ?? [],
    completedOutputs,
    retryCount: (vals.retry_count as number) ?? 0,
    lastCheckpoint: (vals.last_checkpoint as string) ?? "",
    checkpointAgent: (vals.checkpoint_agent as string) ?? "",
    humanReviewStatus: (vals.human_review_status as string) ?? null,
    reviewRound: (vals.review_round as number) ?? 0,
    outputContents,
    vsDistributions,
    timingData,
  };
}
```

- [ ] **Step 3: Update listRunningAgents() and listAllAgents() to include projectName**

In `listRunningAgents()`, after getting the latest run, also fetch thread state for project name:

```typescript
export async function listRunningAgents(): Promise<RunningAgent[]> {
  const client = createClient();
  const threads = await client.threads.search({
    status: "busy",
    limit: 50,
  });

  const agents: RunningAgent[] = [];

  for (const thread of threads) {
    const runs = await client.runs.list(thread.thread_id, { limit: 1 });
    const latestRun = runs[0];
    if (latestRun) {
      let projectName = "";
      try {
        const state = await client.threads.getState(thread.thread_id);
        const vals = (state.values as Record<string, unknown>) ?? {};
        projectName = (vals.project_name as string) ?? "";
      } catch { /* thread may not have state yet */ }

      agents.push({
        threadId: thread.thread_id,
        runId: latestRun.run_id,
        graphId: (thread.metadata?.graph_id as string) ?? "unknown",
        status: latestRun.status,
        createdAt: thread.created_at,
        updatedAt: thread.updated_at,
        metadata: (thread.metadata as Record<string, unknown>) ?? {},
        projectName,
      });
    }
  }

  return agents;
}
```

Apply the same pattern to `listAllAgents()`:

```typescript
export async function listAllAgents(): Promise<RunningAgent[]> {
  const client = createClient();
  const threads = await client.threads.search({ limit: 50 });

  const agents: RunningAgent[] = [];

  for (const thread of threads) {
    const runs = await client.runs.list(thread.thread_id, { limit: 1 });
    const latestRun = runs[0];

    let projectName = "";
    try {
      const state = await client.threads.getState(thread.thread_id);
      const vals = (state.values as Record<string, unknown>) ?? {};
      projectName = (vals.project_name as string) ?? "";
    } catch { /* thread may not have state yet */ }

    agents.push({
      threadId: thread.thread_id,
      runId: latestRun?.run_id ?? "",
      graphId: (thread.metadata?.graph_id as string) ?? "unknown",
      status: latestRun?.status ?? "idle",
      createdAt: thread.created_at,
      updatedAt: thread.updated_at,
      metadata: (thread.metadata as Record<string, unknown>) ?? {},
      projectName,
    });
  }

  return agents;
}
```

- [ ] **Step 4: Add retryAgent() function**

Add at the end of `agentsApi.ts`:

```typescript
export async function retryAgent(threadId: string): Promise<string> {
  const client = createClient();
  const run = await client.runs.create(threadId, "needs_package", {});
  return run.run_id;
}
```

- [ ] **Step 5: Add getPreviousRunOutput() function**

Add at the end of `agentsApi.ts`:

```typescript
export async function getPreviousRunOutput(
  projectId: string,
  beforeDate: string,
  outputKey: string,
): Promise<string | null> {
  const client = createClient();
  const threads = await client.threads.search({ limit: 20 });

  for (const thread of threads) {
    if (thread.created_at >= beforeDate) continue;
    try {
      const state = await client.threads.getState(thread.thread_id);
      const vals = (state.values as Record<string, unknown>) ?? {};
      if (vals.project_id === projectId && vals[outputKey] != null) {
        const content = vals[outputKey];
        return typeof content === "string" ? content : JSON.stringify(content);
      }
    } catch {
      continue;
    }
  }
  return null;
}
```

- [ ] **Step 6: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: No errors in `agentsApi.ts`

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/agentsApi.ts
git commit -m "feat(agents): add projectName to RunningAgent, extend ThreadState with outputs/VS/timing"
```

---

### Task 1b: Update agent-tree-item to show project name

**Files:**
- Modify: `frontend/src/components/agents/agent-tree-item.tsx`

- [ ] **Step 1: Add project name display below graph ID**

Replace the tree item content in `agent-tree-item.tsx`:

```typescript
"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { RunningAgent } from "@/lib/agentsApi";

const STATUS_COLORS: Record<string, string> = {
  running: "bg-dhg-orange",
  success: "bg-green-500",
  error: "bg-destructive",
  pending: "bg-muted-foreground/30",
  interrupted: "bg-yellow-500",
};

interface AgentTreeItemProps {
  agent: RunningAgent;
  selected: boolean;
  onClick: () => void;
}

export function AgentTreeItem({ agent, selected, onClick }: AgentTreeItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 w-full text-left px-3 py-2 rounded-md text-xs transition-colors",
        selected ? "bg-primary/10 text-primary" : "text-foreground hover:bg-muted",
      )}
    >
      <span className={cn("h-2 w-2 rounded-full shrink-0", STATUS_COLORS[agent.status] ?? "bg-muted-foreground/30")} />
      <div className="flex-1 min-w-0">
        <span className="block truncate font-medium">{agent.graphId}</span>
        {agent.projectName && (
          <span className="block truncate text-[10px] text-muted-foreground">{agent.projectName}</span>
        )}
      </div>
      <Badge variant="outline" className="text-[9px] shrink-0">
        {agent.status}
      </Badge>
    </button>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/agents/agent-tree-item.tsx
git commit -m "feat(agents): show project name on tree item cards"
```

---

### Task 2: Create agentsStreamApi

**Files:**
- Create: `frontend/src/lib/agentsStreamApi.ts`

- [ ] **Step 1: Create the streaming API module**

```typescript
import { Client } from "@langchain/langgraph-sdk";

const createClient = () => {
  const baseUrl =
    process.env.NEXT_PUBLIC_LANGGRAPH_API_URL ||
    (typeof window !== "undefined"
      ? `${window.location.origin}/api/langgraph`
      : "http://localhost:3000/api/langgraph");
  return new Client({ apiUrl: baseUrl });
};

export interface StreamEvent {
  id: string;
  timestamp: string;
  eventType: string;
  agentName: string;
  message: string;
  level: "info" | "warn" | "error" | "debug";
  tokenUsage?: { inputTokens: number; outputTokens: number };
}

let eventCounter = 0;

function formatTime(): string {
  return new Date().toLocaleTimeString("en-US", { hour12: false });
}

function parseStreamEvent(event: Record<string, unknown>): StreamEvent | null {
  const eventType = event.event as string;
  const name = (event.name as string) ?? "unknown";
  const id = `evt-${++eventCounter}`;
  const timestamp = formatTime();

  switch (eventType) {
    case "on_chain_start":
      return { id, timestamp, eventType, agentName: name, message: "Starting...", level: "info" };
    case "on_chain_end":
      return { id, timestamp, eventType, agentName: name, message: "\u2713 Complete", level: "info" };
    case "on_tool_start":
      return { id, timestamp, eventType, agentName: name, message: `Calling ${name}...`, level: "debug" };
    case "on_tool_end":
      return { id, timestamp, eventType, agentName: name, message: "Tool result received", level: "debug" };
    case "on_llm_end": {
      const output = event.data as Record<string, unknown> | undefined;
      const usage = output?.usage_metadata as { input_tokens?: number; output_tokens?: number } | undefined;
      if (usage) {
        return {
          id, timestamp, eventType, agentName: name,
          message: `LLM complete (${usage.input_tokens ?? 0} in / ${usage.output_tokens ?? 0} out)`,
          level: "debug",
          tokenUsage: {
            inputTokens: usage.input_tokens ?? 0,
            outputTokens: usage.output_tokens ?? 0,
          },
        };
      }
      return null;
    }
    case "on_llm_stream": {
      const chunk = event.data as Record<string, unknown> | undefined;
      const content = (chunk?.content as string) ?? "";
      if (!content) return null;
      return { id, timestamp, eventType, agentName: name, message: content, level: "info" };
    }
    default:
      return null;
  }
}

export async function resolveRunId(threadId: string): Promise<string | null> {
  const client = createClient();
  const runs = await client.runs.list(threadId, { limit: 1 });
  return runs[0]?.run_id ?? null;
}

export async function connectStream(
  threadId: string,
  onEvent: (event: StreamEvent) => void,
  onEnd: () => void,
  signal: AbortSignal,
): Promise<void> {
  const runId = await resolveRunId(threadId);
  if (!runId) {
    onEnd();
    return;
  }

  const client = createClient();
  let batchBuffer: StreamEvent[] = [];
  let batchTimer: ReturnType<typeof setTimeout> | null = null;

  const flushBatch = () => {
    for (const evt of batchBuffer) {
      onEvent(evt);
    }
    batchBuffer = [];
    batchTimer = null;
  };

  try {
    const stream = client.runs.stream(threadId, runId, {
      streamMode: "events",
    });

    for await (const chunk of stream) {
      if (signal.aborted) break;

      const event = chunk as unknown as Record<string, unknown>;
      const parsed = parseStreamEvent(event);
      if (!parsed) continue;

      if (parsed.eventType === "on_llm_stream") {
        batchBuffer.push(parsed);
        if (!batchTimer) {
          batchTimer = setTimeout(flushBatch, 200);
        }
      } else {
        if (batchTimer) {
          clearTimeout(batchTimer);
          flushBatch();
        }
        onEvent(parsed);
      }
    }

    if (batchTimer) {
      clearTimeout(batchTimer);
      flushBatch();
    }
  } catch (e) {
    if (!signal.aborted) {
      onEvent({
        id: `evt-${++eventCounter}`,
        timestamp: formatTime(),
        eventType: "error",
        agentName: "system",
        message: `Stream error: ${(e as Error).message}`,
        level: "error",
      });
    }
  } finally {
    onEnd();
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: No errors in `agentsStreamApi.ts`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/agentsStreamApi.ts
git commit -m "feat(agents): add streaming API with SDK AsyncGenerator and event batching"
```

---

### Task 3: Extend Zustand store

**Files:**
- Modify: `frontend/src/stores/agents-store.ts`

- [ ] **Step 1: Add stream and token state + actions**

Replace the entire file with:

```typescript
"use client";

import { create } from "zustand";
import type { RunningAgent, AssistantInfo, AgentStats, ThreadState } from "@/lib/agentsApi";
import type { StreamEvent } from "@/lib/agentsStreamApi";
import * as agentsApi from "@/lib/agentsApi";
import { connectStream } from "@/lib/agentsStreamApi";

interface TokenUsage {
  inputTokens: number;
  outputTokens: number;
}

interface AgentsState {
  agents: RunningAgent[];
  assistants: AssistantInfo[];
  stats: AgentStats | null;
  selectedAgent: RunningAgent | null;
  selectedState: ThreadState | null;
  loading: boolean;
  error: string | null;
  filter: "running" | "all" | "errors";

  // Stream state
  streamEvents: StreamEvent[];
  streamStatus: "idle" | "connecting" | "streaming" | "ended" | "error";
  tokenUsage: TokenUsage;
  streamAbort: AbortController | null;

  // Actions
  fetchRunning: () => Promise<void>;
  fetchAll: () => Promise<void>;
  fetchAssistants: () => Promise<void>;
  fetchStats: () => Promise<void>;
  fetchThreadState: (threadId: string) => Promise<void>;
  setSelected: (agent: RunningAgent | null) => void;
  setFilter: (filter: AgentsState["filter"]) => void;
  startStream: (threadId: string) => void;
  stopStream: () => void;
  retryRun: (threadId: string) => Promise<void>;
}

export const useAgentsStore = create<AgentsState>((set, get) => ({
  agents: [],
  assistants: [],
  stats: null,
  selectedAgent: null,
  selectedState: null,
  loading: false,
  error: null,
  filter: "all",

  streamEvents: [],
  streamStatus: "idle",
  tokenUsage: { inputTokens: 0, outputTokens: 0 },
  streamAbort: null,

  fetchRunning: async () => {
    set({ loading: true, error: null });
    try {
      const agents = await agentsApi.listRunningAgents();
      set({ agents, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchAll: async () => {
    set({ loading: true, error: null });
    try {
      const agents = await agentsApi.listAllAgents();
      set({ agents, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchAssistants: async () => {
    try {
      const assistants = await agentsApi.listAssistants();
      set({ assistants });
    } catch (e) {
      console.error("Failed to fetch assistants:", e);
    }
  },

  fetchStats: async () => {
    try {
      const stats = await agentsApi.getAgentStats();
      set({ stats });
    } catch (e) {
      console.error("Failed to fetch stats:", e);
    }
  },

  fetchThreadState: async (threadId: string) => {
    try {
      const selectedState = await agentsApi.getThreadState(threadId);
      set({ selectedState });
    } catch (e) {
      set({ selectedState: null });
      console.error("Failed to fetch thread state:", e);
    }
  },

  setSelected: (agent) => {
    const { streamAbort } = get();
    if (streamAbort) streamAbort.abort();
    set({
      selectedAgent: agent,
      selectedState: null,
      streamEvents: [],
      streamStatus: "idle",
      tokenUsage: { inputTokens: 0, outputTokens: 0 },
      streamAbort: null,
    });
  },

  setFilter: (filter) => set({ filter }),

  startStream: (threadId: string) => {
    const { streamAbort: existing } = get();
    if (existing) existing.abort();

    const abort = new AbortController();
    set({
      streamEvents: [],
      streamStatus: "connecting",
      tokenUsage: { inputTokens: 0, outputTokens: 0 },
      streamAbort: abort,
    });

    connectStream(
      threadId,
      (event) => {
        const state = get();
        const newEvents = [...state.streamEvents, event];
        const newTokens = { ...state.tokenUsage };
        if (event.tokenUsage) {
          newTokens.inputTokens += event.tokenUsage.inputTokens;
          newTokens.outputTokens += event.tokenUsage.outputTokens;
        }
        set({
          streamEvents: newEvents,
          streamStatus: "streaming",
          tokenUsage: newTokens,
        });
      },
      () => {
        set({ streamStatus: "ended", streamAbort: null });
      },
      abort.signal,
    );
  },

  stopStream: () => {
    const { streamAbort } = get();
    if (streamAbort) streamAbort.abort();
    set({ streamStatus: "ended", streamAbort: null });
  },

  retryRun: async (threadId: string) => {
    try {
      const newRunId = await agentsApi.retryAgent(threadId);
      const { selectedAgent } = get();
      if (selectedAgent && selectedAgent.threadId === threadId) {
        set({
          selectedAgent: { ...selectedAgent, runId: newRunId, status: "busy", projectName: selectedAgent.projectName },
        });
        get().startStream(threadId);
      }
    } catch (e) {
      console.error("Failed to retry:", e);
    }
  },
}));
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/agents-store.ts
git commit -m "feat(agents): add stream events, token tracking, retry to Zustand store"
```

---

## Chunk 2: Tab Shell + Detail Tab + Stream Tab

### Task 4: Create agent-tabs container

**Files:**
- Create: `frontend/src/components/agents/agent-tabs.tsx`
- Modify: `frontend/src/app/agents/page.tsx`

- [ ] **Step 1: Create agent-tabs.tsx**

```typescript
"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { PipelineProgress } from "./pipeline-progress";
import { StreamTab } from "./stream-tab";
import { DetailTab } from "./detail-tab";
import { VsTab } from "./vs-tab";
import { OutputsTab } from "./outputs-tab";
import { TimelineTab } from "./timeline-tab";
import { useAgentsStore } from "@/stores/agents-store";
import type { RunningAgent, ThreadState } from "@/lib/agentsApi";

function statusBadgeVariant(status: string) {
  if (status === "running" || status === "in_progress" || status === "busy")
    return "default" as const;
  if (status === "success" || status === "complete") return "secondary" as const;
  if (status === "error" || status === "failed") return "destructive" as const;
  return "outline" as const;
}

function autoTab(agent: RunningAgent | null): string {
  if (!agent) return "detail";
  const s = agent.status;
  if (s === "busy") return "stream";
  if (s === "error" || s === "failed" || s === "interrupted") return "detail";
  return "outputs";
}

interface AgentTabsProps {
  agent: RunningAgent;
  state: ThreadState | null;
}

export function AgentTabs({ agent, state }: AgentTabsProps) {
  const streamStatus = useAgentsStore((s) => s.streamStatus);
  const [tab, setTab] = useState(() => autoTab(agent));
  const [prevThreadId, setPrevThreadId] = useState(agent.threadId);

  // Reset tab on thread switch
  if (agent.threadId !== prevThreadId) {
    setPrevThreadId(agent.threadId);
    setTab(autoTab(agent));
  }

  // Auto-start stream for busy threads
  const startStream = useAgentsStore((s) => s.startStream);
  useEffect(() => {
    if (agent.status === "busy") {
      startStream(agent.threadId);
    }
    return () => {
      useAgentsStore.getState().stopStream();
    };
  }, [agent.threadId, agent.status, startStream]);

  const isStreaming = streamStatus === "streaming" || streamStatus === "connecting";

  return (
    <div className="flex flex-col h-full overflow-hidden p-4">
      {/* Persistent header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold">{agent.graphId}</h3>
          {state?.projectName && (
            <p className="text-xs text-muted-foreground mt-0.5">{state.projectName}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={statusBadgeVariant(agent.status)}>{agent.status}</Badge>
          {state?.humanReviewStatus && (
            <Badge variant="outline" className="text-[9px]">
              Review: {state.humanReviewStatus}
            </Badge>
          )}
        </div>
      </div>

      {/* Pipeline progress — always visible */}
      {state && <PipelineProgress state={state} graphId={agent.graphId} />}

      {/* Tabs */}
      <Tabs value={tab} onValueChange={setTab} className="flex flex-col flex-1 overflow-hidden mt-3">
        <TabsList className="w-full justify-start">
          <TabsTrigger value="stream" className="relative">
            Stream
            {isStreaming && (
              <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-orange-500 animate-pulse" />
            )}
          </TabsTrigger>
          <TabsTrigger value="detail">Detail</TabsTrigger>
          <TabsTrigger value="vs">VS</TabsTrigger>
          <TabsTrigger value="outputs">Outputs</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
        </TabsList>

        <TabsContent value="stream" className="flex-1 overflow-hidden mt-2">
          <StreamTab agent={agent} />
        </TabsContent>
        <TabsContent value="detail" className="flex-1 overflow-auto mt-2">
          <DetailTab agent={agent} state={state} />
        </TabsContent>
        <TabsContent value="vs" className="flex-1 overflow-auto mt-2">
          <VsTab state={state} />
        </TabsContent>
        <TabsContent value="outputs" className="flex-1 overflow-auto mt-2">
          <OutputsTab agent={agent} state={state} />
        </TabsContent>
        <TabsContent value="timeline" className="flex-1 overflow-auto mt-2">
          <TimelineTab agent={agent} state={state} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

- [ ] **Step 2: Update agents page to use AgentTabs**

Replace `frontend/src/app/agents/page.tsx` with:

```typescript
"use client";

import { useEffect, useRef } from "react";
import { AgentTree } from "@/components/agents/agent-tree";
import { AgentTabs } from "@/components/agents/agent-tabs";
import { StatsBar } from "@/components/agents/stats-bar";
import { AssistantsRegistry } from "@/components/agents/assistants-registry";
import { useAgentsStore } from "@/stores/agents-store";

export default function AgentsPage() {
  const {
    selectedAgent,
    selectedState,
    assistants,
    stats,
    filter,
    fetchRunning,
    fetchAll,
    fetchAssistants,
    fetchStats,
    fetchThreadState,
  } = useAgentsStore();
  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    fetchAssistants();
    fetchStats();
  }, [fetchAssistants, fetchStats]);

  useEffect(() => {
    const fetch = filter === "all" ? fetchAll : fetchRunning;
    fetch();
    fetchStats();
    intervalRef.current = setInterval(() => {
      fetch();
      fetchStats();
    }, 5000);
    return () => clearInterval(intervalRef.current);
  }, [filter, fetchRunning, fetchAll, fetchStats]);

  useEffect(() => {
    if (!selectedAgent) return;
    fetchThreadState(selectedAgent.threadId);
    const id = setInterval(() => fetchThreadState(selectedAgent.threadId), 5000);
    return () => clearInterval(id);
  }, [selectedAgent, fetchThreadState]);

  const showRegistry = !selectedAgent;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <StatsBar stats={stats} />
      <div className="flex flex-1 overflow-hidden">
        <AgentTree />
        <div className="flex-1 overflow-hidden">
          {showRegistry ? (
            <AssistantsRegistry assistants={assistants} />
          ) : (
            <AgentTabs agent={selectedAgent} state={selectedState} />
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/agents/agent-tabs.tsx frontend/src/app/agents/page.tsx
git commit -m "feat(agents): add tabbed detail container with auto-selection"
```

---

### Task 5: Create detail-tab (refactor from agent-detail)

**Files:**
- Create: `frontend/src/components/agents/detail-tab.tsx`

- [ ] **Step 1: Create detail-tab.tsx**

Extract metrics, IDs, errors from `agent-detail.tsx` and add token/cost cards + retry button:

```typescript
"use client";

import { Clock, Hash, Shield, RotateCcw, Coins, Zap, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAgentsStore } from "@/stores/agents-store";
import type { RunningAgent, ThreadState } from "@/lib/agentsApi";

interface DetailTabProps {
  agent: RunningAgent;
  state: ThreadState | null;
}

function formatDuration(start: string, end: string): string {
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms}ms`;
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem}s`;
}

function formatTokens(n: number): string {
  if (n === 0) return "\u2014";
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function estimateCost(input: number, output: number): string {
  if (input === 0 && output === 0) return "\u2014";
  const cost = (input * 3 + output * 15) / 1_000_000;
  return `$${cost.toFixed(4)}`;
}

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border px-3 py-2">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon className="h-3 w-3 text-muted-foreground" />
        <span className="text-[10px] text-muted-foreground">{label}</span>
      </div>
      <p className="text-xs font-medium truncate capitalize">{value}</p>
    </div>
  );
}

export function DetailTab({ agent, state }: DetailTabProps) {
  const tokenUsage = useAgentsStore((s) => s.tokenUsage);
  const retryRun = useAgentsStore((s) => s.retryRun);

  const duration =
    agent.updatedAt && agent.createdAt
      ? formatDuration(agent.createdAt, agent.updatedAt)
      : "\u2014";

  return (
    <div className="space-y-5">
      {/* Key Metrics */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
        <MetricCard icon={Clock} label="Duration" value={duration} />
        <MetricCard
          icon={Hash}
          label="Step"
          value={state?.currentStep.replace(/_/g, " ") ?? "\u2014"}
        />
        <MetricCard icon={RotateCcw} label="Retries" value={String(state?.retryCount ?? 0)} />
        <MetricCard icon={Shield} label="Review Round" value={String(state?.reviewRound ?? 0)} />
        <MetricCard icon={Zap} label="Tokens" value={formatTokens(tokenUsage.inputTokens + tokenUsage.outputTokens)} />
        <MetricCard icon={Coins} label="Est. Cost" value={estimateCost(tokenUsage.inputTokens, tokenUsage.outputTokens)} />
      </div>

      {/* IDs */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <span className="text-muted-foreground">Thread ID</span>
          <p className="font-mono truncate text-[10px]">{agent.threadId}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Run ID</span>
          <p className="font-mono truncate text-[10px]">{agent.runId}</p>
        </div>
        {state?.projectId && (
          <div>
            <span className="text-muted-foreground">Project ID</span>
            <p className="font-mono truncate text-[10px]">{state.projectId}</p>
          </div>
        )}
        {state?.lastCheckpoint && (
          <div>
            <span className="text-muted-foreground">Last Checkpoint</span>
            <p className="text-[10px]">
              {new Date(state.lastCheckpoint).toLocaleTimeString()} &mdash;{" "}
              {state.checkpointAgent.replace(/_/g, " ")}
            </p>
          </div>
        )}
      </div>

      {/* Errors */}
      {state && state.errors.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-destructive mb-2">
            Errors ({state.errors.length})
          </h4>
          <div className="space-y-1.5">
            {state.errors.map((err, i) => (
              <div
                key={i}
                className="flex items-start justify-between rounded-md bg-destructive/10 px-3 py-2"
              >
                <div className="text-[11px] text-destructive">
                  <span className="font-medium">
                    [{String(err.agent ?? "unknown")}]
                  </span>{" "}
                  {String(err.message ?? "Unknown error")}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-[10px] shrink-0 ml-2"
                  onClick={() => retryRun(agent.threadId)}
                >
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Retry
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/agents/detail-tab.tsx
git commit -m "feat(agents): create detail tab with token/cost metrics and retry"
```

---

### Task 6: Extend log-stream and create stream-tab

**Files:**
- Modify: `frontend/src/components/agents/log-stream.tsx`
- Create: `frontend/src/components/agents/stream-tab.tsx`

- [ ] **Step 1: Update log-stream.tsx with scroll lock and no max height**

Replace the entire file:

```typescript
"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface LogEntry {
  id: string;
  timestamp: string;
  source: string;
  message: string;
  level: "info" | "warn" | "error" | "debug";
}

const LEVEL_COLORS: Record<string, string> = {
  info: "text-green-400",
  warn: "text-yellow-400",
  error: "text-red-400",
  debug: "text-blue-400",
};

interface LogStreamProps {
  logs: LogEntry[];
  footer?: string;
}

export function LogStream({ logs, footer }: LogStreamProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [scrollLocked, setScrollLocked] = useState(true);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setScrollLocked(atBottom);
  }, []);

  useEffect(() => {
    if (scrollLocked) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs.length, scrollLocked]);

  return (
    <div className="relative h-full flex flex-col">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="bg-[#0d1117] text-[#c9d1d9] rounded-md p-3 font-mono text-[11px] leading-relaxed overflow-auto flex-1"
      >
        {logs.length === 0 ? (
          <p className="text-gray-500">Waiting for stream events...</p>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="flex gap-2">
              <span className="text-gray-500 shrink-0">{log.timestamp}</span>
              <span
                className={`shrink-0 ${LEVEL_COLORS[log.level] ?? "text-gray-400"}`}
              >
                {log.source}
              </span>
              <span>{log.message}</span>
            </div>
          ))
        )}
        {footer && (
          <div className="text-gray-500 mt-2 pt-2 border-t border-gray-700">
            {footer}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      {!scrollLocked && logs.length > 0 && (
        <button
          onClick={() => {
            setScrollLocked(true);
            bottomRef.current?.scrollIntoView({ behavior: "smooth" });
          }}
          className="absolute bottom-3 right-3 bg-gray-700 text-gray-300 text-[10px] px-2 py-1 rounded hover:bg-gray-600"
        >
          ↓ Follow
        </button>
      )}
    </div>
  );
}

export type { LogEntry };
```

- [ ] **Step 2: Create stream-tab.tsx**

```typescript
"use client";

import { LogStream } from "./log-stream";
import { useAgentsStore } from "@/stores/agents-store";
import type { RunningAgent } from "@/lib/agentsApi";

interface StreamTabProps {
  agent: RunningAgent;
}

export function StreamTab({ agent }: StreamTabProps) {
  const streamEvents = useAgentsStore((s) => s.streamEvents);
  const streamStatus = useAgentsStore((s) => s.streamStatus);

  const logs = streamEvents.map((evt) => ({
    id: evt.id,
    timestamp: evt.timestamp,
    source: evt.agentName,
    message: evt.message,
    level: evt.level,
  }));

  const isIdle = agent.status !== "busy" && streamStatus === "idle";

  if (isIdle) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        No active stream — this thread is not running.
      </div>
    );
  }

  const footer =
    streamStatus === "ended"
      ? `Stream ended at ${new Date().toLocaleTimeString()}`
      : undefined;

  return (
    <div className="h-full">
      <LogStream logs={logs} footer={footer} />
    </div>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/agents/log-stream.tsx frontend/src/components/agents/stream-tab.tsx
git commit -m "feat(agents): add stream tab with scroll lock and connection lifecycle"
```

---

## Chunk 3: VS Tab + Outputs Tab + Slide-Over

### Task 7: Create VS sparkline and VS tab

**Files:**
- Create: `frontend/src/components/agents/vs-sparkline.tsx`
- Create: `frontend/src/components/agents/vs-tab.tsx`

- [ ] **Step 1: Create vs-sparkline.tsx**

```typescript
interface VsSparklineProps {
  scores: number[];
  maxScore?: number;
}

export function VsSparkline({ scores, maxScore = 1 }: VsSparklineProps) {
  if (scores.length === 0) return null;

  return (
    <div className="flex items-end gap-0.5 h-4">
      {scores
        .sort((a, b) => b - a)
        .map((score, i) => (
          <div
            key={i}
            className="w-2 rounded-sm"
            style={{
              height: `${(score / maxScore) * 100}%`,
              backgroundColor:
                i === 0
                  ? "var(--dhg-border-focus, #663399)"
                  : "var(--dhg-text-placeholder, #A1A1AA)",
              opacity: i === 0 ? 1 : 0.5,
            }}
          />
        ))}
    </div>
  );
}
```

- [ ] **Step 2: Create vs-tab.tsx**

```typescript
"use client";

import { useState } from "react";
import { VsSparkline } from "./vs-sparkline";
import type { ThreadState, VsDistribution } from "@/lib/agentsApi";

const AGENT_LABELS: Record<string, string> = {
  needs_assessment: "Needs Assessment",
  research: "Research",
  clinical_practice: "Clinical Practice",
  gap_analysis: "Gap Analysis",
  learning_objectives: "Learning Objectives",
  curriculum_design: "Curriculum Design",
  research_protocol: "Research Protocol",
  marketing_plan: "Marketing Plan",
  grant_writer: "Grant Writer",
};

interface VsTabProps {
  state: ThreadState | null;
}

export function VsTab({ state }: VsTabProps) {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  if (!state || Object.keys(state.vsDistributions).length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        No VS distributions available
      </div>
    );
  }

  const entries = Object.entries(state.vsDistributions);

  return (
    <div className="space-y-1">
      {/* Header */}
      <div className="grid grid-cols-[1fr_2fr_80px_80px_60px_60px] gap-2 px-3 py-2 text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
        <span>Agent</span>
        <span>Selected Approach</span>
        <span className="text-right">Confidence</span>
        <span className="text-right">Runner-Up</span>
        <span className="text-right">Spread</span>
        <span>Dist.</span>
      </div>

      {entries.map(([agentName, dist]: [string, VsDistribution]) => {
        const sorted = [...dist.candidates].sort((a, b) => b.score - a.score);
        const runnerUp = sorted.length > 1 ? sorted[1] : null;
        const spread = runnerUp
          ? (dist.selected.score - runnerUp.score).toFixed(2)
          : "\u2014";
        const isExpanded = expandedAgent === agentName;

        return (
          <div key={agentName}>
            <button
              onClick={() => setExpandedAgent(isExpanded ? null : agentName)}
              className="w-full grid grid-cols-[1fr_2fr_80px_80px_60px_60px] gap-2 px-3 py-2.5 text-xs hover:bg-muted/50 rounded-md transition-colors items-center"
            >
              <span className="font-medium text-left truncate">
                {AGENT_LABELS[agentName] ?? agentName}
              </span>
              <span className="text-left truncate text-muted-foreground">
                {dist.selected.name}
              </span>
              <span className="text-right font-mono">
                {dist.selected.score.toFixed(2)}
              </span>
              <span className="text-right font-mono text-muted-foreground">
                {runnerUp?.score.toFixed(2) ?? "\u2014"}
              </span>
              <span className="text-right font-mono">{spread}</span>
              <VsSparkline scores={dist.candidates.map((c) => c.score)} />
            </button>

            {isExpanded && (
              <div className="mx-3 mb-2 p-3 rounded-md bg-muted/30 space-y-2">
                <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
                  All Candidates
                </p>
                {sorted.map((candidate, i) => (
                  <div
                    key={i}
                    className={`flex justify-between text-[11px] px-2 py-1.5 rounded ${
                      candidate === dist.selected
                        ? "bg-primary/10 font-medium"
                        : ""
                    }`}
                  >
                    <div className="flex-1">
                      <span className="font-medium">{candidate.name}</span>
                      {candidate.description && (
                        <p className="text-[10px] text-muted-foreground mt-0.5">
                          {candidate.description}
                        </p>
                      )}
                    </div>
                    <span className="font-mono ml-4 shrink-0">
                      {candidate.score.toFixed(3)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/agents/vs-sparkline.tsx frontend/src/components/agents/vs-tab.tsx
git commit -m "feat(agents): add VS distribution tab with sparklines and expandable rows"
```

---

### Task 8: Create outputs-tab and output-slide-over

**Files:**
- Create: `frontend/src/components/agents/outputs-tab.tsx`
- Create: `frontend/src/components/agents/output-slide-over.tsx`

- [ ] **Step 1: Create output-slide-over.tsx**

```typescript
"use client";

import { useState, useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip";
import { getPreviousRunOutput } from "@/lib/agentsApi";

const OUTPUT_LABELS: Record<string, string> = {
  research_output: "Research & Literature",
  clinical_output: "Clinical Practice",
  gap_analysis_output: "Gap Analysis",
  learning_objectives_output: "Learning Objectives",
  needs_assessment_output: "Needs Assessment",
  curriculum_output: "Curriculum Design",
  protocol_output: "Research Protocol",
  marketing_output: "Marketing Plan",
  grant_package_output: "Grant Package",
  prose_quality_pass_1: "Prose QA Pass 1",
  prose_quality_pass_2: "Prose QA Pass 2",
  compliance_result: "Compliance Review",
};

interface OutputSlideOverProps {
  open: boolean;
  onClose: () => void;
  outputKey: string;
  content: string;
  projectId: string;
  threadCreatedAt: string;
}

function wordCount(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

function lineDiff(current: string, previous: string): { left: string[]; right: string[] } {
  const currentLines = current.split("\n");
  const previousLines = previous.split("\n");
  return { left: currentLines, right: previousLines };
}

export function OutputSlideOver({
  open,
  onClose,
  outputKey,
  content,
  projectId,
  threadCreatedAt,
}: OutputSlideOverProps) {
  const [showDiff, setShowDiff] = useState(false);
  const [previousContent, setPreviousContent] = useState<string | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffChecked, setDiffChecked] = useState(false);

  useEffect(() => {
    if (!open) {
      setShowDiff(false);
      setPreviousContent(null);
      setDiffChecked(false);
      return;
    }

    setDiffLoading(true);
    getPreviousRunOutput(projectId, threadCreatedAt, outputKey)
      .then((prev) => {
        setPreviousContent(prev);
        setDiffChecked(true);
      })
      .catch(() => {
        setPreviousContent(null);
        setDiffChecked(true);
      })
      .finally(() => setDiffLoading(false));
  }, [open, projectId, threadCreatedAt, outputKey]);

  const label = OUTPUT_LABELS[outputKey] ?? outputKey.replace(/_/g, " ");
  const words = wordCount(content);

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-[60vw] sm:max-w-none overflow-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center justify-between">
            <span>{label}</span>
            <div className="flex items-center gap-3 text-xs font-normal text-muted-foreground">
              <span>{words.toLocaleString()} words</span>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-[11px]"
                        disabled={!diffChecked || previousContent === null}
                        onClick={() => setShowDiff(!showDiff)}
                      >
                        {showDiff ? "Hide Diff" : "Compare"}
                      </Button>
                    </span>
                  </TooltipTrigger>
                  {diffChecked && previousContent === null && (
                    <TooltipContent>No previous run to compare</TooltipContent>
                  )}
                </Tooltip>
              </TooltipProvider>
            </div>
          </SheetTitle>
        </SheetHeader>

        <div className="mt-4">
          {showDiff && previousContent ? (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-[10px] text-muted-foreground font-medium uppercase mb-2">
                  Current Run
                </p>
                <div className="text-sm leading-relaxed whitespace-pre-wrap font-[Inter]">
                  {lineDiff(content, previousContent).left.map((line, i) => {
                    const prevLines = previousContent.split("\n");
                    const isNew = !prevLines.includes(line) && line.trim() !== "";
                    return (
                      <div
                        key={i}
                        className={isNew ? "bg-green-500/10 px-1 -mx-1 rounded" : ""}
                      >
                        {line || "\u00A0"}
                      </div>
                    );
                  })}
                </div>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground font-medium uppercase mb-2">
                  Previous Run
                </p>
                <div className="text-sm leading-relaxed whitespace-pre-wrap font-[Inter]">
                  {lineDiff(content, previousContent).right.map((line, i) => {
                    const currentLines = content.split("\n");
                    const isRemoved = !currentLines.includes(line) && line.trim() !== "";
                    return (
                      <div
                        key={i}
                        className={isRemoved ? "bg-red-500/10 px-1 -mx-1 rounded" : ""}
                      >
                        {line || "\u00A0"}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-sm leading-relaxed whitespace-pre-wrap font-[Inter]">
              {content}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 2: Create outputs-tab.tsx**

```typescript
"use client";

import { useState } from "react";
import { FileText } from "lucide-react";
import { OutputSlideOver } from "./output-slide-over";
import { OUTPUT_KEYS } from "@/lib/agentsApi";
import type { RunningAgent, ThreadState } from "@/lib/agentsApi";

const OUTPUT_LABELS: Record<string, string> = {
  research_output: "Research & Literature",
  clinical_output: "Clinical Practice",
  gap_analysis_output: "Gap Analysis",
  learning_objectives_output: "Learning Objectives",
  needs_assessment_output: "Needs Assessment",
  curriculum_output: "Curriculum Design",
  protocol_output: "Research Protocol",
  marketing_output: "Marketing Plan",
  grant_package_output: "Grant Package",
  prose_quality_pass_1: "Prose QA Pass 1",
  prose_quality_pass_2: "Prose QA Pass 2",
  compliance_result: "Compliance Review",
};

function preview(text: string, maxLen = 150): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen).trimEnd() + "...";
}

function wordCount(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

interface OutputsTabProps {
  agent: RunningAgent;
  state: ThreadState | null;
}

export function OutputsTab({ agent, state }: OutputsTabProps) {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  if (!state || state.completedOutputs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        No completed outputs yet
      </div>
    );
  }

  // Order by pipeline sequence
  const ordered = OUTPUT_KEYS.filter((k) => state.completedOutputs.includes(k));

  return (
    <>
      <div className="grid grid-cols-2 gap-3">
        {ordered.map((key) => {
          const content = state.outputContents[key] ?? "";
          const label = OUTPUT_LABELS[key] ?? key.replace(/_/g, " ");
          const words = wordCount(content);

          return (
            <button
              key={key}
              onClick={() => setSelectedKey(key)}
              className="flex items-start gap-3 p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors text-left"
            >
              <FileText className="h-4 w-4 text-green-600 dark:text-green-400 shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="text-xs font-medium">{label}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  {words.toLocaleString()} words
                </p>
                {content && (
                  <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">
                    {preview(content)}
                  </p>
                )}
              </div>
            </button>
          );
        })}
      </div>

      <OutputSlideOver
        open={selectedKey !== null}
        onClose={() => setSelectedKey(null)}
        outputKey={selectedKey ?? ""}
        content={selectedKey ? (state.outputContents[selectedKey] ?? "") : ""}
        projectId={state.projectId}
        threadCreatedAt={agent.createdAt}
      />
    </>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/agents/outputs-tab.tsx frontend/src/components/agents/output-slide-over.tsx
git commit -m "feat(agents): add outputs tab with slide-over viewer and diff toggle"
```

---

## Chunk 4: Timeline Tab + Cleanup

### Task 9: Create timeline-tab

**Files:**
- Create: `frontend/src/components/agents/timeline-tab.tsx`

- [ ] **Step 1: Create timeline-tab.tsx**

```typescript
"use client";

import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip";
import { useAgentsStore } from "@/stores/agents-store";
import type { RunningAgent, ThreadState } from "@/lib/agentsApi";

const PIPELINE_ORDER = [
  "research",
  "clinical_practice",
  "gap_analysis",
  "learning_objectives",
  "needs_assessment",
  "curriculum_design",
  "research_protocol",
  "marketing_plan",
  "grant_writer",
  "prose_quality_1",
  "prose_quality_2",
  "compliance_review",
];

const AGENT_LABELS: Record<string, string> = {
  research: "Research",
  clinical_practice: "Clinical Practice",
  gap_analysis: "Gap Analysis",
  learning_objectives: "Learning Objectives",
  needs_assessment: "Needs Assessment",
  curriculum_design: "Curriculum Design",
  research_protocol: "Research Protocol",
  marketing_plan: "Marketing Plan",
  grant_writer: "Grant Writer",
  prose_quality_1: "Prose QA 1",
  prose_quality_2: "Prose QA 2",
  compliance_review: "Compliance",
};

const STATUS_COLORS: Record<string, string> = {
  complete: "bg-green-500",
  running: "bg-orange-500 animate-pulse",
  failed: "bg-red-500",
  pending: "bg-gray-300 dark:bg-gray-600",
};

function formatMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${s % 60}s`;
}

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

interface TimelineTabProps {
  agent: RunningAgent;
  state: ThreadState | null;
}

export function TimelineTab({ agent, state }: TimelineTabProps) {
  const tokenUsage = useAgentsStore((s) => s.tokenUsage);
  const streamEvents = useAgentsStore((s) => s.streamEvents);

  if (!state) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        No timeline data available
      </div>
    );
  }

  const timingData = state.timingData;
  const hasTimingData = Object.keys(timingData).length > 0;

  if (!hasTimingData && streamEvents.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        Timeline unavailable &mdash; view in LangSmith
      </div>
    );
  }

  // Calculate timeline bounds
  let minTime = Infinity;
  let maxTime = 0;

  const agentBars: Array<{
    name: string;
    label: string;
    startMs: number;
    endMs: number;
    status: string;
    tokens?: number;
  }> = [];

  for (const agentKey of PIPELINE_ORDER) {
    const timing = timingData[agentKey];
    if (!timing?.startedAt) continue;

    const startMs = new Date(timing.startedAt).getTime();
    const endMs = timing.completedAt
      ? new Date(timing.completedAt).getTime()
      : Date.now();

    minTime = Math.min(minTime, startMs);
    maxTime = Math.max(maxTime, endMs);

    const isComplete = state.completedOutputs.some((k) =>
      k.toLowerCase().includes(agentKey.replace(/_/g, "")),
    );
    const isCurrent = state.currentStep === agentKey;
    const hasFailed = state.errors.some(
      (e) => String(e.agent) === agentKey,
    );

    agentBars.push({
      name: agentKey,
      label: AGENT_LABELS[agentKey] ?? agentKey,
      startMs,
      endMs,
      status: hasFailed
        ? "failed"
        : isComplete
          ? "complete"
          : isCurrent
            ? "running"
            : "pending",
    });
  }

  const totalDuration = maxTime - minTime || 1;

  const pipelineDuration = formatMs(totalDuration);
  const totalTokens = tokenUsage.inputTokens + tokenUsage.outputTokens;
  const totalCost =
    totalTokens > 0
      ? `$${((tokenUsage.inputTokens * 3 + tokenUsage.outputTokens * 15) / 1_000_000).toFixed(4)}`
      : "\u2014";

  return (
    <TooltipProvider>
      <div className="space-y-1">
        {agentBars.map((bar) => {
          const leftPercent = ((bar.startMs - minTime) / totalDuration) * 100;
          const widthPercent = Math.max(
            ((bar.endMs - bar.startMs) / totalDuration) * 100,
            2,
          );
          const duration = formatMs(bar.endMs - bar.startMs);

          return (
            <div
              key={bar.name}
              className="grid grid-cols-[140px_1fr] gap-3 items-center"
            >
              <span className="text-[11px] text-right truncate text-muted-foreground">
                {bar.label}
              </span>
              <div className="relative h-6 bg-muted/30 rounded">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div
                      className={`absolute top-0.5 bottom-0.5 rounded ${STATUS_COLORS[bar.status] ?? STATUS_COLORS.pending}`}
                      style={{
                        left: `${leftPercent}%`,
                        width: `${widthPercent}%`,
                        minWidth: "8px",
                      }}
                    >
                      {widthPercent > 15 && (
                        <span className="absolute right-1.5 top-1/2 -translate-y-1/2 text-[9px] text-white/80 font-mono">
                          {duration}
                        </span>
                      )}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs">
                      {bar.label}: {duration}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
            </div>
          );
        })}

        {/* Summary row */}
        <div className="grid grid-cols-[140px_1fr] gap-3 items-center pt-2 mt-2 border-t border-border">
          <span className="text-[11px] text-right font-medium">Total</span>
          <div className="flex gap-4 text-[11px] text-muted-foreground">
            <span>{pipelineDuration}</span>
            <span>{formatTokens(totalTokens)} tokens</span>
            <span>{totalCost}</span>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/agents/timeline-tab.tsx
git commit -m "feat(agents): add timeline tab with Gantt bars and cost summary"
```

---

### Task 10: Remove old agent-detail.tsx and verify build

**Files:**
- Delete: `frontend/src/components/agents/agent-detail.tsx`

- [ ] **Step 1: Delete agent-detail.tsx**

```bash
git rm frontend/src/components/agents/agent-detail.tsx
```

- [ ] **Step 2: Check for any remaining imports of AgentDetail**

Run: `cd frontend && grep -r "agent-detail\|AgentDetail" src/ --include="*.ts" --include="*.tsx"`
Expected: No results (page.tsx no longer imports it)

- [ ] **Step 3: Full TypeScript check**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -50`
Expected: No errors

- [ ] **Step 4: Build check**

Run: `cd frontend && npm run build 2>&1 | tail -20`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(agents): remove old agent-detail, all functionality now in tabs"
```

---

### Task 11: Docker rebuild and verify

- [ ] **Step 1: Rebuild frontend container**

```bash
docker compose build --no-cache dhg-frontend
docker compose up -d dhg-frontend
```

- [ ] **Step 2: Wait for healthy**

```bash
docker compose ps dhg-frontend
```

Expected: Status `healthy`

- [ ] **Step 3: Verify agents page loads in browser**

Navigate to `https://app.digitalharmonyai.com/agents`:
- Stats bar shows at top
- Thread tree on left
- Click a thread → tabbed panel appears with 5 tabs
- Completed thread → auto-selects Outputs tab
- Running thread (if any) → auto-selects Stream tab with live events

- [ ] **Step 4: Commit and push**

```bash
git push origin master
```
