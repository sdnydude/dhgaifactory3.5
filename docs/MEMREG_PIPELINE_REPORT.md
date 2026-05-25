# Memreg Pipeline Report

**Generated:** 2026-05-22 (original) · **Last updated:** 2026-05-24 (post-migration)
**Project:** DHG AI Factory v3.5
**Server:** g700data1 (10.0.0.251)
**Registry API:** http://10.0.0.251:8011
**Status:** All 7 pipelines operational + read-side wired (SessionStart KB briefing + kb-search skill); D5/D6 auto-inject hook deferred

---

## 🔁 2026-05-24 Migration Update (READ THIS FIRST)

This report was originally written at the pre-migration state. The capture pipeline still works the same way, but several **sources of truth and architecture details have moved**. Read this section first; trust the post-migration paths below over older sections.

### What changed

| Aspect | Before (pre-2026-05-24) | After (post-migration) |
|---|---|---|
| **Source of truth** | 6 capture scripts symlinked from `~/DHG/portage/.claude/scripts/`, 1 standalone in `~/.claude/scripts/` | All 7 now resolve via `~/.claude/scripts/post-*.sh` → `~/DHG/dhg-memreg/scripts/` (new private repo `sdnydude/dhg-memreg`) |
| **Capture script implementation** | 7 separate ~30-line bash scripts (~90% duplicated) | 7 thin bash shims → one `memreg_capture.py` argparse module with 7 subcommands |
| **Test coverage on captures** | 0 | 12 tests in `dhg-memreg/tests/test_capture.py` |
| **Bulk ingest scripts** | `ingest-memory-files.py` portage-hardcoded; `ingest-claude-md.py` had hardcoded TARGETS + "multi-project" wrapper | Both project-aware: `--project`+`--memory-dir` flags (memory) and `--dhg-root`+`--projects`+`--batch-name` (claude-md) |
| **Docker** | None | `dhg-memreg:dev` (145 MB, `python:3.12-slim`) — single entrypoint dispatcher routes all 7 captures + 2 ingests; **LAN-only** (off-LAN access via tunnel deferred) |
| **Read side** | None — registry was write-only, Claude never consulted KB | (a) **SessionStart KB briefing hook** auto-runs at every new Claude session in DHG projects (project-aware filter, parallel 4-curl, 2s/curl timeout, graceful failure); (b) **`kb-search` skill** for explicit invocation; (c) D5/D6 PreToolUse auto-inject **deferred** (advisor caught wrong hook event — needs `SubagentStart` pivot, see registry `2e87973e-e301-4bae-b31a-957a624ce57e`) |

### Updated architecture (5 layers, was 3)

