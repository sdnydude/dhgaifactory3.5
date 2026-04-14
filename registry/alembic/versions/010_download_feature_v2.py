"""download feature v2

Revision ID: 010
Revises: 009
Create Date: 2026-04-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # download_jobs: add project_id + selected_document_ids
    op.add_column(
        "download_jobs",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "download_jobs",
        sa.Column("selected_document_ids", postgresql.JSONB, nullable=True),
    )
    op.create_foreign_key(
        "fk_download_jobs_project",
        "download_jobs",
        "cme_projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_download_jobs_project_status",
        "download_jobs",
        ["project_id", "status"],
    )

    # Widen scope CHECK
    op.drop_constraint(
        "download_jobs_scope_check", "download_jobs", type_="check"
    )
    op.create_check_constraint(
        "download_jobs_scope_check",
        "download_jobs",
        "scope IN ('document','project_bundle','drive_sync')",
    )

    # cme_projects: Drive tracking
    op.add_column(
        "cme_projects",
        sa.Column("drive_folder_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "cme_projects",
        sa.Column(
            "drive_last_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "cme_projects",
        sa.Column("drive_sync_status", sa.Text(), nullable=True),
    )

    # cme_documents: Drive tracking
    op.add_column(
        "cme_documents",
        sa.Column("drive_file_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "cme_documents",
        sa.Column(
            "drive_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "cme_documents",
        sa.Column("drive_md5", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cme_documents", "drive_md5")
    op.drop_column("cme_documents", "drive_synced_at")
    op.drop_column("cme_documents", "drive_file_id")
    op.drop_column("cme_projects", "drive_sync_status")
    op.drop_column("cme_projects", "drive_last_synced_at")
    op.drop_column("cme_projects", "drive_folder_id")

    # Remove rows that would violate the narrow v1 constraint before reinstating it.
    # These are transient download jobs; losing them on downgrade is acceptable.
    op.execute(
        "DELETE FROM download_jobs WHERE scope IN ('project_bundle','drive_sync')"
    )
    op.drop_constraint(
        "download_jobs_scope_check", "download_jobs", type_="check"
    )
    op.create_check_constraint(
        "download_jobs_scope_check",
        "download_jobs",
        "scope IN ('document','project')",
    )

    op.drop_index(
        "ix_download_jobs_project_status", table_name="download_jobs"
    )
    op.drop_constraint(
        "fk_download_jobs_project", "download_jobs", type_="foreignkey"
    )
    op.drop_column("download_jobs", "selected_document_ids")
    op.drop_column("download_jobs", "project_id")
