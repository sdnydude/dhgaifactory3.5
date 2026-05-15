"""Add KB search infrastructure to dev_changelog

Revision ID: 022
Revises: 021
Create Date: 2026-05-15

Adds project_name, search_vector, embedding columns to dev_changelog so it
can participate in the unified KB search endpoint as the 7th source.
Backfills search_vector for existing 16 rows.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- new columns ---
    op.add_column("dev_changelog", sa.Column(
        "project_name", sa.String(100), nullable=False, server_default="shared",
    ))
    op.add_column("dev_changelog", sa.Column(
        "search_vector", postgresql.TSVECTOR, nullable=True,
    ))
    op.add_column("dev_changelog", sa.Column(
        "embedding", Vector(768), nullable=True,
    ))
    op.add_column("dev_changelog", sa.Column(
        "embedding_model", sa.String(64), nullable=True,
    ))

    # --- indexes ---
    op.create_index("ix_dev_changelog_project_name", "dev_changelog", ["project_name"])
    op.create_index("ix_dev_changelog_search", "dev_changelog", ["search_vector"],
                    postgresql_using="gin")

    # --- trigger: auto-populate search_vector on INSERT/UPDATE ---
    op.execute("""
        CREATE OR REPLACE FUNCTION dev_changelog_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.epic, '') || ' ' ||
                coalesce(NEW.key_insight, '') || ' ' ||
                coalesce(NEW.notes, '') || ' ' ||
                coalesce(NEW.category, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER dev_changelog_search_vector_trigger
            BEFORE INSERT OR UPDATE ON dev_changelog
            FOR EACH ROW EXECUTE FUNCTION dev_changelog_search_vector_update();
    """)

    # --- backfill search_vector for existing rows ---
    op.execute("""
        UPDATE dev_changelog SET search_vector = to_tsvector('english',
            coalesce(epic, '') || ' ' ||
            coalesce(key_insight, '') || ' ' ||
            coalesce(notes, '') || ' ' ||
            coalesce(category, '')
        )
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS dev_changelog_search_vector_trigger ON dev_changelog;")
    op.execute("DROP FUNCTION IF EXISTS dev_changelog_search_vector_update();")
    op.drop_index("ix_dev_changelog_search", table_name="dev_changelog")
    op.drop_index("ix_dev_changelog_project_name", table_name="dev_changelog")
    op.drop_column("dev_changelog", "embedding_model")
    op.drop_column("dev_changelog", "embedding")
    op.drop_column("dev_changelog", "search_vector")
    op.drop_column("dev_changelog", "project_name")
