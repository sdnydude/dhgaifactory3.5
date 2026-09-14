"""recreate the projects table (and conversations.project_id) lost to schema drift

Revision ID: 035
Revises: 034
Create Date: 2026-09-05

Migration 002_claude_data created projects/conversations/messages/artifacts, and
no later migration drops any of them, yet the live registry database has
`conversations` (built by hand: text columns, uuid_generate_v4() defaults, no
`project_id`) and no `projects` at all. alembic_version was already at 034, so
002's DDL was never going to be replayed.

The visible consequence: GET /api/v1/projects returned 500. claude_service.list_projects
issues `FROM projects LEFT OUTER JOIN conversations ON conversations.project_id =
projects.id`, so the endpoint needs both halves — creating `projects` alone just
moves the error from `relation "projects" does not exist` to `column
conversations.project_id does not exist` (verified in a rolled-back transaction
against the live database before writing this).

Scope is deliberately additive. `conversations` holds live rows, so its existing
columns and types are left exactly as they are; the only change there is the
nullable `project_id` FK that migration 002 always specified. Nothing is dropped
and no row is rewritten.

Both steps are guarded on current schema state so this replays cleanly against a
database where 002 did apply normally.
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


# Offline (`alembic upgrade --sql`) has no connection to inspect, so each guard
# takes the answer to assume there: the one that makes the generated script emit
# the full DDL for review.
def _has_table(name: str, *, offline: bool) -> bool:
    if context.is_offline_mode():
        return offline
    return sa.inspect(op.get_bind()).has_table(name)


def _has_column(table: str, column: str, *, offline: bool) -> bool:
    if context.is_offline_mode():
        return offline
    inspector = sa.inspect(op.get_bind())
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    # projects — column-for-column as models.Project / migration 002.
    if not _has_table("projects", offline=False):
        op.create_table(
            "projects",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("name", sa.String(512), nullable=False),
            sa.Column("project_id", sa.String(256), nullable=True, unique=True),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("custom_instructions", sa.Text, nullable=True),
            sa.Column("knowledge_files", JSONB, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
            sa.Column("meta_data", JSONB, nullable=True),
        )
        op.create_index("idx_projects_name", "projects", ["name"])
        op.create_index("idx_projects_created_at", "projects", ["created_at"])

    # conversations.project_id — the FK migration 002 specified. Additive only:
    # nullable, no default, no backfill, existing columns untouched.
    if _has_table("conversations", offline=True) and not _has_column(
        "conversations", "project_id", offline=False
    ):
        op.add_column(
            "conversations",
            sa.Column("project_id", UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "conversations_project_id_fkey",
            "conversations",
            "projects",
            ["project_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("idx_conversations_project_id", "conversations", ["project_id"])


def downgrade() -> None:
    if _has_table("conversations", offline=True) and _has_column(
        "conversations", "project_id", offline=True
    ):
        op.drop_index("idx_conversations_project_id", table_name="conversations")
        op.drop_constraint(
            "conversations_project_id_fkey", "conversations", type_="foreignkey"
        )
        op.drop_column("conversations", "project_id")

    if _has_table("projects", offline=True):
        op.drop_index("idx_projects_created_at", table_name="projects")
        op.drop_index("idx_projects_name", table_name="projects")
        op.drop_table("projects")
