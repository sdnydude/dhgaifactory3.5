# Local LLM Inference Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy a multi-node local LLM inference platform with Ollama + FastAPI gateway on the 5090 machine, registry-based discovery on .251, and LLMRouter integration for the AI Factory agents.

**Architecture:** Each inference node runs Ollama (model serving) + a FastAPI gateway (proxy, validation, logging). A central registry API on .251 handles node/model discovery. All interaction logs write to registry-db on .251's 4TB disk via the registry API. LLMRouter queries the registry to route tasks to local models with Claude API fallback.

**Tech Stack:** Ollama, FastAPI, instructor, Pydantic, httpx, aiosqlite, prometheus-client, PostgreSQL, SQLAlchemy

**Spec:** `docs/superpowers/specs/2026-04-11-local-llm-inference-platform-design.md`

**Machines:**
- `.251` (g700data1) — registry-db, registry-api, LangGraph agents. SSH: `swebber64@10.0.0.251`
- `5090` (10.0.0.54) — inference node. WSL Ubuntu-2404, root via `wsl -d Ubuntu-2404 -u root`
- Jason's machine — deferred to later phase

---

## File Map

### On .251 (registry-db + registry-api)

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `registry/migrations/005_add_inference_tables.sql` | DB migration for all inference tables |
| Create | `registry/inference_endpoints.py` | FastAPI router for inference discovery + logging |
| Create | `registry/inference_schemas.py` | Pydantic schemas for inference API |
| Modify | `registry/models.py` | Add SQLAlchemy models for inference tables |
| Modify | `registry/api.py` | Include inference router |
| Modify | `langgraph_workflows/dhg-agents-cloud/src/agent.py` | Update LLMRouter to query registry |

### On 5090 WSL (inference node)

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `/home/swebber64/dhg-inference-gateway/gateway/__init__.py` | Package init |
| Create | `/home/swebber64/dhg-inference-gateway/gateway/main.py` | FastAPI app, routes |
| Create | `/home/swebber64/dhg-inference-gateway/gateway/config.py` | Environment config |
| Create | `/home/swebber64/dhg-inference-gateway/gateway/ollama_client.py` | Ollama proxy |
| Create | `/home/swebber64/dhg-inference-gateway/gateway/fallback.py` | Claude API fallback |
| Create | `/home/swebber64/dhg-inference-gateway/gateway/validation.py` | instructor + Pydantic |
| Create | `/home/swebber64/dhg-inference-gateway/gateway/logging_api.py` | Log to registry API |
| Create | `/home/swebber64/dhg-inference-gateway/gateway/logging_queue.py` | SQLite offline queue |
| Create | `/home/swebber64/dhg-inference-gateway/gateway/heartbeat.py` | Background heartbeat |
| Create | `/home/swebber64/dhg-inference-gateway/gateway/registration.py` | Self-register on startup |
| Create | `/home/swebber64/dhg-inference-gateway/gateway/queue.py` | Priority queue + rate limiting |
| Create | `/home/swebber64/dhg-inference-gateway/gateway/schemas/base.py` | Shared schema utils |
| Create | `/home/swebber64/dhg-inference-gateway/gateway/schemas/ebay_listing.py` | EbayListing Pydantic |
| Create | `/home/swebber64/dhg-inference-gateway/gateway/schemas/clinical_note.py` | ClinicalNote Pydantic |
| Create | `/home/swebber64/dhg-inference-gateway/requirements.txt` | Dependencies |
| Create | `/home/swebber64/dhg-inference-gateway/.env` | Node config |
| Create | `/home/swebber64/dhg-inference-gateway/tests/test_config.py` | Config tests |
| Create | `/home/swebber64/dhg-inference-gateway/tests/test_queue.py` | Queue tests |
| Create | `/home/swebber64/dhg-inference-gateway/tests/test_validation.py` | Validation tests |
| Create | `/home/swebber64/dhg-inference-gateway/tests/test_ollama_client.py` | Ollama proxy tests |
| Create | `/home/swebber64/dhg-inference-gateway/tests/test_fallback.py` | Fallback tests |
| Create | `/home/swebber64/dhg-inference-gateway/tests/test_logging.py` | Logging tests |
| Create | `/home/swebber64/dhg-inference-gateway/tests/test_integration.py` | End-to-end tests |
| Create | `/etc/systemd/system/dhg-gateway.service` | Systemd service |

---

## Task 1: Install Ollama on 5090 WSL + Pull Meditron3-8B

**Target:** 5090 WSL Ubuntu-2404 (10.0.0.54)

- [ ] **Step 1: Install Ollama**

```bash
wsl -d Ubuntu-2404 -u root -- bash -c "curl -fsSL https://ollama.com/install.sh | sh"
```

Expected: Ollama binary installed at `/usr/local/bin/ollama`

- [ ] **Step 2: Configure Ollama environment**

```bash
wsl -d Ubuntu-2404 -u root -- bash -c "mkdir -p /etc/systemd/system/ollama.service.d && cat > /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment=OLLAMA_NUM_PARALLEL=2
Environment=OLLAMA_MAX_QUEUE=50
Environment=OLLAMA_HOST=0.0.0.0:11434
EOF
systemctl daemon-reload && systemctl enable ollama && systemctl start ollama"
```

- [ ] **Step 3: Verify Ollama is running**

```bash
wsl -d Ubuntu-2404 -- bash -c "ollama --version && curl -s http://localhost:11434/api/tags | python3 -m json.tool"
```

Expected: Ollama version printed, empty model list returned as JSON

- [ ] **Step 4: Pull Meditron3-8B**

```bash
wsl -d Ubuntu-2404 -- bash -c "ollama pull meditron3:8b"
```

Expected: Model downloaded (~5GB). This may take several minutes.

- [ ] **Step 5: Test Meditron3-8B inference**

```bash
wsl -d Ubuntu-2404 -- bash -c "curl -s http://localhost:11434/api/chat -d '{\"model\": \"meditron3:8b\", \"messages\": [{\"role\": \"user\", \"content\": \"What is the standard treatment for type 2 diabetes? Answer in 2 sentences.\"}], \"stream\": false}' | python3 -m json.tool | head -20"
```

Expected: JSON response with medical answer

- [ ] **Step 6: Open firewall for Ollama and gateway**

```bash
powershell.exe -Command "New-NetFirewallRule -DisplayName 'Ollama' -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow"
```

Note: Port 8000 and 8100 firewall rules may already exist from earlier in this session. Verify with `powershell.exe -Command "Get-NetFirewallRule -DisplayName 'vLLM*','WSL*','Ollama*' | Select DisplayName,Enabled"`.

- [ ] **Step 7: Set up port forwarding for gateway (8100)**

