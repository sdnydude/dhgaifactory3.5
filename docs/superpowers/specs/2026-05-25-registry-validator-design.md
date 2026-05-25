# Registry Validator — Design Spec

**Date:** 2026-05-25
**Status:** Approved
**Author:** Claude (Opus 4.6) with Stephen Webber

## Problem

The DHG AI Factory registry layer has 34 endpoint files, 40 service files, and 19 schema files. The three-layer pattern (Pydantic schemas, SQLAlchemy models, FastAPI endpoints) creates drift risk — a field added to a model but not to the response schema, or a response_model referencing a schema that doesn't match the return value. This "serializer drift" pattern has caused production bugs and is documented in `feedback_serializer_drift.md`.

There is no automated check for cross-layer alignment. Bugs surface at runtime when an endpoint returns data that doesn't match its declared schema.

## Solution

A `/registry-validator` slash command that reads recently changed registry files, validates alignment across layers, and reports findings in `/status`-style output. Runs directly in the main session (not as a subagent). Uses grep/Read for structured text matching (not CodeGraph — this is field-name comparison, not call-flow tracing).

## Scope

### In scope (v1)

**Check 1 — Schema <-> Model field alignment:**
- For each `*Response` Pydantic schema class in the diff, extract field names
- Find the corresponding SQLAlchemy model class in `models.py`, extract column names
- Report fields in schema but not in model as `[FAIL]`
- Report fields in model but not in schema as `[WARN]` (some exclusions are intentional: `embedding`, `embedding_model`, `search_vector`, `upsert_key_hash`)
- Known-exclusion list is defined in the command file, not hardcoded in logic. The v1 list is exhaustive as of May 2026. When new internal-only columns are added to models, the exclusion list must be manually updated in the command file — this is a known maintenance requirement.

**Check 2 — Endpoint <-> Schema wiring:**
- For each endpoint function with a `response_model=X` parameter:
  1. Scan the endpoint file's import block for the class name `X`
  2. Confirm the import comes from a module whose name contains `_schemas` (e.g., `from insights_schemas import InsightResponse`)
  3. Read that schemas module and confirm `class X` exists
- Report `[FAIL]` if: class name not found in any `_schemas` import, or the class does not exist in the imported module

### Out of scope (v1)

- **Test coverage check** — dropped per advisor review. 16 of 25 endpoint files have no test file; reporting this as errors on every run produces noise, not signal. Ship separately with a baseline manifest.
- **Full-registry scan** — diff-scoped only at launch. Full scan would exhaust context reading 1250+ lines of models.py plus 34 endpoint files.
- **Type-level validation** — v1 checks field name presence, not type compatibility (e.g., `String` vs `str`). Type mapping is consistent in this codebase per feasibility review.
- **Service layer validation** — service files are pass-through; schema and model alignment catches the bugs.

## Invocation

```
/registry-validator              # validates registry/*.py files in git diff
/registry-validator insights     # validates insights domain (all layers)
```

**No-args mode (default):** Runs `git diff --name-only HEAD` plus `git diff --name-only` (unstaged), deduplicates (a file appearing in both is processed once), then filters to `registry/*.py`. If no registry files changed, prints `[ok] No registry files in diff — nothing to validate.` and exits.

**Named-domain mode:** Accepts a domain name (e.g., `insights`, `corrections`, `cme`). Reads `{domain}_endpoints.py`, `{domain}_schemas.py`, `{domain}_service.py`. To find model classes: grep `models.py` for all classes whose `__tablename__` starts with the domain name or whose class name contains it (case-insensitive). Each matching model class is a separate alignment target. Limited to one domain per invocation to stay within context budget.

## Output Format

Matches `/status` command conventions — `[FAIL]` before `[WARN]` before `[ok]`, table format.

```
Registry Validation Report (2026-05-25 14:32 ET)
=================================================
Scope: git diff (3 registry files changed)

Schema ↔ Model Alignment
  [ok]   InsightResponse: 14/14 fields match Insight model
  [WARN] Model-only fields (intentional): embedding, embedding_model, search_vector

Endpoint ↔ Schema Wiring
  [ok]   POST /api/insights → InsightResponse (imported, exists)
  [ok]   GET  /api/insights → InsightList (imported, exists)

Summary: 0 FAIL, 1 WARN | No action required
```

Error example:
```
Schema ↔ Model Alignment
  [FAIL] CorrectionResponse.claude_action — field in schema, not in model
  [FAIL] Correction.embedding — field in model, not in schema (not in known-exclusion list)

Summary: 2 FAIL, 0 WARN | Fix before committing
```

## Auto-capture

When any `[FAIL]` finding is reported, the command makes **one** `post-deferred-items.sh` call per run that aggregates all findings:
- `title`: "Registry drift: {N} field alignment failures in {domain(s)}"
- `description`: all `[FAIL]` lines concatenated
- `category`: "registry"
- `priority`: "high"
- `source_context`: "/registry-validator"
- `affected_files`: the files checked

This is fire-and-forget — capture failure does not block the report.

## Implementation

Single file: `.claude/commands/registry-validator.md`

The command file contains:
1. Frontmatter (description only, matching `/status` pattern)
2. Argument handling ($ARGUMENTS)
3. Step-by-step instructions for the two checks
4. Known-exclusion list for model-only fields
5. Output format template
6. Auto-capture instruction

No Python scripts, no Docker changes, no database migrations. The command is a markdown prompt that instructs Claude to read files and compare field lists.

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `.claude/commands/registry-validator.md` | Create | Slash command definition |

## Acceptance Criteria

1. `/registry-validator` with no registry files in diff prints `[ok]` and exits
2. `/registry-validator insights` reads insights_schemas.py, models.py (Insight class), insights_endpoints.py and produces a correct alignment report
3. A deliberately introduced drift (field in schema not in model) is reported as `[FAIL]`
4. Known-exclusion fields (embedding, search_vector, etc.) are reported as `[WARN]`, not `[FAIL]`
5. `[FAIL]` findings trigger `post-deferred-items.sh` call
6. Output follows `[FAIL]` > `[WARN]` > `[ok]` ordering

## Decisions

| Decision | Choice | Rejected | Rationale |
|----------|--------|----------|-----------|
| Mechanism | Slash command (.claude/commands/) | Skill, subagent | Matches /status diagnostic pattern; commands are user-invocable from slash menu |
| Execution | Main session | Spawned agent | Diagnostic commands run in-session per project convention; subagents are for /ship workflow phases |
| Exploration tool | grep/Read | CodeGraph | Structured text matching doesn't need semantic graph; avoids index staleness risk |
| Scope | Diff-scoped default | Full registry scan | Full scan exhausts context (1250-line models.py + 34 endpoint files) |
| Test coverage check | Deferred to v2 | Include in v1 | 16/25 endpoint files lack tests — produces 16 false positives on every run |
