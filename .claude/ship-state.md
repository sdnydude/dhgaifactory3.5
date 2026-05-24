status: in_progress
phase: 4
feature: Close the Loop V1 — feedback loop enforcement, dashboard, deferred item intelligence
approach: Hook-based enforcement (SessionStart + PreToolUse) + stats endpoints + dashboard panel + AI-driven deferred item triage
complexity: complex
explore_scope: targeted
kb_findings: Portage Loop 4 (ship-log 018) built corrections capture + briefing surface. Deferred from that: Grafana dashboard, auto-generated feedback from >3 occurrences, cross-project detection. KB insight: "AI behavioral rules are suggestions competing for attention — move enforcement to deterministic hooks."
codegraph_scan: corrections stack (corrections_schemas/service/endpoints.py), deferred_items stack (same pattern), DashboardsPage (frontend/src/app/dashboards/page.tsx, 1133 lines), cme_stats pattern (service + endpoints), SessionStart hook in settings.json

## Phase 3 Plan (12 tasks, approved)

### Assumption Audit Corrections Applied
- Task 5: PreToolUse hook reads stdin JSON via `jq -r`, NOT env vars ($CLAUDE_TOOL_NAME is fabricated)
- Task 5: tool_input may be empty for some tools — add graceful fallback (default to no-op)
- Task 10: Embedding backfill via direct Ollama curl (`nomic-embed-text`), not API re-POST
- Task 10: Clean 2 junk insight records (__test__, _perf) during data fix

### Build Order
1. Backend endpoints (Tasks 1-3) — no dependencies
2. Hooks (Tasks 4-5) — depend on endpoints from Tasks 1-3
3. Test coverage fix (Task 6) — independent
4. Dashboard decomposition (Task 7) — independent, unblocks Tasks 8-9
5. Dashboard panels (Tasks 8-9) — depend on Tasks 1-3 (endpoints) + Task 7 (decomposed page)
6. Data fixes (Task 10) — independent
7. /ship Phase 0 (Task 11) — depends on Task 1 (corrections stats)
8. Auto-resolution hook (Task 12) — depends on Task 2 (deferred items PATCH)

---

# Spec: Close the Loop V1

## What it does

Closes the feedback loop on the memreg capture pipeline. Currently write-only (262 events captured, nothing reads them back). This ship makes the data flow back into Claude's behavior and Stephen's visibility.

## What it doesn't do

- Does NOT build full behavioral enforcement (blocking tool calls based on corrections) — that's V2
- Does NOT build cross-project pattern detection
- Does NOT build a scoring algorithm for correction severity

## 4 Items

### Item 1: Session-Start Briefing + PreToolUse Enforcement

**SessionStart hook** (`~/.claude/scripts/session-briefing.sh`):
- Curls `GET /api/corrections/stats` (new endpoint, item 3)
- Outputs one structural line: top correction category + count + most recent example
- Format: `⚠ ACTIVE PATTERN: fabrication (3x in 7d) — last: "recommended moondream2 without research"`
- Also outputs open deferred item count and top-priority item

**PreToolUse hook** (`~/.claude/scripts/check-corrections.sh`):
- Fires on `Write|Edit` matcher
- When target file matches spec/plan/architecture patterns (*.md in docs/superpowers/, .claude/ship-state.md)
- Curls corrections stats
- If top category count > 2, injects `additionalContext` with the specific pattern warning
- Does NOT block — injects context only (V1)

**Phase 0 for /ship**: Update /ship_v2 skill to query feedback loop data before Phase 1:
- Recent corrections (7 days)
- Repeat patterns (category count > 2)
- Related deferred items (by category/tag match to feature description)
- Related decision logs

### Item 2: Feedback Loop Dashboard Panel

