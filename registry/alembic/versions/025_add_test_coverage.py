"""add test_coverage table

Revision ID: 025
Revises: 024
Create Date: 2026-05-15

Stores test suite change events — tracks when tests are added, removed, or
modified with counts, deltas, and affected files.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "test_coverage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(280), nullable=False),
        sa.Column("test_count_before", sa.Integer, nullable=False),
        sa.Column("test_count_after", sa.Integer, nullable=False),
        sa.Column("delta", sa.Integer, nullable=False),
        sa.Column("tests_added", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("tests_removed", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("tests_modified", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("files_affected", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("trigger", sa.Text, nullable=True),
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
    op.create_unique_constraint("uq_test_coverage_project_title", "test_coverage",
                                ["project_name", "title"])

    # Indexes
    op.create_index("ix_test_coverage_project_category", "test_coverage",
                    ["project_name", "category"])
    op.create_index("ix_test_coverage_delta", "test_coverage", ["delta"])
    op.create_index("ix_test_coverage_created", "test_coverage", ["created_at"])
    op.create_index("ix_test_coverage_tags", "test_coverage", ["tags"],
                    postgresql_using="gin")
    op.create_index("ix_test_coverage_search", "test_coverage", ["search_vector"],
                    postgresql_using="gin")

    # Auto-populate search_vector on INSERT/UPDATE
    op.execute("""
        CREATE OR REPLACE FUNCTION test_coverage_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.title, '') || ' ' ||
                coalesce(NEW.trigger, '') || ' ' ||
                coalesce(NEW.project_name, '') || ' ' ||
                coalesce(NEW.category, '') || ' ' ||
                coalesce(array_to_string(NEW.tests_added, ' '), '') || ' ' ||
                coalesce(array_to_string(NEW.tests_removed, ' '), '') || ' ' ||
                coalesce(array_to_string(NEW.tests_modified, ' '), '') || ' ' ||
                coalesce(array_to_string(NEW.files_affected, ' '), '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER test_coverage_search_vector_trigger
            BEFORE INSERT OR UPDATE ON test_coverage
            FOR EACH ROW EXECUTE FUNCTION test_coverage_search_vector_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS test_coverage_search_vector_trigger ON test_coverage;")
    op.execute("DROP FUNCTION IF EXISTS test_coverage_search_vector_update();")
    op.drop_table("test_coverage")
