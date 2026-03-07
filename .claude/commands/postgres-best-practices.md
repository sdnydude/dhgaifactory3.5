# Postgres Best Practices

Apply comprehensive Postgres performance, schema, and security guidelines to the task described in $ARGUMENTS.

When $ARGUMENTS is empty, audit the current codebase — focusing on registry/models.py, any raw SQL, and SQLAlchemy query patterns — and report findings against all rules below.

## Capabilities

**What this command does:** Audits and improves query performance, indexing strategy, connection management, schema design, and security configuration for the DHG PostgreSQL 15 registry database (`dhg-registry-db`).

**Use it when you need to:**
- Identify missing indexes on foreign key columns or JSONB `meta_data` fields
- Fix N+1 query patterns, OFFSET pagination, or non-atomic upserts in SQLAlchemy code
- Tune connection pool settings or set statement timeouts on the registry engine
- Apply Row-Level Security policies or least-privilege role grants to the registry schema
- Diagnose slow queries using `pg_stat_statements` and `EXPLAIN (ANALYZE, BUFFERS)`

**Example invocations:**
- `/project:postgres-best-practices audit registry/models.py for missing FK indexes`
- `/project:postgres-best-practices add a GIN index for the meta_data JSONB column on the media table`
- `/project:postgres-best-practices replace OFFSET pagination in the segments endpoint with cursor-based keyset pagination`

---

## Project Context

- Database: PostgreSQL 15 + pgvector
- Container: `dhg-registry-db` on Docker network `dhgaifactory35_dhg-network`
- ORM: SQLAlchemy 2.0 (`registry/models.py`)
- Scale: 57 tables, UUID v4 primary keys throughout
- Access URL (internal): `postgresql://...@dhg-registry-db:5432/...`
- Known issue: all PKs are UUIDv4 (random) — flag this when creating new tables; prefer `bigint generated always as identity` or UUIDv7 for new tables

---

## Rule Priority Reference

| Priority | Category | Impact |
|----------|----------|--------|
| 1 | Query Performance | CRITICAL |
| 2 | Connection Management | CRITICAL |
| 3 | Security & RLS | CRITICAL |
| 4 | Schema Design | HIGH |
| 5 | Concurrency & Locking | MEDIUM-HIGH |
| 6 | Data Access Patterns | MEDIUM |
| 7 | Monitoring & Diagnostics | LOW-MEDIUM |
| 8 | Advanced Features (JSONB, FTS) | LOW |

---

## 1. Query Performance — CRITICAL

### 1.1 Add Indexes on WHERE and JOIN Columns

Missing indexes cause full sequential scans that grow exponentially with table size.

**Bad:**
```sql
-- No index on media_id causes seq scan across segments table
SELECT * FROM segments WHERE transcript_id = $1;
```

**Good:**
```sql
CREATE INDEX segments_transcript_id_idx ON segments (transcript_id);
SELECT * FROM segments WHERE transcript_id = $1;
-- EXPLAIN: Index Scan using segments_transcript_id_idx
```

In SQLAlchemy 2.0:
```python
from sqlalchemy import Index
Index('segments_transcript_id_idx', Segment.transcript_id)
# Or inline on the Column:
transcript_id = Column(UUID, ForeignKey('transcripts.id'), index=True)
```

### 1.2 Choose the Right Index Type

Default B-tree is not always correct. Match the index type to the operator being used.

| Use Case | Index Type | Operators |
|----------|-----------|-----------|
| Equality, ranges, sorts | B-tree (default) | `=`, `<`, `>`, `BETWEEN` |
| JSONB containment | GIN | `@>`, `?`, `?&`, `?\|` |
| Arrays | GIN | `@>`, `&&` |
| Full-text search | GIN | `@@` |
| Large time-series (append-only) | BRIN | `<`, `>`, `BETWEEN` |
| Equality only, no ordering needed | Hash | `=` |
| pgvector similarity | ivfflat / hnsw | `<->`, `<#>`, `<=>` |

