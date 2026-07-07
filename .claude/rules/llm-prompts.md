# LLM Prompts — versioned prompt modules, never inline literals

Applies to `langgraph_workflows/dhg-agents-cloud/src/` (all LangGraph agents).

## The rule
- **Every agent prompt lives in a versioned prompt module:** `src/prompts/<agent_name>.py` (agent name without the `_agent` suffix), exporting UPPERCASE named constants. Agent modules import — they never inline.
- **Prompt literals >1 line in agent code are a review-blocking violation.** This covers system prompts, extraction/verification templates, and reusable guidance blocks. (Existing per-node f-string bodies that interpolate local state are grandfathered — see Scope below — but new ones must compose from imported constants.)
- **Prompt changes ship as prompt-file diffs.** A prompt edit is reviewable in isolation — no agent-logic noise in the diff, LLM-agnostic per the standing LLM strategy.
- **Extraction must be byte-identical.** When moving a literal, SHA-256 the string value before and after; the hashes must match. Zero behavioral change is the contract.
- **`langgraph.json` is the source of truth** for which agents exist. When adding an agent, add its prompts module in the same change.

## Scope (as of 2026-07-07 extraction)
- All 17 module-level prompt constants across the 14 registered agent modules live in `src/prompts/` (import-checked, hash-verified).
- Grandfathered: per-node f-string prompt bodies inside node functions that interpolate local state and compose from the imported system-prompt constants. Converting these is tracked as a deferred item — do not add new ones.

## Reviewer grep
```
# module-level multi-line string constants back in agent code — must return zero
grep -rnE '^[A-Z_]+ = (f?"""|\x27\x27\x27)' langgraph_workflows/dhg-agents-cloud/src/*_agent.py
```
