# CME Video Transcription Pipeline: Architecture Specification

**Date:** 2026-05-23
**Machines:** dh40801 (10.0.0.179, RTX 4080 16GB, 64GB RAM) + g700data1 (10.0.0.251)
**Prerequisite:** dh40801 server setup (docs/superpowers/plans/2026-05-19-dh40801-kb-server-setup.md)
**Status:** Draft — awaiting review

---

## What It Does

Processes recorded CME (Continuing Medical Education) video lectures into structured, searchable, medical-grade transcription documents. The archive contains 500+ lectures.

**Scope boundaries:**
- DOES build the processing pipeline on dh40801
- DOES create registry tables + API on g700data1 for storing/searching results
- DOES NOT build the Haystack retrieval API (separate project)
- DOES NOT replace the medkb ingestor pipeline (separate)
- Prerequisite: dh40801 server setup must complete first (Phase 0)

---

## Patterns and Conventions (from codebase exploration)

The codebase has a rigidly consistent five-layer memreg pattern:

1. **Migration** (`registry/alembic/versions/NNN_*.py`): UUID PK via `gen_random_uuid()`, TSVECTOR column, Vector(768) column, GIN indexes on both, auto-update trigger function wired as BEFORE INSERT OR UPDATE trigger. Unique constraint on `(project_name, <title_field>)` for upsert idempotency.

2. **SQLAlchemy Model** (`registry/models.py`): Legacy declarative Base (not mapped_column style — that is medkb only). `JSONB` for `meta_data`. `ARRAY(Text)` for tags and file lists. `onupdate=func.now()` on `updated_at`.

3. **Service layer** (`registry/*_service.py`): `upsert_by_unique_constraint`, `list_with_filters`, `search_fts`, `delete`. IntegrityError catch-and-retry on race condition. Embedding passed in as optional parameter; service never calls Ollama itself — the endpoint does.

4. **Endpoints** (`registry/*_endpoints.py`): `APIRouter` with prefix, Prometheus instrumentation from `registry/metrics.py` (same 5 metrics everywhere), embedding generation via `embedding_utils.get_embedding()` fired before upsert, validation of enum fields before DB call.

5. **Schemas** (`registry/*_schemas.py`): `Create` / `Response` / `List` / `Search` — same four schema pattern for every domain.

The kb_service.py hybrid search (RRF over FTS + vector, `_RRF_K=60`) is the unified search layer. Every new domain table should register an extractor there to become KB-searchable.

The download_jobs worker (`services/pdf-renderer/worker.py`) uses `FOR UPDATE SKIP LOCKED` + polling loop + scope-dispatched handlers — this is the established pattern for durable async job processing.

---

## Architecture Decision: Chosen Approach

**Processing model: dh40801-resident Docker service with stateful job queue + synchronous push to g700data1 registry API.**

dh40801 runs a containerized `dhg-transcription-pipeline` service. Each lecture is enqueued as a job in a local SQLite queue. The pipeline processes jobs sequentially to stay within VRAM limits, produces structured output, then POSTs the result to `http://10.0.0.251:8011/api/cme/transcriptions` on g700data1.

**Rationale:** Sequential processing is the right choice because the VRAM budget (analyzed below) requires model swapping between pipeline stages. A queue-based approach makes every failure recoverable and every result idempotent. Posting to the existing registry API avoids creating a second database access path and lets the existing KB search (kb_service.py) index transcriptions immediately.

---

## VRAM Budget (RTX 4080, 16GB)

All models cannot run simultaneously. The pipeline uses a load-on-demand pattern: each stage loads its model, runs to completion, releases VRAM before the next stage loads.

| Stage | Model | VRAM Required | Notes |
|-------|-------|---------------|-------|
| Scene detection | moondream2 (2B VLM) | ~2.5GB | Lightweight multimodal for frame classification |
| ASR | WhisperX large-v3 | ~3.0GB | float16 on CUDA |
| Diarization | pyannote/speaker-diarization-3.1 | ~1.5GB | Runs concurrently with WhisperX, then released |
| Medical NLP | scispacy en_core_sci_lg + custom | ~0.5GB CPU | CPU-only; no GPU needed |
| Embedding | nomic-embed-text (Ollama) | ~0.3GB | Ollama manages separately |

**Peak stage budget: ~4.5GB** (WhisperX + pyannote loaded together during diarization).
**Remaining headroom: ~11.5GB** after peak.

Sequential stage constraint: Scene detection completes and model is released before ASR loads. ASR + diarization run together (both needed simultaneously). Medical NLP runs CPU-side while embeddings are generated.

