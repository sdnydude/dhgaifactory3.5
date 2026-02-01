---
description: Run at the start of every session to verify server state
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Session Startup Workflow (Remote-SSH)

// turbo-all

Run this workflow at the beginning of every DHG AI Factory session.

**Environment:** VS Code Remote-SSH on g700data1 (10.0.0.251)

---

## 0. MANDATORY: Read Critical Instructions First

**Read these files using view_file tool:**
- `.agent/rules/honesty.md`
- `.agent/rules/verification-required.md`
- `.agent/rules/proof-required.md`
- `.agent/workflows/secret-safety.md`
- `.agent/dhg-style-guide.md`
- `.agent/workflows/debug-protocol.md`
- `.agent/workflows/server-work.md`

**MANDATORY: Quote one line from honesty rules to prove you read them:**
> Example: "Do NOT say 'done' or 'completed' without showing proof"

---

## 1. Verify Server Environment

```bash
hostname && echo "✓ Connected to $(hostname) at $(date)"
```

## 2. Check Git Branch and Status

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "Branch:" && git branch --show-current && echo "" && echo "Status:" && git status --short
```

## 3. Recent Commits (Last 5)

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git log --oneline -5
```

## 4. Docker Services Status

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null | head -30
```

## 5. Check Critical Services Health

**Note:** Orchestrator (:8011) is EOL'd

```bash
for port in 8002 8003 3010; do echo -n "Port $port: "; curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health 2>/dev/null || echo "N/A"; done
```

## 6. Check Planning Files (If Complex Task)

If this session involves a complex task (5+ tool calls expected):

```bash
ls -la task_plan.md findings.md progress.md 2>/dev/null || echo "No planning files found - create them if starting complex work"
```

If files exist, read them to recover context:
```bash
head -50 task_plan.md 2>/dev/null
```

---

## After Running

Report findings to user:
- Confirm you read all critical instructions
- Current branch (should be `feature/langgraph-migration` for active work)
- Any uncommitted changes
- Number of healthy vs unhealthy containers
- Any services that need attention

## CRITICAL REMINDERS

1. **NEVER expose API keys** - use masked output only
2. **Debug protocol** - one fix per hypothesis
3. **DHG style guide** - use official colors
4. **All file tools work directly** - no SSH wrapping needed
