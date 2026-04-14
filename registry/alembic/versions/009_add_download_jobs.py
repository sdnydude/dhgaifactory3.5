"""add download_jobs table

Revision ID: 009
Revises: 008
Create Date: 2026-04-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "download_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("thread_id", sa.Text(), nullable=False),
        sa.Column("graph_id", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("artifact_sha256", sa.Text(), nullable=True),
        sa.Column("artifact_bytes", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "scope IN ('document','project')",
            name="download_jobs_scope_check",
        ),
        sa.CheckConstraint(
            "status IN ('pending','running','succeeded','failed')",
            name="download_jobs_status_check",
        ),
    )
    op.create_index(
        "ix_download_jobs_status_created_at",
        "download_jobs",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_download_jobs_thread_scope_status",
        "download_jobs",
        ["thread_id", "scope", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_download_jobs_thread_scope_status",
        table_name="download_jobs",
    )
    op.drop_index(
        "ix_download_jobs_status_created_at",
        table_name="download_jobs",
    )
    op.drop_table("download_jobs")
