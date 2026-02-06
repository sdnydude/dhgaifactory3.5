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

## 2. LangGraph Server (CME Agents)

**Primary CME agent backend on port 2026.**

```bash
echo "=== LANGGRAPH SERVER (2026) ===" && status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://localhost:2026/ok 2>/dev/null) && if [ "$status" = "200" ]; then echo "✓ LangGraph running (localhost:2026)"; else echo "✗ LangGraph not responding ($status)"; fi && echo "" && echo "Available graphs:" && curl -s http://localhost:2026/info 2>/dev/null | jq -r '.graphs | keys[]' 2>/dev/null || echo "Could not fetch graphs"
```

## 3. Legacy Agent Endpoints (Deprecated)

**Note:** These are the OLD agents. Most have been replaced by CME Instruments on LangGraph.

```bash
echo "=== LEGACY AGENT ENDPOINTS (May be deprecated) ===" && printf "%-20s %-8s %-10s\n" "Agent" "Port" "Status" && printf "%-20s %-8s %-10s\n" "--------------------" "--------" "----------" && for pair in "Medical-LLM:8002" "Competitor-Intel:8006" "Visuals:8008" "Logo-Maker:8012"; do agent="${pair%%:*}"; port="${pair##*:}"; status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://localhost:$port/health 2>/dev/null); if [ "$status" = "200" ]; then printf "%-20s %-8s %-10s\n" "$agent" "$port" "✓ Healthy"; elif [ -z "$status" ] || [ "$status" = "000" ]; then printf "%-20s %-8s %-10s\n" "$agent" "$port" "✗ Down"; else printf "%-20s %-8s %-10s\n" "$agent" "$port" "? ($status)"; fi; done
```

## 4. Git Status & Branch Info

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "=== GIT STATUS ===" && echo "Branch: $(git branch --show-current)" && echo "Latest commit: $(git log -1 --oneline)" && echo "Remote: $(git remote get-url origin)" && echo "" && git status --short
```

## 5. Ollama Models

```bash
echo "=== OLLAMA MODELS ===" && docker exec dhg-ollama ollama list 2>/dev/null || echo "Ollama not available"
```

## 6. LibreChat Status

```bash
echo "=== LIBRECHAT ===" && status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3010 2>/dev/null) && if [ "$status" = "200" ]; then echo "✓ LibreChat running (localhost:3010)"; else echo "✗ LibreChat not responding ($status)"; fi
```

## 7. Review TODO.md

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "=== TODO.md SUMMARY ===" && head -30 docs/TODO.md 2>/dev/null || echo "TODO.md not found"
```

## 8. CME Agent Implementation Status

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "=== CME AGENT IMPLEMENTATION ===" && echo "LangGraph agents (agents/cme-*):" && ls -d agents/cme-*/ 2>/dev/null | wc -l && echo "" && echo "Agent directories:" && ls agents/cme-*/ 2>/dev/null || echo "No cme-* agents found"
```

## 9. Recent Activity (Last 5 Commits)

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "=== RECENT COMMITS ===" && git log -5 --oneline --decorate
```

## 10. Disk Usage

```bash
echo "=== DISK USAGE ===" && df -h /home/swebber64 | tail -1
```

## 11. GPU Status

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
✅ LangGraph Server: Running/Down (port 2026)
✅ LibreChat: Running (port 3010)
✅ Git Status: Clean / Uncommitted changes
✅ Branch: feature/langgraph-migration

⚠️ Issues Found:
- [List any issues]

🎯 Recommended Next Steps:
1. [Priority 1]
2. [Priority 2]
```

---

## CME Agent Roster (Current)

### CME Instruments (11 agents on LangGraph)
1. Medical Research
2. Clinical Practice
3. Gap Analysis
4. Needs Assessment
5. Learning Objectives
6. Curriculum Design
7. Research Protocol
8. Marketing Plan
9. Grant Writer
10. Prose QA
11. Compliance Review

### CME Compositions (4 recipes)
1. full_pipeline - Complete CME grant workflow
2. needs_package - Research → Gap → Needs Assessment
3. curriculum_package - Design curriculum + objectives
4. grant_package - Grant writing + QA + compliance

---

## Commit Changes (if approved)

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git add docs/TODO.md && git commit -m "docs: update TODO.md from /agent-check" && git push origin feature/langgraph-migration
```