**Bad (B-tree on JSONB containment):**
```sql
CREATE INDEX media_meta_idx ON media (meta_data);
SELECT * FROM media WHERE meta_data @> '{"source": "upload"}';
-- Full table scan — B-tree cannot serve @>
```

**Good:**
```sql
CREATE INDEX media_meta_gin ON media USING gin (meta_data);
SELECT * FROM media WHERE meta_data @> '{"source": "upload"}';
```

### 1.3 Create Composite Indexes for Multi-Column Queries

Place equality columns first, range columns last.

**Bad:**
```sql
CREATE INDEX events_type_idx ON events (event_type);
CREATE INDEX events_created_idx ON events (created_at);
-- Two indexes combined via bitmap scan — slower than one composite
SELECT * FROM events WHERE event_type = 'transcribe' AND created_at > now() - INTERVAL '7 days';
```

**Good:**
```sql
CREATE INDEX events_type_created_idx ON events (event_type, created_at);
-- Leftmost prefix rule: also satisfies WHERE event_type = 'transcribe' alone
```

### 1.4 Use Covering Indexes to Eliminate Heap Fetches

Include columns you SELECT but do not filter on using `INCLUDE`.

```sql
-- Query fetches status and created_at after an index scan on media_id
CREATE INDEX transcripts_media_id_idx ON transcripts (media_id)
  INCLUDE (confidence_score, created_at);

SELECT media_id, confidence_score, created_at FROM transcripts WHERE media_id = $1;
-- Index-only scan: zero heap access
```

### 1.5 Use Partial Indexes for Filtered Queries

Index only the rows your queries actually touch.

```sql
-- Index only pending media — active status covers a small fraction of total rows
CREATE INDEX media_pending_idx ON media (created_at)
  WHERE status = 'pending';

-- Only non-null speaker segments
CREATE INDEX segments_speaker_idx ON segments (speaker_id)
  WHERE speaker_id IS NOT NULL;
```

---

## 2. Connection Management — CRITICAL

### 2.1 Configure Idle Connection Timeouts

Idle connections inside transactions hold locks and exhaust the connection pool.

```sql
-- In postgresql.conf or via ALTER SYSTEM
ALTER SYSTEM SET idle_in_transaction_session_timeout = '30s';
ALTER SYSTEM SET idle_session_timeout = '10min';
SELECT pg_reload_conf();
```

For DHG: set `statement_timeout` in the SQLAlchemy engine connect args:
```python
engine = create_engine(
    DATABASE_URL,
    connect_args={"options": "-c statement_timeout=30000"},  # 30 seconds
)
```

### 2.2 Set Appropriate Connection Limits

Formula: `max_connections = floor(RAM_MB / 5) - reserved_superuser_connections`

Practical ceiling for query performance is 100–200 even on well-provisioned hosts. Each connection costs 1–3 MB RAM plus `work_mem` per sort/hash operation.

```sql
SHOW max_connections;  -- Check current
SELECT count(*), state FROM pg_stat_activity GROUP BY state;  -- Check usage
```

### 2.3 Use Connection Pooling

SQLAlchemy's built-in pool is adequate for single-process services. Configure it explicitly:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # Persistent connections
    max_overflow=20,        # Burst connections
    pool_pre_ping=True,     # Detect stale connections
    pool_recycle=3600,      # Recycle after 1 hour
)
```

For multi-process deployments (e.g., Gunicorn workers), use PgBouncer in transaction mode between the app and `dhg-registry-db`.

### 2.4 Prepared Statements and Pooling

Named prepared statements are tied to a single backend connection. In transaction-mode pooling they cause `ERROR: prepared statement does not exist`.

SQLAlchemy 2.0 uses unnamed prepared statements by default — this is correct. Do not name statements manually unless using session-mode pooling.

```python
# Safe — unnamed, compatible with transaction pooling
result = session.execute(text("SELECT * FROM media WHERE id = :id"), {"id": media_id})

# Dangerous in transaction pooling
# PREPARE get_media AS SELECT * FROM media WHERE id = $1;
```

---

## 3. Security & RLS — CRITICAL

### 3.1 Principle of Least Privilege

The application role must never be a superuser or own the schema outright.

```sql
-- Separate read and write roles
CREATE ROLE dhg_readonly NOLOGIN;
GRANT USAGE ON SCHEMA public TO dhg_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dhg_readonly;

