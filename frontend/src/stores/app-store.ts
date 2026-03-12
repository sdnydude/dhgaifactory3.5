"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AppState {
  sidebarCollapsed: boolean;
  darkMode: boolean;
  badgeCounts: {
    inbox: number;
    processing: number;
  };

  toggleSidebar: () => void;
  toggleDarkMode: () => void;
  setBadgeCounts: (counts: Partial<AppState["badgeCounts"]>) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      darkMode: false,
      badgeCounts: {
        inbox: 0,
        processing: 0,
      },

      toggleSidebar: () =>
        set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

      toggleDarkMode: () =>
        set((s) => {
          const next = !s.darkMode;
          if (typeof document !== "undefined") {
            document.documentElement.classList.toggle("dark", next);
          }
          return { darkMode: next };
        }),

      setBadgeCounts: (counts) =>
        set((s) => ({ badgeCounts: { ...s.badgeCounts, ...counts } })),
    }),
    {
      name: "dhg-app-store",
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        darkMode: state.darkMode,
      }),
    },
  ),
);
