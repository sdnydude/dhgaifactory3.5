"""Add Claude AI data tables

Revision ID: 002_claude_data
Revises: 001_initial
Create Date: 2025-11-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

# revision identifiers
revision = '002_claude_data'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(512), nullable=False),
        sa.Column('project_id', sa.String(256), nullable=True, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('custom_instructions', sa.Text, nullable=True),
        sa.Column('knowledge_files', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('meta_data', JSONB, nullable=True)
    )
    op.create_index('idx_projects_name', 'projects', ['name'])
    op.create_index('idx_projects_created_at', 'projects', ['created_at'])
    
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('title', sa.String(1024), nullable=False),
        sa.Column('conversation_id', sa.String(256), nullable=True, unique=True),
        sa.Column('export_source', sa.String(64), nullable=False),
        sa.Column('model_name', sa.String(128), nullable=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('meta_data', JSONB, nullable=True)
    )
    op.create_index('idx_conversations_title', 'conversations', ['title'])
    op.create_index('idx_conversations_project_id', 'conversations', ['project_id'])
    op.create_index('idx_conversations_created_at', 'conversations', ['created_at'])
    op.create_index('idx_conversations_export_source', 'conversations', ['export_source'])
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message_index', sa.Integer, nullable=False),
        sa.Column('role', sa.String(32), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('attachments', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('meta_data', JSONB, nullable=True)
    )
    op.create_index('idx_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('idx_messages_conversation_index', 'messages', ['conversation_id', 'message_index'])
    op.create_index('idx_messages_role', 'messages', ['role'])
    op.create_index('idx_messages_created_at', 'messages', ['created_at'])
    
    # Create artifacts table
    op.create_table(
        'artifacts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message_id', UUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('artifact_type', sa.String(64), nullable=False),
        sa.Column('language', sa.String(64), nullable=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=True),
        sa.Column('published_url', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('meta_data', JSONB, nullable=True)
    )
    op.create_index('idx_artifacts_conversation_id', 'artifacts', ['conversation_id'])
    op.create_index('idx_artifacts_message_id', 'artifacts', ['message_id'])
    op.create_index('idx_artifacts_type', 'artifacts', ['artifact_type'])
    op.create_index('idx_artifacts_created_at', 'artifacts', ['created_at'])


def downgrade() -> None:
    op.drop_table('artifacts')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('projects')
