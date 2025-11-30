-- DHG AI Factory - Registry Database Initialization
-- PostgreSQL + pgvector schema

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- References: All validated citations and sources
CREATE TABLE IF NOT EXISTS references (
    reference_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    authors TEXT,
    publication_date DATE,
    source_type VARCHAR(50), -- pubmed, clinical_trial, guideline, etc.
    source_confidence DECIMAL(3,2), -- 0.00 to 1.00
    evidence_level VARCHAR(20), -- I, II, III, IV, V (GRADE)
    validated BOOLEAN DEFAULT FALSE,
    validation_attempts INT DEFAULT 0,
    last_validation_attempt TIMESTAMP,
    abstract TEXT,
    doi TEXT,
    pmid TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_references_url ON references(url);
CREATE INDEX idx_references_validated ON references(validated);
CREATE INDEX idx_references_source_type ON references(source_type);

-- Vector embeddings for references
CREATE TABLE IF NOT EXISTS vector (
    vector_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_id UUID REFERENCES references(reference_id) ON DELETE CASCADE,
    embedding vector(1536), -- OpenAI text-embedding-3-small
    embedding_model VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vector_embedding ON vector USING ivfflat (embedding vector_cosine_ops);

-- Events: Request/response logging
CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- request, response, error
    endpoint VARCHAR(200),
    payload JSONB,
    compliance_mode VARCHAR(20), -- cme, non-cme
    violations JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_agent ON events(agent_name);
CREATE INDEX idx_events_created_at ON events(created_at DESC);
CREATE INDEX idx_events_compliance_mode ON events(compliance_mode);

-- API Cache: Research results caching
CREATE TABLE IF NOT EXISTS api_cache (
    cache_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cache_key TEXT NOT NULL UNIQUE,
    source VARCHAR(50) NOT NULL,
    query_params JSONB,
    response_data JSONB,
    expires_at TIMESTAMP,
    hit_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_cache_key ON api_cache(cache_key);
CREATE INDEX idx_api_cache_expires ON api_cache(expires_at);

-- Topic Source State: Incremental update tracking
CREATE TABLE IF NOT EXISTS topic_source_state (
    state_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic TEXT NOT NULL,
    source VARCHAR(50) NOT NULL,
    last_query_at TIMESTAMP,
    last_result_count INT,
    last_new_results INT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(topic, source)
);

CREATE INDEX idx_topic_source ON topic_source_state(topic, source);

-- ============================================================================
-- CME CONTENT TABLES
-- ============================================================================

-- Content Segments: Needs assessments, scripts, etc.
CREATE TABLE IF NOT EXISTS segments (
    segment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_type VARCHAR(50) NOT NULL, -- needs_assessment, script, curriculum
    topic TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INT,
    compliance_mode VARCHAR(20),
    qa_passed BOOLEAN DEFAULT FALSE,
    violations JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_segments_type ON segments(content_type);
CREATE INDEX idx_segments_compliance ON segments(compliance_mode);

-- Segment References: Many-to-many relationship
CREATE TABLE IF NOT EXISTS segment_references (
    segment_id UUID REFERENCES segments(segment_id) ON DELETE CASCADE,
    reference_id UUID REFERENCES references(reference_id) ON DELETE CASCADE,
    PRIMARY KEY (segment_id, reference_id)
);

-- Learning Objectives
CREATE TABLE IF NOT EXISTS learning_objectives (
    objective_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    segment_id UUID REFERENCES segments(segment_id) ON DELETE CASCADE,
    objective_text TEXT NOT NULL,
    moore_levels TEXT[], -- Array of Moore levels
    icd10_codes TEXT[],
    qi_measures TEXT[],
    target_behaviors TEXT[],
    bloom_taxonomy VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Assessments: Pre/post/follow-up
CREATE TABLE IF NOT EXISTS assessments (
    assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    segment_id UUID REFERENCES segments(segment_id) ON DELETE CASCADE,
    assessment_type VARCHAR(20) NOT NULL, -- pre, post, 6_week_follow_up
    moore_levels INT[],
    questions JSONB,
    scoring_rubric JSONB,
    estimated_minutes INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Outcomes Data
CREATE TABLE IF NOT EXISTS outcomes (
    outcome_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    segment_id UUID REFERENCES segments(segment_id) ON DELETE CASCADE,
    moore_level INT NOT NULL,
    metric_name VARCHAR(200),
    baseline_value DECIMAL,
    target_value DECIMAL,
    actual_value DECIMAL,
    measurement_date DATE,
    data_source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- COMPETITOR INTELLIGENCE TABLES
-- ============================================================================

-- Competitor Activities
CREATE TABLE IF NOT EXISTS competitor_activities (
    activity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider VARCHAR(200),
    funder VARCHAR(200),
    activity_date DATE,
    format VARCHAR(50),
    credits DECIMAL(4,2),
    topic TEXT,
    url TEXT,
    activity_title TEXT,
    source VARCHAR(50),
    validated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_competitor_provider ON competitor_activities(provider);
CREATE INDEX idx_competitor_funder ON competitor_activities(funder);
CREATE INDEX idx_competitor_date ON competitor_activities(activity_date DESC);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for references table
CREATE TRIGGER update_references_updated_at BEFORE UPDATE ON references
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert system event for database initialization
INSERT INTO events (agent_name, event_type, endpoint, payload, compliance_mode)
VALUES ('system', 'initialization', '/init', '{"action": "database_initialized"}', 'system');

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'DHG AI Factory Registry Database initialized successfully';
END $$;
