"""Add unique constraints for upsert idempotency on 4 KB tables

Revision ID: 021
Revises: 020
Create Date: 2026-05-15

Adds DB-level unique constraints as safety nets for app-level upsert logic.
Also adds upsert_key_hash column to corrections (MD5 of user_message) since
user_message is TEXT and can't participate in a btree index directly.

Keys:
  decision_logs:  (project_name, title)
  insights:       (project_name, tldr)
  ship_sessions:  (project_name, left(feature, 255))  — functional index for TEXT col
  corrections:    (project_name, category, upsert_key_hash)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- corrections: add hash column, backfill, make NOT NULL ---
    op.add_column("corrections", sa.Column("upsert_key_hash", sa.String(32), nullable=True))
    op.execute("UPDATE corrections SET upsert_key_hash = md5(user_message) WHERE upsert_key_hash IS NULL")
    op.alter_column("corrections", "upsert_key_hash", nullable=False)

    # --- unique constraints ---
    op.create_unique_constraint(
        "uq_decision_logs_project_title", "decision_logs", ["project_name", "title"],
    )
    op.create_unique_constraint(
        "uq_insights_project_tldr", "insights", ["project_name", "tldr"],
    )
    op.create_unique_constraint(
        "uq_corrections_project_cat_hash", "corrections",
        ["project_name", "category", "upsert_key_hash"],
    )
    # ship_sessions.feature is TEXT — use functional index to stay within btree limits
    op.execute("""
        CREATE UNIQUE INDEX uq_ship_sessions_project_feature
        ON ship_sessions (project_name, left(feature, 255))
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_ship_sessions_project_feature")
    op.drop_constraint("uq_corrections_project_cat_hash", "corrections", type_="unique")
    op.drop_constraint("uq_insights_project_tldr", "insights", type_="unique")
    op.drop_constraint("uq_decision_logs_project_title", "decision_logs", type_="unique")
    op.alter_column("corrections", "upsert_key_hash", nullable=True)
    op.drop_column("corrections", "upsert_key_hash")
