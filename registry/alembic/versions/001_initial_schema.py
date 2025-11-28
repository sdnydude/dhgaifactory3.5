"""Initial schema - media, transcripts, segments, events tables

Revision ID: 001_initial
Revises: 
Create Date: 2025-11-28 15:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create media table
    op.create_table(
        'media',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('filename', sa.String(512), nullable=False),
        sa.Column('filepath', sa.String(1024), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger, nullable=False),
        sa.Column('mime_type', sa.String(128), nullable=False),
        sa.Column('duration_seconds', sa.Float, nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='pending'),
        sa.Column('meta_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('idx_media_status', 'media', ['status'])
    op.create_index('idx_media_created_at', 'media', ['created_at'])
    
    # Create transcripts table
    op.create_table(
        'transcripts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('media_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('full_text', sa.Text, nullable=False),
        sa.Column('language', sa.String(16), nullable=True),
        sa.Column('confidence_score', sa.Float, nullable=True),
        sa.Column('model_name', sa.String(64), nullable=True),
        sa.Column('model_version', sa.String(32), nullable=True),
        sa.Column('processing_time_seconds', sa.Float, nullable=False),
        sa.Column('meta_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['media_id'], ['media.id'], ondelete='CASCADE')
    )
    op.create_index('idx_transcripts_media_id', 'transcripts', ['media_id'])
    op.create_index('idx_transcripts_created_at', 'transcripts', ['created_at'])
    
    # Create segments table (timestamped segments)
    op.create_table(
        'segments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('transcript_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('segment_index', sa.Integer, nullable=False),
        sa.Column('start_time_seconds', sa.Float, nullable=False),
        sa.Column('end_time_seconds', sa.Float, nullable=False),
        sa.Column('text', sa.Text, nullable=False),
        sa.Column('confidence_score', sa.Float, nullable=True),
        sa.Column('speaker_id', sa.String(64), nullable=True),
        sa.Column('meta_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['transcript_id'], ['transcripts.id'], ondelete='CASCADE')
    )
    op.create_index('idx_segments_transcript_id', 'segments', ['transcript_id'])
    op.create_index('idx_segments_times', 'segments', ['start_time_seconds', 'end_time_seconds'])
    
    # Create events table (audit log)
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('entity_type', sa.String(64), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', sa.String(128), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('meta_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('idx_events_type', 'events', ['event_type'])
    op.create_index('idx_events_entity', 'events', ['entity_type', 'entity_id'])
    op.create_index('idx_events_created_at', 'events', ['created_at'])


def downgrade() -> None:
    op.drop_table('events')
    op.drop_table('segments')
    op.drop_table('transcripts')
    op.drop_table('media')
