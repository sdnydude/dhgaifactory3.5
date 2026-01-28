---
description: Check all databases, RAG systems, documentation, and data processing infrastructure
---

# Data Infrastructure Health Check

Run this workflow to verify all data infrastructure is operational.

// turbo-all

## 1. Database Health Checks

### PostgreSQL Databases
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 '
echo "=== PostgreSQL Databases ==="
echo ""
echo "--- Registry DB (dhg-registry-db) ---"
docker exec 986cbb4003b3_dhg-registry-db pg_isready -U dhg 2>/dev/null && echo "✅ Registry DB: Healthy" || echo "❌ Registry DB: Unhealthy"

echo ""
echo "--- Infisical DB ---"
docker exec infisical-db pg_isready -U infisical 2>/dev/null && echo "✅ Infisical DB: Healthy" || echo "❌ Infisical DB: Unhealthy"

echo ""
echo "--- Transcribe DB ---"
docker exec dhg-transcribe-db pg_isready -U postgres 2>/dev/null && echo "✅ Transcribe DB: Healthy" || echo "❌ Transcribe DB: Unhealthy"
'
```

### MySQL Databases
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 '
echo "=== MySQL Databases ==="
echo ""
echo "--- RAGFlow MySQL ---"
docker exec docker-mysql-1 mysqladmin ping -u root --silent 2>/dev/null && echo "✅ RAGFlow MySQL: Healthy" || echo "❌ RAGFlow MySQL: Unhealthy"
'
```

### Redis Instances
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 '
echo "=== Redis Instances ==="
echo ""
docker ps --format "{{.Names}}" | grep redis | while read name; do
  docker exec $name redis-cli ping 2>/dev/null | grep -q PONG && echo "✅ $name: Healthy" || echo "❌ $name: Unhealthy"
done
'
```

## 2. RAG Systems

### RAGFlow
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 '
echo "=== RAGFlow ==="
echo ""
curl -s -o /dev/null -w "%{http_code}" http://localhost:8585 | grep -q "200\|302" && echo "✅ RAGFlow UI (port 8585): Accessible" || echo "❌ RAGFlow UI: Not accessible"

echo ""
echo "RAGFlow Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "ragflow|es01|minio"
'
```

### Dify (RAG + Workflows)
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 '
echo "=== Dify ==="
echo ""
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200\|302" && echo "✅ Dify UI (port 3000): Accessible" || echo "❌ Dify UI: Not accessible"

echo ""
echo "Dify Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "docker-(api|worker|web|nginx|sandbox|plugin)"
'
```

### Elasticsearch
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 '
echo "=== Elasticsearch ==="
echo ""
curl -s http://localhost:1200/_cluster/health 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Status: {d.get('status','unknown')}, Nodes: {d.get('number_of_nodes',0)}\")" 2>/dev/null || echo "❌ Elasticsearch: Not responding"
'
```

## 3. Vector Databases
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 '
echo "=== Vector Databases ==="
echo ""
docker ps --format "{{.Names}}\t{{.Status}}" | grep -i vector
'
```

## 4. Object Storage

### MinIO
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 '
echo "=== MinIO Object Storage ==="
echo ""
curl -s -o /dev/null -w "%{http_code}" http://localhost:9010/minio/health/live | grep -q "200" && echo "✅ MinIO (port 9010): Healthy" || echo "❌ MinIO: Unhealthy"
echo "Console: http://10.0.0.251:9011"
'
```

## 5. Secrets Management

### Infisical
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 '
echo "=== Infisical Secrets ==="
echo ""
curl -s -o /dev/null -w "%{http_code}" http://localhost:8089 | grep -q "200\|302" && echo "✅ Infisical (port 8089): Accessible" || echo "❌ Infisical: Not accessible"
echo "URL: https://secrets.digitalharmonyai.com"
'
```

## 6. LLM Infrastructure

### Ollama
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 '
echo "=== Ollama LLM ==="
echo ""
curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); models=[m[\"name\"] for m in d.get(\"models\",[])]; print(f\"✅ Ollama: Running with {len(models)} models: {models}\")" 2>/dev/null || echo "❌ Ollama: Not responding"
'
```

## 7. External Services Check

### Cloudflare Tunnel
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 '
echo "=== Cloudflare Tunnel ==="
echo ""
docker ps --format "{{.Names}}\t{{.Status}}" | grep cloudflare
'
```

### Public URLs
```bash
echo "=== Public URL Checks ==="
echo ""
for url in "https://dify.digitalharmonyai.com" "https://secrets.digitalharmonyai.com" "https://app.digitalharmonyai.com"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
  [ "$code" = "200" ] || [ "$code" = "302" ] && echo "✅ $url: OK ($code)" || echo "❌ $url: Failed ($code)"
done
```

## 8. Summary

After running all checks, review:
- Total databases checked
- Services healthy vs unhealthy  
- Any critical issues requiring immediate attention

---

## Adding New Checks

To add a new data infrastructure component:
1. Add a new section with appropriate header
2. Use consistent output format (✅/❌ prefix)
3. Update this workflow file
