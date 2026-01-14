# DHG AI Factory API Documentation

Complete API reference for the DHG AI Factory multi-agent orchestration system.

## Quick Reference

| Service | Port | Base URL | Swagger Docs |
|---------|------|----------|--------------|
| Orchestrator | 8011 | `http://localhost:8011` | `/docs` |
| Medical LLM | 8002 | `http://localhost:8002` | `/docs` |
| Research | 8003 | `http://localhost:8003` | `/docs` |
| Curriculum | 8004 | `http://localhost:8004` | `/docs` |
| Outcomes | 8005 | `http://localhost:8005` | `/docs` |
| Competitor Intel | 8006 | `http://localhost:8006` | `/docs` |
| QA/Compliance | 8007 | `http://localhost:8007` | `/docs` |
| Visuals | 8008 | `http://localhost:8008` | `/docs` |

---

## Orchestrator API (Port 8011)

The master coordination service that routes requests and coordinates agents.

### POST /orchestrate

Main orchestration endpoint. Detects compliance mode, coordinates agents, returns deliverables.

```bash
curl -X POST http://localhost:8011/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "needs_assessment",
    "topic": "Type 2 Diabetes Management in Primary Care",
    "compliance_mode": "auto",
    "target_audience": "Primary Care Physicians",
    "word_count_target": 1250,
    "include_sdoh": true,
    "include_equity": true,
    "reference_count_min": 6,
    "reference_count_max": 12
  }'
```

**Task Types:**
- `needs_assessment` - CME needs assessment document
- `curriculum` - Full curriculum design
- `learning_objectives` - Generate learning objectives only
- `cme_script` - CME script/content
- `grant_request` - Grant request documentation
- `gap_analysis` - Educational gap analysis
- `outcomes_plan` - Outcomes measurement plan
- `business_strategy` - NON-CME business strategy
- `competitor_analysis` - NON-CME competitor analysis

**Compliance Modes:**
- `auto` - Automatically detects based on task type and keywords
- `cme` - Enforces ACCME rules, fair balance, no commercial bias
- `non-cme` - No compliance restrictions

### GET /health

Returns health status of orchestrator and all connected agents.

```bash
curl http://localhost:8011/health
```

### POST /api/prompt-analyze

Analyzes prompt quality with semantic analysis via Ollama.

```bash
curl -X POST http://localhost:8011/api/prompt-analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a CME needs assessment about hypertension"}'
```

**Response includes:**
- `overall_score`, `clarity_score`, `specificity_score`, `compliance_score` (0-1)
- `detected_mode` - auto-detected compliance mode
- `suggestions` - improvement recommendations
- `semantic_analysis` - LLM-powered analysis (if Ollama available)

### POST /api/transcribe

Queue audio transcription from URL.

```bash
curl -X POST http://localhost:8011/api/transcribe \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/audio.mp3", "project_type": "medical"}'
```

### GET /api/transcribe/{transcription_id}

Check transcription status.

---

## Ollama Endpoints (Port 8011)

Direct access to local LLM inference.

### GET /api/ollama/models

List available Ollama models.

```bash
curl http://localhost:8011/api/ollama/models
```

### POST /api/ollama/chat

Direct chat with Ollama model (bypasses agent pipeline).

```bash
curl -X POST http://localhost:8011/api/ollama/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral:latest",
    "message": "What are the key components of a CME needs assessment?",
    "system_prompt": "You are a medical education expert."
  }'
```

---

## LangGraph Endpoints (Port 8011)

Workflow execution with PostgreSQL state persistence.

### POST /langgraph/run

Execute a LangGraph workflow.

```bash
curl -X POST http://localhost:8011/langgraph/run \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Diabetes Management",
    "task_type": "needs_assessment",
    "compliance_mode": "cme"
  }'
```

### POST /langgraph/resume

Resume a paused workflow thread.

```bash
curl -X POST http://localhost:8011/langgraph/resume \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "abc123",
    "message": "Add more detail about SGLT2 inhibitors"
  }'
```

### GET /langgraph/history/{thread_id}

Get all checkpointed states for a thread.

### GET /langgraph/status

Get LangGraph system status (checkpointer type, nodes, db connection).

---

## Artifacts Registry (Port 8011)

Central catalog for all generated assets.

### GET /api/artifacts

List artifacts with optional filtering.

```bash
# All artifacts
curl "http://localhost:8011/api/artifacts?limit=20"

# Filter by type
curl "http://localhost:8011/api/artifacts?artifact_type=image"
```

### POST /api/artifacts/register

Register a new artifact (called by agents after content creation).

```bash
curl -X POST http://localhost:8011/api/artifacts/register \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_type": "image",
    "source_agent": "visuals",
    "source_table": "generated_images",
    "source_id": "uuid-here",
    "title": "Diabetes Infographic",
    "file_format": "jpg",
    "tags": ["infographic", "diabetes", "cme"]
  }'
```

