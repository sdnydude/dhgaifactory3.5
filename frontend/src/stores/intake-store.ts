"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { IntakeSubmission } from "@/types/cme";

function createEmptyIntake(): IntakeSubmission {
  return {
    section_a: {
      project_name: "",
      therapeutic_area: "",
      disease_state: "",
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

interface IntakeState {
  intake: IntakeSubmission;
  activeSection: string;

  setIntake: (intake: IntakeSubmission) => void;
  updateIntake: (updater: (prev: IntakeSubmission) => IntakeSubmission) => void;
  setActiveSection: (section: string) => void;
  reset: () => void;
}

export const useIntakeStore = create<IntakeState>()(
  persist(
    (set) => ({
      intake: createEmptyIntake(),
      activeSection: "a",

      setIntake: (intake) => set({ intake }),
      updateIntake: (updater) => set((s) => ({ intake: updater(s.intake) })),
      setActiveSection: (activeSection) => set({ activeSection }),
      reset: () => set({ intake: createEmptyIntake(), activeSection: "a" }),
    }),
    {
      name: "dhg-intake-draft",
    },
  ),
);
