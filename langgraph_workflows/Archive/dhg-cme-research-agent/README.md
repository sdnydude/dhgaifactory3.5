# DHG CME Research Agent

**Evidence-based research agent for clinical gap analysis, needs assessments, and CME content development.**

Part of the DHG AI Factory v3.5 architecture. Designed for Digital Harmony Group's medical education division.

**LangSmith Cloud enabled for full observability and evaluation.**

---

## 🎯 Purpose

This agent enables DHG CME to:
- Conduct **clinical gap analyses** with peer-reviewed evidence
- Support **needs assessments** for CME program development
- Generate **podcast content** with proper citations
- Create **CME materials** meeting ACCME requirements
- Support **pharmaceutical grant proposals** (e.g., GSK chronic cough)

---

## 📊 LangSmith Cloud Integration

Full observability with LangSmith Cloud:

### What's Traced
- **Every LLM call** (Claude, Gemini) with inputs/outputs
- **Retrieval operations** (PubMed, Perplexity searches)
- **Chain execution** (all LangGraph nodes)
- **Token usage and costs** per run
- **Evidence validation** steps

### LangSmith Features Used
| Feature | Use Case |
|---------|----------|
| **Tracing** | Debug research workflows, identify bottlenecks |
| **Feedback** | Rate research quality for improvement |
| **Datasets** | Create evaluation sets for testing |
| **Monitoring** | Track costs, latency, error rates |
| **Playground** | Test prompts before deployment |

### Setup LangSmith

```bash
# In your .env file
LANGCHAIN_API_KEY=lsv2_pt_your-key-here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=dhg-cme-research-agent
```

### View Traces

1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Select project `dhg-cme-research-agent`
3. View run traces, costs, latency

### Submit Feedback

```python
agent = CMEResearchAgent()
result = await agent.research(...)

# Get run ID from trace
agent.submit_feedback(
    run_id="run-id-from-trace",
    score=0.9,
    comment="Excellent evidence synthesis",
    key="quality"
)
```

---

## 🔒 Evidence Standards

**CRITICAL: This agent ONLY uses peer-reviewed, evidence-based sources.**

### Allowed Sources
| Source | Type | Use Case |
|--------|------|----------|
| PubMed | Peer-reviewed journals | Primary literature |
| Cochrane Library | Systematic reviews | High-level evidence |
| ClinicalTrials.gov | Trial data | Ongoing research |
| FDA | Drug labels | Regulatory information |
| Professional guidelines | Consensus statements | Practice recommendations |

### Blocked Sources
- Wikipedia, WebMD, Healthline (patient-facing, not peer-reviewed)
- News sites, social media
- Non-peer-reviewed web content

### Evidence Hierarchy (Oxford CEBM)
| Level | Type | Example |
|-------|------|---------|
| 1a | Systematic review/meta-analysis | Cochrane reviews |
| 1b | High-quality RCT | Well-designed trials |
| 2a | Lower-quality RCT | Trials with limitations |
| 2b | Cohort/case-control | Observational studies |
| 3 | Case series | Individual reports |
| 4 | Expert opinion | Practice guidelines |
| 5 | Narrative review | Editorials, letters |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CME Research Agent                           │
│                   (LangSmith Cloud Traced)                      │
├─────────────────────────────────────────────────────────────────┤
│  LangGraph Orchestration (@traceable on all nodes)              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Query    │→│ PubMed   │→│ Validate │→│ Synthesize│        │
│  │ Parser   │  │ Search   │  │ Sources  │  │ Findings │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                     ↓                             ↓             │
│              ┌──────────┐              ┌──────────────┐         │
│              │Perplexity│              │ Extract Gaps │         │
│              │ Academic │              │ & Compile    │         │
│              └──────────┘              └──────────────┘         │
├─────────────────────────────────────────────────────────────────┤
│  LLM Routing (LangChain wrappers for native tracing)            │
│  • Claude Sonnet 4.1 → Complex synthesis, CME content           │
│  • Gemini 2.5 Flash → Bulk screening, classification            │
│  • Claude Haiku → Citation extraction, structured parsing       │
├─────────────────────────────────────────────────────────────────┤
│  Storage: PostgreSQL + pgvector │ Cache: Redis                  │
├─────────────────────────────────────────────────────────────────┤
│  Observability: LangSmith Cloud (traces, feedback, evals)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- API keys for: Anthropic, Google AI, Perplexity, NCBI (optional)

### 1. Clone and Configure

```bash
# Clone (or copy files)
cd dhg-cme-research-agent

# Copy environment template
cp .env.template .env

# Edit .env with your API keys
nano .env
```

### 2. Start Services

```bash
# Create network (if not exists)
docker network create dhg-ai-factory

# Start all services
docker compose up -d

# Check health
curl http://localhost:8080/health
```

### 3. Run Your First Query

```bash
# Async query (returns immediately with job ID)
curl -X POST http://localhost:8080/research \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "chronic cough refractory treatment",
    "therapeutic_area": "pulmonology",
    "query_type": "gap_analysis",
    "target_audience": "primary_care"
  }'

# Poll for results
curl http://localhost:8080/research/{research_id}

# Or run synchronously (blocking)
curl -X POST "http://localhost:8080/research?sync=true" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "chronic cough",
    "therapeutic_area": "pulmonology",
    "query_type": "gap_analysis"
  }'
```

