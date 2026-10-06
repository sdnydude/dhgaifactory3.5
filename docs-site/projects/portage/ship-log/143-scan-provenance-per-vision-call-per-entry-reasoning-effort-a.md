---
title: "Scan provenance per vision call + per-entry reasoning_effort; approved chain gemini-3.5-flash-lite@minimal → 3.8-flash → haiku"
sidebar_label: "Scan provenance per vision call + per-entry reason"
sidebar_position: 143
slug: ship-3bbb89cf
registry_id: 3bbb89cf-9b3e-488c-8d9f-508e7784d9a3
generated: true
---

# Scan provenance per vision call + per-entry reasoning_effort; approved chain gemini-3.5-flash-lite@minimal → 3.8-flash → haiku

| Field | Value |
|-------|-------|
| **Status** | complete |
| **Complexity** | complex |
| **TDD** | Yes |
| **PR** | [#356](https://github.com/sdnydude/portage/pull/356) |
| **Completed** | 2026-09-05 |
| **Model** | claude-fable-5-1 |

## Approach

TDD in worktree feat+scan-provenance (base 7041820) via a local vitest guard config pointing the tdd-guard reporter at the main-checkout data dir. Shared ScanProvenance types; analyzeImage(s) return fallbacks; identify*/generateListingFields stamp provenance; prefillCandidateAspects returns \{candidates, provenance\}; scan routes merge + log; items zod; web ScanFlow + desktop ingest pass-through; buildChain provider\[:model\]\[@effort\] with fail-fast validation. Live proof on the ephemeral e2e stack with a real Gemini key: Flash-Lite scan → real taxonomy/prefill → Save → DB row provenance both calls.

## Commits

- ee3abe2 feat(scan): stamp vision provenance per call; per-entry reasoning_effort in VISION_PROVIDERS
- 83a1ed8 test(e2e): live scan-provenance proof spec

## Decisions

- Vision chain: gemini-3.5-flash-lite (minimal) primary, gemini-3.8-flash second, claude-haiku-4-5 third; local qwen3-vl removed (live probe 10 items)
- @ as the effort delimiter because Ollama tags contain :
- fallbacks optional on VisionCallProvenance: chat path does not report it; chat() return type left unchanged to keep Porter tests untouched
- Provenance rides under marketplaceData.scan (existing slot) — no new column, no db:push

## Review

- Agents: caveman:cavecrew-reviewer x2
- Critical found: 0 · Important found: 3

## Verification

- **lint:** 0 errors / 27 warnings baseline
- **tests:** api 1083/1083, web 713/713, e2e scan-provenance 2/2 live
- **typecheck:** pass

**Tags:** `scan`, `vision`, `provenance`, `gemini`, `flash-lite`, `reasoning_effort`, `e2e-proof`
