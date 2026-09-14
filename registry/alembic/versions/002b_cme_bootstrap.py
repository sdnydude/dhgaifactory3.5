"""bootstrap the hand-applied CME tables so the alembic chain replays on a clean database

Revision ID: 002b_cme_bootstrap
Revises: 002_claude_data
Create Date: 2026-09-13

Production got `cme_projects` and `cme_agent_outputs` from
registry/migrations/003_add_cme_projects.sql (applied by hand, 2026-02-01) and
`cme_documents` / `cme_source_references` the same way; no alembic revision ever
created them, yet 003 (FK to cme_projects), 005 (columns on
cme_source_references), 008 and 010 (columns on cme_projects / cme_documents)
depend on them. On an empty database (with 001 now owning the extensions)
`alembic upgrade head` therefore failed at 003 and, because the whole chain
runs in one transaction, left nothing behind. CI's Test Registry API job was
red for that reason.

This revision creates the five tables (the four above plus cme_intake_fields,
also hand-created) exactly as production has them, minus the
columns that later revisions add (005: verification_status, verified_at,
verified_by; 008: intake_version, current_run_id; 010: drive_folder_id,
drive_last_synced_at, drive_sync_status on cme_projects and drive_file_id,
drive_synced_at, drive_md5 on cme_documents), so those revisions apply
unchanged afterwards. Each table is guarded on its own existence, so
production (alembic_version already past this point) is untouched and a
database built from the SQL file (which has only the first two tables) still
gets the other three.

Also recreated, idempotently (CREATE OR REPLACE): the four search-vector
trigger functions and their triggers — registry/cme_search_service.py
filters on search_vector with @@, so without them CME full-text search
returns nothing — the cme_projects updated_at trigger, and the
update_updated_at_column() function that 011_add_incidents attaches to.
Function bodies are production's (pg_get_functiondef, 2026-09-13).
"""
from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import context, op

log = logging.getLogger("alembic.runtime.migration")

revision = "002b_cme_bootstrap"
down_revision = "002_claude_data"
branch_labels = None
depends_on = None


def _refuse_offline() -> None:
    # The guards need a live connection; an offline --sql script would emit
    # unguarded CREATE TABLE statements that collide with production.
    if context.is_offline_mode():
        raise RuntimeError("002b_cme_bootstrap must run online (no --sql): its table guards inspect the database")


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


# Idempotent prelude: extension, enum (8 labels as production has today; the
# original SQL file had 6, `awaiting_review` and `archived` were added by hand),
# and the trigger functions the tables below attach to.
PRELUDE_SQL = """
CREATE EXTENSION IF NOT EXISTS pg_trgm;

DO $$ BEGIN
    CREATE TYPE cme_project_status AS ENUM (
        'intake', 'processing', 'review', 'complete', 'failed', 'cancelled',
        'awaiting_review', 'archived'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_cme_docs_search_vector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector := to_tsvector('english',
    COALESCE(NEW.title, '') || ' ' ||
    COALESCE(NEW.content_text, '') || ' ' ||
    COALESCE(NEW.document_type, '')
  );
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_cme_outputs_search_vector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector := to_tsvector('english', COALESCE(NEW.document_text, '') || ' ' || COALESCE(NEW.agent_name, ''));
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_cme_refs_search_vector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector := to_tsvector('english',
    COALESCE(NEW.title, '') || ' ' ||
    COALESCE(NEW.authors, '') || ' ' ||
    COALESCE(NEW.abstract, '') || ' ' ||
    COALESCE(NEW.journal, '')
  );
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_cme_intake_search_vector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector := to_tsvector('english',
    COALESCE(NEW.field_label, '') || ' ' ||
    COALESCE(NEW.value_text, '') || ' ' ||
    COALESCE(NEW.section, '')
  );
  RETURN NEW;
END
$$ LANGUAGE plpgsql;
"""

# One block per table, in foreign-key order; each carries its indexes and the
# trigger production has on it. Guarded per table so a database built from the
# legacy SQL file (which has only the first two) still gets the other three.
TABLE_SQL = {
    "cme_projects": """
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
CREATE TRIGGER update_cme_projects_updated_at BEFORE UPDATE ON cme_projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
""",
    "cme_agent_outputs": """
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
CREATE TRIGGER cme_outputs_search_vector_trigger BEFORE INSERT OR UPDATE ON cme_agent_outputs FOR EACH ROW EXECUTE FUNCTION update_cme_outputs_search_vector();
""",
    "cme_documents": """
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
CREATE TRIGGER cme_docs_search_vector_trigger BEFORE INSERT OR UPDATE ON cme_documents FOR EACH ROW EXECUTE FUNCTION update_cme_docs_search_vector();
""",
    "cme_source_references": """
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
CREATE TRIGGER cme_refs_search_vector_trigger BEFORE INSERT OR UPDATE ON cme_source_references FOR EACH ROW EXECUTE FUNCTION update_cme_refs_search_vector();
""",
    "cme_intake_fields": """
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
CREATE TRIGGER cme_intake_search_vector_trigger BEFORE INSERT OR UPDATE ON cme_intake_fields FOR EACH ROW EXECUTE FUNCTION update_cme_intake_search_vector();
""",
}


def upgrade() -> None:
    _refuse_offline()
    op.execute(PRELUDE_SQL)
    for name, sql in TABLE_SQL.items():
        if _has_table(name):
            log.info("002b: %s already exists, skipping bootstrap", name)
            continue
        log.info("002b: creating %s (hand-applied in production, absent here)", name)
        op.execute(sql)


def downgrade() -> None:
    log.warning(
        "002b downgrade keeps cme_projects, cme_agent_outputs, cme_documents, "
        "cme_source_references, cme_intake_fields, the cme_project_status enum, "
        "pg_trgm and the trigger functions: a database that had them before "
        "skipped upgrade() and must keep them"
    )