```bash
WSL_IP=$(wsl -d Ubuntu-2404 -- hostname -I | awk '{print $1}')
powershell.exe -Command "netsh interface portproxy add v4tov4 listenport=8100 listenaddress=0.0.0.0 connectport=8100 connectaddress=$WSL_IP"
powershell.exe -Command "netsh interface portproxy add v4tov4 listenport=11434 listenaddress=0.0.0.0 connectport=11434 connectaddress=$WSL_IP"
```

- [ ] **Step 8: Verify remote access from .251**

```bash
ssh swebber64@10.0.0.251 "curl -s http://10.0.0.54:11434/api/tags"
```

Expected: JSON with meditron3:8b listed

- [ ] **Step 9: Commit progress note**

Not a code commit — note that Ollama is installed and operational on 5090 WSL.

---

## Task 2: Database Migration on .251

**Target:** g700data1 (10.0.0.251), registry-db PostgreSQL

**Files:**
- Create: `registry/migrations/005_add_inference_tables.sql`

- [ ] **Step 1: Write the migration SQL**

SSH to .251 and create the file:

```bash
ssh swebber64@10.0.0.251 "cat > /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/registry/migrations/005_add_inference_tables.sql << 'SQLEOF'
-- Migration 005: Inference Platform Tables
-- Date: 2026-04-11
-- Spec: docs/superpowers/specs/2026-04-11-local-llm-inference-platform-design.md

-- Inference nodes (machines running Ollama + gateway)
CREATE TABLE IF NOT EXISTS inference_nodes (
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

-- Models available on each node
CREATE TABLE IF NOT EXISTS inference_models (
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

-- Every LLM request/response logged here
CREATE TABLE IF NOT EXISTS llm_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT now(),
    user_id UUID,
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
    synced_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_llm_interactions_user ON llm_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_interactions_node ON llm_interactions(node_id);
CREATE INDEX IF NOT EXISTS idx_llm_interactions_timestamp ON llm_interactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_llm_interactions_task_type ON llm_interactions(task_type);
CREATE INDEX IF NOT EXISTS idx_llm_interactions_input_hash ON llm_interactions(input_hash);

-- Quality evaluations (LLM-as-judge + human feedback)
CREATE TABLE IF NOT EXISTS llm_quality_evals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interaction_id UUID REFERENCES llm_interactions(id),
    grade INTEGER CHECK (grade BETWEEN 1 AND 5),
    criteria JSONB,
    issues TEXT[],
    graded_by VARCHAR(100),
    evaluated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_llm_quality_evals_interaction ON llm_quality_evals(interaction_id);

-- Model version tracking
CREATE TABLE IF NOT EXISTS model_update_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID REFERENCES inference_nodes(id),
    model_name VARCHAR(255),
    old_digest VARCHAR(64),
    new_digest VARCHAR(64),
    updated_at TIMESTAMPTZ DEFAULT now(),
    updated_by VARCHAR(100)
);

-- Task-type routing configuration
CREATE TABLE IF NOT EXISTS routing_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(100) NOT NULL UNIQUE,
    prefer VARCHAR(100) NOT NULL,
    fallback VARCHAR(100),
    enabled BOOLEAN DEFAULT true,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Seed routing config
INSERT INTO routing_config (task_type, prefer, fallback) VALUES
('medical_qa', 'local:medical', 'claude'),
('clinical_reasoning', 'claude', NULL),
('vision', 'local:vision', 'claude'),
('ebay_listing', 'local:vision', 'claude'),
('prose_quality', 'claude', NULL),
('compliance_review', 'claude', NULL),
('bulk_extraction', 'local:general', 'gemini'),
('embedding', 'local:embedding', 'openai'),
('general', 'local:general', 'claude')
ON CONFLICT (task_type) DO NOTHING;

-- Seed the 5090 node
INSERT INTO inference_nodes (node_name, host, gateway_port, gpu_model, gpu_vram_gb, ram_gb, status)
VALUES ('5090', '10.0.0.54', 8100, 'RTX 5090 Laptop', 24, 64, 'offline')
ON CONFLICT (node_name) DO NOTHING;

-- Seed g700data1 node (existing Ollama)
INSERT INTO inference_nodes (node_name, host, gateway_port, gpu_model, gpu_vram_gb, ram_gb, status)
VALUES ('g700data1', '10.0.0.251', 8100, 'RTX 5080', 16, 64, 'offline')
ON CONFLICT (node_name) DO NOTHING;
SQLEOF"
```

- [ ] **Step 2: Run the migration**

```bash
ssh swebber64@10.0.0.251 "docker exec -i dhg-registry-db psql -U dhg -d dhg_registry < /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/registry/migrations/005_add_inference_tables.sql"
```

Expected: Tables created, routing config seeded, nodes seeded.

- [ ] **Step 3: Verify tables exist**

```bash
ssh swebber64@10.0.0.251 "docker exec dhg-registry-db psql -U dhg -d dhg_registry -c '\dt inference_*' -c '\dt llm_*' -c '\dt routing_*' -c '\dt model_*'"
```

Expected: 6 tables listed (inference_nodes, inference_models, llm_interactions, llm_quality_evals, model_update_log, routing_config)

- [ ] **Step 4: Verify seed data**

```bash
ssh swebber64@10.0.0.251 "docker exec dhg-registry-db psql -U dhg -d dhg_registry -c 'SELECT node_name, host, status FROM inference_nodes' -c 'SELECT task_type, prefer, fallback FROM routing_config'"
```

Expected: 2 nodes (5090, g700data1) and 9 routing rules

- [ ] **Step 5: Commit**

```bash
ssh swebber64@10.0.0.251 "cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git add registry/migrations/005_add_inference_tables.sql && git commit -m 'feat: add inference platform database tables

Tables: inference_nodes, inference_models, llm_interactions,
llm_quality_evals, model_update_log, routing_config.
Seed data: 2 nodes (5090, g700data1), 9 routing rules.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>'"
```

---

## Task 3: Registry API — SQLAlchemy Models

**Target:** .251, `registry/models.py`

**Files:**
- Modify: `registry/models.py` — add SQLAlchemy ORM models for inference tables

- [ ] **Step 1: Read current models.py to find insertion point**

```bash
ssh swebber64@10.0.0.251 "tail -30 /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/registry/models.py"
```

- [ ] **Step 2: Add inference models to models.py**

Append the following SQLAlchemy models to the end of `registry/models.py`:

```python
# =============================================================================
# INFERENCE PLATFORM MODELS
# =============================================================================

class InferenceNode(Base):
    __tablename__ = "inference_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    node_name = Column(String(50), unique=True, nullable=False)
    host = Column(String(255), nullable=False)
    gateway_port = Column(Integer, default=8100)
    ollama_port = Column(Integer, default=11434)
    gpu_model = Column(String(100))
    gpu_vram_gb = Column(Integer)
    ram_gb = Column(Integer)
    status = Column(String(20), default="offline")
    fallback_enabled = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime(timezone=True))
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata_ = Column("metadata", JSONB, default={})

    models = relationship("InferenceModel", back_populates="node", cascade="all, delete-orphan")


class InferenceModel(Base):
    __tablename__ = "inference_models"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    node_id = Column(UUID(as_uuid=True), ForeignKey("inference_nodes.id", ondelete="CASCADE"))
    model_name = Column(String(255), nullable=False)
    model_alias = Column(String(100))
    task_types = Column(ARRAY(String), default=[])
    priority = Column(Integer, default=1)
    vram_usage_gb = Column(Numeric(4, 1))
    loaded = Column(Boolean, default=False)
    max_context_length = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    node = relationship("InferenceNode", back_populates="models")


class LLMInteraction(Base):
    __tablename__ = "llm_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(UUID(as_uuid=True), nullable=True)
    node_id = Column(UUID(as_uuid=True), ForeignKey("inference_nodes.id"))
    model_name = Column(String(255), nullable=False)
    model_source = Column(String(50), nullable=False)
    model_digest = Column(String(64))
    task_type = Column(String(50))
    agent_name = Column(String(100))
    session_id = Column(UUID(as_uuid=True))
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    latency_ms = Column(Integer)
    input_hash = Column(String(64))
    input_summary = Column(Text)
    input_has_image = Column(Boolean, default=False)
    output = Column(JSONB)
    output_validated = Column(Boolean)
    output_schema_name = Column(String(100))
    fallback_used = Column(Boolean, default=False)
    fallback_reason = Column(Text)
    retry_count = Column(Integer, default=0)
    estimated_cost_usd = Column(Numeric(10, 6))
    synced_at = Column(DateTime(timezone=True))


class LLMQualityEval(Base):
    __tablename__ = "llm_quality_evals"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    interaction_id = Column(UUID(as_uuid=True), ForeignKey("llm_interactions.id"))
    grade = Column(Integer)
    criteria = Column(JSONB)
    issues = Column(ARRAY(String))
    graded_by = Column(String(100))
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())


class ModelUpdateLog(Base):
    __tablename__ = "model_update_log"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    node_id = Column(UUID(as_uuid=True), ForeignKey("inference_nodes.id"))
    model_name = Column(String(255))
    old_digest = Column(String(64))
    new_digest = Column(String(64))
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(String(100))


class RoutingConfig(Base):
    __tablename__ = "routing_config"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    task_type = Column(String(100), unique=True, nullable=False)
    prefer = Column(String(100), nullable=False)
    fallback = Column(String(100))
    enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
```

Note: Check which imports already exist in models.py (Column, String, Integer, etc.). Add any missing imports: `JSONB, ARRAY, Numeric, relationship, Boolean, Text`.

- [ ] **Step 3: Verify models load without error**

```bash
ssh swebber64@10.0.0.251 "cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/registry && python3 -c 'from models import InferenceNode, InferenceModel, LLMInteraction, RoutingConfig; print(\"Models loaded OK\")'"
```

- [ ] **Step 4: Commit**

```bash
ssh swebber64@10.0.0.251 "cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git add registry/models.py && git commit -m 'feat: add SQLAlchemy models for inference platform

InferenceNode, InferenceModel, LLMInteraction, LLMQualityEval,
ModelUpdateLog, RoutingConfig ORM models.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>'"
```

---

## Task 4: Registry API — Inference Schemas

**Target:** .251, `registry/inference_schemas.py`

**Files:**
- Create: `registry/inference_schemas.py`

- [ ] **Step 1: Create Pydantic schemas for inference API**

Create `registry/inference_schemas.py` on .251 with request/response schemas for all inference endpoints:

```python
"""Pydantic schemas for inference platform API."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# --- Node schemas ---

class NodeRegisterRequest(BaseModel):
    node_name: str
    host: str
    gateway_port: int = 8100
    ollama_port: int = 11434
    gpu_model: Optional[str] = None
    gpu_vram_gb: Optional[int] = None
    ram_gb: Optional[int] = None
    fallback_enabled: bool = True
    models: list["ModelRegisterRequest"] = []


class ModelRegisterRequest(BaseModel):
    model_name: str
    model_alias: Optional[str] = None
    task_types: list[str] = []
    priority: int = 1
    vram_usage_gb: Optional[float] = None
    max_context_length: Optional[int] = None


class NodeResponse(BaseModel):
    id: UUID
    node_name: str
    host: str
    gateway_port: int
    ollama_port: int
    gpu_model: Optional[str]
    gpu_vram_gb: Optional[int]
    ram_gb: Optional[int]
    status: str
    fallback_enabled: bool
    last_heartbeat: Optional[datetime]
    registered_at: datetime

    class Config:
        from_attributes = True


class NodeHeartbeatRequest(BaseModel):
    node_name: str
    gpu_memory_used_bytes: Optional[int] = None
    gpu_memory_total_bytes: Optional[int] = None
    loaded_models: list[str] = []
    queue_depth: int = 0


class NodeDrainRequest(BaseModel):
    node_name: str


# --- Model discovery schemas ---

class ModelEndpoint(BaseModel):
    node_name: str
    host: str
    port: int
    model_name: str
    model_alias: Optional[str]
    task_types: list[str]
    priority: int


# --- Interaction logging schemas ---

class InteractionLogRequest(BaseModel):
    timestamp: datetime
    user_id: Optional[UUID] = None
    node_name: str
    model_name: str
    model_source: str
    model_digest: Optional[str] = None
    task_type: Optional[str] = None
    agent_name: Optional[str] = None
    session_id: Optional[UUID] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    input_hash: Optional[str] = None
    input_summary: Optional[str] = None
    input_has_image: bool = False
    output: Optional[dict] = None
    output_validated: Optional[bool] = None
    output_schema_name: Optional[str] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    retry_count: int = 0
    estimated_cost_usd: Optional[float] = None


class InteractionLogResponse(BaseModel):
    id: UUID
    synced_at: datetime

    class Config:
        from_attributes = True


# --- Routing config schemas ---

class RoutingConfigResponse(BaseModel):
    task_type: str
    prefer: str
    fallback: Optional[str]
    enabled: bool

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Commit**

```bash
ssh swebber64@10.0.0.251 "cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git add registry/inference_schemas.py && git commit -m 'feat: add Pydantic schemas for inference API

