"""Add verification_status to cme_source_references

Revision ID: 005
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004_add_security_rbac"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cme_source_references",
        sa.Column(
            "verification_status",
            sa.String(50),
            nullable=True,
            index=True,
            comment="verified | not_found | retracted | outdated | landmark",
        ),
    )
    op.add_column(
        "cme_source_references",
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of last verification check",
        ),
    )
    op.add_column(
        "cme_source_references",
        sa.Column(
            "verified_by",
            sa.String(100),
            nullable=True,
            comment="Agent or user that performed verification",
        ),
    )


def downgrade():
    op.drop_column("cme_source_references", "verified_by")
    op.drop_column("cme_source_references", "verified_at")
    op.drop_column("cme_source_references", "verification_status")
