-- Migration: Add cme_projects table for CME Grant pipeline
-- Date: 2026-02-01
-- Note: No data migration needed - test projects in memory can be discarded

-- Create CME project status enum
DO $$ BEGIN
    CREATE TYPE cme_project_status AS ENUM (
        'intake',
        'processing', 
        'review',
        'complete',
        'failed',
        'cancelled'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create cme_projects table
CREATE TABLE IF NOT EXISTS cme_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Project basics
    name VARCHAR(255) NOT NULL,
    status cme_project_status NOT NULL DEFAULT 'intake',
    
    -- Full intake form stored as JSONB (10 sections, 47 fields)
    intake JSONB NOT NULL,
    
    -- Pipeline execution tracking
    current_agent VARCHAR(100),
    progress_percent INTEGER DEFAULT 0,
    agents_completed TEXT[] DEFAULT '{}',
    agents_pending TEXT[] DEFAULT '{}',
    
    -- LangGraph integration
    pipeline_thread_id VARCHAR(100),
    langsmith_run_id VARCHAR(100),
    
    -- Outputs from each agent stored as JSONB
    outputs JSONB DEFAULT '{}',
    
    -- Error tracking
    errors JSONB DEFAULT '[]',
    
    -- Human review
    human_review_status VARCHAR(50),
    human_review_notes TEXT,
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_cme_projects_status ON cme_projects(status);
CREATE INDEX IF NOT EXISTS idx_cme_projects_created_at ON cme_projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cme_projects_current_agent ON cme_projects(current_agent);
CREATE INDEX IF NOT EXISTS idx_cme_projects_pipeline_thread ON cme_projects(pipeline_thread_id);

-- GIN index for JSONB intake searching
CREATE INDEX IF NOT EXISTS idx_cme_projects_intake ON cme_projects USING GIN (intake);

-- Create trigger for updated_at (uses existing function from 001_add_agents.sql)
DROP TRIGGER IF EXISTS update_cme_projects_updated_at ON cme_projects;
CREATE TRIGGER update_cme_projects_updated_at
    BEFORE UPDATE ON cme_projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create agent_outputs table for detailed output tracking
CREATE TABLE IF NOT EXISTS cme_agent_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES cme_projects(id) ON DELETE CASCADE,
    
    agent_name VARCHAR(100) NOT NULL,
    output_type VARCHAR(100) NOT NULL,
    content JSONB NOT NULL,
    quality_score FLOAT,
    
    -- LangSmith trace reference
    langsmith_trace_id VARCHAR(100),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for agent outputs
CREATE INDEX IF NOT EXISTS idx_cme_outputs_project_id ON cme_agent_outputs(project_id);
CREATE INDEX IF NOT EXISTS idx_cme_outputs_agent_name ON cme_agent_outputs(agent_name);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE cme_projects TO swebber64;
GRANT ALL PRIVILEGES ON TABLE cme_agent_outputs TO swebber64;

-- Add comment for documentation
COMMENT ON TABLE cme_projects IS 'CME Grant projects with intake data and pipeline execution status';
COMMENT ON TABLE cme_agent_outputs IS 'Individual outputs from each agent in the 12-agent pipeline';
