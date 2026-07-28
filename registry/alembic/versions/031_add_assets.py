"""add assets table

Revision ID: 031
Revises: 030
Create Date: 2026-07-18

Design/media asset catalog — visual, vector, font, and design-source files
collected across drives and grouped by design system (e.g. portage-forest-green).
Idempotent ingest via UNIQUE(project_name, sha256).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("filepath", sa.String(1024), nullable=True),
        sa.Column("source_path", sa.String(1024), nullable=True),
        sa.Column("source_drive", sa.String(32), nullable=True),
        sa.Column("project_name", sa.String(100), nullable=False),
        sa.Column("design_system", sa.String(64), nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("dominant_color", sa.String(9), nullable=True),
        sa.Column("alt_text", sa.Text, nullable=True),
        sa.Column("exif", postgresql.JSONB, nullable=True),
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

    op.create_unique_constraint("uq_assets_project_sha256", "assets",
                                ["project_name", "sha256"])

    op.create_index("ix_assets_project_category", "assets",
                    ["project_name", "category"])
    op.create_index("ix_assets_source_drive", "assets", ["source_drive"])
    op.create_index("ix_assets_design_system", "assets", ["design_system"])
    op.create_index("ix_assets_created", "assets", ["created_at"])
    op.create_index("ix_assets_tags", "assets", ["tags"],
                    postgresql_using="gin")
    op.create_index("ix_assets_search", "assets", ["search_vector"],
                    postgresql_using="gin")

    # Auto-populate search_vector on INSERT/UPDATE (filename + alt_text + tags + facets)
    op.execute("""
        CREATE OR REPLACE FUNCTION assets_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.filename, '') || ' ' ||
                coalesce(NEW.alt_text, '') || ' ' ||
                coalesce(array_to_string(NEW.tags, ' '), '') || ' ' ||
                coalesce(NEW.category, '') || ' ' ||
                coalesce(NEW.design_system, '') || ' ' ||
                coalesce(NEW.project_name, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER assets_search_vector_trigger
            BEFORE INSERT OR UPDATE ON assets
            FOR EACH ROW EXECUTE FUNCTION assets_search_vector_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS assets_search_vector_trigger ON assets;")
    op.execute("DROP FUNCTION IF EXISTS assets_search_vector_update();")
    op.drop_table("assets")
