# dhg-memreg-agent — Autonomous Pipeline Daemon

**Date:** 2026-05-28
**Status:** Design approved, pending implementation plan
**Repo:** `~/DHG/dhg-memreg` (github.com/sdnydude/dhg-memreg)
**Runtime:** Python daemon, main process of dhg-memreg Docker container

---

## Problem Statement

The dhg-memreg pipeline has three operational modes today, all with reliability gaps:

| Mode | How it runs | Gap |
|------|------------|-----|
| Write-side captures (7 scripts) | Behavioral rules instruct Claude to fire them mid-session | Claude forgets. Backstop only runs on Stop. Failed POSTs are silently lost. |
| Read-side hooks (13 wired) | settings.json hooks fire on session events | Live registry queries under 8s timeout. Stale data if ingestion hasn't run. |
| Ingestion (2 scripts) | Manual — human runs them by hand | Never automated. KB goes stale between manual runs. |

Additionally:
- Three memory systems (Claude Code, Serena, Registry KB) don't sync.
- Injected context enters at system-reminder tier — Claude treats it as ambient and often ignores it.
- No metrics or health visibility for the pipeline.

## Solution

A Python polling daemon that watches Claude Code session transcript token growth and runs a 9-step sweep when activity crosses a configurable token threshold. The daemon runs as the main process in the existing `dhg-memreg` Docker container.

---

## Trigger Model

```
~/.claude/projects/<slug>/<session>.jsonl
     ↓ poll every 30s
daemon reads new JSONL lines since last poll
     ↓ extract text from human/assistant messages
     ↓ tokenize via tiktoken (cl100k_base encoding)
     ↓ accumulate per-session token count
     ↓ when cumulative ≥ 100K tokens since last sweep
SWEEP fires (steps 1-9), per-session counter resets
```

- No file watchers (proven unreliable — CodeGraph watcher bug).
- Pure polling + token-based threshold.
- Threshold configurable via `SWEEP_THRESHOLD_TOKENS` env var (default: 100000).
- Tokenizer: tiktoken `cl100k_base` — closest local approximation to Claude's tokenizer. Documented choice; do not change without re-tuning the threshold.
- Incremental counting: poller stores last-parsed byte offset (always at a newline boundary) and only tokenizes new bytes since last check. Avoids re-parsing the full transcript every 30s.
- Per-session baselines persisted to `~/.claude/run/memreg-sweep-state.json` via atomic temp-file + `os.replace()` (crash-safe).
- On restart, daemon honors existing offsets rather than re-baselining — prevents crash-loops from resetting threshold progress.
- On first run with no state file, current sizes become baseline (no-fire first pass).

### Compaction handling

Claude Code can compact transcripts mid-session (the file shrinks). If the daemon detects a file is smaller than the last-known size, it resets that session's baseline to the current size and dedup state. Compacted sessions are treated as "start fresh" for capture counting.

---

## Sweep Pipeline

Runs in order on each threshold crossing. Each step has an explicit timeout.

### Step 1: Capture-guarantee sweep (timeout: 30s)

Same logic as the existing `capture-guarantee.py`: scan the JSONL transcript for insight blocks, correction signals, bug-fix commits, etc. Compare against POST script calls in the same transcript. Fire captures for any gaps. Dedup tracked per session via state files in `~/.claude/run/guarantee-posted-<session>`.

**Change from current:** Runs mid-session at the token threshold instead of only on Stop. The Stop hook is removed; the daemon subsumes it.

### Step 2: Dead-letter queue retry (timeout: 30s)

New. When any capture POST fails (registry down, HTTP 422, timeout), the payload is appended to `~/.claude/run/memreg-dlq.jsonl` — one JSON line per failed payload:

```json
{"endpoint": "/api/insights", "payload": {...}, "timestamp": "2026-05-28T12:00:00Z", "attempts": 1}
```

Each sweep, the daemon reads the DLQ and retries all entries. Successful retries are removed. Entries are dropped when:
- Age exceeds `DLQ_MAX_AGE_DAYS` (default: 7)
- Queue depth exceeds `DLQ_MAX_ENTRIES` (default: 1000)

Dropped entries log a warning metric.

