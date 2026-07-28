"""add agent_findings, agent_actions, resolution to burndown_items

Revision ID: 028
Revises: 027
Create Date: 2026-06-05

Adds columns for tracking agent (Claude) findings and actions during burndown
walkthroughs, plus a `resolution` state to drive items to closure independently
of the pass/fail check `status`. Existing rows backfill to resolution='open'.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("burndown_items", sa.Column("agent_findings", sa.Text, nullable=True))
    op.add_column("burndown_items", sa.Column("agent_actions", sa.Text, nullable=True))
    op.add_column(
        "burndown_items",
        sa.Column("resolution", sa.String(20), nullable=False, server_default="open"),
    )


def downgrade() -> None:
    op.drop_column("burndown_items", "resolution")
    op.drop_column("burndown_items", "agent_actions")
    op.drop_column("burndown_items", "agent_findings")
