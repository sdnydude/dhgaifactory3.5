"""add deferred_items table

Revision ID: 024
Revises: 023
Create Date: 2026-05-15

Stores work discovered during sessions that was intentionally not fixed and
logged for later — deferred items with priority, category, status, and affected files.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deferred_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(280), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("source_context", sa.Text, nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("affected_files", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("project_name", sa.String(100), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("embedding_model", sa.String(64), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR, nullable=True),
        sa.Column("session_id", sa.String(128), nullable=True),
        sa.Column("model_name", sa.String(64), nullable=True),
        sa.Column("meta_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    # Unique constraint for upsert
    op.create_unique_constraint("uq_deferred_items_project_title", "deferred_items",
                                ["project_name", "title"])

    # Indexes
    op.create_index("ix_deferred_items_project_category", "deferred_items",
                    ["project_name", "category"])
    op.create_index("ix_deferred_items_priority", "deferred_items", ["priority"])
    op.create_index("ix_deferred_items_status", "deferred_items", ["status"])
    op.create_index("ix_deferred_items_created", "deferred_items", ["created_at"])
    op.create_index("ix_deferred_items_tags", "deferred_items", ["tags"],
                    postgresql_using="gin")
    op.create_index("ix_deferred_items_search", "deferred_items", ["search_vector"],
                    postgresql_using="gin")

    # Auto-populate search_vector on INSERT/UPDATE
    op.execute("""
        CREATE OR REPLACE FUNCTION deferred_items_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.title, '') || ' ' ||
                coalesce(NEW.description, '') || ' ' ||
                coalesce(NEW.reason, '') || ' ' ||
                coalesce(NEW.source_context, '') || ' ' ||
                coalesce(NEW.project_name, '') || ' ' ||
                coalesce(NEW.category, '') || ' ' ||
                coalesce(NEW.priority, '') || ' ' ||
                coalesce(NEW.status, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER deferred_items_search_vector_trigger
            BEFORE INSERT OR UPDATE ON deferred_items
            FOR EACH ROW EXECUTE FUNCTION deferred_items_search_vector_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS deferred_items_search_vector_trigger ON deferred_items;")
    op.execute("DROP FUNCTION IF EXISTS deferred_items_search_vector_update();")
    op.drop_table("deferred_items")