### Step 3: Ingest memory files (timeout: 60s)

Tracks mtimes of all `*.md` files in `~/.claude/projects/*/memory/`. On each sweep, any file newer than last sweep gets re-ingested. Uses the existing `ingest-memory-files.py` logic extracted into a Python function (not shelled out). Project name derived from the directory slug.

Mtime state persisted to `~/.claude/run/memreg-mtime-state.json`. On first run with no state file, records current mtimes as baseline without firing ingestion (prevents mass re-ingest on fresh daemon start).

The existing `ingest-memory-files.py` script remains for manual use. The daemon imports its core logic as a Python module — no duplication.

**Prerequisite:** Verify that the registry's ingestion endpoint is idempotent on duplicate content. If not, add content-hash dedup at the daemon layer.

### Step 4: Ingest CLAUDE.md files (timeout: 60s)

Same approach as Step 3 — tracks mtimes of `~/DHG/*/CLAUDE.md` files across all DHG projects. Re-ingests on change via existing `ingest-claude-md.py` logic.

### Step 5: CodeGraph sync (timeout: 30s)

For each project directory that contains `.codegraph/`, run `codegraph sync`.

**Note:** The existing PostToolUse hook for codegraph sync is **kept** — it's cheap (30ms, async), always-on, and doesn't depend on the daemon. The daemon provides an additional batch sync that catches non-Claude edits (IDE saves, git operations). Belt and suspenders.

### Step 6: Materialize read-side views (timeout: 30s)

Queries the registry and writes pre-computed content to local files:

**KB briefing** → `~/.claude/run/kb-briefing-<project>.json`
```json
{
  "recent_ships": [...],
  "open_deferred_high": [...],
  "relevant_prior_work": [...],
  "generated_at": "2026-05-28T12:00:00Z"
}
```

**Correction patterns** → `~/.claude/run/correction-patterns-<project>.json`
```json
{
  "patterns": [
    {"category": "fabrication", "count_7d": 5, "last": "you already have this on another port..."}
  ],
  "generated_at": "2026-05-28T12:00:00Z"
}
```

SessionStart and UserPromptSubmit hooks read these files instead of querying the registry live. Result: instant delivery, never times out, never fails on registry latency.

### Step 7: Write Serena digests (timeout: 15s)

Writes 3 files per project to `.serena/memories/daemon/`:

| File | Content | Max size |
|------|---------|----------|
| `daemon/kb_digest` | Rolling 30-day summary: recent decisions, key insights, recurring bug patterns | ~2KB |
| `daemon/open_items` | Open deferred items by category and priority | ~2KB |
| `daemon/correction_patterns` | Active correction patterns with counts and examples | ~1KB |

Daemon-owned namespace — Claude and other agents don't write to `daemon/*` files. Any MCP-compatible tool connecting via Serena sees these alongside the agent-authored memories.

**Implementation order:** This is the lowest-priority materialization step. Implement after Steps 6 and 8 are working.

### Step 8: Write rules-tier briefing (timeout: 10s)

Writes `<project-root>/.claude/rules/daemon-live-briefing.md` for each active project. This file is **gitignored** and auto-loads at the project-instructions tier — same priority as CLAUDE.md, higher attention than system-reminders.

Content:
```markdown
# Active Correction Patterns (auto-generated by memreg daemon)

- **fabrication** (5x in 7 days) — verify before asserting facts
- **missed-context** (2x in 7 days) — read files before speaking about them

# Key Recent Decisions

- Pyright 144 errors: do not fix — suppress or ignore
- Standardize project_name to dhg-ai-factory

# Open High-Priority Deferred Items

- No test coverage: security_endpoints.py, kb_endpoints.py
```

**Project-scoped:** Written to each project's own `.claude/rules/` directory, not the global `~/.claude/rules/`. Prevents cross-project bleed (e.g., aifactory correction patterns appearing in portage sessions).

**Gitignore entry required:** Add `daemon-live-briefing.md` to each project's `.gitignore`.

### Step 9: Update Prometheus metrics (timeout: 5s)

Update in-memory Prometheus counters/gauges. Exposed via the daemon's `/metrics` HTTP endpoint.

