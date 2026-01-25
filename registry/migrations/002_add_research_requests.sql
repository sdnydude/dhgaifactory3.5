-- Migration: Add research_requests table
-- Date: 2026-01-24

CREATE TABLE IF NOT EXISTS research_requests (
    request_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    agent_type VARCHAR NOT NULL DEFAULT 'cme_research',
    status VARCHAR NOT NULL DEFAULT 'pending',
    
    input_params JSONB NOT NULL,
    output_summary JSONB,
    metadata JSONB,
    
    error_message TEXT,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_research_user_id ON research_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_research_status ON research_requests(status);
CREATE INDEX IF NOT EXISTS idx_research_created_at ON research_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_research_user_created ON research_requests(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_research_status_created ON research_requests(status, created_at);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_research_requests_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER research_requests_updated_at
    BEFORE UPDATE ON research_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_research_requests_updated_at();
