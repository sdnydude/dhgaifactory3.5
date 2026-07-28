"""add session_reports table

Revision ID: 030
Revises: 029
Create Date: 2026-07-10

Stores narrative end-of-session reports — the story of a session's work plus
learnings, insights, and deferred items, ingested from docs/session-reports/
markdown files in project repos.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(280), nullable=False),
        sa.Column("session_span", sa.Text, nullable=True),
        sa.Column("report_md", sa.Text, nullable=False),
        sa.Column("prs", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("learnings", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("insights", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("deferred", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
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
    op.create_unique_constraint("uq_session_reports_project_title", "session_reports",
                                ["project_name", "title"])

    # Indexes
    op.create_index("ix_session_reports_project_category", "session_reports",
                    ["project_name", "category"])
    op.create_index("ix_session_reports_created", "session_reports", ["created_at"])
    op.create_index("ix_session_reports_tags", "session_reports", ["tags"],
                    postgresql_using="gin")
    op.create_index("ix_session_reports_search", "session_reports", ["search_vector"],
                    postgresql_using="gin")

    # Auto-populate search_vector on INSERT/UPDATE
    op.execute("""
        CREATE OR REPLACE FUNCTION session_reports_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.title, '') || ' ' ||
                coalesce(NEW.report_md, '') || ' ' ||
                coalesce(array_to_string(NEW.learnings, ' '), '') || ' ' ||
                coalesce(array_to_string(NEW.insights, ' '), '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER session_reports_search_vector_trigger
            BEFORE INSERT OR UPDATE ON session_reports
            FOR EACH ROW EXECUTE FUNCTION session_reports_search_vector_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS session_reports_search_vector_trigger ON session_reports;")
    op.execute("DROP FUNCTION IF EXISTS session_reports_search_vector_update();")
    op.drop_table("session_reports")
