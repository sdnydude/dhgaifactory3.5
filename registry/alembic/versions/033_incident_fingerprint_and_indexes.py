"""incident fingerprint dedup columns + hot-path indexes

Revision ID: 033
Revises: 032
Create Date: 2026-09-05

Two problems, one migration.

1. Alertmanager re-fires created a fresh incident every time the old
   15-minute trigger+service dedup window lapsed (1,112 open incidents from
   14 distinct conditions). `fingerprint` gives a condition a stable identity
   for as long as it stays open; `occurrence_count` and `last_seen_at` carry
   the re-fire information that used to be one new row each.

2. incident_actions had grown to 741 MB / 2.6M rows with no index on
   created_at, so any time-ranged read was a seq scan. Measured build cost on
   the live table: 443 ms, 56 MB — small enough that a plain CREATE INDEX in
   the startup transaction is preferable to the CONCURRENTLY/INVALID-index
   failure mode.

Fully reversible: downgrade drops only what upgrade added. The new columns
are not backfilled — historical incidents keep a NULL fingerprint and are
left to the operator cleanup, so this migration loses nothing.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column("fingerprint", sa.String(255), nullable=True),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "occurrence_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "incidents",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_incidents_fingerprint", "incidents", ["fingerprint"])
    op.create_index(
        "ix_incidents_status_created_at",
        "incidents",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_incident_actions_created_at",
        "incident_actions",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_incident_actions_created_at", table_name="incident_actions")
    op.drop_index("ix_incidents_status_created_at", table_name="incidents")
    op.drop_index("ix_incidents_fingerprint", table_name="incidents")

    op.drop_column("incidents", "last_seen_at")
    op.drop_column("incidents", "occurrence_count")
    op.drop_column("incidents", "fingerprint")
