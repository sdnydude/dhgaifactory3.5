---
description: Sync planning files (task_plan.md, findings.md, progress.md) to CR database
---

# Planning Files Sync Workflow

// turbo-all

> **Use at the end of significant work sessions to persist planning files to the database.**

---

## Overview

This workflow syncs planning files from the current project to the CR database for:
- Knowledge search across projects
- Reporting and analytics  
- Session recovery
- Pattern detection

---

## Step 1: Verify Planning Files Exist

```bash
ls -la task_plan.md findings.md progress.md 2>/dev/null || echo "WARNING: Some planning files missing"
```

---

## Step 2: Check Database Connection

```bash
# Ensure password is available
if [ -z "$DB_PASSWORD" ] && [ -z "$PGPASSWORD" ]; then
    echo "ERROR: Set DB_PASSWORD or PGPASSWORD environment variable"
    exit 1
fi
echo "Database credentials available"
```

---

## Step 3: Run Sync Script

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
python3 scripts/sync_planning_files.py --project-dir "$(pwd)"
```

---

## Step 4: Verify Sync

```bash
psql -h localhost -U dhg -d dhg_registry -c "
SELECT project_name, file_name, updated_at, 
       (metadata->>'line_count')::int as lines,
       (metadata->>'completed_tasks')::int as completed,
       (metadata->>'total_tasks')::int as total
FROM planning_documents 
ORDER BY updated_at DESC 
LIMIT 10
"
```

---

## Step 5: Generate Embeddings (Optional)

If you want searchable embeddings:

```bash
python3 scripts/generate_planning_embeddings.py
```

---

## Automatic Sync

For automatic sync at session end, add to your shell profile:

```bash
# ~/.bashrc or ~/.zshrc
alias plan-sync="cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && python3 scripts/sync_planning_files.py --project-dir \$(pwd)"
```

---

## Troubleshooting

### No planning files found
- Create them first: `touch task_plan.md findings.md progress.md`
- Or use the planning-with-files skill to initialize

### Database connection failed
- Check DB_PASSWORD or PGPASSWORD is set
- Verify database is running: `psql -h localhost -U dhg -d dhg_registry -c "SELECT 1"`

### Sync says "No changes detected"
- This is normal if content hasn't changed since last sync
- Force re-sync by modifying a planning file

---

## Related

- `/planning-with-files` — The skill this syncs from
- Rule: `.agent/rules/planning-with-files.md` — Mandates using planning files
