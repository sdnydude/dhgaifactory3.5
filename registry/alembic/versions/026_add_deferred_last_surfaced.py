"""add last_surfaced_at to deferred_items

Revision ID: 026
Revises: 025
Create Date: 2026-05-28

Adds `last_surfaced_at` timestamp and a covering index for the
(status, priority, created_at) query the briefing materialization uses.

Why: the existing query orders by created_at DESC and limits to 5. Old
high-priority items are structurally invisible once 5 newer items exist.
This migration adds the field needed to track surfacing without bumping
updated_at (which the upsert path already touches), and the index needed
to make age-ascending queries cheap.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "deferred_items",
        sa.Column("last_surfaced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_deferred_items_status_priority_created",
        "deferred_items",
        ["status", "priority", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_deferred_items_status_priority_created",
        table_name="deferred_items",
    )
    op.drop_column("deferred_items", "last_surfaced_at")
