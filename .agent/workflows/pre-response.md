---
description: MANDATORY pre-flight check before every response - read global rules and server-work workflow
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

---

## Step 1: Acknowledge Global Rules

1. **No Placeholders** — Never use TODO, TBD, FIXME, dummy values
2. **No Truncated Files** — If a file is shown, it is complete
3. **Truth Over Helpfulness** — Never fabricate files, values, or completeness
4. **Debug Discipline** — ONE fix per hypothesis, track all attempts
5. **Pre-Edit Verification** — View files before editing, state purpose and impact

---

## Step 2: EVERYTHING GOES ON .251 (NO EXCEPTIONS)

> **⚠️ THERE ARE NO EXCEPTIONS. EVERYTHING PROJECT-RELATED GOES ON THE SERVER.**

**All file operations use SSH:**
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'command'
```

**Project path:**
```
/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/
```

**This includes:**
- All documentation (docs/)
- All code (agents/, registry/, tools/, etc.)
- All images and assets (docs/assets/)
- All configuration (.agent/, .env files, etc.)
- All workflows and rules

**Do NOT use:**
- write_to_file tool for project files
- replace_file_content tool for project files  
- Local artifacts folder for project docs

**Browser work accessing external services (LangSmith Cloud) is fine.

---

## Step 3: Before Responding

1. Have I violated any global rules?
2. Am I about to use a local file tool? → STOP, use SSH instead
3. Am I creating a doc locally? → STOP, create on .251 directly

If violations detected → FIX before responding.
