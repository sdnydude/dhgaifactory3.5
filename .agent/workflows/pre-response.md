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

If you catch yourself violating: Stop immediately, state "I made an unverified claim. Let me verify," then run verification.

---

## Step 1: Acknowledge Global Rules

Before responding, confirm you understand:

1. **No Placeholders** — Never use TODO, TBD, FIXME, dummy values, or "Replace this later"
2. **No Truncated Files** — If a file is shown, it is complete
3. **Truth Over Helpfulness** — Never fabricate files, values, or completeness
4. **Debug Discipline** — ONE fix per hypothesis, track all attempts
5. **Pre-Edit Verification** — View files before editing, state purpose and impact

---

## Step 2: Server-First Check (DHG AI Factory Project)

For ANY file operation on the DHG AI Factory project:

**Pre-Flight Checklist:**
- [ ] Target path is on 10.0.0.251, NOT local Mac?
- [ ] Using SSH command, NOT write_to_file or replace_file_content tools?
- [ ] Path starts with `/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/`?

**If any answer is NO → STOP and redirect to server.**

**SSH Command:**
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'command here'
```

**Project Path:**
```
/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/
```

---

## Step 3: Exceptions (Do NOT Require Server)

- Local `.agent/` files (rules, workflows)
- Browser-based work (Infisical UI, LibreChat UI)
- Antigravity brain artifacts in `.gemini/antigravity/brain/` — **session artifacts only** (task.md, implementation_plan.md, walkthroughs)
- Viewing screenshots or recordings

> **⚠️ PROJECT DOCUMENTATION IS NOT AN EXCEPTION.**
> Docs like REGISTRY_API.md, DHG_AGENTS_TEAM.md, planning docs, and images
> MUST go directly to `.251:/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/docs/`
> Do NOT create them locally first then copy over.

---

## Step 4: Before Responding

1. Have I violated any global rules?
2. Am I about to create/edit a file on the Mac that should be on .251?
3. Am I using heredocs correctly with single-quoted delimiters?

If violations detected → FIX before responding.
