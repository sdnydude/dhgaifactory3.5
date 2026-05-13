"""add doc_pages table

Revision ID: 017
Revises: 016
Create Date: 2026-05-10

Documentation pages ingested from DHG project markdown files.
Chunks stored with pgvector embeddings (nomic-embed-text, 768 dims)
and full-text search. Unique constraint on (project, file, chunk)
for idempotent upsert.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "doc_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_name", sa.String(100), nullable=False),
        sa.Column("source_file", sa.String(500), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("heading_path", sa.String(500), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("embedding_model", sa.String(100), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("meta_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("project_name", "source_file", "chunk_index",
                            name="uq_doc_pages_file_chunk"),
    )

    op.create_index("ix_doc_pages_project_file", "doc_pages",
                    ["project_name", "source_file"])
    op.create_index("ix_doc_pages_created", "doc_pages", ["created_at"])
    op.create_index("ix_doc_pages_tags", "doc_pages", ["tags"],
                    postgresql_using="gin")
    op.create_index("ix_doc_pages_search", "doc_pages", ["search_vector"],
                    postgresql_using="gin")

    op.execute("""
        CREATE OR REPLACE FUNCTION doc_pages_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.title, '') || ' ' ||
                coalesce(NEW.content, '') || ' ' ||
                coalesce(NEW.heading_path, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER doc_pages_search_vector_trigger
            BEFORE INSERT OR UPDATE ON doc_pages
            FOR EACH ROW EXECUTE FUNCTION doc_pages_search_vector_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS doc_pages_search_vector_trigger ON doc_pages")
    op.execute("DROP FUNCTION IF EXISTS doc_pages_search_vector_update()")
    op.drop_table("doc_pages")
