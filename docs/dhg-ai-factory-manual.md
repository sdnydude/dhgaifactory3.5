# DHG AI Factory - Complete System Manual

> **Last Updated**: January 26, 2026, 11:15 AM
> **Server**: 10.0.0.251
> **Branch**: `feature/langgraph-migration`

---

## EXECUTIVE SUMMARY

DHG AI Factory is a multi-agent system for automated CME (Continuing Medical Education) content generation, orchestrating 7+ specialized agents through a master orchestrator.

**Current State**: Core infrastructure operational, LangSmith Cloud deployment active, but data ingestion (CR/Onyx) not complete.

---

## SYSTEM ARCHITECTURE

### High-Level Overview

```
┌────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                          │
│   LibreChat (3010) │ LangSmith Studio │ API (8011)              │
└─────────────────────────────┬──────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────┐
│                      ORCHESTRATOR (8011)                        │
│        CME/NON-CME Mode Detection & Multi-Agent Coordination    │
└─────────────────────────────┬──────────────────────────────────┘
                              │
    ┌─────────────┬───────────┼───────────┬─────────────┐
    │             │           │           │             │
┌───▼───┐    ┌───▼───┐   ┌───▼───┐   ┌───▼───┐    ┌───▼───┐
│Medical│    │Research│   │Currclm│   │Outcomes│   │Compet.│
│  LLM  │    │ Agent  │   │ Agent │   │ Agent  │   │ Intel │
│ (8002)│    │ (8003) │   │ (8004)│   │ (8005) │   │ (8006)│
└───────┘    └────────┘   └───────┘   └────────┘   └───────┘
                              │
                    ┌─────────▼─────────┐
                    │  QA/Compliance    │
                    │     (8007)        │
                    └─────────┬─────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────┐
│                      DATA LAYER                                 │
│  Central Registry (PostgreSQL 5432) │ Qdrant (6333) │ Onyx     │
└────────────────────────────────────────────────────────────────┘
```

---

## CONTAINER STATUS (as of Jan 26, 2026)

### Healthy Containers (11/12)

| Container | Port | Status | Purpose |
|-----------|------|--------|---------|
| dhg-registry-db | 5432 | ✅ Healthy | PostgreSQL (40 tables) |
| dhg-registry-api | 8500 | ⚠️ Schema issue | API for Central Registry |
| dhg-medical-llm | 8002 | ✅ Healthy | ICD-10, NER, Guidelines |
| dhg-research | 8003 | ✅ Healthy | PubMed, Perplexity, 9 sources |
| dhg-curriculum | 8004 | ✅ Healthy | Learning objectives, Moore |
| dhg-outcomes | 8005 | ✅ Healthy | Moore Levels 3-5 |
| dhg-competitor-intel | 8006 | ✅ Healthy | Market analysis |
| dhg-qa-compliance | 8007 | ✅ Healthy | ACCME validation |
| dhg-visuals-media | 8008 | ✅ Healthy | Visual content |
| dhg-session-logger | 8009 | ✅ Healthy | Session tracking |
| dhg-ollama | 11434 | ✅ Running | Qwen 3 14B local LLM |
| LibreChat | 3010 | ✅ Running | Chat UI |

### Not Running

| Service | Expected Port | Status |
|---------|---------------|--------|
| Onyx Stack | 3001 | ❌ NOT RUNNING |
| Infisical | - | ❌ Container deleted |

---

## LANGSMITH CLOUD DEPLOYMENT

| Property | Value |
|----------|-------|
| **Deployment ID** | `df113409-49ee-4f08-ac29-0c52402d54e6` |
| **Name** | `dhg-agents` |
| **Graph** | `cme_research` |
| **URL** | `https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app` |
| **Status** | ✅ READY |
| **Secrets** | ANTHROPIC, GOOGLE, PERPLEXITY, NCBI (all configured) |
| **Latest Commit** | `26fdada` (finalize_node fix + EvidenceLevel fix) |

