# PostgreSQL Schema Design

Design, review, or evolve a PostgreSQL schema for the DHG AI Factory project (PostgreSQL 15 + pgvector, 57 tables, SQLAlchemy 2.0).

**Task:** $ARGUMENTS

## Capabilities

**What this command does:** Designs and reviews PostgreSQL schemas for the DHG AI Factory, covering data types, constraints, indexes, partitioning, RLS policies, and the corresponding SQLAlchemy 2.0 model definitions.

**Use it when you need to:**
- Design a new table with correct data types, PKs, FKs, and indexes for the DHG registry
- Choose between B-tree, GIN, HNSW, and IVFFlat indexes for a specific query pattern
- Plan table partitioning for the `events` audit log or other high-volume append-only tables
- Write or review safe schema migrations using `CREATE INDEX CONCURRENTLY` and transactional DDL
- Produce a matched pair of DDL and SQLAlchemy 2.0 `Mapped`/`mapped_column` model code

**Example invocations:**
- `/project:postgresql design a table for storing LangGraph agent run history with pgvector embeddings`
- `/project:postgresql review the segments table schema for scale to 100M rows`
- `/project:postgresql add RLS policies to the media table to isolate per-tenant data`

---

## When to use this command

- Designing a new table or schema for PostgreSQL
- Selecting data types and constraints
- Planning indexes, partitions, or RLS policies
- Reviewing existing tables for scale and maintainability
- Writing or auditing migrations

## When NOT to use this command

- Targeting a non-PostgreSQL database
- Query tuning only, with no schema changes
- Requiring a DB-agnostic modeling guide

---

## Approach

1. Capture entities, access patterns, and scale targets (rows, QPS, retention).
2. Choose data types and constraints that enforce invariants.
3. Add indexes for real query paths and validate with `EXPLAIN`.
4. Plan partitioning or RLS where required by scale or access control.
5. Review migration impact and apply changes safely.

---

## Safety

- Never run destructive DDL on production without backups and a rollback plan.
- Use migrations and staging validation before applying schema changes.
- Use `CREATE INDEX CONCURRENTLY` to avoid blocking writes on live tables.
- Test DDL changes in a transaction: `BEGIN; ALTER TABLE ...; ROLLBACK;` before committing.

---

## Core Rules

- Define a **PRIMARY KEY** for reference tables (users, orders, agents, etc.). Not always needed for time-series/event/log data. When used, prefer `BIGINT GENERATED ALWAYS AS IDENTITY`; use `UUID` only when global uniqueness or opacity is needed (e.g., external-facing IDs, distributed systems).
- **Normalize first (to 3NF)** to eliminate redundancy and update anomalies. Denormalize only for measured, high-ROI reads where join performance is proven problematic.
- Add **NOT NULL** everywhere semantically required; use **DEFAULT**s for common values.
- Create **indexes for access paths you actually query**: PK/unique (auto-created), FK columns (manual — PostgreSQL does NOT auto-index FK columns), frequent filters, sorts, and join keys.
- Prefer **TIMESTAMPTZ** for event time; **NUMERIC** for money; **TEXT** for strings; **BIGINT** for integers; **DOUBLE PRECISION** for floats (or `NUMERIC` for exact decimal arithmetic).

---

## PostgreSQL Gotchas

- **Identifiers**: unquoted identifiers are lowercased. Use `snake_case` for all table and column names. Never use quoted/mixed-case names.
- **Unique + NULLs**: `UNIQUE` allows multiple NULLs. Use `UNIQUE (...) NULLS NOT DISTINCT` (PG15+) to allow only one NULL.
- **FK indexes**: PostgreSQL does NOT auto-index foreign key columns. Always add them explicitly.
- **No silent coercions**: length/precision overflows raise errors, not silent truncation. `INSERT 999 INTO NUMERIC(2,0)` fails.
- **Sequence gaps are normal**: rollbacks, crashes, and concurrent transactions create gaps in identity sequences (1, 2, 5, 6...). Never try to make IDs consecutive.
- **Heap storage**: no clustered PK by default. `CLUSTER` is a one-off reorganization, not maintained on subsequent inserts.
- **MVCC**: updates and deletes leave dead tuples. Autovacuum handles reclaim — design to avoid hot wide-row churn.

