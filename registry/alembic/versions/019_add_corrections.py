"""add corrections table for Loop 4 self-training

Revision ID: 019
Revises: 018
Create Date: 2026-05-13

Captures user corrections of Claude behavior — pushback patterns that indicate
Claude needs to adjust default behavior. Auto-populated by behavioral rule
fired on user pushback patterns. Searchable via /api/kb/search and the
unified KB endpoint.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "corrections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("user_message", sa.Text, nullable=False),
        sa.Column("context", sa.Text, nullable=True),
        sa.Column("claude_action", sa.Text, nullable=True),
        sa.Column("session_id", sa.String(128), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("embedding_model", sa.String(64), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR, nullable=True),
        sa.Column("model_name", sa.String(64), nullable=True),
        sa.Column("meta_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    op.create_index("ix_corrections_project_category", "corrections",
                    ["project_name", "category"])
    op.create_index("ix_corrections_created", "corrections", ["created_at"])
    op.create_index("ix_corrections_tags", "corrections", ["tags"],
                    postgresql_using="gin")
    op.create_index("ix_corrections_search", "corrections", ["search_vector"],
                    postgresql_using="gin")

    # Auto-populate search_vector on INSERT/UPDATE
    op.execute("""
        CREATE OR REPLACE FUNCTION corrections_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.category, '') || ' ' ||
                coalesce(NEW.user_message, '') || ' ' ||
                coalesce(NEW.context, '') || ' ' ||
                coalesce(NEW.claude_action, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER corrections_search_vector_trigger
            BEFORE INSERT OR UPDATE ON corrections
            FOR EACH ROW EXECUTE FUNCTION corrections_search_vector_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS corrections_search_vector_trigger ON corrections;")
    op.execute("DROP FUNCTION IF EXISTS corrections_search_vector_update();")
    op.drop_table("corrections")