**VRAM model unloading**: Use `del model; torch.cuda.empty_cache()` at end of each stage function — do not rely on Python garbage collection for GPU memory. Test with `nvidia-smi --query-gpu=memory.used --format=csv` between stages.

---

## Pipeline Stages (Detailed)

### Stage 0: Job Intake
- **Input:** Video file path (absolute path on dh40801), lecture metadata (title, date, speakers list, CME topic)
- **Action:** Validate file exists, extract basic metadata via `ffprobe` (duration, resolution, audio channels), insert job row with `status=pending`
- **Output:** `job_id` UUID
- **Tool:** `ffprobe` (subprocess), no GPU

### Stage 1: Audio Extraction
- **Input:** Video file path
- **Action:** `ffmpeg -i input.mp4 -vn -ar 16000 -ac 1 -c:a pcm_s16le output.wav`
- **Output:** 16kHz mono WAV on local scratch disk (`/tmp/dhg-transcription/{job_id}/audio.wav`)
- **Tool:** `ffmpeg` (subprocess), no GPU
- **Rationale:** WhisperX expects 16kHz mono; extracting upfront avoids video decoding overhead during ASR

### Stage 2: Frame Extraction for Scene Detection
- **Input:** Video file
- **Action:** Extract 1 frame per 2 seconds using ffmpeg (`-vf fps=0.5`), write to `/tmp/dhg-transcription/{job_id}/frames/`
- **Output:** JPEG frames at 2-second intervals
- **Tool:** `ffmpeg` (subprocess), no GPU
- **Rationale:** 2-second resolution is sufficient to detect scene transitions (slides change at presentation pace, not sub-second)

### Stage 3: Scene Classification (GPU)
- **Input:** Frame directory
- **Action:** Load moondream2 via `transformers`. For each frame, run inference with prompt: `"Classify this frame as one of: [faculty_on_camera, presentation_slide, lower_third, chart_or_graphic, broll_transition]. Describe any text visible on slide titles or name/title lower thirds."`
- **Output:** List of `{timestamp_seconds, scene_type, description, slide_title_if_visible, speaker_name_if_lower_third}` dicts
- **Tool:** `moondream2` (HuggingFace `transformers`, CUDA)
- **Post-process:** Merge adjacent frames with same scene_type into scene segments (collapse runs)
- **VRAM:** Load, run all frames, unload before Stage 4

**Why moondream2 over CLIP or OCR-only:** moondream2 (2B parameter VLM) can simultaneously classify the scene type AND extract text from slides/lower thirds in a single inference pass. CLIP cannot read text. Pure OCR (Tesseract/EasyOCR) would require a separate classification step. moondream2 fits in ~2.5GB making it the most practical choice for this VRAM budget.

**Batch inference:** Do not call moondream2 frame-by-frame in a Python loop — use batch inference with `batch_size=32` for the GPU inference pass. At 0.5fps for a 90-minute lecture = 2,700 frames. Batch processing at 32 frames/batch = 85 GPU calls at ~0.1s each = ~9 seconds total.

### Stage 4: ASR + Diarization (GPU)
- **Input:** `audio.wav`
- **Action:**
  1. Load WhisperX `large-v3` model (float16, CUDA)
  2. Transcribe with `word_timestamps=True`, `batch_size=16`
  3. Run `whisperx.DiarizationPipeline` (pyannote 3.1) — requires HuggingFace token
  4. Align words to speaker turns
- **Output:** List of `{start, end, text, speaker, word_segments}` dicts
- **VRAM:** WhisperX (~3.0GB) + pyannote (~1.5GB) = 4.5GB peak. Both unloaded after this stage.
- **Error handling:** If diarization fails (missing HF token, model unavailable), continue with `speaker=null` on all segments — transcription is still useful without speaker labels.

**Why WhisperX over faster-whisper:** The existing audio agent used faster-whisper, which does not have built-in alignment. WhisperX adds word-level alignment (needed to sync with scene boundaries) and wraps pyannote integration natively.

### Stage 5: Medical Terminology Post-Processing (CPU)
- **Input:** Transcribed segments
- **Action:**
  1. Load `scispacy` with `en_core_sci_lg` model (CPU, ~500MB RAM not VRAM)
  2. For each segment text, run NER to identify DISEASE, CHEMICAL, GENE entities
  3. Apply custom medical corrections dictionary (`medical_corrections.json`) — drug brand names, anatomical abbreviations, CME-specific terms
  4. Apply UMLS concept normalization for recognized entities (Phase 5 — links entity spans to UMLS CUIs)
  5. Reconstruct corrected segment text
