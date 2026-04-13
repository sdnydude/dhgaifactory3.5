# Inbox Demo Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show demo review data in the LLManager inbox when no real interrupted LangGraph threads exist, so all review components (ReflectionPanel, DecisionBar, MetricsBar, DocumentViewer, VSAlternatives) are visible.

**Architecture:** A single data file provides two `PendingReview` objects (one happy-path, one error-path). The existing `InboxMasterDetail` component checks if `listPendingReviews()` returned empty and, if so, injects demo data into the Zustand store. A banner indicates sample data. Decision actions on demo reviews skip the backend call and just remove the item.

**Tech Stack:** TypeScript, React, Zustand, existing shadcn/ui components

**Spec:** `docs/superpowers/specs/2026-04-09-inbox-demo-mode-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/components/review/demo-reviews.ts` | Create | Two `PendingReview` objects with full `ReviewPayloadWithVS` payloads |
| `frontend/src/components/review/inbox-master-detail.tsx` | Modify | Empty-state detection, demo injection, banner, demo action guard |

No other files are changed. All review subcomponents render demo data through their existing props.

---

### Task 1: Create Demo Data File

**Files:**
- Create: `frontend/src/components/review/demo-reviews.ts`

- [ ] **Step 1: Create `demo-reviews.ts` with two demo reviews**

```typescript
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
```

- [ ] **Step 2: Verify the file compiles**

Run:
```bash
cd frontend && npx tsc --noEmit src/components/review/demo-reviews.ts 2>&1 | head -20
```

If TypeScript path aliases don't resolve with `--noEmit` on a single file, use the full project check:
```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -i "demo-reviews" | head -10
```

Expected: No errors related to `demo-reviews.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/review/demo-reviews.ts
git commit -m "feat(inbox): add demo review data for empty inbox state"
```

---

### Task 2: Integrate Demo Data into InboxMasterDetail

**Files:**
- Modify: `frontend/src/components/review/inbox-master-detail.tsx`

- [ ] **Step 1: Add imports**

At the top of `inbox-master-detail.tsx`, after the existing imports, add:

```typescript
import { DEMO_REVIEWS, isDemoReview } from "./demo-reviews";
import { Info } from "lucide-react";
```

Also add `Info` to the existing `lucide-react` import — merge it with the existing line:

```typescript
import { Inbox, RefreshCw, AlertCircle, Info } from "lucide-react";
```

And remove the separate `Info` import. The result is one lucide import line.

- [ ] **Step 2: Add `demoDismissed` ref to prevent re-injection after dismissal**

After the store destructuring (after line 58), add:

```typescript
  const demoDismissedRef = useRef(false);
```

Also add `useRef` to the existing React import at line 3:

```typescript
import { useEffect, useCallback, useRef } from "react";
```

- [ ] **Step 3: Modify `fetchReviews` to inject demo data on empty result**

Replace the `fetchReviews` callback (lines 60-69):

```typescript
  const fetchReviews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listPendingReviews();
      if (data.length > 0) {
        demoDismissedRef.current = false;
        setReviews(data);
      } else if (!demoDismissedRef.current) {
        setReviews(DEMO_REVIEWS);
      } else {
        setReviews([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reviews");
    }
  }, [setReviews, setLoading, setError]);
```

Three branches:
- Real data exists → use it, reset dismissed flag (real data arriving should allow demo to show again later if emptied)
- No real data, demo not dismissed → inject demo
- No real data, demo dismissed → empty list (standard empty state)

- [ ] **Step 4: Derive `isDemo` flag from store state**

After the `selectedReview` line (line 77), add:

```typescript
  const isDemo = reviews.length > 0 && reviews.every((r) => isDemoReview(r.threadId));
```

- [ ] **Step 5: Add demo banner in the master list**

After the error display block (after line 116, the closing `)}` of the error block), add the banner:

```typescript
        {isDemo && (
          <div className="mx-3 mt-2 flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
            <Info className="h-3.5 w-3.5 shrink-0" />
            Sample data — reviews appear when agents reach human review gates
          </div>
        )}
```

- [ ] **Step 6: Guard the `handleAction` to skip backend call for demo reviews**

Replace the `handleAction` function (lines 79-93):

```typescript
  const handleAction = async (
    threadId: string,
    graphId: string,
    resumeValue: ResumeValue,
  ) => {
    if (isDemoReview(threadId)) {
      removeReview(threadId);
      const remainingDemo = reviews.filter(
        (r) => r.threadId !== threadId && isDemoReview(r.threadId),
      );
      if (remainingDemo.length === 0) {
        demoDismissedRef.current = true;
      }
      return;
    }
    setActionLoading(threadId);
    try {
      await resumeThread(threadId, graphId, resumeValue);
      removeReview(threadId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to process action");
    } finally {
      setActionLoading(null);
    }
  };
```

The only addition is the `isDemoReview` guard at the top that calls `removeReview` and returns early.

- [ ] **Step 7: Verify the file compiles**

Run:
```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -i "inbox-master-detail\|demo-reviews" | head -10
```

Expected: No errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/review/inbox-master-detail.tsx
git commit -m "feat(inbox): show demo data when inbox is empty, with banner and action guard"
```

---

### Task 3: Build and Verify

**Files:**
- None changed — verification only

- [ ] **Step 1: Build the frontend**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: Build succeeds with no errors.

- [ ] **Step 2: Rebuild the Docker container**

```bash
docker compose build dhg-frontend 2>&1 | tail -10
```

Expected: Build completes successfully.

- [ ] **Step 3: Restart the frontend container**

```bash
docker compose up -d dhg-frontend
```

- [ ] **Step 4: Wait for healthy status and verify**

```bash
sleep 5 && docker ps --filter name=dhg-frontend --format "{{.Names}} {{.Status}}"
```

Expected: `dhg-frontend Up X seconds (healthy)`

- [ ] **Step 5: Verify the inbox page renders demo data**

```bash
curl -sf http://localhost:3000/inbox 2>&1 | grep -o "Sample data" | head -1
```

Expected: `Sample data` — confirms the demo banner is rendering.

```bash
curl -sf http://localhost:3000/inbox 2>&1 | grep -o "Cardio-Oncology\|Immunotherapy" | head -5
```

Expected: Both review titles appear in the HTML.

- [ ] **Step 6: Verify demo review components render**

```bash
curl -sf http://localhost:3000/inbox 2>&1 | grep -o "AI Reflection\|Quality Signals\|Recommend" | head -5
```

Expected: Component text appears, confirming ReflectionPanel renders with demo data.

- [ ] **Step 7: Commit (if any build fixes were needed)**

Only if changes were required during build verification. Otherwise skip.
