---
title: "Reverb reference-data token fix (edge 403)"
sidebar_label: "Reverb reference-data token fix (edge 403)"
sidebar_position: 141
slug: ship-8e9af39f
registry_id: 8e9af39f-0adc-4529-9b48-6fa375cc60e0
generated: true
---

# Reverb reference-data token fix (edge 403)

| Field | Value |
|-------|-------|
| **Status** | complete |
| **Complexity** | simple |
| **TDD** | Yes |
| **PR** | no PR recorded |
| **Completed** | 2026-09-03 |
| **Model** | claude-fable-5-1 |

## Approach

Send seller PAT (service-token fallback) on public /categories/flat + /listing_conditions fetches; map 401/403 to 502 REVERB_UNAVAILABLE via publicFetchError helper

## Commits

- 6632795 fix(reverb): send a token on public reference-data fetches (edge 403 fix)

## Decisions

- reference data is seller-agnostic but needs a token to clear Reverb edge; prefer seller PAT, fall back to service token

## Verification

- **lint:** 27 warnings (baseline)
- **tests:** 1075 API pass
- **typecheck:** pass

**Tags:** `reverb`, `marketplace`, `403`, `edge`, `incident`, `live-proven`, `deployed`
