# Implementation Plan: Agent Enhancements (Priority 1)

**Last Updated:** January 13, 2026  
**Status:** Planning  

## Goal

Enhance the core CME pipeline agents with real data sources and production-ready reliability, transforming them from mock/stub implementations to fully functional services.

---

## 1. Research Agent - Multi-Source APIs

**Target:** Connect to real medical research APIs

### Endpoints to Implement
- **PubMed/NCBI** - `eutils.ncbi.nlm.nih.gov/entrez`
- **ClinicalTrials.gov** - `clinicaltrials.gov/api/v2`
- **CDC WONDER** - `wonder.cdc.gov` (data access)
- **CMS Quality Measures** - `data.cms.gov`

### Implementation Steps
1. Add API client modules in `agents/research/sources/`
2. Configure rate limiting and caching in `api_cache` table
3. Implement unified response normalization
4. Add fallback chain (PubMed -> Consensus -> Perplexity)

### Files to Modify
- `agents/research/main.py`
- `agents/research/sources/pubmed.py` [NEW]
- `agents/research/sources/clinical_trials.py` [NEW]

---

## 2. Competitor-Intel - Web Scrapers

**Target:** Automated competitive intelligence from CME providers

### Sources to Scrape
- ACCME Provider Directory
- Medscape Education
- WebMD Medscape CME
- FreeCME
- PriMed
- NEJM Knowledge+

### Implementation Steps
1. Add async scraper modules with rate limiting
2. Store in `competitor_activities` table
3. Implement deduplication logic
4. Add alerting for new competitor activities

### Files to Modify
- `agents/competitor-intel/main.py`
- `agents/competitor-intel/scrapers/` [NEW DIR]

---

## 3. Medical LLM - Cloud Fallbacks

**Target:** Reliable content generation with provider redundancy

### Fallback Chain
1. **Ollama** (local) - Primary, fastest
2. **OpenAI GPT-4** - Cloud fallback
3. **Anthropic Claude** - Secondary fallback

### Implementation Steps
1. Add provider abstraction layer
2. Implement automatic failover on timeout/error
3. Log provider usage to registry for cost tracking
4. Add model-specific prompts per provider

### Files to Modify
- `agents/medical-llm/main.py`
- `agents/medical-llm/providers/` [NEW DIR]

---

## 4. QA-Compliance - Registry Logging

**Target:** Full audit trail for compliance reviews

### Data to Log
- Validation results (pass/fail, score)
- Rule violations detected
- Content checksums
- Reviewer actions (if human review)

### Implementation Steps
1. Add `compliance_audits` table to schema
2. Log every validation to registry
3. Add query endpoint for audit history
4. Implement retention policy

### Files to Modify
- `agents/qa-compliance/main.py`
- `registry/init.sql` (add table)

---

## 5. Visuals - Metadata and Compliance Mode

**Target:** Embedded metadata and user-selectable compliance mode

### Features
- XMP metadata in generated images
- `compliance_mode` dropdown in UI (auto/cme/non-cme)
- Watermarking for CME content

### Implementation Steps
1. Add XMP embedding using `python-xmp-toolkit` or `pyexiv2`
2. Add `compliance_mode` to `/generate` endpoint
3. Update `VisualsToolPanel.jsx` with dropdown
4. Store metadata in `visual_artifacts` table

### Files to Modify
- `agents/visuals/main.py`
- `web-ui/src/components/panels/VisualsToolPanel.jsx`

---

## Verification Plan

### Automated Tests
```bash
# Test Research Agent API connectivity
curl http://localhost:8003/health
curl -X POST http://localhost:8003/research -H "Content-Type: application/json" -d '{"topic":"diabetes","sources":["pubmed"]}'

# Test Medical LLM fallback
curl -X POST http://localhost:8002/generate -H "Content-Type: application/json" -d '{"topic":"hypertension","force_provider":"openai"}'

# Test QA-Compliance logging
curl http://localhost:8007/audit-history?limit=10
```

### Manual Verification
1. Generate CME content and verify registry entries
2. Check competitor scraper results in database
3. Verify XMP metadata in downloaded images

---

**Executable as delivered in the stated environment**.

Intentionally omitted:
- None - plan is complete for Priority 1 scope.
