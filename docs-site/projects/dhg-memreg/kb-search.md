---
title: KB Search
sidebar_position: 6
---

# KB Search

The `kb-search` skill provides explicit, on-demand search over the DHG Registry knowledge base. While the session hooks inject KB context automatically, this skill gives you direct control — useful when you want to check what the registry knows about a specific topic before starting work.

## When to Use

Use `kb-search` before any of these activities:

- **Audit or review** — "audit the CME endpoints" → search first to see prior findings
- **Planning or design** — "plan the auth wiring" → search for prior decisions and deferred items
- **Recommendations** — "what should we use for X" → search for prior research
- **Investigation** — "how does X work" / "what do we know about X" → search for prior insights
- **New ship** — before starting `/ship` on a subsystem, search for prior session activity

Skipping KB search when the registry has relevant prior work leads to re-deriving decisions that were already made — the exact failure mode that the `feedback_loaded_is_not_attended` memory warns against.

## Usage

```bash
bash ~/DHG/dhg-memreg/skills/kb-search/search.sh "<query>" [project=<name>] [limit=<N>] [sources=<csv>]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `<query>` | Required | Free-text search query |
| `project=` | Derived from `pwd` | Project name filter |
| `limit=` | `5` | Max results to return |
| `sources=` | `decisions,insights,deferred_items,ship_sessions` | Comma-separated source types to search |

## Output

Returns a markdown table for direct use in conversation context:

```
Query: memreg capture pipeline (project=dhg-ai-factory, 5 results)

| Source | Title | Score |
|---|---|---|
| decision | Use medkb /v1/query when ingestor ships | 0.91 |
| insight  | Dashboard decomposition pattern | 0.84 |
| deferred | No test coverage: kb_endpoints.py | 0.77 |
| decision | Standardize project_name to dhg-ai-factory | 0.72 |
| insight  | Memreg capture pipeline was built for Portage | 0.68 |
```

If no results match, returns `(no KB matches for: <query>)`.

If the registry is unreachable, returns `(KB search failed — registry unreachable)`.

## Examples

```bash
# Search for prior decisions about auth
bash ~/DHG/dhg-memreg/skills/kb-search/search.sh "authentication wiring"

# Search only for deferred items in portage
bash ~/DHG/dhg-memreg/skills/kb-search/search.sh "billing" project=portage sources=deferred_items

# Broad search with more results
bash ~/DHG/dhg-memreg/skills/kb-search/search.sh "observability prometheus" limit=10
```

## How It Works

1. Derives the project name from `pwd` if not specified (same logic as the hooks)
2. Builds a JSON payload with query, project, sources, and limit
3. POSTs to `$REGISTRY_URL/api/kb/search` (default: `http://10.0.0.251:8011/api/kb/search`)
4. Parses the response (handles both `{results: [...]}` and bare array formats)
5. Formats results as a markdown table

The search endpoint uses hybrid full-text + vector search on the registry side, so both keyword matches and semantic similarity are considered.

## Relationship to Hooks

The `pre-tool-kb-search-inject.sh` hook runs this same search automatically when you dispatch an Agent subagent with trigger keywords in its prompt. That hook is a safety net — the kb-search skill is the explicit, controllable version for when you want to search intentionally.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REGISTRY_URL` | `http://10.0.0.251:8011` | Registry base URL |
| `KB_ENDPOINT` | `$REGISTRY_URL/api/kb/search` | KB search endpoint (override for future medkb swap) |
