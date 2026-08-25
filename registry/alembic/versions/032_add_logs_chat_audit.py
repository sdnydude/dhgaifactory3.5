"""add logs_chat_audit table

Revision ID: 032
Revises: 031
Create Date: 2026-08-25

Immutable audit trail for /api/logs/chat (P5 log program T10). Keep-all
directive: the downgrade drops recorded audit rows and is therefore
OPERATOR-ONLY once real rows exist (see the Log Program Runbook, Rollback section).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "logs_chat_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("resolved_container", sa.String(128), nullable=True),
        sa.Column("logql_queries", postgresql.JSONB, nullable=True),
        sa.Column("context_lines", sa.Integer, nullable=False, server_default="0"),
        sa.Column("answer_chars", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("elapsed_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_logs_chat_audit_created_at", "logs_chat_audit", ["created_at"])


def downgrade() -> None:
    # OPERATOR-ONLY once real audit rows exist (keep-all directive 2026-08-23;
    # procedure: docs-site operations/log-program-runbook, Rollback section).
    op.drop_index("ix_logs_chat_audit_created_at", table_name="logs_chat_audit")
    op.drop_table("logs_chat_audit")