- **Output:** Segments with corrected text + `medical_entities` list (entity text, type, UMLS CUI)
- **Tool:** `scispacy`, `en_core_sci_lg`, custom `medical_corrections.json`

**Medical corrections dictionary strategy:** A JSON file (`pipeline/data/medical_corrections.json`) with structure `{"pattern": "replacement", ...}` applied as regex before spacy NLP. This handles ASR-specific misheard medical terms (e.g., "ace inhibitor" → "ACE inhibitor", "met foreman" → "metformin"). The dictionary is curated manually and committed to the repo.

**Why not an LLM for medical correction:** LLMs are non-deterministic and cannot be run inline on dh40801 without consuming the VRAM budget needed for the core pipeline. scispacy + dictionary is deterministic, auditable, and fast.

**Speaker name recognition:** If speaker names are provided at job submission (from lecture metadata), they are added to the corrections dictionary at runtime: `{"dr chen": "Dr. Chen", "dr rivera": "Dr. Rivera"}`.

### Stage 6: Structured Document Assembly (CPU)
- **Input:** Scene segments (Stage 3), speaker-attributed ASR segments (Stage 4+5), lecture metadata
- **Action:** Merge timelines — for each scene segment, collect all ASR segments whose timestamps overlap, group by speaker, format into Markdown
- **Output:** Structured `.md` document (format specified below)

**WhisperX speaker name resolution:** WhisperX assigns anonymous labels (`SPEAKER_0`, `SPEAKER_1`). The doc assembly stage resolves these to real names using the lower third data from scene detection (Stage 3). Resolution logic: for each diarization speaker label, find which lower third overlays appeared while that speaker was active — majority wins.

### Stage 7: Embedding + Registry Push (CPU + Ollama)
- **Input:** Assembled document, scene segments, ASR segments
- **Action:**
  1. Generate embedding for full transcript text via local Ollama `nomic-embed-text` on dh40801
  2. HTTP POST to `http://10.0.0.251:8011/api/cme/transcriptions` with full payload
  3. Mark job as `completed`
- **Output:** Registry row ID on g700data1

---

## Output Format: Structured Markdown

```markdown
---
title: "Managing Cardiovascular Risk in Type 2 Diabetes: Current Evidence and Emerging Therapies"
date: "2024-03-15"
duration: "01:23:47"
speakers:
  - name: "Dr. Sarah Chen"
    title: "Professor of Endocrinology, Johns Hopkins"
  - name: "Dr. Marcus Rivera"
    title: "Cardiologist, Mayo Clinic"
cme_topic: "cardiovascular-risk-management"
accme_category: "AMA PRA Category 1"
processing:
  whisperx_model: "large-v3"
  diarization: true
  medical_nlp: "scispacy-en_core_sci_lg"
  processed_at: "2026-05-23T14:32:11Z"
---

# Managing Cardiovascular Risk in Type 2 Diabetes: Current Evidence and Emerging Therapies

## Summary

Dr. Chen and Dr. Rivera discuss evidence-based approaches to reducing MACE (Major Adverse Cardiovascular Events) in patients with Type 2 diabetes mellitus (T2DM), with focus on SGLT-2 inhibitors and GLP-1 receptor agonists.

---

## [00:00:00] Opening — Faculty on Camera

**Dr. Sarah Chen:** Welcome to this CME program on cardiovascular risk management in type 2 diabetes. I'm Dr. Sarah Chen from Johns Hopkins, and I'm joined today by...

**Dr. Marcus Rivera:** Marcus Rivera from Mayo Clinic. We're going to cover the latest evidence on SGLT-2 inhibitors, GLP-1 agonists, and the EMPA-REG OUTCOME trial data that really changed how we think about this.

---

## [00:03:22] Slide: Treatment Algorithm — First-Line Therapy

*Slide content: "ADA/EASD 2023 Consensus: Pathway for Glucose-Lowering in T2DM with Established CVD"*

**Dr. Chen:** So if we look at the 2023 ADA-EASD consensus statement, patients with established cardiovascular disease — meaning prior MI, prior stroke, or high-risk atherosclerosis — go directly to SGLT-2 inhibitor or GLP-1 receptor agonist as add-on to metformin, regardless of HbA1c.

**Dr. Rivera:** The evidence really does support that. The EMPA-REG trial showed a 38% relative risk reduction in cardiovascular death with empagliflozin. That's hard to ignore.

---

## [00:07:45] Lower Third: Dr. Sarah Chen — Disclosures

*Faculty disclosure: Consultant — AstraZeneca, Novo Nordisk. Research support — NIH.*

---

## [00:09:10] Chart/Graphic: EMPA-REG OUTCOME Trial — Primary Endpoint

*Description: Kaplan-Meier curve showing separation of empagliflozin versus placebo arms for 3-point MACE at approximately 3 months, maintained through 4-year follow-up.*

**Dr. Rivera:** This is the EMPA-REG OUTCOME curve. Notice the early separation — about 90 days — that's not what you'd expect from pure glycemic control. This is clearly a direct cardioprotective effect, likely through hemodynamic and renal mechanisms.

---

## [01:21:30] Closing — Faculty on Camera

**Dr. Chen:** To summarize: for patients with T2DM and established CVD or high CV risk, SGLT-2 inhibitors and GLP-1 agonists are now Class I recommendations. The evidence is unambiguous.

**Dr. Rivera:** Agreed. Thank you for joining us for this program.

---

## Medical Terms Index

| Term | Type | Full Form |
|------|------|-----------|
| T2DM | DISEASE | Type 2 Diabetes Mellitus |
| MACE | — | Major Adverse Cardiovascular Events |
| SGLT-2 | CHEMICAL | Sodium-Glucose Cotransporter-2 |
| GLP-1 | CHEMICAL | Glucagon-Like Peptide-1 |
| HbA1c | CHEMICAL | Glycated Hemoglobin A1c |
| EMPA-REG | — | Empagliflozin Cardiovascular Outcome Event Trial |

---

## Scene Timeline

| Timestamp | Scene Type | Label |
|-----------|-----------|-------|
| 00:00:00 | faculty_on_camera | Opening |
| 00:03:22 | presentation_slide | Treatment Algorithm — First-Line Therapy |
| 00:07:45 | lower_third | Dr. Sarah Chen — Disclosures |
| 00:09:10 | chart_or_graphic | EMPA-REG OUTCOME Trial — Primary Endpoint |
| 01:21:30 | faculty_on_camera | Closing |
```

