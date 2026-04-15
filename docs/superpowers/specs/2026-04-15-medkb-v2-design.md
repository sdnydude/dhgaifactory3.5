# MedKB v2 — Unified Design Spec (Phases 1 through 5)

**Status:** Draft for review
**Date:** 2026-04-15
**Author:** Stephen Webber (design direction) + Claude (drafting)
**Supersedes:** `2026-04-15-medkb-phase4-5-addendum-design_v1.md` (the addendum-framed draft, saved as `_v1.md` per planning-file-versioning rule)
**Related:** DHG `prose_quality_agent.py` (integration target), DHG registry-db (sibling service, separate database)

---

## 0. Executive Summary

MedKB is a biomedical knowledge base service that DHG AI Factory agents query at inference time to ground drafted prose in vetted sources: biomedical concepts, inter-concept relationships, peer-reviewed literature, clinical guidelines, FDA drug labels, consumer health statements, and editorial style rules and exemplars.

**Greenfield status:** Nothing currently exists in the repo. No `medkb` directory, no `medkb` schema, no ingestor code, no `dhg-medkb-db` container. This spec defines the complete build from zero.

**Phase map:**

| Phase | Scope | Timeline | Exit gate owner |
|-------|-------|----------|-----------------|
| **1 — Foundation** | Schema, deployment topology, ingestor framework, embedding pipeline, 5 Phase 1 sources (MeSH, RxNorm, PrimeKG, PubMed abstracts, PMC OA), 4 API endpoints | This spec | Phase 1 exit gate in §12 |
| 2 — Reserved | Not in this spec | Separate spec when scoped | — |
| 3 — Reserved | Includes future MIMIC-IV / MedAlpaca DUA-gated work per prior decisions | Separate spec when scoped | — |
| **4 — Authoritative positions + writing layer** | USPSTF, DailyMed, MedlinePlus, style rules seed, CDC exemplars anchor. Writing layer integration into DHG agents. | This spec | Phase 4 exit gate in §12 |
| **5 — Fan-out** | Full DailyMed (~120K), more guideline bodies, MedlinePlus Spanish + NIH institutes + CDC full, expanded exemplars | This spec | Per-sub-phase gates in §12 |

**Six pillars (three from Phase 1, three from Phase 4):**

1. **Concepts** (Phase 1) — biomedical concepts from MeSH, RxNorm, PrimeKG nodes
2. **Relationships** (Phase 1) — inter-concept edges from PrimeKG + ingestor-derived
3. **Documents** (Phase 1) — chunked text with embeddings, initially from PubMed + PMC
4. **Authoritative Positions** (Phase 4) — clinical guidelines, FDA drug labels, consumer health statements, stored in `documents` with new metadata
5. **Style & Writing Guidance** (Phase 4) — editorial rules + public-domain prose exemplars, new tables
6. **Citation & Provenance** (Phase 4) — API layer composing citations over document metadata, no new table

**Deployment topology:**