CREATE ROLE dhg_writer NOLOGIN;
GRANT USAGE ON SCHEMA public TO dhg_writer;
GRANT SELECT, INSERT, UPDATE ON media, transcripts, segments, events TO dhg_writer;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO dhg_writer;

CREATE ROLE dhg_app LOGIN PASSWORD '...';
GRANT dhg_writer TO dhg_app;

-- Revoke default public access
REVOKE ALL ON SCHEMA public FROM public;
```

### 3.2 Enable RLS for Multi-Tenant Tables

If any table stores data belonging to different tenants or users, enforce isolation at the database layer — never rely on application-level WHERE clauses alone.

```sql
ALTER TABLE media ENABLE ROW LEVEL SECURITY;
ALTER TABLE media FORCE ROW LEVEL SECURITY;

CREATE POLICY media_owner_policy ON media
  FOR ALL
  USING (user_id = current_setting('app.current_user_id')::text);

-- Set context in each request
SET app.current_user_id = 'user-uuid-here';
```

### 3.3 Optimize RLS Policies for Performance

Calling a volatile function (like `auth.uid()` or `current_setting()`) at the top level of a policy expression evaluates it once per row. Wrap it in a subquery to evaluate it once per query.

**Bad (per-row function call):**
```sql
CREATE POLICY slow_policy ON media
  USING (owner_id = current_setting('app.current_user_id')::uuid);
```

**Good (evaluated once, cached):**
```sql
CREATE POLICY fast_policy ON media
  USING (owner_id = (SELECT current_setting('app.current_user_id')::uuid));

-- Always add an index on the column used in the policy
CREATE INDEX media_owner_id_idx ON media (owner_id);
```

---

## 4. Schema Design — HIGH

### 4.1 Choose Appropriate Data Types

| Column Use | Correct Type | Avoid |
|-----------|-------------|-------|
| Identifiers (new tables) | `bigint generated always as identity` | `serial`, random UUID PK |
| Distributed/exposed IDs | `uuid` with UUIDv7 | `uuid` with `gen_random_uuid()` (v4) |
| Short strings with no max needed | `text` | `varchar(255)` |
| Timestamps | `timestamptz` | `timestamp` (no timezone) |
| Booleans | `boolean` | `varchar`, `int` |
| Money / exact decimal | `numeric(p,s)` | `float`, `double precision` |
| Structured metadata | `jsonb` | `json`, `text` |
| ML embeddings (pgvector) | `vector(n)` | `float[]` |

DHG-specific note: existing models use `UUID(as_uuid=True)` with `default=uuid.uuid4` throughout. This is acceptable for the existing 57 tables. For new tables, prefer `bigint identity` unless a UUID is needed for external exposure.

### 4.2 Index Every Foreign Key Column

Postgres does NOT automatically index foreign key columns. Missing FK indexes cause slow JOINs and catastrophically slow CASCADE DELETEs.

Audit query to find unindexed FK columns:
```sql
SELECT
  conrelid::regclass AS table_name,
  a.attname AS fk_column,
  confrelid::regclass AS references_table
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid AND a.attnum = ANY(i.indkey)
  )
ORDER BY table_name;
```

In SQLAlchemy, set `index=True` on every `ForeignKey` column or declare explicit `Index` objects.

### 4.3 Partition Large, Time-Series Tables

Apply partitioning when a table exceeds ~50–100M rows or requires regular purging of old data.

```sql
-- Partition events by month
CREATE TABLE events (
  id uuid NOT NULL,
  event_type text NOT NULL,
  created_at timestamptz NOT NULL,
  meta_data jsonb
) PARTITION BY RANGE (created_at);

CREATE TABLE events_2026_01 PARTITION OF events
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE events_2026_02 PARTITION OF events
  FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- Drop old data instantly (no DELETE scan)
