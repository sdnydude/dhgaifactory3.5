"""add ship_sessions table

Revision ID: 018
Revises: 017
Create Date: 2026-05-13

Structured records of /ship workflow runs — feature, approach, review,
verification, deferred items. pgvector embeddings + full-text search.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ship_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_name", sa.String(100), nullable=False),
        sa.Column("feature", sa.Text, nullable=False),
        sa.Column("approach", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("complexity", sa.String(20), nullable=True),
        sa.Column("tdd", sa.Boolean, nullable=True),
        sa.Column("pr_url", sa.String(512), nullable=True),
        sa.Column("branch", sa.String(255), nullable=True),
        sa.Column("commits", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("deferred", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("surprises", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("decisions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("review", postgresql.JSONB, nullable=True),
        sa.Column("verification", postgresql.JSONB, nullable=True),
        sa.Column("file_map", postgresql.JSONB, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("embedding_model", sa.String(64), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR, nullable=True),
        sa.Column("session_id", sa.String(128), nullable=True),
        sa.Column("model_name", sa.String(64), nullable=True),
        sa.Column("meta_data", postgresql.JSONB, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_ship_sessions_project_status", "ship_sessions", ["project_name", "status"])
    op.create_index("ix_ship_sessions_created", "ship_sessions", ["created_at"])
    op.create_index("ix_ship_sessions_tags", "ship_sessions", ["tags"], postgresql_using="gin")

    op.execute("""
        CREATE OR REPLACE FUNCTION ship_sessions_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.feature, '') || ' ' ||
                coalesce(NEW.approach, '') || ' ' ||
                coalesce(NEW.project_name, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER ship_sessions_search_vector_trigger
            BEFORE INSERT OR UPDATE ON ship_sessions
            FOR EACH ROW EXECUTE FUNCTION ship_sessions_search_vector_update();
    """)

    op.create_index("ix_ship_sessions_search", "ship_sessions", ["search_vector"], postgresql_using="gin")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS ship_sessions_search_vector_trigger ON ship_sessions")
    op.execute("DROP FUNCTION IF EXISTS ship_sessions_search_vector_update()")
    op.drop_table("ship_sessions")
