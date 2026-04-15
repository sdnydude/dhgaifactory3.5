"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  ProjectDocumentItem,
  ProjectListItem,
} from "@/lib/filesApi";

interface FilesTabState {
  projects: ProjectListItem[];
  documentsByProject: Record<string, ProjectDocumentItem[]>;
  expandedProjectIds: string[];
  selectedDocumentIds: string[];
  selectedProjectId: string | null;
  searchQuery: string;
  previewDocumentId: string | null;

  setProjects: (projects: ProjectListItem[]) => void;
  setDocuments: (projectId: string, docs: ProjectDocumentItem[]) => void;
  toggleProjectExpanded: (id: string) => void;
  toggleDocumentSelected: (projectId: string, documentId: string) => void;
  clearSelection: () => void;
  setPreview: (documentId: string | null) => void;
  setSearch: (q: string) => void;
}

export const useFilesTabStore = create<FilesTabState>()(
  persist(
    (set, get) => ({
      projects: [],
      documentsByProject: {},
      expandedProjectIds: [],
      selectedDocumentIds: [],
      selectedProjectId: null,
      searchQuery: "",
      previewDocumentId: null,

      setProjects: (projects) => set({ projects }),

      setDocuments: (projectId, docs) =>
        set((s) => ({
          documentsByProject: { ...s.documentsByProject, [projectId]: docs },
        })),

      toggleProjectExpanded: (id) =>
        set((s) => ({
          expandedProjectIds: s.expandedProjectIds.includes(id)
            ? s.expandedProjectIds.filter((x) => x !== id)
            : [...s.expandedProjectIds, id],
        })),

      toggleDocumentSelected: (projectId, documentId) => {
        const s = get();
        if (s.selectedProjectId && s.selectedProjectId !== projectId) {
          set({
            selectedDocumentIds: [documentId],
            selectedProjectId: projectId,
          });
          return;
        }
        const next = s.selectedDocumentIds.includes(documentId)
          ? s.selectedDocumentIds.filter((x) => x !== documentId)
          : [...s.selectedDocumentIds, documentId];
        set({
          selectedDocumentIds: next,
          selectedProjectId: next.length ? projectId : null,
        });
      },

      clearSelection: () =>
        set({ selectedDocumentIds: [], selectedProjectId: null }),

      setPreview: (documentId) => set({ previewDocumentId: documentId }),

      setSearch: (q) => set({ searchQuery: q }),
    }),
    {
      name: "dhg-files-tab-store",
      partialize: (state) => ({
        expandedProjectIds: state.expandedProjectIds,
      }),
    },
  ),
);