DROP TABLE events_2025_01;
```

DHG: the `events` audit log table is a candidate for partitioning as it grows.

### 4.4 Primary Key Strategy

- Single-process services: `bigint generated always as identity` (8 bytes, sequential, no fragmentation)
- Distributed / externally exposed IDs: UUIDv7 (time-ordered, requires `pg_uuidv7` extension)
- Avoid UUIDv4 as PK on large tables — random inserts fragment the B-tree index

DHG existing tables: UUIDv4 PKs are in place. Do not change them retroactively. Use `bigint identity` for new high-volume tables (e.g., vector embedding tables, analytics event tables).

### 4.5 Use Lowercase snake_case Identifiers

All table and column names must be unquoted lowercase with underscores. Mixed-case quoted identifiers require quotes in every query and break most tooling.

```sql
-- Correct
CREATE TABLE agent_runs (
  run_id bigint generated always as identity primary key,
  agent_name text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now()
);

-- Wrong — requires quotes forever
CREATE TABLE "AgentRuns" ("runId" bigint PRIMARY KEY, "agentName" text);
```

---

## 5. Concurrency & Locking — MEDIUM-HIGH

### 5.1 Keep Transactions Short

Never make network calls, file I/O, or slow computations inside a database transaction. Hold locks only for the actual SQL statements.

```python
# Bad — HTTP call inside transaction holds row lock for seconds
with session.begin():
    media = session.get(Media, media_id, with_for_update=True)
    result = requests.post("http://transcriber/run", ...)  # seconds of lock hold
    media.status = "completed"

# Good — do external work first, then write atomically
result = requests.post("http://transcriber/run", ...)
with session.begin():
    session.execute(
        update(Media)
        .where(Media.id == media_id, Media.status == "processing")
        .values(status="completed", meta_data=result.json())
    )
```

Set a statement timeout to catch runaway queries:
```sql
SET statement_timeout = '30s';
```

### 5.2 Prevent Deadlocks with Consistent Lock Ordering

When multiple transactions update the same set of rows, always acquire locks in a deterministic order (e.g., ascending ID).

```sql
-- Acquire all row locks before any updates
BEGIN;
SELECT * FROM media WHERE id = ANY($1) ORDER BY id FOR UPDATE;
-- Now update in any order — locks already held
UPDATE media SET status = 'archived' WHERE id = ANY($1);
COMMIT;
```

Monitor deadlocks:
```sql
SELECT datname, deadlocks FROM pg_stat_database WHERE deadlocks > 0;
```

### 5.3 Use Advisory Locks for Singleton Jobs

Advisory locks coordinate application-level exclusivity (e.g., "only one vacuum job at a time") without creating or locking database rows.

```sql
-- Attempt to acquire; returns true/false immediately
SELECT pg_try_advisory_lock(hashtext('dhg_daily_cleanup'));

-- Release when done
SELECT pg_advisory_unlock(hashtext('dhg_daily_cleanup'));

-- Transaction-scoped (auto-released on commit/rollback)
BEGIN;
SELECT pg_advisory_xact_lock(hashtext('embedding_batch_job'));
-- ... run job ...
COMMIT;
```

### 5.4 Use SKIP LOCKED for Worker Queues

When multiple LangGraph agents or workers consume from the same job queue, `SKIP LOCKED` prevents workers from blocking each other.

```sql
-- Atomic claim: one statement, no race condition
UPDATE agent_tasks
SET status = 'running', worker_id = $1, started_at = now()
WHERE id = (
  SELECT id FROM agent_tasks
  WHERE status = 'pending'
  ORDER BY created_at
  LIMIT 1
  FOR UPDATE SKIP LOCKED
)
RETURNING *;
```

---

## 6. Data Access Patterns — MEDIUM

### 6.1 Batch INSERT for Bulk Data

Individual INSERT round-trips are 10–50x slower than batched inserts.

```python
# Bad — one INSERT per item
for segment in segments:
    session.add(Segment(**segment))
    session.flush()

