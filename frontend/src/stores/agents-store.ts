"use client";

import { create } from "zustand";
import type { RunningAgent, AssistantInfo, AgentStats, ThreadState } from "@/lib/agentsApi";
import * as agentsApi from "@/lib/agentsApi";

interface AgentsState {
  agents: RunningAgent[];
  assistants: AssistantInfo[];
  stats: AgentStats | null;
  selectedAgent: RunningAgent | null;
  selectedState: ThreadState | null;
  loading: boolean;
  error: string | null;
  filter: "running" | "all" | "errors";

  fetchRunning: () => Promise<void>;
  fetchAll: () => Promise<void>;
  fetchAssistants: () => Promise<void>;
  fetchStats: () => Promise<void>;
  fetchThreadState: (threadId: string) => Promise<void>;
  setSelected: (agent: RunningAgent | null) => void;
  setFilter: (filter: AgentsState["filter"]) => void;
}

export const useAgentsStore = create<AgentsState>((set) => ({
  agents: [],
  assistants: [],
  stats: null,
  selectedAgent: null,
  selectedState: null,
  loading: false,
  error: null,
  filter: "all",

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

  setSelected: (agent) => set({ selectedAgent: agent, selectedState: null }),
  setFilter: (filter) => set({ filter }),
}));
