---
description: Validate alignment between Pydantic schemas, SQLAlchemy models, and FastAPI endpoints in the registry layer. Catches serializer drift before it reaches production.
---

You are running a registry validation check. Read files, compare field lists, and print a structured report. Do not narrate your process. Run the checks and print the result.

The user may have provided a domain name: $ARGUMENTS

## Scope Resolution

**If $ARGUMENTS is empty (no-args mode):**

1. Run these two commands and combine their output, deduplicating any file that appears in both:
   ```bash
   git diff --name-only HEAD 2>/dev/null
   git diff --name-only 2>/dev/null
   ```
2. Filter to files matching `registry/*.py`. Exclude files starting with `test_`.
3. If no registry files remain, print this and stop:
   ```
   [ok] No registry files in diff — nothing to validate.
   ```
4. From the remaining files, extract domain names. A domain name is the prefix before `_endpoints.py`, `_schemas.py`, or `_service.py` (e.g., `insights_endpoints.py` → domain `insights`).
5. For each domain found, run both checks below.

**If $ARGUMENTS contains a domain name (named-domain mode):**

1. Set the domain to the provided argument (e.g., `insights`, `corrections`, `cme_stats`).
2. Verify that `registry/{domain}_endpoints.py` exists. If not, print `[FAIL] No endpoint file found for domain "{domain}"` and stop.
3. Run both checks below for that domain.

---

## Check 1: Schema ↔ Model Field Alignment

For the domain being checked:

1. **Read the schema file** (`registry/{domain}_schemas.py`). If the file does not exist, print `[WARN] No schema file for domain "{domain}" — Check 1 skipped` and proceed to Check 2 only. Otherwise, find all classes ending in `Response` (e.g., `InsightResponse`, `CorrectionResponse`). For each Response class, extract the list of field names (lines matching the pattern `field_name: type` or `field_name: Optional[type]` inside the class body).

2. **Find the model class** in `registry/models.py`. Search for SQLAlchemy model classes related to this domain:
   - Grep for `class {Name}(Base):` where `Name` is the singular form of the domain (e.g., domain `insights` → class `Insight`, domain `corrections` → class `Correction`)
   - If no match, try: grep for classes whose `__tablename__` starts with the domain name
   - Read the matched class and extract column names (lines matching `column_name = Column(...)`)

3. **Compare the two field lists:**

   Fields in schema but NOT in model → `[FAIL]` (schema references a field that doesn't exist)

   Fields in model but NOT in schema → check against the known-exclusion list below:
   - If the field is in the exclusion list → `[WARN]` (intentional omission, expected)
   - If the field is NOT in the exclusion list → `[WARN]` with note: "not in known-exclusion list — verify this is intentional"

### Known-Exclusion List (v1, exhaustive as of May 2026)

These model columns are intentionally excluded from API response schemas:

- `embedding` — vector storage, not API-visible
- `embedding_model` — internal metadata
- `search_vector` — tsvector for full-text search
- `upsert_key_hash` — deduplication hash, internal

When new internal-only columns are added to models, update this list.

---

## Check 2: Endpoint ↔ Schema Wiring

For the domain being checked:

1. **Read the endpoint file** (`registry/{domain}_endpoints.py`). Find all route decorators (`@router.get`, `@router.post`, `@router.patch`, `@router.put`, `@router.delete`) that include a `response_model=X` parameter. Extract the class name `X` and the HTTP method + path.

2. **For each response_model class name `X`:**
   a. Scan the endpoint file's import block (lines before the first function definition) for `X`
   b. Confirm the import comes from a module whose name contains `_schemas` (e.g., `from insights_schemas import InsightResponse`)
   c. If found, read that schemas module and confirm `class X` exists in it

3. **Report:**
   - Class not found in any `_schemas` import → `[FAIL]` with the specific endpoint route
   - Class imported from `_schemas` but class definition not found in the schemas file → `[FAIL]`
   - Class imported and confirmed to exist → `[ok]`

---

## Output Format

Print the report in this format. Order: `[FAIL]` first, then `[WARN]`, then `[ok]`.

```
Registry Validation Report
==========================
Scope: {describe scope — "git diff (N registry files)" or "domain: insights"}

Schema ↔ Model Alignment
  {[FAIL/WARN/ok] findings, one per line}

Endpoint ↔ Schema Wiring
  {[FAIL/WARN/ok] findings, one per line}

Summary: N FAIL, N WARN | {verdict}
```

Verdict rules:
- 0 FAIL → "No action required"
- 1+ FAIL → "Fix before committing"

---

## Auto-Capture

If ANY `[FAIL]` findings were reported, make one call to capture them:

```bash
~/.claude/scripts/post-deferred-items.sh '{"title":"Registry drift: N field alignment failures in DOMAIN","description":"FAIL_LINES","reason":"Detected by /registry-validator","source_context":"/registry-validator","priority":"high","category":"registry","project_name":"dhg-ai-factory","affected_files":["FILES_CHECKED"],"tags":["serializer-drift","registry-validator"],"model_name":"claude-opus-4-6"}'
```

Replace:
- `N` with the count of FAIL findings
- `DOMAIN` with the domain(s) checked
- `FAIL_LINES` with all [FAIL] lines joined by semicolons
- `FILES_CHECKED` with the files that were read

This is fire-and-forget — if it fails, proceed without blocking.