# Good — bulk insert
session.execute(insert(Segment), [dict(**s) for s in segments])
session.commit()
```

For loading large datasets (CSV, parquet exports), use `COPY`:
```sql
COPY segments (transcript_id, segment_index, start_time_seconds, end_time_seconds, text)
FROM '/tmp/segments.csv' WITH (FORMAT csv, HEADER true);
```

### 6.2 Eliminate N+1 Queries

Loading a list of records then querying related records in a loop generates N+1 round trips.

```python
# Bad — N+1
transcripts = session.scalars(select(Transcript)).all()
for t in transcripts:
    segments = session.scalars(select(Segment).where(Segment.transcript_id == t.id)).all()

# Good — single JOIN or selectinload
transcripts = session.scalars(
    select(Transcript).options(selectinload(Transcript.segments))
).all()

# Or in raw SQL with ANY
SELECT * FROM segments WHERE transcript_id = ANY(:ids::uuid[]);
```

### 6.3 Cursor-Based Pagination Instead of OFFSET

`OFFSET N` scans and discards N rows on every page. At page 500 it reads 500 * page_size rows.

```sql
-- Bad — OFFSET grows linearly slower
SELECT * FROM events ORDER BY created_at DESC LIMIT 50 OFFSET 5000;

-- Good — cursor pagination, always O(1)
SELECT * FROM events
WHERE created_at < :last_created_at
  OR (created_at = :last_created_at AND id < :last_id)
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

Composite cursor covers ties on `created_at` by including `id` as a tiebreaker.

### 6.4 UPSERT for Insert-or-Update

Separate SELECT → INSERT/UPDATE is not atomic and creates race conditions under concurrency.

```sql
-- Atomic upsert — safe under concurrent writers
INSERT INTO agent_registry (agent_name, endpoint, status, updated_at)
VALUES ($1, $2, 'active', now())
ON CONFLICT (agent_name)
DO UPDATE SET
  endpoint = EXCLUDED.endpoint,
  status = EXCLUDED.status,
  updated_at = EXCLUDED.updated_at
RETURNING *;
```

In SQLAlchemy 2.0:
```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = pg_insert(AgentRegistry).values(
    agent_name=name, endpoint=endpoint, status="active"
).on_conflict_do_update(
    index_elements=["agent_name"],
    set_={"endpoint": endpoint, "status": "active", "updated_at": func.now()},
)
session.execute(stmt)
```

---

## 7. Monitoring & Diagnostics — LOW-MEDIUM

### 7.1 Enable pg_stat_statements

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 10 queries by total cumulative time
SELECT
  calls,
  round(total_exec_time::numeric, 2) AS total_ms,
  round(mean_exec_time::numeric, 2) AS mean_ms,
  round((100 * total_exec_time / sum(total_exec_time) OVER ())::numeric, 2) AS pct,
  query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;

-- High mean latency candidates for optimization
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100   -- > 100ms average
ORDER BY mean_exec_time DESC;

-- Reset after a tuning change
SELECT pg_stat_statements_reset();
```

### 7.2 VACUUM and ANALYZE

Dead tuples accumulate from UPDATEs and DELETEs. Autovacuum handles this, but tune it for high-churn tables.

```sql
-- Check last maintenance per table
SELECT
  relname,
  n_dead_tup,
  last_vacuum,
  last_autovacuum,
  last_analyze,
  last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- Tune autovacuum for high-churn tables (e.g., events, agent_tasks)
ALTER TABLE events SET (
  autovacuum_vacuum_scale_factor = 0.05,   -- Vacuum at 5% dead tuples
  autovacuum_analyze_scale_factor = 0.02   -- Analyze at 2% row changes
);

-- Manual analyze after bulk load or large delete
ANALYZE media;
ANALYZE transcripts (media_id, confidence_score, created_at);
```

### 7.3 EXPLAIN ANALYZE for Slow Query Diagnosis

Always run `EXPLAIN (ANALYZE, BUFFERS)` before and after any index or query change.

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT t.*, m.filename
FROM transcripts t
JOIN media m ON m.id = t.media_id
WHERE m.status = 'completed' AND t.confidence_score > 0.9
ORDER BY t.created_at DESC
LIMIT 20;
```