---

## Data Types

### IDs
- `BIGINT GENERATED ALWAYS AS IDENTITY` — preferred for surrogate PKs
- `UUID` — use only when merging/federating data or for opaque external-facing IDs; generate with `gen_random_uuid()` (PG15) or `uuidv7()` (PG18+)

### Integers
- `BIGINT` — preferred unless storage is critical
- `INTEGER` — for smaller ranges
- Avoid `SMALLINT` unless strictly constrained

### Floats
- `DOUBLE PRECISION` — preferred over `REAL`
- `NUMERIC(p,s)` — for exact decimal arithmetic (prices, financial data)

### Strings
- `TEXT` — always; if length limits are needed, use `CHECK (LENGTH(col) <= n)` instead of `VARCHAR(n)`
- Never use `CHAR(n)`
- `BYTEA` — for binary data
- Case-insensitive: use expression index on `LOWER(col)` for plain ASCII; use non-deterministic collation for locale/accent handling; use `CITEXT` only if you need case-insensitive PK/FK/UNIQUE

### Time
- `TIMESTAMPTZ` — always for timestamps
- `DATE` — for date-only values
- `INTERVAL` — for durations
- Never use `TIMESTAMP` (without timezone) or `TIMETZ`
- `now()` — transaction start time; `clock_timestamp()` — current wall-clock time

### Booleans
- `BOOLEAN NOT NULL` unless tri-state values are explicitly required

### Enums
- `CREATE TYPE ... AS ENUM` — only for small, stable sets (e.g., days of week, US states)
- For evolving business values (e.g., order statuses): use `TEXT` with `CHECK` or a lookup table

### Arrays
- `TEXT[]`, `INTEGER[]`, etc. — for ordered lists where you query elements
- Index with **GIN** for containment (`@>`, `<@`) and overlap (`&&`)
- 1-indexed: `arr[1]`, slice: `arr[1:3]`
- Good for tags and categories; use junction tables for relations

### Range Types
- `daterange`, `numrange`, `tstzrange` — for intervals with overlap/containment logic
- Index with **GiST**
- Good for scheduling, versioning, numeric ranges
- Use `[)` (inclusive/exclusive) bounds consistently

### Network Types
- `INET` for IP addresses, `CIDR` for network ranges, `MACADDR` for MAC addresses

### Text Search
- `TSVECTOR` for indexed documents, `TSQUERY` for search queries
- Index `tsvector` with **GIN**
- Always specify language: `to_tsvector('english', col)` and `to_tsquery('english', 'query')`

### JSONB
- Preferred over `JSON`; index with **GIN**
- Use only for optional or semi-structured attributes
- Only use `JSON` (not `JSONB`) if original key ordering must be preserved
- Constrain allowed shapes: `CHECK (jsonb_typeof(col) = 'object')`

### Vectors (pgvector)
- `vector(n)` type from the `pgvector` extension for embedding similarity search
- Index with **IVFFlat** or **HNSW** depending on recall vs. throughput needs

### Domain and Composite Types
- `CREATE DOMAIN email AS TEXT CHECK (VALUE ~ '^[^@]+@[^@]+$')` — reusable validated types
- `CREATE TYPE address AS (street TEXT, city TEXT, zip TEXT)` — structured columns; access with `(col).field`

### Prohibited Types
- `TIMESTAMP` (without time zone) — use `TIMESTAMPTZ`
- `CHAR(n)` or `VARCHAR(n)` — use `TEXT`
- `MONEY` type — use `NUMERIC`
- `TIMETZ` — use `TIMESTAMPTZ`
- `TIMESTAMPTZ(0)` or any precision specification — use plain `TIMESTAMPTZ`
- `SERIAL` type — use `GENERATED ALWAYS AS IDENTITY`

---

## Table Types

