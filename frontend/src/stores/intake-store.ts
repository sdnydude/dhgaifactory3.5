"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { IntakeSubmission, PrefillConfidence } from "@/types/cme";

function createEmptyIntake(): IntakeSubmission {
  return {
    section_a: {
      project_name: "",
      therapeutic_area: [],
      disease_state: [],
      target_audience_primary: [],
    },
    section_b: { supporter_name: "" },
    section_c: { learning_format: "", include_post_test: false, include_pre_test: false },
    section_d: { clinical_topics: [] },
    section_e: {},
    section_f: {},
    section_g: {},
    section_h: {},
    section_i: {
      accme_compliant: true,
      financial_disclosure_required: true,
      off_label_discussion: false,
      commercial_support_acknowledgment: true,
    },
    section_j: {},
  };
}

type PrefillSectionStatus = "prefilled" | "accepted" | "cleared";

const PREFILLABLE_SECTIONS = ["b", "c", "d", "e", "f", "g", "h"] as const;

interface IntakeState {
  intake: IntakeSubmission;
  activeSection: string;

  // Prefill state
  prefillStatus: Record<string, PrefillSectionStatus>;
  researchSummary: string | null;
  prefillConfidence: Record<string, PrefillConfidence>;

  // Actions
  setIntake: (intake: IntakeSubmission) => void;
  updateIntake: (updater: (prev: IntakeSubmission) => IntakeSubmission) => void;
  setActiveSection: (section: string) => void;
  reset: () => void;

  // Prefill actions
  applyPrefill: (
    sections: Record<string, Record<string, unknown>>,
    summary: string,
    confidence: Record<string, PrefillConfidence>,
  ) => void;
  acceptSection: (sectionId: string) => void;
  clearSection: (sectionId: string) => void;
  acceptAll: () => void;
  clearAll: () => void;
}

export const useIntakeStore = create<IntakeState>()(
  persist(
    (set) => ({
      intake: createEmptyIntake(),
      activeSection: "a",
      prefillStatus: {},
      researchSummary: null,
      prefillConfidence: {},

      setIntake: (intake) => set({ intake }),
      updateIntake: (updater) => set((s) => ({ intake: updater(s.intake) })),
      setActiveSection: (activeSection) => set({ activeSection }),
      reset: () =>
        set({
          intake: createEmptyIntake(),
          activeSection: "a",
          prefillStatus: {},
          researchSummary: null,
          prefillConfidence: {},
        }),

      applyPrefill: (sections, summary, confidence) =>
        set((s) => {
          const next = { ...s.intake };
          const status: Record<string, PrefillSectionStatus> = {};

          for (const id of PREFILLABLE_SECTIONS) {
            const key = `section_${id}` as keyof IntakeSubmission;
            const data = sections[key];
            if (data && typeof data === "object") {
              (next as Record<string, unknown>)[key] = {
                ...(next[key] as Record<string, unknown>),
                ...data,
              };
              status[id] = "prefilled";
            }
          }

          return {
            intake: next,
            prefillStatus: status,
            researchSummary: summary,
            prefillConfidence: confidence,
          };
        }),

      acceptSection: (sectionId) =>
        set((s) => ({
          prefillStatus: { ...s.prefillStatus, [sectionId]: "accepted" as const },
        })),

      clearSection: (sectionId) =>
        set((s) => {
          const key = `section_${sectionId}` as keyof IntakeSubmission;
          const empty = createEmptyIntake();
          return {
            intake: { ...s.intake, [key]: empty[key] },
            prefillStatus: { ...s.prefillStatus, [sectionId]: "cleared" as const },
          };
        }),

      acceptAll: () =>
        set((s) => {
          const updated: Record<string, PrefillSectionStatus> = {};
          for (const [id, status] of Object.entries(s.prefillStatus)) {
            updated[id] = status === "prefilled" ? "accepted" : status;
          }
          return { prefillStatus: updated };
        }),

      clearAll: () =>
        set(() => {
          const empty = createEmptyIntake();
          return {
            intake: { ...empty },
            prefillStatus: {},
            researchSummary: null,
            prefillConfidence: {},
          };
        }),
    }),
    {
      name: "dhg-intake-draft",
      version: 1,
      migrate: (persisted: unknown, version: number) => {
        if (version === 0) {
          const state = persisted as Record<string, unknown>;
          const intake = state.intake as Record<string, unknown> | undefined;
          if (intake) {
            const a = intake.section_a as Record<string, unknown> | undefined;
            if (a) {
              if (typeof a.therapeutic_area === "string") {
                a.therapeutic_area = a.therapeutic_area ? [a.therapeutic_area] : [];
              }
              if (typeof a.disease_state === "string") {
                a.disease_state = a.disease_state ? [a.disease_state] : [];
              }
            }
          }
        }
        return persisted as IntakeState;
      },
    },
  ),
);
