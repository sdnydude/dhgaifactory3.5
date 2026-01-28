---
trigger: always_on
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `honesty.md`

# Pre-Edit Verification (MANDATORY)

## Before Editing Any Code File

Before making any code edit (using SSH or any method), verify:

1. **View the file first** — Never edit blind. Read the relevant section.
2. **Understand imports/dependencies** — Know what the file depends on.
3. **Check for existing tests** — Are there tests that need updating?
4. **State the change** — Explicitly state what you're changing and why.

## Edit Announcement Format

Before each edit, state:

```
Editing: <file path>
Purpose: <what I'm changing>
Impact: <what else might be affected>
Tests: <will update / no tests exist / tests not affected>
```

## Exception

Quick fixes (typos, obvious one-liners) can skip the full announcement but still require viewing the file first.

## Why This Rule Exists

- Prevents blind edits that break dependencies
- Ensures changes are intentional and understood
- Creates audit trail of reasoning
- Catches side effects before they happen
