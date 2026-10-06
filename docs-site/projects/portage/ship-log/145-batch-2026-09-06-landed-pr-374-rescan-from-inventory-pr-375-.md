---
title: "Batch 2026-09-06 landed (PR #374) + Rescan from inventory (PR #375) + recall-before-write hook; 38h publish outage rollback"
sidebar_label: "Batch 2026-09-06 landed (PR #374) + Rescan from in"
sidebar_position: 145
slug: ship-f941d075
registry_id: f941d075-474e-4fa4-8c15-fcff4c5c7a88
generated: true
---

# Batch 2026-09-06 landed (PR #374) + Rescan from inventory (PR #375) + recall-before-write hook; 38h publish outage rollback

| Field | Value |
|-------|-------|
| **Status** | complete |
| **Complexity** | complex |
| **TDD** | Yes |
| **PR** | [#375](https://github.com/sdnydude/portage/pull/375) |
| **Completed** | 2026-09-13 |
| **Model** | claude-fable-5-1 |

## Approach

Rollback of an accidental batch-image deploy; 4-advisor review of PR #374 -\> 8 fixes (handling-time precedence, PATCH sellerReturns parity, HeaderActions lg:hidden, pager clamp, Porter trigram degrade, lane-E pins, CI 201-item seed + stub glob, workbench token reuse); live db:push of 3 seller_profiles cols; merge; rescan lifted onto main, 3 review passes -\> category row removed, adapter SELECTION_ONLY/FREE_TEXT aspect value gate + NFC + cache evict, sheet busy-close + focus trap; proof via isolated e2e stack + new rescan-proof.spec; one deploy from main; Chrome walk on prod.

## Commits

- 973c876 fix(batch): advisor round
- bd1bb41 Merge PR #374
- d8e9206 feat(inventory): Rescan diff sheet
- 8e2050d test(e2e): rescan proof spec
- c7ac21c Merge PR #375

## Decisions

- Rescan = diff sheet (C) over overwrite (A) / seeded edit page (B)
- No category row in rescan diff: item.category is the eBay leaf name, candidate.category the vision bucket
- Closed-list aspect values filtered only for SELECTION_ONLY aspectMode; FREE_TEXT suggestions pass through
- Condition notes edit wipes prepared listing conditionDescription (item wins) kept as built — operator A

## Review

- Agents: marketplace-adapter-reviewer x2, config-safety-reviewer, feature-dev:code-reviewer x4, pr-review-toolkit:pr-test-analyzer x2
- Critical found: 4 · Important found: 7

## Verification

- **lint:** 0 errors / 27 warnings (baseline)
- **tests:** API 1125/1125, web 777/777; e2e batch-proof 13/13 + rescan-proof 2/2 on isolated stack; CI green on both PRs
- **typecheck:** pass

**Tags:** `batch-2026-09-06`, `rescan`, `ebay`, `aspects`, `deploy`, `outage`, `recall-hook`