---

## Data Model (g700data1 Registry)

Two new tables for distinct concerns: `cme_lecture_jobs` tracks pipeline execution state, `cme_transcriptions` stores the final searchable artifact.

### Migration 026: `cme_lecture_jobs`

```sql
CREATE TABLE cme_lecture_jobs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_filename         TEXT NOT NULL,
    source_path             TEXT NOT NULL,       -- path on dh40801
    lecture_title           TEXT,
    lecture_date            DATE,
    cme_topic               TEXT,
    speaker_names           TEXT[],              -- known speakers (may be provided pre-processing)
    duration_seconds        FLOAT,               -- from ffprobe
    status                  TEXT NOT NULL DEFAULT 'pending',
    -- CHECK: pending | extracting_audio | extracting_frames | scene_detection
    --        | transcribing | medical_nlp | assembling | pushing | completed | failed
    current_stage           TEXT,
    error_message           TEXT,
    error_stage             TEXT,
    retry_count             INTEGER NOT NULL DEFAULT 0,
    max_retries             INTEGER NOT NULL DEFAULT 3,
    processing_host         TEXT DEFAULT 'dh40801',
    transcription_id        UUID,                -- FK added after cme_transcriptions exists
    submitted_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at              TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    meta_data               JSONB
);

CREATE INDEX ix_cme_lecture_jobs_status ON cme_lecture_jobs(status);
CREATE INDEX ix_cme_lecture_jobs_submitted ON cme_lecture_jobs(submitted_at);
CREATE UNIQUE INDEX uq_cme_lecture_jobs_source_path ON cme_lecture_jobs(source_path);
CREATE INDEX ix_cme_lecture_jobs_pending ON cme_lecture_jobs(submitted_at) WHERE status = 'pending';
```

### Migration 027: `cme_transcriptions`

