-- DHG CME Research Agent - Database Schema
-- PostgreSQL with pgvector extension

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- CITATIONS TABLE
-- Stores validated peer-reviewed citations with vector embeddings
-- =============================================================================
CREATE TABLE IF NOT EXISTS citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pmid VARCHAR(20) UNIQUE,
    doi VARCHAR(100) UNIQUE,
    title TEXT NOT NULL,
    authors TEXT[], -- Array of author names
    journal VARCHAR(255),
    year INTEGER,
    volume VARCHAR(20),
    issue VARCHAR(20),
    pages VARCHAR(50),
    abstract TEXT,
    evidence_level VARCHAR(50) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    url VARCHAR(500),
    publication_types TEXT[],
    
    -- Vector embedding for semantic search
    embedding vector(1536),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    access_count INTEGER DEFAULT 0
);

-- Indexes for citations
CREATE INDEX IF NOT EXISTS idx_citations_pmid ON citations(pmid);
CREATE INDEX IF NOT EXISTS idx_citations_doi ON citations(doi);
CREATE INDEX IF NOT EXISTS idx_citations_year ON citations(year);
CREATE INDEX IF NOT EXISTS idx_citations_evidence ON citations(evidence_level);
CREATE INDEX IF NOT EXISTS idx_citations_journal ON citations(journal);

-- Vector similarity search index (IVFFlat for approximate nearest neighbor)
CREATE INDEX IF NOT EXISTS idx_citations_embedding ON citations 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- =============================================================================
-- RESEARCH JOBS TABLE
-- Tracks research queries and their results
-- =============================================================================
CREATE TABLE IF NOT EXISTS research_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic TEXT NOT NULL,
    therapeutic_area VARCHAR(100) NOT NULL,
    query_type VARCHAR(50) NOT NULL,
    target_audience VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Query parameters
    date_range_years INTEGER DEFAULT 5,
    minimum_evidence_level VARCHAR(10) DEFAULT '2b',
    max_results INTEGER DEFAULT 50,
    specific_questions TEXT[],
    
    -- Results
    synthesis TEXT,
    clinical_gaps TEXT[],
    key_findings TEXT[],
    recommendations TEXT[],
    
    -- Cost tracking
    model_used VARCHAR(100),
    tokens_used INTEGER DEFAULT 0,
    cost_estimate DECIMAL(10, 4) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

-- Indexes for research jobs
CREATE INDEX IF NOT EXISTS idx_jobs_status ON research_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_therapeutic ON research_jobs(therapeutic_area);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON research_jobs(created_at DESC);

-- =============================================================================
-- JOB CITATIONS (Junction Table)
-- Links research jobs to their citations
-- =============================================================================
CREATE TABLE IF NOT EXISTS job_citations (
    job_id UUID REFERENCES research_jobs(id) ON DELETE CASCADE,
    citation_id UUID REFERENCES citations(id) ON DELETE CASCADE,
    relevance_score DECIMAL(5, 4),
    position INTEGER, -- Order in results
    PRIMARY KEY (job_id, citation_id)
);

CREATE INDEX IF NOT EXISTS idx_job_citations_job ON job_citations(job_id);
CREATE INDEX IF NOT EXISTS idx_job_citations_citation ON job_citations(citation_id);

-- =============================================================================
-- THERAPEUTIC AREAS REFERENCE
-- Lookup table for supported therapeutic areas
-- =============================================================================
CREATE TABLE IF NOT EXISTS therapeutic_areas (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    mesh_terms TEXT[], -- MeSH terms for PubMed queries
    description TEXT,
    is_active BOOLEAN DEFAULT true
);

-- Insert default therapeutic areas
INSERT INTO therapeutic_areas (name, display_name, mesh_terms) VALUES
    ('cardiology', 'Cardiology', ARRAY['Cardiovascular Diseases', 'Heart Diseases']),
    ('oncology', 'Oncology', ARRAY['Neoplasms', 'Cancer']),
    ('neurology', 'Neurology', ARRAY['Nervous System Diseases', 'Neurological']),
    ('pulmonology', 'Pulmonology', ARRAY['Respiratory Tract Diseases', 'Lung Diseases']),
    ('gastroenterology', 'Gastroenterology', ARRAY['Gastrointestinal Diseases', 'Digestive System']),
    ('endocrinology', 'Endocrinology', ARRAY['Endocrine System Diseases', 'Metabolic Diseases']),
    ('rheumatology', 'Rheumatology', ARRAY['Rheumatic Diseases', 'Autoimmune Diseases']),
    ('infectious_disease', 'Infectious Disease', ARRAY['Communicable Diseases', 'Infection']),
    ('dermatology', 'Dermatology', ARRAY['Skin Diseases', 'Dermatologic']),
    ('psychiatry', 'Psychiatry', ARRAY['Mental Disorders', 'Psychiatric']),
    ('nephrology', 'Nephrology', ARRAY['Kidney Diseases', 'Renal']),
    ('hematology', 'Hematology', ARRAY['Hematologic Diseases', 'Blood Diseases']),
    ('immunology', 'Immunology', ARRAY['Immune System Diseases', 'Immunologic']),
    ('primary_care', 'Primary Care', ARRAY['Primary Health Care', 'General Practice']),
    ('pediatrics', 'Pediatrics', ARRAY['Pediatrics', 'Child Health']),
    ('geriatrics', 'Geriatrics', ARRAY['Geriatrics', 'Aged']),
    ('emergency_medicine', 'Emergency Medicine', ARRAY['Emergency Medicine', 'Critical Care']),
    ('critical_care', 'Critical Care', ARRAY['Critical Care', 'Intensive Care'])
