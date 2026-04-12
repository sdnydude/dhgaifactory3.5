# Local LLM Inference Platform Design

**Date:** 2026-04-11
**Author:** Stephen Webber + Claude
**Status:** Approved

## Overview

A multi-node local LLM inference platform for DHG AI Factory. Each node runs Ollama + a FastAPI gateway service. A central registry on g700data1 (.251) handles model/node discovery, logging, and feedback loops. Claude API serves as fallback for quality-critical tasks.

## Goals

1. Run local LLMs for medical, vision, and general tasks — reduce API costs, keep data on-premise
2. Every LLM interaction (input, output, tokens, latency, user_id) logged to registry-db on .251's 4TB disk
3. Automatic fallback to Claude API when local models fail or are unavailable
4. Quality feedback loops with automated evaluation and human review
5. Same gateway codebase deployed to every node — no per-node code changes

## Non-Goals (YAGNI)

- Load balancing across multiple nodes with the same model
- Auto-scaling / spinning up new nodes dynamically
- Model fine-tuning pipeline
- A/B testing framework (feedback loops serve this purpose)

---

## Architecture

### Network Topology

```
+-------------------------------------------------------------+
|                    10.0.0.0/24 LAN                          |
|                                                             |
|  +--------------+  +--------------+  +------------------+  |
|  | 5090 Node    |  | Jason Node   |  | g700data1 (.251) |  |
|  | 10.0.0.54    |  | 10.0.0.??    |  | 10.0.0.251       |  |
|  |              |  |              |  |                    |  |
|  | Gateway:8100 |  | Gateway:8100 |  | Registry API:8011 |  |
|  | Ollama:11434 |  | Ollama:11434 |  | Registry DB:5432  |  |
|  |              |  |              |  | Ollama:11434       |  |
|  | Meditron3-8B |  | Qwen2.5-VL   |  | LangGraph Agents  |  |
|  | (medical)    |  | (vision)     |  | Frontend:3000     |  |
|  +------+-------+  +------+-------+  | Transcription     |  |
|         |                 |          +--------+-----------+  |
|         +--------+--------+                   |              |
|                  v                             |              |
|          All logs/records ------------------>  |              |
|          write to registry-db on .251          |              |
|          stored on /mnt/4tb                    |              |
+-------------------------------------------------------------+
```

### Per-Node Stack

Each NEW inference node runs:
- **Ollama** (native install) — model serving with built-in parallelism
- **Node Gateway** (FastAPI on port 8100) — proxy, validation, logging, heartbeat

**Exception:** g700data1 (.251) keeps its existing Docker-based Ollama (`dhg-ollama` container). The gateway on .251 addresses it at `http://dhg-ollama:11434` (Docker DNS) instead of `http://localhost:11434`.

### Data Storage

| What | Where |
|------|-------|
| Model weights | Local per node (Ollama default path) |
| All LLM interaction logs | registry-db on .251 (/mnt/4tb/docker) |
| Embeddings | pgvector in registry-db on .251 |
| Large media references | /mnt/4tb on .251 |
| Local failover queue | SQLite on each node (flushed when .251 returns) |

---

## Initial Deployment

| Node | GPU | VRAM | Model | Task Types |
|------|-----|------|-------|------------|
| 5090 (10.0.0.54) | RTX 5090 | 24GB | meditron3:8b | medical, clinical |
| Jason (10.0.0.??) | RTX 5080 | 16GB | qwen2.5-vl:7b | vision, ebay_listing |
| .251 g700data1 | RTX 5080 | 16GB | qwen3:14b, llama3.1:8b, nomic-embed-text (existing) | general, bulk, embedding |

### VRAM Budget: g700data1 (.251, 16GB RTX 5080)

qwen3:14b is already running on .251 and is the heaviest model. VRAM budget:
- qwen3:14b weights (Q4): ~9GB
- NUM_PARALLEL=2 KV cache: ~3GB
- nomic-embed-text: ~0.3GB
- Total: ~12.3GB of 16GB
- Headroom: ~3.7GB

Note: .251 also runs PostgreSQL, Docker services, LangGraph agents, and will run transcription. The 3.7GB headroom is tight. If OOM occurs, reduce to NUM_PARALLEL=1 or offload qwen3:14b to another node.

### Ollama Configuration (per node)

```
OLLAMA_NUM_PARALLEL=2        # 2 concurrent requests
OLLAMA_MAX_QUEUE=50          # Reject after 50 pending
```