```
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 5 (NEW): READ-SIDE WIRING                                     │
│ - SessionStart hook in ~/.claude/settings.json (3rd entry) →        │
│   ~/DHG/dhg-memreg/hooks/session-start-kb-briefing.sh               │
│ - kb-search skill at ~/DHG/dhg-memreg/skills/kb-search/             │
│ - (deferred) PreToolUse forced-inject — SubagentStart pivot pending │
└──────────────────────────▲──────────────────────────────────────────┘
                           │ injected as session context
┌──────────────────────────┼──────────────────────────────────────────┐
│ Layer 4: TRIGGER RULES (unchanged)                                  │
│ .claude/rules/auto-*.md (7 files, in each project)                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Claude fires bash call
┌──────────────────────────▼──────────────────────────────────────────┐
│ Layer 3 (NEW SHAPE): CAPTURE DISPATCH                               │
│ ~/.claude/scripts/post-*.sh (7 symlinks) → ~/DHG/dhg-memreg/        │
│   scripts/post-*.sh (7 thin shims) → exec python3 memreg_capture.py │
│ All paths preserved (rules + symlinks unchanged); implementation    │
│ unified into Python module with 12 tests.                           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ httpx POST (2s/5s timeout)
┌──────────────────────────▼──────────────────────────────────────────┐
│ Layer 2: REGISTRY API ENDPOINTS (unchanged)                         │
│ http://10.0.0.251:8011/api/<table>  — 7 capture + kb/search +       │
│ stats endpoints, FastAPI + SQLAlchemy + PostgreSQL 15 + pgvector    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ tsvector + nomic-embed-text on write
┌──────────────────────────▼──────────────────────────────────────────┐
│ Layer 1: STORAGE (unchanged)                                        │
│ Postgres tables + pgvector + tsvector indexes                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Authoritative paths (post-migration)

| Asset | Pre-migration | Post-migration |
|---|---|---|
| Capture script source | `/home/swebber64/DHG/portage/.claude/scripts/post-*.sh` | **`/home/swebber64/DHG/dhg-memreg/scripts/post-*.sh`** (thin shims) + **`/home/swebber64/DHG/dhg-memreg/scripts/memreg_capture.py`** (logic) |
| `ingest-memory-files.py` | `~/.claude/scripts/ingest-memory-files.py` (portage-only) | **`~/DHG/dhg-memreg/scripts/ingest-memory-files.py`** (project-aware) |
| `ingest-claude-md.py` | `~/.claude/scripts/ingest-claude-md.py` (hardcoded TARGETS) | **`~/DHG/dhg-memreg/scripts/ingest-claude-md.py`** (project-aware) |
| Tests | None | **`~/DHG/dhg-memreg/tests/`** (22 passing) |
| Docker image | None | **`dhg-memreg:dev`** (build from `~/DHG/dhg-memreg/Dockerfile`) |
| GitHub repo | None | **https://github.com/sdnydude/dhg-memreg** (private) |
| Ship log entry | None | **`docs-site/projects/dhg-ai-factory/ship-log/001-memreg-pipeline-migration-complete.md`** |
| Recovery: symlink rollback | n/a | `bash ~/DHG/dhg-memreg/setup-symlinks.sh --rollback` |
| Recovery: settings.json hook | n/a | Restore `~/.claude/settings.json.bak.20260524-221847` from a `claude --bare` shell |

### What still applies from this report

The per-pipeline details below (7 sections covering schemas, valid categories, when each fires, record counts) are still accurate for the **write side**. The 3-layer architecture diagram in the next section is **superseded** by the 5-layer diagram above — kept for historical reference.

**For the current architecture, trust this update section + the ship-log entry. The rest of this doc is a snapshot of pre-migration state.**

---

**Status (original):** All 7 pipelines operational and verified end-to-end

---

## What Is Memreg?

Memreg ("memory + registry") is the auto-capture pipeline that records session knowledge into the DHG Registry database. Every Claude Code session generates valuable artifacts — bug diagnoses, architectural decisions, deferred work items, insights, corrections — that would otherwise vanish when the session ends. Memreg captures these automatically, in real-time, without interrupting the session.

The captured data feeds the unified KB search system (`/api/kb/search`), enabling future sessions to search across all prior session knowledge via full-text search and semantic vector search (pgvector, 768-dim nomic-embed-text embeddings).

---

## Architecture: Three Layers

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: TRIGGER RULES                                     │
│  .claude/rules/auto-*.md (7 files)                          │
│  Loaded into session context at startup.                    │
│  Tell Claude WHEN to fire each capture script.              │
│  Set project_name, category, and JSON template per project. │
└──────────────────────────┬──────────────────────────────────┘
                           │ Claude fires bash call
┌──────────────────────────▼──────────────────────────────────┐
│  Layer 2: CAPTURE SCRIPTS                                   │
│  ~/.claude/scripts/post-*.sh (7 files)                      │
│  Fire-and-forget bash scripts. Always exit 0.               │
│  POST JSON to registry API with 2s connect / 5s max timeout.│
│  6 symlinked from Portage, 1 standalone (test-coverage).    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP POST
┌──────────────────────────▼──────────────────────────────────┐
│  Layer 1: REGISTRY API ENDPOINTS                            │
│  http://10.0.0.251:8011/api/<table>                         │
│  FastAPI + SQLAlchemy + PostgreSQL 15 + pgvector             │
│  Pydantic validation, category allowlists, upsert support.  │
│  Ollama embeddings (nomic-embed-text) on ingest.            │
│  tsvector full-text search triggers on write.               │
└─────────────────────────────────────────────────────────────┘
```

