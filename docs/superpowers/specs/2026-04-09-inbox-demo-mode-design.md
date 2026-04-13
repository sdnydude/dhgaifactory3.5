# Inbox Demo Mode — Design Spec

**Date:** 2026-04-09
**Status:** Approved
**Author:** Stephen Webber + Claude

## Problem

The LLManager inbox at `/inbox` renders all review components (ReflectionPanel, DecisionBar, MetricsBar, DocumentViewer, VSAlternatives) conditionally — they only appear when interrupted LangGraph threads exist with payload data. When no pipelines have run to a human review gate, the inbox shows an empty shell: a "Reviews" list with count 0 and a "Select a review" placeholder. This makes the feature appear incomplete or broken.

## Solution

Inject demo `PendingReview` data into the Zustand store when the live inbox is empty. Demo data flows through the identical component tree as real data, exercising every visual state. Demo data disappears automatically when real interrupted threads exist.

## Approach

**Store-layer injection (Approach A):** Demo data is shaped as `PendingReview[]` and injected via the existing `setReviews()` Zustand action. Zero changes to any review subcomponent.

## Demo Reviews

| # | Title | Recipe | Round | Quality | Banned Patterns | Compliance | VS Data | Recommendation | Purpose |
|---|-------|--------|-------|---------|-----------------|------------|---------|----------------|---------|
| 1 | Cardio-Oncology Needs Assessment | needs_package | 1 | Passed (3,142 words, 87% density) | None | Passed | 3 items (conventional/novel/exploratory) | Approve | Happy path — all green states |
| 2 | Immunotherapy Grant Package | grant_package | 2 | Failed (1,847 words, 62% density) | "it is important to note", "in conclusion" | Failed | None | Needs Attention | Error path — red/warning states |

- Thread IDs prefixed with `demo-` for identification
- Document content is realistic CME prose (~300 words per review)

## Integration Point

In `inbox-master-detail.tsx`:

1. After `listPendingReviews()` resolves with an empty array, inject demo reviews into the store
2. Display a banner at the top of the master list: "Sample data — reviews appear when agents reach human review gates" — styled with `bg-muted`, info icon, not an error state
3. When at least one real review exists, demo data is excluded entirely — no mixing
4. Banner disappears with the demo data

## Decision Bar Behavior on Demo Data

When Approve/Revise/Reject is clicked on a demo review:

- Skip the `resumeThread()` call (no real thread)
- Remove the demo review from the list via existing `removeReview()` action (no toast library installed — the removal itself is sufficient feedback)
- If both demo reviews are dismissed, show the standard empty state

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/components/review/demo-reviews.ts` | **New** — demo `PendingReview[]` data (2 reviews with full payloads) |
| `frontend/src/components/review/inbox-master-detail.tsx` | **Modified** — empty-check, demo injection, banner, demo action guard |

## Files NOT Changed

ReflectionPanel, DecisionBar, DocumentViewer, MetricsBar, VSAlternatives, CommentsSidebar, review-store, inboxApi, types — all unchanged. Demo data conforms to existing types.

## Behavior Summary

```
listPendingReviews() returns data?
  YES → render real reviews (no demo data, no banner)
  NO  → inject demo reviews + show "Sample data" banner
         User clicks Approve/Revise/Reject on demo?
           → remove from list (no backend call)
         All demo reviews dismissed?
           → standard empty state ("No pending reviews")
```