Context length is set per-model via Modelfile or API `num_ctx` parameter (default 8192), not via environment variable.

VRAM budget for 5090 (24GB) with NUM_PARALLEL=2:
- Model weights: ~16GB
- 2x KV cache: ~4GB
- Headroom: ~4GB

---

## Node Gateway Service

### Responsibilities

| Function | Description |
|----------|-------------|
| Proxy | Receives OpenAI-compatible requests, forwards to local Ollama |
| Schema enforcement | instructor + Pydantic validates output matches requested schema |
| Retry | If Ollama returns malformed output, retry up to 2x |
| Fallback | If local fails 3x, route to Claude API (configurable) |
| Logging | Every request/response to llm_interactions table on .251 |
| Local queue | If .251 DB unreachable, queue to local SQLite, flush on reconnect |
| Heartbeat | Every 30s, POST health status to registry API |
| Self-registration | On startup, registers itself and its models with registry |
| Auth | Validates API key or Cloudflare JWT |
| Priority queue | Reorders requests by priority before forwarding to Ollama |
| Rate limiting | Per-user and per-agent limits |

### API Surface

```
POST /v1/chat/completions    <- OpenAI-compatible (main endpoint)
POST /v1/completions         <- OpenAI-compatible
POST /v1/embeddings          <- OpenAI-compatible
GET  /v1/models              <- list available models on this node
GET  /health                 <- node health + GPU status
GET  /metrics                <- Prometheus metrics
POST /admin/reload           <- pull/reload models
POST /admin/drain            <- graceful drain for updates
```

### Configuration (environment variables)

```
NODE_NAME=5090
NODE_HOST=10.0.0.54
GATEWAY_PORT=8100
OLLAMA_URL=http://localhost:11434          # or http://dhg-ollama:11434 on .251
REGISTRY_API_URL=http://10.0.0.251:8011
ANTHROPIC_API_KEY=sk-...
FALLBACK_ENABLED=true
FALLBACK_MODEL=claude-sonnet-4-20250514
GATEWAY_API_KEY=<shared-secret>            # for LAN-internal auth between agents and gateway
```

Note: Gateways do NOT connect directly to PostgreSQL. All data writes go through the registry API. This keeps schema knowledge centralized and avoids N external DB connections.

### Codebase Structure

```
dhg-inference-gateway/
├── gateway/
│   ├── __init__.py
│   ├── main.py              <- FastAPI app, routes
│   ├── config.py            <- env vars, node config
│   ├── ollama_client.py     <- proxy to local Ollama
│   ├── fallback.py          <- Claude API fallback logic
│   ├── validation.py        <- instructor + Pydantic schemas
│   ├── logging_api.py       <- write to llm_interactions via registry API
│   ├── logging_queue.py     <- local SQLite queue when .251 API is down
│   ├── heartbeat.py         <- background task, POST to registry
│   ├── registration.py      <- self-register on startup
│   ├── queue.py             <- priority queue + rate limiting
│   └── schemas/
│       ├── __init__.py
│       ├── ebay_listing.py
│       ├── clinical_note.py
│       └── base.py
├── tests/
│   ├── test_validation.py
│   ├── test_queue.py
│   ├── test_fallback.py
│   ├── test_logging.py
│   └── test_integration.py
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

### Dependencies

```
fastapi
uvicorn
instructor
pydantic
openai
anthropic
aiosqlite
httpx
prometheus-client
```

---

## Database Schema

All tables in registry-db on .251 (PostgreSQL, stored on /mnt/4tb).

### inference_nodes

```sql
CREATE TABLE inference_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_name VARCHAR(50) NOT NULL UNIQUE,
    host VARCHAR(255) NOT NULL,
    gateway_port INTEGER DEFAULT 8100,
    ollama_port INTEGER DEFAULT 11434,
    gpu_model VARCHAR(100),
    gpu_vram_gb INTEGER,
    ram_gb INTEGER,
    status VARCHAR(20) DEFAULT 'offline' CHECK (status IN ('online', 'offline', 'draining')),
    fallback_enabled BOOLEAN DEFAULT true,
    last_heartbeat TIMESTAMPTZ,
    registered_at TIMESTAMPTZ DEFAULT now(),
    metadata JSONB DEFAULT '{}'
);
```

### inference_models

```sql
CREATE TABLE inference_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID REFERENCES inference_nodes(id) ON DELETE CASCADE,
    model_name VARCHAR(255) NOT NULL,
    model_alias VARCHAR(100),
    task_types TEXT[] DEFAULT '{}',
    priority INTEGER DEFAULT 1,
    vram_usage_gb NUMERIC(4,1),
    loaded BOOLEAN DEFAULT false,
    max_context_length INTEGER,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(node_id, model_name)
);
```

### llm_interactions

```sql
CREATE TABLE llm_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT now(),
    user_id UUID,                                  -- nullable: system/agent calls have no user
    node_id UUID REFERENCES inference_nodes(id),
    model_name VARCHAR(255) NOT NULL,
    model_source VARCHAR(50) NOT NULL CHECK (model_source IN ('local_ollama', 'anthropic_api', 'google_api', 'openai_api')),
    model_digest VARCHAR(64),
    task_type VARCHAR(50),
    agent_name VARCHAR(100),
    session_id UUID,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    latency_ms INTEGER,
    input_hash VARCHAR(64),
    input_summary TEXT,
    input_has_image BOOLEAN DEFAULT false,
    output JSONB,
    output_validated BOOLEAN,
    output_schema_name VARCHAR(100),
    fallback_used BOOLEAN DEFAULT false,
    fallback_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    estimated_cost_usd NUMERIC(10,6),
    synced_at TIMESTAMPTZ                          -- when row was written to DB (for delayed flush tracking)
);

