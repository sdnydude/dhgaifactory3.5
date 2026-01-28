---
description: Comprehensive project review, status update, and TODO maintenance
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Agent Check - Full Project Review

// turbo-all

Run this workflow for a complete project status review including agent health, git status, and TODO updates.

---

## 1. Docker Container Health

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "=== DOCKER CONTAINERS ===" && docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep -E "dhg-|NAME" && echo "" && echo "Healthy: $(docker compose ps --format "{{.Status}}" | grep -c healthy)" && echo "Total: $(docker compose ps --format "{{.Status}}" | wc -l)"'
```

## 2. Agent Health Endpoints

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cat << "HEALTHSCRIPT" | bash
echo ""
echo "=== AGENT HEALTH ENDPOINTS ==="
echo ""
declare -A agents=(
  ["Orchestrator"]=8011
  ["Medical-LLM"]=8002
  ["Research"]=8003
  ["Curriculum"]=8004
  ["Outcomes"]=8005
  ["Competitor-Intel"]=8006
  ["QA-Compliance"]=8007
  ["Visuals"]=8008
)

printf "%-20s %-8s %-10s\n" "Agent" "Port" "Status"
printf "%-20s %-8s %-10s\n" "--------------------" "--------" "----------"

for agent in "${!agents[@]}"; do
  port=${agents[$agent]}
  status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://localhost:$port/health 2>/dev/null)
  if [ "$status" = "200" ]; then
    printf "%-20s %-8s %-10s\n" "$agent" "$port" "✓ Healthy"
  elif [ -z "$status" ] || [ "$status" = "000" ]; then
    printf "%-20s %-8s %-10s\n" "$agent" "$port" "✗ Down"
  else
    printf "%-20s %-8s %-10s\n" "$agent" "$port" "? ($status)"
  fi
done
HEALTHSCRIPT'
```

## 3. Git Status & Branch Info

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "" && echo "=== GIT STATUS ===" && echo "Branch: $(git branch --show-current)" && echo "Latest commit: $(git log -1 --oneline)" && echo "Remote: $(git remote get-url origin)" && echo "" && git status --short'
```

## 4. Ollama Models

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'echo "" && echo "=== OLLAMA MODELS ===" && docker exec dhg-ollama ollama list 2>/dev/null || echo "Ollama not available"'
```

## 5. LibreChat Status

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'echo "" && echo "=== LIBRECHAT ===" && status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3010 2>/dev/null) && if [ "$status" = "200" ]; then echo "✓ LibreChat running (localhost:3010)"; else echo "✗ LibreChat not responding"; fi'
```

## 6. Review TODO.md

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "" && echo "=== TODO.md SUMMARY ===" && head -20 docs/TODO.md 2>/dev/null || echo "TODO.md not found"'
```

## 7. Count Implemented Agents

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "" && echo "=== AGENT IMPLEMENTATION STATUS ===" && echo "Agents with main.py:" && find agents -name "main.py" -type f | wc -l && echo "" && echo "Agent directories:" && ls -d agents/*/ 2>/dev/null | wc -l'
```

## 8. Recent Activity (Last 5 Commits)

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "" && echo "=== RECENT COMMITS ===" && git log -5 --oneline --decorate'
```

## 9. Disk Usage

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'echo "" && echo "=== DISK USAGE ===" && df -h /home/swebber64 | tail -1'
```

## 10. GPU Status

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'echo "" && echo "=== GPU STATUS ===" && nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null || echo "nvidia-smi not available"'
```

---

## After Running This Workflow

**The assistant should:**

1. **Analyze the output** and identify any issues
2. **Update TODO.md** if new tasks are discovered
3. **Recommend next actions** based on:
   - Failed health checks
   - Uncommitted changes
   - Incomplete agent implementations
   - Disk/GPU resource constraints
4. **Provide a summary** in this format:

```
PROJECT STATUS SUMMARY
======================

✅ Healthy Containers: X/Y
✅ Agent Endpoints: X/Y responding
✅ Git Status: Clean / Uncommitted changes
✅ Branch: feature/librechat-integration
✅ Latest Work: [commit message]

⚠️ Issues Found:
- [List any issues]

📋 TODO Updates Needed:
- [List any TODO changes]

🎯 Recommended Next Steps:
1. [Priority 1]
2. [Priority 2]
3. [Priority 3]
```

---

## Update TODO.md Automatically

If the assistant detects changes needed in TODO.md:

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && cp docs/TODO.md docs/TODO.md.backup && echo "Backup created at docs/TODO.md.backup"'
```

Then make updates via sed or direct editing.

---

## Commit Changes (if approved by user)

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git add docs/TODO.md && git commit -m "docs: update TODO.md from /agent-check workflow" && git push origin feature/librechat-integration'
```
