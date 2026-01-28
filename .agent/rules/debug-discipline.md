---
trigger: always_on
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `honesty.md`

# Debug Discipline (MANDATORY)

## When Encountering Any Error or Unexpected Behavior

### STOP. Do not attempt a fix immediately.

Before ANY fix attempt, you MUST:

1. **State the problem** — What is the symptom? What was expected?
2. **Gather evidence** — Check logs, recent changes, search web if needed
3. **Form hypothesis** — What do you think is wrong and why?
4. **Output a plan** — State exactly what you will try
5. **Wait for approval** — User must approve before you proceed

---

## ONE FIX RULE (ABSOLUTE)

**You get ONE attempt per hypothesis.**

- If a fix fails, you MUST form a NEW hypothesis
- You CANNOT try the same fix with different wording
- You CANNOT make "small adjustments" to a failed fix
- Variations of the same approach = same fix = violation

### Examples of Violations:
- ❌ "Let me try restarting the service" → fails → "Let me restart with --force"
- ❌ "Adding import X" → fails → "Adding import X at a different line"
- ❌ "Setting timeout to 30s" → fails → "Setting timeout to 60s"

### Correct Approach:
- ✓ "Restart didn't work → NEW HYPOTHESIS: The config file is invalid"
- ✓ "Import X didn't help → NEW HYPOTHESIS: The module isn't installed"

---

## Fix Attempt Tracking

Maintain this table for any debug session:

```
| # | Hypothesis | Fix Tried | Result |
|---|------------|-----------|--------|
| 1 |            |           |        |
```

Before attempting fix #2, verify it targets a DIFFERENT hypothesis.

---

## Tools to Use

| Phase | Tools |
|-------|-------|
| **Research** | `run_command` (SSH for logs, git), `grep_search`, `view_file` |
| **Web Search** | `search_web` for error codes, stack traces |
| **Code Review** | `view_file`, `view_file_outline`, `view_code_item` |
| **Fix** | `run_command` (SSH), `replace_file_content` via SSH |
| **Verify** | `run_command` (health checks, tests) |

---

## Escalation Triggers

Stop and ask the user if:
- 3+ hypotheses tested without resolution
- You're unsure what's causing the issue
- The fix requires changes to multiple files/services
- Data integrity or security could be affected

---

## Invoke Full Protocol

For complex issues, invoke the full workflow:
```
/debug-protocol
```
