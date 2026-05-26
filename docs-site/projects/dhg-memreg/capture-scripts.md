---
title: Capture Scripts
sidebar_position: 3
---

# Capture Scripts

Seven fire-and-forget scripts capture structured events from Claude Code sessions into the DHG Registry. Each accepts a single JSON payload string and POSTs to a specific registry endpoint.

## How They Work

All 7 scripts are thin bash shims that delegate to `memreg_capture.py`, a unified Python dispatcher:

```
post-insight.sh "{...}"
  → memreg_capture.py post-insight "{...}"
    → POST http://10.0.0.251:8011/api/insights
      → "insight captured: <uuid>"
```

**Contract:**
- Always exit 0 (never block the session)
- 2-second connect timeout, 5-second max time
- On success: prints `<label> captured: <uuid>` to stdout
- On failure: prints error to stderr, still exits 0

## Trigger Rules

Each capture script is fired automatically by a corresponding trigger rule in the consuming project's `.claude/rules/` directory:

| Script | Trigger Rule | When It Fires |
|--------|-------------|---------------|
| `post-bug-fixes.sh` | `auto-bug-fixes-capture.md` | After a non-trivial bug is diagnosed and fixed |
| `post-correction.sh` | `auto-correction-capture.md` | When the user corrects Claude's behavior |
| `post-decision-logs.sh` | `auto-decision-logs-capture.md` | When an architectural/implementation decision is made |
| `post-deferred-items.sh` | `auto-deferred-items-capture.md` | When work is discovered but intentionally not done |
| `post-insight.sh` | `auto-insight-capture.md` | When a non-obvious technical insight is generated |
| `post-ship-session.sh` | `auto-ship-session-capture.md` | At the end of a `/ship` workflow |
| `post-test-coverage.sh` | `auto-test-coverage-capture.md` | After tests are added, removed, or modified |

The trigger rules live in each project (e.g., `dhgaifactory3.5/.claude/rules/`), not in the dhg-memreg repo. This separation lets each project define its own trigger conditions while sharing the same capture infrastructure.

---

## Script Reference

### post-bug-fixes

**Endpoint:** `POST /api/bug-fixes`

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `tldr` | Yes | string (max 280) | One-line bug summary |
| `symptom` | Yes | string | What was observed |
| `root_cause` | Yes | string | What was actually wrong |
| `fix_applied` | Yes | string | What was changed |
| `severity` | Yes | enum | `low`, `medium`, `high`, `critical` |
| `category` | Yes | enum | `registry`, `cme`, `langgraph`, `frontend`, `database`, `infra`, `observability`, `auth`, `api`, `testing`, `security`, `performance`, `config`, `other` |
| `project_name` | Yes | string | e.g., `dhg-ai-factory` |
| `files_affected` | No | string[] | File paths modified |
| `source_file` | No | string | Primary file where the bug lived |
| `tags` | No | string[] | Semantic search tags |
| `model_name` | No | string | e.g., `claude-opus-4-6` |

```bash
~/.claude/scripts/post-bug-fixes.sh '{
  "tldr": "Registry endpoint returning 500 due to unhandled null",
  "symptom": "GET /api/cme/stats returns 500 on projects with no sessions",
  "root_cause": "Service layer called .first() without null check",
  "fix_applied": "Added Optional[] return type and null guard in cme_service.py",
  "files_affected": ["registry/cme_service.py", "registry/cme_endpoints.py"],
  "severity": "medium",
  "category": "registry",
  "project_name": "dhg-ai-factory",
  "tags": ["null-handling", "service-layer"],
  "model_name": "claude-opus-4-6"
}'
```

### post-correction

**Endpoint:** `POST /api/corrections`

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `project_name` | Yes | string | e.g., `dhg-ai-factory` |
| `category` | Yes | enum | `docker-guessing`, `fabrication`, `missed-context`, `wrong-assumption`, `repeated-instruction`, `workflow-violation`, `premature-action`, `other` |
| `user_message` | Yes | string | The user's exact correction message |
| `context` | Yes | string | What Claude had just done |
| `claude_action` | Yes | string | What Claude should have done instead |
| `tags` | No | string[] | Semantic search tags |
| `model_name` | No | string | Model in use |

```bash
~/.claude/scripts/post-correction.sh '{
  "project_name": "dhg-ai-factory",
  "category": "fabrication",
  "user_message": "that file doesnt exist",
  "context": "Claude referenced registry/kb_service.py which does not exist in the codebase",
  "claude_action": "Should have verified file existence with ls or Read before referencing it",
  "tags": ["file-reference", "verification"],
  "model_name": "claude-opus-4-6"
}'
```

### post-decision-logs

**Endpoint:** `POST /api/decision-logs`

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `title` | Yes | string (max 280) | Short decision title |
| `choice` | Yes | string | What was decided |
| `rationale` | Yes | string | Why this choice was made |
| `domain` | Yes | enum | `registry`, `frontend`, `langgraph`, `cme`, `infra`, `observability`, `auth`, `ops` |
| `project_name` | Yes | string | e.g., `dhg-ai-factory` |
| `alternatives_rejected` | No | string | What was considered and rejected |
| `source_file` | No | string | File being discussed |
| `tags` | No | string[] | Semantic search tags |
| `supersedes` | No | string | Slug of a previous decision this replaces |
| `model_name` | No | string | Model in use |

```bash
~/.claude/scripts/post-decision-logs.sh '{
  "title": "Use symlink-based install for memreg",
  "choice": "Symlink ~/.claude/scripts/post-*.sh to dhg-memreg/scripts/",
  "alternatives_rejected": "Copy scripts directly (no update path), npm package (overkill)",
  "rationale": "Symlinks allow updating scripts by pulling the repo without re-installing",
  "domain": "infra",
  "project_name": "dhg-ai-factory",
  "tags": ["memreg", "install"],
  "model_name": "claude-opus-4-6"
}'
```