**Control Plane API**:
```bash
curl -X GET "https://api.host.langchain.com/v2/deployments" \
  -H "X-Api-Key: lsv2_sk_..." \
  -H "X-Tenant-Id: bad71132-9f05-443d-9a04-1f923632024c"
```

---

## CENTRAL REGISTRY (PostgreSQL)

**Container**: `986cbb4003b3_dhg-registry-db`
**User**: `dhg` | **Password**: `weenie64` | **Database**: `dhg_registry`

### Tables (40 total)
Key tables: `conversations`, `messages`, `artifacts`, `antigravity_chats`, `antigravity_messages`, `research_requests`, `agents`, `agent_memory`

### Current Data
| Table | Count |
|-------|-------|
| conversations | 2 |
| messages | 2 |
| artifacts | 1 |
| antigravity_chats | 2 |
| research_requests | 0 |

**⚠️ Issue**: Schema mismatch - `projects` table missing, API has column errors.

---

## KNOWN ISSUES & FIXES NEEDED

### P0 - Critical

| Issue | Status | Fix |
|-------|--------|-----|
| Registry-api schema mismatch | 🔧 | Run migrations, rebuild container |
| Onyx not running | ❌ | `cd infrastructure && docker compose up -d` |
| Session sync not working | ❌ | Implement CR sync in antigravity |
| Infisical container deleted | ❌ | Restart with new image |

### P1 - High

| Issue | Status | Fix |
|-------|--------|-----|
| LangSmith Cloud agent output | ✅ Fixed | Deployed with commit 26fdada |
| PubMed not working | ✅ Fixed | EvidenceLevel enum + NCBI key |
| LibreChat → LangSmith | 📋 | Update librechat.yaml endpoint |

### P2 - Medium

| Issue | Status |
|-------|--------|
| Data ingestion pipeline | Not started |
| Claude chat imports | ingest_claude_data.py exists, not run |
| Onyx collections empty | Qdrant has 0 collections |

---

## PRIORITIES (My Recommendation)

### Immediate (Today)

1. **Verify LangSmith Cloud deployment** - Test with JSON input, confirm output shows
2. **Start Onyx stack** - `cd infrastructure && docker compose up -d`
3. **Fix registry-api schema** - Run migrations for `projects` table

### This Week

4. **Run data ingestion** - `python ingest_claude_data.py` with Claude exports
5. **Update LibreChat config** - Point to LangSmith Cloud URL
6. **Rebuild dhg-registry-api** - Include antigravity_endpoints.py

### Next Sprint

7. Complete LangSmith assistants setup
8. Multi-provider BYOK integration
9. CME video transcription pipeline

---

## KEY FILES & LOCATIONS

| Purpose | Path |
|---------|------|
| Main project | `/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/` |
| Docker compose | `docker-compose.yml` |
| Environment | `.env` |
| Agents | `agents/` (8 subdirectories) |
| LangGraph Cloud | `langgraph_workflows/dhg-agents-cloud/` |
| Registry | `registry/` |
| Documentation | `docs/` |
| Infrastructure | `infrastructure/` (Onyx stack) |

---

## API KEYS (Configured)

| Key | Location | Status |
|-----|----------|--------|
| ANTHROPIC_API_KEY | .env + LangSmith | ✅ |
| GOOGLE_API_KEY | .env + LangSmith | ✅ |
| PERPLEXITY_API_KEY | .env + LangSmith | ✅ |
| NCBI_API_KEY | .env + LangSmith | ✅ |
| LANGCHAIN_API_KEY | .env | ✅ |
| PUBMED_API_KEY | .env | ✅ |

---

## TEST COMMANDS

### Agent Health Check
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 \
  'for port in 8002 8003 8004 8005 8006 8007 8008; do \
    echo -n "Port $port: "; \
    curl -s http://localhost:$port/health || echo "DOWN"; \
  done'
