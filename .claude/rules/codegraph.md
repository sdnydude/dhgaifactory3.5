# CodeGraph Usage Rules

This project has CodeGraph initialized at `.claude/../.codegraph/`. Follow these rules when using it.

## Main-Session Safe vs Subagent-Only

The main session MUST NOT call `codegraph_explore` or `codegraph_context` directly — they return full source code sections from many files and pollute the main context window. Spawn an Explore subagent for any exploration that would use those tools.

These CodeGraph tools are safe to call directly in the main session (they return locations/metadata, not bodies):

| Tool | Use For |
|------|---------|
| `codegraph_search` | Find symbols by name |
| `codegraph_callers` / `codegraph_callees` | Trace call flow |
| `codegraph_impact` | Check blast radius before editing |
| `codegraph_node` | Get a single symbol's details |
| `codegraph_status` / `codegraph_files` | Index state |

## When to Spawn an Explore Subagent

| Trigger | Action |
|---------|--------|
| Open-ended "how does X work?", "trace the flow of Y", "where else do we Z?" | Spawn Explore subagent (`subagent_type: Explore`) with the `codegraph-explore` skill's prompt template |
| Question spans ≥3 files | Spawn Explore subagent |
| Single-file or single-symbol lookup with a known target | `codegraph_search` / `codegraph_node` in main session |
| About to edit and need an impact check | `codegraph_impact` in main session |
| User asks for a change, not an explanation | Skip Explore — targeted `codegraph_search` then Edit |
| User says "just check" or "quick look" | Main session only |

Rule of thumb: **Explore subagent for understanding, main session for doing.**

## Watcher State

The MCP server's FileWatcher is not reliably auto-syncing in this environment. Hooks in `~/.claude/settings.json` run `codegraph sync` at session start and after every Edit/Write/MultiEdit to keep the index fresh. If you suspect the index is stale (e.g., a symbol you just wrote is not found), run `codegraph sync` manually — it takes ~30–50ms per changed file.

## Legacy Path Warning

`agents/` is the legacy Docker-based FastAPI agent system, being decommissioned. Current LangGraph agents live in `langgraph_workflows/dhg-agents-cloud/src/`. CodeGraph indexes both; when searching for an agent by name, prefer results from `langgraph_workflows/` and treat `agents/` results as legacy reference.
