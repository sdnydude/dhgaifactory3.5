---
title: Operations
sidebar_position: 7
---

# Operations

Day-to-day management, health checks, extending the pipeline, and recovery procedures.

---

## Health Verification

### Quick Check

Fire a single capture and confirm it reaches the registry:

```bash
~/.claude/scripts/post-insight.sh '{
  "tldr": "health check",
  "insight_statement": "verifying memreg end-to-end",
  "project_name": "dhg-ai-factory",
  "category": "infra",
  "tags": ["health"],
  "model_name": "manual"
}'
# Expected: "insight captured: <uuid>"
```

### Registry Reachability

```bash
curl -s -o /dev/null -w "%{http_code}\n" --max-time 3 http://10.0.0.251:8011/healthz
# Expected: 200
```

### KB Search

```bash
bash ~/DHG/dhg-memreg/skills/kb-search/search.sh "test"
# Expected: table of results (or "no KB matches" if registry is empty)
```

### Symlink Integrity

```bash
ls -la ~/.claude/scripts/post-*.sh
# All 7 should point to ~/DHG/dhg-memreg/scripts/
```

### Hook Registration

```bash
jq '.hooks.SessionStart' ~/.claude/settings.json
# Should include session-start-kb-briefing.sh entry
```

---

## Adding a New Capture Type

To add an 8th capture endpoint (e.g., `post-code-review`):

### 1. Add the Registry Endpoint

In the aifactory repo (not dhg-memreg), create the endpoint, service, and schema files. This is standard FastAPI development — see existing endpoints like `registry/insights_endpoints.py` for the pattern.

### 2. Add the Dispatcher Entry

In `dhg-memreg/scripts/memreg_capture.py`, add the new command to the `ENDPOINTS` dict:

```python
ENDPOINTS["post-code-review"] = ("/api/code-reviews", "code-review")
```

### 3. Add the Bash Shim

Create `dhg-memreg/scripts/post-code-review.sh`:

```bash
#!/usr/bin/env bash
exec python3 "$(dirname "$(readlink -f "$0")")/memreg_capture.py" post-code-review "$@"
```

```bash
chmod +x ~/DHG/dhg-memreg/scripts/post-code-review.sh
```

### 4. Add a Test

In `dhg-memreg/tests/test_capture.py`, add the new command to the parametrized test:

```python
@pytest.mark.parametrize("command,expected_path", [
    # ... existing entries ...
    ("post-code-review", "/api/code-reviews"),
])
```

### 5. Add the Trigger Rule

In each consuming project's `.claude/rules/`, create `auto-code-review-capture.md` with the trigger conditions and capture call template.

### 6. Update Symlinks

If users have already run `setup-symlinks.sh`, the new `.sh` file won't be symlinked automatically. Re-run:

```bash
bash ~/DHG/dhg-memreg/setup-symlinks.sh
```

This is idempotent — existing correct symlinks are skipped.

### 7. Rebuild Docker Image

```bash
docker build -t dhg-memreg:dev ~/DHG/dhg-memreg
```

The entrypoint dispatcher picks up new `.sh` files automatically.

---

## Rollback Procedures

### Capture Pipeline (Symlinks)

Previous symlink targets are logged in `~/.claude/scripts/.dhg-memreg-prev-targets`. To restore:

```bash
bash ~/DHG/dhg-memreg/setup-symlinks.sh --rollback
```

Preview first with `--dry-run`:

```bash
bash ~/DHG/dhg-memreg/setup-symlinks.sh --rollback --dry-run
```

### SessionStart Hook

If a fresh session breaks or hangs due to a hook issue:

```bash
# Start a bare session (bypasses all hooks)
claude --bare

# Inside the bare session, restore settings backup
cp ~/.claude/settings.json.bak.<timestamp> ~/.claude/settings.json
```

### Docker Image

```bash
docker rmi dhg-memreg:dev
```

No registry push has been configured, so there's nothing to roll back remotely.

### Repo State

All commits are on `main`. Standard git revert:

```bash
cd ~/DHG/dhg-memreg
git revert <sha>
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Capture script prints "registry unreachable" | Not on g700data1 LAN, or registry-api is down | `curl http://10.0.0.251:8011/healthz` to diagnose |
| Capture fires but no record appears in registry | Pydantic schema validation failed on the registry side | Check capture script stderr — it logs HTTP status on non-2xx. Curl the endpoint directly with the same payload to see the validation error. |
| `setup-symlinks.sh` errors "source missing" | Repo not cloned at expected path | Confirm clone is at `~/DHG/dhg-memreg/` |
| SessionStart briefing shows all "(none)" | Registry has no data for this project | Run both ingestion scripts to seed the registry, then start a new session |
| SessionStart briefing doesn't appear | Hook removed from settings.json, or hook timeout exceeded | `jq '.hooks.SessionStart' ~/.claude/settings.json` — confirm the kb-briefing entry exists |
| `kb-search` returns "no matches" but data exists | Query keywords don't hit FTS or vector matches | Try broader search terms. Test raw: `curl -s -X POST -H "Content-Type: application/json" -d '{"query":"X","project_name":"Y","limit":10}' http://10.0.0.251:8011/api/kb/search` |
| Docker capture fails with connection refused | Default bridge network can't reach LAN | Use `--network=host` |
| `ingest-memory-files.py` argparse error | Missing `--project` or `--memory-dir` | Both flags are required — no defaults |

---

## Onboarding a New Machine

```bash
# 1. Clone the repo
git clone git@github.com:sdnydude/dhg-memreg.git ~/DHG/dhg-memreg

# 2. Run symlink setup
bash ~/DHG/dhg-memreg/setup-symlinks.sh

# 3. Verify capture
~/.claude/scripts/post-insight.sh '{"tldr":"new-machine onboarding","insight_statement":"memreg installed","project_name":"dhg-ai-factory","category":"infra","tags":["onboarding"],"model_name":"manual"}'

# 4. Wire hooks in ~/.claude/settings.json
# Add entries for SessionStart, UserPromptSubmit, SubagentStart, PreToolUse
# (see the Hooks page for exact JSON)

# 5. Seed the registry with existing content
python3 ~/DHG/dhg-memreg/scripts/ingest-memory-files.py \
  --project dhg-ai-factory \
  --memory-dir ~/.claude/projects/-home-swebber64-DHG-aifactory3-5-dhgaifactory3-5/memory

python3 ~/DHG/dhg-memreg/scripts/ingest-claude-md.py \
  --dhg-root ~/DHG

# 6. Start a new Claude session and verify the KB briefing appears
```

**Prerequisite:** LAN connectivity to `10.0.0.251:8011`. Off-LAN access is not currently supported.

---

## Running Tests

```bash
cd ~/DHG/dhg-memreg
python3 -m pytest tests/ -v
```

Tests cover:
- Capture dispatcher routing (all 7 commands to correct endpoints)
- Fire-and-forget behavior (timeout, connection failure → exit 0)
- Memory file ingestion (frontmatter parsing, type routing)
- CLAUDE.md ingestion (chunking, project path resolution)
- Hook output format (JSON protocol compliance)
