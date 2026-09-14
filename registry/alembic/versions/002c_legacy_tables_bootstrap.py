"""bootstrap the hand-applied registry tables (agents, inference, done-gate, research, antigravity)

Revision ID: 002c_legacy_tables_bootstrap
Revises: 002b_cme_bootstrap
Create Date: 2026-09-13

Twelve tables that SQLAlchemy models in registry/models.py map to were created
by hand from registry/migrations/*.sql (001_add_agents, 002_add_research_requests,
005_add_inference_tables, 006_add_done_gate_runs) or directly in psql
(antigravity_*). No alembic revision creates them, so a clean database booted
with `alembic upgrade head` lacks them and any endpoint touching them fails.

DDL is column-for-column what production has (pg_dump --schema-only,
2026-09-13). Each table is guarded on its own existence, so production and any
database built from the SQL files are untouched. The trigger function
update_research_requests_updated_at is recreated idempotently (CREATE OR
REPLACE, every run); its trigger is created together with research_requests
only when this revision creates that table. Production has no trigger on
`agents` (001_add_agents.sql defined one, it was never applied), so none is
created here. Offline --sql mode is refused: the guards need a connection.
"""
from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import context, op

log = logging.getLogger("alembic.runtime.migration")

revision = "002c_legacy_tables_bootstrap"
down_revision = "002b_cme_bootstrap"
branch_labels = None
depends_on = None


def _refuse_offline() -> None:
    if context.is_offline_mode():
        raise RuntimeError("002c_legacy_tables_bootstrap must run online (no --sql): its table guards inspect the database")


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


# Creation order respects foreign keys: agents -> agent_heartbeats,
# antigravity_chats -> antigravity_files, inference_nodes -> inference_models /
# llm_interactions -> llm_quality_evals, model_update_log.
# Idempotent: the trigger function research_requests attaches to (from
# registry/migrations/002_add_research_requests.sql / init.sql).
FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION update_research_requests_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

