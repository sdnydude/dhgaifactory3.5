---
description: Post-deployment verification workflow
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Deploy and Verify Workflow (Remote-SSH)

// turbo-all

**Environment:** VS Code Remote-SSH on g700data1

---

## 1. Bring Up Services

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose up -d
```

## 2. Wait for Health Checks (30 seconds)

```bash
echo "Waiting 30s for containers to stabilize..." && sleep 30
```

## 3. Check Container Status

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose ps --format "table {{.Name}}\t{{.Status}}"
```

## 4. Identify Unhealthy Containers

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose ps --format "{{.Name}}: {{.Status}}" | grep -v "healthy" | grep -v "running"
```

## 5. Check Recent Logs for Errors

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose logs --tail=20 2>&1 | grep -iE "error|exception|failed|critical" | head -20
```

## 6. Verify Critical Endpoints

**Note:** Orchestrator (:8011) is EOL'd

```bash
for port in 8002 8003 3010 11434; do echo -n "Port $port: "; curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "http://localhost:$port/health" 2>/dev/null || echo "N/A"; done
```

---

## If Issues Found

### View specific container logs:
```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose logs --tail=100 <container-name>
```

### Restart a specific service:
```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose restart <service-name>
```

### Full rebuild of a service:
```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose up -d --build <service-name>
```

### Rollback (if needed):
```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git checkout HEAD~1 -- docker-compose.yml && docker compose up -d
```