```
memreg_sweep_duration_seconds        — histogram
memreg_sweep_total                   — counter
memreg_captures_total{type,status}   — counter (type=insight|bug_fix|..., status=success|failed|retried)
memreg_dlq_depth                     — gauge
memreg_dlq_dropped_total             — counter
memreg_ingestion_files_total{source} — counter (source=memory|claude_md)
memreg_codegraph_sync_duration       — histogram
memreg_active_sessions               — gauge
memreg_sweep_threshold_bytes         — gauge (current config)
memreg_materialization_age_seconds   — gauge (time since last successful materialization)
```

---

## Behavioral Enforcement (v2 — deferred)

PreToolUse blocking hook (`enforce-attention.sh`) is deferred to v2. The advisor review identified critical risks:
- Subagent transcripts are separate files — parent Edit after subagent Read triggers false positive
- Files read via `Bash(cat ...)` leave no `Read` tool call — false positive
- Concurrent read/write on live transcript during PreToolUse window causes parse errors
- Missing rules config (daemon down) — fail-open vs. fail-closed not resolvable safely

The v1 daemon provides the behavioral scoring and materialized briefings (Steps 6, 8) that raise attention without mechanical blocking. v2 can add blocking once mid-session transcript access patterns are better understood.

---

## Container Deployment

Added to `docker-compose.override.yml` in the aifactory project:

```yaml
dhg-memreg-agent:
  build: /home/swebber64/DHG/dhg-memreg
  container_name: dhg-memreg-agent
  network_mode: host
  volumes:
    - /home/swebber64/.claude:/home/swebber64/.claude
    - /home/swebber64/DHG:/home/swebber64/DHG
  restart: unless-stopped
  user: "1000:1000"  # match host swebber64 UID — files in volumes are owned by host user
  environment:
    - REGISTRY_URL=http://10.0.0.251:8011
    - SWEEP_THRESHOLD_TOKENS=100000
    - DLQ_MAX_AGE_DAYS=7
    - DLQ_MAX_ENTRIES=1000
```

- `network_mode: host` — LAN access to registry at 10.0.0.251:8011.
- Writable volume mounts for `~/.claude` (DLQ, sweep state, materialized files) and `~/DHG` (Serena digests, rules-tier briefings, CodeGraph sync).
- Health endpoint at `/health` — returns 200 with last sweep timestamp. Docker healthcheck: `curl -f http://localhost:<port>/health`.
- Prometheus metrics at `/metrics` on the same HTTP server.

**Port:** Must check availability before assigning. Candidate: 8018 (not in current port map).

### Dockerfile changes

The existing Dockerfile needs:
- `codegraph` binary installed (for Step 5 sync)
- Health/metrics HTTP server (stdlib `http.server` or lightweight framework)
- New entrypoint: `python3 daemon.py` instead of the current entrypoint dispatcher

The existing entrypoint dispatcher for capture scripts (`post-*.sh`) stays available for manual/hook invocation. The daemon is an additional entry point.

---

## What Stays in Hooks

These hooks remain in `~/.claude/settings.json` because they must fire **synchronously within a Claude Code session**:

| Hook | Event | Change |
|------|-------|--------|
| `session-briefing.sh` | SessionStart | Unchanged — loads .remember files |
| `memory-sync.sh` | SessionStart | Unchanged — git pull claude-memory |
| `session-start-kb-briefing.sh` | SessionStart | **Modified** — reads pre-computed `~/.claude/run/kb-briefing-<project>.json` instead of querying registry live |
| `journal-age.sh` | SessionStart | Unchanged |
| `reset-sweep-counter.sh` | SessionStart | Unchanged |
| `user-prompt-kb-inject.sh` | UserPromptSubmit | **Modified** — reads pre-computed `~/.claude/run/correction-patterns-<project>.json` instead of querying live |
| `subagent-start-kb-inject.sh` | SubagentStart | Reads pre-computed file |
| `pre-tool-kb-search-inject.sh` | PreToolUse | Reads pre-computed file |
| `commit-log.sh` | PostToolUse | Unchanged |
| `capture-sweep-reminder.sh` | PostToolUse | Unchanged |
| `check-deferred-resolution.sh` | PostToolUse | Unchanged |
| `check-corrections.sh` | PreToolUse | Unchanged |
| codegraph sync | SessionStart + PostToolUse | **Kept** — daemon adds batch sync, doesn't replace |