```

### LangSmith Cloud Test
```json
{
  "topic": "chronic cough management",
  "therapeutic_area": "pulmonology",
  "query_type": "gap_analysis",
  "target_audience": "physicians",
  "date_range_years": 5,
  "minimum_evidence_level": "2",
  "output_format": "json"
}
```

### Database Query
```bash
docker exec 986cbb4003b3_dhg-registry-db psql -U dhg -d dhg_registry -c "SELECT * FROM conversations;"
```

---

## DIAGRAM PROMPTS

### 1. Full System Architecture (4K)

```
Create a detailed 4K technical architecture diagram of the DHG AI Factory system:

TOP LAYER - User Interfaces:
- LibreChat web UI (port 3010) with chat bubbles
- LangSmith Studio cloud icon
- REST API gateway (port 8011)

MIDDLE LAYER - Orchestration:
- Central Orchestrator box connecting to all agents
- 7 specialized agent boxes arranged in a grid:
  * Medical LLM (8002) - stethoscope icon
  * Research (8003) - magnifying glass icon
  * Curriculum (8004) - graduation cap icon
  * Outcomes (8005) - chart icon
  * Competitor Intel (8006) - radar icon
  * QA/Compliance (8007) - checkmark shield icon
  * Visuals (8008) - image icon

CLOUD LAYER - LangSmith:
- LangSmith Cloud box with "cme_research" graph inside
- Arrows showing deployment from GitHub
- Studio, Tracing, Assistants sub-components

BOTTOM LAYER - Data:
- PostgreSQL Central Registry (40 tables icon)
- Qdrant Vector DB (geometric shapes)
- Onyx Knowledge Base (grayed out - not running)

EXTERNAL SERVICES (right side):
- PubMed/NCBI
- Perplexity API
- Anthropic (Claude)
- Google (Gemini)
- Ollama (local Qwen)

Style: Modern dark theme, neon accent colors (green=healthy, red=issues, yellow=warning)
Show all port numbers and container names
Resolution: 4K (3840x2160)
```

### 2. LangGraph CME Research Agent Flow

```
Create a detailed flow diagram of the CME Research Agent in LangSmith Cloud:

START node (green)
  ↓
log_request node - "Log to registry"
  ↓
PARALLEL SPLIT (two branches)
  ├─→ pubmed_search node - "NCBI API, Evidence Grading" (green border)
  └─→ perplexity_search node - "Web Research" (green border)
  
Both branches merge at:
combine_results node - "Merge sources"
  ↓
validate_sources node - "Dedupe, validate URLs"
  ↓
synthesize node - "Claude/Gemini LLM synthesis"
  ↓
extract_gaps node - "Identify clinical gaps"
  ↓
finalize node - "Return output to Studio" (green - fixed)
  ↓
END node

Show state schema on the side:
- topic, therapeutic_area, query_type
- pubmed_results, perplexity_results
- validated_citations, synthesis
- clinical_gaps, key_findings
- errors, messages

Style: Clean flowchart, dark background, colored nodes
```

### 3. Data Flow Diagram

```
Create a data flow diagram showing how data moves through DHG AI Factory:

SOURCES (left):
- Claude AI exports (ZIP files)
- LibreChat sessions
- Antigravity sessions
- CME video transcripts
- PubMed articles

INGESTION (middle-left):
- ingest_claude_data.py
- Session Logger (8009)
- Onyx Connector

STORAGE (center):
- Central Registry PostgreSQL
  * conversations table
  * messages table
  * artifacts table
  * research_requests table
- Qdrant Vector DB
  * Embeddings collections
- Onyx Knowledge Base

RETRIEVAL (middle-right):
- Research Agent queries
- RAG pipeline
- Semantic search

OUTPUT (right):
- CME Proposals
- Gap Reports
- Podcast Scripts
- PowerPoint Outlines

Show arrows with data types flowing between each layer
```

---

## QUICK REFERENCE

### SSH to Server
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251
```

### Project Directory
```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
```

### Restart All Containers
```bash
docker compose down && docker compose up -d
```

### View Logs
```bash
docker compose logs -f [service-name]
```

### Git Status
```bash
git status && git log -3 --oneline
```