**Key design principle:** The pipeline must never block or fail a session. Scripts always `exit 0`. If the registry is down, the capture is silently dropped — reliability of the coding session takes priority over data completeness.

---

## The 7 Pipelines

### 1. Bug Fixes (`/api/bug-fixes`)

**Purpose:** Root cause analyses for non-trivial bugs. Captures the symptom, root cause, fix applied, severity, and affected files.

**When it fires:** After a debugging session where a symptom was observed, root cause identified, and fix applied. Skips trivial fixes (typos, missing imports).

**Trigger rule:** `.claude/rules/auto-bug-fixes-capture.md`  
**Script:** `~/.claude/scripts/post-bug-fixes.sh`  
**Schema:** `registry/bug_fixes_schemas.py`

**Valid categories:** api, auth, cme, config, database, frontend, infra, langgraph, marketplace, observability, other, performance, registry, security, shared, testing

**Valid severities:** low, medium, high, critical

**Current records:** 8 total (2 dhg-ai-factory, 6 portage)

| ID (short) | Project | Severity | Category | Summary |
|------------|---------|----------|----------|---------|
| 372baf66 | dhg-ai-factory | high | config | Memreg capture pipeline inert — trigger rules never created |
| 0ed61908 | dhg-ai-factory | medium | config | E2E pipeline test — memreg wiring verification |
| portage-1 | portage | high | frontend | iOS WebKit aspect-ratio bug causes BeforeAfterSlider 0px height |
| portage-2 | portage | medium | frontend | BeforeAfterSlider preview added to PhotoEditor but not ScanFlow |
| portage-3 | portage | high | frontend | BeforeAfterSlider invisible on iOS WebKit |
| portage-4 | portage | high | frontend | Crop tool handles misaligned due to coordinate-space mismatch |
| portage-5 | portage | medium | testing | Billing enforcement test fails in CI due to env caching |
| portage-6 | portage | low | other | audit-test |

---

### 2. Corrections (`/api/corrections`)

**Purpose:** Self-training data. Captures moments when the user corrects Claude's behavior — wrong assumptions, fabrications, missed context, workflow violations. The `claude_action` field records what should have been done instead, enabling Loop 4 self-improvement.

**When it fires:** When the user pushes back with corrections ("no", "stop", "you're wrong"), frustrated redirects, pattern instructions, or repeated instructions. Fires once per correction event, not on every follow-up turn.

**Trigger rule:** `.claude/rules/auto-correction-capture.md`  
**Script:** `~/.claude/scripts/post-correction.sh`  
**Schema:** `registry/corrections_schemas.py`

**Valid categories:** docker-guessing, fabrication, missed-context, other, premature-action, repeated-instruction, workflow-violation, wrong-assumption

**Current records:** 10 total (2 dhg-ai-factory, 8 portage)

| ID (short) | Project | Category | User Message (excerpt) |
|------------|---------|----------|----------------------|
| bf589ec0 | dhg-ai-factory | other | E2E pipeline test |
| aa8e4b36 | dhg-ai-factory | fabrication | "you've said you've already done this twice in the past..." |
| portage-1 | portage | wrong-assumption | "this is not an mvp. i dont build mvps" |
| portage-2 | portage | workflow-violation | "it looks to me like you are trying to shortcut again" |
| portage-3 | portage | workflow-violation | "trying to shortcut to finish fast at the cost of quality" |
| portage-4 | portage | missed-context | "are you guessing or researching first?" |
| portage-5 | portage | workflow-violation | "are you building this using /ship?" |
| portage-6 | portage | missed-context | "need to fix the triggers so they are processing more often" |
| portage-7 | portage | missed-context | "you don't understand the project completely. read the codebase" |
| portage-8 | portage | other | audit-test |

---

### 3. Decision Logs (`/api/decision-logs`)

