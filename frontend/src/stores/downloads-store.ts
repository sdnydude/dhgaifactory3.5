"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { BundleJobResponse } from "@/lib/filesApi";

interface DownloadsState {
  jobs: BundleJobResponse[];
  trayOpen: boolean;

  setJobs: (jobs: BundleJobResponse[]) => void;
  upsertJob: (job: BundleJobResponse) => void;
  openTray: () => void;
  closeTray: () => void;
  toggleTray: () => void;
}

export const useDownloadsStore = create<DownloadsState>()(
  persist(
    (set) => ({
      jobs: [],
      trayOpen: false,

      setJobs: (jobs) => set({ jobs }),

      upsertJob: (job) =>
        set((s) => {
          const idx = s.jobs.findIndex((j) => j.id === job.id);
          if (idx === -1) return { jobs: [job, ...s.jobs] };
          const next = [...s.jobs];
          next[idx] = job;
          return { jobs: next };
        }),

      openTray: () => set({ trayOpen: true }),
      closeTray: () => set({ trayOpen: false }),
      toggleTray: () => set((s) => ({ trayOpen: !s.trayOpen })),
    }),
    {
      name: "dhg-downloads-store",
      partialize: (state) => ({ jobs: state.jobs }),
    },
  ),
);