```sql
CREATE TABLE cme_transcriptions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id                  UUID REFERENCES cme_lecture_jobs(id) ON DELETE SET NULL,
    source_filename         TEXT NOT NULL,
    lecture_title           TEXT NOT NULL,
    lecture_date            DATE,
    cme_topic               TEXT,
    duration_seconds        FLOAT NOT NULL,
    speakers                JSONB NOT NULL DEFAULT '[]',
    -- [{"name": "Dr. X", "title": "Prof...", "institution": "..."}]
    scene_segments          JSONB NOT NULL DEFAULT '[]',
    -- [{"start_seconds": 0.0, "end_seconds": 183.2, "scene_type": "faculty_on_camera",
    --   "label": "Opening", "description": "..."}]
    transcript_segments     JSONB NOT NULL DEFAULT '[]',
    -- [{"start_seconds": 0.0, "end_seconds": 4.2, "speaker": "SPEAKER_0",
    --   "speaker_name": "Dr. Chen", "text": "...", "medical_entities": [...]}]
    full_text               TEXT NOT NULL,       -- concatenated transcript (for FTS)
    markdown_document       TEXT NOT NULL,       -- complete formatted .md output
    medical_entities        JSONB DEFAULT '[]',  -- deduplicated entity index
    -- [{"term": "T2DM", "entity_type": "DISEASE", "full_form": "...", "umls_cui": "C0011860"}]
    whisperx_model          TEXT,
    diarization_enabled     BOOLEAN NOT NULL DEFAULT true,
    medical_nlp_model       TEXT,
    confidence_score        FLOAT,
    language                TEXT DEFAULT 'en',
    processing_host         TEXT DEFAULT 'dh40801',
    tags                    TEXT[],
    embedding               vector(768),
    embedding_model         TEXT,
    search_vector           TSVECTOR,
    meta_data               JSONB,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uq_cme_transcriptions_source_filename ON cme_transcriptions(source_filename);
CREATE INDEX ix_cme_transcriptions_lecture_date ON cme_transcriptions(lecture_date);
CREATE INDEX ix_cme_transcriptions_cme_topic ON cme_transcriptions(cme_topic);
CREATE INDEX ix_cme_transcriptions_tags ON cme_transcriptions USING GIN(tags);
CREATE INDEX ix_cme_transcriptions_search ON cme_transcriptions USING GIN(search_vector);
CREATE INDEX ix_cme_transcriptions_created ON cme_transcriptions(created_at);

-- TSVECTOR auto-update trigger
CREATE OR REPLACE FUNCTION cme_transcriptions_search_vector_update()
RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('english',
        coalesce(NEW.lecture_title, '') || ' ' ||
        coalesce(NEW.cme_topic, '') || ' ' ||
        coalesce(NEW.full_text, '') || ' ' ||
        coalesce(NEW.source_filename, '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER cme_transcriptions_search_vector_trigger
    BEFORE INSERT OR UPDATE ON cme_transcriptions
    FOR EACH ROW EXECUTE FUNCTION cme_transcriptions_search_vector_update();

-- Add FK from cme_lecture_jobs to cme_transcriptions
ALTER TABLE cme_lecture_jobs
    ADD CONSTRAINT fk_cme_lecture_jobs_transcription
    FOREIGN KEY (transcription_id) REFERENCES cme_transcriptions(id) ON DELETE SET NULL;
```

**Note on `full_text` in TSVECTOR:** The full transcript can be long (60-90 minute lectures). PostgreSQL TSVECTOR has no hard size limit but `to_tsvector` truncates at ~1MB. For lectures exceeding this, the TSVECTOR covers title + topic + first ~50,000 chars. Full semantic search uses the embedding.

**Migration numbering:** The last migration is `025_add_test_coverage.py`. New migrations are `026` and `027`. The 027 migration defines `down_revision = "026"` and 026 references `025`.

**Upsert key:** `source_filename` (the original video filename). Reprocessing a lecture updates the existing row rather than creating a duplicate.

---

## API Design (g700data1)

Endpoint file: `registry/cme_transcriptions_endpoints.py`

```
POST   /api/cme/transcriptions              # submit from dh40801 (upsert by source_filename)
GET    /api/cme/transcriptions              # list with filters: cme_topic, lecture_date, limit, offset
GET    /api/cme/transcriptions/{id}         # get one by UUID
POST   /api/cme/transcriptions/search       # hybrid FTS + vector search
GET    /api/cme/transcriptions/{id}/markdown # return markdown_document as text/plain
DELETE /api/cme/transcriptions/{id}         # delete (admin only)

POST   /api/cme/lecture-jobs                # enqueue a new job
GET    /api/cme/lecture-jobs                # list jobs with status filter
GET    /api/cme/lecture-jobs/{id}           # poll job status
PATCH  /api/cme/lecture-jobs/{id}/status    # dh40801 pipeline updates stage/status
```

The `POST /api/cme/transcriptions` endpoint upserts on `source_filename` (idempotent). It generates the embedding inline using `embedding_utils.get_embedding(full_text[:8000])`.

The `PATCH /api/cme/lecture-jobs/{id}/status` accepts `{"status": "transcribing", "current_stage": "transcribing"}` — allows dh40801 to report progress without a full payload.

---

## Cross-Machine Data Flow