**Purpose:** Architectural and implementation decisions where an alternative was explicitly considered and rejected. Prevents future sessions from making the opposite choice without understanding why.

**When it fires:** When a decision is made where (1) an alternative was considered, (2) a future session could plausibly choose differently, (3) the reasoning is non-obvious from code alone.

**Trigger rule:** `.claude/rules/auto-decision-logs-capture.md`  
**Script:** `~/.claude/scripts/post-decision-logs.sh`

**Valid domains:** registry, frontend, langgraph, cme, infra, observability, auth, ops

**Current records:** 29 total (2 dhg-ai-factory, 27 portage)

Notable AI Factory decisions:
- **Keep capture scripts as Portage symlinks** — no project-specific logic in scripts, only trigger rules differ
- E2E pipeline test verification

Notable Portage decisions:
- Reverb uses token-paste, not OAuth
- Deep Teal over Purple for AI/assistive color
- JPEG over WebP for marketplace-bound images
- Drizzle ORM over Prisma
- Self-hosted runner over GitHub Pages for docs
- Doppler SaaS over self-hosted Infisical/Vault

---

### 4. Deferred Items (`/api/deferred-items`)

**Purpose:** Work discovered during sessions but intentionally not done. Captures the what, why-deferred, priority, and affected files. Seeds the backlog for future `/ship` runs.

**When it fires:** During `/ship` Phase 4 (unrelated issues found), during debugging (secondary issues spotted), during code review (flagged but deprioritized), or when the user says "defer that", "out of scope", etc.

**Trigger rule:** `.claude/rules/auto-deferred-items-capture.md`  
**Script:** `~/.claude/scripts/post-deferred-items.sh`  
**Schema:** `registry/deferred_items_schemas.py`

**Valid categories:** api, auth, cme, config, database, docs, frontend, infra, langgraph, marketplace, observability, other, performance, registry, security, testing

**Valid priorities:** low, medium, high, critical  
**Valid statuses:** open, in_progress, resolved, wont_fix

**Current records:** 48 total (2 dhg-ai-factory, 17 dhgaifactory3.5, 29 portage)

**Open items by priority (AI Factory + dhgaifactory3.5):**

| Priority | Count | Examples |
|----------|-------|---------|
| high | 4 | Ship advisor fix (CME stats), security_endpoints coverage, kb_endpoints coverage, inference_endpoints coverage |
| medium | 7 | insights, decision_logs, corrections, agent_sessions, doc_pages endpoint test coverage |
| low | 6 | research, memory_metrics, frontend_specs, claude, antigravity endpoint test coverage; E2E test |

---

### 5. Insights (`/api/insights`)

**Purpose:** Non-obvious technical discoveries. Architecture patterns, debugging lessons, platform-specific quirks, design wisdom that a future session would benefit from knowing.

**When it fires:** Whenever a `★ Insight` block is generated, or whenever a non-obvious technical discovery is made.

**Trigger rule:** `.claude/rules/auto-insight-capture.md`  
**Script:** `~/.claude/scripts/post-insight.sh`

**Valid categories:** testing, architecture, security, performance, patterns, debugging, database, frontend, devops, api-design, langgraph, observability, cme

**Current records:** 66 total (3 dhg-ai-factory, 63 portage)

**Top categories by count:**

| Category | Count | Sample insight |
|----------|-------|---------------|
| architecture | 15 | "Memreg pipeline has 3 layers — layer 3 (trigger rules) breaks silently" |
| testing | 14 | "Pure function tests need zero mocking — highest value, lowest cost" |
| frontend | 8 | "iOS WebKit aspect-ratio collapses to 0px in flex+overflow" |
| devops | 8 | "Next.js standalone binds to container hostname not 0.0.0.0" |
| api-design | 7 | "search_api.py user_id filter must be conditional for shared tables" |
| database | 5 | "TOCTOU race in DB: unset-then-set needs transaction + partial unique index" |
| security | 4 | "Timing oracle defense: DUMMY_HASH ensures bcrypt runs on every login path" |

---

### 6. Ship Sessions (`/api/ship-sessions`)