### GET /api/artifacts/{artifact_id}

Get artifact details by ID.

---

## Medical LLM Agent (Port 8002)

Clinical content generation, NER, ICD-10 extraction, quality measures.

### POST /generate

Generate medical content based on research and requirements.

```bash
curl -X POST http://localhost:8002/generate \
  -H "Content-Type: application/json" \
  -d '{
    "task": "needs_assessment",
    "topic": "Type 2 Diabetes in Primary Care",
    "compliance_mode": "cme",
    "word_count_target": 1250,
    "style": "cleo_abram_narrative",
    "structure": "scr_framework"
  }'
```

**Styles:** `conversational`, `cleo_abram_narrative`, `clinical`, `academic`
**Structures:** `general`, `scr_framework`, `imrad`

### POST /ner

Clinical Named Entity Recognition.

```bash
curl -X POST http://localhost:8002/ner \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Patient presents with Type 2 diabetes and hypertension, currently on metformin 1000mg BID.",
    "entity_types": ["disease", "drug", "dosage"]
  }'
```

### POST /icd10

Extract ICD-10 codes from clinical text.

```bash
curl -X POST http://localhost:8002/icd10 \
  -H "Content-Type: application/json" \
  -d '{"text": "Patient diagnosed with Type 2 diabetes mellitus with chronic kidney disease"}'
```

### POST /quality-measures

Suggest NQF/CMS/MIPS quality measures.

```bash
curl -X POST http://localhost:8002/quality-measures \
  -H "Content-Type: application/json" \
  -d '{"topic": "Diabetes Management", "condition": "Type 2 Diabetes"}'
```

### POST /guideline-summary

Summarize clinical guidelines from references.

```bash
curl -X POST http://localhost:8002/guideline-summary \
  -H "Content-Type: application/json" \
  -d '{
    "guideline_source": "ADA",
    "topic": "Type 2 Diabetes Treatment",
    "references": [{"title": "ADA Standards of Care 2024", "url": "https://..."}]
  }'
```

---

## Research Agent (Port 8003)

Multi-source evidence retrieval from 9+ sources.

### POST /research

Execute multi-source research query.

```bash
curl -X POST http://localhost:8003/research \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "SGLT2 inhibitors cardiovascular outcomes",
    "sources": ["pubmed", "clinical_trials", "cms_quality", "uspstf"],
    "max_results": 50,
    "include_epidemiology": true,
    "include_guidelines": true
  }'
```

**Available Sources:**
- `pubmed` - PubMed/NCBI biomedical literature
- `clinical_trials` - ClinicalTrials.gov
- `cdc_wonder` - CDC WONDER public health data
- `cms_quality` - CMS Quality Measures
- `uspstf` - USPSTF recommendations
- `ahrq` - AHRQ Evidence Reports
- `nih_reporter` - NIH RePORTER grants
- `consensus` - Consensus API (requires key)
- `perplexity` - Perplexity API (requires key)

### GET /sources

Get status of all research sources.

### POST /validate-urls

Validate reference URLs with retry logic.

```bash
curl -X POST http://localhost:8003/validate-urls \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://pubmed.ncbi.nlm.nih.gov/12345678/"],
    "retry_failed": true
  }'
```

### GET /cache/stats

Get cache statistics (hit rate, counts).

### DELETE /cache

Clear cache entries (by topic or source).

---

## Curriculum Agent (Port 8004)

Learning objectives and Moore Levels mapping.

### POST /design

Design complete curriculum with 6-10 learning objectives.

```bash
curl -X POST http://localhost:8004/design \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Diabetes Management Update",
    "target_audience": "Primary Care Physicians",
    "learning_gaps": ["SGLT2 inhibitor selection", "GLP-1 dosing"],
    "moore_levels_target": ["level_3_learning_declarative", "level_5_performance"],
    "compliance_mode": "cme",
    "format": "enduring",
    "include_assessments": true,
    "include_faculty_brief": true
  }'
```

### POST /objectives/generate

Generate learning objectives only.

### POST /objectives/map

Map existing objectives to Moore Levels, ICD-10, QI measures.

### GET /moore-levels

Get Moore Levels definitions and examples.

### POST /faculty-brief

Generate instructor briefing document.

### GET /templates/{format_type}

Get curriculum template for format: `enduring`, `live_webinar`, `podcast`, `video`, `written_monograph`, `case_based`, `simulation`

---

## Outcomes Agent (Port 8005)

Moore Levels outcomes planning and measurement.

### POST /plan

Build comprehensive outcomes plan.

```bash
curl -X POST http://localhost:8005/plan \
  -H "Content-Type: application/json" \
  -d '{
    "learning_objectives": ["Identify appropriate SGLT2 candidates", "Implement shared decision making"],
    "target_moore_levels": [3, 4, 5],
    "intervention_type": "webinar",
    "target_audience": "Endocrinologists",
    "icd10_codes": ["E11"],
    "qi_measures": ["NQF 0059"]
  }'
```

