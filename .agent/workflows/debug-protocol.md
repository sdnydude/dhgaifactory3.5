---
description: Systematic debugging protocol with mandatory reflection and tracking
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Debug Protocol Workflow (Remote-SSH)

// turbo-all

**Environment:** VS Code Remote-SSH on g700data1

## CRITICAL RULES (NON-NEGOTIABLE)

1. **ONE FIX ATTEMPT PER HYPOTHESIS** — If a fix doesn't work, you MUST form a NEW hypothesis
2. **NO DISGUISED RETRIES** — Same fix reworded is STILL the same fix
3. **PAUSE BEFORE ACTION** — No fix attempts without completing Phases 1-4
4. **APPROVAL REQUIRED** — User must approve debug plan before Phase 5

---

## Phase 1: PAUSE (Mandatory)

Stop. Do not attempt any fixes. State the problem clearly.

```
## Problem Statement
- **Symptom:** [What is happening]
- **Expected:** [What should happen]
- **Context:** [When did this start, what changed]
- **Severity:** [Critical/High/Medium/Low]
```

---

## Phase 2: RESEARCH (Mandatory)

### 2.1 Check Container Logs
```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose logs --tail=100 <service-name> 2>&1 | grep -iE "error|exception|failed|warn"
```

### 2.2 Check Recent Code Changes
```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git log --oneline -10 && git diff HEAD~3 --stat
```

### 2.3 Web Search (if error unfamiliar)
- Search exact error message
- Check official documentation
- Look for GitHub issues

```
## Evidence Gathered
- **Logs:** [Key error lines or "No errors found"]
- **Recent changes:** [Relevant commits or "None related"]
- **Web findings:** [Links and summaries or "N/A"]
```

---

## Phase 3: HYPOTHESIZE (Mandatory)

Form 2-3 possible causes, ranked by likelihood.

```
## Hypotheses (Ranked)
1. [Most likely cause] — Confidence: X%
2. [Second possibility] — Confidence: X%
3. [Third possibility] — Confidence: X%

## Ruling Out
- [What evidence supports/refutes each]
```

---

## Phase 4: PLAN (Requires Approval)

⚠️ **STOP HERE AND WAIT FOR USER APPROVAL.**

```
## Debug Plan

### Hypothesis Being Tested: [#1 from above]

### Investigation Steps:
1. [Specific action]
2. [Specific action]

### Proposed Fix (if confirmed):
[Exact change to be made]

### Rollback Plan:
[How to undo if fix fails]

⚠️ AWAITING USER APPROVAL BEFORE PROCEEDING
```

---

## Phase 5: INVESTIGATE

Execute the approved plan. Log findings.

```
## Investigation Log
- Step 1: [Action] → [Result]
- Step 2: [Action] → [Result]

## Conclusion: [Hypothesis confirmed/refuted]
```

---

## Phase 6: FIX (One Attempt Only)

⚠️ **You get ONE attempt per hypothesis.**

- Apply the smallest possible change
- If fix fails, return to Phase 3 with NEW hypothesis
- You CANNOT retry same fix with modifications

---

## Phase 7: VERIFY

```
- [ ] Original symptom resolved
- [ ] Service health check passes
- [ ] Related services unaffected
- [ ] No new errors in logs
```

---

## Phase 8: DOCUMENT

```
## Debug Report: [Issue Title]
**Date:** [Date]
**Duration:** [Time spent]

### Root Cause
[What was actually wrong]

### Fix Applied
[Exact change made]

### Prevention
[How to prevent in future]
```

---

## Fix Attempt Tracking

```
| # | Hypothesis | Fix Description | Result |
|---|------------|-----------------|--------|
| 1 | [H1]       | [What I tried]  | ❌/✓   |
```

---

## When to Escalate

Escalate immediately if:
- More than 3 hypotheses tested without resolution
- Fix requires changes to multiple services
- Root cause unclear after 30 minutes
- Issue involves data loss or security