**Purpose:** Summary records of completed `/ship` workflow runs. Captures the feature name, approach, status, branch, commits, deferred items, review findings, and verification results.

**When it fires:** At the end of a `/ship` workflow (Phase 7 or when stopped).

**Trigger rule:** `.claude/rules/auto-ship-session-capture.md`  
**Script:** `~/.claude/scripts/post-ship-session.sh`

**Current records:** 39 total (1 dhg-ai-factory, 38 portage)

**AI Factory ship sessions:**
- **memreg pipeline wiring** (complete, 2026-05-22)

**Portage ship sessions (most recent 10):**
- eBay buyer messaging — read inbox + reply via Trading API
- scan comp cards + reverb UI + features doc + docs tunnel
- eBay Seller Hub Reports CSV export with marketplace data caching
- Reverb token-paste auth flow
- Billing enforcement gaps
- Stripe subscription billing — Pro tier, trials, credit packs
- Fix all 4 feedback loops — cron, journal aging, correction/bug-fix surfacing
- Capture-guarantee V3 — corrections + bug-fixes auto-fire
- Capture-guarantee V2 — decisions + deferred auto-fire
- Hook-driven capture — guaranteed registry ingest via session hooks

---

### 7. Test Coverage (`/api/test-coverage`)

**Purpose:** Tracks test count changes across sessions. Captures before/after counts, delta, specific tests added/removed/modified, and what triggered the change.

**When it fires:** After any work that adds, removes, or modifies test files.

**Trigger rule:** `.claude/rules/auto-test-coverage-capture.md`  
**Script:** `~/.claude/scripts/post-test-coverage.sh`  
**Schema:** `registry/test_coverage_schemas.py`

**Valid categories:** admin, api, auth, cme, e2e, integration, langgraph, marketplace, other, performance, registry, security, unit

**Current records:** 2 total

| Project | Before | After | Delta | Title |
|---------|--------|-------|-------|-------|
| dhg-ai-factory | 271 | 271 | +0 | E2E pipeline test — baseline |
| dhgaifactory3.5 | 227 | 271 | +44 | Ship B: memreg knowledge-generating tests |

---

## Registry Totals

| Table | Records | AI Factory | Portage | Other |
|-------|---------|------------|---------|-------|
| insights | 66 | 3 | 63 | 0 |
| corrections | 10 | 2 | 8 | 0 |
| bug_fixes | 8 | 2 | 6 | 0 |
| deferred_items | 48 | 2 | 29 | 17 |
| decision_logs | 29 | 2 | 27 | 0 |
| ship_sessions | 39 | 1 | 38 | 0 |
| test_coverage | 2 | 1 | 1 | 0 |
| **Total** | **202** | **13** | **172** | **17** |

---

## File Inventory

### Trigger Rules (Layer 3) — `.claude/rules/`

| File | Pipeline | Lines |
|------|----------|-------|
| auto-bug-fixes-capture.md | bug_fixes | 68 |
| auto-correction-capture.md | corrections | 43 |
| auto-decision-logs-capture.md | decision_logs | 26 |
| auto-deferred-items-capture.md | deferred_items | 57 |
| auto-insight-capture.md | insights | 14 |
| auto-ship-session-capture.md | ship_sessions | 14 |
| auto-test-coverage-capture.md | test_coverage | 68 |

### Capture Scripts (Layer 2) — `~/.claude/scripts/`

| File | Type | Target |
|------|------|--------|
| post-bug-fixes.sh | symlink | ~/DHG/portage/.claude/scripts/post-bug-fixes.sh |
| post-correction.sh | symlink | ~/DHG/portage/.claude/scripts/post-correction.sh |
| post-decision-logs.sh | symlink | ~/DHG/portage/.claude/scripts/post-decision-logs.sh |
| post-deferred-items.sh | symlink | ~/DHG/portage/.claude/scripts/post-deferred-items.sh |
| post-insight.sh | symlink | ~/DHG/portage/.claude/scripts/post-insight.sh |
| post-ship-session.sh | symlink | ~/DHG/portage/.claude/scripts/post-ship-session.sh |
| post-test-coverage.sh | standalone | (1467 bytes) |

