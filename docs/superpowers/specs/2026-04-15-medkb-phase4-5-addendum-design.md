# MedKB Phase 4 / 5 Addendum — Design Spec

**Status:** Draft for review
**Date:** 2026-04-15
**Author:** Stephen Webber (design direction) + Claude (drafting)
**Supersedes:** nothing — this is an *addendum* to the MedKB v2 brief, not a replacement
**Related:** MedKB v2 brief (Phase 1 concepts/relationships/documents); DHG prose_quality_agent.py BANNED_PATTERNS

---

## 0. Executive Summary

This addendum extends the MedKB v2 brief with three new pillars and three schema deltas, all additive. Phase 4 lands the anchor sources for each new pillar — enough content to prove the mechanism end-to-end. Phase 5 fans out to the full corpora once Phase 4 is verified in production.

**New pillars added on top of v2:**

| # | Pillar | Data class | Tables touched |
|---|--------|-----------|----------------|
| IV | Authoritative Positions | Clinical guidelines, FDA drug labels, consumer health statements | `medkb.documents` (new columns) + `medkb.relationships` (new `supersedes` rel_type) |
| V | Style & Writing Guidance | Editorial rules + public-domain prose exemplars | `medkb.style_rules` (new), `medkb.style_exemplars` (new) |
| VI | Citation & Provenance | Formatted citations + source quality metadata | No new table — API layer composes over existing columns |

**Phase split:**

- **Phase 4** — Anchor sources only: USPSTF (~120 guidelines), DailyMed (~200 drugs), MedlinePlus English (~1,000 topics), DHG+AMA+PLAIN style rules (~47), CDC patient handouts (20 pieces). Total new chunks: ~8,500.
- **Phase 5** — Fan-out: full DailyMed (~120K labels), more guideline bodies (AHA/ACC, IDSA, Cochrane abstracts, AHRQ, WHO, CDC CPSTF), MedlinePlus Spanish + NIH institutes + CDC full + AHRQ patient + FDA Consumer, expanded exemplars (PLOS Med, eLife, NIH News, NLM Profiles, NIH Record, PMC narrative). Total new chunks at end of Phase 5: ~725,000.

**Key invariants the architecture enforces:**

1. **v2 schema unchanged** — every Phase 4 change is `ALTER TABLE ADD COLUMN` (nullable) or `CREATE TABLE`. No existing v2 column is touched. Existing v2 data remains valid after migration.
2. **Backward compatibility** — v2 Phase 1 agents keep working because every new column is nullable and every new API parameter defaults to v2 behavior.
3. **One embedding model across all six pillars** — PubMedBERT 768d (with nomic fallback per v2 decision). Style rules, exemplars, guidelines, and PubMed chunks share one embedding space so a single semantic query can return the full mix.
4. **Citation/provenance is API-only, no new table** — composes over existing document metadata rather than duplicating it. Citability = `source` + `evidence_level_oxford` + `grade_rating` + `valid_to IS NULL`, assembled into AMA-style citations at query time.
5. **Writing layer composes into prompts, not into weights** — rules and exemplars are retrievable, foldable into LLM context at inference. No fine-tuning.

**What this addendum deliberately does NOT include:**

- No new authentication / auth surface. Existing v2 API key gating applies to new endpoints.
- No new embedding model. Same PubMedBERT 768d (or nomic fallback).
- No replacement of `prose_quality_agent`. That agent stays; its `BANNED_PATTERNS` list gets mirrored into `style_rules` so drafting LLMs see rules before writing, while the agent still validates after writing. Same rules, two enforcement points.
- No MIMIC-IV, no MedAlpaca (those stay in v2 Phase 3). DUA/compliance work is separate.
- No NCCN, no NICE (copyrighted / restrictive redistribution — declined for Phase 5, revisit in Phase 6 only with direct licensing).
- No full-text Cochrane (paywalled — abstracts only; full text is a separate institutional-license workstream).

---

## 1. Architecture Overview

The addendum sits on top of the v2 brief. v2's three pillars (concepts / relationships / documents) stay exactly as specified. Phases 4 and 5 add three new pillars and three schema deltas, all additive.

```
┌────────────────────── v2 Brief (Phase 1) ──────────────────────┐
│  concepts       relationships        documents                 │
│  (MeSH/RxNorm)  (PrimeKG edges)      (PubMed/PMC chunks)        │
└────────────────────────────────────────────────────────────────┘
                            │
                            ▼  extends, does not replace
┌─────────────── Phase 4 / 5 Addendum ───────────────────────────┐
│                                                                │
│  Pillar IV — AUTHORITATIVE POSITIONS                           │
│  Clinical guidelines, FDA drug labels, consumer health state-  │
│  ments. Stored in medkb.documents with new metadata columns    │
│  (audience, evidence_level_oxford, grade_rating, valid_from,   │
│   valid_to, version_label) and supersedes edges.               │
│                                                                │
│  Pillar V — STYLE & WRITING GUIDANCE                           │
│  New tables:                                                   │
│    medkb.style_rules     — ~47 editorial rules, queryable      │
│    medkb.style_exemplars — public-domain prose chunks, tagged  │
│                            by audience + register              │
│                                                                │
│  Pillar VI — CITATION & PROVENANCE                             │
│  New API layer (no new table) returning formatted citations    │
│  + source quality metadata alongside retrieval results.        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────── DHG Agent Integration (existing) ────────────────┐
│  needs_assessment_agent → MedKB for gap evidence + patient     │
│                           voice                                │
│  research_agent         → MedKB for literature + guidelines    │
│  clinical_practice_agent→ MedKB for standard-of-care positions │
│  grant_writer_agent     → MedKB for citations + rules +        │
│                           exemplars                            │
│  prose_quality_agent    → MedKB style_rules becomes queryable, │
│                           not just hardcoded BANNED_PATTERNS   │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. Schema Deltas (exact DDL)

Every change is additive. No `DROP`, no `ALTER ... TYPE`, no data-destroying operation. Migration runs on a live database.

### 2a. `ALTER TABLE medkb.documents` — 8 nullable columns + 3 CHECK constraints

```sql
ALTER TABLE medkb.documents
  ADD COLUMN audience              TEXT,
  ADD COLUMN evidence_level_oxford TEXT,
  ADD COLUMN grade_rating          TEXT,
  ADD COLUMN valid_from            DATE,
  ADD COLUMN valid_to              DATE,
  ADD COLUMN version_label         TEXT,
  ADD COLUMN readability_grade     NUMERIC(4,1),
  ADD COLUMN source_authority      TEXT;

ALTER TABLE medkb.documents
  ADD CONSTRAINT documents_audience_check
    CHECK (audience IS NULL OR audience IN
      ('clinician','patient','journalist','mixed','unknown')),
  ADD CONSTRAINT documents_oxford_check
    CHECK (evidence_level_oxford IS NULL OR evidence_level_oxford IN
      ('1a','1b','2a','2b','3a','3b','4','5','na')),
  ADD CONSTRAINT documents_authority_check
    CHECK (source_authority IS NULL OR source_authority IN
      ('guideline_body','regulatory','peer_reviewed',
       'consumer_health','preprint','tertiary_reference'));
```

| Column | Purpose | Assigned by |
|--------|---------|-------------|
| `audience` | Target reader register | Ingestor, per-source heuristic + readability score |
| `evidence_level_oxford` | Auto-assigned CEBM level | Ingestor, mapped from PubMed PublicationType |
| `grade_rating` | GRADE rating when source supplies it | Ingestor, only when present in source |
| `valid_from` / `valid_to` | Temporal validity window | Ingestor (Phase 4 sources); null for PubMed |
| `version_label` | Human-readable version ("2023 Update") | Ingestor, null for non-versioned sources |
| `readability_grade` | Flesch-Kincaid grade level | Ingestor, computed by `textstat` library |
| `source_authority` | Provenance tier for citation layer | Ingestor, per-source constant |

**Why nullable:** existing v2 Phase 1 data (PubMed chunks) gets backfilled by a one-time script (see §2d). New Phase 4 sources populate at ingest time. Nullable tolerates the gap between migration and backfill completion.

### 2b. New table — `medkb.style_rules`

```sql
CREATE TABLE medkb.style_rules (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_category  TEXT NOT NULL,     -- 'banned_phrase' | 'structure' | 'citation_format'
                                      -- | 'readability' | 'tone' | 'ama_style'
    rule_name      TEXT NOT NULL UNIQUE,
    rule_text      TEXT NOT NULL,     -- human-readable rule for LLM context
    pattern        TEXT,              -- optional regex for automated check (nullable)
    severity       TEXT NOT NULL,     -- 'must' | 'should' | 'avoid'
    source         TEXT NOT NULL,     -- 'DHG_BANNED_PATTERNS' | 'AMA_Manual' |
                                      -- 'ICMJE' | 'PLAIN' | 'FDA_Patient_Labeling'
    audience_scope TEXT[],            -- ['clinician','patient'] or just one
    embedding      vector(768),
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT style_rules_severity_check
        CHECK (severity IN ('must','should','avoid'))
);

CREATE INDEX medkb_style_rules_embedding_hnsw
    ON medkb.style_rules USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX ON medkb.style_rules (rule_category);
