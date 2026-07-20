---
title: "Explore subagent return format — contract + compliance measurement hook"
sidebar_label: "002 — Explore return-format hook"
sidebar_position: 2
---

# Explore subagent return format — contract + compliance measurement hook

| Field | Value |
|---|---|
| **Status** | complete — **measurement only; enforcement NOT delivered** |
| **Complexity** | simple |
| **TDD** | No — hook written first, then execution-tested across 6 scenarios, then verified against a live spawn |
| **PR** | none — uncommitted at time of writing, branch `feat/beta-reports` |
| **Completed** | 2026-07-20 |
| **Model** | claude-opus-4-8[1m] |
| **Decision log** | `c147dff0-9a07-48f8-a98b-5fbe20bda45b` |

## Problem

Explore subagents handing back to the main session caused a noticeable pause. Cause: reports pasted the full source blocks that `codegraph_explore` had returned, so the payload landing in main context was large.

Stated goal was to "force compliance" with a summaries-not-source rule. What shipped is weaker than that, deliberately — see [What this does not do](#what-this-does-not-do).

## Premise correction

The work was requested as edits to "Explore and Codegraph subagent definitions in `.claude/agents/`". Those files do not exist:

- Project `.claude/agents/` does not exist.
- Global `~/.claude/agents/` holds 9 definitions, none named Explore or Codegraph.
- `Explore` is a **built-in** agent type — its system prompt is harness-baked and not file-editable.

The editable levers are the project skill `.claude/skills/codegraph-explore/SKILL.md` (the prompt template used when spawning Explore) and `.claude/rules/codegraph.md`.

## What shipped

### 1. Return-format contract (model-driven)

`.claude/skills/codegraph-explore/SKILL.md`:

- Added to "What to report back": **Never paste source blocks.** Cite `file:line`. Quote ≤3 lines only when a single line is the decisive evidence. Describe behavior in prose.
- Retuned caps 400–600w → per-level: quick ~150w, medium ~300w, very thorough ~500w.
- Fixed a contradiction — the "Thoroughness level guide" still carried the old 200/400/600 numbers.

`.claude/rules/codegraph.md` — new section, applies to every Explore spawn including ones that never load the skill:

> Explore subagents return summaries, not source: cite `file:line`, never paste code blocks, quote ≤3 lines only when a single line is the decisive evidence.

### 2. Compliance measurement hook (deterministic)

`.claude/hooks/explore-compliance-log.sh` — PostToolUse, matcher `Agent|Task`. Scoped to `subagent_type == Explore`; every other agent type exits immediately. Per report it appends one JSON line to `.claude/logs/explore-compliance.log`:

| Field | Meaning |
|---|---|
| `words` | Total words in the returned report |
| `code_fences` | Number of fenced blocks |
| `fenced_lines` | Lines sitting inside fences — the actual bloat measure |
| `prompt_had_contract` | Whether the spawn prompt carried the contract text |
| `violation` | `code_fences >= 2` or `words > 700` |

Fail-open: no `set -e`, all exceptions swallowed, always exits 0. A telemetry hook must never disrupt a session.

`prompt_had_contract` is an **experiment variable, not a gate**. It records whether the contract was present so contract-presence can be correlated against actual source-dumping. It is deliberately not used to allow or deny anything.

## Why no blocking hook

A PreToolUse gate was designed and then dropped. Two prior decisions killed it:

**2026-07-05 — `enforce-capture-sweep.sh` blocking hook rejected.** Independent `config-safety-reviewer` found 2 CRITICAL bricking defects (broken MultiEdit/Bash self-repair escape hatches) and 1 HIGH: "gate defeated by accidental substring match with zero real capture compliance." Found by execution testing, not code reading. Rejected alternative: wiring in after author self-testing, because "author-authored tests share author blind spots."

The proposed gate here — deny any Explore spawn whose prompt lacks a `[RETURN-CONTRACT v1]` sentinel — reproduces that HIGH defect exactly. A substring check is satisfied by pasting the token with zero real compliance.

**2026-06-30 — insight capture must be a deterministic Stop-hook, not a model-driven rule.** Recorded that the rule-driven approach "depends on the model remembering, rarely followed, ~2 months produced almost no captures."

That verdict applies to the contract edits in section 1 above. They are the same model-driven pattern with a measured near-zero compliance record on this codebase. **They should not be counted as the fix.** The hook exists precisely because the rule alone is not trustworthy.

Additional structural reason: PostToolUse fires *after* the payload has entered main context. Blocking there cannot prevent the bloat it targets. Only measurement is honest at that point.

## Evidence

### Execution test — 6 scenarios, pre-wiring

| # | Input | Expected | Result |
|---|---|---|---|
| T1 | Explore + source dump | `violation:true` | pass |
| T2 | Explore clean + contract in prompt | `violation:false`, `contract:true` | pass |
| T3 | `subagent_type: code-reviewer` + fences | no log line | pass |
| T4 | Malformed JSON | exit 0, no crash, no line | pass |
| T5 | Empty stdin | exit 0 | pass |
| T6 | `tool_response` as list-of-blocks | parsed | pass |

3 log lines written (T1, T2, T6); T3/T4/T5 correctly silent. All paths exit 0.

### Wiring validation

`.claude/settings.json` gained a `PostToolUse` event. Re-parsed as valid JSON; `PreToolUse` matchers (`Bash`, `Read|Glob`, `Write|Edit|MultiEdit`), `permissions`, and `enabledPlugins` confirmed intact. Backup at `/tmp/claude-1000/settings.json.bak`. Log path confirmed gitignored via `logs/` at `.gitignore:18`.

### Live spawn — the decisive test

Synthetic rows cleared, leaving **no log file**. One real Explore spawn was then run (question: which health endpoints the registry actually defines). Resulting log line:

```json
{"ts":"2026-07-20T09:39:51-04:00","subagent_type":"Explore","words":133,
 "code_fences":0,"fenced_lines":0,"prompt_had_contract":true,"violation":false}
```

This proves the last untested path — that the hook parses a genuine `tool_response`, whose exact shape had been inferred rather than observed. Corroboration:

- 133 words matches a report visibly under its 150-word cap.
- 0 fences matches a report containing no code blocks.
- Settings change took effect **without a session restart** — this had been flagged as a risk; it was not one.

The subagent's own output was independently verified rather than taken on trust: it reported `/healthz` at `registry/api.py:281` and no bare `/health`. Direct curl confirmed `/healthz` → **200**, `/health` → **404**.

## What this does not do

- **It does not force compliance.** The request was enforcement. Nothing here prevents an Explore subagent from dumping source; it records that it happened.
- **The failure mode has never been observed in the wild.** `violation:true` has only ever fired on a self-authored payload. Thresholds (2+ fences, >700 words) are untuned guesses until real violations appear.
- **One live sample, and it is the easy case** — contract present, subagent complied. No data yet on the contract-absent case.
- **Tests are author-authored**, the exact blind spot the 2026-07-05 review flagged.

## Files changed

| File | Change |
|---|---|
| `.claude/hooks/explore-compliance-log.sh` | new, executable |
| `.claude/settings.json` | new `PostToolUse` event, matcher `Agent\|Task` |
| `.claude/rules/codegraph.md` | new "Explore Subagent Return Format" section |
| `.claude/skills/codegraph-explore/SKILL.md` | no-source rule, per-level caps, guide de-contradicted |

Not touched: 8 stale copies of the skill under `.claude/worktrees/*/`.

## Next

1. Let the log accumulate real spawns. The open question is the violation rate, and whether `prompt_had_contract:false` correlates with it.
2. Only if data justifies it, revisit a blocking gate — and per the 2026-07-05 precedent, route it through an independent `config-safety-reviewer` with execution testing before it touches `settings.json`.
3. Tune thresholds once real violations exist to tune against.
