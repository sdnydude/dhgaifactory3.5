-- Migration 005: Inference Platform Tables
-- Date: 2026-04-11

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

CREATE TABLE IF NOT EXISTS model_update_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID REFERENCES inference_nodes(id),
    model_name VARCHAR(255),
    old_digest VARCHAR(64),
    new_digest VARCHAR(64),
    updated_at TIMESTAMPTZ DEFAULT now(),
    updated_by VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS routing_config (
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
('general', 'local:general', 'claude')
ON CONFLICT (task_type) DO NOTHING;

INSERT INTO inference_nodes (node_name, host, gateway_port, gpu_model, gpu_vram_gb, ram_gb, status)
VALUES ('5090', '10.0.0.54', 8100, 'RTX 5090 Laptop', 24, 64, 'offline')
ON CONFLICT (node_name) DO NOTHING;

INSERT INTO inference_nodes (node_name, host, gateway_port, gpu_model, gpu_vram_gb, ram_gb, status)
VALUES ('g700data1', '10.0.0.251', 8100, 'RTX 5080', 16, 64, 'offline')
ON CONFLICT (node_name) DO NOTHING;
