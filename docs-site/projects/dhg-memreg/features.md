---
title: Features
sidebar_label: Features
sidebar_position: 2
---

# Features

*Last updated: 2026-05-25*

dhg-memreg closes the loop between Claude Code sessions — what one session learns, future sessions know. It captures structured events during sessions, syncs persistent memory files into the registry, and injects relevant prior knowledge back into new sessions automatically.

---

## What Makes This Different

| Traditional approach | What memreg does |
|---------------------|------------------|
| Memory files in `~/.claude/projects/` are local markdown that Claude reads at session start | Memory files are also bulk-synced to the registry, making them searchable via KB queries and available to hooks |
| CLAUDE.md is loaded once and pattern-matched against the request | CLAUDE.md content is chunked and indexed in the registry, enabling semantic search across all projects |
| Session insights die with the session | 7 event types are captured in real time and persisted to PostgreSQL with full-text + vector search |
| Subagents start with no project context | Hooks inject corrections, decisions, and KB matches into every subagent at spawn time |
| "Did we already decide this?" requires human memory | KB search returns prior decisions, insights, and deferred items before Claude answers |

---

## Three Systems

### 1. Real-Time Capture (7 Scripts)

During every Claude Code session, trigger rules in `.claude/rules/auto-*.md` fire capture scripts automatically when specific events occur. Each script POSTs a JSON payload to the DHG Registry and exits immediately — never blocking the session.

| Event | Trigger | What's Captured |
|-------|---------|-----------------|
| Bug Fix | Non-trivial bug diagnosed and fixed | Symptom, root cause, fix applied, severity, affected files |
| Correction | User pushes back on Claude's behavior | User message, what Claude did wrong, what it should do instead |
| Decision | Architecture/implementation choice with rejected alternatives | Choice, alternatives, rationale, domain |
| Deferred Item | Work discovered but intentionally not done | Title, description, reason deferred, priority |
| Insight | Non-obvious technical discovery | Summary, full statement, category |
| Ship Session | `/ship` workflow completes | Feature, approach, status, commits, verification results |
| Test Coverage | Tests added, removed, or modified | Before/after counts, delta, test names, trigger |

All 7 scripts share a unified Python dispatcher (`memreg_capture.py`) with a 2-second connect timeout and fire-and-forget semantics.

### 2. Bulk Ingestion (2 Scripts)

Two Python scripts sync larger content into the registry on demand:

| Script | What It Syncs | Registry Target |
|--------|--------------|-----------------|
| `ingest-memory-files.py` | `~/.claude/projects/<slug>/memory/*.md` files with frontmatter | `decisions` table (type=decision) or `doc_pages` table (all other types) |
| `ingest-claude-md.py` | `CLAUDE.md` files from all DHG projects, chunked by heading | `doc_pages` table (bulk upsert) |

Both support `--dry-run` for previewing changes and `--registry-url` for targeting alternate registries.

### 3. KB Intelligence (4 Hooks + 1 Skill)

The read side — injecting prior knowledge back into sessions:

| Hook | Event | What It Injects |
|------|-------|-----------------|
| `session-start-kb-briefing.sh` | SessionStart | Recent ships, high-priority deferred items, KB matches from git log keywords |
| `user-prompt-kb-inject.sh` | UserPromptSubmit | KB matches for the user's prompt + active correction pattern warning |
| `subagent-start-kb-inject.sh` | SubagentStart | Recent corrections and decisions for the current project |
| `pre-tool-kb-search-inject.sh` | PreToolUse (Agent) | KB matches when an Agent dispatch contains audit/plan/design/review keywords |

The `kb-search` skill provides explicit, on-demand search when Claude (or the user) wants to query the KB directly rather than relying on automatic injection.

---

## Capture Pipeline at a Glance

```
Claude Code Session
  │
  ├─ auto-*.md trigger rules fire on matching events
  │    └─ ~/.claude/scripts/post-*.sh (symlinks to dhg-memreg)
  │         └─ memreg_capture.py → POST /api/<endpoint>
  │              └─ DHG Registry (PostgreSQL)
  │
  ├─ SessionStart hook
  │    └─ session-start-kb-briefing.sh
  │         └─ GET recent ships, deferred items
  │         └─ POST /api/kb/search (git log keywords)
  │         └─ Injects briefing into session context
  │
  ├─ UserPromptSubmit hook
  │    └─ user-prompt-kb-inject.sh
  │         └─ POST /api/kb/search (user's prompt)
  │         └─ GET /api/corrections/stats
  │         └─ Injects KB matches + correction warnings
  │
  ├─ SubagentStart hook
  │    └─ subagent-start-kb-inject.sh
  │         └─ Injects corrections + decisions into every subagent
  │
  └─ PreToolUse hook (Agent dispatches only)
       └─ pre-tool-kb-search-inject.sh
            └─ POST /api/kb/search (agent prompt keywords)
            └─ Injects relevant prior work into agent context
```

---

## Supported Projects

Memreg derives the project name from the current working directory:

| Directory pattern | Project name |
|-------------------|-------------|
| `*/aifactory*` | `dhg-ai-factory` |
| `*/portage*` | `portage` |
| `*/c2l-vault*` | `c2l-vault` |
| `*/claude-code-tresor*` | `claude-code-tresor` |
| `*/Digital-Harmony-Studio*` | `digital-harmony-studio` |

Sessions in unknown directories are silently skipped by the KB hooks (no noise). To enable memreg for a new project, add a `.dhg-project` sentinel file to the project root and add the directory pattern to the hooks' case statements.
