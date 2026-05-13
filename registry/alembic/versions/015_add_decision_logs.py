"""add decision_logs table

Revision ID: 015
Revises: 014
Create Date: 2026-05-10

Stores architectural decision logs from coding sessions — what was decided,
what was rejected, and why — with full-text search for knowledge retrieval.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(280), nullable=False),
        sa.Column("choice", sa.Text, nullable=False),
        sa.Column("alternatives_rejected", sa.Text, nullable=True),
        sa.Column("rationale", sa.Text, nullable=False),
        sa.Column("domain", sa.String(32), nullable=False),
        sa.Column("supersedes", sa.String(128), nullable=True),
        sa.Column("project_name", sa.String(100), nullable=False),
        sa.Column("source_file", sa.String(512), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR, nullable=True),
        sa.Column("session_id", sa.String(128), nullable=True),
        sa.Column("model_name", sa.String(64), nullable=True),
        sa.Column("meta_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_decision_logs_project_domain", "decision_logs", ["project_name", "domain"])
    op.create_index("ix_decision_logs_created", "decision_logs", ["created_at"])
    op.create_index("ix_decision_logs_tags", "decision_logs", ["tags"], postgresql_using="gin")
    op.create_index("ix_decision_logs_search", "decision_logs", ["search_vector"], postgresql_using="gin")

    op.execute("""
        CREATE OR REPLACE FUNCTION decision_logs_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.title, '') || ' ' ||
                coalesce(NEW.choice, '') || ' ' ||
                coalesce(NEW.alternatives_rejected, '') || ' ' ||
                coalesce(NEW.rationale, '') || ' ' ||
                coalesce(NEW.project_name, '') || ' ' ||
                coalesce(NEW.domain, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER decision_logs_search_vector_trigger
            BEFORE INSERT OR UPDATE ON decision_logs
            FOR EACH ROW EXECUTE FUNCTION decision_logs_search_vector_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS decision_logs_search_vector_trigger ON decision_logs")
    op.execute("DROP FUNCTION IF EXISTS decision_logs_search_vector_update()")
    op.drop_table("decision_logs")