### Registry Schemas (Layer 1) — `registry/`

| File | Categories Added (2026-05-22) |
|------|------------------------------|
| bug_fixes_schemas.py | +cme, +langgraph, +observability, +registry |
| deferred_items_schemas.py | +cme, +langgraph, +observability, +registry |
| test_coverage_schemas.py | +cme, +langgraph, +registry |
| corrections_schemas.py | +premature-action |

### Registry Endpoints (Layer 1) — `registry/`

| Endpoint | File | Response Key |
|----------|------|-------------|
| POST/GET /api/bug-fixes | bug_fixes_endpoints.py | `bug_fixes` |
| POST/GET /api/corrections | corrections_endpoints.py | `corrections` |
| POST/GET /api/decision-logs | decision_logs_endpoints.py | `decision_logs` |
| POST/GET /api/deferred-items | deferred_items_endpoints.py | `deferred_items` |
| POST/GET /api/insights | insights_endpoints.py | `insights` |
| POST/GET /api/ship-sessions | ship_sessions_endpoints.py | `ship_sessions` |
| POST/GET /api/test-coverage | test_coverage_endpoints.py | `test_coverage_events` |

**Note:** Default page limit is 20 records. Use `?limit=100` to retrieve more.

---

## How It Works In Practice

### During a session:

1. Claude encounters a trigger condition (e.g., fixes a bug with a non-trivial root cause)
2. The trigger rule in `.claude/rules/auto-bug-fixes-capture.md` fires
3. Claude constructs a JSON payload with the required fields
4. Claude makes a Bash tool call: `~/.claude/scripts/post-bug-fixes.sh '<json>'`
5. The script POSTs to `http://10.0.0.251:8011/api/bug-fixes`
6. The registry API validates the payload, generates a UUID, creates Ollama embeddings, and stores the record
7. The script returns the UUID and exits 0
8. The session continues uninterrupted

### For future sessions:

1. A session needs context about prior work
2. Queries `POST /api/kb/search` with a natural language query
3. KB search runs across 9 of the 10 memreg tables (excludes test_coverage)
4. Returns ranked results via reciprocal rank fusion (full-text + vector similarity)
5. Session uses the results to avoid repeating mistakes, build on prior decisions, and maintain continuity

---

## E2E Verification (2026-05-22)

All 7 pipelines tested with real session data. Each record verified by UUID in the registry API response.

| Pipeline | Script Return | Registry Lookup | Status |
|----------|--------------|-----------------|--------|
| bug_fixes | 372baf66 | CONFIRMED | PASS |
| corrections | aa8e4b36 | CONFIRMED | PASS |
| decision_logs | 53756516 | CONFIRMED | PASS |
| deferred_items | 9493af89 | CONFIRMED | PASS |
| insights | 9ea36a88 | CONFIRMED | PASS |
| ship_sessions | 2a8bd050 | CONFIRMED | PASS |
| test_coverage | f726bd83 | CONFIRMED | PASS |

---

## Known Gaps

1. **Scripts are symlinked from Portage** — 6 of 7 scripts live in `~/DHG/portage/.claude/scripts/`. If Portage is deleted or moved, the pipeline breaks. Decision was to keep symlinks because scripts contain no project-specific logic (project_name is set in trigger rules).

2. **No session hooks for guaranteed capture** — Portage has `SessionStop` hooks that sweep for uncaptured events. AI Factory does not yet have these. If Claude misses a trigger condition during the session, the event is lost.

3. **No cron for periodic re-ingest** — Memory files, CLAUDE.md, and other evolving documents are not automatically re-ingested into the KB. Manual `/sync-memory` is needed.

4. **Test coverage is thin** — Only 2 test_coverage records. The pipeline captures deltas but the registry test suite itself (271 tests) predates the capture pipeline.

5. **Cross-project data mixing** — Both Portage and AI Factory write to the same registry DB. The `project_name` field differentiates them, but KB search returns results from all projects unless filtered.