### post-deferred-items

**Endpoint:** `POST /api/deferred-items`

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `title` | Yes | string (max 280) | Short description of deferred work |
| `description` | Yes | string | What needs to be done |
| `reason` | Yes | string | Why it was deferred |
| `priority` | Yes | enum | `low`, `medium`, `high`, `critical` |
| `category` | Yes | enum | Same as bug-fixes categories |
| `project_name` | Yes | string | e.g., `dhg-ai-factory` |
| `source_context` | No | string | What work was happening when discovered |
| `status` | No | enum | `open`, `in_progress`, `resolved`, `wont_fix` (default: `open`) |
| `affected_files` | No | string[] | Files that would need changes |
| `tags` | No | string[] | Semantic search tags |
| `model_name` | No | string | Model in use |

```bash
~/.claude/scripts/post-deferred-items.sh '{
  "title": "Add rate limiting to CME sync endpoints",
  "description": "CME sync endpoints have no rate limiting — could be abused to overload PubMed API",
  "reason": "Out of scope for current /ship session",
  "source_context": "/ship advisor fix C8",
  "priority": "medium",
  "category": "security",
  "project_name": "dhg-ai-factory",
  "affected_files": ["registry/cme_endpoints.py"],
  "tags": ["rate-limiting", "cme", "security"],
  "model_name": "claude-opus-4-6"
}'
```

### post-insight

**Endpoint:** `POST /api/insights`

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `tldr` | Yes | string (max 280) | One-line summary |
| `insight_statement` | Yes | string | Full insight text |
| `project_name` | Yes | string | e.g., `dhg-ai-factory` |
| `category` | Yes | enum | `testing`, `architecture`, `security`, `performance`, `patterns`, `debugging`, `database`, `frontend`, `devops`, `api-design`, `langgraph`, `observability`, `cme` |
| `source_file` | No | string | File the insight relates to |
| `tags` | No | string[] | Semantic search tags |
| `model_name` | No | string | Model in use |

```bash
~/.claude/scripts/post-insight.sh '{
  "tldr": "Pydantic schemas in endpoint files are hand-constructed, not auto-generated",
  "insight_statement": "When data exists in the DB but is missing from API responses, the cause is almost always serializer drift in the endpoint Pydantic schema — not a migration issue.",
  "project_name": "dhg-ai-factory",
  "category": "api-design",
  "source_file": "registry/cme_endpoints.py",
  "tags": ["pydantic", "serializer", "debugging"],
  "model_name": "claude-opus-4-6"
}'
```

### post-ship-session

**Endpoint:** `POST /api/ship-sessions`

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `project_name` | Yes | string | e.g., `dhg-ai-factory` |
| `feature` | Yes | string | Feature name |
| `approach` | No | string | Implementation summary |
| `status` | No | string | `complete`, `partial`, `blocked` |
| `complexity` | No | enum | `simple`, `complex` |
| `tdd` | No | boolean | Whether TDD was used |
| `pr_url` | No | string | Pull request URL |
| `branch` | No | string | Branch name |
| `completed_at` | No | string | ISO 8601 timestamp |
| `commits` | No | string[] | Commit summaries |
| `deferred` | No | string[] | Deferred items |
| `decisions` | No | string[] | Decisions made |
| `review` | No | object | Review results |
| `verification` | No | object | Verification results |
| `tags` | No | string[] | Semantic search tags |
| `model_name` | No | string | Model in use |

```bash
~/.claude/scripts/post-ship-session.sh '{
  "project_name": "dhg-ai-factory",
  "feature": "memreg pipeline migration",
  "approach": "Extract capture scripts from aifactory into standalone dhg-memreg repo",
  "status": "complete",
  "complexity": "complex",
  "commits": ["a9430bb refactor: unify capture scripts"],
  "tags": ["memreg", "migration"],
  "model_name": "claude-opus-4-6"
}'
```

### post-test-coverage

**Endpoint:** `POST /api/test-coverage`

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `title` | Yes | string (max 280) | Short description |
| `test_count_before` | Yes | int | Total tests before |
| `test_count_after` | Yes | int | Total tests after |
| `delta` | Yes | int | Net change (can be negative) |
| `category` | Yes | enum | `unit`, `integration`, `e2e`, `api`, `auth`, `cme`, `registry`, `langgraph`, `security`, `performance`, `other` |
| `project_name` | Yes | string | e.g., `dhg-ai-factory` |
| `tests_added` | No | string[] | New test names |
| `tests_removed` | No | string[] | Removed test names |
| `tests_modified` | No | string[] | Modified test names |
| `files_affected` | No | string[] | File paths |
| `trigger` | No | string | What prompted the change |
| `tags` | No | string[] | Semantic search tags |
| `model_name` | No | string | Model in use |

```bash
~/.claude/scripts/post-test-coverage.sh '{
  "title": "Add memreg capture dispatcher tests",
  "test_count_before": 514,
  "test_count_after": 524,
  "delta": 10,
  "tests_added": ["test_command_routes_to_correct_endpoint", "test_fire_and_forget_on_timeout"],
  "tests_removed": [],
  "tests_modified": [],
  "files_affected": ["tests/test_capture.py"],
  "category": "unit",
  "trigger": "memreg migration ship",
  "project_name": "dhg-ai-factory",
  "tags": ["memreg", "capture"],
  "model_name": "claude-opus-4-6"
}'
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REGISTRY_URL` | `http://10.0.0.251:8011` | Registry base URL (all scripts) |
