"use client";

import { create } from "zustand";
import type {
  IncidentListItem,
  IncidentDetail,
  IncidentStats,
} from "@/lib/incidentsApi";
import * as api from "@/lib/incidentsApi";
import { useAppStore } from "@/stores/app-store";

interface IncidentsState {
  incidents: IncidentListItem[];
  selectedIncident: IncidentDetail | null;
  stats: IncidentStats | null;
  loading: boolean;
  detailLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;

  // Filters
  filterStatus: string | null;
  filterSeverity: string | null;
  filterCategory: string | null;

  // Mutation loading
  actionLoading: boolean;

  // Actions
  fetchAll: () => Promise<void>;
  fetchIncidents: () => Promise<void>;
  fetchStats: () => Promise<void>;
  selectIncident: (id: string | null) => Promise<void>;
  mitigateIncident: (id: string) => Promise<void>;
  resolveIncident: (id: string) => Promise<void>;
  setFilterStatus: (status: string | null) => void;
  setFilterSeverity: (severity: string | null) => void;
  setFilterCategory: (category: string | null) => void;
  clearFilters: () => void;
}

export const useIncidentsStore = create<IncidentsState>((set, get) => ({
  incidents: [],
  selectedIncident: null,
  stats: null,
  loading: false,
  detailLoading: false,
  error: null,
  lastUpdated: null,

  filterStatus: null,
  filterSeverity: null,
  filterCategory: null,
  actionLoading: false,

  fetchAll: async () => {
    if (get().loading) return;
    set({ loading: true, error: null });
    try {
      const state = get();
      const [incidents, stats] = await Promise.all([
        api.listIncidents({
          status: state.filterStatus ?? undefined,
          severity: state.filterSeverity ?? undefined,
          category: state.filterCategory ?? undefined,
          limit: 100,
        }),
        api.getStats(30),
      ]);
      const activeCount = incidents.filter((i) => i.status === "active").length;
      useAppStore.getState().setBadgeCounts({ incidents: activeCount });
      set({ incidents, stats, loading: false, lastUpdated: new Date() });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchIncidents: async () => {
    try {
      const state = get();
      const incidents = await api.listIncidents({
        status: state.filterStatus ?? undefined,
        severity: state.filterSeverity ?? undefined,
        category: state.filterCategory ?? undefined,
        limit: 100,
      });
      set({ incidents });
    } catch (e) {
      console.error("Failed to fetch incidents:", (e as Error).message);
    }
  },

  fetchStats: async () => {
    try {
      const stats = await api.getStats(30);
      set({ stats });
    } catch (e) {
      console.error("Failed to fetch stats:", (e as Error).message);
    }
  },

  selectIncident: async (id) => {
    if (!id) {
      set({ selectedIncident: null });
      return;
    }
    set({ detailLoading: true });
    try {
      const detail = await api.getIncident(id);
      set({ selectedIncident: detail, detailLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, detailLoading: false });
    }
  },

  mitigateIncident: async (id) => {
    set({ actionLoading: true });
    try {
      const now = new Date().toISOString();
      await api.updateIncident(id, { mitigated_at: now });
      // Refresh the selected incident and the list
      const detail = await api.getIncident(id);
      set({ selectedIncident: detail, actionLoading: false });
      get().fetchAll();
    } catch (e) {
      set({ error: (e as Error).message, actionLoading: false });
    }
  },

  resolveIncident: async (id) => {
    set({ actionLoading: true });
    try {
      const now = new Date().toISOString();
      await api.updateIncident(id, { resolved_at: now });
      const detail = await api.getIncident(id);
      set({ selectedIncident: detail, actionLoading: false });
      get().fetchAll();
    } catch (e) {
      set({ error: (e as Error).message, actionLoading: false });
    }
  },

  setFilterStatus: (status) => set({ filterStatus: status }),
  setFilterSeverity: (severity) => set({ filterSeverity: severity }),
  setFilterCategory: (category) => set({ filterCategory: category }),
  clearFilters: () =>
    set({ filterStatus: null, filterSeverity: null, filterCategory: null }),
}));
