"""add agent_sessions table

Revision ID: 012
Revises: 011
Create Date: 2026-05-09

Tracks Claude Code sessions, scheduled routines, and subagent runs
across all DHG projects.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.String(255), nullable=False),
        sa.Column("project", sa.String(100), nullable=False),
        sa.Column("branch", sa.String(255), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("tldr", sa.Text, nullable=True),
        sa.Column("commits", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("files_changed", sa.Integer, nullable=True),
        sa.Column("skills_used", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("meta_data", postgresql.JSONB, nullable=True),
    )

    op.create_unique_constraint("uq_agent_sessions_session_id", "agent_sessions", ["session_id"])
    op.create_index("ix_agent_sessions_session_id", "agent_sessions", ["session_id"])
    op.create_index("ix_agent_sessions_project", "agent_sessions", ["project"])
    op.create_index("ix_agent_sessions_source", "agent_sessions", ["source"])
    op.create_index("ix_agent_sessions_project_created", "agent_sessions", ["project", "created_at"])


def downgrade() -> None:
    op.drop_table("agent_sessions")
