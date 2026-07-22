"""add burndown_lists and burndown_items tables

Revision ID: 027
Revises: 026
Create Date: 2026-06-04

Project-agnostic burndown list tracking for feature verification, debugging
sessions, and release checklists. Two tables: burndown_lists (the list itself)
and burndown_items (individual checkable items with status, severity, comments).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "burndown_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(280), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("project_name", sa.String(100), nullable=False),
        sa.Column("list_type", sa.String(40), nullable=False, server_default="debug"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("meta_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    op.create_index("ix_burndown_lists_project", "burndown_lists", ["project_name"])
    op.create_index("ix_burndown_lists_status", "burndown_lists", ["status"])

    op.create_table(
        "burndown_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("list_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("burndown_lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("feature", sa.String(280), nullable=False),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("what_to_check", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="not_started"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="none"),
        sa.Column("user_comment", sa.Text, nullable=True),
        sa.Column("console_errors", sa.Text, nullable=True),
        sa.Column("assigned_to", sa.String(100), nullable=True),
        sa.Column("fixed_in_commit", sa.String(100), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    op.create_index("ix_burndown_items_list_id", "burndown_items", ["list_id"])
    op.create_index("ix_burndown_items_status", "burndown_items", ["status"])
    op.create_index("ix_burndown_items_list_seq", "burndown_items", ["list_id", "seq"])


def downgrade() -> None:
    op.drop_table("burndown_items")
    op.drop_table("burndown_lists")
