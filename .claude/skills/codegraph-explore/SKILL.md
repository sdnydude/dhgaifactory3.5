---
name: codegraph-explore
description: Use when spawning an Explore subagent to investigate code flow, trace cross-file behavior, or answer open-ended "how does X work" questions in this repo. Provides the standardized prompt template with CodeGraph instructions, project context, and honesty guardrails. Invoke BEFORE calling the Agent tool with subagent_type=Explore so the prompt is built correctly.
---

# CodeGraph Explore Subagent Template

This skill provides the canonical prompt template for spawning Explore subagents that use CodeGraph. Use it whenever the rule in `.claude/rules/codegraph.md` says to spawn an Explore subagent.

## How to use

1. Identify the user's question and the key files/symbols involved.
2. Choose a thoroughness level: **quick**, **medium**, or **very thorough**.
3. Fill in the template below, replacing every `<<...>>` placeholder.
4. Call the Agent tool with `subagent_type: "Explore"` and the filled-in prompt.
5. Relay the subagent's summary to the user — do NOT paraphrase the subagent's tool output, just its written report.

## Prompt template

Copy this and fill in the placeholders:

```
<<ONE-SENTENCE TASK>>. I want <<the specific output shape — flow diagram, impact list, "where is X used", etc.>>.

Thoroughness: **<<quick|medium|very thorough>>**. <<Optional: why this level was chosen.>>

## Project context

This is DHG AI Factory v3.5. Key facts for this question:
- <<Relevant subsystem — e.g., "LangGraph agents live in langgraph_workflows/dhg-agents-cloud/src/, FastAPI Registry in registry/">>
- <<Current vs legacy note if applicable — e.g., "agents/ is the legacy path, langgraph_workflows/ is current">>
- <<Auth / infra facts if relevant — e.g., "LangGraph Cloud URL + x-api-key header; Cloudflare JWT for registry proxy">>
- <<Uncommitted-work warning if git status shows modified files touched by the question — name them explicitly>>

## CodeGraph instructions

This project has CodeGraph initialized (.codegraph/ exists). Use `codegraph_explore` as your PRIMARY tool — it returns full source sections from all relevant files in one call.

**Rules:**
1. Follow the explore call budget in the `codegraph_explore` tool description — it scales automatically based on project size.
2. Do NOT re-read files that `codegraph_explore` already returned source code for. The source sections are complete and authoritative.
3. Only fall back to grep/glob/Read for files listed under "Additional relevant files" if you need more detail, or if CodeGraph returned no results.
4. If you need to check the working-tree state of a file that's in git status as modified, Read it directly — CodeGraph's index may lag unstaged edits.

## What to report back

Keep the report under ~<<400–600>> words. Structure it as:

1. <<Primary deliverable — flow diagram / impact list / component map>>
2. **Key functions** (file:line for each hop)
3. <<Secondary deliverables specific to the question>>
4. **Benchmark notes at the end**: (a) total tool calls, (b) codegraph_* vs grep/read/glob breakdown, (c) whether CodeGraph gave you everything or you needed fallback and WHY, (d) anything CodeGraph missed or got wrong.

## Honesty guardrails

- If you're uncertain about a claim, say so explicitly. Do not present guesses as facts.
- If CodeGraph returned no results for a symbol, say "CodeGraph returned no results for X" rather than inferring from filename.
- If you fall back to Read/grep, say WHY (index stale? wrong kind of file? symbol too generic?). Be specific — "CodeGraph didn't return it" is not enough.
- Truth over impressiveness. A short, accurate report is worth more than a long report with fabricated details.
```

## Thoroughness level guide

- **quick**: 1–2 tool calls, short report (~200 words). Use for "where is X defined" when CodeGraph's main-session tools would suffice but the question has one extra hop.
- **medium**: moderate exploration, ~400 words. Default for most cross-cutting questions.
- **very thorough**: comprehensive multi-round exploration, ~600 words, multiple naming conventions checked. Use when the user explicitly asks for depth, or when the question is a benchmark/audit.

## When NOT to use this skill

- User asked for a code change (edit), not an explanation. Use targeted `codegraph_search` + Edit instead.
- Single-file or single-symbol lookup where `codegraph_search` / `codegraph_node` would answer in the main session.
- User said "just check" or "quick look" — work in the main session directly.

See `.claude/rules/codegraph.md` for the full decision table.
