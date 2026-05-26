---
sidebar_position: 4
title: Session Hooks
---

# Session Hooks

Claude Code hooks provide the automation layer that triggers capture and injects context without manual intervention.

## SessionStart Hook

Fires at the beginning of every Claude Code session. Runs `session-briefing.sh` which injects a 7-source context briefing:

| Source | What it provides |
|--------|-----------------|
| Recent sessions | Last 3 session summaries from registry |
| Recent ship sessions | Last 5 /ship workflow records |
| Recent activity | 7-day remember journal entries |
| Hot areas | Most-active code areas with tags |
| Correction lessons | Recent user corrections to avoid repeating |
| Bug-fix root causes | Recent debugging lessons |
| Decision log | Index of architectural decisions |
| Git state | Current branch + recent commits |
| Progress | Task completion status by phase |

This eliminates the cold-start problem — every new session starts with full project context.

## Stop Hook

Fires when a session ends. Performs a capture sweep:

1. Checks for any insights, decisions, or corrections that weren't captured during the session
2. Posts missed items to the registry
3. Updates session metadata

## PostToolUse Hooks

Two hooks fire after tool use:

### CodeGraph Sync (Write|Edit|MultiEdit)

Keeps the CodeGraph index current after file modifications:

```bash
test -d .codegraph && codegraph sync >/dev/null 2>&1 || true
```

### Enforce /ship (Bash)

When a `/ship` session is active, validates that code changes follow the /ship workflow and aren't being made outside the planned tasks.

## Memory System

The `.claude/projects/<project>/memory/` directory provides persistent file-based memory:

| File | Purpose |
|------|---------|
| `MEMORY.md` | Index of all memory files (loaded every session) |
| `user_*.md` | User profile and preferences |
| `feedback_*.md` | Behavioral corrections (do/don't) |
| `project_*.md` | Project state and context |
| `reference_*.md` | Pointers to external systems |
| `decisions_index.md` | Decision log index |

Memory files use frontmatter with `name`, `description`, `type` fields. They link to each other via `[[name]]` references.

### Memory Lifecycle

1. **Write**: Claude saves memories during sessions based on trigger conditions
2. **Read**: MEMORY.md is loaded at session start; individual files read on demand
3. **Update**: Stale memories are updated when contradicted by current state
4. **Prune**: Duplicate or outdated memories are removed

## Configuration

Hooks are configured in two places:

- `~/.claude/settings.json` — Global hooks (CodeGraph sync, Doppler env sync)
- `.claude/settings.json` — Project-level hooks (enforce-ship, session briefing)

Rules are in `.claude/rules/auto-*.md` — one per capture type, loaded into every session.
