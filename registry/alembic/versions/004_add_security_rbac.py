"""Add security RBAC tables

Revision ID: 004_add_security_rbac
Revises: 003_add_cme_review
Create Date: 2026-04-06

Defense-in-depth Layer 4: PostgreSQL RBAC tables.
  - security_users: authenticated identities (Cloudflare Access)
  - security_roles: admin, operations, finance, editor, viewer
  - security_user_roles: many-to-many user-role assignments
  - security_project_access: per-project access grants
  - security_audit_log: immutable action trail
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers
revision = '004_add_security_rbac'
down_revision = '003_add_cme_review'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- security_users ---
    op.create_table(
        'security_users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('cloudflare_id', sa.String(255), unique=True, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- security_roles ---
    op.create_table(
        'security_roles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('permissions', JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- security_user_roles ---
    op.create_table(
        'security_user_roles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('security_users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role_id', UUID(as_uuid=True), sa.ForeignKey('security_roles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('granted_by', UUID(as_uuid=True), sa.ForeignKey('security_users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_security_user_role'),
    )

    # --- security_project_access ---
    op.create_table(
        'security_project_access',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('security_users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('cme_projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('access_level', sa.String(50), nullable=False, server_default=sa.text("'viewer'")),
        sa.Column('granted_by', UUID(as_uuid=True), sa.ForeignKey('security_users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'project_id', name='uq_security_user_project'),
    )

    # --- security_audit_log ---
    op.create_table(
        'security_audit_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('security_users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('action', sa.String(100), nullable=False, index=True),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('detail', JSONB, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )

    # --- Seed default roles ---
    op.execute("""
        INSERT INTO security_roles (name, description, permissions) VALUES
        ('admin', 'Full system access — user management, role assignment, all projects, settings', '{"users.read": true, "users.write": true, "users.delete": true, "roles.read": true, "roles.write": true, "projects.read": true, "projects.write": true, "projects.delete": true, "reviews.read": true, "reviews.write": true, "audit.read": true, "settings.read": true, "settings.write": true, "all_projects": true}'::jsonb),
        ('operations', 'Project management and team operations', '{"users.read": true, "projects.read": true, "projects.write": true, "reviews.read": true, "reviews.write": true, "audit.read": true, "all_projects": true}'::jsonb),
        ('finance', 'Financial data access — project costs, reports, budgets', '{"projects.read": true, "reports.read": true, "costs.read": true, "all_projects": true}'::jsonb),
        ('editor', 'Content editing on assigned projects with review comments', '{"projects.read": true, "projects.write": true, "reviews.read": true, "reviews.write": true}'::jsonb),
        ('viewer', 'Read-only access to assigned projects', '{"projects.read": true, "reviews.read": true}'::jsonb)
        ON CONFLICT (name) DO UPDATE SET
            description = EXCLUDED.description,
            permissions = EXCLUDED.permissions;
    """)

    # --- Seed initial admin user (Stephen Webber) ---
    op.execute("""
        INSERT INTO security_users (email, display_name)
        VALUES ('swebber@fafstudios.com', 'Stephen Webber')
        ON CONFLICT (email) DO NOTHING;
    """)
    op.execute("""
        INSERT INTO security_user_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM security_users u, security_roles r
        WHERE u.email = 'swebber@fafstudios.com' AND r.name = 'admin'
        ON CONFLICT ON CONSTRAINT uq_security_user_role DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('security_audit_log')
    op.drop_table('security_project_access')
    op.drop_table('security_user_roles')
    op.drop_table('security_roles')
    op.drop_table('security_users')