- **Regular** — default; fully durable, WAL-logged
- **TEMPORARY** — session-scoped, auto-dropped, not logged; faster for scratch work
- **UNLOGGED** — persistent but not crash-safe; faster writes; good for caches and staging data

---

## Constraints

- **PRIMARY KEY**: implicit UNIQUE + NOT NULL; creates a B-tree index automatically
- **FOREIGN KEY**: specify `ON DELETE/UPDATE` action (`CASCADE`, `RESTRICT`, `SET NULL`, `SET DEFAULT`); always add an explicit index on the referencing column; use `DEFERRABLE INITIALLY DEFERRED` for circular FK dependencies
- **UNIQUE**: creates a B-tree index; allows multiple NULLs by default; prefer `NULLS NOT DISTINCT` (PG15+) unless duplicate NULLs are intentional
- **CHECK**: row-local; NULL values pass three-valued logic — combine with `NOT NULL` to fully enforce
- **EXCLUDE**: prevents overlapping values; `EXCLUDE USING gist (room_id WITH =, booking_period WITH &&)` prevents double-booking; requires GiST index

---

## Indexing

- **B-tree** — default; equality and range queries (`=`, `<`, `>`, `BETWEEN`, `ORDER BY`)
- **Composite** — column order matters; leftmost prefix rule; put most selective columns first
- **Covering** — `CREATE INDEX ON tbl (id) INCLUDE (name, email)` for index-only scans
- **Partial** — for hot subsets: `CREATE INDEX ON tbl (user_id) WHERE status = 'active'`
- **Expression** — for computed search keys: `CREATE INDEX ON tbl (LOWER(email))`; expression must match exactly in WHERE clause
- **GIN** — JSONB containment/existence, arrays, full-text search
- **GiST** — ranges, geometry, exclusion constraints
- **BRIN** — very large, naturally ordered data (time-series); minimal storage overhead; only effective when row order correlates with the indexed column

---

## JSONB Indexing

- Default GIN index: `CREATE INDEX ON tbl USING GIN (jsonb_col)` — accelerates containment (`@>`), key existence (`?`, `?|`, `?&`), and path containment
- Heavy containment workloads only: `CREATE INDEX ON tbl USING GIN (jsonb_col jsonb_path_ops)` — smaller and faster but loses `?`/`?|`/`?&` support
- Scalar field equality/range: extract with a generated column and B-tree index:
  ```sql
  ALTER TABLE tbl ADD COLUMN price INT GENERATED ALWAYS AS ((jsonb_col->>'price')::INT) STORED;
  CREATE INDEX ON tbl (price);
  ```
- Keep core relations in normalized columns; reserve JSONB for optional or variable attributes

---

## Partitioning

- Use for very large tables (>100M rows) where queries consistently filter on the partition key, or where data is pruned or bulk-replaced periodically.
- **RANGE** — time-series: `PARTITION BY RANGE (created_at)`
- **LIST** — discrete values: `PARTITION BY LIST (region)`
- **HASH** — even distribution: `PARTITION BY HASH (user_id)`
- Use declarative partitioning (PG10+). Do NOT use table inheritance.
- **Limitations**: no global UNIQUE constraints (include partition key in PK/UNIQUE); FKs from partitioned tables not supported — use triggers.
- **TimescaleDB** automates time-based or ID-based partitioning with retention policies and compression.

---

## Row-Level Security

```sql
ALTER TABLE tbl ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_access ON orders
  FOR SELECT TO app_users
  USING (user_id = current_user_id());
```

---

## Generated Columns

```sql
theme TEXT GENERATED ALWAYS AS (attrs->>'theme') STORED
```

PG18+ adds VIRTUAL columns (computed on read, not stored).

---

## Special Considerations

### Update-Heavy Tables

- Separate hot and cold columns — put frequently updated columns in a separate table to minimize bloat
- Use `fillfactor=90` to leave space for HOT updates that avoid index maintenance
- Avoid updating indexed columns — prevents beneficial HOT updates
- Partition by update patterns — separate frequently updated rows from stable data

### Insert-Heavy Workloads

