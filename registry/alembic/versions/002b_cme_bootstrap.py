"""bootstrap the hand-applied CME tables so the alembic chain replays on a clean database

Revision ID: 002b_cme_bootstrap
Revises: 002_claude_data
Create Date: 2026-09-13

Production got `cme_projects` and `cme_agent_outputs` from
registry/migrations/003_add_cme_projects.sql (applied by hand, 2026-02-01) and
`cme_documents` / `cme_source_references` the same way; no alembic revision ever
created them, yet 003 (FK to cme_projects), 005 (columns on
cme_source_references), 008 and 010 (columns on cme_projects / cme_documents)
depend on them. On an empty database `alembic upgrade head` therefore failed at
003 and, because the whole chain runs in one transaction, left nothing behind.
CI's Test Registry API job was red for that reason.

This revision creates the five tables (the four above plus cme_intake_fields,
also hand-created) exactly as production has them, minus the
columns that later revisions add (005: verification_*; 008: intake_version,
current_run_id; 010: drive_*), so those revisions apply unchanged afterwards.
It is guarded on `cme_projects` existing: production (alembic_version already
past this point) and any database built from the SQL file are untouched.

Search-vector triggers are deliberately not recreated (maintenance
conveniences, nothing in the code depends on them). The updated_at trigger
function from 001_add_agents.sql IS recreated, unconditionally and
idempotently, because 011_add_incidents attaches triggers to it.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "002b_cme_bootstrap"
down_revision = "002_claude_data"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    if context.is_offline_mode():
        return False  # emit the DDL for review in --sql mode
    return sa.inspect(op.get_bind()).has_table(name)


BOOTSTRAP_SQL = """
CREATE EXTENSION IF NOT EXISTS pg_trgm;

DO $$ BEGIN
    CREATE TYPE cme_project_status AS ENUM (
        'intake', 'processing', 'review', 'complete', 'failed', 'cancelled',
        'awaiting_review', 'archived'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE cme_projects (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    name character varying(255) NOT NULL,
    status cme_project_status DEFAULT 'intake'::cme_project_status NOT NULL,
    intake jsonb NOT NULL,
    current_agent character varying(100),
    progress_percent integer DEFAULT 0,
    agents_completed text[] DEFAULT '{}'::text[],
    agents_pending text[] DEFAULT '{}'::text[],
    pipeline_thread_id character varying(100),
    langsmith_run_id character varying(100),
    outputs jsonb DEFAULT '{}'::jsonb,
    errors jsonb DEFAULT '[]'::jsonb,
    human_review_status character varying(50),
    human_review_notes text,
    reviewed_by character varying(255),
    reviewed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    started_at timestamp with time zone,
    completed_at timestamp with time zone
);
CREATE INDEX idx_cme_projects_status ON cme_projects USING btree (status);
CREATE INDEX idx_cme_projects_created_at ON cme_projects USING btree (created_at DESC);
CREATE INDEX idx_cme_projects_current_agent ON cme_projects USING btree (current_agent);
CREATE INDEX idx_cme_projects_pipeline_thread ON cme_projects USING btree (pipeline_thread_id);
CREATE INDEX idx_cme_projects_intake ON cme_projects USING gin (intake);

CREATE TABLE cme_agent_outputs (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES cme_projects(id) ON DELETE CASCADE,
    agent_name character varying(100) NOT NULL,
    output_type character varying(100) NOT NULL,
    content jsonb NOT NULL,
    quality_score double precision,
    langsmith_trace_id character varying(100),
    created_at timestamp with time zone DEFAULT now(),
    document_text text,
    embedding vector(768),
    search_vector tsvector
);
CREATE INDEX idx_cme_outputs_project_id ON cme_agent_outputs USING btree (project_id);
CREATE INDEX idx_cme_outputs_agent_name ON cme_agent_outputs USING btree (agent_name);
CREATE INDEX idx_cme_outputs_doc_text_trgm ON cme_agent_outputs USING gin (document_text gin_trgm_ops);
CREATE INDEX idx_cme_outputs_embedding ON cme_agent_outputs USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_cme_outputs_search_vector ON cme_agent_outputs USING gin (search_vector);

CREATE TABLE cme_documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES cme_projects(id) ON DELETE RESTRICT,
    agent_output_id uuid REFERENCES cme_agent_outputs(id),
    document_type character varying(100) NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    is_current boolean DEFAULT true NOT NULL,
    title character varying(500) NOT NULL,
    content_text text NOT NULL,
    content_html text,
    content_json jsonb,
    word_count integer,
    quality_score double precision,
    quality_passed boolean,
    quality_details jsonb,
    embedding vector(768),
    search_vector tsvector,
    source_references jsonb DEFAULT '[]'::jsonb,
    created_by character varying(255) DEFAULT 'system'::character varying NOT NULL,
    retention_until timestamp with time zone DEFAULT (now() + '7 years'::interval) NOT NULL,
    is_archived boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);
