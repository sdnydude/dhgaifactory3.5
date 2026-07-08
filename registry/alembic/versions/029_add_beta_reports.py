"""add beta_reports table

Revision ID: 029
Revises: 028
Create Date: 2026-07-08

Stores beta-tester bug/feedback reports submitted from client apps (e.g.
Portage) — reporter identity, app page, feature area, severity, description,
optional screenshot, and a triage status lifecycle.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "beta_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_name", sa.Text, nullable=False),
        sa.Column("reporter_email", sa.Text, nullable=False),
        sa.Column("reporter_user_id", sa.Text, nullable=True),
        sa.Column("page", sa.Text, nullable=False),
        sa.Column("area", sa.Text, nullable=True),
        sa.Column("severity", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("screenshot_url", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_beta_reports_severity",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'triaged', 'in_progress', 'resolved', 'wont_fix')",
            name="ck_beta_reports_status",
        ),
    )

    # Indexes
    op.create_index("ix_beta_reports_project_status", "beta_reports",
                    ["project_name", "status"])
    op.create_index("ix_beta_reports_severity", "beta_reports", ["severity"])
    op.create_index("ix_beta_reports_created", "beta_reports", ["created_at"])


def downgrade() -> None:
    op.drop_table("beta_reports")