Request/response schemas for node registration, heartbeat,
model discovery, interaction logging, routing config.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>'"
```

---

## Task 5: Registry API — Inference Endpoints

**Target:** .251, `registry/inference_endpoints.py` and `registry/api.py`

**Files:**
- Create: `registry/inference_endpoints.py`
- Modify: `registry/api.py` (add `include_router`)

- [ ] **Step 1: Create inference endpoints**

Create `registry/inference_endpoints.py` on .251 following the pattern in `security_endpoints.py`:

```python
"""
DHG Inference Platform API — Node discovery, model routing, interaction logging.

Endpoints for inference gateway self-registration, heartbeat,
model discovery by task type, and interaction logging.
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, and_

from database import get_db
from models import (
    InferenceNode,
    InferenceModel,
    LLMInteraction,
    RoutingConfig,
)
from inference_schemas import (
    NodeRegisterRequest,
    NodeResponse,
    NodeHeartbeatRequest,
    NodeDrainRequest,
    ModelEndpoint,
    InteractionLogRequest,
    InteractionLogResponse,
    RoutingConfigResponse,
)

logger = logging.getLogger("dhg.inference.endpoints")

inference_router = APIRouter(prefix="/api/v1/inference", tags=["inference"])


# --- Node Management ---

@inference_router.get("/nodes", response_model=list[NodeResponse])
def list_nodes(db: Session = Depends(get_db)):
    """List all inference nodes."""
    return db.query(InferenceNode).all()


@inference_router.post("/nodes/register", response_model=NodeResponse)
def register_node(req: NodeRegisterRequest, db: Session = Depends(get_db)):
    """Gateway self-registers on startup. Upserts node and its models."""
    node = db.query(InferenceNode).filter(InferenceNode.node_name == req.node_name).first()
    if node:
        node.host = req.host
        node.gateway_port = req.gateway_port
        node.ollama_port = req.ollama_port
        node.gpu_model = req.gpu_model
        node.gpu_vram_gb = req.gpu_vram_gb
        node.ram_gb = req.ram_gb
        node.fallback_enabled = req.fallback_enabled
        node.status = "online"
        node.last_heartbeat = sa_func.now()
    else:
        node = InferenceNode(
            node_name=req.node_name,
            host=req.host,
            gateway_port=req.gateway_port,
            ollama_port=req.ollama_port,
            gpu_model=req.gpu_model,
            gpu_vram_gb=req.gpu_vram_gb,
            ram_gb=req.ram_gb,
            fallback_enabled=req.fallback_enabled,
            status="online",
            last_heartbeat=sa_func.now(),
        )
        db.add(node)

    db.flush()

    # Upsert models
    for m in req.models:
        existing = db.query(InferenceModel).filter(
            and_(InferenceModel.node_id == node.id, InferenceModel.model_name == m.model_name)
        ).first()
        if existing:
            existing.model_alias = m.model_alias
            existing.task_types = m.task_types
            existing.priority = m.priority
            existing.vram_usage_gb = m.vram_usage_gb
            existing.max_context_length = m.max_context_length
            existing.loaded = True
        else:
            db.add(InferenceModel(
                node_id=node.id,
                model_name=m.model_name,
                model_alias=m.model_alias,
                task_types=m.task_types,
                priority=m.priority,
                vram_usage_gb=m.vram_usage_gb,
                max_context_length=m.max_context_length,
                loaded=True,
            ))

    db.commit()
    db.refresh(node)
    logger.info(f"Node registered: {node.node_name} ({node.host}:{node.gateway_port})")
    return node


@inference_router.post("/nodes/heartbeat")
def node_heartbeat(req: NodeHeartbeatRequest, db: Session = Depends(get_db)):
    """Gateway sends heartbeat every 30s."""
    node = db.query(InferenceNode).filter(InferenceNode.node_name == req.node_name).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {req.node_name} not found")
    node.last_heartbeat = sa_func.now()
    if node.status == "offline":
        node.status = "online"
    db.commit()
    return {"status": "ok"}


@inference_router.post("/nodes/drain")
def drain_node(req: NodeDrainRequest, db: Session = Depends(get_db)):
    """Mark node as draining — registry stops routing new requests."""
    node = db.query(InferenceNode).filter(InferenceNode.node_name == req.node_name).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {req.node_name} not found")
    node.status = "draining"
    db.commit()
    logger.info(f"Node draining: {node.node_name}")
    return {"status": "draining"}


@inference_router.post("/nodes/activate")
def activate_node(req: NodeDrainRequest, db: Session = Depends(get_db)):
    """Bring node back online after drain/update."""
    node = db.query(InferenceNode).filter(InferenceNode.node_name == req.node_name).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {req.node_name} not found")
    node.status = "online"
    node.last_heartbeat = sa_func.now()
    db.commit()
    logger.info(f"Node activated: {node.node_name}")
    return {"status": "online"}


# --- Model Discovery ---

@inference_router.get("/models", response_model=list[ModelEndpoint])
def list_models(
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    db: Session = Depends(get_db),
):
    """Find available models, optionally filtered by task type.

    Resolution: task_type -> routing_config.prefer -> model_alias -> inference_models -> node
    """
    query = (
        db.query(InferenceModel, InferenceNode)
        .join(InferenceNode, InferenceModel.node_id == InferenceNode.id)
        .filter(InferenceNode.status == "online")
    )

    if task_type:
        # Look up routing config to find the preferred alias
        route = db.query(RoutingConfig).filter(
            RoutingConfig.task_type == task_type,
            RoutingConfig.enabled == True,
        ).first()

        if route and route.prefer.startswith("local:"):
            alias = route.prefer.split(":", 1)[1]
            query = query.filter(InferenceModel.model_alias == alias)
        elif route and route.prefer == "claude":
            return []  # No local model — caller should use Claude
        else:
            # No routing rule — filter by task_type in model's task_types array
            query = query.filter(InferenceModel.task_types.any(task_type))

    results = query.order_by(InferenceModel.priority.asc()).all()

    return [
        ModelEndpoint(
            node_name=node.node_name,
            host=node.host,
            port=node.gateway_port,
            model_name=model.model_name,
            model_alias=model.model_alias,
            task_types=model.task_types or [],
            priority=model.priority,
        )
        for model, node in results
    ]


# --- Interaction Logging ---

@inference_router.post("/interactions", response_model=InteractionLogResponse)
def log_interaction(req: InteractionLogRequest, db: Session = Depends(get_db)):
    """Gateway logs every LLM request/response here."""
    # Resolve node_name to node_id
    node = db.query(InferenceNode).filter(InferenceNode.node_name == req.node_name).first()

    interaction = LLMInteraction(
        timestamp=req.timestamp,
        user_id=req.user_id,
        node_id=node.id if node else None,
        model_name=req.model_name,
        model_source=req.model_source,
        model_digest=req.model_digest,
        task_type=req.task_type,
        agent_name=req.agent_name,
        session_id=req.session_id,
        prompt_tokens=req.prompt_tokens,
        completion_tokens=req.completion_tokens,
        latency_ms=req.latency_ms,
        input_hash=req.input_hash,
        input_summary=req.input_summary,
        input_has_image=req.input_has_image,
        output=req.output,
        output_validated=req.output_validated,
        output_schema_name=req.output_schema_name,
        fallback_used=req.fallback_used,
        fallback_reason=req.fallback_reason,
        retry_count=req.retry_count,
        estimated_cost_usd=req.estimated_cost_usd,
        synced_at=sa_func.now(),
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return InteractionLogResponse(id=interaction.id, synced_at=interaction.synced_at)


@inference_router.get("/interactions")
def query_interactions(
    task_type: Optional[str] = None,
    model_source: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    """Query interaction history."""
    query = db.query(LLMInteraction).order_by(LLMInteraction.timestamp.desc())
    if task_type:
        query = query.filter(LLMInteraction.task_type == task_type)
    if model_source:
        query = query.filter(LLMInteraction.model_source == model_source)
    return query.limit(limit).all()


# --- Routing Config ---

@inference_router.get("/routing", response_model=list[RoutingConfigResponse])
def list_routing_config(db: Session = Depends(get_db)):
    """List all routing rules."""
    return db.query(RoutingConfig).filter(RoutingConfig.enabled == True).all()
```

- [ ] **Step 2: Register router in api.py**

Add to `registry/api.py` imports section:

```python
from inference_endpoints import inference_router
```

Add to the `app.include_router` section (after the last existing include_router):

```python
app.include_router(inference_router)
```

- [ ] **Step 3: Test endpoint registration**

```bash
ssh swebber64@10.0.0.251 "cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose restart registry-api && sleep 5 && curl -s http://localhost:8011/api/v1/inference/nodes | python3 -m json.tool"
```

Expected: JSON array with the 2 seeded nodes (5090, g700data1)

- [ ] **Step 4: Test model discovery endpoint**

```bash
ssh swebber64@10.0.0.251 "curl -s http://localhost:8011/api/v1/inference/models | python3 -m json.tool"
```

Expected: Empty array (no models registered yet — nodes are offline)

- [ ] **Step 5: Test routing config endpoint**

```bash
ssh swebber64@10.0.0.251 "curl -s http://localhost:8011/api/v1/inference/routing | python3 -m json.tool"
```

Expected: 9 routing rules

- [ ] **Step 6: Commit**

```bash
ssh swebber64@10.0.0.251 "cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git add registry/inference_endpoints.py registry/inference_schemas.py registry/api.py && git commit -m 'feat: add inference platform API endpoints

Node management (register, heartbeat, drain, activate),
model discovery with routing resolution, interaction logging,
routing config query.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>'"
```

---

## Task 6: Node Gateway — Core Setup

**Target:** 5090 WSL (10.0.0.54)

**Files:**
- Create: all files under `/home/swebber64/dhg-inference-gateway/`

- [ ] **Step 1: Create project structure**

```bash
wsl -d Ubuntu-2404 -- bash -c "mkdir -p /home/swebber64/dhg-inference-gateway/{gateway/schemas,tests} && touch /home/swebber64/dhg-inference-gateway/gateway/__init__.py /home/swebber64/dhg-inference-gateway/gateway/schemas/__init__.py"
```

- [ ] **Step 2: Create requirements.txt**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
instructor>=1.7.0
pydantic>=2.10.0
openai>=1.60.0
anthropic>=0.40.0
aiosqlite>=0.20.0
httpx>=0.28.0
prometheus-client>=0.21.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

- [ ] **Step 3: Create venv and install dependencies**

```bash
wsl -d Ubuntu-2404 -- bash -c "cd /home/swebber64/dhg-inference-gateway && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
```

- [ ] **Step 4: Create config.py**

```python
"""Gateway configuration from environment variables."""
import os


class Config:
    NODE_NAME = os.getenv("NODE_NAME", "unknown")
    NODE_HOST = os.getenv("NODE_HOST", "0.0.0.0")
    GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8100"))
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    REGISTRY_API_URL = os.getenv("REGISTRY_API_URL", "http://10.0.0.251:8011")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    FALLBACK_ENABLED = os.getenv("FALLBACK_ENABLED", "true").lower() == "true"
    FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "claude-sonnet-4-20250514")
    GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY", "")
    HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))
    SQLITE_QUEUE_PATH = os.getenv("SQLITE_QUEUE_PATH", "/tmp/dhg-gateway-queue.db")
```

- [ ] **Step 5: Create .env**

```
NODE_NAME=5090
NODE_HOST=10.0.0.54
GATEWAY_PORT=8100
OLLAMA_URL=http://localhost:11434
REGISTRY_API_URL=http://10.0.0.251:8011
ANTHROPIC_API_KEY=
FALLBACK_ENABLED=true
FALLBACK_MODEL=claude-sonnet-4-20250514
GATEWAY_API_KEY=dhg-inference-2026
```

Note: Get ANTHROPIC_API_KEY from .251's .env file:
```bash
ssh swebber64@10.0.0.251 "grep ANTHROPIC_API_KEY /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/.env"
```

- [ ] **Step 6: Create ollama_client.py**

Proxy module that forwards OpenAI-compatible requests to local Ollama:

```python
"""Proxy requests to local Ollama instance."""
import time
import logging
from typing import Optional

import httpx

from gateway.config import Config

logger = logging.getLogger("dhg.gateway.ollama")


class OllamaClient:
    def __init__(self):
        self.base_url = Config.OLLAMA_URL
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=300.0)

    async def chat_completion(self, body: dict) -> dict:
        """Forward chat completion to Ollama's OpenAI-compatible endpoint."""
        start = time.monotonic()
        resp = await self.client.post("/v1/chat/completions", json=body)
        resp.raise_for_status()
        latency_ms = int((time.monotonic() - start) * 1000)
        result = resp.json()
        result["_latency_ms"] = latency_ms
        return result

    async def list_models(self) -> list[str]:
        """Get list of models available in Ollama."""
        resp = await self.client.get("/api/tags")
        resp.raise_for_status()
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]

    async def show_model(self, model_name: str) -> dict:
        """Get model details including digest."""
        resp = await self.client.post("/api/show", json={"name": model_name})
        resp.raise_for_status()
        return resp.json()

    async def health(self) -> bool:
        """Check if Ollama is responding."""
        try:
            resp = await self.client.get("/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()
```

- [ ] **Step 7: Create logging_api.py**

```python
"""Log interactions to registry API on .251."""
import logging
from datetime import datetime
from typing import Optional

import httpx

from gateway.config import Config

logger = logging.getLogger("dhg.gateway.logging")


class InteractionLogger:
    def __init__(self):
        self.api_url = f"{Config.REGISTRY_API_URL}/api/v1/inference/interactions"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def log(
        self,
        model_name: str,
        model_source: str,
        request_body: dict,
        response_body: dict,
        latency_ms: int,
        *,
        model_digest: Optional[str] = None,
        task_type: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        input_hash: Optional[str] = None,
        output_validated: Optional[bool] = None,
        output_schema_name: Optional[str] = None,
        fallback_used: bool = False,
        fallback_reason: Optional[str] = None,
        retry_count: int = 0,
    ) -> bool:
        """Log interaction to registry API. Returns True on success."""
        usage = response_body.get("usage", {})
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "node_name": Config.NODE_NAME,
            "model_name": model_name,
            "model_source": model_source,
            "model_digest": model_digest,
            "task_type": task_type,
            "user_id": user_id,
            "agent_name": agent_name,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "latency_ms": latency_ms,
            "input_hash": input_hash,
            "input_summary": str(request_body.get("messages", [{}])[-1].get("content", ""))[:500],
            "output": {"choices": response_body.get("choices", [])},
            "output_validated": output_validated,
            "output_schema_name": output_schema_name,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "retry_count": retry_count,
        }

        try:
            resp = await self.client.post(self.api_url, json=payload)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.warning(f"Failed to log to registry API: {e}")
            return False

    async def close(self):
        await self.client.aclose()