### What the daemon replaces

| Current | Replaced by |
|---------|-------------|
| `capture-guarantee.py` as Stop hook | Daemon Step 1 (runs mid-session at token threshold) |
| `session-capture.sh` as Stop hook | Daemon Step 1 (subsumes session-end sweep) |
| Manual `ingest-memory-files.py` | Daemon Step 3 (automatic on file change) |
| Manual `ingest-claude-md.py` | Daemon Step 4 (automatic on file change) |
| Live registry queries in hooks | Daemon-materialized local files (Steps 6, 8) |

---

## Operational Concerns

### Daemon crash/restart
- `restart: unless-stopped` handles crashes automatically.
- Sweep state persisted to `~/.claude/run/memreg-sweep-state.json` — restarts resume from last known baselines.
- DLQ persisted to `~/.claude/run/memreg-dlq.jsonl` — survives restarts.
- Mtime state persisted to `~/.claude/run/memreg-mtime-state.json` — prevents mass re-ingest.

### Sweep stalls
- Each step has an explicit timeout (listed above).
- If total sweep exceeds 180s, it's abandoned with a warning metric and the daemon resumes polling.
- Sweeps don't stack — if the previous sweep is still running when the next threshold is crossed, the threshold crossing is recorded but the sweep is deferred until the current one completes.

### Registry downtime
- Captures go to the DLQ and are retried on subsequent sweeps.
- Materialization (Steps 6-8) uses cached data from the last successful query. Staleness tracked via `memreg_materialization_age_seconds` metric.
- Ingestion (Steps 3-4) queues changed files and retries next sweep.

### First-time startup
- No state files → record current baselines, no-fire first pass.
- Ingestion deferred until second sweep to avoid mass re-ingest.
- DLQ starts empty.

---

## Configuration

All configurable via environment variables:

| Var | Default | Purpose |
|-----|---------|---------|
| `REGISTRY_URL` | `http://10.0.0.251:8011` | Registry API base URL |
| `SWEEP_THRESHOLD_TOKENS` | `100000` | Token growth threshold to trigger sweep (tiktoken cl100k_base) |
| `SWEEP_INTERVAL_SECONDS` | `30` | How often to poll transcript sizes |
| `SWEEP_TIMEOUT_SECONDS` | `180` | Max total sweep duration before abandoning |
| `DLQ_MAX_AGE_DAYS` | `7` | Drop DLQ entries older than this |
| `DLQ_MAX_ENTRIES` | `1000` | Max DLQ size |
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects` | Where to find session transcripts |
| `DHG_ROOT` | `~/DHG` | Root of DHG project directories |
| `METRICS_PORT` | `8018` | Port for /health and /metrics endpoints |

---

## Open Questions

1. **Registry ingestion idempotency:** Is the existing `/api/doc-pages` endpoint idempotent on duplicate content? If not, the daemon needs content-hash dedup. Must verify before building Step 3.
2. **Port 8018 availability:** Must confirm not in use before assigning to the daemon's metrics endpoint.
3. **codegraph binary in Docker:** The `codegraph` CLI may not be available inside the container. Need to check if it's a standalone binary that can be copied in, or if it requires a full installation. If unavailable, Step 5 shells out to the host via `docker exec` or is skipped in the container and only runs via the existing hooks.

---

## Success Criteria

1. **Write-side:** Zero permanently lost captures — every capture either succeeds or lands in the DLQ and is retried.
2. **Read-side:** SessionStart hook delivers briefing in <100ms (local file read) instead of 2-8s (live registry query).
3. **Ingestion:** Memory files and CLAUDE.md changes are ingested within one sweep cycle (~30s + threshold) of being written.
4. **Observability:** Pipeline health visible in Grafana — sweep duration, capture success rate, DLQ depth.
5. **Serena:** Any MCP-compatible tool connecting via Serena sees DHG institutional knowledge in `daemon/*` memories.
6. **Attention:** Active correction patterns injected at project-instructions tier via `daemon-live-briefing.md`, measured by compliance scoring in metrics.
