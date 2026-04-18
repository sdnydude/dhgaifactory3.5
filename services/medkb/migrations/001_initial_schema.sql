-- services/medkb/migrations/001_initial_schema.sql
-- medkb initial schema — Phase 0
-- Run against dhg-medkb-db (port 5433), NOT the registry DB.

CREATE SCHEMA IF NOT EXISTS medkb;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE medkb.corpora (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL UNIQUE,
    description     TEXT,
    owner           TEXT NOT NULL,
    visibility      TEXT NOT NULL,
    contains_phi    BOOLEAN NOT NULL DEFAULT FALSE,
    default_chunker TEXT NOT NULL DEFAULT 'markdown',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT corpora_visibility_check
        CHECK (visibility IN ('public','dhg_internal','division_only'))
);

CREATE TABLE medkb.documents (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id     UUID NOT NULL REFERENCES medkb.corpora(id),
    source        TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    title         TEXT,
    url           TEXT,
    audience      TEXT,
    authority     TEXT,
    valid_from    DATE,
    valid_to      DATE,
    superseded_by UUID REFERENCES medkb.documents(id),
    version_label TEXT,
    metadata      JSONB DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (corpus_id, source, source_id)
);

CREATE TABLE medkb.chunks (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id        UUID NOT NULL REFERENCES medkb.documents(id) ON DELETE CASCADE,
    corpus_id          UUID NOT NULL REFERENCES medkb.corpora(id),
    parent_chunk_id    UUID REFERENCES medkb.chunks(id),
    chunk_index        INT NOT NULL,
    chunk_text         TEXT NOT NULL,
    chunk_tokens       INT NOT NULL,
    section            TEXT,
    word_count         INT,
    readability_grade  NUMERIC(4,1),
    embedding_v1       vector(768),
    embedding_v2       vector(768),
    active_version     INT NOT NULL DEFAULT 1 CHECK (active_version IN (1,2)),
    tsv                tsvector,
    metadata           JSONB DEFAULT '{}'::jsonb,
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE medkb.ingestion_jobs (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id      UUID NOT NULL REFERENCES medkb.corpora(id),
    source         TEXT NOT NULL,
    scope          TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',
    payload        JSONB NOT NULL,
    result_summary JSONB,
    items_total    INT,
    items_done     INT DEFAULT 0,
    items_error    INT DEFAULT 0,
    started_at     TIMESTAMPTZ,
    completed_at   TIMESTAMPTZ,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT ingestion_jobs_status_check
        CHECK (status IN ('pending','running','completed','failed'))
);

CREATE TABLE medkb.embedding_cache (
    text_hash    TEXT PRIMARY KEY,
    model        TEXT NOT NULL,
    embedding    vector(768) NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE medkb.query_audit (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      TEXT NOT NULL,
    caller_id   TEXT NOT NULL,
    corpus_list TEXT[] NOT NULL,
    query_hash  TEXT NOT NULL,
    result_count INT,
    strategy    TEXT,
    groundedness_score NUMERIC(4,3),
    redaction_count    INT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX medkb_chunks_embedding_v1_hnsw
    ON medkb.chunks USING hnsw (embedding_v1 vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE active_version = 1;

CREATE INDEX medkb_chunks_embedding_v2_hnsw
    ON medkb.chunks USING hnsw (embedding_v2 vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE active_version = 2;

CREATE INDEX medkb_chunks_tsv_gin ON medkb.chunks USING gin(tsv);
CREATE INDEX medkb_chunks_corpus ON medkb.chunks (corpus_id);
CREATE INDEX medkb_chunks_parent ON medkb.chunks (parent_chunk_id);

CREATE INDEX medkb_documents_corpus_audience ON medkb.documents (corpus_id, audience);
CREATE INDEX medkb_documents_valid ON medkb.documents (valid_to) WHERE valid_to IS NULL;

CREATE INDEX medkb_ingestion_pending ON medkb.ingestion_jobs (status, created_at) WHERE status = 'pending';

CREATE INDEX medkb_query_audit_caller ON medkb.query_audit (caller_id, created_at DESC);

CREATE OR REPLACE FUNCTION medkb.chunks_tsv_trigger() RETURNS trigger AS $$
BEGIN
    NEW.tsv := to_tsvector('english', NEW.chunk_text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER chunks_tsv_update
    BEFORE INSERT OR UPDATE OF chunk_text ON medkb.chunks
    FOR EACH ROW EXECUTE FUNCTION medkb.chunks_tsv_trigger();
