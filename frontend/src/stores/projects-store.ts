"use client";

import { create } from "zustand";
import type { CMEProjectDetail, ExecutionStatus } from "@/types/cme";
import * as registryApi from "@/lib/registryApi";

interface ProjectsState {
  projects: CMEProjectDetail[];
  currentProject: CMEProjectDetail | null;
  pipelineStatus: ExecutionStatus | null;
  loading: boolean;
  error: string | null;

  fetchProjects: () => Promise<void>;
  fetchProject: (id: string) => Promise<void>;
  fetchPipelineStatus: (id: string) => Promise<void>;
  archiveProject: (id: string) => Promise<void>;
  clearCurrent: () => void;
}

export const useProjectsStore = create<ProjectsState>((set) => ({
  projects: [],
  currentProject: null,
  pipelineStatus: null,
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const projects = await registryApi.listProjects();
      set({ projects, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchProject: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const project = await registryApi.getProject(id);
      set({ currentProject: project, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchPipelineStatus: async (id: string) => {
    try {
      const status = await registryApi.getPipelineStatus(id);
      set({ pipelineStatus: status });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  archiveProject: async (id: string) => {
    try {
      await registryApi.archiveProject(id);
      set((s) => ({
        projects: s.projects.filter((p) => p.id !== id),
        currentProject:
          s.currentProject?.id === id ? null : s.currentProject,
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  clearCurrent: () => set({ currentProject: null, pipelineStatus: null }),
}));
