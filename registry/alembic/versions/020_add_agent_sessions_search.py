"""add search_vector and embedding to agent_sessions for KB search

Revision ID: 020
Revises: 019
Create Date: 2026-05-15

Adds embedding (vector 768), embedding_model, search_vector (tsvector),
and project_name (alias for project column) to agent_sessions so it can
participate in the unified /api/kb/search endpoint. Backfills search_vector
for existing rows with summary content.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_sessions", sa.Column("embedding", Vector(768), nullable=True))
    op.add_column("agent_sessions", sa.Column("embedding_model", sa.String(64), nullable=True))
    op.add_column("agent_sessions", sa.Column("search_vector", postgresql.TSVECTOR, nullable=True))
    op.add_column("agent_sessions", sa.Column("project_name", sa.String(100), nullable=True))

    op.create_index("ix_agent_sessions_search", "agent_sessions", ["search_vector"],
                    postgresql_using="gin")

    # Backfill project_name from project column
    op.execute("UPDATE agent_sessions SET project_name = project WHERE project_name IS NULL;")

    # Auto-populate search_vector on INSERT/UPDATE
    op.execute("""
        CREATE OR REPLACE FUNCTION agent_sessions_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.tldr, '') || ' ' ||
                coalesce(NEW.summary, '') || ' ' ||
                coalesce(NEW.project, '') || ' ' ||
                coalesce(NEW.source, '')
            );
            IF NEW.project_name IS NULL THEN
                NEW.project_name := NEW.project;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER agent_sessions_search_vector_trigger
            BEFORE INSERT OR UPDATE ON agent_sessions
            FOR EACH ROW EXECUTE FUNCTION agent_sessions_search_vector_update();
    """)

    # Backfill search_vector for existing rows that have summaries
    op.execute("""
        UPDATE agent_sessions SET
            search_vector = to_tsvector('english',
                coalesce(tldr, '') || ' ' ||
                coalesce(summary, '') || ' ' ||
                coalesce(project, '') || ' ' ||
                coalesce(source, '')
            )
        WHERE summary IS NOT NULL AND length(trim(summary)) > 50;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS agent_sessions_search_vector_trigger ON agent_sessions;")
    op.execute("DROP FUNCTION IF EXISTS agent_sessions_search_vector_update();")
    op.drop_index("ix_agent_sessions_search", table_name="agent_sessions")
    op.drop_column("agent_sessions", "search_vector")
    op.drop_column("agent_sessions", "embedding_model")
    op.drop_column("agent_sessions", "embedding")
    op.drop_column("agent_sessions", "project_name")
