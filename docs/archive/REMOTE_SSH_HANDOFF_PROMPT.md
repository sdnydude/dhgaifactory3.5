# Remote-SSH Session Handoff

**Updated:** January 28, 2026 10:40 AM

## Project Location

```
/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/
```

## Current Git State

| Property | Value |
|----------|-------|
| **Branch** | `feature/langgraph-migration` |
| **Last commit** | `f7915a4` |
| **Status** | Clean, synced with remote |

## What Was Done This Session

1. ✅ Committed all outstanding files
2. ✅ Fixed hardcoded credentials in scripts (now use env vars)
3. ✅ Added swincoming/ to .gitignore (1GB of .pb files)
4. ✅ Removed swincoming from git history
5. ✅ Rebased onto master
6. ✅ Synced .agent/ folder from Mac to .251
7. ✅ Deleted 4 stale remote branches
8. ✅ Generated embeddings for 4,712 messages
9. ✅ Created git-github workflow (`/git-github`)
10. ✅ Created session context docs
11. ✅ Added mandatory-context.md rule (CR database query + pre-response enforcement)
12. ✅ Created FRONT_FACING_AGENTS_PLAN.md (CME Research + Visuals)

## Database (CR)

- **4,712 messages** with embeddings (MiniLM 384-dim)
- **4,974 total messages** in antigravity_messages
- Scripts use environment variables (DB_PASSWORD)

## Immediate Priority

### 2 Front-Facing Agent Completions

1. **CME Research Agent** - LibreChat form, RAGFlow integration, output templates
2. **Visuals Agent** - Control panel, LibreChat integration

See: `docs/FRONT_FACING_AGENTS_PLAN.md`

## Platform Roles

| Platform | Role | Status |
|----------|------|--------|
| **LibreChat** | Chat UI | Running :3010 |
| **Dify** | Workflow builder | Running :3000 |
| **RAGFlow** | Enterprise RAG | Running :8585 |
| **LangSmith** | Agent tracing | Cloud |

## Key Workflows

- `/pre-response` — MANDATORY read before every response
- `/agent-check` — Full status check
- `/git-github` — Git operations

## Mandatory Rules

1. Read `/pre-response` before EVERY response
2. Query CR database for lost context
3. Server-first: All files on .251
4. No placeholders or shortcuts
5. Verify before claiming completion

## To Resume

```
Run /agent-check for current status.
Read docs/FRONT_FACING_AGENTS_PLAN.md for the 2 priority agents.
```