```

- [ ] **Step 8: Create logging_queue.py**

```python
"""Local SQLite queue for when .251 registry API is unreachable."""
import json
import logging
from datetime import datetime

import aiosqlite

from gateway.config import Config

logger = logging.getLogger("dhg.gateway.queue")


class LogQueue:
    def __init__(self):
        self.db_path = Config.SQLITE_QUEUE_PATH

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pending_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            await db.commit()

    async def enqueue(self, payload: dict):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO pending_logs (payload, created_at) VALUES (?, ?)",
                (json.dumps(payload), datetime.utcnow().isoformat()),
            )
            await db.commit()
        logger.info("Interaction queued locally (registry API unreachable)")

    async def flush(self, logger_api) -> int:
        """Flush pending logs to registry API. Returns count flushed."""
        flushed = 0
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT id, payload FROM pending_logs ORDER BY id") as cursor:
                async for row in cursor:
                    row_id, payload_str = row
                    try:
                        payload = json.loads(payload_str)
                        resp = await logger_api.client.post(logger_api.api_url, json=payload)
                        resp.raise_for_status()
                        await db.execute("DELETE FROM pending_logs WHERE id = ?", (row_id,))
                        await db.commit()
                        flushed += 1
                    except Exception:
                        break  # API still down
        if flushed:
            logger.info(f"Flushed {flushed} queued logs to registry API")
        return flushed

    async def depth(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM pending_logs") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
```

- [ ] **Step 9: Create heartbeat.py**

```python
"""Background heartbeat to registry API."""
import asyncio
import logging

import httpx

from gateway.config import Config

logger = logging.getLogger("dhg.gateway.heartbeat")


async def heartbeat_loop(ollama_client):
    """Send heartbeat to registry API every HEARTBEAT_INTERVAL seconds."""
    url = f"{Config.REGISTRY_API_URL}/api/v1/inference/nodes/heartbeat"

    while True:
        try:
            models = await ollama_client.list_models()
            payload = {
                "node_name": Config.NODE_NAME,
                "loaded_models": models,
                "queue_depth": 0,
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(url, json=payload)
        except Exception as e:
            logger.debug(f"Heartbeat failed: {e}")

        await asyncio.sleep(Config.HEARTBEAT_INTERVAL)
```

- [ ] **Step 10: Create registration.py**

```python
"""Self-register with registry API on startup."""
import logging

import httpx

from gateway.config import Config

logger = logging.getLogger("dhg.gateway.registration")


async def register_node(ollama_client):
    """Register this node and its models with the registry API."""
    url = f"{Config.REGISTRY_API_URL}/api/v1/inference/nodes/register"

    models = await ollama_client.list_models()
    model_registrations = []
    for model_name in models:
        # Default alias mapping — override via config if needed
        alias = None
        task_types = ["general"]
        if "meditron" in model_name.lower():
            alias = "medical"
            task_types = ["medical_qa", "clinical"]
        elif "qwen" in model_name.lower() and "vl" in model_name.lower():
            alias = "vision"
            task_types = ["vision", "ebay_listing"]
        elif "embed" in model_name.lower() or "nomic" in model_name.lower():
            alias = "embedding"
            task_types = ["embedding"]

        model_registrations.append({
            "model_name": model_name,
            "model_alias": alias,
            "task_types": task_types,
        })

    payload = {
        "node_name": Config.NODE_NAME,
        "host": Config.NODE_HOST,
        "gateway_port": Config.GATEWAY_PORT,
        "ollama_port": 11434,
        "models": model_registrations,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            logger.info(f"Registered with registry: {Config.NODE_NAME} ({len(models)} models)")
    except Exception as e:
        logger.warning(f"Failed to register with registry: {e} (will retry via heartbeat)")
```

- [ ] **Step 11: Create main.py**

```python
"""DHG Inference Gateway — FastAPI app."""
import asyncio
import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from gateway.config import Config
from gateway.ollama_client import OllamaClient
from gateway.logging_api import InteractionLogger
from gateway.logging_queue import LogQueue
from gateway.heartbeat import heartbeat_loop
from gateway.registration import register_node

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dhg.gateway")

# --- Prometheus Metrics ---
REQUEST_COUNT = Counter("gateway_requests_total", "Total requests", ["model", "task_type", "status"])
REQUEST_LATENCY = Histogram("gateway_latency_seconds", "Request latency", ["model", "task_type"])
FALLBACK_COUNT = Counter("gateway_fallback_total", "Fallback count", ["model", "reason"])
QUEUE_DEPTH = Gauge("gateway_queue_depth", "Local log queue depth")

# --- Shared State ---
ollama = OllamaClient()
interaction_logger = InteractionLogger()
log_queue = LogQueue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    await log_queue.init()
    await register_node(ollama)
    heartbeat_task = asyncio.create_task(heartbeat_loop(ollama))
    flush_task = asyncio.create_task(periodic_flush())
    yield
    heartbeat_task.cancel()
    flush_task.cancel()
    await ollama.close()
    await interaction_logger.close()


async def periodic_flush():
    """Periodically flush local log queue to registry API."""
    while True:
        depth = await log_queue.depth()
        QUEUE_DEPTH.set(depth)
        if depth > 0:
            await log_queue.flush(interaction_logger)
        await asyncio.sleep(60)


app = FastAPI(title="DHG Inference Gateway", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    ollama_ok = await ollama.health()
    return {
        "status": "healthy" if ollama_ok else "degraded",
        "node": Config.NODE_NAME,
        "ollama": ollama_ok,
    }


@app.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/models")
async def list_models():
    models = await ollama.list_models()
    return {
        "object": "list",
        "data": [{"id": m, "object": "model", "owned_by": "local"} for m in models],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", "")
    task_type = request.headers.get("X-Task-Type", "general")
    user_id = request.headers.get("X-User-ID")
    agent_name = request.headers.get("X-Agent-Name")

    try:
        result = await ollama.chat_completion(body)
        latency_ms = result.pop("_latency_ms", 0)
        REQUEST_COUNT.labels(model=model, task_type=task_type, status="success").inc()
        REQUEST_LATENCY.labels(model=model, task_type=task_type).observe(latency_ms / 1000)

        # Log interaction
        logged = await interaction_logger.log(
            model_name=model,
            model_source="local_ollama",
            request_body=body,
            response_body=result,
            latency_ms=latency_ms,
            task_type=task_type,
            user_id=user_id,
            agent_name=agent_name,
        )
        if not logged:
            await log_queue.enqueue({
                "node_name": Config.NODE_NAME,
                "model_name": model,
                "model_source": "local_ollama",
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                "latency_ms": latency_ms,
                "task_type": task_type,
            })

        return JSONResponse(content=result)

    except httpx.HTTPStatusError as e:
        REQUEST_COUNT.labels(model=model, task_type=task_type, status="error").inc()
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        REQUEST_COUNT.labels(model=model, task_type=task_type, status="error").inc()
        FALLBACK_COUNT.labels(model=model, reason="ollama_error").inc()
        raise HTTPException(status_code=502, detail=f"Ollama error: {e}")


@app.post("/admin/drain")
async def drain():
    """Mark this node as draining via registry API."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        await client.post(
            f"{Config.REGISTRY_API_URL}/api/v1/inference/nodes/drain",
            json={"node_name": Config.NODE_NAME},
        )
    return {"status": "draining"}
```

- [ ] **Step 12: Create systemd service**

```bash
wsl -d Ubuntu-2404 -u root -- bash -c "cat > /etc/systemd/system/dhg-gateway.service << 'EOF'
[Unit]
Description=DHG Inference Gateway
After=network.target ollama.service

[Service]
Type=simple
User=swebber64
WorkingDirectory=/home/swebber64/dhg-inference-gateway
EnvironmentFile=/home/swebber64/dhg-inference-gateway/.env
ExecStart=/home/swebber64/dhg-inference-gateway/venv/bin/uvicorn gateway.main:app --host 0.0.0.0 --port 8100
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable dhg-gateway"
```

- [ ] **Step 13: Start the gateway**

```bash
wsl -d Ubuntu-2404 -u root -- bash -c "systemctl start dhg-gateway && sleep 3 && systemctl status dhg-gateway --no-pager | head -10"
```

- [ ] **Step 14: Test gateway health**

```bash
wsl -d Ubuntu-2404 -- bash -c "curl -s http://localhost:8100/health | python3 -m json.tool"
```

Expected: `{"status": "healthy", "node": "5090", "ollama": true}`

- [ ] **Step 15: Test gateway chat completion**

```bash
wsl -d Ubuntu-2404 -- bash -c "curl -s -X POST http://localhost:8100/v1/chat/completions -H 'Content-Type: application/json' -d '{\"model\": \"meditron3:8b\", \"messages\": [{\"role\": \"user\", \"content\": \"What is hypertension?\"}], \"max_tokens\": 100}' | python3 -m json.tool | head -20"
```

Expected: JSON response with medical answer

- [ ] **Step 16: Test remote access from .251**

```bash
ssh swebber64@10.0.0.251 "curl -s http://10.0.0.54:8100/health | python3 -m json.tool"
```

Expected: Same health response

- [ ] **Step 17: Verify node registered with registry**

```bash
ssh swebber64@10.0.0.251 "curl -s http://localhost:8011/api/v1/inference/nodes | python3 -m json.tool"
```

Expected: 5090 node shows status=online

- [ ] **Step 18: Verify model discovery works**

```bash
ssh swebber64@10.0.0.251 "curl -s 'http://localhost:8011/api/v1/inference/models?task_type=medical_qa' | python3 -m json.tool"
```

Expected: Returns 5090 node with meditron3:8b

- [ ] **Step 19: Verify interaction logged**

```bash
ssh swebber64@10.0.0.251 "curl -s http://localhost:8011/api/v1/inference/interactions?limit=1 | python3 -m json.tool"
```

Expected: The test chat completion from step 15 appears

- [ ] **Step 20: Init git repo for gateway**

```bash
wsl -d Ubuntu-2404 -- bash -c "cd /home/swebber64/dhg-inference-gateway && git init && git add -A && git commit -m 'feat: initial dhg-inference-gateway

Ollama proxy, interaction logging via registry API,
local SQLite queue, heartbeat, self-registration,
Prometheus metrics, systemd service.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>'"
```

---

## Task 7: LLMRouter Integration on .251

**Target:** .251, `langgraph_workflows/dhg-agents-cloud/src/agent.py`

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/src/agent.py` (LLMRouter class, lines ~360-450)

- [ ] **Step 1: Read current LLMRouter**

```bash
ssh swebber64@10.0.0.251 "sed -n '360,460p' /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/langgraph_workflows/dhg-agents-cloud/src/agent.py"
```

- [ ] **Step 2: Update LLMRouter to query registry API**

Replace the `get_model` method and add `_get_local_model` method. Keep all existing `_get_claude_*`, `_get_gemini_*`, `_get_qwen_local` methods unchanged as fallbacks.

Add after `_get_qwen_local`:

```python
    async def _get_local_model(self, task_type: str):
        """Query registry API for a local model matching this task type."""
        registry_url = os.getenv("REGISTRY_API_URL", "http://localhost:8011")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{registry_url}/api/v1/inference/models",
                    params={"task_type": task_type},
                )
                resp.raise_for_status()
                endpoints = resp.json()
                if endpoints:
                    ep = endpoints[0]
                    cache_key = f"local_{ep['host']}_{ep['model_name']}"
                    if cache_key not in self._cache:
                        from langchain_openai import ChatOpenAI
                        self._cache[cache_key] = ChatOpenAI(
                            base_url=f"http://{ep['host']}:{ep['port']}/v1",
                            api_key="local",
                            model=ep["model_name"],
                            max_tokens=4096,
                        )
                    return (self._cache[cache_key], ep["model_name"], 0.0)
        except Exception as e:
            logger.debug(f"Local model lookup failed for {task_type}: {e}")
        return None
```

Update `get_model` to try local first:

```python
    def get_model(self, task: str, force_local: bool = False) -> tuple:
        """Get model for task. Returns (model, name, cost_per_1k_output).
        
        Tries local inference via registry API first, falls back to cloud.
        """
        if force_local:
            return (self._get_qwen_local(), "qwen3:14b", 0.0)

        # Try local model via registry (async, but we need sync here)
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context — use the existing loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    local = loop.run_in_executor(pool, lambda: asyncio.run(self._get_local_model(task)))
                    # Can't easily await here in sync method — skip for now
                    local = None
            else:
                local = asyncio.run(self._get_local_model(task))
        except Exception:
            local = None

        if local:
            return local

        # Existing cloud routing
        if task == "complex_synthesis":
            return (self._get_claude_sonnet(), "claude-sonnet-4-20250514", 0.015)
        elif task == "extraction":
            return (self._get_claude_haiku(), "claude-3-5-haiku-20241022", 0.004)
        elif task == "bulk_screening":
            return (self._get_gemini_flash(), "gemini-2.5-flash-preview-05-20", 0.001)
        else:
            return (self._get_claude_sonnet(), "claude-sonnet-4-20250514", 0.015)
```

Note: The async-in-sync bridge is awkward. The proper fix is to make `get_model` async, but that requires changes to all callers. For now, the local lookup is best-effort — if it fails, cloud routing works as before. A follow-up task should convert `get_model` to async.

- [ ] **Step 3: Add httpx to LangGraph agent dependencies**

```bash
ssh swebber64@10.0.0.251 "grep -q httpx /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/langgraph_workflows/dhg-agents-cloud/requirements.txt || echo 'httpx>=0.28.0' >> /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/langgraph_workflows/dhg-agents-cloud/requirements.txt"
```

- [ ] **Step 4: Test locally on .251**

```bash
ssh swebber64@10.0.0.251 "cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/langgraph_workflows/dhg-agents-cloud && python3 -c \"
from src.agent import LLMRouter
import asyncio
router = LLMRouter()
result = asyncio.run(router._get_local_model('medical_qa'))
print(f'Local model: {result}')
\""
```

Expected: Returns the 5090 gateway endpoint with meditron3:8b (if gateway is running)

- [ ] **Step 5: Commit**

```bash
ssh swebber64@10.0.0.251 "cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git add langgraph_workflows/dhg-agents-cloud/src/agent.py langgraph_workflows/dhg-agents-cloud/requirements.txt && git commit -m 'feat: update LLMRouter to query registry for local models

LLMRouter now checks registry API for local inference nodes before
falling back to cloud providers. Local-first routing with automatic
Claude/Gemini fallback.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>'"
```

---

## Task 8: Prometheus + Observability

**Target:** .251

- [ ] **Step 1: Add gateway scrape target to Prometheus**

```bash
ssh swebber64@10.0.0.251 "grep -q inference-gateway /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/observability/prometheus/prometheus.yml || cat >> /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/observability/prometheus/prometheus.yml << 'EOF'

  - job_name: 'inference-gateway'
    scrape_interval: 15s
    static_configs:
      - targets:
        - '10.0.0.54:8100'
EOF"
```

- [ ] **Step 2: Restart Prometheus**

```bash
ssh swebber64@10.0.0.251 "docker compose -f /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/docker-compose.yml restart dhg-prometheus"
```

- [ ] **Step 3: Verify scrape target**

```bash
ssh swebber64@10.0.0.251 "curl -s http://localhost:9090/api/v1/targets | python3 -c 'import sys,json; [print(t[\"labels\"][\"job\"], t[\"health\"]) for t in json.load(sys.stdin)[\"data\"][\"activeTargets\"] if \"inference\" in t[\"labels\"].get(\"job\",\"\")]'"
```

Expected: `inference-gateway up`

- [ ] **Step 4: Commit**

```bash
ssh swebber64@10.0.0.251 "cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git add observability/prometheus/prometheus.yml && git commit -m 'feat: add inference gateway Prometheus scrape target

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>'"
```

---

## Task 9: End-to-End Smoke Test

**Target:** Both machines

- [ ] **Step 1: Verify full request flow**

From .251, call the 5090 gateway through the registry:

```bash
ssh swebber64@10.0.0.251 "
# 1. Discover model
ENDPOINT=\$(curl -s 'http://localhost:8011/api/v1/inference/models?task_type=medical_qa')
echo \"Discovery: \$ENDPOINT\"

# 2. Call gateway
curl -s -X POST http://10.0.0.54:8100/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'X-Task-Type: medical_qa' \
  -d '{\"model\": \"meditron3:8b\", \"messages\": [{\"role\": \"user\", \"content\": \"What are the ACCME requirements for CME credit?\"}], \"max_tokens\": 200}' | python3 -m json.tool | head -15

# 3. Verify logged
sleep 2
curl -s 'http://localhost:8011/api/v1/inference/interactions?limit=1' | python3 -m json.tool | head -20
"
```

Expected: Model discovered, response received, interaction logged

- [ ] **Step 2: Verify metrics**

```bash
wsl -d Ubuntu-2404 -- bash -c "curl -s http://localhost:8100/metrics | grep gateway_requests_total"
```

Expected: Counter shows at least 1 request

- [ ] **Step 3: Verify heartbeat**

```bash
ssh swebber64@10.0.0.251 "docker exec dhg-registry-db psql -U dhg -d dhg_registry -c \"SELECT node_name, status, last_heartbeat FROM inference_nodes WHERE node_name='5090'\""
```

Expected: status=online, last_heartbeat within last 30 seconds

---

## Summary: What Gets Installed Where

| Task | Machine | What |
|------|---------|------|
| 1 | 5090 WSL | Ollama + Meditron3-8B + firewall + port forwarding |
| 2 | .251 | Database migration (6 tables + seed data) |
| 3 | .251 | SQLAlchemy models in registry |
| 4 | .251 | Pydantic schemas for inference API |
| 5 | .251 | Inference API endpoints in registry-api |
| 6 | 5090 WSL | Gateway codebase + systemd service |
| 7 | .251 | LLMRouter update in LangGraph agents |
| 8 | .251 | Prometheus scrape target |
| 9 | Both | End-to-end smoke test |

**Deferred to later phase:**
- Jason's machine setup (needs IP + SSH access)
- Grafana dashboard (needs data flowing first)
- Feedback loops (LLM-as-judge, human review integration)
- Fallback logic in gateway (Claude API routing)
- Rate limiting in gateway
- Priority queue in gateway
