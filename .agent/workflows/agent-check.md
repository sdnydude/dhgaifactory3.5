---
description: Comprehensive project review, status update, and TODO maintenance
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Agent Check - Full Project Review (Remote-SSH)

// turbo-all

Run this workflow for a complete project status review. **Environment:** VS Code Remote-SSH on g700data1.

---

## 1. Docker Container Health

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "=== DOCKER CONTAINERS ===" && docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep -E "dhg-|NAME" && echo "" && echo "Healthy: $(docker compose ps --format "{{.Status}}" | grep -c healthy)" && echo "Total: $(docker compose ps --format "{{.Status}}" | wc -l)"
```

## 2. Agent Health Endpoints

**Note:** Orchestrator (:8011) was EOL'd - not included in checks.

```bash
echo "=== AGENT HEALTH ENDPOINTS ===" && printf "%-20s %-8s %-10s\n" "Agent" "Port" "Status" && printf "%-20s %-8s %-10s\n" "--------------------" "--------" "----------" && for pair in "Medical-LLM:8002" "Research:8003" "Curriculum:8004" "Outcomes:8005" "Competitor-Intel:8006" "QA-Compliance:8007" "Visuals:8008"; do agent="${pair%%:*}"; port="${pair##*:}"; status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://localhost:$port/health 2>/dev/null); if [ "$status" = "200" ]; then printf "%-20s %-8s %-10s\n" "$agent" "$port" "✓ Healthy"; elif [ -z "$status" ] || [ "$status" = "000" ]; then printf "%-20s %-8s %-10s\n" "$agent" "$port" "✗ Down"; else printf "%-20s %-8s %-10s\n" "$agent" "$port" "? ($status)"; fi; done
```

## 3. Git Status & Branch Info

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "=== GIT STATUS ===" && echo "Branch: $(git branch --show-current)" && echo "Latest commit: $(git log -1 --oneline)" && echo "Remote: $(git remote get-url origin)" && echo "" && git status --short
```

## 4. Ollama Models

```bash
echo "=== OLLAMA MODELS ===" && docker exec dhg-ollama ollama list 2>/dev/null || echo "Ollama not available"
```

## 5. LibreChat Status

```bash
echo "=== LIBRECHAT ===" && status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3010 2>/dev/null) && if [ "$status" = "200" ]; then echo "✓ LibreChat running (localhost:3010)"; else echo "✗ LibreChat not responding ($status)"; fi
```

## 6. Review TODO.md

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "=== TODO.md SUMMARY ===" && head -30 docs/TODO.md 2>/dev/null || echo "TODO.md not found"
```

## 7. Count Implemented Agents

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "=== AGENT IMPLEMENTATION STATUS ===" && echo "Agents with main.py:" && find agents -name "main.py" -type f | wc -l && echo "Agent directories:" && ls -d agents/*/ 2>/dev/null | wc -l
```

## 8. Recent Activity (Last 5 Commits)

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "=== RECENT COMMITS ===" && git log -5 --oneline --decorate
```

## 9. Disk Usage

```bash
echo "=== DISK USAGE ===" && df -h /home/swebber64 | tail -1
```

## 10. GPU Status

```bash
echo "=== GPU STATUS ===" && nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null || echo "nvidia-smi not available"
```

---

## Summary Format

After running, provide:

```
PROJECT STATUS SUMMARY
======================

✅ Healthy Containers: X/Y
✅ Agent Endpoints: X/7 responding
✅ Git Status: Clean / Uncommitted changes
✅ Branch: feature/langgraph-migration

⚠️ Issues Found:
- [List any issues]

🎯 Recommended Next Steps:
1. [Priority 1]
2. [Priority 2]
```

---

## Commit Changes (if approved)

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git add docs/TODO.md && git commit -m "docs: update TODO.md from /agent-check" && git push origin feature/langgraph-migration
```
