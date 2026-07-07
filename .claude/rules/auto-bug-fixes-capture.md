---
name: Auto-capture bug fixes
description: Instructs Claude to post bug-fix root cause analyses to the registry whenever a non-trivial bug is diagnosed and fixed
type: rule
---

## When to trigger

After completing a debugging session where ALL of the following are true:

1. A **symptom** was observed (error, unexpected behavior, test failure, crash)
2. A **root cause** was identified (not just "it works now" — the actual why)
3. A **fix was applied** (code change, config change, or workaround)
4. The fix was **non-trivial** — skip single-typo fixes, missing imports, or obvious syntax errors

Examples that SHOULD trigger:
- Database query returning wrong results due to missing join or bad SQL
- Docker container failing to start due to environment variable misconfiguration
- Frontend state corruption from stale closure in useEffect
- Registry endpoint returning 500 due to unhandled null in service layer
- LangGraph agent node timeout from missing asyncio.wait_for
- Prometheus scrape target down due to network misconfiguration
- Auth middleware blocking endpoints that should be open
- Serializer drift between Pydantic schema and SQLAlchemy model

Examples that should NOT trigger:
- Missing semicolon / syntax error
- Forgot to import a module
- Typo in variable name
- Simple "add the missing field" fixes

## What to capture

Required fields:
- `tldr`: One-line summary of the bug (max 280 chars)
- `symptom`: What was observed — the user-visible or developer-visible behavior
- `root_cause`: What was actually wrong — the underlying technical cause
- `fix_applied`: What was changed to fix it — be specific about files and approach
- `severity`: One of `low`, `medium`, `high`, `critical`
- `category`: One of `registry`, `cme`, `langgraph`, `frontend`, `database`, `infra`, `observability`, `auth`, `api`, `testing`, `security`, `performance`, `config`, `other`
- `project_name`: "dhg-ai-factory"

Optional fields:
- `files_affected`: Array of file paths that were modified as part of the fix
- `source_file`: Primary file where the bug was located
- `tags`: Semantic search tags (e.g., `["sql","service-layer","null-handling"]`)
- `session_id`: Current session ID if known
- `model_name`: the current session's model ID — never hardcode

### Severity guide

| Severity | When to use |
|----------|-------------|
| `critical` | Data loss, security vulnerability, complete feature outage |
| `high` | Major feature broken, auth issues, data corruption risk |
| `medium` | Feature degraded, incorrect behavior affecting some users |
| `low` | Minor UI glitch, edge case, cosmetic issue |

## How to call

After diagnosing and fixing the bug, call the capture script silently in a bash tool call:

```bash
~/.claude/scripts/post-bug-fixes.sh --stdin <<'MEMREG_JSON'
{"tldr":"<summary>","symptom":"<what was observed>","root_cause":"<what was wrong>","fix_applied":"<what was changed>","files_affected":["<file1>","<file2>"],"severity":"<severity>","category":"<category>","project_name":"dhg-ai-factory","source_file":"<primary file>","tags":["<tag1>","<tag2>"],"model_name":"<current session model ID>"}
MEMREG_JSON
```

## Do not ask permission

Call this automatically every time the trigger condition is met — see [capture-common.md](capture-common.md) for the shared mechanics (automated fire-and-forget, announce-only-on-failure, planning-gate exemption, `model_name`, LAN IP).
