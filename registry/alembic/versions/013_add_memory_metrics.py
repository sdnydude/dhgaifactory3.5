"""add memory_metrics table

Revision ID: 013
Revises: 012
Create Date: 2026-05-09

Tracks memory intelligence sync results — pattern detection, pruning, health.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project", sa.String(100), nullable=False),
        sa.Column("sync_mode", sa.String(10), nullable=False),
        sa.Column("sync_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hot_areas", postgresql.JSONB, nullable=True),
        sa.Column("workflow_distribution", postgresql.JSONB, nullable=True),
        sa.Column("workflow_trend", postgresql.JSONB, nullable=True),
        sa.Column("memory_health", postgresql.JSONB, nullable=False),
        sa.Column("decision_stats", postgresql.JSONB, nullable=True),
        sa.Column("contradictions", postgresql.JSONB, nullable=True),
        sa.Column("unfinished_branches", postgresql.JSONB, nullable=True),
        sa.Column("journal_backfills", sa.Integer, nullable=True),
        sa.Column("patterns_detected", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_memory_metrics_project", "memory_metrics", ["project"])
    op.create_index("ix_memory_metrics_project_created", "memory_metrics", ["project", "created_at"])


def downgrade() -> None:
    op.drop_table("memory_metrics")