- Minimize indexes — every index slows inserts; create only what is queried
- Use `COPY` or multi-row `INSERT` instead of single-row inserts
- Use `UNLOGGED` tables for rebuildable staging data
- Defer index creation for bulk loads: drop indexes, load data, recreate indexes
- Partition by time or hash to distribute load
- Consider a natural composite key (e.g., `(timestamp, device_id)`) instead of a surrogate PK

### Upsert-Friendly Design

- Requires a `UNIQUE` index on the conflict target columns — partial indexes do not work with `ON CONFLICT`
- Use `EXCLUDED.column` to reference would-be-inserted values; only update columns that actually changed
- `DO NOTHING` is faster than `DO UPDATE` when no actual update is needed

### Safe Schema Evolution

- **Transactional DDL**: most DDL runs in transactions — `BEGIN; ALTER TABLE ...; ROLLBACK;` for safe testing
- **Concurrent index creation**: `CREATE INDEX CONCURRENTLY` avoids write-blocking but cannot run inside a transaction
- **Volatile defaults cause table rewrites**: adding `NOT NULL` columns with volatile defaults (e.g., `now()`, `gen_random_uuid()`) rewrites the entire table; non-volatile defaults are fast
- **Drop constraints before columns**: `DROP CONSTRAINT` then `DROP COLUMN` to avoid dependency errors
- **Function signature changes**: `CREATE OR REPLACE` with different arguments creates overloads, not replacements — DROP the old version if no overload is intended

---

## Extensions Available in DHG AI Factory

- **`pgvector`** — vector similarity search for embeddings (installed)
- **`pgcrypto`** — `crypt()` for password hashing
- **`uuid-ossp`** — alternative UUID functions; prefer `gen_random_uuid()` for new work
- **`pg_trgm`** — fuzzy text search with `%` operator and `similarity()`; GIN index for `LIKE '%pattern%'`
- **`citext`** — case-insensitive text type
- **`btree_gin`** / **`btree_gist`** — mixed-type indexes (e.g., GIN on both JSONB and text)
- **`hstore`** — key-value pairs; mostly superseded by JSONB
- **`timescaledb`** — automated partitioning, retention, compression, continuous aggregates for time-series
- **`postgis`** — comprehensive geospatial support
- **`pgaudit`** — audit logging for all database activity

---

## SQLAlchemy 2.0 Alignment

When producing schema designs for this project, also provide the corresponding SQLAlchemy 2.0 model using:

- `mapped_column()` with explicit types (`BigInteger`, `Text`, `Numeric`, `DateTime(timezone=True)`, `JSONB`)
- `Mapped[T]` type annotations for all columns
- `relationship()` with `back_populates` rather than `backref`
- `ForeignKey` with `ondelete` matching the DDL `ON DELETE` action
- `Index()` objects for non-PK indexes, defined at the `__table_args__` level
- `CheckConstraint` for business rules
- `UniqueConstraint` for composite unique constraints

---

## Reference Examples

### Users Table

```sql
CREATE TABLE users (
  user_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email      TEXT NOT NULL,
  name       TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ON users (LOWER(email));
CREATE INDEX ON users (created_at);
```

### Orders Table

```sql
CREATE TABLE orders (
  order_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id    BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
  status     TEXT NOT NULL DEFAULT 'PENDING'
               CHECK (status IN ('PENDING', 'PAID', 'CANCELED')),
  total      NUMERIC(10,2) NOT NULL CHECK (total > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON orders (user_id);
CREATE INDEX ON orders (created_at);
```

### JSONB Attributes Table

```sql
CREATE TABLE profiles (
  user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
  attrs   JSONB NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(attrs) = 'object'),
  theme   TEXT GENERATED ALWAYS AS (attrs->>'theme') STORED
);
CREATE INDEX profiles_attrs_gin ON profiles USING GIN (attrs);
```

### Vector Embeddings Table

```sql
CREATE TABLE document_embeddings (
  embedding_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  document_id  BIGINT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
  model        TEXT NOT NULL,
  embedding    vector(1536) NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON document_embeddings (document_id);
CREATE INDEX ON document_embeddings USING hnsw (embedding vector_cosine_ops);
```