```
dh40801 (10.0.0.179)                          g700data1 (10.0.0.251)
─────────────────────────────                 ─────────────────────────────
pipeline/main.py
  │
  ├─ ffprobe metadata
  │
  ├─ POST /api/cme/lecture-jobs               → creates job row, returns job_id
  │         {source_filename, lecture_title,
  │          duration_seconds, speaker_names}
  │
  ├─ Stage 1-6: local processing
  │   For each stage:
  │   PATCH /api/cme/lecture-jobs/{id}/status → updates current_stage in registry
  │         {status: "transcribing",
  │          current_stage: "transcribing"}
  │
  └─ Stage 7: push result
      POST /api/cme/transcriptions            → upserts cme_transcriptions row
            {source_filename, lecture_title,
             scene_segments, transcript_segments,
             markdown_document, medical_entities,
             speakers, full_text, ...}

      PATCH /api/cme/lecture-jobs/{id}/status → marks job completed
            {status: "completed",
             transcription_id: <uuid>}
```

**Authentication:** The pipeline's `registry_client.py` uses an `X-Internal-Token` header matching an env var `INTERNAL_SERVICE_TOKEN` on g700data1. This avoids needing a full Cloudflare JWT for LAN-internal machine-to-machine calls. The registry auth middleware gets a one-line check: `if token == settings.internal_service_token: return system_user`.

**Payload size:** A 90-minute lecture will have ~50-80KB of JSON (transcript_segments + scene_segments + medical_entities). The markdown_document will be ~30-60KB. Total POST body: ~100-150KB. Well within HTTP limits.

---

## dh40801 Pipeline Service Layout

```
/home/swebber64/dhg-transcription/
├── docker-compose.yml               # pipeline service container
├── pipeline/
│   ├── main.py                      # CLI entrypoint + job loop
│   ├── job_queue.py                 # local job queue (SQLite)
│   ├── registry_client.py           # HTTP client for g700data1 registry API
│   ├── stages/
│   │   ├── audio_extract.py         # Stage 1: ffmpeg audio extraction
│   │   ├── frame_extract.py         # Stage 2: ffmpeg frame extraction
│   │   ├── scene_detect.py          # Stage 3: moondream2 scene classification
│   │   ├── asr.py                   # Stage 4: WhisperX + pyannote
│   │   ├── medical_nlp.py           # Stage 5: scispacy + corrections dict
│   │   └── doc_assemble.py          # Stage 6: markdown assembly
│   ├── data/
│   │   └── medical_corrections.json # drug names, anatomical abbreviations
│   └── tests/
│       ├── test_scene_detect.py
│       ├── test_asr.py
│       ├── test_medical_nlp.py
│       └── test_doc_assemble.py
├── requirements.txt
└── Dockerfile
```

The `main.py` job loop polls the local queue for pending jobs, processes sequentially, handles errors with retry logic. Designed to run as `python -m pipeline.main --watch /mnt/lectures` or process a single file with `python -m pipeline.main --file lecture.mp4`.

---

## Error Handling

### Per-stage failure recovery

Each stage writes its output to a job-local scratch directory (`/tmp/dhg-transcription/{job_id}/stage_N_output.json`). If a stage fails:
1. The job status in the local queue is set to `failed` with `error_stage` and `error_message`
2. The registry API is notified via `PATCH /api/cme/lecture-jobs/{id}/status`
3. If `retry_count < max_retries`: the job re-queues itself, skipping completed stages (re-uses stage output files that already exist on disk)

### Stage skip logic (re-run from failure point)

```python
def process_job(job: Job):
    scratch = Path(f"/tmp/dhg-transcription/{job.id}")
    scratch.mkdir(exist_ok=True)

    stages = [
        ("audio", audio_extract, scratch / "audio.wav"),
        ("frames", frame_extract, scratch / "frames"),
        ("scenes", scene_detect, scratch / "scenes.json"),
        ("asr", run_asr, scratch / "asr.json"),
        ("medical_nlp", run_medical_nlp, scratch / "medical_nlp.json"),
        ("document", assemble_document, scratch / "document.md"),
    ]

    for stage_name, stage_fn, output_path in stages:
        if output_path.exists():
            continue  # skip already-completed stages
        update_job_status(job.id, stage=stage_name)
        stage_fn(job, scratch)
```

### Network failure (push to g700data1)

The push to the registry API retries with exponential backoff (3 attempts, 2s/4s/8s delays). If all attempts fail, the local job is marked `push_failed` — a separate retry process polls for `push_failed` jobs hourly and re-attempts. The markdown document and all intermediate outputs remain on disk until a configurable retention period (default: 72 hours after successful push).

### VRAM OOM

