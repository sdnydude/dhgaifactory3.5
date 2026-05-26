---
title: Session Hooks
sidebar_position: 5
---

# Session Hooks

Four Claude Code hooks inject prior knowledge from the DHG Registry into sessions automatically. Together they form the "read side" of the memreg pipeline — the write side captures events, the read side feeds them back.

All hooks share these properties:
- **Always exit 0** — a hook failure must never block a session
- **2-second curl timeout** — hooks that can't reach the registry silently degrade
- **Parallel curl calls** — multiple registry queries run concurrently to minimize latency
- **Project-aware** — derive the project name from the working directory and skip non-DHG projects silently

---

## session-start-kb-briefing.sh

**Event:** `SessionStart`

Fires once when a new Claude Code session begins. Prints a structured briefing that appears in the session context.

### What It Injects

```
=== KB BRIEFING — dhg-ai-factory (project-aware) ===
RECENT SHIPS (last 3):
  - memreg pipeline migration [complete]
  - close-the-loop v1 [complete]
OPEN HIGH-PRIORITY DEFERRED:
  - No test coverage: security_endpoints.py [Discovered during...]
  - Ship advisor fix — CME stats endpoints [...]
RELEVANT PRIOR WORK (KB, q="docs(memreg): add 2026-05-24..."):
  - [decisions] Standardize project_name to dhg-ai-factory
  - [insights] memreg migration B3 smoke test
=== END BRIEFING ===
```

### How It Works

1. Derives project name from `pwd` (e.g., `*/aifactory*` → `dhg-ai-factory`)
2. Short-circuits if the project is not in the known whitelist and no `.dhg-project` file exists
3. Extracts search keywords from the last 5 git commit messages
4. Fires 3 parallel curls:
   - `GET /api/ship-sessions?project_name=X&limit=3` — recent ships
   - `GET /api/deferred-items?project_name=X&status=open&priority=high&limit=5` — open high-priority items
   - `POST /api/kb/search` — KB matches from git log keywords
5. Parses responses with shape-tolerant `jq` filters (handles both array and object responses)
6. Prints the briefing to stdout

### Complements, Does Not Duplicate

This hook complements the existing `~/.claude/scripts/session-briefing.sh` which covers corrections pattern summaries and deferred-count totals. The KB briefing adds project-specific ships, deferred item titles, and semantic KB search results.

---

## user-prompt-kb-inject.sh

**Event:** `UserPromptSubmit`

Fires on every user prompt. Searches the KB for content relevant to what the user just asked, and injects matches as `additionalContext` so Claude has prior work context before responding.

### Filtering Logic

The hook skips noise to avoid unnecessary registry calls:

| Filter | Skips when... |
|--------|--------------|
| Word count | Prompt is fewer than 4 words |
| Noise words | Prompt matches `yes`, `no`, `go`, `ok`, `continue`, `done`, `thanks`, `approved`, `lgtm`, `ship it`, etc. |
| Keyword match | Prompt doesn't contain any of: `plan`, `design`, `review`, `fix`, `how`, `build`, `analyze`, `implement`, `audit`, `trace`, `what`, `where`, `why`, `debug`, `investigate`, `refactor`, `ship`, `test`, `deploy`, `wire`, `hook`, `read-side` |

### What It Injects

When the prompt passes all filters:

1. Searches KB with the user's prompt text (first 200 chars)
2. Fetches correction stats (`GET /api/corrections/stats`)
3. If the active correction pattern has recent hits, adds a warning: `ACTIVE CORRECTION PATTERN: fabrication (4x in 7d)`
4. Lists matched KB results: `[decision] Use medkb /v1/query when ingestor ships`

### Output Protocol

Uses the `UserPromptSubmit` hook output format:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "ACTIVE CORRECTION PATTERN: ...\n\nPRIOR KB WORK: ..."
  }
}
```

---

## subagent-start-kb-inject.sh

**Event:** `SubagentStart`

Fires every time Claude dispatches a subagent (Explore, code-reviewer, etc.). Injects recent corrections and decisions so subagents don't silently contradict prior session work.

### What It Injects

1. Searches KB for corrections and decisions matching the current project
2. If an active correction pattern exists, adds: `CORRECTION PATTERN (fabrication): verify facts before asserting`
3. Lists the 3 most relevant prior decisions/corrections

### Why This Matters

Subagents start with no project context — they don't see CLAUDE.md, memory files, or the main session's conversation history. Without this hook, a subagent could recommend an approach that was explicitly rejected in a prior session. The injection gives subagents just enough context to avoid contradicting established decisions.

---

## pre-tool-kb-search-inject.sh

**Event:** `PreToolUse` (filtered to `Agent` and `Task` tool calls only)

Fires before Claude dispatches an Agent subagent, but only when the agent's prompt contains trigger keywords that suggest research or analysis work.

### Trigger Keywords

The hook only fires when the agent prompt contains: `audit`, `plan`, `design`, `recommend`, `review`, `how does`, `what do we know`, `trace`, `investigate`, `analyze`.

Other Agent dispatches (e.g., simple file searches) pass through with no injection.

### What It Injects

```
=== RELEVANT PRIOR KB FINDINGS (auto-injected, project=dhg-ai-factory) ===
The following items from the DHG Registry KB match this Agent dispatch's
prompt keywords. Consult these before answering.

- [decision] Use symlink-based install for memreg
- [insight] Pydantic schemas are hand-constructed in endpoint files
- [deferred] No test coverage: security_endpoints.py
=== END KB FINDINGS ===
```

### Relationship to subagent-start-kb-inject

Both hooks inject into subagents, but at different points:

| Hook | When | What | Scope |
|------|------|------|-------|
| `subagent-start-kb-inject` | At subagent creation | Corrections + decisions | All subagent types |
| `pre-tool-kb-search-inject` | Before Agent tool call | Full KB search results | Only Agent/Task with trigger keywords |

They complement each other — the SubagentStart hook provides baseline correction awareness, while the PreToolUse hook provides topic-specific prior work context.

---

## Installing Hooks

Hooks are registered in `~/.claude/settings.json` under the appropriate event keys. Example entries:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "bash ~/DHG/dhg-memreg/hooks/session-start-kb-briefing.sh 2>/dev/null || true",
        "timeout": 8000
      }
    ],
    "UserPromptSubmit": [
      {
        "type": "command",
        "command": "bash ~/DHG/dhg-memreg/hooks/user-prompt-kb-inject.sh 2>/dev/null || true",
        "timeout": 5000
      }
    ],
    "SubagentStart": [
      {
        "type": "command",
        "command": "bash ~/DHG/dhg-memreg/hooks/subagent-start-kb-inject.sh 2>/dev/null || true",
        "timeout": 5000
      }
    ],
    "PreToolUse": [
      {
        "type": "command",
        "command": "bash ~/DHG/dhg-memreg/hooks/pre-tool-kb-search-inject.sh 2>/dev/null || true",
        "timeout": 5000
      }
    ]
  }
}
```

The `2>/dev/null || true` wrapper ensures that hook failures never produce visible errors or block sessions.
