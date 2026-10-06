---
title: "eBay-spec descriptions + 4000 cap + <br> at publish + footer on edit-sync + multi-value whitelisted aspects"
sidebar_label: "eBay-spec descriptions + 4000 cap + <br> at publis"
sidebar_position: 144
slug: ship-5d5a2c17
registry_id: 5d5a2c17-7c84-4317-9fd3-183326941582
generated: true
---

# eBay-spec descriptions + 4000 cap + \<br\> at publish + footer on edit-sync + multi-value whitelisted aspects

| Field | Value |
|-------|-------|
| **Status** | complete |
| **Complexity** | complex |
| **TDD** | Yes |
| **PR** | [#359](https://github.com/sdnydude/portage/pull/359) |
| **Completed** | 2026-09-06 |
| **Model** | claude-fable-5-1 |

## Approach

External research (25 sources) → description spec in both prompts (150–300 words, Overview/Condition/Function/Included/Specs, seller first person, policy never-list) + cap 4000 end to end. Epson incident investigation: live GetItem (DetailLevel=ItemReturnDescription) proved the edit synced but the item-edit worker stripped the seller footer → applyFooter parity on eBay+Reverb. Sync audit truth table (agent). Gap 4: MULTI-cardinality aspects get every value, whitelisted to eBay list, pick pass cardinality-aware. TDD throughout under a local guard config; four reviewer passes; e2e proof on branch build.

## Commits

- 4c01452 feat(listing): eBay-spec descriptions, 4000 cap, \<br\> at publish, footer on edit-sync, multi-value aspects

## Decisions

- Description spec encodes eBay rules (condition consistency, no links/contact/marketplaces, no copied copy) and conversion heuristics (150–300 words, standalone first sentences, section order) — description is a conversion surface not SEO
- Function section states operation as fact in the seller voice per operator directive; Used = fully operational per eBay
- Aspect values whitelisted to eBay allowed list before Revise; MULTI aspects filled fully
- Footer applied on edit-sync via best-effort profile read (never blocks the edit)

## Review

- Agents: caveman:cavecrew-reviewer x4, general-purpose audit x2
- Critical found: 4 · Important found: 9

## Verification

- **lint:** 0 errors / 27 warnings baseline
- **tests:** api 1094/1094; e2e scan-provenance 2/2 on branch build
- **typecheck:** pass

**Tags:** `ebay`, `description`, `prompt`, `aspects`, `footer`, `edit-sync`, `research`