---

## 📡 API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/therapeutic-areas` | List supported areas |
| POST | `/research` | Create research query |
| GET | `/research/{id}` | Get results |
| GET | `/research` | List all jobs |
| GET | `/research/{id}/citations` | Get citations |
| GET | `/research/{id}/export` | Export results |

### Research Request Schema

```json
{
  "topic": "chronic cough refractory treatment",
  "therapeutic_area": "pulmonology",
  "query_type": "gap_analysis",
  "target_audience": "primary_care",
  "date_range_years": 5,
  "minimum_evidence_level": "2b",
  "max_results": 50,
  "specific_questions": [
    "What are current guideline recommendations?",
    "What gaps exist in primary care management?"
  ]
}
```

### Query Types
- `gap_analysis` - Identify clinical practice gaps
- `needs_assessment` - Support CME needs assessment
- `literature_review` - Comprehensive literature review
- `podcast_content` - Content for medical podcasts
- `cme_content` - CME educational materials

### Target Audiences
- `primary_care` - PCPs, family medicine
- `specialist` - Medical specialists
- `np_pa` - Nurse practitioners, physician assistants
- `pharmacist` - Clinical pharmacists
- `nurse` - Nursing professionals
- `mixed` - Multi-disciplinary

---

## 💻 Python SDK Usage

```python
import asyncio
from agents.research_agent import CMEResearchAgent, EvidenceLevel

async def main():
    agent = CMEResearchAgent()
    
    # Run research
    result = await agent.research(
        topic="chronic cough refractory treatment guidelines",
        therapeutic_area="pulmonology",
        query_type="gap_analysis",
        target_audience="primary_care",
        date_range_years=5,
        minimum_evidence_level=EvidenceLevel.LEVEL_2B,
        specific_questions=[
            "What are current guideline recommendations?",
            "What therapeutic options are emerging?"
        ]
    )
    
    # Access results
    print(f"Citations: {len(result.citations)}")
    print(f"Clinical Gaps: {result.clinical_gaps}")
    print(f"Synthesis: {result.synthesis}")
    
    # Export
    agent.export_to_json(result, "output.json")
    print(agent.export_citations_ama(result))

asyncio.run(main())
```

---

## 💰 Cost Optimization

The agent uses intelligent model routing to optimize costs:

| Task | Model | Est. Cost/Query |
|------|-------|-----------------|
| Literature screening | Gemini 2.5 Flash | ~$0.01 |
| Citation extraction | Claude Haiku | ~$0.02 |
| Complex synthesis | Claude Sonnet 4.1 | ~$0.15 |
| **Typical full query** | Mixed | **~$0.20-0.50** |

### Cost Controls
- Set `MAX_COST_PER_QUERY` in .env
- Use caching (Redis) for repeated queries
- Adjust `max_results` based on needs

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `PERPLEXITY_API_KEY` | Yes | Perplexity API key |
| `NCBI_API_KEY` | No | PubMed (increases rate limit) |
| `POSTGRES_PASSWORD` | Yes | Database password |

### Model Configuration

Edit `MODEL_CONFIG` in `research_agent.py`:

```python
MODEL_CONFIG = {
    "complex_synthesis": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",  # Or older for cost savings
        ...
    }
}
```

---

## 📊 Supported Therapeutic Areas

- Cardiology
- Oncology
- Neurology
- Pulmonology
- Gastroenterology
- Endocrinology
- Rheumatology
- Infectious Disease
- Dermatology
- Psychiatry
- Nephrology
- Hematology
- Immunology
- Primary Care
- Pediatrics
- Geriatrics
- Emergency Medicine
- Critical Care

---

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Integration test (requires API keys)
pytest tests/integration/ -v --run-integration
```

---

## 📁 Project Structure

```
dhg-cme-research-agent/
├── src/
│   ├── agents/
│   │   └── research_agent.py    # Main agent logic
│   └── api/
│       └── server.py            # FastAPI server
├── config/
│   └── init.sql                 # Database schema
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.template
└── README.md
```

---

## 🔗 Integration with DHG AI Factory

This agent integrates with the broader AI Factory architecture:

```yaml
# In your main AI Factory docker-compose
services:
  research-agent:
    image: dhg/cme-research-agent:latest
    networks:
      - dhg-ai-factory
    # Connects to shared PostgreSQL, Redis
```

---

## 📝 ACCME Compliance

This agent supports ACCME-compliant CME development by:
- **Traceability**: Every claim linked to peer-reviewed source
- **Evidence grading**: All citations classified by evidence level
- **AMA citations**: Export citations in AMA format
- **Audit trail**: Full provenance for all content

---

## 🛠️ Troubleshooting

### Common Issues

**PubMed rate limiting**
- Add NCBI_API_KEY for 10 req/sec (vs 3 without)

**Perplexity returning general web results**
- Check domain filter in client configuration

**High costs**
- Reduce `max_results`
- Use `bulk_screening` model for initial filtering
- Enable Redis caching

---

## 📄 License

Proprietary - Digital Harmony Group

---

## 👥 Support

For DHG internal support:
- Slack: #ai-factory
- Email: tech@digitalharmonygroup.com
