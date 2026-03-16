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
    const { selectedAgent } = get();
    const graphId = selectedAgent?.graphId ?? "needs_package";
    try {
      const newRunId = await agentsApi.retryAgent(threadId, graphId);
      if (selectedAgent && selectedAgent.threadId === threadId) {
        set({
          selectedAgent: { ...selectedAgent, runId: newRunId, status: "busy" },
        });
        get().startStream(threadId);
      }
    } catch (e) {
      console.error("Failed to retry:", e);
    }
  },
}));
