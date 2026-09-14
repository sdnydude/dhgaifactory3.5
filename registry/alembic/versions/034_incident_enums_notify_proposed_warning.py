"""incident enums: remediation_mode 'notify', action_type 'proposed', severity 'warning'

Revision ID: 034
Revises: 033
Create Date: 2026-09-05

The remediator is now notify-only (services/remediator): it runs allowlisted
read-only diagnostics and records anything else as a proposal instead of
executing it. Three enum values make the table say so:

- remediation_mode 'notify'  — the only mode observability/runbooks/*.yml uses.
- incident_action_type 'proposed' — a step whose command is not on the
  allowlist, recorded with its command text and never run.
- incident_severity 'warning' — the alert taxonomy's third value (the rule
  files use critical|high|warning; 'medium' is retired), so a runbook row for
  a warning alert can carry its real severity.

ALTER TYPE ... ADD VALUE cannot be undone; downgrade is a documented no-op.
"""
from __future__ import annotations

from alembic import op


revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE remediation_mode ADD VALUE IF NOT EXISTS 'notify'")
    op.execute("ALTER TYPE incident_action_type ADD VALUE IF NOT EXISTS 'proposed'")
    op.execute("ALTER TYPE incident_severity ADD VALUE IF NOT EXISTS 'warning'")


def downgrade() -> None:
    # PostgreSQL has no ALTER TYPE ... DROP VALUE. The values are inert if
    # unused; removing them would require rebuilding three enum types.
    pass
