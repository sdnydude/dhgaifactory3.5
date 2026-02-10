-- DHG Audio Analysis Agent — Initial Migration
-- Creates jobs and results tables per Build Spec Section 7

-- Enable pgvector extension for future semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Jobs table: tracks processing state
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audio_path TEXT NOT NULL,
    language_id VARCHAR(10),
    diarize BOOLEAN DEFAULT TRUE,
    num_speakers INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    progress FLOAT DEFAULT 0.0,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Results table: stores completed analysis output
CREATE TABLE IF NOT EXISTS results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    transcript_text TEXT NOT NULL,
    transcript_segments JSONB NOT NULL,
    detected_language VARCHAR(10) NOT NULL,
    confidence FLOAT NOT NULL,
    translation TEXT,
    summary TEXT NOT NULL,
    topics JSONB NOT NULL,
    duration_seconds FLOAT NOT NULL,
    processing_seconds FLOAT NOT NULL,
    transcript_embedding vector(1536),  -- For future semantic search
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_results_job_id ON results(job_id);