Warning signs in EXPLAIN output:
- `Seq Scan` on a large table → missing index
- `Rows Removed by Filter` is large relative to returned rows → poor selectivity or wrong index
- `Buffers: read >> hit` → data not in shared_buffers, consider increasing `shared_buffers`
- `Sort Method: external merge` → `work_mem` too low for this sort
- `Nested Loop` with high `loops` count → consider Hash Join or add index on inner side

---

## 8. Advanced Features — LOW

### 8.1 JSONB Indexing

All `meta_data` JSONB columns in DHG models should be indexed if queried for containment or key access.

```sql
-- GIN for containment (@>, ?, ?&, ?|) — default operator class
CREATE INDEX media_meta_gin ON media USING gin (meta_data);

-- GIN jsonb_path_ops: supports only @> but index is 2–3x smaller
CREATE INDEX media_meta_path_gin ON media USING gin (meta_data jsonb_path_ops);

-- Expression index for a specific key (faster than GIN for single-key lookups)
CREATE INDEX media_source_idx ON media ((meta_data->>'source'));
SELECT * FROM media WHERE meta_data->>'source' = 'upload';

-- Query with GIN
SELECT * FROM media WHERE meta_data @> '{"processed": true}';
```

### 8.2 Full-Text Search with tsvector

For searching transcript text or segment text, use `tsvector` with a GIN index rather than `LIKE '%term%'`.

```sql
-- Add a stored generated tsvector column
ALTER TABLE transcripts ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(full_text, ''))
  ) STORED;

CREATE INDEX transcripts_search_idx ON transcripts USING gin (search_vector);

-- Fast full-text search with ranking
SELECT id, ts_rank(search_vector, query) AS rank
FROM transcripts, to_tsquery('english', 'climate & change') query
WHERE search_vector @@ query
ORDER BY rank DESC
LIMIT 20;
```

### 8.3 pgvector Best Practices

DHG uses pgvector. Apply these rules when working with embedding columns.

```sql
-- Create the extension once
CREATE EXTENSION IF NOT EXISTS vector;

-- Declare embedding column (match your model's output dimension)
ALTER TABLE segments ADD COLUMN embedding vector(1536);

-- IVFFlat index — faster builds, good for medium tables
-- lists = sqrt(row_count) is a common starting point
CREATE INDEX segments_embedding_ivfflat ON segments
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- HNSW index — slower build, faster queries, better recall
CREATE INDEX segments_embedding_hnsw ON segments
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Similarity search (cosine distance)
SELECT id, text, embedding <=> $1::vector AS distance
FROM segments
ORDER BY distance
LIMIT 10;

-- Tune probes at query time for accuracy/speed tradeoff (IVFFlat)
SET ivfflat.probes = 10;
```

---

## Checklist: Before Merging Any Schema or Query Change

- [ ] Every FK column has an index
- [ ] `EXPLAIN (ANALYZE, BUFFERS)` run on new queries — no unexpected Seq Scans
- [ ] JSONB columns queried for containment have a GIN index
- [ ] Timestamps use `timestamptz`, not `timestamp`
- [ ] New tables use lowercase snake_case identifiers
- [ ] Bulk writes use batch INSERT or COPY, not per-row loops
- [ ] Pagination uses cursor-based keyset, not OFFSET
- [ ] Upserts use `INSERT ... ON CONFLICT`, not SELECT-then-INSERT
- [ ] Transactions contain no external I/O (HTTP, file, sleep)
- [ ] `statement_timeout` is set on the SQLAlchemy engine
- [ ] Any singleton background job uses advisory locks

---

## Quick Reference: Run Inside dhg-registry-db

Connect:
```bash
docker exec -it dhg-registry-db psql -U postgres -d dhg_registry
```

Find missing FK indexes:
```sql
SELECT conrelid::regclass AS tbl, a.attname AS col
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid AND a.attnum = ANY(i.indkey)
  );
```

Top slow queries:
```sql
SELECT round(mean_exec_time::numeric,2) AS mean_ms, calls, query
FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
```

Table bloat check:
```sql
SELECT relname, n_dead_tup, n_live_tup,
  round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 1) AS dead_pct
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;
```
