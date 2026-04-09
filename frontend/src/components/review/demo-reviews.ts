import type { PendingReview } from "@/lib/inboxApi";
import type { ReviewPayloadWithVS } from "./types";

const DEMO_NEEDS_PAYLOAD: ReviewPayloadWithVS = {
  document: {
    needs_assessment: `# Needs Assessment: Cardio-Oncology Survivorship Care

## Background

Cardiovascular toxicity remains the leading non-cancer cause of morbidity and mortality among cancer survivors. With over 18 million cancer survivors in the United States, the intersection of cardiology and oncology has emerged as a critical subspecialty requiring dedicated educational programming.

## Identified Practice Gaps

Current oncology training programs dedicate fewer than 8 hours to cardiovascular risk assessment during cancer therapy. A 2025 survey of 1,200 oncologists revealed that 67% felt inadequately prepared to manage cardiotoxicity from immune checkpoint inhibitors, and 73% reported uncertainty about appropriate cardiac surveillance intervals for patients receiving anthracycline-based regimens.

## Target Audience

This educational initiative targets practicing oncologists, cardiologists, advanced practice providers, and clinical pharmacists involved in cancer survivorship care. The primary audience comprises community-based practitioners who manage the majority of cancer survivors but have limited access to multidisciplinary cardio-oncology teams.

## Educational Need

The rapid expansion of cancer immunotherapies has outpaced the development of evidence-based cardiotoxicity management guidelines. Healthcare professionals need structured education on risk stratification, biomarker monitoring, and collaborative care models that bridge oncology and cardiology expertise.`,
  },
  metrics: {
    word_count: 3142,
    prose_density: 0.87,
    quality_passed: true,
    banned_patterns_found: [],
    compliance_result: { passed: true, details: "All ACCME criteria met" },
  },
  recipe: "needs_package",
  project_id: "demo-project-001",
  project_name: "Cardio-Oncology CME Grant",
  review_round: 1,
  current_step: "human_review",
  vs_distributions: {
    needs_assessment: {
      distribution_id: "demo-vs-dist-001",
      items: [
        {
          content:
            "Cardiovascular toxicity remains the leading non-cancer cause of morbidity and mortality among cancer survivors. With over 18 million cancer survivors in the United States, the intersection of cardiology and oncology demands dedicated education.",
          probability: 0.52,
          metadata: {
            label: "conventional",
            quality_score: 0.91,
            p_raw: 0.55,
          },
        },
        {
          content:
            "The cardio-oncology gap represents a systemic failure: we cure the cancer but lose the patient to the treatment's cardiac aftermath. Survivor care must evolve from reactive monitoring to predictive interception.",
          probability: 0.31,
          metadata: {
            label: "novel",
            quality_score: 0.88,
            p_raw: 0.3,
          },
        },
        {
          content:
            "What if we reframed cardiotoxicity not as a side effect to manage but as a design constraint for therapy selection? A constraint-first model would integrate cardiac risk into initial treatment planning rather than surveillance after the fact.",
          probability: 0.17,
          metadata: {
            label: "exploratory",
            quality_score: 0.79,
            p_raw: 0.15,
          },
        },
      ],
      model: "claude-sonnet-4-20250514",
      phase: "generation",
      k: 3,
      tau: 0.7,
      sum_probability: 1.0,
      tau_relaxed: false,
      num_filtered: 1,
      created_at: "2026-04-09T10:30:00Z",
    },
  },
};

const DEMO_GRANT_PAYLOAD: ReviewPayloadWithVS = {
  document: {
    grant_package: `# Grant Package: Immunotherapy-Induced Autoimmune Complications

## Executive Summary

It is important to note that immune checkpoint inhibitor therapy has transformed cancer treatment outcomes across multiple tumor types. This grant proposal addresses the educational gap in managing immune-related adverse events (irAEs) among community oncologists. In conclusion, the proposed curriculum will establish a comprehensive framework for irAE identification, grading, and multidisciplinary management.

## Program Description

The proposed 12-month continuing medical education initiative targets community-based oncologists who prescribe immune checkpoint inhibitors but lack access to specialized irAE management teams. Current evidence demonstrates that 40-60% of patients receiving combination immunotherapy experience grade 2 or higher irAEs, yet fewer than 30% of community oncologists report confidence in managing these complications independently.

## Educational Design

The curriculum employs a case-based learning model incorporating real-world patient scenarios drawn from the FAERS database. Participants engage in longitudinal case management simulations where treatment decisions have downstream consequences mirroring clinical practice.`,
  },
  metrics: {
    word_count: 1847,
    prose_density: 0.62,
    quality_passed: false,
    banned_patterns_found: ["it is important to note", "in conclusion"],
    compliance_result: {
      passed: false,
      details: "Missing learning objectives mapping to Moore's framework",
    },
  },
  recipe: "grant_package",
  project_id: "demo-project-002",
  project_name: "Immunotherapy irAE Education Grant",
  review_round: 2,
  current_step: "human_review",
};

export const DEMO_REVIEWS: PendingReview[] = [
  {
    threadId: "demo-cardio-onc-needs-001",
    graphId: "needs_package",
    createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    payload: DEMO_NEEDS_PAYLOAD,
    currentStep: "human_review",
    status: "awaiting_review",
  },
  {
    threadId: "demo-immuno-grant-002",
    graphId: "grant_package",
    createdAt: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    payload: DEMO_GRANT_PAYLOAD,
    currentStep: "human_review",
    status: "awaiting_review",
  },
];

export function isDemoReview(threadId: string): boolean {
  return threadId.startsWith("demo-");
}
