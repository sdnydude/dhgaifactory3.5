"use client";

import { create } from "zustand";
import type {
  CMEProjectDetail,
  ExecutionStatus,
  PipelineRun,
} from "@/types/cme";
import * as registryApi from "@/lib/registryApi";

interface ProjectsState {
  projects: CMEProjectDetail[];
  currentProject: CMEProjectDetail | null;
  pipelineStatus: ExecutionStatus | null;

  // Pipeline run history (keyed by projectId so switching projects doesn't
  // leak state across views).
  runsByProject: Record<string, PipelineRun[]>;
  runsLoading: boolean;

  loading: boolean;
  error: string | null;

  fetchProjects: () => Promise<void>;
  fetchProject: (id: string) => Promise<void>;
  fetchPipelineStatus: (id: string) => Promise<void>;
  archiveProject: (id: string) => Promise<void>;

  fetchRuns: (projectId: string) => Promise<void>;
  cancelRun: (projectId: string) => Promise<PipelineRun | null>;
  rerunPipeline: (
    projectId: string,
    reason?: string,
  ) => Promise<PipelineRun | null>;

  clearCurrent: () => void;
}

export const useProjectsStore = create<ProjectsState>((set, get) => ({
  projects: [],
  currentProject: null,
  pipelineStatus: null,
  runsByProject: {},
  runsLoading: false,
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

  fetchRuns: async (projectId: string) => {
    set({ runsLoading: true, error: null });
    try {
      const response = await registryApi.listPipelineRuns(projectId);
      set((s) => ({
        runsByProject: { ...s.runsByProject, [projectId]: response.runs },
        runsLoading: false,
      }));
    } catch (e) {
      set({ error: (e as Error).message, runsLoading: false });
    }
  },

  cancelRun: async (projectId: string) => {
    try {
      const run = await registryApi.cancelPipeline(projectId);
      // Refresh the project detail and run history so the UI reflects the
      // terminal state without a manual reload.
      await Promise.all([
        get().fetchProject(projectId),
        get().fetchRuns(projectId),
      ]);
      return run;
    } catch (e) {
      set({ error: (e as Error).message });
      return null;
    }
  },

  rerunPipeline: async (projectId: string, reason?: string) => {
    try {
      const run = await registryApi.rerunPipeline(projectId, { reason });
      await Promise.all([
        get().fetchProject(projectId),
        get().fetchRuns(projectId),
      ]);
      return run;
    } catch (e) {
      set({ error: (e as Error).message });
      return null;
    }
  },

  clearCurrent: () =>
    set({ currentProject: null, pipelineStatus: null, runsLoading: false }),
}));
