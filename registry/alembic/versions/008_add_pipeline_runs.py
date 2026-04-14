"""Add cme_pipeline_runs table + intake_version/current_run_id on cme_projects

Revision ID: 008
Create Date: 2026-04-13

Adds run-level tracking for CME pipeline executions. Each rerun of a project
creates a new row in cme_pipeline_runs, enabling history, cancel, and future
rerun-from-step workflows. Backfills one row per existing project that has
an associated LangGraph thread.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cme_pipeline_runs",
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cme_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_number", sa.Integer, nullable=False),
        sa.Column("thread_id", sa.String(100), nullable=False),
        sa.Column("langgraph_run_id", sa.String(100), nullable=False),
        sa.Column(
            "intake_version_used",
            sa.Integer,
            nullable=False,
            server_default="1",
        ),
        sa.Column("triggered_by", sa.String(255), nullable=True),
        sa.Column(
            "trigger_reason",
            sa.String(32),
            nullable=False,
            server_default="manual",
            comment="initial | manual | retry | auto",
        ),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="processing",
            comment="processing | success | failed | cancelled",
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("final_agent", sa.String(100), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_cme_pipeline_runs_project_run",
        "cme_pipeline_runs",
        ["project_id", sa.text("run_number DESC")],
    )
    op.create_index(
        "ix_cme_pipeline_runs_status",
        "cme_pipeline_runs",
        ["status"],
    )
    op.create_unique_constraint(
        "uq_cme_pipeline_runs_project_run_number",
        "cme_pipeline_runs",
        ["project_id", "run_number"],
    )

    op.add_column(
        "cme_projects",
        sa.Column(
            "intake_version",
            sa.Integer,
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "cme_projects",
        sa.Column(
            "current_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cme_pipeline_runs.run_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Backfill: create a run_number=1 row for every project that already
    # has a pipeline_thread_id. Status derived from current project state.
    # Projects still in 'intake' have no run yet — skipped.
    op.get_bind().exec_driver_sql("""
INSERT INTO cme_pipeline_runs (
    project_id,
    run_number,
    thread_id,
    langgraph_run_id,
    intake_version_used,
    trigger_reason,
    triggered_at,
    completed_at,
    status,
    final_agent
)
SELECT
    p.id,
    1,
    COALESCE(p.pipeline_thread_id, 'legacy-' || p.id::text),
    COALESCE(p.langsmith_run_id, 'legacy-' || p.id::text),
    1,
    'initial',
    p.started_at,
    p.completed_at,
    CASE p.status
        WHEN 'processing' THEN 'processing'
        WHEN 'review'     THEN 'processing'
        WHEN 'complete'   THEN 'success'
        WHEN 'failed'     THEN 'failed'
        WHEN 'cancelled'  THEN 'cancelled'
        WHEN 'archived'   THEN 'success'
        ELSE 'processing'
    END,
    p.current_agent
FROM cme_projects p
WHERE p.status != 'intake'
  AND p.started_at IS NOT NULL;
""")

    # Point current_run_id at the backfilled row for each project.
    op.get_bind().exec_driver_sql("""
UPDATE cme_projects p
SET current_run_id = r.run_id
FROM cme_pipeline_runs r
WHERE r.project_id = p.id
  AND r.run_number = 1;
""")


def downgrade():
    op.drop_column("cme_projects", "current_run_id")
    op.drop_column("cme_projects", "intake_version")
    op.drop_constraint(
        "uq_cme_pipeline_runs_project_run_number",
        "cme_pipeline_runs",
        type_="unique",
    )
    op.drop_index("ix_cme_pipeline_runs_status", table_name="cme_pipeline_runs")
    op.drop_index("ix_cme_pipeline_runs_project_run", table_name="cme_pipeline_runs")
    op.drop_table("cme_pipeline_runs")
