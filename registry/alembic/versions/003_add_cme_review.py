"""Add CME review workflow tables

Revision ID: 003_add_cme_review
Revises: 002_add_claude_data
Create Date: 2026-02-04

Implements decisions R1-R7:
- R1: Admin-configurable reviewer assignment
- R2: Up to 3 reviewers per project
- R3: 24-hour SLA per reviewer
- R4/R5: Timeout escalation
- R6: Email + Google Chat notifications
- R7: Plate JS annotation storage
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers
revision = '003_add_cme_review'
down_revision = '002_claude_data'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create cme_reviewer_config table
    op.create_table(
        'cme_reviewer_config',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('max_concurrent_reviews', sa.Integer(), default=5),
        sa.Column('notify_email', sa.Boolean(), default=True),
        sa.Column('notify_google_chat', sa.Boolean(), default=True),
        sa.Column('google_chat_webhook_url', sa.String(500), nullable=True),
        sa.Column('total_reviews', sa.Integer(), default=0),
        sa.Column('avg_review_time_hours', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create cme_review_assignments table
    op.create_table(
        'cme_review_assignments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('cme_projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('reviewer_id', UUID(as_uuid=True), sa.ForeignKey('cme_reviewer_config.id'), nullable=False, index=True),
        sa.Column('reviewer_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sla_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decision', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('annotations', JSONB, default=[]),
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('escalation_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Add index for finding active assignments by deadline (for timeout handler)
    op.create_index(
        'ix_cme_review_assignments_sla_lookup',
        'cme_review_assignments',
        ['status', 'sla_deadline'],
        postgresql_where=sa.text("status = 'active'")
    )


def downgrade() -> None:
    op.drop_index('ix_cme_review_assignments_sla_lookup', table_name='cme_review_assignments')
    op.drop_table('cme_review_assignments')
    op.drop_table('cme_reviewer_config')
