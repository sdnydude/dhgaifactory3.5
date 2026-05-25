status: complete
phase: 8
feature: /registry-validator slash command — schema <-> model drift detection
approach: Single .claude/commands/registry-validator.md file. Diff-scoped by default, named-domain mode for targeted checks. Two validation checks: schema-model field alignment + endpoint-schema wiring. Main-session execution (not subagent). grep/Read (not CodeGraph). Auto-capture FAIL findings to deferred_items.
complexity: simple
explore_scope: targeted
spec: docs/superpowers/specs/2026-05-25-registry-validator-design.md

## Verification Results
- Smoke test (insights domain): PASS — 15/15 fields match, 3 known-exclusion [WARN], 3 endpoints [ok]
- Smoke test (clean diff): PASS — [ok] No registry files in diff
- All 6 acceptance criteria met

## Files Changed
- .claude/commands/registry-validator.md (CREATE) — slash command definition
- docs/superpowers/specs/2026-05-25-registry-validator-design.md (CREATE) — design spec
