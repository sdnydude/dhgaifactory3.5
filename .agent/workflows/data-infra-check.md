---
description: Check all databases, RAG systems, documentation, and data processing infrastructure
---

# Data Infrastructure Health Check (Remote-SSH)

// turbo-all

Run this workflow to verify all data infrastructure is operational.

**Environment:** VS Code Remote-SSH on g700data1

---

## 1. Database Health Checks

### PostgreSQL Databases
```bash
echo "=== PostgreSQL Databases ===" && \
echo "--- Registry DB ---" && \
docker exec 986cbb4003b3_dhg-registry-db pg_isready -U dhg 2>/dev/null && echo "✅ Registry DB: Healthy" || echo "❌ Registry DB: Unhealthy" && \
echo "--- Infisical DB ---" && \
docker exec infisical-db pg_isready -U infisical 2>/dev/null && echo "✅ Infisical DB: Healthy" || echo "❌ Infisical DB: Unhealthy" && \
echo "--- Transcribe DB ---" && \
docker exec dhg-transcribe-db pg_isready -U postgres 2>/dev/null && echo "✅ Transcribe DB: Healthy" || echo "❌ Transcribe DB: Unhealthy"
```

### MySQL Databases
```bash
echo "=== MySQL Databases ===" && \
docker exec docker-mysql-1 mysqladmin ping -u root --silent 2>/dev/null && echo "✅ RAGFlow MySQL: Healthy" || echo "❌ RAGFlow MySQL: Unhealthy"
```

### Redis Instances
```bash
echo "=== Redis Instances ===" && \
docker ps --format "{{.Names}}" | grep redis | while read name; do docker exec $name redis-cli ping 2>/dev/null | grep -q PONG && echo "✅ $name: Healthy" || echo "❌ $name: Unhealthy"; done
```

## 2. RAG Systems

### RAGFlow
```bash
echo "=== RAGFlow ===" && \
curl -s -o /dev/null -w "%{http_code}" http://localhost:8585 | grep -qE "200|302|307" && echo "✅ RAGFlow UI (port 8585): Accessible" || echo "❌ RAGFlow UI: Not accessible" && \
echo "RAGFlow Containers:" && \
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "ragflow|es01|minio"
```

### Dify (RAG + Workflows)
```bash
echo "=== Dify ===" && \
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -qE "200|302|307" && echo "✅ Dify UI (port 3000): Accessible" || echo "❌ Dify UI: Not accessible" && \
echo "Dify Containers:" && \
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "docker-(api|worker|web|nginx|sandbox|plugin)"
```

### Elasticsearch
```bash
echo "=== Elasticsearch ===" && \
curl -s http://localhost:1200/_cluster/health 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Status: {d.get('status','unknown')}, Nodes: {d.get('number_of_nodes',0)}\")" 2>/dev/null || echo "❌ Elasticsearch: Not responding"
```

## 3. Vector Databases
```bash
echo "=== Vector Databases ===" && docker ps --format "{{.Names}}\t{{.Status}}" | grep -i vector
```

## 4. Object Storage

### MinIO
```bash
echo "=== MinIO Object Storage ===" && \
curl -s -o /dev/null -w "%{http_code}" http://localhost:9010/minio/health/live | grep -q "200" && echo "✅ MinIO (port 9010): Healthy" || echo "❌ MinIO: Unhealthy" && \
echo "Console: http://10.0.0.251:9011"
```

## 5. Secrets Management

### Infisical
```bash
echo "=== Infisical Secrets ===" && \
curl -s -o /dev/null -w "%{http_code}" http://localhost:8089 | grep -qE "200|302|307" && echo "✅ Infisical (port 8089): Accessible" || echo "❌ Infisical: Not accessible" && \
echo "URL: https://secrets.digitalharmonyai.com"
```

## 6. LLM Infrastructure

### Ollama
```bash
echo "=== Ollama LLM ===" && \
curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); models=[m['name'] for m in d.get('models',[])]; print(f\"✅ Ollama: Running with {len(models)} models: {models}\")" 2>/dev/null || echo "❌ Ollama: Not responding"
```

## 7. External Services Check

### Cloudflare Tunnel
```bash
echo "=== Cloudflare Tunnel ===" && docker ps --format "{{.Names}}\t{{.Status}}" | grep cloudflare
```

### Public URLs
```bash
echo "=== Public URL Checks ===" && \
for url in "https://dify.digitalharmonyai.com" "https://secrets.digitalharmonyai.com" "https://app.digitalharmonyai.com"; do code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null); [ "$code" = "200" ] || [ "$code" = "302" ] && echo "✅ $url: OK ($code)" || echo "❌ $url: Failed ($code)"; done
```

## 8. Summary

After running all checks, provide summary of:
- Total databases checked
- Services healthy vs unhealthy
- Any critical issues requiring immediate attention
