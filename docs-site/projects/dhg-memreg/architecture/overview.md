---
title: Architecture Overview
sidebar_position: 1
---

# Architecture Overview

dhg-memreg is a standalone toolchain that bridges Claude Code sessions and the DHG Registry. It has no runtime server of its own — it's a collection of scripts and hooks that run inside Claude Code's process model.

## System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code Session                      │
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐ │
│  │ .claude/rules│   │ Claude Code   │   │ Claude Code      │ │
│  │ auto-*.md    │   │ Hook Engine   │   │ Skill System     │ │
│  │ (7 triggers) │   │ (4 hooks)     │   │ (kb-search)      │ │
│  └──────┬───────┘   └──────┬───────┘   └────────┬─────────┘ │
│         │                  │                     │           │
└─────────┼──────────────────┼─────────────────────┼───────────┘
          │                  │                     │
          ▼                  ▼                     ▼
┌──────────────────────────────────────────────────────────────┐
│                      dhg-memreg repo                         │
│                                                              │
│  scripts/              hooks/              skills/           │
│  ├─ memreg_capture.py  ├─ session-start-   └─ kb-search/    │
│  ├─ post-*.sh (7)      │  kb-briefing.sh      ├─ SKILL.md   │
│  ├─ ingest-memory-     ├─ user-prompt-        └─ search.sh  │
│  │  files.py           │  kb-inject.sh                       │
│  └─ ingest-claude-     ├─ subagent-start-                    │
│     md.py              │  kb-inject.sh                       │
│                        └─ pre-tool-kb-                       │
│                           search-inject.sh                   │
└──────────────────────────┬───────────────────────────────────┘
                           │
                    HTTP (LAN only)
                    10.0.0.251:8011
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    DHG Registry API                           │
│                    (FastAPI on g700data1)                     │
│                                                              │
│  POST /api/bug-fixes        GET /api/ship-sessions           │
│  POST /api/corrections      GET /api/deferred-items          │
│  POST /api/decision-logs    GET /api/corrections/stats       │
│  POST /api/deferred-items   POST /api/kb/search              │
│  POST /api/insights         POST /api/doc-pages/bulk         │
│  POST /api/ship-sessions                                     │
│  POST /api/test-coverage                                     │
│                                                              │
│                         ┌────────────┐                       │
│                         │ PostgreSQL │                       │
│                         │ 15 + pgvec │                       │
│                         └────────────┘                       │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

### Write Path (Capture)

```
Session event occurs (bug fixed, decision made, etc.)
  → .claude/rules/auto-*.md trigger rule matches
    → Claude calls ~/.claude/scripts/post-*.sh (symlink to dhg-memreg)
      → memreg_capture.py parses command + JSON payload
        → POST /api/<endpoint> with 2s connect timeout
          → Registry validates, persists to PostgreSQL
            → "insight captured: <uuid>" (stdout)
```

### Write Path (Ingestion)

```
User runs ingest script manually
  → ingest-memory-files.py reads ~/.claude/projects/<slug>/memory/*.md
    → Parses YAML frontmatter, routes by type
      → POST /api/decision-logs (type=decision)
      → POST /api/doc-pages/bulk (all other types)

  → ingest-claude-md.py reads ~/DHG/<project>/CLAUDE.md
    → Chunks by markdown heading
      → POST /api/doc-pages/bulk (batch upsert)
```

### Read Path (KB Intelligence)

```
Session starts
  → SessionStart hook fires
    → 3 parallel curls: ships, deferred items, KB search
      → Briefing injected into session context

User types a prompt
  → UserPromptSubmit hook fires
    → Skip if < 4 words, noise word, or no keyword match
    → 2 parallel curls: KB search (user prompt), correction stats
      → Matches + correction warnings injected as additionalContext

Claude dispatches a subagent
  → SubagentStart hook fires
    → 2 parallel curls: KB search (project), correction stats
      → Corrections + decisions injected into subagent context

Claude dispatches an Agent with analysis keywords
  → PreToolUse hook fires
    → KB search on agent prompt
      → Prior findings injected into agent context
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Standalone repo | Separate from aifactory | Memreg serves all DHG projects, not just AI Factory |
| Symlink install | `~/.claude/scripts/post-*.sh` → repo | Updates via `git pull` without re-installing |
| Fire-and-forget | Always exit 0, never block | Capture must never interfere with session work |
| Trigger rules per-project | `.claude/rules/auto-*.md` lives in each project | Each project can customize when capture fires |
| Parallel curls in hooks | `curl &` + `wait` pattern | KB briefing latency drops from ~8s to ~2s |
| Project derivation from pwd | Case statement on directory path | No env var to forget; works automatically |
| Unified Python dispatcher | `memreg_capture.py` replaces 7 bash implementations | Single code path for HTTP, timeout, error handling |

## Networking

All communication is over HTTP on the g700data1 LAN (`10.0.0.251:8011`). There is no authentication — the registry is LAN-only and not exposed through the Cloudflare tunnel.

**Docker note:** Containers using dhg-memreg must use `--network=host` to reach the registry at its LAN address. The default Docker bridge network does not route to `10.0.0.251`.

## Dependencies

dhg-memreg has minimal dependencies:

| Component | Dependency | Used For |
|-----------|-----------|----------|
| Capture scripts | Python 3.10+, `httpx` | HTTP POST to registry |
| Hooks | `bash`, `curl`, `jq` | Registry queries + JSON parsing |
| KB search skill | `bash`, `curl`, `jq` | Same as hooks |
| Docker image | Python 3.10 base | Containerized execution |

No database, no server process, no background daemon. Everything runs on-demand inside Claude Code's hook/script execution model.