CREATE INDEX idx_cme_docs_project ON cme_documents USING btree (project_id);
CREATE INDEX idx_cme_docs_type ON cme_documents USING btree (document_type);
CREATE INDEX idx_cme_docs_current ON cme_documents USING btree (project_id, document_type) WHERE (is_current = true);
CREATE INDEX idx_cme_docs_retention ON cme_documents USING btree (retention_until) WHERE (NOT is_archived);
CREATE INDEX idx_cme_docs_content_json ON cme_documents USING gin (content_json);
CREATE INDEX idx_cme_docs_embedding ON cme_documents USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_cme_docs_search ON cme_documents USING gin (search_vector);

CREATE TABLE cme_source_references (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES cme_projects(id) ON DELETE RESTRICT,
    document_id uuid REFERENCES cme_documents(id),
    ref_type character varying(50) NOT NULL,
    ref_id character varying(255),
    title text NOT NULL,
    authors text,
    journal character varying(500),
    publication_date date,
    url text,
    abstract text,
    embedding vector(768),
    search_vector tsvector,
    accessed_at timestamp with time zone DEFAULT now() NOT NULL,
    cached_content jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);
CREATE INDEX idx_cme_refs_project ON cme_source_references USING btree (project_id);
CREATE INDEX idx_cme_refs_ref_id ON cme_source_references USING btree (ref_id);
CREATE INDEX idx_cme_refs_type ON cme_source_references USING btree (ref_type);
CREATE INDEX idx_cme_refs_embedding ON cme_source_references USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_cme_refs_search ON cme_source_references USING gin (search_vector);

CREATE TABLE cme_intake_fields (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES cme_projects(id) ON DELETE RESTRICT,
    section character varying(50) NOT NULL,
    field_name character varying(100) NOT NULL,
    field_label character varying(255) NOT NULL,
    value_text text,
    value_json jsonb,
    search_vector tsvector,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT cme_intake_fields_project_id_section_field_name_key UNIQUE (project_id, section, field_name)
);
CREATE INDEX idx_cme_intake_project ON cme_intake_fields USING btree (project_id);
CREATE INDEX idx_cme_intake_section ON cme_intake_fields USING btree (section);
CREATE INDEX idx_cme_intake_search ON cme_intake_fields USING gin (search_vector);
CREATE INDEX idx_cme_intake_value_json ON cme_intake_fields USING gin (value_json);
"""


UPDATED_AT_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    # Trigger function from registry/migrations/001_add_agents.sql (also in
    # init.sql); 011_add_incidents attaches triggers to it. Idempotent.
    op.execute(UPDATED_AT_FUNCTION_SQL)
    if _has_table("cme_projects"):
        return
    op.execute(BOOTSTRAP_SQL)


def downgrade() -> None:
    # Only undo what this revision created; a database that had the tables
    # before (production) skipped upgrade() and must keep them.
    pass
