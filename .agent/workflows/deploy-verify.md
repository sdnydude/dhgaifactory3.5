---
description: Post-deployment verification workflow
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Deploy and Verify Workflow

// turbo-all

Use this workflow after any Docker Compose changes to verify deployment.

---

## 1. Bring Up Services

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose up -d'
```

## 2. Wait for Health Checks (30 seconds)

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'echo "Waiting 30s for containers to stabilize..." && sleep 30'
```

## 3. Check Container Status

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose ps --format "table {{.Name}}\t{{.Status}}"'
```

## 4. Identify Unhealthy Containers

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose ps --format "{{.Name}}: {{.Status}}" | grep -v "healthy" | grep -v "running"'
```

## 5. Check Recent Logs for Errors

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose logs --tail=20 2>&1 | grep -iE "error|exception|failed|critical" | head -20'
```

## 6. Verify Critical Endpoints

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cat << "SCRIPT" | bash
echo "=== Critical Endpoints ==="
endpoints=(
  "http://localhost:5432"
  "http://localhost:8011/health"
  "http://localhost:3010"
  "http://localhost:11434/api/tags"
)

for endpoint in "${endpoints[@]}"; do
  status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "$endpoint" 2>/dev/null)
  echo "$endpoint: $status"
done
SCRIPT'
```

---

## If Issues Found

### View specific container logs:
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose logs --tail=100 <container-name>'
```

### Restart a specific service:
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose restart <service-name>'
```

### Full rebuild of a service:
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose up -d --build <service-name>'
```
