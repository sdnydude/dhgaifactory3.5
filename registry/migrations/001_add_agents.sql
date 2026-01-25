-- Migration: Add agents and agent_heartbeats tables for LangSmith Cloud
-- Date: 2026-01-24

-- Create agents table
CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    division VARCHAR(100) NOT NULL,
    type VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Deployment info
    deployment_type VARCHAR(50) DEFAULT 'langsmith_cloud',
    deployment_url TEXT,
    langsmith_deployment_id VARCHAR(255),
    langsmith_org VARCHAR(255),
    
    -- GitHub integration
    github_repo VARCHAR(255),
    github_branch VARCHAR(100) DEFAULT 'main',
    github_path VARCHAR(255),
    
    -- Legacy self-hosted
    endpoint TEXT,
    
    -- JSON data
    capabilities JSONB,
    io_schema JSONB,
    models JSONB,
    external_apis JSONB,
    observability JSONB,
    
    -- Status
    status VARCHAR(50) DEFAULT 'healthy',
    last_heartbeat TIMESTAMPTZ,
    
    -- Timestamps
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on agent type for filtering
CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(type);
CREATE INDEX IF NOT EXISTS idx_agents_division ON agents(division);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_deployment_type ON agents(deployment_type);

-- Create agent_heartbeats table
CREATE TABLE IF NOT EXISTS agent_heartbeats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    
    status VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    -- Model status
    models JSONB,
    
    -- Metrics
    requests_total INTEGER DEFAULT 0,
    requests_success INTEGER DEFAULT 0,
    requests_failed INTEGER DEFAULT 0,
    avg_latency_ms FLOAT DEFAULT 0.0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd FLOAT DEFAULT 0.0,
    
    -- LangSmith Cloud metrics
    langsmith_deployment_status VARCHAR(50),
    langsmith_traces_count INTEGER,
    deployment_tier VARCHAR(50)
);

-- Create indexes for heartbeats
CREATE INDEX IF NOT EXISTS idx_heartbeats_agent_id ON agent_heartbeats(agent_id);
CREATE INDEX IF NOT EXISTS idx_heartbeats_timestamp ON agent_heartbeats(timestamp DESC);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for agents table
DROP TRIGGER IF EXISTS update_agents_updated_at ON agents;
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (adjust user as needed)
GRANT ALL PRIVILEGES ON TABLE agents TO swebber64;
GRANT ALL PRIVILEGES ON TABLE agent_heartbeats TO swebber64;
