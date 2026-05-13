"""add insights table

Revision ID: 014
Revises: 013
Create Date: 2026-05-10

Stores AI-generated educational insight statements from coding sessions
with pgvector embeddings and full-text search for knowledge retrieval.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tldr", sa.String(280), nullable=False),
        sa.Column("insight_statement", sa.Text, nullable=False),
        sa.Column("project_name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("subcategory", sa.String(64), nullable=True),
        sa.Column("source_file", sa.String(512), nullable=True),
        sa.Column("source_language", sa.String(32), nullable=True),
        sa.Column("source_framework", sa.String(64), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("embedding_model", sa.String(64), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR, nullable=True),
        sa.Column("session_id", sa.String(128), nullable=True),
        sa.Column("model_name", sa.String(64), nullable=True),
        sa.Column("meta_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_insights_project_category", "insights", ["project_name", "category"])
    op.create_index("ix_insights_created", "insights", ["created_at"])
    op.create_index("ix_insights_tags", "insights", ["tags"], postgresql_using="gin")
    op.create_index("ix_insights_search", "insights", ["search_vector"], postgresql_using="gin")

    op.execute("""
        CREATE OR REPLACE FUNCTION insights_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.tldr, '') || ' ' ||
                coalesce(NEW.insight_statement, '') || ' ' ||
                coalesce(NEW.project_name, '') || ' ' ||
                coalesce(NEW.category, '') || ' ' ||
                coalesce(NEW.subcategory, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER insights_search_vector_trigger
            BEFORE INSERT OR UPDATE ON insights
            FOR EACH ROW EXECUTE FUNCTION insights_search_vector_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS insights_search_vector_trigger ON insights")
    op.execute("DROP FUNCTION IF EXISTS insights_search_vector_update()")
    op.drop_table("insights")