CREATE INDEX ON medkb.style_rules (source);
```

**Design note on `pattern`:** regex is optional. `prose_quality_agent`'s 27 `BANNED_PATTERNS` entries already have regex — those migrate over as-is. AMA-style rules like "spell out numbers under 10 unless they start a sentence" carry `rule_text` but no `pattern`.

### 2c. New table — `medkb.style_exemplars`

```sql
CREATE TABLE medkb.style_exemplars (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title             TEXT NOT NULL,
    source            TEXT NOT NULL,     -- 'CDC' | 'MedlinePlus' | 'NIH_News' | 'PLOS' | ...
    source_url        TEXT NOT NULL,
    license           TEXT NOT NULL,     -- 'public_domain' | 'CC-BY' | 'CC-BY-SA'
    audience_tag      TEXT NOT NULL,     -- 'clinician' | 'patient' | 'journalist'
    register_tag      TEXT NOT NULL,     -- 'authoritative' | 'explanatory' |
                                         -- 'narrative' | 'instructional'
    topic_tags        TEXT[],            -- ['cardiology','screening','diabetes']
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

CREATE INDEX ON medkb.style_exemplars (audience_tag, register_tag);
CREATE INDEX ON medkb.style_exemplars (source);
```

**Critical guardrail:** the `license` CHECK constraint is enforced at schema level. Any attempt to insert a copyrighted source fails at the database. This is the single most important safety property of the addendum — it makes a licensing violation impossible to accidentally commit.

### 2d. Backfill script for existing v2 Phase 1 data

After the `ALTER TABLE` above, run a one-time Python script (part of the Phase 4 migration package — not a SQL migration because it needs `textstat` and PubMed metadata parsing logic):

```python
# scripts/backfill_v2_documents.py
# Runs once after 2a migration lands.
# Populates: audience, evidence_level_oxford, readability_grade, source_authority
# Leaves null: grade_rating, valid_from, valid_to, version_label
#
# Logic:
#   audience          = 'clinician'       (all PubMed chunks are clinician-register)
#   evidence_level    = map(metadata->>'publication_type') via CEBM table
#   readability_grade = textstat.flesch_kincaid_grade(chunk_text)
#   source_authority  = 'peer_reviewed'   (or 'preprint' if journal is bioRxiv/medRxiv)
```

Backfill is **chunked** (1000 rows per batch), **idempotent** (`WHERE audience IS NULL`), and **re-runnable**. Reports progress and any rows it couldn't classify (logged, not failed).

### 2e. New relationship type (no DDL — just a value)

`medkb.relationships.rel_type` already accepts any TEXT value. Phase 4 adds `'supersedes'` as a new documented value:

```
source_id   = newer version UUID
target_id   = older version UUID
rel_type    = 'supersedes'
provenance  = 'USPSTF' | 'NCCN' | 'FDA' | etc.
evidence    = 'auto:ingest' OR explicit supersession statement from source
```

No schema change; convention only.

### 2f. Migration ordering

Runs as a single transaction except for HNSW index creation and backfill, which run outside the transaction:

1. `BEGIN;` — apply 2a, 2b, 2c (DDL and CHECK constraints)
2. `COMMIT;`
3. `CREATE INDEX CONCURRENTLY` for all HNSW indexes (cannot run inside transaction; concurrent to avoid locking writes)
4. Run `backfill_v2_documents.py` (script, not SQL)
5. Verify row counts and constraint pass-through with a smoke-test query

### 2g. What's deliberately NOT added

- **No `audience NOT NULL` constraint.** Backfill populates it, but the column stays permanently nullable so a future ambiguous source can write NULL while a human review decides. Enforcement happens at API query time (`WHERE audience = 'clinician'` treats NULL as non-matching, the safe default).
- **No foreign key from `style_exemplars.topic_tags` to `medkb.concepts`.** Tag strings only. Keeps curation flexible for topics that don't have formal concept records. Tradeoff: no referential integrity on tags.
- **No `medkb.citations` table.** Citation formatting composes over existing document columns at API time. A table would duplicate data and create sync problems.

---

## 3. Phase 4 Anchor Sources

Five anchor sources — one per new data class — each proven end-to-end before Phase 5 fan-out. URLs, access methods, volume, and ingest targets are explicit so nothing is ambiguous when ingestor code gets written.

### 3a. Clinical Guidelines anchor — USPSTF

| Property | Value |
|----------|-------|
| Source | US Preventive Services Task Force |
| Access | JSON recommendation summaries at `https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics` + per-recommendation JSON endpoints |
| License | US federal government work — public domain |
| Volume (Phase 4 anchor) | All ~90 current recommendations + ~30 archived (superseded) versions for supersession-chain testing |
| Writes to | `medkb.documents` only (no concept creation — USPSTF topics map to existing MeSH concepts) |
| Chunking | Section-level: Recommendation, Rationale, Clinical Considerations, Supporting Evidence. Do not chunk below section — each section is itself a citable unit. |

**Field mapping:**

```
audience              = 'clinician'
source                = 'USPSTF'
source_authority      = 'guideline_body'
evidence_level_oxford = NULL            (not a study; it's a recommendation)
grade_rating          = NULL            (USPSTF uses its own A/B/C/D/I scale, not GRADE)
valid_from            = recommendation publication date
valid_to              = NULL if current; set to supersession date when newer version lands
version_label         = "2021 Update" etc. from source
readability_grade     = computed via textstat
metadata.uspstf_grade = raw letter grade ("B", "I") stored in existing metadata JSONB
```

**Gotcha:** USPSTF letter grades (A/B/C/D/I) are NOT GRADE. Storing them in `grade_rating` would conflate two different systems. They go in the existing `metadata` JSONB column as `{"uspstf_grade": "B"}`, and the citation API surfaces them separately. Documented convention, no schema change.

**Supersession chain test:** When the 2023 lung cancer screening recommendation is ingested after the 2021 version, the ingestor:

1. Finds the existing 2021 record by `source = 'USPSTF'` + `metadata.topic = 'lung_cancer_screening'`
2. Sets its `valid_to` to 2023 publication date
3. Writes a `supersedes` relationship edge: new_record → old_record
4. Logs both versions remained queryable via `as_of_date` parameter

This is the first real exercise of the supersedes logic. If it doesn't work right here with a known dataset, we fix it before any other source hits it.

### 3b. FDA Drug Labels anchor — DailyMed

| Property | Value |
|----------|-------|
| Source | NLM DailyMed Structured Product Labels (SPL) |
| Access | REST API at `https://dailymed.nlm.nih.gov/dailymed/services/v2/spls` + bulk SPL zip archives from `https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm` |
| License | Public domain (NLM) |
| Volume (Phase 4 anchor) | ~200 drugs — intersection of (all ~400 FDA boxed-warning drugs) + (top 100 by US prescription volume per CMS data). Full ~120K in Phase 5. |
| Writes to | `medkb.documents` (SPL sections as chunks) + `medkb.relationships` (`interacts_with`, `contraindicated_in` edges when parseable) |
| Chunking | SPL section-level — Boxed Warning, Indications and Usage, Contraindications, Warnings and Precautions, Drug Interactions, Adverse Reactions, Dosage, Patient Counseling Information |

**Field mapping:**

```
audience              = 'clinician' for prescribing sections
                      = 'patient' for Patient Counseling Information sections
                                  (SPL separates these cleanly — we preserve it)
source                = 'DailyMed'
source_authority      = 'regulatory'
evidence_level_oxford = NULL (regulatory label, not a study)
grade_rating          = NULL
valid_from            = SPL effective date
valid_to              = set when a newer SPL version for same setid is ingested
version_label         = SPL version number
metadata.setid        = SPL set ID (stable drug identifier across versions)
metadata.ndc          = NDC codes from the SPL
metadata.rxcui        = cross-reference to existing RxNorm concept records
```

**Concept reconciliation:** each SPL gets linked to its RxNorm concept record (populated in v2 Phase 1) via `rxcui`. If no RxNorm match exists, log to `dailymed_unmapped.log` — same pattern as PrimeKG unmapped nodes. Don't create orphan concepts.

**Gotcha:** SPL XML is dense (200–800 KB per label) and inconsistently structured across manufacturers. The parser must tolerate missing sections. We parse section-by-section with graceful degradation — a missing Drug Interactions section is logged but doesn't fail the ingest.

**Safety layer tie-in:** boxed warnings get special treatment — every chunk from a Boxed Warning section writes `metadata.safety_critical = true`. The citation API prepends boxed warnings to any retrieval for the associated drug concept. A clinician agent asking about metformin always sees the boxed warning regardless of query wording. This prevents the "agent didn't happen to retrieve the warning" failure mode. See §5e.

### 3c. Consumer Health anchor — MedlinePlus

| Property | Value |
|----------|-------|
| Source | NLM MedlinePlus (English health topics) |
| Access | Web Service API at `https://wsearch.nlm.nih.gov/ws/query` + bulk XML at `https://medlineplus.gov/xml.html` |
| License | Public domain (NLM) |
| Volume (Phase 4 anchor) | All ~1,000 English health topics. Spanish deferred to Phase 5. Drug info deferred (DailyMed covers it). |
| Writes to | `medkb.documents` only (concepts already exist from MeSH) |
| Chunking | Topic-section level — Summary, Symptoms, Causes, Tests, Treatments, Prevention, Living With |

**Field mapping:**

```
audience          = 'patient'
source            = 'MedlinePlus'
source_authority  = 'consumer_health'
readability_grade = computed via textstat (MedlinePlus targets grade 6–8 — verify with spot-checks)
valid_from/to     = NULL — MedlinePlus is updated in place without version history
version_label     = NULL
metadata.mesh_ids = cross-reference to MeSH concepts from Phase 1
```

**Gotcha:** MedlinePlus is updated in place. We cannot reconstruct "what MedlinePlus said about X in 2019" — only current state. This is explicitly acknowledged in the spec, and the temporal query API (`as_of_date` parameter) does not apply to MedlinePlus records. Queries with `as_of_date` on MedlinePlus records return current state with a flag `temporal_unavailable: true`. Documented limitation, not a bug.

**Concept reconciliation:** each MedlinePlus topic cross-references to MeSH via the topic's MeSH ID (published in the XML). Agents asking about "hypertension" get both the MeSH concept definition (clinician register) and the MedlinePlus topic (patient register) in a single query with `audience=mixed`.

### 3d. Style Rules seed — DHG BANNED_PATTERNS + AMA + PLAIN

| Source | Records | Notes |
|--------|---------|-------|
| `DHG_BANNED_PATTERNS` | 27 | Lifted verbatim from `prose_quality_agent.py` lines 39–67. Same regexes, same rule names. `severity='avoid'`, `rule_category='banned_phrase'`, `audience_scope=['clinician','patient']`. |
| AMA Manual of Style (essentials) | ~15 | Hand-authored summaries with citation to the source chapter — fair-use internal reference. Examples: "Spell out numbers under 10 except in tables, measurements, or sentence starts (AMA §19.1)", "Drug names: use generic; include brand in parentheses on first mention (AMA §15.4)". `rule_category='ama_style'`, `severity='should'`. |
| PLAIN (Plain Language Action Network) | ~5 | Hand-authored essentials for patient register. Examples: "Address the reader directly as 'you'", "Use common words, not jargon — 'heart attack' not 'myocardial infarction'". `rule_category='readability'`, `severity='must'`, `audience_scope=['patient']`. |
| **Total Phase 4 seed** | **~47 records** | Embedded via PubMedBERT. Stored in `medkb.style_rules`. Added as a one-time migration script. |

**Critical design property:** the DHG banned-patterns list lives in exactly one place after Phase 4 — the database. `prose_quality_agent.py` gets updated to query `medkb.style_rules` at node startup rather than hardcoding the 27 patterns. This means:

- Adding a new banned phrase is a database insert, not a code change.
- Drafting LLMs (`needs_assessment`, `research`, `grant_writer`) see the same rules *before* writing that `prose_quality` checks *after* writing.
- One source of truth for editorial policy.

This is the only change to an existing DHG agent that Phase 4 makes. It's a small but important integration point — details in §6.

### 3e. Style Exemplars anchor — CDC Patient Handouts

| Property | Value |
|----------|-------|
| Source | CDC patient fact sheets across major conditions |
| Access | Direct HTTPS download of HTML or PDF from `https://www.cdc.gov` topic pages |
| License | Public domain (US federal work) — explicitly verified per page |
| Volume (Phase 4 anchor) | 20 hand-curated pieces. Topics: diabetes, hypertension, COPD, A1C education, cancer screening (colorectal, breast, lung), vaccination, heart attack warning signs, stroke FAST, hand hygiene, foodborne illness, antibiotic stewardship, tobacco cessation, mental health, chronic pain, kidney disease, asthma, sleep, nutrition, physical activity, healthy aging |
| Chunks after ingestion | ~300–500 (hand-picked pieces average ~15–25 chunks at 512 tokens) |
| Writes to | `medkb.style_exemplars` only |

**Field mapping:**

```
source            = 'CDC'
source_url        = the exact https://www.cdc.gov/... URL
license           = 'public_domain'
audience_tag      = 'patient'
register_tag      = 'explanatory' for conditions, 'instructional' for "what to do" pieces
topic_tags        = ['diabetes','A1C','screening',...] hand-tagged at ingestion
readability_grade = computed
```

**Why 20 and not 200:** Phase 4 anchor is about proving the mechanism. If the drafting LLM can actually produce patient-register prose when given CDC exemplars as few-shot anchors — and if `prose_quality_agent` validates the output cleanly — then the mechanism works and Phase 5 can safely fan out to PLOS, eLife, NIH News in Health, etc. If the mechanism fails or needs tuning, we learn that with 20 pieces and 5 test queries, not 2,000 pieces and regret.

### 3f. Anchor source summary

| Source | Pillar | Table | Records (Phase 4) | Access method |
|--------|--------|-------|-------------------|---------------|
| USPSTF | Guidelines | `documents` | ~120 | JSON API |
| DailyMed | FDA labels | `documents` + `relationships` | ~200 drugs, ~2K chunks | REST API + bulk |
| MedlinePlus | Consumer health | `documents` | ~1,000 topics, ~6K chunks | Web Service API + XML bulk |
| DHG + AMA + PLAIN | Style rules | `style_rules` | ~47 | Migration script |
| CDC handouts | Style exemplars | `style_exemplars` | 20 pieces, ~400 chunks | Direct HTTPS |

**Total new chunk volume at end of Phase 4:** ~8,500 chunks across the two new tables plus expanded `documents`. All embedded via PubMedBERT (or nomic fallback if PubMedBERT still isn't available at Phase 4 build time — same decision as Phase 1).

---

## 4. Phase 5 Fan-Out Sources

No new architecture. Phase 5 adds content through the proven Phase 4 pattern — same tables, same ingestor base class, same API. Every new source is a `SourceIngestor` subclass that writes to existing columns.

### 4a. Pillar IV expansion — Clinical Guidelines (beyond USPSTF)

| # | Source | License | Access | Est. records | Notes |
|---|--------|---------|--------|--------------|-------|
| 1 | AHA/ACC | Journal article (CC-BY when OA) | PubMed / PMC full-text XML | ~50 active | CV prevention, HF, HTN, lipids. PMC only if OA. |
| 2 | IDSA | Journal article (OA variable) | PubMed / PMC | ~40 active | Infectious disease. Same OA-only rule. |
| 3 | Cochrane Systematic Reviews | Abstract public; full review paywalled | PubMed E-utilities (abstracts + GRADE ratings only) | ~9,000 active | Phase 5 = abstracts only. Full-text deferred to separate institutional-license workstream. GRADE ratings in abstract, so evidence grading still lands. |
| 4 | AHRQ Evidence Reports | Public domain (federal) | Bulk download from `https://effectivehealthcare.ahrq.gov/` | ~300 reports | Full text, directly ingestible. |
| 5 | CDC Community Preventive Services | Public domain | Direct HTTPS / XML | ~250 recommendations | Pairs with USPSTF. |
| 6 | WHO Guidelines | Mixed PD / CC-BY | IRIS repository bulk download | ~400 active | License verified per-document at ingest; ingestor rejects anything not explicitly PD or CC-BY. |

Field mapping is identical to USPSTF Phase 4 pattern — `audience='clinician'`, `source_authority='guideline_body'`, `valid_from`/`valid_to` populated, `supersedes` edges written when a newer version of the same guideline arrives.

**Deliberate Phase 5 exclusions (flagged now so they don't drift in later):**

- **NCCN** — oncology guidelines are copyrighted. NCCN's free clinician registration grants viewing rights, not redistribution rights. Storing full text in a local KB even for internal use is a licensing gray area. **Declined for Phase 5.** Revisit in Phase 6 only with NCCN direct outreach or a paid license.
- **NICE (UK)** — free to read, restrictive redistribution license. Same treatment as NCCN. **Declined for Phase 5.**
- **Paywalled Cochrane full text** — abstracts only. Full text requires institutional license negotiation. Separate project.

### 4b. Pillar IV expansion — FDA data (beyond 200 anchor drugs)

| # | Source | License | Access | Scope |
|---|--------|---------|--------|-------|
| 1 | DailyMed full corpus | Public domain | Bulk SPL zip archives | ~120,000 drug labels. Fan-out of the 200-drug anchor. Same parser, same field mapping. |
| 2 | openFDA Adverse Events (FAERS) | Public domain | REST API at `https://api.fda.gov/drug/event.json` | Not stored per-event (too large). Ingested as drug-level summaries: top 20 most-reported adverse events per drug, updated quarterly. Writes to `medkb.documents` with `source='openFDA'`, `audience='clinician'`. |
| 3 | FDA Drug Approvals | Public domain | REST API at `https://api.fda.gov/drug/drugsfda.json` | Approval dates, indications, NDAs. Populates `valid_from` for DailyMed records where label history is incomplete. |

**Why FAERS is summarized and not stored raw:** FAERS ships millions of individual adverse event reports. Storing per-event gives zero retrieval value (agents want patterns, not individual reports) and explodes the HNSW index. Summarization at ingest — "top 20 events per drug with counts and MedDRA terms" — gives agents the answer they actually want in ~200 words per drug.

### 4c. Pillar V expansion — Consumer Health (beyond English MedlinePlus)

| # | Source | License | Access | Scope |
|---|--------|---------|--------|-------|
| 1 | MedlinePlus Spanish | Public domain | Same XML bulk | ~1,000 topics, Spanish register |
| 2 | NIH Institute patient content | Public domain (federal) | Direct HTTPS per institute | NHLBI, NIDDK, NCI, NIMH, NINDS, NIA, NIAID, NIAMS. Each institute publishes ~100–300 patient-facing pages. |
| 3 | CDC full topic pages | Public domain | Direct HTTPS | Fan-out from 20 anchor handouts to full CDC patient corpus — ~1,500 topics |
| 4 | AHRQ patient materials | Public domain | Bulk download | ~400 patient decision aids and explainers |
| 5 | FDA Consumer Updates | Public domain | REST API | ~2,000 articles, plain-language FDA consumer safety information |

Field mapping identical to MedlinePlus anchor — `audience='patient'`, `source_authority='consumer_health'`, `readability_grade` computed, temporal fields null (all of these update in place).

**Language handling:** Spanish MedlinePlus records get `metadata.language='es'`; English defaults to `metadata.language='en'`. API accepts a `language` filter. No separate table.

### 4d. Pillar V expansion — Style Exemplars (beyond 20 CDC anchors)

| # | Source | License | Est. pieces | Register |
|---|--------|---------|-------------|----------|
| 1 | CDC full handout corpus | Public domain | ~500 | explanatory + instructional |
| 2 | NIH News in Health | Public domain | ~400 monthly articles (archive back to 2006) | narrative + explanatory |
| 3 | PLOS Medicine Essays | CC-BY | ~600 essays | authoritative + narrative |
| 4 | eLife Features & Essays | CC-BY | ~300 pieces | authoritative + narrative |
| 5 | NLM Profiles in Science essays | Public domain | ~200 historical pieces | narrative (biography/history of medicine) |
| 6 | NIH Record newsletter archive | Public domain | ~300 articles | narrative + explanatory (institutional voice) |
| 7 | PubMed Central narrative medicine tagged articles | CC-BY subset only | ~500 filtered by PMC license field | narrative |

**Total Phase 5 exemplar corpus:** ~2,800 pieces → ~35,000–50,000 chunks at 512 tokens. All CHECK-constrained at schema level to `license IN ('public_domain','CC-BY','CC-BY-SA')`, so a buggy ingestor cannot accidentally store copyrighted content.

**Register balance:**

| Register | Phase 4 anchor | Phase 5 total |
|----------|----------------|---------------|
| explanatory | ~250 chunks (CDC) | ~15,000 chunks |
| instructional | ~150 chunks (CDC) | ~8,000 chunks |
| authoritative | 0 | ~12,000 chunks (PLOS Med, eLife) |
| narrative | 0 | ~10,000 chunks (NIH News, Profiles, narrative medicine) |

The 4-register breakdown lets an agent retrieve exemplars matching the specific output it needs — authoritative for a CME grant's clinical rationale section, narrative for a cold-open patient vignette, explanatory for a gap description, instructional for patient counseling copy.

### 4e. Phase 5 source summary

| Pillar | Phase 4 anchors | Phase 5 additions | Phase 5 new chunks (est.) |
|--------|-----------------|-------------------|---------------------------|
| Clinical guidelines | USPSTF (~120) | AHA/ACC, IDSA, Cochrane abstracts, AHRQ, CDC CPSTF, WHO | ~35,000 |
| FDA data | DailyMed 200 drugs (~2K) | Full DailyMed ~120K labels, openFDA summaries, FDA approvals | ~600,000 |
| Consumer health | MedlinePlus EN (~6K) | MedlinePlus ES, NIH institutes, CDC full, AHRQ patient, FDA Consumer | ~40,000 |
| Style exemplars | CDC 20 pieces (~400) | CDC full, NIH News, PLOS Med, eLife, NLM Profiles, NIH Record, PMC narrative | ~50,000 |
| Style rules | DHG + AMA + PLAIN (~47) | Phase 5 adds no new rules — rules stabilize in Phase 4 | 0 |
| **Grand total new chunks after Phase 5** | — | — | **~725,000** |

### 4f. Phase 5 sequencing within the phase

Phase 5 itself has internal order. Not all sources ship simultaneously.

1. **First** — fan out DailyMed to full 120K labels. Highest volume, proven parser, biggest payoff (comprehensive drug knowledge).
2. **Then** — MedlinePlus Spanish + CDC full topic pages. Proven parsers, straightforward fan-out, improves consumer coverage dramatically.
3. **Then** — PLOS Medicine + eLife exemplars. Adds authoritative register (the biggest gap in the Phase 4 exemplar corpus). Requires verifying CC-BY on each article.
4. **Then** — AHA/ACC + IDSA + Cochrane abstracts. Clinical guidelines fan-out. Requires OA filtering logic.
5. **Then** — AHRQ reports, CDC CPSTF, WHO guidelines, NIH institutes, openFDA, NIH News, FDA Consumer, NLM Profiles, NIH Record, PMC narrative. The long tail.

Each step ships independently and ships only when the one before it is verified in production — no big-bang Phase 5 release.

---

## 5. API Additions

All routes versioned under `/v1/` (matches v2 convention). Auth, rate limiting, and base URL unchanged from v2. FastAPI auto-generates OpenAPI docs at `/v1/docs`.

### 5a. New endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/search/guidelines` | Search clinical guidelines + regulatory docs, temporal-aware |
| POST | `/v1/search/patient` | Patient-register semantic search (convenience wrapper with forced `audience='patient'`) |
| POST | `/v1/search/rules` | Query style rules by category, severity, audience |
| POST | `/v1/search/exemplars` | Query style exemplars by audience, register, topic |
| GET | `/v1/cite/{document_id}` | Formatted AMA citation + structured citation fields for one document |
| POST | `/v1/cite/bulk` | Same, for up to 50 document IDs in one call |
| GET | `/v1/drug/{rxcui}/safety` | All `safety_critical` chunks for a drug (boxed warnings, contraindications, interactions) |
| GET | `/v1/history/{document_id}` | Temporal history: this record + full predecessor chain via `supersedes` |

### 5b. New parameters on existing v2 endpoints

Every v2 search endpoint (`/v1/search/semantic`, `/v1/search/literature`, `/v1/search/concept`) gains these optional parameters. Each has a safe default preserving v2 behavior.

| Parameter | Type | Default | Effect |
|-----------|------|---------|--------|
| `audience` | `str \| str[]` | null (no filter) | Filter chunks to one or more audiences. Null matches any audience including null. |
| `min_evidence_level` | `str` | null | Filter to chunks at this Oxford CEBM level or higher (`'1a'` strongest, `'5'` weakest) |
| `source_authority` | `str[]` | null | Filter by authority tier: `guideline_body`, `regulatory`, `peer_reviewed`, `consumer_health`, `preprint`, `tertiary_reference` |
| `as_of_date` | `date` (ISO 8601) | null | Temporal query. Returns records where `valid_from <= as_of_date AND (valid_to IS NULL OR valid_to > as_of_date)`. Null = current. |
| `current_only` | `bool` | `true` | When true, filter `valid_to IS NULL`. Superseded by `as_of_date` when both provided. |
| `readability_max` | `number` | null | Filter chunks to Flesch-Kincaid grade ≤ this value. Typical patient query: `readability_max=8`. |
| `with_citations` | `bool` | `false` | When true, each result includes inline citation object (same shape as `/v1/cite` response). |
| `with_safety` | `bool` | `true` for drug-concept queries, `false` otherwise | Controls safety-critical prepending (see §5e). |

**Filter precedence:** filters combine with AND. A query with `audience='clinician'` & `source_authority='guideline_body'` & `current_only=true` returns only current clinical guidelines written for clinicians.

### 5c. New endpoint details

#### POST `/v1/search/guidelines`

Request:
```json
{
  "query": "lung cancer screening eligibility",
  "limit": 10,
  "source_authority": ["guideline_body", "regulatory"],
  "as_of_date": null,
  "min_evidence_level": null,
  "with_citations": true,
  "with_history": false
}
```

Response:
```json
{
  "results": [
    {
      "document_id": "uuid",
      "source": "USPSTF",
      "title": "Lung Cancer: Screening",
      "chunk_text": "...",
      "chunk_index": 0,
      "audience": "clinician",
      "source_authority": "guideline_body",
      "evidence_level_oxford": null,
      "grade_rating": null,
      "version_label": "2021 Update",
      "valid_from": "2021-03-09",
      "valid_to": null,
      "readability_grade": 14.2,
      "similarity_score": 0.87,
      "metadata": {"uspstf_grade": "B", "topic": "lung_cancer_screening"},
      "citation": {
        "ama_formatted": "US Preventive Services Task Force. Lung Cancer: Screening. 2021. https://www.uspreventiveservicestaskforce.org/... Accessed April 15, 2026.",
        "authoring_body": "US Preventive Services Task Force",
        "title": "Lung Cancer: Screening",
        "year": 2021,
        "url": "https://www.uspreventiveservicestaskforce.org/...",
        "accessed_date": "2026-04-15",
        "citation_type": "guideline"
      }
    }
  ],
  "total_matches": 14,
  "query_time_ms": 38
}
```

**Why a dedicated guidelines endpoint when `/v1/search/semantic` with filters could do the same:** guidelines have a specific retrieval pattern that differs from general semantic search — agents almost always want `current_only=true`, `source_authority` restricted to authoritative tiers, and inline citations. A dedicated endpoint with these defaults pre-set means a grant-writer agent's call is one line: `POST /v1/search/guidelines {query: "..."}`. The semantic endpoint remains available for the rare case an agent wants to search across all corpora at once.

#### POST `/v1/search/rules`

Request:
```json
{
  "query": "citation format for drug names",
  "audience_scope": ["clinician"],
  "severity": ["must", "should"],
  "category": ["ama_style", "banned_phrase"]
}
```

Response: array of style rule records with `rule_name`, `rule_text`, `pattern`, `severity`, `source`, `similarity_score`.

**Use case:** a drafting LLM, before writing a section, retrieves the top 10 most-relevant rules and folds them into the system prompt as constraints. The `severity` field lets the prompt say "must never: X; should avoid: Y".

#### POST `/v1/search/exemplars`

Request:
```json
{
  "query": "explaining diabetes A1C to patients",
  "audience_tag": "patient",
  "register_tag": "explanatory",
  "topic_tags": ["diabetes"],
  "limit": 3
}
```

Response: array of exemplar chunks with `title`, `source`, `source_url`, `chunk_text`, `word_count`, `readability_grade`, `license`, `similarity_score`.

**Use case:** same drafting LLM retrieves 3 exemplars after retrieving rules. Exemplars go into the few-shot anchor section of the prompt with "write in the voice of these examples:" framing.

#### GET `/v1/cite/{document_id}`

Returns the citation for one document in both structured and AMA-formatted form. Format depends on `citation_type` inferred from `source_authority`:

| `source_authority` | `citation_type` | AMA template |
|--------------------|-----------------|--------------|
| `peer_reviewed` | `journal` | Authors. Title. Journal. Year;Volume(Issue):Pages. doi:XXX. PMID: XXX. |
| `guideline_body` | `guideline` | Authoring Body. Title. Year. URL. Accessed date. |
| `regulatory` | `label` | Manufacturer. Drug Name (Brand) [prescribing information]. Place: Manufacturer; Year. URL. |
| `consumer_health` | `consumer` | Authoring Body. Title. Site. Year. URL. Accessed date. |
| `preprint` | `preprint` | Authors. Title [preprint]. Server. Year. doi:XXX. |
| `tertiary_reference` | `reference` | Authoring Body. Title. Year. URL. |

Citation construction happens at query time from existing columns — no citations table. The `ama_formatted` string is assembled by a pure function in `api/citations.py`. Deterministic, testable, no persistence.

**Why AMA only:** CME grant applications use AMA. Variance in citation format is itself a quality signal to reviewers. One canonical format, built-in, correctly — not five half-correct ones. APA/Vancouver/MLA deferred until a concrete use case requires them.

#### GET `/v1/drug/{rxcui}/safety`

Returns all chunks from documents that (a) are linked to this RxCUI via DailyMed's `metadata.rxcui`, and (b) carry `metadata.safety_critical = true`. Result includes boxed warnings, contraindications, major drug interactions, and patient counseling warnings.

Response: array of chunks plus a top-level `warning_level` field: `boxed_warning`, `contraindication`, `major_interaction`, or `precaution`. Sorted by severity (boxed warnings first).

**Why a dedicated endpoint:** missing a boxed warning on a drug query is not a retrieval miss — it's a safety failure. A dedicated endpoint forces agents working on drug content to make an explicit call, and the endpoint guarantees deterministic, complete return of all safety data for that drug regardless of query wording.

#### GET `/v1/history/{document_id}`

Returns the record + all predecessors reachable via `supersedes` edges, ordered newest → oldest. Also returns any successor if this record has been superseded.

Response:
```json
{
  "current": { "...newest valid version..." },
  "requested": { "...the document_id originally queried..." },
  "predecessors": [ "...array of superseded versions, newest-first..." ],
  "successor": null
}
```

**Use case:** a grant writer needs to cite both the current USPSTF recommendation and the prior version it replaced to make a "practice gap" argument. One API call, complete history.

### 5d. Changes to existing v2 endpoints

- **`POST /v1/search/semantic`** — gains all parameters in §5b. Default behavior unchanged: a v2-shaped request (no new params) returns v2-shaped results. Adding `audience=clinician` restricts the corpus post-Phase-4.
- **`POST /v1/search/literature`** — same new parameters apply. Responses gain the new columns on each chunk. v2 clients that ignore unknown fields keep working.
- **`GET /v1/concept/{source}/{id}`** — response gains a `related_documents` summary: counts of documents linked to this concept, broken down by `audience` and `source_authority`. Agents can see at a glance "this concept has 14 clinician-register documents from guideline bodies and 3 patient-register documents from consumer health sources" before committing to a full retrieval.
- **`GET /v1/graph/neighbors/{id}`** — gains a `rel_types` filter parameter including the new `supersedes` edge type. Default behavior excludes `supersedes` edges (they're an internal mechanism, not a clinical relationship).

### 5e. Safety-critical prepending — the default-on behavior

When any search endpoint retrieves chunks linked to a drug concept (RxNorm source), and the query does not explicitly set `with_safety=false`, the API automatically prepends a `safety_context` object to the response:

```json
{
  "results": [ "...normal query results..." ],
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

1. Resolve the query's top-3 matched concepts.
2. If any matched concept has `source='RXNORM'`, look up its RxCUI.
3. Query `medkb.documents` for chunks with `metadata.rxcui = <X>` AND `metadata.safety_critical = true`.
4. If any exist, include the top-severity warnings in the response's `safety_context` block.
5. Prepending happens at API layer — agents cannot forget to ask.

**Opt-out:** `with_safety=false` skips this logic. The only legitimate reason to opt out is bulk exploratory analysis where safety context would be noise.

**Why default-on:** safety warnings missed are safety warnings violated. Making the default behavior safe and requiring an explicit opt-out for the non-safe path is the correct asymmetry for a medical product. The cost is ~10ms on drug-related queries (one indexed lookup). The payoff is structural — an agent cannot accidentally recommend a drug without the boxed warning reaching it.

### 5f. Error handling

Standard FastAPI exception responses. Specific new error cases:

| Code | Scenario |
|------|----------|
| 400 | Invalid `audience` value; invalid `evidence_level_oxford` value; `as_of_date` in the future; `as_of_date` combined with `current_only=true` contradictorily |
| 404 | Document ID not found (`/v1/cite`, `/v1/history`) |
| 422 | Validation error on request body (FastAPI Pydantic default) |
| 503 | Database connection unavailable; embedding service unavailable |

All errors return a structured JSON body with `error_code`, `message`, and optional `hint` — no raw stack traces.

### 5g. What the API does NOT do (deliberately deferred)

- No `/v1/search/multi-register` that returns both clinician and patient content in one call with cross-register re-ranking. Composable at the agent layer with two calls and a merge; premature until we see how agents actually use it.
- No streaming responses. All responses are batched. LangGraph tool calls don't benefit from streaming at this layer.
- No caching headers. Caching happens at the agent/LangGraph level, not here.
- No authentication changes. Same key-based auth as v2.
- No rate limiting implementation in Phase 4 — document the intended limits (60 req/s per key) in the spec, implement in Phase 5 or later.
- No admin mutation endpoints. The API is read-only. All writes happen via ingestor containers writing directly to the database.

---

## 6. Writing Layer Mechanics

The writing layer is how style rules and exemplars actually flow into DHG agent prompts at inference time. This section is the integration point where the MedKB addendum meets the existing DHG LangGraph agents.

### 6a. The before/after enforcement pattern

Editorial policy gets enforced at **two** points in the agent lifecycle:

| Point | Agent | Mechanism | What it sees |
|-------|-------|-----------|--------------|
| **Before drafting** | `needs_assessment`, `research`, `clinical_practice`, `gap_analysis`, `learning_objectives`, `curriculum_design`, `grant_writer` (all drafting agents) | Retrieval from `medkb.style_rules` + `medkb.style_exemplars`, folded into system prompt | Top-k most-relevant rules (`severity='must'` + `severity='should'`) + 2–3 matching exemplars |
| **After drafting** | `prose_quality_agent` | Query `medkb.style_rules` for `rule_category='banned_phrase'`, apply `pattern` regex to draft output | All active banned-phrase rules with compiled regex |

Same rules, two enforcement points. The "before" pass gives the drafting LLM guardrails so it writes cleanly the first time. The "after" pass catches anything the drafting LLM ignored or that a newly-added rule would now flag.

### 6b. Prompt assembly flow (before-drafting pass)

This is the new code path added to every drafting agent's graph node. Pseudo-code:

```python
# Inside a LangGraph @traced_node for, e.g., needs_assessment_agent
async def draft_cold_open(state: NeedsAssessmentState) -> dict:
    topic = state["topic"]
    audience = state.get("target_audience", "clinician")

    # 1. Retrieve rules relevant to THIS section
    rules_resp = await medkb_client.post("/v1/search/rules", json={
        "query": f"cold open narrative {topic}",
        "audience_scope": [audience],
        "severity": ["must", "should"],
        "limit": 10,
    })

    # 2. Retrieve exemplars matching the register we want
    exemplars_resp = await medkb_client.post("/v1/search/exemplars", json={
        "query": f"patient vignette {topic}",
        "audience_tag": audience,
        "register_tag": "narrative",
        "limit": 3,
    })

    # 3. Assemble prompt
    system_prompt = build_needs_cold_open_prompt(
        topic=topic,
        rules=rules_resp["results"],
        exemplars=exemplars_resp["results"],
    )

    # 4. Call LLM with assembled prompt
    draft = await llm.ainvoke(system_prompt)
    return {"cold_open_draft": draft.content}
```

**Prompt template structure** (assembled by `build_needs_cold_open_prompt`):

```
You are drafting the cold-open narrative for a CME grant application on {topic}.

[EDITORIAL RULES — follow these strictly]
Must never:
  - {rule_1.rule_text}  (source: {rule_1.source})
  - {rule_2.rule_text}  (source: {rule_2.source})
Should avoid:
  - {rule_3.rule_text}  (source: {rule_3.source})
  - ...

[VOICE EXEMPLARS — write in this register]
Example 1 ({exemplar_1.source}, {exemplar_1.register_tag}):
> {exemplar_1.chunk_text}

Example 2 ({exemplar_2.source}):
> {exemplar_2.chunk_text}

[TASK]
Write a 150–200 word cold open that opens with a patient vignette...
```

### 6c. `prose_quality_agent` modification (after-drafting pass)

**Current state** (`prose_quality_agent.py` lines 39–67): `BANNED_PATTERNS` is a hardcoded Python list of 27 regex/description pairs. The agent compiles them at module load and applies them to every draft.

**Phase 4 change:** replace the hardcoded list with a startup query to `medkb.style_rules`.

```python
# prose_quality_agent.py — new module init
_BANNED_PATTERNS_CACHE: list[CompiledRule] | None = None
_CACHE_TIMESTAMP: float = 0.0
_CACHE_TTL_SECONDS = 300  # 5 minutes

async def get_banned_patterns() -> list[CompiledRule]:
    global _BANNED_PATTERNS_CACHE, _CACHE_TIMESTAMP
    now = time.monotonic()
    if _BANNED_PATTERNS_CACHE is not None and (now - _CACHE_TIMESTAMP) < _CACHE_TTL_SECONDS:
        return _BANNED_PATTERNS_CACHE

    resp = await medkb_client.post("/v1/search/rules", json={
        "query": "",  # empty query = return all, ordered by rule_name
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
        if r.get("pattern")  # after-pass only uses rules with a regex
    ]
    _CACHE_TIMESTAMP = now
    return _BANNED_PATTERNS_CACHE
```

**Properties of this design:**

- **5-minute TTL cache** — adding a new banned phrase propagates within 5 minutes across all running agent pods without a restart.
- **Regex-only filter** — the after-pass only applies rules that have a compiled `pattern`. Rules with only `rule_text` (AMA style, PLAIN readability) are before-pass-only.
- **Graceful degradation on MedKB failure** — if the MedKB query fails, fall back to a locally-stored snapshot of the last-known-good rule set committed to the repo as `prose_quality_agent/fallback_rules.json`. The agent logs a warning but keeps running. [UNCERTAIN — RESOLVE AT REVIEW: do we want fallback, or do we want a hard fail that wedges the pipeline until MedKB is back? Hard fail is more consistent with the production rules, graceful fallback is more consistent with the observability-first philosophy.]
- **Empty `query`** — `/v1/search/rules` with empty query returns all rules in the category, unsorted by similarity. This is intentional for the after-pass: it wants the full set, not the most-relevant subset.

### 6d. Retrieval strategies per agent

Not every drafting agent needs the same rule/exemplar mix. Per-agent defaults:

| Agent | Rules retrieved | Exemplars retrieved | Notes |
|-------|-----------------|---------------------|-------|
| `needs_assessment` | Top 10 rules (`must`+`should`), `audience_scope` matches state | 3 narrative exemplars for cold open; 2 explanatory for gap sections | Cold open is the highest-stakes prose in a grant |
| `research` | Top 8 rules including `citation_format` category | 2 authoritative exemplars | Research section is citation-heavy; cite format rules matter most |
| `clinical_practice` | Top 8 rules | 2 explanatory exemplars | Standard-of-care framing; neutral authoritative voice |
| `gap_analysis` | Top 8 rules | 2 explanatory exemplars | Quantification-heavy — AMA number rules matter |
| `learning_objectives` | Top 5 rules focused on `structure` category | 0 exemplars | LOs are structural, not stylistic |
| `curriculum_design` | Top 8 rules | 2 instructional exemplars | Educational design; instructional voice |
| `grant_writer` (assembly) | Top 15 rules (broadest retrieval) | 3 exemplars matching target audience | Assembles final doc; needs the most coverage |

These are **defaults**, not hardcoded constants. Each agent's retrieval parameters live in its own config (e.g., `needs_assessment_config.py`) so tuning one agent doesn't touch others.

### 6e. Token budget impact

Rules + exemplars add tokens to every drafting call. Budget:

| Component | Estimated tokens per draft call | Notes |
|-----------|--------------------------------|-------|
| Rule block (10 rules × ~30 tokens each) | ~300 | Short rule text is a design goal for this reason |
| Exemplar block (3 exemplars × ~400 tokens each, 512-token chunks) | ~1,200 | Exemplars dominate the budget |
| Overhead (section headers, instructions) | ~200 | |
| **Total writing-layer overhead per drafting node** | **~1,700 tokens** | On top of existing agent prompt |

Claude Sonnet's 200K context easily absorbs this. The concern is **cost**, not capacity. At current Sonnet rates and ~85 drafting nodes per full grant pipeline, the writing layer adds roughly `85 × 1,700 / 1000 × $0.003 ≈ $0.43` per grant run for the additional input tokens. Stephen's billing rate ($600/hr) makes this a rounding error. Documented here for completeness, not as a concern.

### 6f. Caching and hot-reload

- **Rules cache** — 5-minute TTL in every drafting agent. Hot-adds a new rule within 5 minutes of insertion. No agent restart.
- **Exemplars** — **not cached** in agents. Every drafting call does a fresh retrieval because the relevance query is different each time (topic-dependent).
- **Embeddings** — the ~47 rule embeddings and ~500 Phase 4 exemplar embeddings all fit in a single HNSW index in memory. Retrieval latency target: <15ms p95 for both `/v1/search/rules` and `/v1/search/exemplars`.

### 6g. Rollout order for the writing layer

This is the order DHG agents get modified during Phase 4. **Critical — do not parallelize.**

1. **`prose_quality_agent`** gets the query-`style_rules`-at-startup change first, with fallback to hardcoded patterns if MedKB returns zero rules. This is the safest change because the agent already knew the 27 patterns.
2. **Seed `medkb.style_rules`** with the 47 Phase 4 rules, verify `prose_quality_agent` queries them correctly, then **remove** the hardcoded `BANNED_PATTERNS` list from the Python source. The remove-hardcoded step is a separate commit so it can be reverted in isolation if the query path breaks.
3. **`needs_assessment_agent`** gets the before-drafting retrieval next. It's the highest-stakes prose (cold open) and will surface writing-layer quality issues fastest.
4. **Iterate on rule/exemplar retrieval quality** using `needs_assessment` as the test bed. Tune `limit` parameters, prompt assembly, exemplar selection. Do NOT touch other agents during this phase.
5. **`grant_writer_agent`** gets the before-drafting retrieval next. It's the final assembly and benefits from the broadest rule coverage.
6. **Remaining agents** (`research`, `clinical_practice`, `gap_analysis`, `learning_objectives`, `curriculum_design`) get the retrieval in a single batch once tuning is stable.

**Each step includes a side-by-side A/B evaluation** — run the same 3 reference topics through the agent with and without the writing-layer retrieval, compare outputs with `prose_quality_agent` scoring. Only proceed to the next step when the writing-layer variant scores equal-or-better than the baseline.

---

## 7. Ingestor Architecture

Every Phase 4 and Phase 5 source gets ingested by a `SourceIngestor` subclass. The base class handles the common concerns — chunking, embedding, upserts, concept reconciliation, error logging — so per-source subclasses stay small (~100–300 lines each).

### 7a. Base class — `SourceIngestor`

```python
# ingestors/base.py
class SourceIngestor(ABC):
    source_name: str                    # 'USPSTF', 'DailyMed', 'CDC', ...
    source_authority: Literal[...]      # 'guideline_body' | 'regulatory' | ...
    default_audience: Literal[...]      # 'clinician' | 'patient' | 'mixed'
    writes_to: Literal["documents", "style_exemplars"]

    @abstractmethod
    async def discover(self) -> AsyncIterator[SourceItem]:
        """Yield metadata records for each item to ingest (URL, ID, version)."""

    @abstractmethod
    async def fetch(self, item: SourceItem) -> RawDocument:
        """Download and parse a single item to RawDocument."""

    @abstractmethod
    def chunk(self, doc: RawDocument) -> list[Chunk]:
        """Split a RawDocument into chunks appropriate for this source."""

    async def run(self) -> IngestReport:
        """Template method — do not override. Drives discover/fetch/chunk/embed/upsert."""
        ...
```

The `run()` template method handles the common pipeline so subclasses only implement the source-specific steps. This template is the single place where we:

1. Compute embeddings (PubMedBERT via the existing embedding service)
2. Assign derived fields (`readability_grade` via `textstat`, `source_authority` from class attribute, `audience` from heuristic or class default)
3. Reconcile concepts (look up RxCUI/MeSH IDs; log unmapped to `{source}_unmapped.log`)
4. Detect supersession (query for existing same-topic records; write `valid_to` + `supersedes` edge)
5. Upsert to target table via idempotent `ON CONFLICT` clause keyed on `(source, metadata->>'source_id')` [UNCERTAIN — RESOLVE AT REVIEW: this requires a unique index on `source + metadata->>'source_id'`. Does v2 already have one? If not, the Phase 4 migration needs to add it. Verify against v2 brief before finalizing.]
6. Emit structured logs to Loki + Prometheus counters (`medkb_ingest_items_total{source,outcome}`)

### 7b. Concept reconciliation strategy

Per-source concept lookup rules, encoded on each subclass:

| Source | Lookup key | Target concept table | Unmapped behavior |
|--------|------------|----------------------|-------------------|
| USPSTF | Topic → MeSH (heuristic match on topic string) | `medkb.concepts WHERE source='MESH'` | Log to `uspstf_unmapped.log`, ingest anyway |
| DailyMed | `rxcui` from SPL XML | `medkb.concepts WHERE source='RXNORM'` | Log to `dailymed_unmapped.log`, ingest anyway |
| MedlinePlus | `mesh_id` from XML | `medkb.concepts WHERE source='MESH'` | Log to `medlineplus_unmapped.log`, ingest anyway |
| CDC handouts | Manual `topic_tags` (hand-curated) | N/A — exemplars don't link to concepts | No log |

**Rule:** never create orphan concepts at ingest time. If a source mentions a concept we don't already have from MeSH or RxNorm, the chunk is still ingested and the missing concept is logged for human review. This prevents an ingestor from polluting the concept table with bad data.

### 7c. Per-source subclass pattern

Example — the USPSTF ingestor in full:

```python
# ingestors/uspstf.py
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

    async def fetch(self, item: SourceItem) -> RawDocument:
        json = await self._get_json(item.url)
        return RawDocument(
            title=json["title"],
            sections={
                "recommendation": json["recommendation_text"],
                "rationale": json["rationale_text"],
                "clinical_considerations": json["clinical_considerations"],
                "supporting_evidence": json["evidence_summary"],
            },
            valid_from=json["publication_date"],
            version_label=json.get("version_label"),
            metadata={**item.metadata, "uspstf_grade": json["grade"]},
        )

    def chunk(self, doc: RawDocument) -> list[Chunk]:
        # Section-level — do not sub-chunk.
        return [
            Chunk(text=text, index=i, section=section_name)
            for i, (section_name, text) in enumerate(doc.sections.items())
            if text and text.strip()
        ]
```

All the embedding, concept reconciliation, supersession detection, and upsert logic happens in the base class `run()` template. The subclass is ~50 lines and covers only the source-specific discover/fetch/chunk.

### 7d. Error handling and observability

Every ingestor run produces a structured report written to `medkb_ingest_reports` (new table, see §8b) and emits Prometheus counters:

```
medkb_ingest_items_total{source="USPSTF", outcome="ingested"}         count of chunks written
medkb_ingest_items_total{source="USPSTF", outcome="skipped_existing"} count of no-ops due to idempotency
medkb_ingest_items_total{source="USPSTF", outcome="unmapped_concept"} count of ingested-but-unmapped items
medkb_ingest_items_total{source="USPSTF", outcome="error_fetch"}      count of HTTP/parse failures
medkb_ingest_items_total{source="USPSTF", outcome="error_chunk"}      count of chunking failures
medkb_ingest_duration_seconds{source="USPSTF"}                        histogram
```

Grafana dashboard panel per source shows: items/sec, error rate, cumulative chunks, last-run timestamp. Alertmanager rule fires if error rate > 5% on any source for > 15 minutes.

### 7e. Scheduling

Each ingestor runs as a separate Docker container with its own cron-like scheduler:

| Source | Cadence | Rationale |
|--------|---------|-----------|
| USPSTF | Weekly | Low update frequency |
| DailyMed | Daily (delta) | FDA publishes rolling updates |
| MedlinePlus | Weekly | Updated in place, polling is cheap |
| CDC handouts | Monthly | Low update frequency |
| Style rules (migration script) | One-time + on-demand | Not a recurring ingest |
| Style exemplars | Monthly (curation review) | Human-gated additions |

All ingestors share the same base container image (`dhg-medkb-ingestor`) and differ only by the `INGESTOR_CLASS` env var, so ops overhead scales sub-linearly with source count.

### 7f. Incremental vs full re-ingest

Every ingestor supports both modes via a CLI flag:

```
python -m ingestors.run --source=USPSTF --mode=incremental
python -m ingestors.run --source=USPSTF --mode=full
```

- **Incremental** (default) — only fetch items whose `source_id` is not already in the DB, or whose `version_label` differs from the stored version.
- **Full** — re-fetch everything. Used after a parser fix or when a source's chunking strategy changes. Full mode re-computes embeddings and re-upserts; the idempotent upsert handles duplicate detection at the DB layer so nothing gets orphaned.

### 7g. What's NOT in the ingestor layer

- **No streaming ingestion.** Sources are batch-polled, not streamed. Phase 4 and 5 have no real-time requirement.
- **No distributed coordination.** One ingestor container per source at a time. If a source needs parallelism in Phase 5 (e.g., full DailyMed fan-out across 120K labels), the `run()` template can dispatch work to an internal `asyncio.Queue` with N workers, but we don't build a multi-container orchestration layer.
- **No per-source Airflow/Prefect.** Docker compose + cron is sufficient. Revisit only if ingestor count exceeds ~20.

---

## 8. Migration, Backfill & Rollback Plan

### 8a. Migration order (production execution)

The migration runs against the live `medkb` database. Each step is independently reversible before the next step runs.

| Step | Action | Reversible via |
|------|--------|----------------|
| 1 | `alembic upgrade medkb_004` — DDL for `ALTER TABLE medkb.documents` (2a) + CHECK constraints | `alembic downgrade medkb_003` (drops new columns) |
| 2 | `alembic upgrade medkb_005` — `CREATE TABLE medkb.style_rules` (2b) | `DROP TABLE medkb.style_rules` |
| 3 | `alembic upgrade medkb_006` — `CREATE TABLE medkb.style_exemplars` (2c) | `DROP TABLE medkb.style_exemplars` |
| 4 | `alembic upgrade medkb_007` — `CREATE TABLE medkb.ingest_reports` (see 8b) | `DROP TABLE medkb.ingest_reports` |
| 5 | `CREATE INDEX CONCURRENTLY` for all HNSW indexes (runs outside transaction) | `DROP INDEX CONCURRENTLY` |
| 6 | `python scripts/backfill_v2_documents.py --dry-run` | N/A (read-only) |
| 7 | `python scripts/backfill_v2_documents.py --commit` | Idempotent — re-runnable |
| 8 | `python scripts/seed_style_rules.py` — loads 47 Phase 4 rules | `DELETE FROM medkb.style_rules WHERE source IN ('DHG_BANNED_PATTERNS','AMA_Manual','PLAIN')` |
| 9 | `python scripts/seed_cdc_exemplars.py` — loads 20 CDC pieces | `DELETE FROM medkb.style_exemplars WHERE source = 'CDC'` |
| 10 | Deploy `prose_quality_agent` with query-style-rules-at-startup + fallback | Revert the agent commit |
| 11 | Verify `prose_quality_agent` is reading from DB (check logs for `medkb_rules_loaded` event) | N/A |
| 12 | Deploy `needs_assessment_agent` with writing-layer retrieval | Revert the agent commit |
| 13 | A/B eval vs baseline (see §9f) | N/A |
| 14 | Deploy remaining drafting agents with writing-layer retrieval (batch) | Revert individual commits |

Steps 1–9 land as a single PR. Steps 10–14 land as a sequence of PRs, each gated on the A/B eval passing.

### 8b. New table for ingest observability

```sql
CREATE TABLE medkb.ingest_reports (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name    TEXT NOT NULL,
    started_at     TIMESTAMPTZ NOT NULL,
    ended_at       TIMESTAMPTZ,
    mode           TEXT NOT NULL,       -- 'incremental' | 'full'
    items_ingested INT DEFAULT 0,
    items_skipped  INT DEFAULT 0,
    items_errored  INT DEFAULT 0,
    unmapped_count INT DEFAULT 0,
    error_summary  JSONB,               -- first 10 errors for post-mortem
    CONSTRAINT ingest_reports_mode_check
        CHECK (mode IN ('incremental','full'))
);

CREATE INDEX ON medkb.ingest_reports (source_name, started_at DESC);
```

This gives ops a single-table audit trail of every ingest run across all sources, plus a place for Grafana to query recent state.

### 8c. Backfill script specifics

`scripts/backfill_v2_documents.py` — runs after step 4 above.

**Preconditions checked before write:**

1. Target column exists (`audience`, `evidence_level_oxford`, `readability_grade`, `source_authority`).
2. No existing rows already have `audience IS NOT NULL` unless `--force` is passed. (Idempotency guard.)
3. `textstat` library importable.

**Batch size:** 1,000 rows per transaction. Progress logged every batch. Estimated runtime for v2 Phase 1 corpus (~200K PubMed chunks): ~15 minutes on g700data1.

**Failure modes:**

- **Unknown `publication_type`** — logged, row left with `evidence_level_oxford = NULL`, not failed.
- **Empty `chunk_text`** — logged, row left with `readability_grade = NULL`, not failed.
- **DB transaction error** — batch rolls back, script retries up to 3 times before aborting. Idempotent on retry.

### 8d. Rollback plan

A rollback at each step of §8a reverses cleanly because:

- New columns are nullable → dropping them loses only the backfilled values, not any v2 Phase 1 data.
- New tables are isolated → dropping them doesn't touch v2 Phase 1 tables.
- HNSW indexes are reproducible from source data → dropping an index costs only re-index time, not data.
- Seed scripts are idempotent → re-running after a rollback + re-migration produces identical state.
- Agent deploys are reverted via git commit revert → no data-layer rollback needed for agent changes.

**The one operation without a safe rollback** is the removal of hardcoded `BANNED_PATTERNS` from `prose_quality_agent.py` (step 2 of §6g). After that commit, the agent depends on `medkb.style_rules` being seeded. Mitigation:

- Keep a `fallback_rules.json` committed to the agent repo containing a snapshot of the 27 DHG banned patterns.
- The agent's `get_banned_patterns()` function falls back to this JSON file if the MedKB query fails and the cache is empty.
- The fallback is logged as a WARNING (visible in Grafana) so ops notices if the fallback path is activating.

### 8e. Production execution checklist

Before running the migration in production:

- [ ] Run full migration sequence on a copy of the production DB (staging restore from prod backup)
- [ ] Verify HNSW index build completes without OOM on the 64GB RAM server
- [ ] Verify backfill script completes within the 20-minute maintenance window
- [ ] Verify `prose_quality_agent` with fallback serves traffic correctly when `style_rules` table is empty
- [ ] Confirm rollback path works end-to-end on staging
- [ ] Snapshot production DB before step 1
- [ ] Have a revert PR pre-written for each agent deploy (steps 10, 12, 14)

---

## 9. Test Plan, Acceptance Criteria & Phase Exit Gates

### 9a. Test layers

| Layer | Scope | Framework | Gate |
|-------|-------|-----------|------|
| Unit | Pure functions (citation formatting, chunking, regex compilation, field mapping) | pytest | 100% line coverage on `api/citations.py`, `ingestors/base.py` chunking utilities |
| Ingestor integration | Each ingestor against a fixture corpus | pytest + HTTP recording (vcrpy) | Every ingestor has ≥1 full-ingest test against 3+ recorded items |
| API integration | Each new endpoint against a seeded test DB | pytest + httpx `AsyncClient` | Every endpoint has a happy-path test + at least 2 error cases |
| Migration integration | Alembic up/down cycle, backfill idempotency | pytest-postgresql | Full up/down/up cycle passes |
| End-to-end | `needs_assessment_agent` drafting with full writing-layer retrieval against real MedKB | pytest + real LangGraph dev server | One golden-path run per agent, compared to baseline on reference topics |
| Playwright | No UI changes in this addendum — n/a | — | — |

### 9b. Per-phase exit gates

**Phase 4 (anchor sources) exit gate — all must be green before Phase 5 starts:**

- [ ] All 5 anchor sources ingested end-to-end (USPSTF ~120 guidelines, DailyMed ~200 drugs, MedlinePlus ~1,000 topics, 47 style rules, 20 CDC exemplars)
- [ ] `medkb.ingest_reports` shows 0 fatal errors for each source's most recent run
- [ ] `medkb.documents` row count increased by expected delta (~8,000 new rows); `medkb.style_rules` = 47; `medkb.style_exemplars` = ~400 chunks
- [ ] USPSTF supersession chain test verified: 2023 lung cancer record supersedes 2021, both queryable via `as_of_date`
- [ ] DailyMed boxed warning test verified: `/v1/drug/{rxcui}/safety` returns metformin's lactic acidosis warning for RxCUI 6809
- [ ] `/v1/search/guidelines` returns USPSTF lung cancer screening for query "lung cancer screening eligibility" with similarity > 0.7
- [ ] `/v1/search/rules` returns relevant AMA rule for query "drug name generic brand" with `severity='should'`
- [ ] `/v1/search/exemplars` returns a CDC diabetes piece for query "explaining A1C" with `register_tag='explanatory'`
- [ ] `/v1/cite/{document_id}` returns correctly-formatted AMA citations for one sample per citation type (journal, guideline, label, consumer, preprint, reference)
- [ ] `prose_quality_agent` reads banned patterns from `medkb.style_rules` in production (log verification: `medkb_rules_loaded rules_count=27`)
- [ ] `needs_assessment_agent` drafts cold open using retrieved rules + exemplars (log verification: `writing_layer_retrieval rules=10 exemplars=3`)
- [ ] A/B eval passes: `needs_assessment_agent` with writing-layer retrieval scores equal-or-better on 3 reference topics vs baseline, measured by `prose_quality_agent` score
- [ ] No regression in `prose_quality_agent` banned-pattern catch rate (the same draft that was caught before is still caught after the DB migration)
- [ ] Grafana dashboards show all 6 ingestors reporting; no alerts firing
- [ ] Migration rollback tested on staging and documented

**Phase 5 (fan-out) exit gate — applied incrementally per sub-phase:**

Each Phase 5 sub-phase in §4f has its own exit gate that mirrors the Phase 4 structure: ingested, verified via sample query, integrated into at least one agent retrieval path, no regression in existing retrievals. Sub-phase N cannot start until sub-phase N-1's gate is green.

### 9c. Regression guards

The addendum must not break v2 Phase 1 behavior. Regression tests pin:

- v2-shaped requests to `/v1/search/semantic` return v2-shaped responses (extra fields present but v2 clients ignoring them behave identically)
- `/v1/search/literature` latency remains within 1.1× v2 baseline
- PubMed chunk retrieval quality on the v2 golden test set (top-10 similarity scores) stays within ±0.02 of v2 baseline after backfill

### 9d. Performance targets

| Metric | Target | Measured by |
|--------|--------|-------------|
| `/v1/search/guidelines` p95 latency | < 80 ms | Prometheus histogram |
| `/v1/search/rules` p95 latency | < 15 ms | Prometheus histogram |
| `/v1/search/exemplars` p95 latency | < 20 ms | Prometheus histogram |
| `/v1/cite/{document_id}` p95 latency | < 10 ms | Prometheus histogram |
| `/v1/drug/{rxcui}/safety` p95 latency | < 30 ms | Prometheus histogram |
| Safety-context prepending overhead on drug queries | < 15 ms | Histogram delta |
| Writing-layer token overhead per drafting node | < 2,000 tokens | LangSmith trace inspection |
| Drafting node latency impact | < 1.2× baseline | LangSmith trace comparison |

### 9e. Safety / compliance tests

These are **must-pass** regardless of other priorities:

- [ ] License CHECK constraint test: attempting to insert a `style_exemplar` with `license='copyrighted'` raises a DB-level constraint error (not just an application-level check)
- [ ] Boxed warning presence test: every drug in the Phase 4 anchor set that has a boxed warning in its DailyMed SPL has `metadata.safety_critical=true` on at least one of its chunks
- [ ] Boxed warning retrieval test: `/v1/drug/{rxcui}/safety` for every boxed-warning drug in the anchor set returns the boxed warning (not just contraindications)
- [ ] Temporal integrity test: for every `supersedes` edge in the DB, the source record's `valid_from` ≥ the target record's `valid_from` (a newer version can't predate the older one)
- [ ] Citation correctness test: a random sample of 10 generated citations across each citation_type are validated by hand against the AMA Manual of Style canonical format
- [ ] Public domain verification test: every ingested CDC piece has an explicit `public_domain` license tag; any piece without passes fails the test

### 9f. A/B evaluation protocol for writing-layer rollout

Used at step 13 of §8a and repeated for each agent in the writing-layer rollout.

**Setup:**

1. Select 3 reference topics covering diverse domains (e.g., NSCLC screening, type 2 diabetes management, heart failure readmission).
2. For each topic, run the agent **twice**:
   - **Baseline:** writing-layer retrieval disabled via a feature flag.
   - **Treatment:** writing-layer retrieval enabled.
3. Collect both outputs plus `prose_quality_agent` scores for each.

**Acceptance criteria for the treatment variant:**

- `prose_quality_agent` banned-phrase count ≤ baseline
- `prose_quality_agent` overall quality score ≥ baseline − 0.02 (tolerance for natural variance)
- Subjective read by Stephen confirms the treatment variant is at least as readable as baseline, with no new stylistic issues
- No new hallucinations introduced (spot-check any factual claim that appears in treatment but not baseline)

**Failure action:** if any criterion fails, the writing-layer retrieval for that agent is rolled back, the prompt template is retuned, and the A/B is re-run. Do NOT proceed to the next agent's rollout until the current one passes.

---

## 10. Open Questions & Items Flagged for Review

Items flagged `[UNCERTAIN]` inline throughout the spec, consolidated here for the review gate:

1. **§6c — `prose_quality_agent` fallback behavior.** Do we want graceful fallback to a committed `fallback_rules.json` when MedKB is unavailable, or a hard fail that wedges the pipeline until MedKB returns? Argument for fallback: consistency with observability-first philosophy, agents keep shipping grants. Argument for hard fail: consistency with production rules (no silent degradation), forces ops to fix MedKB immediately. **My recommendation:** graceful fallback with a prominent Grafana alert when the fallback path activates — the fail-loud-but-don't-wedge default.

2. **§7a — idempotent upsert key.** The `ON CONFLICT (source, metadata->>'source_id')` clause requires a unique index on `(source, (metadata->>'source_id'))`. Does v2 already have this index? If not, the Phase 4 migration needs to add it. Verify against the v2 brief before finalizing the migration script.

3. **§6e — token budget impact is documented but not gated.** Should we add a latency/cost gate to §9d that fails the Phase 4 exit if drafting node latency exceeds some threshold, or is "A/B eval passes" sufficient? **My recommendation:** the < 1.2× baseline target in §9d is sufficient; no separate cost gate needed at this phase.

4. **§3c — MedlinePlus temporal unavailability.** Acknowledged as a documented limitation. Do we want to surface a more prominent warning in the API response when a user queries `/v1/search/patient` with `as_of_date` against MedlinePlus-only results, or is the `temporal_unavailable: true` flag sufficient? **My recommendation:** the flag is sufficient; adding a HTTP warning header would be over-engineering at Phase 4 scale.

5. **§4 — NCCN/NICE exclusion.** Phase 6 revisit was agreed in Section 4 discussion. Should this spec mention Phase 6 explicitly as a placeholder, or is it cleaner to leave Phase 6 entirely out of this document and defer to a separate spec? **My recommendation:** leave out of this document — mentioning Phase 6 here invites scope creep into the Phase 4/5 addendum.

---

## 11. Appendix — Cross-References

- **v2 brief** (Phase 1 concepts/relationships/documents spec) — `docs/superpowers/specs/[v2-brief-file].md` [UNCERTAIN — RESOLVE AT REVIEW: exact filename not verified in this draft; locate and link at review time]
- **DHG prose_quality_agent** — `langgraph_workflows/dhg-agents-cloud/src/prose_quality_agent.py` (lines 39–67 for `BANNED_PATTERNS`)
- **DHG tracing** — `langgraph_workflows/dhg-agents-cloud/src/tracing.py` (`@traced_node` decorator used throughout)
- **MedKB client in agents** — to be created at `langgraph_workflows/dhg-agents-cloud/src/medkb_client.py` as part of Phase 4 step 10 (§8a)
- **Registry API for DHG-side auth/observability** — `registry/api.py` (separate from MedKB API; they do not interact directly)

---

## 12. Deferred for Future Addenda

Explicitly NOT in this spec, listed so future work doesn't duplicate the decision:

- Multi-format citation (APA, Vancouver, MLA) — deferred until a concrete CME reviewer or journal requires it
- Streaming API responses — deferred indefinitely; agents don't benefit at this layer
- NCCN/NICE licensing negotiation — Phase 6 at earliest
- Full-text Cochrane — separate institutional-license workstream
- MIMIC-IV / MedAlpaca — v2 Phase 3 (separate addendum)
- Rate limiting enforcement — document in Phase 4, implement in Phase 5+
- Admin mutation API endpoints — not planned; ingestors write directly to DB
- Fine-tuning or parameter updates based on style exemplars — explicitly rejected; the addendum composes exemplars into prompts, not weights
- Cross-register re-ranking endpoint — premature until agent usage patterns are observed

---

*End of spec. Next step: spec review by Stephen at the review gate, then invoke the `superpowers:writing-plans` skill to produce the implementation plan.*
