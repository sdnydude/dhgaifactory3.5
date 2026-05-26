---
sidebar_position: 2
title: Capture Scripts
---

# Capture Scripts

Seven shell scripts in `~/.claude/scripts/` handle fire-and-forget event capture. Each accepts a JSON payload as the first argument and POSTs it to the Registry API.

## Script Inventory

| Script | Registry Endpoint | Trigger Rule |
|--------|-------------------|--------------|
| `post-insight.sh` | `POST /api/insights` | `auto-insight-capture.md` |
| `post-decision-logs.sh` | `POST /api/decision-logs` | `auto-decision-logs-capture.md` |
| `post-correction.sh` | `POST /api/corrections` | `auto-correction-capture.md` |
| `post-bug-fixes.sh` | `POST /api/bug-fixes` | `auto-bug-fixes-capture.md` |
| `post-ship-session.sh` | `POST /api/ship-sessions` | `auto-ship-session-capture.md` |
| `post-deferred-items.sh` | `POST /api/deferred-items` | `auto-deferred-items-capture.md` |
| `post-test-coverage.sh` | `POST /api/test-coverage-changes` | `auto-test-coverage-capture.md` |

## Common Pattern

All scripts follow the same structure:

```bash
#!/usr/bin/env bash
# Fire-and-forget: always exit 0 so we never block the session
curl -sf -X POST http://10.0.0.251:8011/api/<endpoint> \
  -H "Content-Type: application/json" \
  -d "$1" \
  > /dev/null 2>&1 || true
exit 0
```

Key design decisions:
- **Always exit 0** — capture must never block or fail a Claude session
- **LAN IP `10.0.0.251`** — never localhost (matches server network config)
- **Silent** (`> /dev/null 2>&1`) — no output to pollute session context
- **`-sf` flags** — silent + fail quietly on HTTP errors

## Trigger Rules

Each script has a corresponding `.claude/rules/auto-*.md` file that tells Claude when to fire the script. Rules are loaded into every session and define:

1. **When to trigger** — specific conditions that must all be true
2. **When NOT to trigger** — exclusions to prevent noise
3. **What to capture** — required and optional fields with examples
4. **How to call** — exact bash command with JSON template

### Example: Insight Capture

The simplest pipeline. Fires whenever Claude generates a `★ Insight` block:

```bash
~/.claude/scripts/post-insight.sh '{"tldr":"JWT refresh tokens need 5min buffer before expiry","insight_statement":"The token manager checks expiry with a 5-minute buffer...","project_name":"portage","category":"security","source_file":"apps/api/src/marketplace/token-manager.ts","tags":["jwt","auth","token-refresh"],"model_name":"claude-opus-4-6"}'
```

### Example: Bug Fix Capture

Fires after completing a non-trivial debugging session:

```bash
~/.claude/scripts/post-bug-fixes.sh '{"tldr":"iOS WebKit aspect-ratio collapses to 0px in flex containers","symptom":"BeforeAfterSlider invisible on iOS Safari","root_cause":"WebKit bug: aspect-ratio on element inside flex+overflow-hidden collapses to 0px","fix_applied":"Replaced aspect-square with paddingBottom percentage trick","files_affected":["apps/web/src/components/image/before-after-slider.tsx"],"severity":"medium","category":"frontend","project_name":"portage","tags":["ios","webkit","aspect-ratio","css"],"model_name":"claude-opus-4-6"}'
```

## Additional Scripts

| Script | Purpose |
|--------|---------|
| `generate-ship-log.sh` | Generates Docusaurus ship-log markdown from ship-state.md |
| `ingest-claude-md.py` | Ingests CLAUDE.md files into registry doc_pages |
| `ingest-memory-files.py` | Ingests memory files into registry |
| `cleanup-semantic-dupes.py` | Deduplicates semantically similar registry entries |
