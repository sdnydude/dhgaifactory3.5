"""fix embedding dimensions and add embedding to decision_logs

Revision ID: 016
Revises: 015
Create Date: 2026-05-10

Changes insights.embedding from Vector(1536) to Vector(768) to match
the actual embedding model (nomic-embed-text = 768 dims). Adds embedding
and embedding_model columns to decision_logs table.

Note: no existing embeddings are lost — the columns were always NULL
because embedding generation was never wired into the POST endpoints.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("insights", "embedding", type_=Vector(768),
                    existing_type=Vector(1536), existing_nullable=True)

    op.add_column("decision_logs",
                  sa.Column("embedding", Vector(768), nullable=True))
    op.add_column("decision_logs",
                  sa.Column("embedding_model", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("decision_logs", "embedding_model")
    op.drop_column("decision_logs", "embedding")

    op.alter_column("insights", "embedding", type_=Vector(1536),
                    existing_type=Vector(768), existing_nullable=True)