New section on existing `frontend/src/app/dashboards/page.tsx`:
- **Corrections panel**: Category distribution bar, repeat pattern flags, trend (7d rolling)
- **Deferred items panel**: Open count by priority, category breakdown, age distribution
- **Capture health**: Event counts across all 7 types (corrections, bug_fixes, insights, decision_logs, deferred_items, test_coverage, ship_sessions) — shows the pipeline is alive
- Polls a new unified stats endpoint

### Item 3: Stats + Aggregation Endpoints

**`GET /api/corrections/stats`** — returns:
- Category counts (last 7 / 30 / all time)
- Repeat flags (category count > 2 in rolling 7d = active repeat)
- Most recent correction per category
- Trend direction per category (increasing/decreasing/stable)

**`GET /api/deferred-items/stats`** — returns:
- Open/resolved/wont_fix counts
- Priority distribution
- Category distribution
- Age histogram (0-7d, 7-14d, 14-30d, 30+d)
- Stale candidates (open > 14d, no related git activity)

**`GET /api/feedback-loop/health`** — unified endpoint returns:
- Event counts per type (last 7d)
- Last capture timestamp per type
- Pipeline status (healthy if all types captured in last 7d, degraded if any type has 0)

### Item 4: Deferred Item Intelligence

**Backend:**
- `PATCH /api/deferred-items/{id}` — status lifecycle (open → in_progress → resolved → wont_fix), resolution reason
- `POST /api/deferred-items/triage` — AI triage endpoint: accepts the full open item list, returns clustered intelligence report (duplicate groups, pattern detection, staleness flags, priority recommendations)
- Fix project_name: migrate 17 `dhgaifactory3.5` records to `dhg-ai-factory`
- Add embeddings to deferred items (currently 0/51 have embeddings)

**Scheduled triage (weekly):**
- CronCreate or scheduled agent runs weekly
- Claude reviews all open deferred items
- Groups duplicates (semantic similarity via embeddings + title fuzzy match)
- Flags stale items (open > 14d, no commits touching affected_files)
- Auto-closes items stale for 21+ days as wont_fix with reason "auto-stale"
- Generates intelligence report
- Sends Stephen notification with report summary

**Frontend (not a to-do list):**
- AI-generated intelligence report view — clusters, patterns, recommendations
- Visual groupings by category with priority heat indicators
- One-click actions: resolve, merge duplicates, escalate to /ship
- Report history (previous triage reports viewable)

**Auto-resolution candidates:**
- PostToolUse hook on Bash (matching git commit) checks diff against open deferred items' affected_files
- Overlapping items flagged as "candidate for resolution" in next triage report
- Not auto-resolved — Claude reviews candidates during triage cycle

## Data fix
- Standardize project_name to `dhg-ai-factory` across all capture rules
- Migrate 17 records with `dhgaifactory3.5` to `dhg-ai-factory`

## Acceptance criteria

1. New session starts with a one-line correction briefing showing top pattern
2. Writing a spec file triggers PreToolUse context injection when active correction patterns exist
3. /ship loads Phase 0 feedback briefing before Phase 1
4. Dashboard panel shows correction trends, deferred item status, capture pipeline health
5. `GET /api/corrections/stats` returns category counts with repeat flags
6. `GET /api/deferred-items/stats` returns priority/category/age distributions
7. `GET /api/feedback-loop/health` returns pipeline-wide event counts
8. `PATCH /api/deferred-items/{id}` updates status with resolution reason
9. Weekly triage report generates, clusters duplicates, flags stale items
10. Stephen receives notification with triage report
11. Frontend shows AI intelligence report (not a flat to-do list)
12. Auto-resolution candidates flagged when commits touch affected_files
13. All deferred items have embeddings
14. project_name standardized to `dhg-ai-factory`

## Edge cases
- Registry API down at session start — hook exits 0, session proceeds without briefing
- PreToolUse hook timeout — must complete in <2s or session drags
- Zero corrections in 7 days — briefing says "no active patterns" (one line, not silence)
- Deferred items with no affected_files — can't do auto-resolution check, skip
- Triage report with 0 open items — report says "backlog clear", still sends notification
