-- =============================================================================
-- DHG AI Factory - Database Initialization
-- =============================================================================
-- This script runs when PostgreSQL container starts for the first time
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS transcriptions;
CREATE SCHEMA IF NOT EXISTS content;

-- =============================================================================
-- Transcriptions Schema
-- =============================================================================

CREATE TABLE IF NOT EXISTS transcriptions.jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    source_file VARCHAR(500),
    source_url VARCHAR(1000),
    duration_seconds INTEGER,
    language VARCHAR(10),
    model_used VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS transcriptions.segments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES transcriptions.jobs(id) ON DELETE CASCADE,
    segment_index INTEGER NOT NULL,
    start_time DECIMAL(10, 3) NOT NULL,
    end_time DECIMAL(10, 3) NOT NULL,
    text TEXT NOT NULL,
    speaker VARCHAR(100),
    confidence DECIMAL(5, 4),
    language VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transcriptions.speakers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES transcriptions.jobs(id) ON DELETE CASCADE,
    speaker_id VARCHAR(50) NOT NULL,
    speaker_label VARCHAR(200),
    total_duration DECIMAL(10, 3),
    word_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transcriptions.outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES transcriptions.jobs(id) ON DELETE CASCADE,
    format VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    file_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_jobs_status ON transcriptions.jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON transcriptions.jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_segments_job ON transcriptions.segments(job_id);
CREATE INDEX IF NOT EXISTS idx_speakers_job ON transcriptions.speakers(job_id);

-- =============================================================================
-- Content Schema (CME and general content)
-- =============================================================================

CREATE TABLE IF NOT EXISTS content.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    source_url VARCHAR(1000),
    file_path VARCHAR(500),
    is_cme BOOLEAN DEFAULT FALSE,
    accme_tags JSONB DEFAULT '[]'::jsonb,
    modality VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS content.versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES content.documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    content TEXT,
    changes_summary TEXT,
    created_by VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_type ON content.documents(content_type);
CREATE INDEX IF NOT EXISTS idx_documents_cme ON content.documents(is_cme);
CREATE INDEX IF NOT EXISTS idx_versions_doc ON content.versions(document_id);

-- =============================================================================
-- Audit Log
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id UUID,
    user_id VARCHAR(200),
    details JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_action ON public.audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON public.audit_log(created_at);

-- =============================================================================
-- Grant permissions (Onyx user if created separately)
-- =============================================================================

-- Onyx will use the postgres user by default, so no additional grants needed

COMMENT ON SCHEMA transcriptions IS 'Transcription processing and storage';
COMMENT ON SCHEMA content IS 'CME and general content management';