CREATE INDEX idx_llm_interactions_user ON llm_interactions(user_id);
CREATE INDEX idx_llm_interactions_node ON llm_interactions(node_id);
CREATE INDEX idx_llm_interactions_timestamp ON llm_interactions(timestamp);
CREATE INDEX idx_llm_interactions_task_type ON llm_interactions(task_type);
CREATE INDEX idx_llm_interactions_input_hash ON llm_interactions(input_hash);
```

### llm_quality_evals

```sql
CREATE TABLE llm_quality_evals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interaction_id UUID REFERENCES llm_interactions(id),
    grade INTEGER CHECK (grade BETWEEN 1 AND 5),
    criteria JSONB,
    issues TEXT[],
    graded_by VARCHAR(100),
    evaluated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_llm_quality_evals_interaction ON llm_quality_evals(interaction_id);
```

### model_update_log

```sql
CREATE TABLE model_update_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID REFERENCES inference_nodes(id),
    model_name VARCHAR(255),
    old_digest VARCHAR(64),
    new_digest VARCHAR(64),
    updated_at TIMESTAMPTZ DEFAULT now(),
    updated_by VARCHAR(100)
);
```

### routing_config

```sql
CREATE TABLE routing_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(100) NOT NULL UNIQUE,
    prefer VARCHAR(100) NOT NULL,
    fallback VARCHAR(100),
    enabled BOOLEAN DEFAULT true,
    updated_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO routing_config (task_type, prefer, fallback) VALUES
('medical_qa', 'local:medical', 'claude'),
('clinical_reasoning', 'claude', NULL),
('vision', 'local:vision', 'claude'),
('ebay_listing', 'local:vision', 'claude'),
('prose_quality', 'claude', NULL),
('compliance_review', 'claude', NULL),
('bulk_extraction', 'local:general', 'gemini'),
('embedding', 'local:embedding', 'openai'),
('general', 'local:general', 'claude');
```

---

## Registry API Endpoints

New endpoints added to registry-api on .251 (:8011):

```
GET  /api/v1/inference/models                   <- all available models across online nodes
GET  /api/v1/inference/models?task_type=medical  <- find model for specific task
GET  /api/v1/inference/nodes                    <- list all nodes with status
POST /api/v1/inference/nodes/register           <- gateway self-registers on startup
POST /api/v1/inference/nodes/heartbeat          <- gateway reports health every 30s
POST /api/v1/inference/nodes/drain              <- mark node as draining
POST /api/v1/inference/nodes/activate           <- bring node back online
POST /api/v1/inference/interactions             <- gateway logs request/response here (not direct DB)
GET  /api/v1/inference/interactions             <- query interaction history
```

---

## Routing Resolution

The routing_config `prefer` column uses the format `local:<alias>` where `<alias>` matches `inference_models.model_alias`. Resolution:

```
routing_config.prefer = "local:medical"
    -> query: SELECT n.host, n.gateway_port, m.model_name
       FROM inference_models m
       JOIN inference_nodes n ON m.node_id = n.id
       WHERE m.model_alias = 'medical'
       AND n.status = 'online'
       ORDER BY m.priority ASC
       LIMIT 1
    -> result: {host: "10.0.0.54", port: 8100, model: "meditron3:8b"}