If PyTorch raises CUDA OOM, the stage catches `torch.cuda.OutOfMemoryError`, forces `torch.cuda.empty_cache()`, and fails the stage with `error_message="CUDA OOM — retry when VRAM is free"`. The retry mechanism handles re-queueing.

---

## Medical NLP Strategy

### Primary tool: `scispacy` with `en_core_sci_lg` model

`en_core_sci_lg` is trained on biomedical literature (PubMed + MIMICIII) and provides:
- NER for DISEASE, CHEMICAL, GENE, PROTEIN entity types
- Accurate tokenization of hyphenated drug names (e.g., "empagliflozin" as one token)
- Abbreviation detection (scispacy has a dedicated `AbbreviationDetector` component)

### Custom corrections dictionary (`medical_corrections.json`)

Applied as a pre-processing step (regex find/replace before NLP). Addresses ASR-specific errors:
- Proper nouns WhisperX mishears: `"met foreman"` → `"metformin"`, `"glp one"` → `"GLP-1"`
- Acronym casing: `"ace inhibitor"` → `"ACE inhibitor"`, `"mi"` when followed by context → `"MI"`
- Drug brand names not in common vocabulary: populated from the actual lecture corpus over time

### UMLS normalization (Phase 5)

`scispacy` provides a `scispacy.linking.EntityLinker` component that can resolve named entities to UMLS CUIs. Enabling this adds ~30 seconds per lecture but produces structured `umls_cui` fields enabling cross-lecture entity relationship queries. Deferred to Phase 5 — earlier phases deliver named entity recognition without UMLS linking.

---

## Phased Build Sequence

### Phase 0 — dh40801 Server Setup (existing spec)
**Prerequisite.** Already spec'd at `docs/superpowers/plans/2026-05-19-dh40801-kb-server-setup.md`.
Clean Docker, fleet integration, install base tools (Python, Ollama, ffmpeg).

### Phase 1 — Registry Data Model + API (~3 hours)
**Target:** g700data1. Zero pipeline code. Establishes the data layer the pipeline will push to.

- [ ] Write `registry/alembic/versions/026_add_cme_lecture_jobs.py`
- [ ] Write `registry/alembic/versions/027_add_cme_transcriptions.py` (TSVECTOR trigger + vector(768) + GIN indexes)
- [ ] Add `CmeLectureJob` and `CmeTranscription` SQLAlchemy models to `registry/models.py`
- [ ] Write `registry/cme_transcription_schemas.py` (Create/Response/List/Search + LectureJobCreate/Response)
- [ ] Write `registry/cme_transcription_service.py` (upsert_by_source_filename, list, search_fts, get_by_id, delete)
- [ ] Write `registry/cme_lecture_job_service.py` (create, update_status, list, get_by_id)
- [ ] Write `registry/cme_transcriptions_endpoints.py` (all 8 endpoints with Prometheus instrumentation)
- [ ] Register router in `registry/api.py`
- [ ] Add `cme_transcriptions` source to `registry/kb_service.py` SOURCE_CONFIG with extractor
- [ ] Run migration on g700data1
- [ ] Write `registry/test_cme_transcriptions.py` (create, upsert idempotency, FTS search, vector search)
- **Acceptance:** `POST /api/cme/transcriptions` stores a row and is returned by `POST /api/cme/transcriptions/search`

### Phase 2 — Pipeline Core on dh40801 (~4 hours)
**Target:** dh40801. Audio extraction, ASR, medical NLP, basic document assembly. No vision yet.

- [ ] Create `/home/swebber64/dhg-transcription/` directory structure
- [ ] Write `pipeline/stages/audio_extract.py` (ffmpeg subprocess wrapper, validates output)
- [ ] Write `pipeline/stages/asr.py` (WhisperX large-v3 + pyannote diarization)
- [ ] Write `pipeline/stages/medical_nlp.py` (scispacy en_core_sci_lg, corrections dict, abbreviation detector)
- [ ] Write `pipeline/data/medical_corrections.json` (seed with 50 common CME terms)
- [ ] Write `pipeline/stages/doc_assemble.py` (markdown assembly without scene sections — uses timestamps only)
- [ ] Write `pipeline/registry_client.py` (httpx client for g700data1 10.0.0.251:8011)
- [ ] Write `pipeline/main.py` (CLI, single-file mode, job scratch dir, stage-skip logic)
- [ ] Write tests: `test_asr.py`, `test_medical_nlp.py`, `test_doc_assemble.py`
- [ ] Write `requirements.txt`, `Dockerfile`
- [ ] End-to-end test: process one 10-minute lecture, verify registry row appears on g700data1
- **Acceptance:** Full pipeline runs on a single lecture, produces valid markdown, POST to registry succeeds, FTS search finds the lecture by content

