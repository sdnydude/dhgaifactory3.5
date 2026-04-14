"use client";

import { create } from "zustand";
import type {
  DevChangelogEntry,
  DevChangelogFilters,
} from "@/lib/devChangelogApi";

export type DevChangelogViewMode = "table" | "timeline" | "kanban";

interface DevChangelogState {
  entries: DevChangelogEntry[];
  total: number;
  filters: DevChangelogFilters;
  selectedSlug: string | null;
  viewMode: DevChangelogViewMode;
  loading: boolean;
  error: string | null;

  setEntries: (entries: DevChangelogEntry[], total: number) => void;
  updateEntry: (entry: DevChangelogEntry) => void;
  setFilter: <K extends keyof DevChangelogFilters>(
    key: K,
    value: DevChangelogFilters[K],
  ) => void;
  clearFilters: () => void;
  selectRow: (slug: string | null) => void;
  setViewMode: (mode: DevChangelogViewMode) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useDevChangelogStore = create<DevChangelogState>()((set) => ({
  entries: [],
  total: 0,
  filters: {},
  selectedSlug: null,
  viewMode: "table",
  loading: true,
  error: null,

  setEntries: (entries, total) =>
    set({ entries, total, loading: false, error: null }),
  updateEntry: (entry) =>
    set((s) => ({
      entries: s.entries.map((e) => (e.slug === entry.slug ? entry : e)),
    })),
  setFilter: (key, value) =>
    set((s) => {
      const next = { ...s.filters };
      if (value === undefined || value === null || value === "") {
        delete next[key];
      } else {
        next[key] = value;
      }
      return { filters: next };
    }),
  clearFilters: () => set({ filters: {} }),
  selectRow: (slug) => set({ selectedSlug: slug }),
  setViewMode: (mode) => set({ viewMode: mode }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error, loading: false }),
}));