```

Alias mapping:

| model_alias | model_name | node |
|-------------|-----------|------|
| medical | meditron3:8b | 5090 |
| vision | qwen2.5-vl:7b | Jason |
| general | qwen3:14b | .251 |
| embedding | nomic-embed-text | .251 |

---

## LLMRouter Integration

### Current State

LLMRouter in `langgraph_workflows/dhg-agents-cloud/src/agent.py` has hardcoded backends: ChatAnthropic, ChatGoogleGenerativeAI, ChatOllama with fixed OLLAMA_BASE_URL. This is the CURRENT production system (LangGraph-based).

Note: The legacy Docker-based agents in `agents/` are decommissioned (restart: "no") and use direct Ollama calls. These are NOT in scope — they will not be migrated.

### New State

LLMRouter queries registry API and routes by task type using routing_config table. Zero changes to the 13 LangGraph agent files. Agents keep calling llm_router.get_model(task_type). Only LLMRouter internals change.

Some agents currently hardcode `ChatAnthropic(model="claude-sonnet-4-20250514")` directly instead of using LLMRouter. These agents will continue using Claude for now. As confidence in local models grows (tracked by feedback loops), these can be migrated to LLMRouter one at a time.

### Routing Priority

1. Local model via gateway (free, private, fast)
2. Claude API (paid, highest quality)
3. Google Gemini API (paid, bulk tasks)

---

## Request Flow

```
1. Agent needs medical analysis
2. Agent calls: llm_router.get_model("medical_qa")
3. LLMRouter checks routing_config: prefer=local:medical, fallback=claude
4. LLMRouter calls: GET /api/v1/inference/models?task_type=medical
   -> Registry API returns: {node: "5090", host: "10.0.0.54", port: 8100}
5. LLMRouter returns ChatOpenAI(base_url="http://10.0.0.54:8100/v1")
6. Agent calls model as usual
7. Gateway on 5090:
   a. Validates auth
   b. Checks priority queue / rate limits
   c. Forwards to Ollama (localhost:11434)
   d. Ollama processes (NUM_PARALLEL=2)
   e. instructor/Pydantic validates output
   f. If invalid -> retry up to 2x
   g. If still invalid -> fallback to Claude API
   h. Logs to llm_interactions on .251
   i. Returns response
8. Agent receives response (same format as OpenAI API)
```

---

## Request Queuing and Concurrency

### Ollama Native Parallelism

Ollama supports parallel requests via OLLAMA_NUM_PARALLEL. Multiple requests for the same model are batched into a single GPU operation. Each parallel slot shares model weights but has its own KV cache.

- OLLAMA_NUM_PARALLEL=2: two concurrent, ~4GB extra VRAM
- ~20-40% latency increase per request under load, but 2x throughput
- OLLAMA_MAX_QUEUE=50: additional requests queued FIFO

### Gateway Priority Layer

Ollama queue is FIFO only. Gateway adds priority awareness:

| Priority | Task Types | Behavior |
|----------|------------|----------|
| 0 (highest) | medical | Send immediately |
| 1 | vision, interactive | Send immediately |
| 2 | general | Wait if GPU heavily loaded |
| 3 (lowest) | bulk | Wait for capacity |

Gateway also enforces:
- Request timeout: 120s max wait
- Auto-fallback when queue depth exceeds threshold
- Rate limits per user/agent

---

## Monitoring and Observability

### Gateway Prometheus Metrics

| Metric | Type |
|--------|------|
| gateway_requests_total{model, task_type, status} | Counter |
| gateway_latency_seconds{model, task_type} | Histogram |
| gateway_fallback_total{model, reason} | Counter |
| gateway_validation_failures{model, schema} | Counter |
| gateway_tokens_total{model, direction} | Counter |
| gateway_queue_depth | Gauge |
| gateway_queue_wait_seconds | Histogram |
| gateway_queue_rejected_total | Counter |
| ollama_gpu_memory_used_bytes | Gauge |
| ollama_model_loaded{model} | Gauge |

### Prometheus Scrape Config

Add to .251 prometheus.yml:

```yaml
- job_name: 'inference-gateway'
  scrape_interval: 15s
  static_configs:
    - targets:
      - '10.0.0.54:8100'
      - '10.0.0.x:8100'
