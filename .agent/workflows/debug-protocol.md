---
description: Systematic debugging protocol with mandatory reflection and tracking
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Debug Protocol Workflow

## CRITICAL RULES (NON-NEGOTIABLE)

1. **ONE FIX ATTEMPT PER HYPOTHESIS** — If a fix doesn't work, you MUST form a NEW hypothesis before trying again
2. **NO DISGUISED RETRIES** — The same fix reworded, restructured, or slightly modified is STILL the same fix
3. **PAUSE BEFORE ACTION** — No fix attempts without completing Phases 1-4 first
4. **APPROVAL REQUIRED** — User must approve debug plan before Phase 5

---

## Phase 1: PAUSE (Mandatory)

Stop. Do not attempt any fixes. State the problem clearly.

**Output required:**
```
## Problem Statement
- **Symptom:** [What is happening]
- **Expected:** [What should happen]
- **Context:** [When did this start, what changed]
- **Severity:** [Critical/High/Medium/Low]
```

---

## Phase 2: RESEARCH (Mandatory)

Gather evidence before forming any hypothesis.

### 2.1 Check Container Logs
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose logs --tail=100 <service-name> 2>&1 | grep -iE "error|exception|failed|warn"'
```

### 2.2 Check Recent Code Changes
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git log --oneline -10 && git diff HEAD~3 --stat'
```

### 2.3 Web Search (if error code/message unfamiliar)
- Search for exact error message
- Check official documentation
- Look for GitHub issues

**Output required:**
```
## Evidence Gathered
- **Logs:** [Key error lines or "No errors found"]
- **Recent changes:** [Relevant commits or "None related"]
- **Web findings:** [Links and summaries or "N/A"]
```

---

## Phase 3: HYPOTHESIZE (Mandatory)

Form 2-3 possible causes, ranked by likelihood.

**Output required:**
```
## Hypotheses (Ranked)
1. [Most likely cause] — Confidence: X%
2. [Second possibility] — Confidence: X%
3. [Third possibility] — Confidence: X%

## Ruling Out
- [What evidence supports/refutes each hypothesis]
```

---

## Phase 4: PLAN (Mandatory — Requires Approval)

Define specific investigation steps. **STOP HERE AND WAIT FOR USER APPROVAL.**

**Output required:**
```
## Debug Plan

### Hypothesis Being Tested: [#1 from above]

### Investigation Steps:
1. [Specific action]
2. [Specific action]
3. [Specific action]

### Proposed Fix (if investigation confirms):
[Exact change to be made]

### Rollback Plan:
[How to undo if fix fails]

⚠️ AWAITING USER APPROVAL BEFORE PROCEEDING
```

---

## Phase 5: INVESTIGATE

Execute the approved plan. Log findings at each step.

**Output required:**
```
## Investigation Log
- Step 1: [Action] → [Result]
- Step 2: [Action] → [Result]
- Step 3: [Action] → [Result]

## Conclusion: [Hypothesis confirmed/refuted]
```

---

## Phase 6: FIX (One Attempt Only)

⚠️ **CRITICAL: You get ONE attempt per hypothesis.**

- Apply the smallest possible change
- If the fix fails, return to Phase 3 with a NEW hypothesis
- You CANNOT retry the same fix with minor modifications

```bash
# Before fixing, document:
echo "Fix attempt #[N] for hypothesis #[X]"
echo "If this fails, next hypothesis is #[Y]"
```

---

## Phase 7: VERIFY

Confirm the fix works and check for regressions.

**Verification checklist:**
```
- [ ] Original symptom resolved
- [ ] Service health check passes
- [ ] Related services unaffected
- [ ] No new errors in logs
```

---

## Phase 8: DOCUMENT

Create a debug report for future reference.

**Output required:**
```
## Debug Report: [Issue Title]
**Date:** [Date]
**Duration:** [Time spent]

### Root Cause
[What was actually wrong]

### Fix Applied
[Exact change made]

### Prevention
[How to prevent this in future]

### Lessons Learned
[What to remember]
```

---

## Fix Attempt Tracking

Maintain a running count per debug session:

```
## Fix Attempts This Session
| # | Hypothesis | Fix Description | Result |
|---|------------|-----------------|--------|
| 1 | [H1]       | [What I tried]  | ❌/✓   |
| 2 | [H2]       | [What I tried]  | ❌/✓   |
```

If you attempt the same fix twice (even reworded), you are violating the protocol.

---

## When to Escalate

Escalate to user immediately if:
- More than 3 hypotheses have been tested without resolution
- Fix requires changes to multiple services
- Root cause is unclear after 30 minutes of investigation
- Issue involves data loss or security
