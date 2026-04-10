"""Add frontend_design_specs table

Revision ID: 006
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "frontend_design_specs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("feature_name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("spec_path", sa.String(512), nullable=False),
        sa.Column("comp_path", sa.String(512), nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("components", JSONB, server_default="[]"),
        sa.Column("design_tokens", JSONB, server_default="{}"),
        sa.Column("visual_polish", JSONB, server_default="{}"),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("implemented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.execute("""
        INSERT INTO frontend_design_specs (
            feature_name, slug, status, spec_path, comp_path, description,
            components, design_tokens, visual_polish
        ) VALUES (
            'Agents Library',
            'agents-library',
            'approved',
            'docs/superpowers/specs/2026-04-09-agents-library-design.md',
            'frontend/src/components/agents/',
            'Interactive agent catalog with grid/list/table views, category filtering, search, live stats, and detail slide-over panel for all 17 LangGraph graphs.',
            '["agents-library.tsx","agents-library-toolbar.tsx","agents-library-grid.tsx","agents-library-list.tsx","agents-library-table.tsx","agent-slide-over.tsx"]'::jsonb,
            '{"category_colors":{"content":"#663399","recipe":"#F77E2D","qa":"#22c55e","infra":"#71717a"},"animation_stagger_ms":40,"animation_duration_ms":350}'::jsonb,
            '{"card_entry_animation":true,"category_hover_shadows":true,"radial_gradient_bg":true,"health_indicator_border":true,"micro_success_bar":true,"table_sticky_header":true}'::jsonb
        );
    """)


def downgrade():
    op.drop_table("frontend_design_specs")