```

### Grafana Dashboard: Inference Platform

- Top row: Total requests, fallback rate, avg latency
- Middle row: Per-node GPU usage, model status, queue depth
- Bottom row: Cost savings, per-user usage
- Alerts: Node offline > 2 min, fallback rate > 20%, queue > 10 sustained

### Cost Reporting

Monthly view comparing local token usage vs Claude API equivalent cost. Shows money saved by running requests locally.

---

## Feedback Loops

### Layer 1: Automated Quality Signals

Tracked in llm_interactions: schema validation pass/fail, fallback rate, retry count, latency, output length anomalies.

### Layer 2: LLM-as-Judge

Scheduled job on .251 samples 10 local outputs per task type per day. Claude grades on accuracy, completeness, safety (1-5). Results in llm_quality_evals.

### Layer 3: Human Feedback

Extend LLManager Review Inbox (/inbox). Low-confidence outputs flagged for review. Feedback stored in llm_quality_evals with graded_by=human.

### Layer 4: Routing Auto-Adjustment

Weekly cron checks average quality grade and fallback rate per task type. Alerts Stephen when local quality degrades below thresholds.

---

## Security

- All traffic on 10.0.0.0/24 LAN
- LAN-internal traffic: gateway validates shared API key (GATEWAY_API_KEY in .env)
- External traffic (if exposed): Cloudflare JWT validation
- user_id passed as header by calling agent, logged to llm_interactions (nullable for system calls)
- Medical tasks configurable with fallback=null (PHI never leaves local)
- API keys in .env files only

---

## Model Versioning

- llm_interactions records model_digest (SHA from Ollama) per request
- model_update_log tracks version changes per node
- Rollback via: ollama pull model@old-digest

---

## Graceful Drain

1. POST /api/v1/inference/nodes/drain -> status=draining
2. Registry stops routing new requests to node
3. In-flight requests complete
4. Wait for queue empty
5. Perform update
6. POST /api/v1/inference/nodes/activate -> status=online

---

## Rate Limiting

| Limit | Default |
|-------|---------|
| Per-user requests/min | 30 |
| Per-user tokens/day | 100K |
| Per-agent requests/min | 10 bulk, 30 interactive |

429 returned with Retry-After header.

---

## eBay App Connectivity

New app, not a LangGraph agent. eBay App Backend queries registry for vision model, calls gateway with image + prompt, validates against EbayListing Pydantic schema. Authenticates via API key or OAuth. user_id logged.

---

## Disaster Recovery

| Scenario | Behavior | Recovery |
|----------|----------|---------|
| Gateway crash | Systemd restarts, heartbeat stops, registry marks offline | Automatic |
| Ollama crash | Gateway returns 503, fallback to Claude | Automatic |
| WSL crash | Node offline | Manual WSL restart |
| .251 DB unreachable | Gateway queues to local SQLite | Auto-flush on reconnect |
| .251 down | Gateways cache routing for 1 hour | Manual .251 recovery |

---

## Model Update Strategy

1. Drain node
2. ollama pull model:tag
3. Run test suite
4. Compare quality vs previous digest
5. If good, activate
6. Roll to remaining nodes one at a time
7. Monitor 48 hours
8. Rollback if needed: ollama pull model@old-digest

---

## Testing

| Type | Scope |
|------|-------|
| Unit | Schema validation, queue logic, rate limiting |
| Integration | Gateway to Ollama round-trip |
| Schema | Every Pydantic schema with sample prompts |
| Fallback | Kill Ollama, verify Claude fallback |
| Queue | 25 concurrent requests, verify queuing |
| DB | Write to llm_interactions, verify fields |
| Offline | Disconnect .251, verify SQLite queue |

---

## Installation Targets

| Component | Install On | Method |
|-----------|-----------|--------|
| Ollama | 5090 WSL Ubuntu 24.04 (10.0.0.54) | Native install |
| Ollama | Jason machine WSL | Native install |
| Node Gateway | 5090 WSL (10.0.0.54) | Python venv + systemd |
| Node Gateway | Jason machine WSL | Python venv + systemd |
| DB tables | .251 registry-db (PostgreSQL) | SQL migration |
| Registry API endpoints | .251 registry-api (FastAPI) | Code update |
| LLMRouter update | .251 LangGraph agents | Code update |
| Prometheus config | .251 | Add scrape targets |
| Grafana dashboard | .251 | New dashboard |
| Meditron3-8B model | 5090 via ollama pull | Ollama |
| Qwen2.5-VL-7B model | Jason machine via ollama pull | Ollama |
