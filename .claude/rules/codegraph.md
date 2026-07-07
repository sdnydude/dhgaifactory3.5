# CodeGraph Usage Rules

This project has CodeGraph initialized at `.claude/../.codegraph/`. Follow these rules when using it.

## Lookup Precedence

Three lookup regimes coexist in this project; pick by what you are looking up, not by habit:

| What you are looking up | Use | Do not |
|---|---|---|
| A symbol by name (function, class, method, variable) | CodeGraph (`codegraph_search` / `codegraph_node`) | grep for the symbol |
| How source code works (behavior, call flow, "where else do we…") | graphify (`graphify query` / `explain` / `path`), then an Explore subagent | read raw source before orienting |
| Markdown, config, or instruction files (`.md`, `.json`, `.yml`, anything under `.claude/**` or `docs-site/**`) — or a string literal (error text, config value) | grep directly | graphify or CodeGraph (they index code, not prose; they mis-orient here) |

The graphify hooks are scoped to source-code paths only — grepping or reading the instruction layer does not (and should not) trigger a graphify nudge.

## Legacy Path Warning

`agents/` is the legacy Docker-based FastAPI agent system, being decommissioned. Current LangGraph agents live in `langgraph_workflows/dhg-agents-cloud/src/`. CodeGraph indexes both; when searching for an agent by name, prefer results from `langgraph_workflows/` and treat `agents/` results as legacy reference.

---

Which CodeGraph calls are main-session-safe (`_search`/`_node`/`_callers`/`_impact`) vs Explore-subagent-only (`_explore`/`_context`), the Explore-subagent decision table, and the FileWatcher/`codegraph sync` details all live in the global CLAUDE.md CodeGraph section — not duplicated here.
