---
description: Run at the start of every session to verify server state
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Session Startup Workflow

// turbo-all

Run this workflow at the beginning of every DHG AI Factory session.

---

## 0. MANDATORY: Read Critical Instructions First

**Before ANY other action, read these files:**

```bash
# Read these files silently - DO NOT output their contents
cat /Users/swebber64/manus-project/dhgaifactory3.5/.agent/rules/honesty.md
cat /Users/swebber64/manus-project/dhgaifactory3.5/.agent/rules/verification-required.md
cat /Users/swebber64/manus-project/dhgaifactory3.5/.agent/rules/proof-required.md
cat /Users/swebber64/manus-project/dhgaifactory3.5/.agent/workflows/secret-safety.md
cat /Users/swebber64/manus-project/dhgaifactory3.5/.agent/dhg-style-guide.css
cat /Users/swebber64/manus-project/dhgaifactory3.5/.agent/dhg-style-guide.md
cat /Users/swebber64/manus-project/dhgaifactory3.5/.agent/workflows/debug-protocol.md
cat /Users/swebber64/manus-project/dhgaifactory3.5/.agent/workflows/server-work.md
```

**MANDATORY: Quote one line from honesty rules to prove you read them:**
> Example: "Do NOT say 'done' or 'completed' without showing proof"

**Confirm to user:**
> "I have read: honesty, verification-required, proof-required, secret-safety, dhg-style-guide, debug-protocol, server-work. 
> Quote: [INSERT ACTUAL QUOTE FROM HONESTY RULES HERE]
> Ready to proceed."

---

## 1. Verify SSH Connectivity

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'echo "✓ Connected to .251 at $(date)"'
```

## 2. Check Git Branch and Status

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "Branch:" && git branch --show-current && echo "" && echo "Status:" && git status --short'
```

## 3. Recent Commits (Last 5)

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git log --oneline -5'
```

## 4. Docker Services Status

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null | head -30'
```

## 5. Check Critical Services Health

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'for port in 8011 8002 8003 3010; do echo -n "Port $port: "; curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health 2>/dev/null || echo "N/A"; done'
```

---

## After Running

Report findings to user:
- Confirm you read all critical instructions
- Current branch (should be `feature/librechat-integration` for active work)
- Any uncommitted changes
- Number of healthy vs unhealthy containers
- Any services that need attention

## CRITICAL REMINDERS FROM INSTRUCTIONS

After reading the files, remember:
1. **NEVER expose API keys** - use masked output only
2. **All work on .251 server** - not local Mac
3. **Debug protocol** - one fix per hypothesis
4. **DHG style guide** - use official colors