### Phase 3 — Scene Detection (~3 hours)
**Target:** dh40801. Adds vision layer.

- [ ] Write `pipeline/stages/frame_extract.py` (ffmpeg 0.5fps JPEG extraction)
- [ ] Write `pipeline/stages/scene_detect.py` (moondream2 via transformers, batch frame inference, scene segment collapsing)
- [ ] Integrate scene segments into `doc_assemble.py` (scene-boundary section headers, lower third extraction for speaker names)
- [ ] Update `medical_corrections.json` with lecture-corpus-specific terms discovered in Phase 2
- [ ] Write `pipeline/tests/test_scene_detect.py`
- **Acceptance:** Scene timeline table appears in output markdown, slide titles are extracted, lower third overlays capture speaker names/titles

### Phase 4 — Job Queue + Batch Processing (~2 hours)
**Target:** dh40801. Converts single-file mode to durable queue.

- [ ] Write `pipeline/job_queue.py` (SQLite-based local queue, retry logic, push_failed state)
- [ ] Add `--watch <directory>` mode to `main.py` (inotify or polling-based file watcher, auto-enqueues new .mp4/.mov files)
- [ ] Add exponential backoff retry to `registry_client.py`
- [ ] Write `docker-compose.yml` for dh40801 (single container, volume mounts for lecture archive and scratch)
- [ ] Test: submit 5 lectures, verify sequential processing, verify one failure mid-pipeline recovers
- **Acceptance:** Unattended processing of 10 lectures from a watched directory, all results in registry, no duplicate rows, one simulated failure recovers

### Phase 5 — UMLS Linking + KB Integration (~2 hours)
**Target:** Both machines. Enriches medical entities and wires into medkb.

- [ ] Enable `scispacy` EntityLinker in `medical_nlp.py` (linker=umls, threshold=0.85)
- [ ] Add UMLS CUI fields to `cme_transcriptions.medical_entities` JSONB schema
- [ ] Update `registry/kb_service.py` extractor for `cme_transcriptions` to include medical entities
- [ ] Write ingestor adapter that pushes `cme_transcriptions` rows as Documents into `medkb.corpora`
- **Acceptance:** `POST /api/kb/search?q=empagliflozin+cardiovascular` returns cme_transcriptions results

### Phase 6 — Observability + Batch Catchup (~2 hours)
**Target:** Both machines.

- [ ] Promtail on dh40801 shipping pipeline logs to Loki on g700data1
- [ ] Node exporter on dh40801 scraped by Prometheus on g700data1
- [ ] Grafana dashboard: lecture job queue depth, stage processing times, error rates
- [ ] Batch script: `pipeline/scripts/backfill_archive.py` — iterates over 500+ existing lectures, submits each to job queue
- **Acceptance:** Grafana shows pipeline metrics, backfill script processes 50 lectures overnight without errors

---

## Key File Paths (to create or modify)

### On g700data1 (this repo)

| File | Action |
|------|--------|
| `registry/alembic/versions/026_add_cme_lecture_jobs.py` | New |
| `registry/alembic/versions/027_add_cme_transcriptions.py` | New |
| `registry/models.py` | Add `CmeLectureJob`, `CmeTranscription` |
| `registry/cme_transcription_schemas.py` | New |
| `registry/cme_transcription_service.py` | New |
| `registry/cme_lecture_job_service.py` | New |
| `registry/cme_transcriptions_endpoints.py` | New |
| `registry/api.py` | Add router include |
| `registry/kb_service.py` | Add `cme_transcriptions` to SOURCE_CONFIG |
| `registry/test_cme_transcriptions.py` | New |

### On dh40801 (new directory)

| File | Action |
|------|--------|
| `dhg-transcription/pipeline/main.py` | New |
| `dhg-transcription/pipeline/stages/audio_extract.py` | New |
| `dhg-transcription/pipeline/stages/frame_extract.py` | New |
| `dhg-transcription/pipeline/stages/scene_detect.py` | New |
| `dhg-transcription/pipeline/stages/asr.py` | New |
| `dhg-transcription/pipeline/stages/medical_nlp.py` | New |
| `dhg-transcription/pipeline/stages/doc_assemble.py` | New |
| `dhg-transcription/pipeline/registry_client.py` | New |
| `dhg-transcription/pipeline/job_queue.py` | New |
| `dhg-transcription/pipeline/data/medical_corrections.json` | New |
| `dhg-transcription/docker-compose.yml` | New |
| `dhg-transcription/Dockerfile` | New |
| `dhg-transcription/requirements.txt` | New |