ON CONFLICT (name) DO NOTHING;

-- =============================================================================
-- EVIDENCE LEVELS REFERENCE
-- Lookup table for evidence classification
-- =============================================================================
CREATE TABLE IF NOT EXISTS evidence_levels (
    level VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    publication_types TEXT[],
    sort_order INTEGER
);

INSERT INTO evidence_levels (level, name, description, publication_types, sort_order) VALUES
    ('1a', 'Systematic Review/Meta-Analysis', 'Systematic review of RCTs with homogeneity', 
     ARRAY['Systematic Review', 'Meta-Analysis'], 1),
    ('1b', 'High-Quality RCT', 'Individual RCT with narrow confidence interval', 
     ARRAY['Randomized Controlled Trial'], 2),
    ('2a', 'Lower-Quality RCT', 'Systematic review of cohort studies or lower-quality RCT', 
     ARRAY['Clinical Trial', 'Controlled Clinical Trial'], 3),
    ('2b', 'Cohort/Case-Control', 'Individual cohort or case-control study', 
     ARRAY['Cohort Study', 'Comparative Study', 'Observational Study'], 4),
    ('3', 'Case Series', 'Case series or poor-quality cohort/case-control', 
     ARRAY['Case Reports'], 5),
    ('4', 'Expert Opinion', 'Expert opinion without explicit critical appraisal', 
     ARRAY['Practice Guideline', 'Guideline', 'Consensus Development Conference'], 6),
    ('5', 'Narrative Review', 'Narrative review or editorial', 
     ARRAY['Review', 'Editorial', 'Comment', 'Letter'], 7)
ON CONFLICT (level) DO NOTHING;

-- =============================================================================
-- CACHE TABLE
-- Stores cached API responses to reduce costs
-- =============================================================================
CREATE TABLE IF NOT EXISTS api_cache (
    cache_key VARCHAR(255) PRIMARY KEY,
    api_source VARCHAR(50) NOT NULL, -- 'pubmed', 'perplexity', 'anthropic', 'gemini'
    request_hash VARCHAR(64) NOT NULL,
    response_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    hit_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_cache_source ON api_cache(api_source);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON api_cache(expires_at);

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to update citation access tracking
CREATE OR REPLACE FUNCTION update_citation_access()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_accessed = NOW();
    NEW.access_count = OLD.access_count + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to find similar citations by embedding
CREATE OR REPLACE FUNCTION find_similar_citations(
    query_embedding vector(1536),
    limit_count INTEGER DEFAULT 10,
    min_evidence_level VARCHAR(10) DEFAULT '2b'
)
RETURNS TABLE (
    id UUID,
    pmid VARCHAR(20),
    title TEXT,
    evidence_level VARCHAR(50),
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.pmid,
        c.title,
        c.evidence_level,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM citations c
    JOIN evidence_levels el ON c.evidence_level LIKE el.level || '%'
    WHERE c.embedding IS NOT NULL
    ORDER BY c.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER citations_updated_at
    BEFORE UPDATE ON citations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER jobs_updated_at
    BEFORE UPDATE ON research_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- VIEWS
-- =============================================================================

-- View for job statistics
CREATE OR REPLACE VIEW job_statistics AS
SELECT 
    therapeutic_area,
    query_type,
    COUNT(*) as total_jobs,
    COUNT(*) FILTER (WHERE status = 'completed') as completed_jobs,
    AVG(tokens_used) as avg_tokens,
    AVG(cost_estimate) as avg_cost,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds
FROM research_jobs
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY therapeutic_area, query_type;

-- View for citation quality distribution
CREATE OR REPLACE VIEW citation_quality AS
SELECT 
    evidence_level,
    COUNT(*) as citation_count,
    COUNT(DISTINCT journal) as unique_journals,
    AVG(access_count) as avg_access_count
FROM citations
GROUP BY evidence_level
ORDER BY evidence_level;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dhg_research;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dhg_research;
