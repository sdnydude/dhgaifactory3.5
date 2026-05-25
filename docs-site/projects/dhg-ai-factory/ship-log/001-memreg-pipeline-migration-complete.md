---
title: "Memreg pipeline migration — portage-independent toolchain + read-side wiring"
sidebar_label: "001 — Memreg migration"
sidebar_position: 1
---

# Memreg pipeline migration — portage-independent toolchain + read-side wiring

| Field | Value |
|---|---|
| **Status** | complete (D5/D6 deferred) |
| **Complexity** | complex |
| **TDD** | Partial (Group A ingest scripts — pytest, 22 tests; Groups B/C/D — smoke tests only) |
| **PR** | New private repo — direct commits on `main`: https://github.com/sdnydude/dhg-memreg |
| **Completed** | 2026-05-24 |
| **Model** | claude-opus-4-7 |

## Approach

Migrate the 7 capture scripts off portage (where they were symlinked-from for historical reasons), eliminate hardcoded portage references in the bulk ingest scripts, dockerize the toolchain for cross-project use, and wire the missing read side (SessionStart KB briefing hook + explicit `kb-search` skill) so Claude actually consults the registry it's been writing to for months.

New private repo `sdnydude/dhg-memreg` at `~/DHG/dhg-memreg/` becomes the single source of truth. `~/.claude/scripts/post-*.sh` symlinks repointed from portage to dhg-memreg. Capture pipeline now portage-independent (proven by renaming `~/DHG/portage` and firing 5 captures successfully).

## Spec

- Fix `ingest-memory-files.py` — accept `--project` + `--memory-dir`, remove portage hardcoding (lines 19, 172, 217, 249)
- Make 7 capture scripts dhg-memreg-resident, eliminate portage symlinks
- Dockerize toolchain: single image, env-var driven, LAN-only scope (off-LAN tunnel exposure deferred)
- Wire read side: SessionStart KB briefing + `kb-search` skill + PreToolUse forced-inject hook (D5/D6 deferred per advisor — wrong event)

## Exploration Findings

- Capture scripts (`post-*.sh`) are generic JSON forwarders — "portage" appears only in usage-example comments
- `ingest-memory-files.py` is the actual blocker — hardcoded portage path + 3 hardcoded `project_name`
- `ingest-claude-md.py` has parallel but smaller hardcoding (only the bulk wrapper)
- KB read side already exists at `/api/kb/search` (hybrid FTS + pgvector) but is never consulted by Claude — the gap that prompted this ship
- Docker entrypoint dispatcher I wrote in Group C reimplemented argparse-subcommand routing in bash → triggered a mid-ship reclassification of "unify scripts into Python module" from deferred to in-scope (B6/B7/B8)

## Commits (`sdnydude/dhg-memreg`)

- `9e087ab` Group A: project-aware ingest scripts + tests
- `14dbdcc` chore: gitignore pycache/venv/test cache
- `7366149` Group B (B1+B2): capture scripts + symlink-swap tool
- `7d1de89` Group C: dockerize + CI
- `82b4ddf` ci: add pytest workflow on push/PR to main
- `a9430bb` B6/B7/B8: unify 7 bash capture scripts → `memreg_capture.py` + thin shims
- `42232da` Group D (D1+D4+D5): KB-briefing hook + kb-search skill + PreToolUse forced-inject

## Verification

- **tests:** 22/22 pass (`pytest tests/`) — 7 ingest-memory-files + 3 ingest-claude-md + 12 capture dispatcher
- **live integrations:** 37 aifactory memories ingested via refactored script; 5+ captures fired via symlinks with `~/DHG/portage` renamed (proved no portage dependency); 3+ docker dispatches return valid capture IDs
- **health checks:** docker image builds clean (145MB), entrypoint dispatcher routes all 7 capture commands + 2 ingest commands; SessionStart KB briefing runs in 0.12s happy / 2.0s parallel timeout (worst case)
- **AgentShield:** not run (not yet installed in dhg-memreg)
- **secret scan:** no secrets in committed source
- **performance baselines:** SessionStart hook 0.12s happy / 2.0s unreachable / 2.0s hung — all within 8s timeout

## Review Findings

Two advisor passes (systems-architect) during this ship:

**First pass (memreg-plan critique):** Block initial plan with 4 critical issues — (1) D3/D6 rollback insufficient (need timestamped backup + verified `claude --bare` fallback), (2) Docker LAN-only goal incoherent with off-LAN teammate framing, (3) HARD-GATE vs SDD-continuous workflow contradiction, (4) D5 nudge pattern doomed by `loaded_is_not_attended`. All 4 applied as amendments before any code shipped.

**Second pass (D6 HARD GATE critique):** STOP D6. `PreToolUse` `additionalContext` fires AFTER tool result, not before — so the "forced-inject" hook injects KB findings too late for the subagent to use them. Correct event is `SubagentStart`. D5 written + D6 registration deferred — see Deferred Items.

## Deferred Items

- **D5/D6: SubagentStart-based KB forced-inject hook (pivot from PreToolUse)** — registry: `2e87973e-e301-4bae-b31a-957a624ce57e`. Preflight: 1-min test for `SubagentStart` event support. Trigger to act: first observed SessionStart-briefing regression OR next 5+ subagent ship. Priority: high.
- **Tunnel-expose registry on `8011`** for off-LAN Docker access (Cloudflare tunnel + Access JWT + CORS + rate limiting). Out of scope — scope explosion. Priority: medium.
- **Re-symlink portage's `post-*.sh` to dhg-memreg** (was B5). Touching portage from aifactory ship conflated scopes. Priority: low.
- **Swap KB endpoint from `/api/kb/search` to medkb `/v1/query`** when medkb ingestor pipeline goes live. `KB_ENDPOINT` env var already exists for 1-line swap. Priority: medium.
- **Backup pruning policy** for `~/.claude/settings.json.bak.*`. Currently keeps 5 most recent via setup script. Worth formalizing. Priority: low.
- **Cosmetic indent on first deferred-item title in SessionStart briefing** (jq `-r` quirk). Readable, non-functional. Priority: low.
- **`session-briefing.sh` + `kb-briefing.sh` unification** — they currently coexist (complementary content, no duplication after C3 fix). Worth merging in a follow-up. Priority: low.

## Park List (Phase 2 divergent discoveries kept for future work)

- `sys.path.insert` in `ingest-claude-md.py` points at aifactory-specific path — should become an arg
- 7 capture scripts could become a Python package with proper entry points (vs. one-script module)
- The B4 portage-rename test could be wired as a CI canary — proves dhg-memreg standalone every commit

## What changed for users

| Before | After |
|---|---|
| Capture scripts symlinked from portage | Symlinked from `~/DHG/dhg-memreg/` (portage-independent) |
| `ingest-memory-files.py` only worked for portage | Project-aware via `--project` + `--memory-dir` (works for aifactory, c2l-vault, etc.) |
| 7 duplicated bash scripts + docker dispatcher reimplementing argparse | One Python module + 7 thin shims |
| Zero test coverage on capture pipeline | 22 tests in dhg-memreg |
| Claude never queried the KB | SessionStart KB briefing block in every new session for known DHG projects |
| No explicit "search the KB" command | `kb-search` skill returns markdown table of relevant captures |

**Tags:** `memreg`, `migration`, `dockerize`, `read-side`, `advisor-driven`, `hard-gate`