```
┌───────────────────────────── Docker network: dhgaifactory35_dhg-network ──────────────────────────────┐
│                                                                                                       │
│    ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐                      │
│    │  dhg-registry-db    │    │  dhg-medkb-db       │    │  dhg-ollama         │                      │
│    │  (existing)         │    │  NEW Postgres+      │    │  (existing)         │                      │
│    │  :5432              │    │  pgvector :5433     │    │  :11434             │                      │
│    └──────────┬──────────┘    └──────────┬──────────┘    └──────────┬──────────┘                      │
│               │                          │                          │                                 │
│               ▼                          ▼                          │                                 │
│    ┌─────────────────────┐    ┌─────────────────────┐                │                                 │
│    │  dhg-registry-api   │    │  dhg-medkb-api      │                │                                 │
│    │  (existing)         │    │  NEW FastAPI :8015  │                │                                 │
│    │  :8011              │    │                     │◄───────────────┘                                 │
│    └──────────┬──────────┘    └──────────┬──────────┘                                                  │
│               │                          │                                                            │
│               │                          │       ┌─────────────────────┐                              │
│               │                          └──────►│  Ingestor containers │                             │
│               │                                  │  NEW per-source     │                              │
│               │                                  │  (cron-scheduled)   │                              │
│               │                                  └─────────────────────┘                              │
│               │                                                                                       │
│               ▼                                                                                       │
│    ┌─────────────────────────────────────────────┐                                                    │
│    │  LangGraph dhg-agents (existing)             │                                                   │
│    │  needs_assessment, research, grant_writer,  │                                                    │
│    │  prose_quality, ...                          │                                                   │
│    │  Reach MedKB via HTTP: dhg-medkb-api:8015    │                                                   │
│    └─────────────────────────────────────────────┘                                                    │
│                                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Key decisions baked in:**

- **Separate Postgres instance** (`dhg-medkb-db` on port 5433) — not a new schema in `dhg-registry-db`. MedKB's update cadence (large batch ingests, HNSW index rebuilds) differs radically from the registry's transactional OLTP pattern. Mixing them risks vacuum pressure and deploy coupling. Separate = separate failure domain.
- **nomic-embed-text for Phase 1 embeddings** — already running in Ollama, zero new infra. Produces 768d vectors compatible with future PubMedBERT migration since the column type is `vector(768)`. PubMedBERT deployment deferred pending Phase 1 retrieval-quality measurement against a golden test set.
- **Direct HTTP from DHG agents** — agents get a small `medkb_client.py` helper and call `dhg-medkb-api:8015` directly on the Docker network. No proxy through `dhg-registry-api`.
- **All Phase 4 columns on `documents` from day 1** — since this is greenfield, the `documents` table is created with `audience`, `evidence_level_oxford`, `grade_rating`, `valid_from`, `valid_to`, `version_label`, `readability_grade`, `source_authority` all present (nullable) from the first migration. No `ALTER TABLE` dance at Phase 4.
- **`style_rules` and `style_exemplars` tables created in Phase 1** — empty until Phase 4 seeds them. Same reason as above: no Phase 4 schema migration, just Phase 4 data.
- **License CHECK constraint on `style_exemplars` is live from Phase 1** — even though no rows exist until Phase 4, the guardrail is enforced from day 1.

**What this spec does NOT cover:**

- Phases 2 and 3 scope (reserved for separate specs when needed)
- MIMIC-IV / MedAlpaca ingestion (DUA-gated, separate workstream)
- NCCN, NICE, full-text Cochrane (copyrighted or paywalled, declined for Phases 1–5, revisit in Phase 6 with licensing negotiation)
- Fine-tuning or model training — the writing layer composes prompts, not weights
- Streaming API responses (batched only)
- Admin mutation API (write path is ingestor containers → DB directly)
- Authentication changes beyond the API-key pattern inherited from the registry

---

## 1. Program Context & Goals

### 1.1 Why MedKB exists

DHG AI Factory's drafting agents (needs_assessment, research, clinical_practice, gap_analysis, learning_objectives, curriculum_design, grant_writer, prose_quality) currently rely on three sources of grounding, each inadequate:

| Current source | Limitation |
|----------------|-----------|
| LLM parametric knowledge | Brittle. Hallucination-prone. No citability. Cutoff-bound. |
| Ad-hoc PubMed E-utilities lookups per agent run | One-off, no persistence, no reuse across runs, no indexing, no semantic search |
| Hardcoded editorial rules (`prose_quality_agent.BANNED_PATTERNS`) | Policy lives in code; adding a rule requires a redeploy; drafting LLMs never see the rules, only the after-pass catches violations |

MedKB consolidates all three into a single queryable service:

- **Citable facts** live in `documents` with provenance columns so generated prose can produce real AMA-format citations.
- **Semantic search** replaces ad-hoc keyword lookups with vector similarity over a persistent corpus.
- **Editorial policy** becomes queryable data instead of hardcoded constants — drafting LLMs retrieve rules *before* writing, and the `prose_quality_agent` queries the same rules *after* writing, eliminating the policy/enforcement split.

### 1.2 Primary callers

The primary users of MedKB are DHG LangGraph agents. Secondary users: human analysts using a future admin UI (out of scope for this spec), and batch evaluation scripts.

| Agent | Uses MedKB for | Phases required |
|-------|----------------|-----------------|
| `research_agent` | Literature retrieval, concept lookup, citation formatting | Phase 1 |
| `clinical_practice_agent` | Standard-of-care positions, clinical guidelines | Phase 1 (literature), Phase 4 (guidelines) |
| `needs_assessment_agent` | Gap evidence, patient-voice exemplars, writing-layer retrieval | Phase 1 (literature), Phase 4 (guidelines + exemplars) |
| `gap_analysis_agent` | Evidence for quantified gaps | Phase 1 |
| `learning_objectives_agent` | Moore's framework evidence | Phase 1 |
| `curriculum_design_agent` | Educational innovation evidence | Phase 1 |
| `grant_writer_agent` | Full-document citation assembly, rules + exemplars for writing layer | Phase 1 (citations), Phase 4 (rules + exemplars) |
| `prose_quality_agent` | Editorial rule enforcement (after-pass) | Phase 4 |

Phase 1 alone unlocks literature grounding and basic citation for all drafting agents. Phase 4 adds the writing layer and authoritative positions. Phase 5 is content fan-out — the same agents with more corpus to retrieve from.

### 1.3 Non-goals

- **Not a general medical Q&A system.** MedKB does not answer clinical questions directly. It returns retrieval results; the drafting LLM interprets them.
- **Not a replacement for RAG in chat UIs.** The `/inbox` chat experience has its own retrieval pipeline (via LangGraph). MedKB is for structured pipeline agents, not conversational interfaces.
- **Not a place for operational/pipeline state.** Agent runs, thread IDs, interrupts, outputs — all of that lives in `dhg-registry-db`. MedKB is read-mostly knowledge.
- **Not a substitute for professional medical review.** A drafted grant is still reviewed by humans before submission. MedKB reduces hallucination risk but does not eliminate the need for human domain review.

---

## 2. Architecture Overview

### 2.1 Six pillars in one schema

All six pillars live in a single Postgres schema named `medkb` inside a dedicated instance:

```
medkb.concepts          — Phase 1, primary populator: MeSH + RxNorm + PrimeKG nodes
medkb.relationships     — Phase 1, primary populator: PrimeKG edges + ingestor-derived
medkb.documents         — Phase 1 (PubMed/PMC) and Phase 4 (guidelines, labels, consumer health)
medkb.style_rules       — Phase 4 seed (DHG + AMA + PLAIN)
medkb.style_exemplars   — Phase 4 seed (CDC), Phase 5 fan-out
medkb.ingest_reports    — Phase 1 forward, observability table for every ingestor run
```

Citation & Provenance (the sixth "pillar") has no table. It is an API layer that composes over existing document columns. See §9.4.

### 2.2 Deployment topology

**New containers added by this spec:**

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `dhg-medkb-db` | `pgvector/pgvector:pg16` | 5433 | Postgres + pgvector, hosts `medkb` schema. Persistent volume `dhg-medkb-db-data`. |
| `dhg-medkb-api` | Built from `services/medkb-api/Dockerfile` | 8015 | FastAPI service exposing `/v1/*` endpoints. Stateless; restarts freely. |
| `dhg-medkb-ingest-{source}` | Built from `services/medkb-ingestors/Dockerfile` with `INGESTOR_CLASS` env | No external port | One container per source. Cron-scheduled via an internal scheduler. Shared base image. |

**Reused infrastructure:**

| Component | Role |
|-----------|------|
| `dhg-ollama` (port 11434) | Serves `nomic-embed-text` for embeddings |
| `dhg-prometheus`, `dhg-grafana`, `dhg-loki`, `dhg-tempo`, `dhg-alertmanager` | Observability stack — MedKB emits metrics, logs, traces |
| `dhgaifactory35_dhg-network` | Docker network — all MedKB containers join the existing network |

**Why a separate Postgres instance (not a new schema in `dhg-registry-db`):**

| Concern | Shared DB impact | Separate DB benefit |
|---------|------------------|---------------------|
| Update cadence | MedKB ingests batch hundreds of thousands of rows; registry is transactional OLTP — mixing wrecks autovacuum scheduling | Separate vacuum, separate statistics, separate workers |
| HNSW index rebuilds | An index rebuild on 725K chunks stalls registry queries | Index rebuilds only affect MedKB traffic |
| Deploy coupling | A MedKB migration could require downtime for registry traffic | Independent deploy + rollback |
| Failure domain | A misbehaving MedKB ingestor could exhaust connections or bloat the shared DB | Failure isolated to MedKB service |
| Storage sizing | Registry DB lives on a volume sized for operational state (~10GB); MedKB expects ~100+ GB at Phase 5 | Separate volume, separate disk planning |

**Why direct HTTP from DHG agents (not via `dhg-registry-api` as proxy):**

- Proxy adds ~5-10ms latency per call. At 20+ MedKB calls per grant run, this is ~200ms overhead for no benefit.
- Proxy creates a failure coupling: `dhg-registry-api` bounce takes MedKB offline for agents even though MedKB itself is fine.
- Proxy requires maintaining a shadow router for MedKB endpoints in `registry/api.py`.
- Direct HTTP means agents get a 30-line `medkb_client.py` helper and that's it.

### 2.3 Phase split (what ships when)

```
Phase 1 (FOUNDATION)                    Phase 4 (ANCHOR)             Phase 5 (FAN-OUT)
──────────────────                      ──────────────               ─────────────────
 Schema (all 6 tables)                    + USPSTF (~120)              + DailyMed full (~120K)
 Ingestor framework                       + DailyMed (~200)            + MedlinePlus ES
 Embedding pipeline                       + MedlinePlus EN (~1K)       + CDC full corpus
 nomic-embed-text wiring                  + 47 style rules seed        + NIH institutes
 MeSH ingest                              + CDC exemplars (20)         + AHA/ACC, IDSA
 RxNorm ingest                            + Writing-layer integration  + Cochrane abstracts
 PrimeKG ingest [UNCERTAIN]               + prose_quality_agent        + AHRQ, CDC CPSTF, WHO
 PubMed abstracts ingest                    migrates to DB rules       + PLOS Med, eLife,
 PMC OA full-text ingest                                                 NIH News, NLM Profiles,
 /v1/search/semantic                                                     NIH Record, PMC narrative
 /v1/search/literature                                                 + openFDA summaries
 /v1/concept/{src}/{id}                                                + FDA Drug Approvals
 /v1/graph/neighbors/{id}                                              + FDA Consumer Updates
 DHG medkb_client.py helper
 Phase 1 exit gate
```

Each phase is independently shippable. Phase 4 cannot start until Phase 1's exit gate is green. Phase 5 sub-phases run in the internal order documented in §6.

---

## 3. Database Design

All DDL is greenfield. No `ALTER TABLE` in this section — tables are created with every column present from the start.

### 3.1 Schema and extensions

```sql
CREATE SCHEMA medkb;
CREATE EXTENSION IF NOT EXISTS vector;          -- pgvector
CREATE EXTENSION IF NOT EXISTS pg_trgm;         -- trigram for synonym lookup
CREATE EXTENSION IF NOT EXISTS btree_gin;       -- composite index support
```

### 3.2 `medkb.concepts`

Biomedical concepts with stable source-specific identifiers.

```sql
CREATE TABLE medkb.concepts (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source       TEXT NOT NULL,                 -- 'MESH' | 'RXNORM' | 'PRIMEKG' | ...
    source_id    TEXT NOT NULL,                 -- MeSH descriptor UI, RxCUI, PrimeKG node id, etc.
    name         TEXT NOT NULL,                 -- canonical name
    definition   TEXT,                          -- prose definition when available
    synonyms     TEXT[],                        -- alternate names / aliases
    embedding    vector(768),                   -- embedding of (name + definition + top-k synonyms)
    metadata     JSONB DEFAULT '{}'::jsonb,     -- source-specific fields (tree numbers, semantic types, ...)
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT concepts_source_id_unique UNIQUE (source, source_id)
);

CREATE INDEX medkb_concepts_embedding_hnsw
    ON medkb.concepts USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX medkb_concepts_name_trgm
    ON medkb.concepts USING gin (name gin_trgm_ops);

CREATE INDEX medkb_concepts_synonyms_gin
    ON medkb.concepts USING gin (synonyms);

CREATE INDEX medkb_concepts_metadata_gin
    ON medkb.concepts USING gin (metadata);
```

The `(source, source_id)` unique constraint is the stable identity for upserts. Ingestors use it for `ON CONFLICT DO UPDATE`.

### 3.3 `medkb.relationships`

Typed edges between concepts.

```sql
CREATE TABLE medkb.relationships (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id    UUID NOT NULL REFERENCES medkb.concepts(id) ON DELETE CASCADE,
    target_id    UUID NOT NULL REFERENCES medkb.concepts(id) ON DELETE CASCADE,
    rel_type     TEXT NOT NULL,                 -- 'is_a' | 'treats' | 'causes' | 'interacts_with' | 'supersedes' | ...
    provenance   TEXT NOT NULL,                 -- 'PRIMEKG' | 'USPSTF' | 'DailyMed' | ...
    evidence     TEXT,                          -- optional evidence pointer (PMID, DOI, URL)
    metadata     JSONB DEFAULT '{}'::jsonb,
    created_at   TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT relationships_no_self_edge CHECK (source_id <> target_id),
    CONSTRAINT relationships_unique UNIQUE (source_id, target_id, rel_type, provenance)
);

CREATE INDEX medkb_relationships_source ON medkb.relationships (source_id, rel_type);
CREATE INDEX medkb_relationships_target ON medkb.relationships (target_id, rel_type);
CREATE INDEX medkb_relationships_rel_type ON medkb.relationships (rel_type);
```

**Note on `rel_type`:** free-text TEXT (not an enum) to accept new edge types without schema migration. Documented vocabulary lives in `docs/medkb-rel-types.md`. `supersedes` is added here — introduced in Phase 4 for guideline version chains — so both phases can use it without an ALTER.

### 3.4 `medkb.documents`

Chunked text with embeddings. Populated in Phase 1 from PubMed + PMC, then in Phase 4 from guidelines + drug labels + consumer health.

```sql
CREATE TABLE medkb.documents (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source                TEXT NOT NULL,             -- 'PUBMED' | 'PMC' | 'USPSTF' | 'DailyMed' | 'MedlinePlus' | ...
    source_id             TEXT NOT NULL,             -- PMID | PMCID | SPL setid | USPSTF topic id | ...
    title                 TEXT NOT NULL,
    chunk_text            TEXT NOT NULL,
    chunk_index           INT  NOT NULL,
    total_chunks          INT,                       -- total chunks for this source_id (null if not yet known)
    embedding             vector(768),
    authors               TEXT[],                    -- populated for literature sources
    publication_date      DATE,                      -- for literature: journal pub date; for guidelines: valid_from
    doi                   TEXT,
    pmid                  TEXT,
    pmcid                 TEXT,

    -- Phase 4 columns, nullable, present from day 1
    audience              TEXT,
    evidence_level_oxford TEXT,
    grade_rating          TEXT,
    valid_from            DATE,
    valid_to              DATE,
    version_label         TEXT,
    readability_grade     NUMERIC(4,1),
    source_authority      TEXT,

    metadata              JSONB DEFAULT '{}'::jsonb,
    ingested_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT documents_source_id_chunk_unique UNIQUE (source, source_id, chunk_index),
    CONSTRAINT documents_audience_check
        CHECK (audience IS NULL OR audience IN
            ('clinician','patient','journalist','mixed','unknown')),
    CONSTRAINT documents_oxford_check
        CHECK (evidence_level_oxford IS NULL OR evidence_level_oxford IN
            ('1a','1b','2a','2b','3a','3b','4','5','na')),
    CONSTRAINT documents_authority_check
        CHECK (source_authority IS NULL OR source_authority IN
            ('guideline_body','regulatory','peer_reviewed',
             'consumer_health','preprint','tertiary_reference'))
);

CREATE INDEX medkb_documents_embedding_hnsw
    ON medkb.documents USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX medkb_documents_source ON medkb.documents (source);
CREATE INDEX medkb_documents_pmid ON medkb.documents (pmid) WHERE pmid IS NOT NULL;
CREATE INDEX medkb_documents_pmcid ON medkb.documents (pmcid) WHERE pmcid IS NOT NULL;
CREATE INDEX medkb_documents_pub_date ON medkb.documents (publication_date);
CREATE INDEX medkb_documents_audience ON medkb.documents (audience) WHERE audience IS NOT NULL;
CREATE INDEX medkb_documents_authority ON medkb.documents (source_authority) WHERE source_authority IS NOT NULL;
CREATE INDEX medkb_documents_valid_from ON medkb.documents (valid_from) WHERE valid_from IS NOT NULL;
CREATE INDEX medkb_documents_metadata_gin ON medkb.documents USING gin (metadata);

-- Partial index for the Phase 4 "current only" hot path
CREATE INDEX medkb_documents_current
    ON medkb.documents (source, source_authority)
    WHERE valid_to IS NULL;
```

**Column rationale:**

| Column | Phase | Why here and not in metadata |
|--------|-------|------------------------------|
| `audience`, `source_authority`, `evidence_level_oxford`, `valid_from`, `valid_to`, `readability_grade` | Phase 4 | Filtered on every hot-path API query. Columns, not JSONB, for B-tree index efficiency. |
| `pmid`, `pmcid`, `doi` | Phase 1 | Literature-specific but extremely hot — agents cite by PMID constantly. Columns + partial indexes beat JSONB extraction. |
| Everything else | — | JSONB `metadata` for source-specific fields that aren't filter targets |

### 3.5 `medkb.style_rules`

Editorial rules. Created in Phase 1, seeded in Phase 4.

```sql
CREATE TABLE medkb.style_rules (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_category  TEXT NOT NULL,           -- 'banned_phrase' | 'structure' | 'citation_format'
                                            --   | 'readability' | 'tone' | 'ama_style'
    rule_name      TEXT NOT NULL UNIQUE,
    rule_text      TEXT NOT NULL,           -- human-readable rule for LLM context
    pattern        TEXT,                    -- optional regex for automated check (nullable)
    severity       TEXT NOT NULL,           -- 'must' | 'should' | 'avoid'
    source         TEXT NOT NULL,           -- 'DHG_BANNED_PATTERNS' | 'AMA_Manual' | 'PLAIN' | ...
    audience_scope TEXT[],                  -- ['clinician','patient'] or single
    embedding      vector(768),
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT style_rules_severity_check
        CHECK (severity IN ('must','should','avoid'))
);

CREATE INDEX medkb_style_rules_embedding_hnsw
    ON medkb.style_rules USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX medkb_style_rules_category ON medkb.style_rules (rule_category);
CREATE INDEX medkb_style_rules_source ON medkb.style_rules (source);
```

### 3.6 `medkb.style_exemplars`

Public-domain or CC-BY prose chunks. Created in Phase 1, seeded in Phase 4.

```sql
CREATE TABLE medkb.style_exemplars (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title             TEXT NOT NULL,
    source            TEXT NOT NULL,
    source_url        TEXT NOT NULL,
    license           TEXT NOT NULL,         -- 'public_domain' | 'CC-BY' | 'CC-BY-SA'
    audience_tag      TEXT NOT NULL,         -- 'clinician' | 'patient' | 'journalist'
    register_tag      TEXT NOT NULL,         -- 'authoritative' | 'explanatory' | 'narrative' | 'instructional'
    topic_tags        TEXT[],
    chunk_text        TEXT NOT NULL,
    chunk_index       INT  NOT NULL,
    word_count        INT  NOT NULL,
    readability_grade NUMERIC(4,1),
    embedding         vector(768),
    ingested_at       TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT exemplars_license_check
        CHECK (license IN ('public_domain','CC-BY','CC-BY-SA')),
    CONSTRAINT exemplars_audience_check
        CHECK (audience_tag IN ('clinician','patient','journalist')),
    CONSTRAINT exemplars_register_check
        CHECK (register_tag IN ('authoritative','explanatory','narrative','instructional'))
);

CREATE INDEX medkb_style_exemplars_embedding_hnsw
    ON medkb.style_exemplars USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX medkb_style_exemplars_audience_register
    ON medkb.style_exemplars (audience_tag, register_tag);

CREATE INDEX medkb_style_exemplars_source ON medkb.style_exemplars (source);
CREATE INDEX medkb_style_exemplars_topic_tags ON medkb.style_exemplars USING gin (topic_tags);
```

**Critical guardrail:** `exemplars_license_check` is enforced at the database level from Phase 1. Even though the table is empty until Phase 4, any ingestor bug that tries to store a copyrighted source fails loudly at the DB. This is the single most important safety property of the style-exemplar design.

### 3.7 `medkb.ingest_reports`

Audit trail of every ingestor run. Used by Grafana and by ops during rollout.

```sql
CREATE TABLE medkb.ingest_reports (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name    TEXT NOT NULL,
    started_at     TIMESTAMPTZ NOT NULL,
    ended_at       TIMESTAMPTZ,
    mode           TEXT NOT NULL,          -- 'incremental' | 'full' | 'backfill'
    items_ingested INT DEFAULT 0,
    items_skipped  INT DEFAULT 0,
    items_errored  INT DEFAULT 0,
    unmapped_count INT DEFAULT 0,
    error_summary  JSONB,                  -- first 10 errors for post-mortem

    CONSTRAINT ingest_reports_mode_check
        CHECK (mode IN ('incremental','full','backfill'))
);

CREATE INDEX medkb_ingest_reports_source_time
    ON medkb.ingest_reports (source_name, started_at DESC);
```

### 3.8 Index rationale summary

| Index | Purpose | Cost consideration |
|-------|---------|---------------------|
| `*_embedding_hnsw` on 4 tables | Vector similarity search — hot path | HNSW rebuild is expensive; `m=16, ef_construction=64` is the standard balance |
| Trigram on `concepts.name` | Fuzzy name lookup when agents query by string | Modest storage cost |
| GIN on `synonyms`, `topic_tags`, `metadata` | Array/JSONB contains queries | Moderate cost; worth it for filter endpoints |
| Partial indexes with `WHERE` clauses | Smaller, faster indexes for hot sub-queries | Only covers rows matching predicate — size ≪ full index |
| Composite `(source, source_id)` unique | Idempotent upsert target | Negligible cost; correctness critical |

---

## 4. Phase 1 Ingestion — Foundation Sources

Five sources land in Phase 1. Each one is proven end-to-end before Phase 4 starts.

### 4.1 MeSH — Medical Subject Headings

| Property | Value |
|----------|-------|
| Source | NLM Medical Subject Headings vocabulary |
| Access | Bulk XML at `https://www.nlm.nih.gov/mesh/download_mesh.html` (annual release + monthly updates) |
| License | Public domain (NLM) |
| Volume (Phase 1) | All ~30,000 descriptors + all ~90,000 supplementary concept records |
| Writes to | `medkb.concepts` + `medkb.relationships` (tree hierarchy edges `parent_of` / `child_of`) |

**Field mapping:**

```
source        = 'MESH'
source_id     = DescriptorUI (e.g., "D006973") or SupplementalRecordUI (e.g., "C000012")
name          = DescriptorName / SupplementalRecordName
definition    = Annotation field (prose when present)
synonyms      = ConceptList / TermList names + entry terms
embedding     = nomic-embed-text of (name + " — " + definition + "; synonyms: " + top-10 synonyms joined)
metadata      = { "tree_numbers": [...], "semantic_types": [...], "mesh_year": 2026 }
```

**Relationships produced:** MeSH's tree hierarchy yields `is_a` and `part_of` edges between descriptors based on tree-number prefixes. Rough count: ~60K edges.

**Update cadence:** monthly incremental (NLM publishes monthly).

### 4.2 RxNorm — Normalized drug vocabulary

| Property | Value |
|----------|-------|
| Source | NLM RxNorm |
| Access | Monthly RRF files at `https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html` |
| License | Public domain (NLM) |
| Volume (Phase 1) | All ~600,000 active RxCUIs + all brand/generic/strength variants |
| Writes to | `medkb.concepts` + `medkb.relationships` (ingredient, brand_of, contains, tradename_of) |

**Field mapping:**

```
source        = 'RXNORM'
source_id     = RxCUI (e.g., "6809" for metformin)
name          = RxNorm string (TTY-preferred: IN > PIN > SCD > SBD)
definition    = NULL (RxNorm doesn't publish prose definitions)
synonyms      = all other TTY strings for this RxCUI
embedding     = nomic-embed-text of (name + "; " + synonyms joined)
metadata      = { "tty": "IN", "ingredients": [...], "ndc_codes": [...] }
```

**Relationships produced:** RxNorm concept relationships (RXNCONSO / RXNREL) yield `has_ingredient`, `brand_of`, `has_tradename`, `has_strength` edges. Rough count: ~2M edges.

**Update cadence:** monthly (NLM monthly release).

### 4.3 PrimeKG — Precision Medicine Knowledge Graph [UNCERTAIN — RESOLVE AT REVIEW]

| Property | Value |
|----------|-------|
| Source | Harvard Precision Medicine Knowledge Graph |
| Access | Bulk CSV download from `https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/IXA7BM` |
| License | **MIT-like (verify before Phase 1 ingest)** — Harvard publishes PrimeKG under an open license but the exact terms should be confirmed at ingest time |
| Volume (Phase 1) | ~130,000 nodes, ~4,000,000 edges across 10 biomedical entity types |
| Writes to | `medkb.concepts` (new nodes that don't reconcile to MeSH/RxNorm) + `medkb.relationships` (all edges) |

**[UNCERTAIN — RESOLVE AT REVIEW]** PrimeKG ingestion is tentatively scoped for Phase 1 because the addendum draft assumed it was there. But: (a) license confirmation is required, (b) 4M edges is a significant volume to ingest and validate in Phase 1, (c) PrimeKG's node model doesn't cleanly reconcile with MeSH/RxNorm (it has its own internal node IDs). Three options for you to decide:

- **A —** Include PrimeKG in Phase 1 as drafted. Confirm license during implementation.
- **B —** Defer PrimeKG to a Phase 1b follow-on after the first three sources ship. Phase 1 ships with MeSH + RxNorm + PubMed + PMC, and PrimeKG lands 2–3 weeks later once the ingestor framework is proven on simpler sources.
- **C —** Drop PrimeKG entirely; use a different relationships source (UMLS Metathesaurus MRREL, SemMedDB predicates, or start with empty relationships and add them later).

**My recommendation: Option B.** PrimeKG is the riskiest Phase 1 source (license + volume + reconciliation complexity). The other four are proven public-domain NLM corpora with simple parsers. Deferring PrimeKG to Phase 1b lets the framework stabilize first and keeps the Phase 1 exit gate achievable.

**Field mapping (if included):**

```
source        = 'PRIMEKG'
source_id     = node_index from PrimeKG nodes.csv
name          = node_name
definition    = node_source-specific (e.g., for disease nodes, the MONDO/UMLS definition)
synonyms      = [] (PrimeKG doesn't publish synonyms)
embedding     = nomic-embed-text of (name + " [" + node_type + "]")
metadata      = { "node_type": "disease"|"gene"|"drug"|..., "x_id": "...", "x_source": "MONDO"|... }
```

**Cross-source reconciliation:** PrimeKG disease nodes carry `x_source` cross-references (e.g., `MONDO:0005090`). The ingestor attempts to match each PrimeKG disease to an existing MeSH descriptor via MONDO→MeSH mappings. Unmatched nodes are ingested as new `source='PRIMEKG'` concepts. Nothing is ever dropped.

### 4.4 PubMed abstracts

| Property | Value |
|----------|-------|
| Source | NCBI PubMed |
| Access | Bulk baseline XML at `https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/` + daily updates at `.../updatefiles/` |
| License | Public domain (US federal work; individual abstracts may have journal-specific restrictions on full text, but abstracts themselves are citable and redistributable) |
| Volume (Phase 1) | Target: ~500,000 abstracts from high-impact biomedical journals, past 5 years. Full baseline (~35M) deferred to Phase 5+ fan-out. |
| Writes to | `medkb.documents` only |

**Journal filter for Phase 1:** limit to a curated list of ~500 journals identified by NLM ID. Covers NEJM, Lancet, JAMA, BMJ, Annals of Internal Medicine, Circulation, JCO, and the top specialty journals per ICMJE / NLM's "core clinical journals" list. This gives agents high-signal literature without paying the full-baseline cost in Phase 1.

**Field mapping:**

```
source            = 'PUBMED'
source_id         = PMID (string form of the integer)
title             = ArticleTitle
chunk_text        = AbstractText (concatenated across structured sections if present)
chunk_index       = 0 (single chunk per abstract; abstract-length fits in one embedding context)
total_chunks      = 1
embedding         = nomic-embed-text of (title + "\n\n" + chunk_text)
authors           = AuthorList / Author LastName + ForeName
publication_date  = ArticleDate or PubDate
doi               = ELocationID[@EIdType='doi']
pmid              = PMID
audience          = 'clinician'
source_authority  = 'peer_reviewed' (or 'preprint' if the journal is flagged as a preprint server)
evidence_level_oxford = mapped from PublicationType via CEBM table (see §4.4.1)
readability_grade = computed via textstat
metadata          = { "publication_type": [...], "journal": "...", "nlm_id": "...", "mesh_terms": [...] }
```

**Concept cross-reference:** each abstract's MeSH terms (from MedlineCitation/MeshHeadingList) get resolved to `medkb.concepts` via `source='MESH' AND source_id=<DescriptorUI>`. Resolved concept IDs go in `metadata.mesh_concept_ids` for graph-aware queries.

#### 4.4.1 CEBM evidence-level mapping

Derived at ingest time from PublicationType tags. Mapping table:

| PublicationType | `evidence_level_oxford` |
|-----------------|--------------------------|
| Systematic Review, Meta-Analysis | `1a` |
| Randomized Controlled Trial | `1b` |
| Controlled Clinical Trial (non-randomized) | `2b` |
| Cohort Studies | `2b` |
| Case-Control Studies | `3b` |
| Case Reports | `4` |
| Editorial, Letter, Comment, News | `5` |
| Review (non-systematic) | `5` |
| Guideline, Practice Guideline | `na` |
| (no matching type) | NULL |

**Update cadence:** daily delta pull.

### 4.5 PMC Open Access subset

| Property | Value |
|----------|-------|
| Source | NCBI PubMed Central Open Access subset |
| Access | Bulk at `https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_bulk/` (commercial-use-allowed subset) |
| License | CC-BY / CC-BY-SA / CC0 (published per article in the bulk metadata) |
| Volume (Phase 1) | Target: ~100,000 articles matching the Phase 1 journal filter from §4.4, or with MeSH terms in a curated domain list |
| Writes to | `medkb.documents` only |

**Field mapping:** same as PubMed abstracts except:

```
source            = 'PMC'
source_id         = PMCID (e.g., "PMC8765432")
chunk_text        = chunk from full-text body (split at section boundaries, max 512 tokens per chunk)
chunk_index       = 0, 1, 2, ... (multi-chunk per article)
total_chunks      = count of chunks for this article
metadata          = { ..., "pmc_license": "CC-BY", "section_title": "Methods"|"Results"|..., "pmc_section_ix": 3 }
```

**Chunking strategy:** split at `<sec>` boundaries from JATS XML, then sub-split any section > 512 tokens using sentence boundaries. Never split mid-sentence.

**License enforcement:** the ingestor checks each article's license field in the bulk metadata and only writes articles with `CC-BY`, `CC-BY-SA`, or `CC0`. Articles with "no-derivatives" or "non-commercial" clauses are logged and skipped. The `style_exemplars` license CHECK doesn't apply to `documents` — commercial-use-restricted PMC articles are safe in `documents` but we skip them for simplicity and legal defensibility.

**Update cadence:** weekly delta pull.

### 4.6 Phase 1 ingest summary

| Source | Table(s) | Records (Phase 1) | Relationships produced | Update cadence |
|--------|----------|-------------------|------------------------|----------------|
| MeSH | `concepts` + `relationships` | ~120K concepts, ~60K edges | `is_a`, `part_of` | Monthly |
| RxNorm | `concepts` + `relationships` | ~600K concepts, ~2M edges | `has_ingredient`, `brand_of`, `has_tradename`, `has_strength` | Monthly |
| PrimeKG [uncertain] | `concepts` + `relationships` | ~130K nodes, ~4M edges | ~30 rel_types | Annual |
| PubMed abstracts | `documents` | ~500K abstracts | — | Daily |
| PMC OA | `documents` | ~100K articles, ~800K chunks | — | Weekly |

**Phase 1 total row counts (if PrimeKG included):** ~850K concepts, ~6M relationships, ~1.3M document chunks.
**Phase 1 total row counts (PrimeKG deferred to Phase 1b):** ~720K concepts, ~2M relationships, ~1.3M document chunks.

---

## 5. Phase 4 Ingestion — Anchor Sources

Phase 4 adds five anchor sources — one per new data class — each proven end-to-end before Phase 5 fan-out. Anchor volumes are deliberately small: Phase 4 proves the mechanism, Phase 5 scales it.

### 5.1 Clinical Guidelines anchor — USPSTF

| Property | Value |
|----------|-------|
| Source | US Preventive Services Task Force |
| Access | JSON recommendation summaries at `https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics` + per-recommendation JSON endpoints |
| License | US federal government work — public domain |
| Volume (Phase 4 anchor) | All ~90 current recommendations + ~30 archived (superseded) versions for supersession-chain testing |
| Writes to | `medkb.documents` only (no concept creation — USPSTF topics map to existing MeSH concepts) |
| Chunking | Section-level: Recommendation, Rationale, Clinical Considerations, Supporting Evidence — do not chunk below section |

**Field mapping:**

```
audience              = 'clinician'
source                = 'USPSTF'
source_authority      = 'guideline_body'
evidence_level_oxford = NULL
grade_rating          = NULL
valid_from            = recommendation publication date
valid_to              = NULL if current; set to supersession date when newer version lands
version_label         = "2021 Update" etc. from source
readability_grade     = computed via textstat
metadata.uspstf_grade = raw letter grade ("B", "I") in metadata JSONB
```

**USPSTF-vs-GRADE gotcha:** USPSTF letter grades (A/B/C/D/I) are NOT GRADE. Storing them in `grade_rating` would conflate two different systems. They live in `metadata.uspstf_grade`. The citation API surfaces them separately.

**Supersession chain test (Phase 4 acceptance):** when the 2023 lung cancer screening recommendation is ingested after the 2021 version, the ingestor:

1. Finds the existing 2021 record via `source='USPSTF' AND metadata->>'topic'='lung_cancer_screening'`
2. Sets its `valid_to` to 2023 publication date
3. Writes a `supersedes` relationship: new_record → old_record
4. Verifies both versions remain queryable via `as_of_date` parameter

If this doesn't work right on a known dataset, we fix it before any other source hits the supersedes logic.

### 5.2 FDA Drug Labels anchor — DailyMed

| Property | Value |
|----------|-------|
| Source | NLM DailyMed Structured Product Labels (SPL) |
| Access | REST API at `https://dailymed.nlm.nih.gov/dailymed/services/v2/spls` + bulk SPL zip archives |
| License | Public domain (NLM) |
| Volume (Phase 4 anchor) | ~200 drugs — intersection of (all ~400 FDA boxed-warning drugs) + (top 100 by US prescription volume per CMS) |
| Writes to | `documents` (SPL sections as chunks) + `relationships` (`interacts_with`, `contraindicated_in` when parseable) |
| Chunking | SPL section-level: Boxed Warning, Indications, Contraindications, Warnings and Precautions, Drug Interactions, Adverse Reactions, Dosage, Patient Counseling Information |

**Field mapping:**

```
audience              = 'clinician' for prescribing sections
                      = 'patient' for Patient Counseling Information sections (SPL separates cleanly)
source                = 'DailyMed'
source_authority      = 'regulatory'
evidence_level_oxford = NULL
grade_rating          = NULL
valid_from            = SPL effective date
valid_to              = set when a newer SPL version for same setid is ingested
version_label         = SPL version number
metadata.setid        = SPL set ID (stable across versions)
metadata.ndc          = NDC codes from the SPL
metadata.rxcui        = cross-reference to existing RxNorm concept records
metadata.safety_critical = true for chunks from Boxed Warning sections
```

**Concept reconciliation:** link each SPL to its RxNorm concept via `rxcui`. Unmapped drugs log to `dailymed_unmapped.log`; don't create orphan concepts.

**Parser robustness:** SPL XML is 200–800 KB per label and inconsistently structured across manufacturers. Parse section-by-section with graceful degradation — a missing Drug Interactions section is logged but doesn't fail the ingest.

**Safety layer:** every Boxed Warning chunk gets `metadata.safety_critical = true`. The citation API prepends these to any drug query. See §9.5.

### 5.3 Consumer Health anchor — MedlinePlus English

| Property | Value |
|----------|-------|
| Source | NLM MedlinePlus (English health topics) |
| Access | Web Service API at `https://wsearch.nlm.nih.gov/ws/query` + bulk XML at `https://medlineplus.gov/xml.html` |
| License | Public domain (NLM) |
| Volume (Phase 4 anchor) | All ~1,000 English health topics. Spanish deferred to Phase 5. Drug info deferred (DailyMed covers it). |
| Writes to | `documents` only (concepts already exist from MeSH) |
| Chunking | Topic-section level — Summary, Symptoms, Causes, Tests, Treatments, Prevention, Living With |

**Field mapping:**

```
audience          = 'patient'
source            = 'MedlinePlus'
source_authority  = 'consumer_health'
readability_grade = computed via textstat (MedlinePlus targets grade 6–8)
valid_from/to     = NULL — MedlinePlus updates in place
version_label     = NULL
metadata.mesh_ids = cross-reference to MeSH concepts from Phase 1
```

**Temporal gotcha:** MedlinePlus updates in place without version history. We cannot reconstruct "what MedlinePlus said about X in 2019". The temporal query API (`as_of_date`) does not apply to MedlinePlus records; queries return current state with a flag `temporal_unavailable: true`. Documented limitation, not a bug.

### 5.4 Style Rules seed — DHG + AMA + PLAIN

| Source | Records | Notes |
|--------|---------|-------|
| `DHG_BANNED_PATTERNS` | 27 | Lifted verbatim from `prose_quality_agent.py` lines 39–67. Same regexes, same rule names. `severity='avoid'`, `rule_category='banned_phrase'`, `audience_scope=['clinician','patient']`. |
| AMA Manual of Style (essentials) | ~15 | Hand-authored summaries with citations to source chapters — fair-use internal reference. `rule_category='ama_style'`, `severity='should'`. |
| PLAIN (Plain Language Action Network) | ~5 | Hand-authored essentials for patient register. `rule_category='readability'`, `severity='must'`, `audience_scope=['patient']`. |
| **Total Phase 4 seed** | **~47 records** | Embedded via nomic-embed-text. Loaded via migration script `scripts/seed_style_rules.py`. |

**Critical design property:** after Phase 4 lands, the DHG banned-patterns list lives in exactly one place — the database. `prose_quality_agent.py` gets updated to query `medkb.style_rules` at node startup rather than hardcoding the 27 patterns. See §10.

### 5.5 Style Exemplars anchor — CDC Patient Handouts

| Property | Value |
|----------|-------|
| Source | CDC patient fact sheets across major conditions |
| Access | Direct HTTPS download from `https://www.cdc.gov` topic pages |
| License | Public domain (US federal work) — verified per page |
| Volume (Phase 4 anchor) | 20 hand-curated pieces covering: diabetes, hypertension, COPD, A1C education, cancer screening (colorectal/breast/lung), vaccination, heart attack warning signs, stroke FAST, hand hygiene, foodborne illness, antibiotic stewardship, tobacco cessation, mental health, chronic pain, kidney disease, asthma, sleep, nutrition, physical activity, healthy aging |
| Chunks after ingestion | ~300–500 |
| Writes to | `style_exemplars` only |

**Field mapping:**

```
source            = 'CDC'
source_url        = exact https://www.cdc.gov/... URL
license           = 'public_domain'
audience_tag      = 'patient'
register_tag      = 'explanatory' for conditions, 'instructional' for "what to do" pieces
topic_tags        = ['diabetes','A1C','screening',...] hand-tagged at ingestion
readability_grade = computed
```

**Why 20 and not 200:** Phase 4 anchor proves the mechanism. If the drafting LLM produces patient-register prose when given CDC exemplars as few-shot anchors AND `prose_quality_agent` validates the output cleanly, the mechanism works and Phase 5 can fan out to PLOS, eLife, NIH News in Health, etc. If the mechanism fails or needs tuning, we learn that with 20 pieces and 5 test queries, not 2,000 pieces and regret.

### 5.6 Phase 4 anchor source summary

| Source | Pillar | Table | Records (Phase 4) | Access method |
|--------|--------|-------|-------------------|---------------|
| USPSTF | Guidelines | `documents` | ~120 | JSON API |
| DailyMed | FDA labels | `documents` + `relationships` | ~200 drugs, ~2K chunks | REST API + bulk |
| MedlinePlus EN | Consumer health | `documents` | ~1,000 topics, ~6K chunks | Web Service API + XML bulk |
| DHG + AMA + PLAIN | Style rules | `style_rules` | ~47 | Migration script |
| CDC handouts | Style exemplars | `style_exemplars` | 20 pieces, ~400 chunks | Direct HTTPS |

**Total new chunks at end of Phase 4:** ~8,500 across `documents`, `style_rules`, `style_exemplars`. All embedded via nomic-embed-text (or PubMedBERT if that migration has happened by Phase 4 time — see §8).

---

## 6. Phase 5 Ingestion — Fan-Out Sources

No new architecture. Phase 5 adds content through the proven Phase 4 pattern — same tables, same ingestor base class, same API. Every new source is a `SourceIngestor` subclass.

### 6.1 Pillar IV expansion — Clinical Guidelines

| # | Source | License | Access | Est. records | Notes |
|---|--------|---------|--------|--------------|-------|
| 1 | AHA/ACC | Journal article (CC-BY when OA) | PubMed / PMC full-text XML | ~50 active | CV prevention, HF, HTN, lipids. PMC only if OA. |
| 2 | IDSA | Journal article (OA variable) | PubMed / PMC | ~40 active | Infectious disease. OA-only. |
| 3 | Cochrane Systematic Reviews | Abstract public; full review paywalled | PubMed E-utilities (abstracts + GRADE ratings only) | ~9,000 active | Phase 5 = abstracts only. Full-text requires institutional license — separate workstream. |
| 4 | AHRQ Evidence Reports | Public domain (federal) | Bulk from `https://effectivehealthcare.ahrq.gov/` | ~300 reports | Full text, directly ingestible |
| 5 | CDC Community Preventive Services | Public domain | Direct HTTPS / XML | ~250 recommendations | Pairs with USPSTF |
| 6 | WHO Guidelines | Mixed PD / CC-BY | IRIS repository bulk download | ~400 active | License verified per-document at ingest; reject anything not explicitly PD or CC-BY |

Field mapping identical to USPSTF Phase 4 pattern — `audience='clinician'`, `source_authority='guideline_body'`, `valid_from`/`valid_to`, `supersedes` edges when newer versions arrive.

**Deliberate exclusions for Phase 5 (flagged so they don't drift in later):**

- **NCCN** — copyrighted oncology guidelines; free clinician registration grants viewing only, not redistribution. Declined for Phase 5; revisit in Phase 6 only with paid license.
- **NICE (UK)** — free to read, restrictive redistribution. Same treatment. Declined for Phase 5.
- **Paywalled Cochrane full text** — abstracts only. Full text requires institutional license negotiation.

### 6.2 Pillar IV expansion — FDA data

| # | Source | License | Access | Scope |
|---|--------|---------|--------|-------|
| 1 | DailyMed full corpus | Public domain | Bulk SPL zip archives | ~120,000 drug labels. Fan-out of the 200-drug anchor. |
| 2 | openFDA Adverse Events (FAERS) | Public domain | REST `https://api.fda.gov/drug/event.json` | Stored as drug-level summaries: top 20 most-reported events per drug, updated quarterly. NOT per-event. |
| 3 | FDA Drug Approvals | Public domain | REST `https://api.fda.gov/drug/drugsfda.json` | Approval dates, indications, NDAs. Populates `valid_from` for DailyMed records where label history is incomplete. |

**Why FAERS is summarized:** FAERS ships millions of individual events. Storing per-event explodes the HNSW index and gives zero retrieval value — agents want patterns, not individual reports. Summarization at ingest produces what agents actually want in ~200 words per drug.

### 6.3 Pillar V expansion — Consumer Health

| # | Source | License | Access | Scope |
|---|--------|---------|--------|-------|
| 1 | MedlinePlus Spanish | Public domain | Same XML bulk | ~1,000 topics, Spanish register |
| 2 | NIH Institute patient content | Public domain (federal) | Direct HTTPS per institute | NHLBI, NIDDK, NCI, NIMH, NINDS, NIA, NIAID, NIAMS. ~100–300 pages each. |
| 3 | CDC full topic pages | Public domain | Direct HTTPS | Fan-out from 20 anchor handouts to ~1,500 topics |
| 4 | AHRQ patient materials | Public domain | Bulk download | ~400 patient decision aids |
| 5 | FDA Consumer Updates | Public domain | REST API | ~2,000 plain-language articles |

**Language handling:** Spanish MedlinePlus records get `metadata.language='es'`; English defaults to `metadata.language='en'`. API accepts a `language` filter. No separate table.

### 6.4 Pillar V expansion — Style Exemplars

| # | Source | License | Est. pieces | Register |
|---|--------|---------|-------------|----------|
| 1 | CDC full handout corpus | Public domain | ~500 | explanatory + instructional |
| 2 | NIH News in Health | Public domain | ~400 articles | narrative + explanatory |
| 3 | PLOS Medicine Essays | CC-BY | ~600 essays | authoritative + narrative |
| 4 | eLife Features & Essays | CC-BY | ~300 pieces | authoritative + narrative |
| 5 | NLM Profiles in Science essays | Public domain | ~200 historical pieces | narrative |
| 6 | NIH Record newsletter archive | Public domain | ~300 articles | narrative + explanatory |
| 7 | PMC narrative medicine tagged articles | CC-BY subset only | ~500 filtered by PMC license | narrative |

**Register balance after Phase 5:**

| Register | Phase 4 anchor | Phase 5 total |
|----------|----------------|---------------|
| explanatory | ~250 chunks (CDC) | ~15,000 chunks |
| instructional | ~150 chunks (CDC) | ~8,000 chunks |
| authoritative | 0 | ~12,000 chunks (PLOS Med, eLife) |
| narrative | 0 | ~10,000 chunks (NIH News, Profiles, narrative medicine) |

The 4-register breakdown lets agents retrieve exemplars matching the specific output they need — authoritative for clinical rationale, narrative for cold opens, explanatory for gap descriptions, instructional for patient counseling.

### 6.5 Phase 5 sub-phase sequencing (internal order)

Phase 5 does not ship as one release. Sub-phases run in order; each sub-phase gates on the previous sub-phase's exit criteria.

1. **5a — Full DailyMed fan-out** (120K labels). Highest volume, proven parser, biggest payoff.
2. **5b — MedlinePlus Spanish + CDC full topic pages**. Proven parsers, straightforward fan-out.
3. **5c — PLOS Medicine + eLife exemplars**. Adds authoritative register (biggest Phase 4 gap). Requires CC-BY verification per article.
4. **5d — AHA/ACC + IDSA + Cochrane abstracts**. Clinical guidelines fan-out with OA filtering.
5. **5e — Long tail** — AHRQ, CDC CPSTF, WHO, NIH institutes, openFDA, NIH News, FDA Consumer, NLM Profiles, NIH Record, PMC narrative.

### 6.6 Phase 5 source summary

| Pillar | Phase 4 anchors | Phase 5 additions | Phase 5 new chunks (est.) |
|--------|-----------------|-------------------|---------------------------|
| Clinical guidelines | USPSTF (~120) | AHA/ACC, IDSA, Cochrane abstracts, AHRQ, CDC CPSTF, WHO | ~35,000 |
| FDA data | DailyMed 200 drugs (~2K) | Full DailyMed ~120K, openFDA summaries, FDA approvals | ~600,000 |
| Consumer health | MedlinePlus EN (~6K) | MedlinePlus ES, NIH institutes, CDC full, AHRQ patient, FDA Consumer | ~40,000 |
| Style exemplars | CDC 20 pieces (~400) | CDC full, NIH News, PLOS Med, eLife, NLM Profiles, NIH Record, PMC narrative | ~50,000 |
| Style rules | DHG + AMA + PLAIN (~47) | No new rules — stabilizes in Phase 4 | 0 |
| **Grand total at end of Phase 5** | — | — | **~725,000 new chunks** |

---

## 7. Ingestor Architecture

Every ingestor — Phase 1 through Phase 5 — is a `SourceIngestor` subclass. The base class handles common concerns (chunking, embedding, upserts, reconciliation, error logging); subclasses stay small (~100–300 lines each).

### 7.1 Base class

```python
# services/medkb-ingestors/base.py
class SourceIngestor(ABC):
    source_name: str                    # 'MESH' | 'RXNORM' | 'USPSTF' | 'DailyMed' | ...
    source_authority: Literal[...] | None  # 'guideline_body' | 'regulatory' | ... | None for concepts
    default_audience: Literal[...] | None
    writes_to: Literal["concepts", "documents", "style_exemplars", "relationships"]

    @abstractmethod
    async def discover(self) -> AsyncIterator[SourceItem]:
        """Yield metadata records for each item to ingest."""

    @abstractmethod
    async def fetch(self, item: SourceItem) -> RawRecord:
        """Download and parse a single item."""

    @abstractmethod
    def chunk(self, raw: RawRecord) -> list[Chunk]:
        """Split a raw record into chunks appropriate for this source."""

    async def run(self, mode: Literal["incremental","full","backfill"]) -> IngestReport:
        """Template method — do not override. Drives discover/fetch/chunk/embed/upsert."""
```

The `run()` template handles:

1. Open an `ingest_reports` row (`started_at`, `source_name`, `mode`)
2. Iterate `discover()` → for each `SourceItem`:
   a. Skip if `mode='incremental'` and already present (idempotency check)
   b. `fetch()` → `chunk()` → embed chunks via `embedding_client.embed(...)`
   c. Derive fields: `readability_grade` via `textstat`, `audience` from class default or heuristic, `source_authority` from class constant
   d. Reconcile concepts (look up MeSH/RxCUI; log unmapped to `{source}_unmapped.log`)
   e. Detect supersession (query for existing same-topic records; write `valid_to` + `supersedes` edge)
   f. Upsert to target table via idempotent `ON CONFLICT` on `(source, source_id)` / `(source, source_id, chunk_index)`
   g. Emit Prometheus counters
3. Close the `ingest_reports` row (`ended_at`, counts, `error_summary`)

### 7.2 Concept reconciliation rules

| Source | Lookup key | Target concept table | Unmapped behavior |
|--------|-----------|----------------------|-------------------|
| USPSTF | topic slug → MeSH (heuristic string match) | `concepts WHERE source='MESH'` | Log to `uspstf_unmapped.log`, ingest anyway |
| DailyMed | `rxcui` from SPL XML | `concepts WHERE source='RXNORM'` | Log to `dailymed_unmapped.log`, ingest anyway |
| MedlinePlus | `mesh_id` from XML | `concepts WHERE source='MESH'` | Log to `medlineplus_unmapped.log`, ingest anyway |
| CDC handouts | Manual `topic_tags` (hand-curated) | N/A (exemplars don't link to concepts) | No log |
| PubMed | MeSH terms from MedlineCitation | `concepts WHERE source='MESH'` | Log, ingest anyway |
| PMC OA | MeSH terms from JATS XML | `concepts WHERE source='MESH'` | Log, ingest anyway |

**Rule:** never create orphan concepts at ingest time. If a source mentions a concept we don't already have, the document/chunk is still ingested and the missing concept is logged for human review. This prevents ingestors from polluting the concept table.

### 7.3 Per-source subclass pattern

Example — USPSTF ingestor in full:

```python
# services/medkb-ingestors/sources/uspstf.py
class USPSTFIngestor(SourceIngestor):
    source_name = "USPSTF"
    source_authority = "guideline_body"
    default_audience = "clinician"
    writes_to = "documents"
    BASE_URL = "https://www.uspreventiveservicestaskforce.org"

    async def discover(self) -> AsyncIterator[SourceItem]:
        topics = await self._fetch_topic_list()
        for topic in topics:
            yield SourceItem(
                source_id=topic["id"],
                url=topic["url"],
                version=topic.get("version_label"),
                metadata={"topic": topic["slug"], "uspstf_grade": topic["grade"]},
            )

    async def fetch(self, item: SourceItem) -> RawRecord:
        json = await self._get_json(item.url)
        return RawRecord(
            title=json["title"],
            sections={
                "recommendation": json["recommendation_text"],
                "rationale": json["rationale_text"],
                "clinical_considerations": json["clinical_considerations"],
                "supporting_evidence": json["evidence_summary"],
            },
            valid_from=json["publication_date"],
            version_label=json.get("version_label"),
            metadata={**item.metadata},
        )

    def chunk(self, raw: RawRecord) -> list[Chunk]:
        return [
            Chunk(text=text, index=i, section=name)
            for i, (name, text) in enumerate(raw.sections.items())
            if text and text.strip()
        ]
```

All embedding, concept reconciliation, supersession detection, and upsert logic happens in the base class. The subclass is ~50 lines and covers only source-specific discover/fetch/chunk.

### 7.4 Error handling and observability

Every ingestor run produces a structured `ingest_reports` row and emits Prometheus counters:

```
medkb_ingest_items_total{source="...", outcome="ingested"}
medkb_ingest_items_total{source="...", outcome="skipped_existing"}
medkb_ingest_items_total{source="...", outcome="unmapped_concept"}
medkb_ingest_items_total{source="...", outcome="error_fetch"}
medkb_ingest_items_total{source="...", outcome="error_chunk"}
medkb_ingest_duration_seconds{source="..."}    histogram
```

Grafana dashboard panel per source: items/sec, error rate, cumulative chunks, last-run timestamp. Alertmanager rule fires if error rate > 5% on any source for > 15 minutes.

### 7.5 Scheduling

Each ingestor runs as a separate Docker container with its own internal scheduler. Shared base image `dhg-medkb-ingestor` differs only by `INGESTOR_CLASS` env var.

| Source | Cadence | Rationale |
|--------|---------|-----------|
| MeSH | Monthly | NLM monthly release |
| RxNorm | Monthly | NLM monthly release |
| PrimeKG | Annual | Harvard annual release |
| PubMed | Daily (delta) | NCBI daily updates |
| PMC OA | Weekly | Fast enough for Phase 1 |
| USPSTF | Weekly | Low update frequency |
| DailyMed | Daily (delta) | FDA rolling updates |
| MedlinePlus | Weekly | Updated in place, polling cheap |
| CDC handouts (anchor) | Monthly | Low update frequency |
| Style rules (seed) | One-time + on-demand | Not recurring |
| Style exemplars (CDC + Phase 5) | Monthly (curation review) | Human-gated additions |

### 7.6 Incremental vs full re-ingest

CLI flags on each ingestor:

```
python -m medkb_ingestors.run --source=USPSTF --mode=incremental
python -m medkb_ingestors.run --source=USPSTF --mode=full
```

- **Incremental** (default) — only fetch items whose `(source, source_id)` is absent or whose `version_label` differs.
- **Full** — re-fetch everything. Used after a parser fix. The idempotent upsert handles duplicate detection at the DB layer.

### 7.7 What's NOT in the ingestor layer

- **No streaming ingestion.** Batch polling only. No real-time requirement.
- **No distributed coordination.** One container per source. If a source needs parallelism (full DailyMed 120K fan-out), the `run()` template can dispatch work to an internal `asyncio.Queue` with N workers — still one container.
- **No Airflow/Prefect.** Docker compose + internal scheduler. Revisit only if ingestor count exceeds ~20.

---

## 8. Embedding Pipeline

### 8.1 Phase 1 embedding model: nomic-embed-text

**Decision:** use `nomic-embed-text` from the existing `dhg-ollama` container for Phase 1. Zero new infrastructure. PubMedBERT deferred pending measured Phase 1 retrieval quality.

**Why nomic-embed-text:**

- Already running in `dhg-ollama` on port 11434 — no new container
- Produces 768-dimensional vectors — identical to PubMedBERT, so migrating later is a re-embed, not a schema change
- Open weights, Apache-2.0 license
- Benchmarked strong on general-purpose retrieval; exact biomedical performance unknown until measured
- Ollama's HTTP API is trivially callable from the ingestors and the `dhg-medkb-api` service

**Embedding service client:**

```python
# services/medkb-api/src/embedding_client.py
class OllamaEmbeddingClient:
    MODEL = "nomic-embed-text"
    OLLAMA_URL = "http://dhg-ollama:11434/api/embeddings"

    async def embed(self, text: str) -> list[float]:
        resp = await httpx.AsyncClient().post(
            self.OLLAMA_URL,
            json={"model": self.MODEL, "prompt": text},
            timeout=30.0,
        )
        resp.raise_for_status()
        vec = resp.json()["embedding"]
        assert len(vec) == 768, f"unexpected dim {len(vec)}"
        return vec

    async def embed_batch(self, texts: list[str], batch_size: int = 16) -> list[list[float]]:
        """Ollama doesn't support true batching — fan out N parallel requests."""
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            results.extend(await asyncio.gather(*[self.embed(t) for t in batch]))
        return results
```

### 8.2 Query-side embedding

The `dhg-medkb-api` service embeds user queries on each request. This is not cached because query text varies too much for caching to be worthwhile at Phase 1 scale. Single-call latency budget: < 30ms p95 to Ollama on loopback, measured during smoke tests.

If query embedding becomes a bottleneck, a simple in-process LRU cache keyed on the raw query string can be added without API changes. [UNCERTAIN — RESOLVE AT REVIEW: worth pre-building the LRU cache in Phase 1 or waiting until measurement proves a need? My recommendation: wait for measurement.]

### 8.3 Ingestor-side embedding

Ingestors embed chunks in batches of 16 via `embed_batch`. Bulk ingestion (MeSH full rebuild, PMC OA weekly pull) processes ~10K chunks before committing to DB to amortize transaction overhead. Embedding parallelism is bounded by Ollama's concurrency — Phase 1 measurement determines whether we cap at 4, 8, or 16 parallel requests.

### 8.4 PubMedBERT migration (deferred, mechanism here)

When Phase 1 measurement shows nomic-embed-text retrieval quality is insufficient on the biomedical golden test set, the migration to PubMedBERT is:

1. Stand up `dhg-pubmedbert` service (new container serving the `NeuML/pubmedbert-base-embeddings` model via FastAPI + sentence-transformers)
2. Add `EMBEDDING_MODEL=pubmedbert` env var to API and ingestor containers
3. Run `scripts/reembed_all.py` — iterates every row with an embedding and re-computes it via the new service. Idempotent, chunked, resumable.
4. Verify the golden test set retrieval quality with new embeddings
5. Decommission the old model

The column type (`vector(768)`) doesn't change. The HNSW indexes will need a rebuild because the distance distribution shifts — that's a one-time operation run with `CREATE INDEX CONCURRENTLY` so the API stays responsive.

**This is a known-and-planned migration path, not a risk.** Phase 1 doesn't need PubMedBERT — it needs a retrieval quality measurement that tells us whether we need PubMedBERT. If nomic-embed-text hits the quality bar on the golden set, the migration never happens.

### 8.5 Golden test set

Phase 1 exit gate requires a golden test set of ~50 biomedical retrieval queries with expected top-5 results. The set is authored by Stephen (or a domain expert) and committed to `services/medkb-api/test/golden_set.json`. Retrieval quality metric: Recall@5 ≥ 0.80 for nomic-embed-text on the golden set. If it falls below, we flip to PubMedBERT before declaring Phase 1 complete. [UNCERTAIN — RESOLVE AT REVIEW: does Stephen author the golden set personally, or is this a task that can be delegated to a research subagent under Stephen's review? Either works for the spec; the plan file needs to commit.]

### 8.6 Embedding dimension lock-in

All tables use `vector(768)` permanently. The HNSW index parameters (`m=16, ef_construction=64`) are also fixed at Phase 1. Changing either requires re-embedding and index rebuild. Both decisions are made once, here, and not revisited unless measurement forces a change.

---

## 9. API Surface

All routes under `/v1/`. Auth: API-key header inherited from the registry's existing pattern. FastAPI auto-generates OpenAPI at `/v1/docs`.

### 9.1 Phase 1 endpoints (foundation)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/search/semantic` | General semantic search across all `documents` |
| POST | `/v1/search/literature` | PubMed/PMC specific search with literature filters |
| GET | `/v1/concept/{source}/{source_id}` | Look up a concept by its source-specific identifier |
| GET | `/v1/graph/neighbors/{concept_id}` | Get directly-connected concepts via `relationships` |

#### POST `/v1/search/semantic` (Phase 1)

Request:
```json
{
  "query": "metformin cardiovascular outcomes",
  "limit": 10,
  "sources": null,
  "year_range": null
}
```

Response:
```json
{
  "results": [
    {
      "document_id": "uuid",
      "source": "PUBMED",
      "title": "Metformin and cardiovascular outcomes in type 2 diabetes",
      "chunk_text": "...",
      "similarity_score": 0.89,
      "pmid": "12345678",
      "doi": "10.xxxx/yyyy",
      "publication_date": "2023-06-15",
      "authors": ["Smith J", "Jones K"],
      "metadata": { "publication_type": ["Randomized Controlled Trial"], "journal": "NEJM" }
    }
  ],
  "total_matches": 142,
  "query_time_ms": 34
}
```

Phase 4 extends this endpoint with additional parameters — see §9.3.

#### POST `/v1/search/literature` (Phase 1)

Literature-specific wrapper over `/v1/search/semantic` with filters pre-configured for PubMed/PMC retrieval:

Request:
```json
{
  "query": "SGLT2 inhibitor heart failure",
  "limit": 10,
  "year_range": [2020, 2026],
  "publication_types": ["Randomized Controlled Trial", "Meta-Analysis"],
  "journals": null,
  "mesh_terms": ["Heart Failure"]
}
```

Response: same shape as `/v1/search/semantic` plus matched MeSH terms in each result.

#### GET `/v1/concept/{source}/{source_id}` (Phase 1)

Example: `GET /v1/concept/MESH/D006973`

Response:
```json
{
  "id": "uuid",
  "source": "MESH",
  "source_id": "D006973",
  "name": "Hypertension",
  "definition": "Persistently high systemic arterial blood pressure...",
  "synonyms": ["High Blood Pressure", "HTN", ...],
  "metadata": { "tree_numbers": ["C14.907.489"], "semantic_types": ["Disease or Syndrome"] },
  "related_documents": {
    "counts_by_audience": { "clinician": 14, "patient": 3 },
    "counts_by_authority": { "peer_reviewed": 14, "consumer_health": 3 }
  }
}
```

The `related_documents` summary is populated from Phase 4 onward (Phase 1 returns only `counts_by_audience.clinician` from PubMed). Phase 1 agents see this as informational; Phase 4 agents use it to decide whether to query by audience.

#### GET `/v1/graph/neighbors/{concept_id}` (Phase 1)

Request: `GET /v1/graph/neighbors/{uuid}?rel_types=has_ingredient,brand_of&limit=20`

Response:
```json
{
  "concept": { "...full concept record..." },
  "neighbors": [
    {
      "concept": { "...neighbor concept..." },
      "rel_type": "has_ingredient",
      "direction": "outgoing",
      "provenance": "RXNORM",
      "evidence": null
    }
  ]
}
```

Default: returns all `rel_type` values except `supersedes` (internal mechanism, excluded unless explicitly requested).

### 9.2 Phase 4 endpoints (on top of Phase 1)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/search/guidelines` | Search clinical guidelines + regulatory docs, temporal-aware |
| POST | `/v1/search/patient` | Patient-register semantic search (wrapper with `audience='patient'`) |
| POST | `/v1/search/rules` | Query style rules by category, severity, audience |
| POST | `/v1/search/exemplars` | Query style exemplars by audience, register, topic |
| GET | `/v1/cite/{document_id}` | AMA citation + structured citation fields for one document |
| POST | `/v1/cite/bulk` | Same, for up to 50 document IDs in one call |
| GET | `/v1/drug/{rxcui}/safety` | All `safety_critical` chunks for a drug |
| GET | `/v1/history/{document_id}` | Temporal history via `supersedes` chain |

Endpoint contracts for these are identical to the content previously detailed — consolidating below to avoid duplication.

#### POST `/v1/search/guidelines` (Phase 4)

Dedicated endpoint with pre-set defaults: `current_only=true`, `source_authority IN ('guideline_body','regulatory')`, `with_citations=true`. Agents get one-line calls instead of composing filters.

#### POST `/v1/search/rules` (Phase 4)

Returns style rule records by category + audience_scope + severity. Used by drafting LLMs to fold rules into system prompts before writing. See §10.

#### POST `/v1/search/exemplars` (Phase 4)

Returns style exemplar chunks by audience_tag + register_tag + topic_tags. Used by drafting LLMs for few-shot voice anchoring. See §10.

#### GET `/v1/cite/{document_id}` (Phase 4)

Returns AMA-formatted citation + structured fields. `citation_type` inferred from `source_authority`:

| `source_authority` | `citation_type` | AMA template |
|--------------------|-----------------|--------------|
| `peer_reviewed` | `journal` | Authors. Title. Journal. Year;Volume(Issue):Pages. doi:XXX. PMID: XXX. |
| `guideline_body` | `guideline` | Authoring Body. Title. Year. URL. Accessed date. |
| `regulatory` | `label` | Manufacturer. Drug Name (Brand) [prescribing information]. Place: Manufacturer; Year. URL. |
| `consumer_health` | `consumer` | Authoring Body. Title. Site. Year. URL. Accessed date. |
| `preprint` | `preprint` | Authors. Title [preprint]. Server. Year. doi:XXX. |
| `tertiary_reference` | `reference` | Authoring Body. Title. Year. URL. |

**Why AMA only:** CME grants use AMA. Variance in citation format is itself a quality signal to reviewers. One format done correctly; APA/Vancouver/MLA deferred until a concrete use case requires them.

#### GET `/v1/drug/{rxcui}/safety` (Phase 4)

Returns all chunks with `metadata.rxcui=X AND metadata.safety_critical=true`. Sorted by severity (boxed warnings first). Dedicated endpoint ensures agents cannot accidentally miss a boxed warning by query wording.

#### GET `/v1/history/{document_id}` (Phase 4)

Returns the record + all predecessors via `supersedes` chain. Used by grant writers to cite both current and prior guideline versions for practice-gap arguments.

### 9.3 Shared parameters (Phase 1 endpoints at Phase 4 time)

Phase 4 extends every Phase 1 search endpoint with these optional parameters. Each has a safe default preserving Phase 1 behavior.

| Parameter | Type | Default | Effect |
|-----------|------|---------|--------|
| `audience` | `str \| str[]` | null | Filter by audience (null = any, including null) |
| `min_evidence_level` | `str` | null | Filter by Oxford CEBM level ≥ this |
| `source_authority` | `str[]` | null | Filter by authority tier |
| `as_of_date` | `date` | null | Temporal query: `valid_from <= X AND (valid_to IS NULL OR valid_to > X)` |
| `current_only` | `bool` | true | Filter `valid_to IS NULL` |
| `readability_max` | `number` | null | Filter `readability_grade ≤ X` |
| `with_citations` | `bool` | false | Inline citation objects in each result |
| `with_safety` | `bool` | true for drug queries, false otherwise | Controls safety-critical prepending (§9.5) |

**Filter precedence:** AND combination. Backward compatible: a Phase 1 request (no new params) returns Phase 1 shape.

### 9.4 Citation formatting (Phase 4, no new table)

Citation construction happens at query time from existing columns via a pure function `api/citations.py::format_ama(doc: Document) -> CitationBlock`. Deterministic, testable, no persistence. See §9.2 template table.

### 9.5 Safety-critical prepending (Phase 4, default-on for drug queries)

When any search endpoint retrieves chunks linked to a drug concept (RxNorm source), and `with_safety != false`, the API automatically prepends a `safety_context` object to the response:

```json
{
  "results": [ "..." ],
  "safety_context": {
    "applies_to_rxcui": "6809",
    "drug_name": "metformin",
    "warnings": [
      {
        "warning_level": "boxed_warning",
        "text": "Postmarketing cases of metformin-associated lactic acidosis...",
        "source_document_id": "uuid",
        "citation": { "...AMA-formatted..." }
      }
    ]
  }
}
```

**Detection logic:**

1. Resolve the query's top-3 matched concepts
2. If any has `source='RXNORM'`, look up its RxCUI
3. Query `documents WHERE metadata.rxcui = <X> AND metadata.safety_critical = true`
4. Include top-severity warnings in `safety_context`

**Why default-on:** safety warnings missed are safety warnings violated. The correct asymmetry for a medical product is: safe default, explicit opt-out for the unsafe path. Cost is ~10ms; payoff is structural.

### 9.6 Error handling

Standard FastAPI responses:

| Code | Scenario |
|------|----------|
| 400 | Invalid `audience`, invalid `evidence_level_oxford`, `as_of_date` in future, `as_of_date` + `current_only=true` contradictory |
| 404 | Document / concept ID not found |
| 422 | Validation error (FastAPI Pydantic default) |
| 503 | Database or embedding service unavailable |

All errors return structured JSON with `error_code`, `message`, optional `hint`. No raw stack traces.

### 9.7 What the API does NOT do

- No `/v1/search/multi-register` — composable at agent layer
- No streaming responses — batched only
- No HTTP caching headers — caching at agent layer
- No auth changes — same API-key pattern
- No rate limiting enforcement in Phase 1 — document intended 60 req/s/key, implement in Phase 4+
- No admin mutation endpoints — writes go through ingestors

---

## 10. Writing Layer Mechanics (Phase 4)

The writing layer is how style rules and exemplars actually flow into DHG agent prompts at inference time. This is the Phase 4 integration point where MedKB meets the existing DHG LangGraph agents.

### 10.1 Before-and-after enforcement pattern

Editorial policy gets enforced at **two** points in the agent lifecycle:

| Point | Agent | Mechanism | What it sees |
|-------|-------|-----------|--------------|
| **Before drafting** | All drafting agents | Retrieval from `style_rules` + `style_exemplars`, folded into system prompt | Top-k rules (`severity='must'` + `severity='should'`) + 2–3 matching exemplars |
| **After drafting** | `prose_quality_agent` | Query `style_rules` for `rule_category='banned_phrase'`, apply `pattern` regex to draft | All active banned-phrase rules with compiled regex |

Same rules, two enforcement points.

### 10.2 Prompt assembly flow (before-drafting)

Pseudo-code for a drafting LangGraph node:

```python
async def draft_cold_open(state: NeedsAssessmentState) -> dict:
    topic = state["topic"]
    audience = state.get("target_audience", "clinician")

    rules_resp = await medkb_client.post("/v1/search/rules", json={
        "query": f"cold open narrative {topic}",
        "audience_scope": [audience],
        "severity": ["must", "should"],
        "limit": 10,
    })

    exemplars_resp = await medkb_client.post("/v1/search/exemplars", json={
        "query": f"patient vignette {topic}",
        "audience_tag": audience,
        "register_tag": "narrative",
        "limit": 3,
    })

    system_prompt = build_needs_cold_open_prompt(
        topic=topic,
        rules=rules_resp["results"],
        exemplars=exemplars_resp["results"],
    )
    draft = await llm.ainvoke(system_prompt)
    return {"cold_open_draft": draft.content}
```

Prompt template structure:

```
You are drafting the cold-open narrative for a CME grant application on {topic}.

[EDITORIAL RULES — follow these strictly]
Must never:
  - {rule.rule_text}  (source: {rule.source})
Should avoid:
  - {rule.rule_text}  (source: {rule.source})

[VOICE EXEMPLARS — write in this register]
Example 1 ({exemplar.source}, {exemplar.register_tag}):
> {exemplar.chunk_text}

[TASK]
Write a 150–200 word cold open that opens with a patient vignette...
```

### 10.3 `prose_quality_agent` modification

Current state: `BANNED_PATTERNS` is a hardcoded Python list of 27 regex/description pairs.

Phase 4 change: replace with a startup query to `medkb.style_rules`.

```python
_BANNED_PATTERNS_CACHE: list[CompiledRule] | None = None
_CACHE_TIMESTAMP: float = 0.0
_CACHE_TTL_SECONDS = 300  # 5 minutes

async def get_banned_patterns() -> list[CompiledRule]:
    global _BANNED_PATTERNS_CACHE, _CACHE_TIMESTAMP
    now = time.monotonic()
    if _BANNED_PATTERNS_CACHE is not None and (now - _CACHE_TIMESTAMP) < _CACHE_TTL_SECONDS:
        return _BANNED_PATTERNS_CACHE

    resp = await medkb_client.post("/v1/search/rules", json={
        "query": "",
        "category": ["banned_phrase"],
        "limit": 500,
    })
    _BANNED_PATTERNS_CACHE = [
        CompiledRule(
            name=r["rule_name"],
            pattern=re.compile(r["pattern"], re.IGNORECASE) if r["pattern"] else None,
            severity=r["severity"],
            source=r["source"],
            rule_text=r["rule_text"],
        )
        for r in resp["results"]
        if r.get("pattern")
    ]
    _CACHE_TIMESTAMP = now
    return _BANNED_PATTERNS_CACHE
```

**Properties:**

- **5-minute TTL cache** — new rules propagate within 5 minutes without agent restart
- **Regex-only filter** — after-pass only applies rules with a compiled `pattern`
- **Graceful fallback** — if MedKB query fails, fall back to a locally-committed `prose_quality_agent/fallback_rules.json` snapshot and log a WARNING. Loud Grafana alert on the fallback path firing. (This is the resolution of the UNCERTAIN item from the _v1 spec: graceful fallback with loud alert, not hard fail.)

### 10.4 Per-agent retrieval defaults

| Agent | Rules retrieved | Exemplars retrieved | Notes |
|-------|-----------------|---------------------|-------|
| `needs_assessment` | Top 10 (`must`+`should`), `audience_scope` matches state | 3 narrative (cold open) + 2 explanatory (gap) | Highest-stakes prose |
| `research` | Top 8 including `citation_format` | 2 authoritative | Citation-heavy |
| `clinical_practice` | Top 8 | 2 explanatory | Neutral authoritative voice |
| `gap_analysis` | Top 8 | 2 explanatory | AMA number rules matter |
| `learning_objectives` | Top 5 focused on `structure` | 0 | LOs are structural, not stylistic |
| `curriculum_design` | Top 8 | 2 instructional | Educational design voice |
| `grant_writer` | Top 15 (broadest) | 3 matching target audience | Final assembly |

Defaults, not hardcoded constants. Each agent's retrieval parameters live in its own config (`needs_assessment_config.py` etc.).

### 10.5 Token budget impact

| Component | Tokens per drafting call |
|-----------|-------------------------|
| Rule block (10 × ~30) | ~300 |
| Exemplar block (3 × ~400) | ~1,200 |
| Overhead (headers, instructions) | ~200 |
| **Total writing-layer overhead** | **~1,700 tokens** |

Claude Sonnet easily absorbs this. At ~85 drafting nodes per full grant pipeline, total cost add: `85 × 1,700 / 1000 × $0.003 ≈ $0.43` per grant run. Noise against Stephen's $600/hr rate.

### 10.6 Rollout order

Do NOT parallelize. Each step gates on A/B eval passing.

1. **`prose_quality_agent`** gets the query-`style_rules`-at-startup change first, with fallback to hardcoded patterns on MedKB zero-results. Safest change.
2. **Seed `medkb.style_rules`** with 47 Phase 4 rules, verify `prose_quality_agent` queries them correctly, then **remove** the hardcoded `BANNED_PATTERNS` list in a separate commit (revertable in isolation).
3. **`needs_assessment_agent`** gets before-drafting retrieval next. Highest-stakes prose surfaces issues fastest.
4. **Iterate on retrieval quality** using `needs_assessment` as test bed. Tune `limit`, prompt assembly, exemplar selection. Do NOT touch other agents.
5. **`grant_writer_agent`** gets before-drafting retrieval next. Broadest rule coverage.
6. **Remaining agents** (`research`, `clinical_practice`, `gap_analysis`, `learning_objectives`, `curriculum_design`) in a single batch once tuning is stable.

Each step includes a side-by-side A/B eval (§12.6): same 3 reference topics through the agent with and without writing-layer retrieval, compared by `prose_quality_agent` scoring. Only proceed when treatment scores equal-or-better than baseline.

---

## 11. Migration & Rollout

### 11.1 Phase 1 initial build sequence

Phase 1 is greenfield. There is no existing `medkb` schema to alter.

| Step | Action | Reversible via |
|------|--------|----------------|
| 1 | Add `dhg-medkb-db` service to `docker-compose.yml` (new Postgres container, port 5433, volume `dhg-medkb-db-data`) | `docker compose down dhg-medkb-db && docker volume rm dhg-medkb-db-data` |
| 2 | Add `dhg-medkb-api` service to `docker-compose.yml` (new FastAPI, port 8015) | Remove service block, `docker compose down` |
| 3 | `docker compose up -d dhg-medkb-db` | `docker compose rm -s dhg-medkb-db` |
| 4 | Run `alembic upgrade head` inside `dhg-medkb-api` container — creates all 6 tables + extensions + indexes (one migration: `medkb_001_initial_schema.py`) | `alembic downgrade base` + re-init |
| 5 | Smoke-test DB: `SELECT 1 FROM medkb.concepts;` (empty table returns) | N/A |
| 6 | `docker compose up -d dhg-medkb-api` | `docker compose rm -s dhg-medkb-api` |
| 7 | Smoke-test API: `curl http://localhost:8015/healthz` | N/A |
| 8 | Build ingestor base image `dhg-medkb-ingestor` | `docker rmi dhg-medkb-ingestor` |
| 9 | Run MeSH ingestor in `--mode=full`: `docker run --rm --network dhgaifactory35_dhg-network -e INGESTOR_CLASS=MeSH dhg-medkb-ingestor` | `TRUNCATE medkb.concepts WHERE source='MESH'; TRUNCATE medkb.relationships WHERE provenance='MESH';` |
| 10 | Run RxNorm ingestor in `--mode=full` | Same truncate pattern |
| 11 | Run PubMed ingestor in `--mode=full` (curated journal filter) | Same truncate pattern |
| 12 | Run PMC OA ingestor in `--mode=full` (curated subset) | Same truncate pattern |
| 13 | *(Optional)* Run PrimeKG ingestor in `--mode=full` — **IF Phase 1 includes PrimeKG per §4.3 resolution** | Same truncate pattern |
| 14 | Author golden test set `services/medkb-api/test/golden_set.json` (~50 queries) | Edit/revert file |
| 15 | Run golden retrieval quality test: measure Recall@5 | N/A (read-only) |
| 16 | If Recall@5 ≥ 0.80: Phase 1 exit gate passes. Otherwise, stand up `dhg-pubmedbert` service and re-embed. | Revert to nomic via env var + re-embed |
| 17 | Add DHG `medkb_client.py` helper to `langgraph_workflows/dhg-agents-cloud/src/` | Revert commit |
| 18 | Smoke test: `research_agent` (or a test harness) makes a real call against `dhg-medkb-api` | N/A |

### 11.2 Phase 4 rollout sequence

Runs after Phase 1 exit gate is green.

| Step | Action | Reversible via |
|------|--------|----------------|
| 1 | Run USPSTF ingestor in `--mode=full` (writes to existing tables) | `DELETE FROM medkb.documents WHERE source='USPSTF'` |
| 2 | Verify supersession chain test with 2021→2023 lung cancer screening records | N/A |
| 3 | Run DailyMed ingestor in `--mode=full` for 200-drug anchor | `DELETE FROM medkb.documents WHERE source='DailyMed'` |
| 4 | Verify boxed warning test: `/v1/drug/6809/safety` returns metformin lactic acidosis warning | N/A |
| 5 | Run MedlinePlus EN ingestor in `--mode=full` | `DELETE FROM medkb.documents WHERE source='MedlinePlus'` |
| 6 | `python scripts/seed_style_rules.py` — loads 47 rules | `DELETE FROM medkb.style_rules` |
| 7 | `python scripts/seed_cdc_exemplars.py` — loads 20 pieces | `DELETE FROM medkb.style_exemplars WHERE source='CDC'` |
| 8 | Deploy `prose_quality_agent` with query-style-rules + fallback | Revert commit |
| 9 | Verify `prose_quality_agent` reads from DB (log: `medkb_rules_loaded rules_count=27`) | N/A |
| 10 | Deploy `needs_assessment_agent` with writing-layer retrieval | Revert commit |
| 11 | A/B eval vs baseline (§12.6) | N/A |
| 12 | Iterate on tuning until A/B passes | — |
| 13 | Deploy `grant_writer_agent` with writing-layer retrieval | Revert commit |
| 14 | Deploy remaining drafting agents (batch) | Revert individual commits |

### 11.3 Phase 5 rollout

Per sub-phase (§6.5). Each sub-phase:

1. Add/enable new ingestor(s) for the sub-phase sources
2. Run in `--mode=full` for the fan-out
3. Verify sample queries return expected results
4. Verify no regression in existing retrieval quality (golden test set re-run)
5. Sub-phase gate passes → next sub-phase starts

### 11.4 Rollback plan

**Full rollback from Phase 1:** `docker compose down dhg-medkb-db dhg-medkb-api` and `docker volume rm dhg-medkb-db-data`. Removes all MedKB state. Safe because MedKB is isolated — no other service depends on it until the DHG agents get their `medkb_client.py` helper in step 17 of §11.1. Reverting that commit restores pre-MedKB behavior.

**Phase 4 partial rollback:** each agent modification is a separate commit. Revert one commit to pull one agent's writing-layer retrieval; data stays in the DB.

**Phase 4 data rollback:** `DELETE FROM medkb.documents WHERE source IN ('USPSTF','DailyMed','MedlinePlus')`, `DELETE FROM medkb.style_rules`, `DELETE FROM medkb.style_exemplars`. Safe because Phase 1 data uses different `source` values.

**The one operation without a safe rollback** is removing hardcoded `BANNED_PATTERNS` from `prose_quality_agent.py` (step 8 of §11.2 after verification). Mitigation: the `fallback_rules.json` committed snapshot keeps the agent operational if MedKB is unreachable, and the change itself is reversible via `git revert`.

### 11.5 Production execution checklist (Phase 1)

Before running Phase 1 in production:

- [ ] Run full migration sequence on a staging Postgres copy
- [ ] Verify HNSW index build on Phase 1 corpus completes without OOM on the 64GB RAM server
- [ ] Verify MeSH + RxNorm + PubMed + PMC ingest completes within the planned window (estimate: 8–12 hours for full Phase 1 corpus)
- [ ] Verify golden test set Recall@5 passes on staging
- [ ] Confirm rollback path works end-to-end on staging
- [ ] Snapshot production state before step 1 (no state yet, but confirm nothing collides on ports 5433 / 8015)
- [ ] Have revert PRs pre-written for agent deploys

---

## 12. Test Plan & Phase Exit Gates

### 12.1 Test layers

| Layer | Scope | Framework | Coverage target |
|-------|-------|-----------|-----------------|
| Unit | Pure functions (citation formatting, chunking, embedding client, field mapping, CEBM map) | pytest | 100% line coverage on `api/citations.py`, `ingestors/base.py` chunking utilities, `embedding_client.py` |
| Ingestor integration | Each ingestor against a fixture corpus | pytest + HTTP recording (vcrpy) | Every ingestor has ≥1 full-run test against 3+ recorded items |
| API integration | Each new endpoint against a seeded test DB | pytest + httpx AsyncClient | Every endpoint has happy-path + ≥2 error cases |
| Migration integration | Alembic up/down cycle, multi-migration order | pytest-postgresql | Full up/down/up cycle passes for all migrations |
| End-to-end | DHG agent drafting with writing-layer retrieval against real MedKB | pytest + real LangGraph dev server | One golden-path run per modified agent |

### 12.2 Phase 1 exit gate (must all be green before Phase 4 starts)

**Infrastructure:**
- [ ] `dhg-medkb-db` healthy, volume persisted, restart survives
- [ ] `dhg-medkb-api` healthy at `/healthz`
- [ ] All 6 tables created with all columns, constraints, and indexes present
- [ ] HNSW indexes build successfully on Phase 1 data without errors

**Data:**
- [ ] MeSH ingest: ≥ 30,000 `concepts` rows with `source='MESH'`, ≥ 60,000 `relationships` rows with `provenance='MESH'`
- [ ] RxNorm ingest: ≥ 500,000 `concepts` rows with `source='RXNORM'`, ≥ 1,500,000 `relationships` rows with `provenance='RXNORM'`
- [ ] PubMed ingest: ≥ 400,000 `documents` rows with `source='PUBMED'`
- [ ] PMC OA ingest: ≥ 80,000 distinct `source_id` values in `documents` with `source='PMC'`, total chunks ≥ 500,000
- [ ] (If PrimeKG included) PrimeKG ingest: ≥ 100,000 concepts, ≥ 3,000,000 relationships
- [ ] `ingest_reports` shows 0 fatal errors for most-recent run of every source

**API functionality:**
- [ ] `GET /v1/concept/MESH/D006973` returns Hypertension with synonyms populated
- [ ] `GET /v1/concept/RXNORM/6809` returns metformin
- [ ] `GET /v1/graph/neighbors/{metformin_uuid}?rel_types=has_ingredient` returns non-empty
- [ ] `POST /v1/search/semantic {query:"SGLT2 heart failure"}` returns relevant PubMed abstracts, top result similarity > 0.7
- [ ] `POST /v1/search/literature {query:"...", year_range:[2023,2026]}` returns only 2023-2026 results
- [ ] 503 returned correctly when Ollama is unreachable

**Retrieval quality:**
- [ ] Golden test set (~50 queries) — Recall@5 ≥ 0.80 on nomic-embed-text
- [ ] If golden set fails: PubMedBERT service stood up, re-embed script runs, golden set re-tested, passes

**Integration:**
- [ ] `medkb_client.py` helper added to `langgraph_workflows/dhg-agents-cloud/src/`
- [ ] Smoke test: a DHG test harness makes a real call to `dhg-medkb-api` from inside the LangGraph network, gets valid results
- [ ] Grafana dashboard shows ingestors reporting; no alerts firing

**Performance:**
- [ ] `/v1/search/semantic` p95 latency < 80ms (target 50ms)
- [ ] `/v1/concept/...` p95 latency < 10ms
- [ ] `/v1/graph/neighbors/...` p95 latency < 30ms
- [ ] Query embedding p95 latency < 30ms

### 12.3 Phase 4 exit gate

**Data (in addition to Phase 1 data, still present):**
- [ ] USPSTF ~120 records in `documents` with `source='USPSTF'`, all with `valid_from` populated
- [ ] DailyMed ~2,000 chunks across 200 drugs in `documents` with `source='DailyMed'`
- [ ] MedlinePlus ~6,000 chunks across 1,000 topics with `source='MedlinePlus'`
- [ ] `style_rules` = 47 records
- [ ] `style_exemplars` ~400 chunks with `source='CDC'`, all `license='public_domain'`

**API functionality:**
- [ ] `POST /v1/search/guidelines {query:"lung cancer screening eligibility"}` returns USPSTF record, similarity > 0.7
- [ ] Supersession chain: 2023 supersedes 2021, both queryable via `as_of_date`, `/v1/history/{id}` returns both
- [ ] `GET /v1/drug/6809/safety` returns metformin boxed warning (lactic acidosis)
- [ ] `POST /v1/search/rules {category:["banned_phrase"]}` returns ≥ 27 DHG banned patterns
- [ ] `POST /v1/search/exemplars {audience_tag:"patient", register_tag:"explanatory", topic_tags:["diabetes"]}` returns a CDC A1C piece
- [ ] `GET /v1/cite/{usp_document_id}` returns correctly-formatted AMA guideline citation
- [ ] `GET /v1/cite/{pubmed_document_id}` returns correctly-formatted AMA journal citation
- [ ] `with_safety=true` on a metformin query prepends safety_context; `with_safety=false` does not
- [ ] License CHECK constraint test: inserting a `style_exemplar` with `license='copyrighted'` raises a DB-level error

**Writing layer integration:**
- [ ] `prose_quality_agent` reads banned patterns from `medkb.style_rules` (log: `medkb_rules_loaded rules_count=27`)
- [ ] `prose_quality_agent` fallback verified: shutting down `dhg-medkb-api` → agent falls back to `fallback_rules.json`, logs WARNING, Grafana alert fires
- [ ] `needs_assessment_agent` drafts cold open using retrieved rules + exemplars (log: `writing_layer_retrieval rules=10 exemplars=3`)
- [ ] A/B eval passes (§12.6) for `needs_assessment_agent`
- [ ] Regression: same draft that was caught as banned-phrase pre-migration is still caught post-migration
- [ ] A/B eval passes for `grant_writer_agent`
- [ ] Remaining drafting agents deployed, no regression on `prose_quality_agent` catch rate

**Performance (in addition to Phase 1):**
- [ ] `/v1/search/guidelines` p95 < 80ms
- [ ] `/v1/search/rules` p95 < 15ms
- [ ] `/v1/search/exemplars` p95 < 20ms
- [ ] `/v1/cite/{id}` p95 < 10ms
- [ ] `/v1/drug/{rxcui}/safety` p95 < 30ms
- [ ] Safety prepending overhead on drug queries < 15ms
- [ ] Writing-layer token overhead per drafting node < 2,000 tokens
- [ ] Drafting node latency impact < 1.2× baseline

### 12.4 Phase 5 exit gate (per sub-phase)

Each sub-phase in §6.5 has its own gate mirroring the Phase 4 structure: ingested row counts, verified sample queries, no regression on prior gates.

### 12.5 Safety / compliance tests (must-pass regardless of priority)

- [ ] License CHECK constraint test (see §12.3)
- [ ] Boxed warning presence: every Phase 4 anchor drug with a boxed warning has `metadata.safety_critical=true` on ≥ 1 chunk
- [ ] Boxed warning retrieval: `/v1/drug/{rxcui}/safety` for every boxed-warning drug in anchor set returns the boxed warning
- [ ] Temporal integrity: for every `supersedes` edge, the source record's `valid_from` ≥ the target record's `valid_from`
- [ ] Citation correctness: random sample of 10 generated citations across each citation_type validated by hand against the AMA Manual of Style
- [ ] Public domain verification: every ingested CDC piece has explicit `public_domain` license; any without fails the test

### 12.6 A/B evaluation protocol for writing-layer rollout

Used per agent in the writing-layer rollout.

**Setup:**
1. Select 3 reference topics covering diverse domains (NSCLC screening, T2DM management, HF readmission)
2. For each topic, run the agent twice:
   - **Baseline:** writing-layer retrieval disabled via feature flag
   - **Treatment:** writing-layer retrieval enabled
3. Collect both outputs + `prose_quality_agent` scores

**Acceptance criteria for treatment variant:**
- `prose_quality_agent` banned-phrase count ≤ baseline
- `prose_quality_agent` overall quality score ≥ baseline − 0.02 (natural variance tolerance)
- Subjective read by Stephen confirms treatment is at least as readable as baseline, no new stylistic issues
- No new hallucinations (spot-check factual claims in treatment but not baseline)

**Failure action:** roll back writing-layer retrieval for the agent, retune prompt template, re-run A/B. Do NOT proceed to the next agent until the current one passes.

### 12.7 Regression guards

Pinned across all phases:

- Phase 1 golden test set retrieval quality must not regress after any subsequent ingest or re-embed
- v2 Phase 1 agents (if any predate MedKB) must be unaffected — verified by running the existing DHG agent test suite before and after each MedKB deploy
- Phase 1 performance targets in §12.2 must hold through Phase 4 and Phase 5 — latency regressions block phase progression

---

## 13. Open Questions

Items flagged `[UNCERTAIN]` throughout the spec, consolidated for the review gate with my recommendations:

1. **§4.3 — PrimeKG in Phase 1.** Include (A), defer to Phase 1b (B), or drop entirely (C)? **My recommendation: B.** PrimeKG is the riskiest Phase 1 source (license + volume + reconciliation complexity). The other four Phase 1 sources are proven NLM corpora. Deferring PrimeKG lets the framework stabilize first and keeps the exit gate achievable.

2. **§8.2 — Query-embedding LRU cache.** Pre-build in Phase 1 or wait for measurement? **My recommendation: wait for measurement.** Query text varies too much at Phase 1 scale for caching to obviously pay off. If measurement shows a bottleneck, adding an in-process LRU is a 20-line change.

3. **§8.5 — Golden test set authorship.** Stephen personally or delegated to a research subagent? Either works for the spec; the plan file commits one way. **My recommendation: delegated to a research subagent under Stephen's review.** Stephen's time is more valuable on design decisions; a subagent can draft 50 queries with expected results and Stephen reviews/edits.

4. **§10.3 — `prose_quality_agent` fallback behavior.** Graceful fallback with loud alert, or hard fail? Already resolved as graceful fallback per the "go" in the previous session, baked into the spec at §10.3 and §11.4. **No action required.**

5. **§5.2 — DailyMed anchor drug list.** Phase 4 anchors at "200 drugs = intersection of boxed-warning + top-100 prescribed". Is the exact list going to be curated by Stephen or derived automatically from FDA data? **My recommendation: automatic derivation at ingest time.** The intersection of (drugs with boxed warnings per FDA `/drug/label.json`) and (top 100 per CMS prescription data) is an automated query — no manual curation needed. Commit file lists drugs actually ingested for audit, but the selection logic is code, not hand-curation.

6. **Program-level — naming.** Currently "MedKB v2". Is "v2" still accurate when this is the first thing to actually land in the repo (v1 was... never built? Or was it the pre-LangGraph Node-RED knowledge base work?). **My recommendation: keep "MedKB v2" for continuity with your prior mental model. The "v2" signals "this is the second try at a knowledge base for DHG" even though it's v1 of the actual implementation.** If you'd rather call it just "MedKB" (no version) or "MedKB v1", say so and I'll rename before plan generation.

7. **§2.2 — DHG `medkb_client.py` location.** I put it at `langgraph_workflows/dhg-agents-cloud/src/medkb_client.py`. Is that the right place, or does it belong in `shared/` for cross-service reuse? **My recommendation: keep it in the LangGraph subtree.** MedKB is consumed by LangGraph agents exclusively in Phase 1. If a second consumer appears, a 10-line extraction to `shared/` is trivial.

---

## 14. Deferred

Explicitly NOT in this spec:

- **Phases 2 and 3** — reserved scope, separate specs when needed
- **MIMIC-IV / MedAlpaca ingestion** — DUA-gated, separate workstream
- **NCCN, NICE** — copyrighted/restrictive, Phase 6 earliest with licensing negotiation
- **Full-text Cochrane** — paywalled, separate institutional-license workstream
- **Multi-format citation** (APA, Vancouver, MLA) — deferred until a CME reviewer or journal requires it
- **Streaming API responses** — deferred indefinitely
- **PubMedBERT deployment** — Phase 1 measurement-gated; documented migration path in §8.4
- **Rate limiting enforcement** — document intended limits in Phase 1, implement in Phase 4+
- **Admin mutation API endpoints** — not planned; ingestors write directly
- **Fine-tuning on style exemplars** — explicitly rejected; the addendum composes into prompts, not weights
- **Cross-register re-ranking endpoint** — premature until agent usage patterns observed
- **Shared `shared/medkb_client.py`** — keep in LangGraph subtree until a second consumer appears
- **PrimeKG** (tentative) — pending §13 item 1 resolution; may land in Phase 1, Phase 1b, or be dropped
- **UI for managing style rules** — out of scope; rules managed via SQL or seeder scripts

---

## 15. Cross-References

- **DHG prose_quality_agent** — `langgraph_workflows/dhg-agents-cloud/src/prose_quality_agent.py` (lines 39–67 for `BANNED_PATTERNS`)
- **DHG tracing** — `langgraph_workflows/dhg-agents-cloud/src/tracing.py` (`@traced_node` decorator used throughout; MedKB-calling nodes should use it too)
- **DHG registry** — `registry/api.py`, `registry/models.py` — sibling service, separate DB, no direct interaction
- **Docker compose main** — `docker-compose.yml` — where `dhg-medkb-db`, `dhg-medkb-api`, and ingestor services get added
- **Ollama** — `dhg-ollama` container, port 11434, serves `nomic-embed-text`
- **Observability** — `observability/` — Prometheus scrape config, Grafana dashboards, Loki scraping, Tempo traces
- **MedKB code location (to be created)** — `services/medkb-api/`, `services/medkb-ingestors/`, `services/medkb-api/alembic/versions/`

---

## 16. Appendix — Notes for the Plan Generator

When `superpowers:writing-plans` turns this spec into an executable plan:

1. **Phase 1 gets its own top-level section** in the plan with all 18 steps in §11.1 as tasks. TDD discipline applies — tests before implementation for every non-trivial module (base ingestor class, citation formatter, embedding client).
2. **Phase 4 gets its own top-level section** with the 14 steps in §11.2 as tasks.
3. **Phase 5 gets a placeholder section** with sub-phases 5a through 5e. Each sub-phase is its own mini-plan — do not fully decompose Phase 5 tasks until Phase 4 is shipping.
4. **Golden test set authoring** (§8.5) lands before Phase 1 exit gate. Research subagent delegation per §13 item 3.
5. **A/B eval harness** needs to be built in Phase 4, before the `needs_assessment_agent` writing-layer rollout. Worth explicit task.
6. **Every ingestor subclass** gets a TDD cycle: unit test → recorded fixture → integration test → deploy.
7. **The `dhg-medkb-api` FastAPI service** needs a `pyproject.toml`, `Dockerfile`, `pyrightconfig.json` path, and Alembic scaffold — add these as setup tasks before any endpoint code.
8. **Secrets**: Ollama URL, Postgres credentials, any API keys — all through environment variables referenced from `.env` (never hardcoded, never committed).

---

*End of spec. Next step: spec review by Stephen at the review gate, then invoke `superpowers:writing-plans` to produce the implementation plan.*
