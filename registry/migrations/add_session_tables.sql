-- DHG AI Factory - Add AI Session, Debug Log, and Knowledge Item Tables

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. AI SESSIONS
CREATE TABLE IF NOT EXISTS ai_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    user_id VARCHAR(100) DEFAULT 'swebber64',
    summary TEXT,
    branch VARCHAR(100),
    commits_made TEXT[],
    files_created TEXT[],
    files_modified TEXT[],
    metadata JSONB,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ai_sessions_conversation ON ai_sessions(conversation_id);

-- 2. DEBUG LOGS
CREATE TABLE IF NOT EXISTS debug_logs (
    debug_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES ai_sessions(session_id) ON DELETE SET NULL,
    problem_statement TEXT NOT NULL,
    severity VARCHAR(20),
    symptoms TEXT[],
    hypotheses JSONB,
    fix_attempts JSONB,
    resolution TEXT,
    root_cause TEXT,
    prevention TEXT,
    duration_minutes INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);
CREATE INDEX idx_debug_logs_session ON debug_logs(session_id);

-- 3. SESSION FILES
CREATE TABLE IF NOT EXISTS session_files (
    file_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES ai_sessions(session_id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    file_type VARCHAR(50),
    content_hash TEXT,
    content TEXT,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_session_files_session ON session_files(session_id);

-- 4. KNOWLEDGE ITEMS
CREATE TABLE IF NOT EXISTS knowledge_items (
    item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type VARCHAR(50),
    source_id UUID,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[],
    embedding vector(1536),
    onyx_doc_id TEXT,
    synced_to_onyx BOOLEAN DEFAULT FALSE,
    sync_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_knowledge_items_synced ON knowledge_items(synced_to_onyx);

-- 5. AGENT MEMORY
CREATE TABLE IF NOT EXISTS agent_memory (
    memory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100),
    memory_type VARCHAR(50),
    content TEXT NOT NULL,
    embedding vector(1536),
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INT DEFAULT 0
);
CREATE INDEX idx_agent_memory_agent ON agent_memory(agent_name);
