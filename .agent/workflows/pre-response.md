---
description: MANDATORY pre-flight check before every response - read global rules
---

# Pre-Response Workflow (MANDATORY)

// turbo-all

> **⚠️ YOU MUST READ THIS FILE AT THE START OF EVERY RESPONSE.**
> Do not skip. Do not assume you remember. Read it, internalize it, then respond.

**Run this workflow BEFORE every response to the user.**

---

## Step 0: Honesty Protocol (ABSOLUTE - NO EXCEPTIONS)

> **RULE 0:** Never lie, sugarcoat, or hide the truth.

**Prohibited:**
- Stating things with confidence that haven't been verified
- Claiming completion without proof
- Presenting assumptions as facts
- Prioritizing forward movement over accuracy

**Before ANY claim of completion:**
1. STOP — Do I have verified evidence?
2. CHECK — If no, run verification commands
3. PROVE — Show the user the evidence
4. THEN — Make the claim

If you catch yourself violating: Stop immediately, state "I made an unverified claim. Let me verify," then run verification.

---

## Step 1: Acknowledge Global Rules

Before responding, confirm you understand:

1. **No Placeholders** — Never use TODO, TBD, FIXME, dummy values, or "Replace this later"
2. **No Truncated Files** — If a file is shown, it is complete
3. **Truth Over Helpfulness** — Never fabricate files, values, or completeness
4. **Debug Discipline** — ONE fix per hypothesis, track all attempts
5. **Pre-Edit Verification** — View files before editing, state purpose and impact
6. **LangChain Docs** — When researching LangGraph/LangSmith/LangChain, ALWAYS start at https://docs.langchain.com/

---

## Step 2: Environment Check (Remote-SSH on g700data1)

**Current Setup:** VS Code Remote-SSH connected directly to **10.0.0.251 (g700data1)**

This means:
- ✅ Standard file tools (`write_to_file`, `replace_file_content`, etc.) work directly on the server
- ✅ No SSH wrapping required for commands
- ✅ All paths are already server paths

**Project Path:**
```
/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/
```

**Verify you're on the server if unsure:**
```bash
hostname  # Should return: g700data1
```

---

## Step 3: Before Responding

1. Have I violated any global rules?
2. Am I making claims without verification?
3. Have I viewed files before editing them?

If violations detected → FIX before responding.
