"""add bug_fixes table

Revision ID: 023
Revises: 022
Create Date: 2026-05-15

Stores structured bug-fix records — symptom, root cause, fix applied, files
affected, severity — captured automatically after non-trivial debugging sessions.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bug_fixes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tldr", sa.String(280), nullable=False),
        sa.Column("symptom", sa.Text, nullable=False),
        sa.Column("root_cause", sa.Text, nullable=False),
        sa.Column("fix_applied", sa.Text, nullable=False),
        sa.Column("files_affected", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("project_name", sa.String(100), nullable=False),
        sa.Column("source_file", sa.String(512), nullable=True),
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
    op.create_unique_constraint("uq_bug_fixes_project_tldr", "bug_fixes",
                                ["project_name", "tldr"])

    # Indexes
    op.create_index("ix_bug_fixes_project_category", "bug_fixes",
                    ["project_name", "category"])
    op.create_index("ix_bug_fixes_severity", "bug_fixes", ["severity"])
    op.create_index("ix_bug_fixes_created", "bug_fixes", ["created_at"])
    op.create_index("ix_bug_fixes_tags", "bug_fixes", ["tags"],
                    postgresql_using="gin")
    op.create_index("ix_bug_fixes_search", "bug_fixes", ["search_vector"],
                    postgresql_using="gin")

    # Auto-populate search_vector on INSERT/UPDATE
    op.execute("""
        CREATE OR REPLACE FUNCTION bug_fixes_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.tldr, '') || ' ' ||
                coalesce(NEW.symptom, '') || ' ' ||
                coalesce(NEW.root_cause, '') || ' ' ||
                coalesce(NEW.fix_applied, '') || ' ' ||
                coalesce(NEW.project_name, '') || ' ' ||
                coalesce(NEW.category, '') || ' ' ||
                coalesce(NEW.severity, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER bug_fixes_search_vector_trigger
            BEFORE INSERT OR UPDATE ON bug_fixes
            FOR EACH ROW EXECUTE FUNCTION bug_fixes_search_vector_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS bug_fixes_search_vector_trigger ON bug_fixes;")
    op.execute("DROP FUNCTION IF EXISTS bug_fixes_search_vector_update();")
    op.drop_table("bug_fixes")
