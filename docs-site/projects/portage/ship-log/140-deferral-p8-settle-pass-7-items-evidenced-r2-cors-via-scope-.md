---
title: "Deferral P8 — settle pass (7 items evidenced, R2 CORS via scope-C token, dhg-docs redirect fix, 14 PNGs removed)"
sidebar_label: "Deferral P8 — settle pass (7 items evidenced, R2 C"
sidebar_position: 140
slug: ship-8c3f82b3
registry_id: 8c3f82b3-d306-4f7b-bd32-ce4b41fc7bcb
generated: true
---

# Deferral P8 — settle pass (7 items evidenced, R2 CORS via scope-C token, dhg-docs redirect fix, 14 PNGs removed)

| Field | Value |
|-------|-------|
| **Status** | complete |
| **Complexity** | simple |
| **TDD** | — |
| **PR** | [#343](https://github.com/sdnydude/portage/pull/343) |
| **Completed** | 2026-08-29 |
| **Model** | claude-fable-5 |

## Approach

Live checks per plan §P8; registry PATCH with evidence; minted claude-cloudflare-ops account token (CF_OPS_TOKEN) per 2026-06-06 spec via the Account-API-Tokens-Write token; PUT R2 CORS live-verified; nginx absolute_redirect off in aifactory; git rm unreferenced PNGs.

## Commits

- f2554fc Merge pull request #343
- aifactory 2f7dd91 fix(docs-site): absolute_redirect off

## Decisions

- Cloudflare writes via minted scope-C account token CF_OPS_TOKEN, not dashboard/connector

## Review

- Agents: —
- Critical found: 0 · Important found: 0

## Verification

- **lint:** clean
- **tests:** check:tutorials pass; CI Lint/Test/e2e/Build pass
- **typecheck:** n/a docs-only

**Tags:** `deferral-program`, `p8`, `cloudflare`, `r2`, `cors`