TABLE_SQL = {
    "agents": """
CREATE TABLE agents (
    id character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    version character varying(50) NOT NULL,
    division character varying(100) NOT NULL,
    type character varying(100) NOT NULL,
    description text,
    deployment_type character varying(50) DEFAULT 'langsmith_cloud'::character varying,
    deployment_url text,
    langsmith_deployment_id character varying(255),
    langsmith_org character varying(255),
    github_repo character varying(255),
    github_branch character varying(100) DEFAULT 'main'::character varying,
    github_path character varying(255),
    endpoint text,
    capabilities jsonb,
    io_schema jsonb,
    models jsonb,
    external_apis jsonb,
    observability jsonb,
    status character varying(50) DEFAULT 'healthy'::character varying,
    last_heartbeat timestamp with time zone,
    registered_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);
ALTER TABLE agents ADD CONSTRAINT agents_pkey PRIMARY KEY (id);
CREATE INDEX idx_agents_deployment_type ON agents USING btree (deployment_type);
CREATE INDEX idx_agents_division ON agents USING btree (division);
CREATE INDEX idx_agents_status ON agents USING btree (status);
CREATE INDEX idx_agents_type ON agents USING btree (type);
""",
    "agent_heartbeats": """
CREATE TABLE agent_heartbeats (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    agent_id character varying(255) NOT NULL,
    status character varying(50) NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now(),
    models jsonb,
    requests_total integer DEFAULT 0,
    requests_success integer DEFAULT 0,
    requests_failed integer DEFAULT 0,
    avg_latency_ms double precision DEFAULT 0.0,
    total_tokens integer DEFAULT 0,
    total_cost_usd double precision DEFAULT 0.0,
    langsmith_deployment_status character varying(50),
    langsmith_traces_count integer,
    deployment_tier character varying(50)
);
ALTER TABLE agent_heartbeats ADD CONSTRAINT agent_heartbeats_pkey PRIMARY KEY (id);
ALTER TABLE agent_heartbeats ADD CONSTRAINT agent_heartbeats_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE;
CREATE INDEX idx_heartbeats_agent_id ON agent_heartbeats USING btree (agent_id);
CREATE INDEX idx_heartbeats_timestamp ON agent_heartbeats USING btree ("timestamp" DESC);
""",
    "antigravity_chats": """
CREATE TABLE antigravity_chats (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    conversation_id character varying(255) NOT NULL,
    title text,
    summary text,
    user_objective text,
    created_at timestamp with time zone DEFAULT now(),
    last_modified timestamp with time zone DEFAULT now(),
    message_count integer DEFAULT 0,
    total_tokens integer DEFAULT 0,
    total_cost_usd double precision DEFAULT 0.0,
    status character varying(50) DEFAULT 'active'::character varying,
    tags text[],
    metadata jsonb
);
ALTER TABLE antigravity_chats ADD CONSTRAINT antigravity_chats_conversation_id_key UNIQUE (conversation_id);
ALTER TABLE antigravity_chats ADD CONSTRAINT antigravity_chats_pkey PRIMARY KEY (id);
CREATE INDEX idx_antigravity_chats_created ON antigravity_chats USING btree (created_at DESC);
CREATE INDEX idx_antigravity_chats_status ON antigravity_chats USING btree (status);
CREATE INDEX idx_antigravity_chats_tags ON antigravity_chats USING gin (tags);
""",
    "antigravity_files": """
CREATE TABLE antigravity_files (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    conversation_id character varying(255),
    file_path text NOT NULL,
    file_type character varying(100),
    file_size_bytes bigint,
    artifact_type character varying(100),
    summary text,
    created_at timestamp with time zone DEFAULT now(),
    last_modified timestamp with time zone DEFAULT now(),
    metadata jsonb
);
ALTER TABLE antigravity_files ADD CONSTRAINT antigravity_files_pkey PRIMARY KEY (id);
ALTER TABLE antigravity_files ADD CONSTRAINT antigravity_files_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES antigravity_chats(conversation_id) ON DELETE CASCADE;
CREATE INDEX idx_antigravity_files_artifact ON antigravity_files USING btree (artifact_type);
CREATE INDEX idx_antigravity_files_conversation ON antigravity_files USING btree (conversation_id);
CREATE INDEX idx_antigravity_files_created ON antigravity_files USING btree (created_at DESC);
CREATE INDEX idx_antigravity_files_type ON antigravity_files USING btree (file_type);
""",
    "inference_nodes": """
CREATE TABLE inference_nodes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    node_name character varying(50) NOT NULL,
    host character varying(255) NOT NULL,
    gateway_port integer DEFAULT 8100,
    ollama_port integer DEFAULT 11434,
    gpu_model character varying(100),
    gpu_vram_gb integer,
    ram_gb integer,
    status character varying(20) DEFAULT 'offline'::character varying,
    fallback_enabled boolean DEFAULT true,
    last_heartbeat timestamp with time zone,
    registered_at timestamp with time zone DEFAULT now(),
    metadata jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT inference_nodes_status_check CHECK (((status)::text = ANY ((ARRAY['online'::character varying, 'offline'::character varying, 'draining'::character varying])::text[])))
);
ALTER TABLE inference_nodes ADD CONSTRAINT inference_nodes_node_name_key UNIQUE (node_name);
ALTER TABLE inference_nodes ADD CONSTRAINT inference_nodes_pkey PRIMARY KEY (id);
""",
    "inference_models": """
CREATE TABLE inference_models (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    node_id uuid,
    model_name character varying(255) NOT NULL,
    model_alias character varying(100),
    task_types text[] DEFAULT '{}'::text[],
    priority integer DEFAULT 1,
    vram_usage_gb numeric(4,1),
    loaded boolean DEFAULT false,
    max_context_length integer,
    created_at timestamp with time zone DEFAULT now()
);
ALTER TABLE inference_models ADD CONSTRAINT inference_models_node_id_model_name_key UNIQUE (node_id, model_name);
ALTER TABLE inference_models ADD CONSTRAINT inference_models_pkey PRIMARY KEY (id);
ALTER TABLE inference_models ADD CONSTRAINT inference_models_node_id_fkey FOREIGN KEY (node_id) REFERENCES inference_nodes(id) ON DELETE CASCADE;
""",
    "llm_interactions": """
CREATE TABLE llm_interactions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now(),
    user_id uuid,
    node_id uuid,
    model_name character varying(255) NOT NULL,
    model_source character varying(50) NOT NULL,
    model_digest character varying(64),
    task_type character varying(50),
    agent_name character varying(100),
    session_id uuid,
    prompt_tokens integer,
    completion_tokens integer,
    latency_ms integer,
    input_hash character varying(64),
    input_summary text,
    input_has_image boolean DEFAULT false,
    output jsonb,
    output_validated boolean,
    output_schema_name character varying(100),
    fallback_used boolean DEFAULT false,
    fallback_reason text,
    retry_count integer DEFAULT 0,
    estimated_cost_usd numeric(10,6),
    synced_at timestamp with time zone,
    CONSTRAINT llm_interactions_model_source_check CHECK (((model_source)::text = ANY ((ARRAY['local_ollama'::character varying, 'anthropic_api'::character varying, 'google_api'::character varying, 'openai_api'::character varying])::text[])))
);
ALTER TABLE llm_interactions ADD CONSTRAINT llm_interactions_pkey PRIMARY KEY (id);
ALTER TABLE llm_interactions ADD CONSTRAINT llm_interactions_node_id_fkey FOREIGN KEY (node_id) REFERENCES inference_nodes(id);
CREATE INDEX idx_llm_interactions_input_hash ON llm_interactions USING btree (input_hash);
CREATE INDEX idx_llm_interactions_node ON llm_interactions USING btree (node_id);
CREATE INDEX idx_llm_interactions_task_type ON llm_interactions USING btree (task_type);
CREATE INDEX idx_llm_interactions_timestamp ON llm_interactions USING btree ("timestamp");
CREATE INDEX idx_llm_interactions_user ON llm_interactions USING btree (user_id);
""",
    "llm_quality_evals": """
CREATE TABLE llm_quality_evals (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    interaction_id uuid,
    grade integer,
    criteria jsonb,
    issues text[],
    graded_by character varying(100),
    evaluated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT llm_quality_evals_grade_check CHECK (((grade >= 1) AND (grade <= 5)))
);
ALTER TABLE llm_quality_evals ADD CONSTRAINT llm_quality_evals_pkey PRIMARY KEY (id);
ALTER TABLE llm_quality_evals ADD CONSTRAINT llm_quality_evals_interaction_id_fkey FOREIGN KEY (interaction_id) REFERENCES llm_interactions(id);
CREATE INDEX idx_llm_quality_evals_interaction ON llm_quality_evals USING btree (interaction_id);
""",
    "model_update_log": """
CREATE TABLE model_update_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    node_id uuid,
    model_name character varying(255),
    old_digest character varying(64),
    new_digest character varying(64),
    updated_at timestamp with time zone DEFAULT now(),
    updated_by character varying(100)
);
ALTER TABLE model_update_log ADD CONSTRAINT model_update_log_pkey PRIMARY KEY (id);
ALTER TABLE model_update_log ADD CONSTRAINT model_update_log_node_id_fkey FOREIGN KEY (node_id) REFERENCES inference_nodes(id);
""",
    "done_gate_runs": """
CREATE TABLE done_gate_runs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id character varying(128) NOT NULL,
    project character varying(100) NOT NULL,
    verdict character varying(16) NOT NULL,
    claim jsonb,
    evidence jsonb,
    gate_mode character varying(16) DEFAULT 'observe'::character varying NOT NULL,
    check_version integer DEFAULT 1 NOT NULL,
    adjudication character varying(16),
    sampled boolean DEFAULT false NOT NULL,
    adjudicated_at timestamp with time zone,
    meta_data jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT done_gate_runs_adjudication_check CHECK (((adjudication)::text = ANY ((ARRAY['true_positive'::character varying, 'false_positive'::character varying, 'false_negative'::character varying, 'true_negative'::character varying])::text[]))),
    CONSTRAINT done_gate_runs_verdict_check CHECK (((verdict)::text = ANY ((ARRAY['pass'::character varying, 'fail'::character varying, 'no_claim'::character varying])::text[])))
);
ALTER TABLE done_gate_runs ADD CONSTRAINT done_gate_runs_pkey PRIMARY KEY (id);
CREATE INDEX ix_done_gate_runs_project_created ON done_gate_runs USING btree (project, created_at);
CREATE INDEX ix_done_gate_runs_verdict ON done_gate_runs USING btree (verdict);
""",
    "research_requests": """
CREATE TABLE research_requests (
    request_id character varying NOT NULL,
    user_id character varying NOT NULL,
    agent_type character varying DEFAULT 'cme_research'::character varying NOT NULL,
    status character varying DEFAULT 'pending'::character varying NOT NULL,
    input_params jsonb NOT NULL,
    output_summary jsonb,
    processing_metadata jsonb,
    error_message text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);
ALTER TABLE research_requests ADD CONSTRAINT research_requests_pkey PRIMARY KEY (request_id);
CREATE INDEX idx_research_created_at ON research_requests USING btree (created_at);
CREATE INDEX idx_research_status ON research_requests USING btree (status);
CREATE INDEX idx_research_status_created ON research_requests USING btree (status, created_at);
CREATE INDEX idx_research_user_created ON research_requests USING btree (user_id, created_at);
CREATE INDEX idx_research_user_id ON research_requests USING btree (user_id);
CREATE TRIGGER research_requests_updated_at BEFORE UPDATE ON research_requests FOR EACH ROW EXECUTE FUNCTION update_research_requests_updated_at();
""",
    "routing_config": """
CREATE TABLE routing_config (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    task_type character varying(100) NOT NULL,
    prefer character varying(100) NOT NULL,
    fallback character varying(100),
    enabled boolean DEFAULT true,
    updated_at timestamp with time zone DEFAULT now()
);
ALTER TABLE routing_config ADD CONSTRAINT routing_config_pkey PRIMARY KEY (id);
ALTER TABLE routing_config ADD CONSTRAINT routing_config_task_type_key UNIQUE (task_type);
""",
}



def upgrade() -> None:
    _refuse_offline()
    op.execute(FUNCTION_SQL)
    for name, sql in TABLE_SQL.items():
        if _has_table(name):
            log.info("002c: %s already exists, skipping bootstrap", name)
            continue
        log.info("002c: creating %s (hand-applied in production, absent here)", name)
        op.execute(sql)


def downgrade() -> None:
    log.warning(
        "002c downgrade keeps the twelve legacy tables and "
        "update_research_requests_updated_at(): a database that had them "
        "before skipped upgrade() and must keep them"
    )