### POST /methodology

Design outcomes measurement methodology.

### POST /instruments/generate

Generate pre/post/6-week follow-up assessment instruments.

### POST /pathways/suggest

Get 3 innovative outcomes measurement pathways.

```bash
curl -X POST "http://localhost:8005/pathways/suggest?intervention_type=webinar&target_moore_levels=3,4,5&count=3"
```

### POST /data-map

Build outcomes data collection map.

### GET /moore-levels

Get detailed Moore Levels information with measurement approaches.

### POST /integrate/qi-measures

Map QI measures to learning objectives.

### POST /integrate/icd10

Link ICD-10 codes to outcome measures.

---

## QA/Compliance Agent (Port 8007)

ACCME validation and quality assurance.

### POST /validate

Validate content for compliance.

```bash
curl -X POST http://localhost:8007/validate \
  -H "Content-Type: application/json" \
  -d '{
    "content": "The full content text here...",
    "compliance_mode": "cme",
    "document_type": "needs_assessment",
    "checks": ["accme_compliance", "fair_balance", "word_count", "reference_validation"],
    "references": [{"title": "Study 1", "url": "https://..."}]
  }'
```

**Available Checks:**
- `compliance_mode` - Verify declared mode matches content
- `hallucinated_sources` - Detect fabricated references
- `reference_validation` - Validate reference format and URLs
- `word_count` - Check word count constraints
- `accme_compliance` - ACCME rules (CME only)
- `fair_balance` - Therapeutic balance check (CME only)
- `commercial_bias` - Detect promotional language (CME only)
- `sdoh_equity` - SDOH and health equity analysis

### POST /quick-check

Quick compliance check with default settings.

```bash
curl -X POST "http://localhost:8007/quick-check?content=Your+content+here&compliance_mode=cme"
```

### GET /accme-rules

Get list of ACCME compliance rules.

### GET /promotional-keywords

Get list of promotional keywords to avoid in CME content.

---

## Visuals Agent (Port 8008)

Medical image generation using Nano Banana Pro (Gemini 3 Pro Image).

### POST /generate

Generate medical visual with XMP metadata embedding.

```bash
curl -X POST http://localhost:8008/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Type 2 Diabetes Treatment Algorithm",
    "visual_type": "flowchart",
    "style": "medical-professional",
    "aspect_ratio": "16:9",
    "compliance_mode": "cme"
  }'
```

**Visual Types (19 total):**

*Core:*
- `infographic` - Data-rich visual with icons
- `slide` - Presentation slide
- `chart` - Clinical data chart
- `diagram` - Process/anatomical diagram
- `illustration` - Medical illustration

*CME-Specific:*
- `thumbnail` - Video/podcast thumbnail
- `certificate` - CME completion certificate
- `logo` - Medical/podcast logo
- `timeline` - Treatment progression
- `comparison` - Side-by-side treatment options
- `anatomical` - Body part/system illustration
- `flowchart` - Clinical decision algorithm
- `case_study` - Patient case visual
- `moa` - Mechanism of action diagram

*Social/Marketing:*
- `social_post` - Instagram/LinkedIn card
- `banner` - Website/email banner
- `avatar` - Profile image

*Data-Heavy:*
- `heatmap` - Data intensity visualization
- `dashboard` - Multi-metric display
- `scorecard` - Performance summary

**Styles:** `medical-professional`, `educational`, `modern-minimal`

**Aspect Ratios:** `16:9`, `4:3`, `1:1`, `9:16`

### GET /styles

Get all available visual types, styles, and aspect ratios.

### GET /images

List recently generated images.

```bash
curl "http://localhost:8008/images?limit=20&offset=0"
```

### GET /images/{image_id}

Retrieve image binary by ID.

### GET /images/{image_id}/info

Get image metadata without binary data.

### POST /edit

Edit existing visual (implementation in progress).

---

## WebSocket API (Port 8011)

Real-time communication for web UI.

### WS /ws

Connect to WebSocket for real-time updates.

```javascript
const ws = new WebSocket('ws://localhost:8011/ws?client_id=my-client');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

ws.send(JSON.stringify({
  type: 'orchestrate',
  payload: { task_type: 'needs_assessment', topic: 'Diabetes' }
}));
```

---

## OpenAPI Specification

Full OpenAPI 3.0 specification available at: `docs/openapi.yaml`

Import into Swagger UI, Postman, or any OpenAPI-compatible tool.

---

## Error Responses

All endpoints return standard error responses:

```json
{
  "detail": "Error message describing the issue"
}
```

**Common Status Codes:**
- `400` - Bad Request (invalid parameters)
- `404` - Not Found
- `500` - Internal Server Error
- `501` - Not Implemented (feature pending)
- `502` - Bad Gateway (agent communication failure)
- `503` - Service Unavailable
