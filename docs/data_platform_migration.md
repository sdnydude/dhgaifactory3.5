# DHG Data Platform - Schema Migration Plan

**Created:** Jan 25, 2026  
**Status:** Ready for implementation

---

## Data Sources to Ingest

| Source | Volume | Priority |
|--------|--------|----------|
| AI Sessions (Claude, ChatGPT, Gemini, etc.) | 1000s | High |
| CME Symposium Videos | 300 hours | High |
| Emails (2001-2026) | Millions | Medium |
| Synology NAS | 35TB (selective) | Low |

---

## Schema Migration

### 1. Chat Messages Table

```sql
CREATE TABLE antigravity_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id VARCHAR(255) REFERENCES antigravity_chats(conversation_id),
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    token_count INTEGER,
    source VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_messages_conversation ON antigravity_messages(conversation_id);
CREATE INDEX idx_messages_embedding ON antigravity_messages USING ivfflat (embedding vector_cosine_ops);
```

---

### 2. CME Video Content Tables

```sql
CREATE TABLE cme_lectures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    speaker VARCHAR(255),
    topic VARCHAR(255),
    duration_seconds INTEGER,
    source_file VARCHAR(500),
    transcript TEXT,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

CREATE TABLE cme_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lecture_id UUID REFERENCES cme_lectures(id) ON DELETE CASCADE,
    start_time_seconds INTEGER,
    end_time_seconds INTEGER,
    speaker VARCHAR(255),
    content TEXT NOT NULL,
    embedding vector(1536),
    medical_entities JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_segments_lecture ON cme_segments(lecture_id);
CREATE INDEX idx_segments_embedding ON cme_segments USING ivfflat (embedding vector_cosine_ops);
```

---

### 3. Marketing Archive Table

```sql
CREATE TABLE marketing_archive (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    received_at TIMESTAMPTZ,
    from_domain VARCHAR(255),
    from_address VARCHAR(500),
    subject TEXT,
    opened BOOLEAN DEFAULT FALSE,
    clicked BOOLEAN DEFAULT FALSE,
    category VARCHAR(100),
    company_name VARCHAR(255),
    product_name VARCHAR(255),
    embedding vector(1536),
    metadata JSONB
);

CREATE INDEX idx_marketing_domain ON marketing_archive(from_domain);
CREATE INDEX idx_marketing_received ON marketing_archive(received_at);
CREATE INDEX idx_marketing_embedding ON marketing_archive USING ivfflat (embedding vector_cosine_ops);
```

---

### 4. Knowledge Graph Table (for GraphRAG)

```sql
CREATE TABLE knowledge_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(100) NOT NULL,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    embedding vector(1536),
    source_table VARCHAR(100),
    source_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    UNIQUE(entity_type, name)
);

CREATE TABLE knowledge_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_entity_id UUID REFERENCES knowledge_entities(id),
    to_entity_id UUID REFERENCES knowledge_entities(id),
    relationship_type VARCHAR(100) NOT NULL,
    weight FLOAT DEFAULT 1.0,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_entities_type ON knowledge_entities(entity_type);
CREATE INDEX idx_entities_embedding ON knowledge_entities USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_relationships_from ON knowledge_relationships(from_entity_id);
CREATE INDEX idx_relationships_to ON knowledge_relationships(to_entity_id);
```

---

## Implementation Order

1. [ ] Run migration on dhg-registry-db
2. [ ] Update models.py with new tables
3. [ ] Create import pipelines:
   - [ ] Claude/ChatGPT JSON importer
   - [ ] Video transcription with Whisper
   - [ ] Email MBOX/EML parser
4. [ ] Add embedding generation on insert
5. [ ] Deploy MemoRAG for cross-session memory
6. [ ] Deploy GraphRAG for medical entities

---

## Enable pgvector if not already

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
