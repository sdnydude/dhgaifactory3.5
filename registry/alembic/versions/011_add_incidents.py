"""add incident management tables

Revision ID: 011
Revises: 010
Create Date: 2026-04-16

Adds incidents, incident_events, incident_actions, incident_runbooks,
and incident_postmortems tables with PostgreSQL enum types for severity,
status, category, root cause, event type, action type, and remediation mode.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None

# ---------- enum definitions ----------

incident_severity = postgresql.ENUM(
    "critical", "high", "medium", "low",
    name="incident_severity",
    create_type=False,
)

incident_status = postgresql.ENUM(
    "active", "mitigated", "resolved", "postmortem",
    name="incident_status",
    create_type=False,
)

incident_category = postgresql.ENUM(
    "infrastructure", "pipeline", "data", "integration", "security", "performance",
    name="incident_category",
    create_type=False,
)

root_cause_category = postgresql.ENUM(
    "memory_leak", "config_error", "type_error", "dependency_failure",
    "resource_exhaustion", "network", "crash_loop", "connection_leak",
    "disk_pressure", "other",
    name="root_cause_category",
    create_type=False,
)

incident_event_type = postgresql.ENUM(
    "symptom", "diagnosis", "escalation", "action", "resolution", "notification",
    name="incident_event_type",
    create_type=False,
)

incident_action_type = postgresql.ENUM(
    "diagnostic", "mitigation", "fix", "prevention", "auto_remediation",
    name="incident_action_type",
    create_type=False,
)

remediation_mode = postgresql.ENUM(
    "auto", "approval", "none",
    name="remediation_mode",
    create_type=False,
)


def upgrade() -> None:
    # ---- create enum types ----
    incident_severity.create(op.get_bind(), checkfirst=True)
    incident_status.create(op.get_bind(), checkfirst=True)
    incident_category.create(op.get_bind(), checkfirst=True)
    root_cause_category.create(op.get_bind(), checkfirst=True)
    incident_event_type.create(op.get_bind(), checkfirst=True)
    incident_action_type.create(op.get_bind(), checkfirst=True)
    remediation_mode.create(op.get_bind(), checkfirst=True)

    # ---- incidents ----
    op.create_table(
        "incidents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("severity", incident_severity, nullable=False),
        sa.Column(
            "status",
            incident_status,
            nullable=False,
            server_default="active",
        ),
        sa.Column("category", incident_category, nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("root_cause_category", root_cause_category, nullable=True),
        sa.Column("impact_summary", sa.Text(), nullable=True),
        sa.Column("prevention", sa.Text(), nullable=True),
        sa.Column("trigger_rule", sa.String(50), nullable=True),
        sa.Column(
            "affected_services",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "affected_project_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "parent_incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "pipeline_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cme_pipeline_runs.run_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("system_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("mitigated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index(
        "ix_incidents_created_at",
        "incidents",
        [sa.text("created_at DESC")],
    )
    op.create_index("ix_incidents_trigger_rule", "incidents", ["trigger_rule"])
    op.create_index("ix_incidents_parent", "incidents", ["parent_incident_id"])
    op.create_index(
        "ix_incidents_affected_services",
        "incidents",
        ["affected_services"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_incidents_tags",
        "incidents",
        ["tags"],
        postgresql_using="gin",
    )

    # updated_at trigger — reuses the update_updated_at_column() function
    # already present in the database (created by 001_add_agents.sql)
    op.execute("""
        CREATE TRIGGER update_incidents_updated_at
            BEFORE UPDATE ON incidents
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # ---- incident_events ----
    op.create_table(
        "incident_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("event_type", incident_event_type, nullable=False),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_incident_events_incident_id",
        "incident_events",
        ["incident_id"],
    )
    op.create_index(
        "ix_incident_events_timestamp",
        "incident_events",
        [sa.text("timestamp DESC")],
    )

    # ---- incident_actions ----
    op.create_table(
        "incident_actions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_type", incident_action_type, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("command", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column(
            "performed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("performed_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_incident_actions_incident_id",
        "incident_actions",
        ["incident_id"],
    )

    # ---- incident_runbooks ----
    op.create_table(
        "incident_runbooks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "trigger_rule",
            sa.String(50),
            nullable=False,
            unique=True,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", incident_severity, nullable=False),
        sa.Column(
            "remediation_mode",
            remediation_mode,
            nullable=False,
            server_default="none",
        ),
        sa.Column(
            "steps",
            postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "container_allowlist",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # updated_at trigger for runbooks
    op.execute("""
        CREATE TRIGGER update_incident_runbooks_updated_at
            BEFORE UPDATE ON incident_runbooks
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # ---- incident_postmortems ----
    op.create_table(
        "incident_postmortems",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("timeline_markdown", sa.Text(), nullable=True),
        sa.Column("root_cause_analysis", sa.Text(), nullable=True),
        sa.Column("impact_analysis", sa.Text(), nullable=True),
        sa.Column("resolution_details", sa.Text(), nullable=True),
        sa.Column("prevention_measures", sa.Text(), nullable=True),
        sa.Column("lessons_learned", sa.Text(), nullable=True),
        sa.Column("sla_metrics", postgresql.JSONB, nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("edited_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    # drop tables in reverse order
    op.drop_table("incident_postmortems")

    op.execute("DROP TRIGGER IF EXISTS update_incident_runbooks_updated_at ON incident_runbooks")
    op.drop_table("incident_runbooks")

    op.drop_table("incident_actions")
    op.drop_table("incident_events")

    op.execute("DROP TRIGGER IF EXISTS update_incidents_updated_at ON incidents")
    op.drop_index("ix_incidents_tags", table_name="incidents")
    op.drop_index("ix_incidents_affected_services", table_name="incidents")
    op.drop_index("ix_incidents_parent", table_name="incidents")
    op.drop_index("ix_incidents_trigger_rule", table_name="incidents")
    op.drop_index("ix_incidents_created_at", table_name="incidents")
    op.drop_index("ix_incidents_severity", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_table("incidents")

    # drop enum types
    remediation_mode.drop(op.get_bind(), checkfirst=True)
    incident_action_type.drop(op.get_bind(), checkfirst=True)
    incident_event_type.drop(op.get_bind(), checkfirst=True)
    root_cause_category.drop(op.get_bind(), checkfirst=True)
    incident_category.drop(op.get_bind(), checkfirst=True)
    incident_status.drop(op.get_bind(), checkfirst=True)
    incident_severity.drop(op.get_bind(), checkfirst=True)
