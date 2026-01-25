# DHG CME Research Agent - LangGraph Cloud

**Evidence-based research agent for clinical gap analysis, needs assessments, and CME content.**

## Features

- ✅ **LangGraph Cloud Ready** - Pure agent, no infrastructure
- ✅ **Multi-LLM Routing** - Claude, Gemini, Qwen3 (Ollama)
- ✅ **AI Factory Registry** - Central service discovery
- ✅ **LangSmith Tracing** - Full observability

---

## LLM Providers

| Model | Provider | Use Case | Cost |
|-------|----------|----------|------|
| Claude Sonnet 4 | Anthropic | Complex synthesis, CME content | $0.015/1K out |
| Claude Haiku | Anthropic | Extraction, structured output | $0.004/1K out |
| Gemini 2.5 Flash | Google | Bulk screening, fast tasks | $0.001/1K out |
| **Qwen 3 14B** | **Ollama (local)** | **Cost-free, offline** | **$0.00** |

### Using Qwen3 Locally

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull Qwen3 14B
ollama pull qwen3:14b

# Run research with local LLM
python -c "
import asyncio
from src.agent import run_research

result = asyncio.run(run_research(
    topic='chronic cough',
    therapeutic_area='pulmonology',
    use_local_llm=True  # Uses Qwen3 via Ollama
))
print(result['synthesis'])
"
```

---

## AI Factory Registry Integration

This agent integrates with the DHG AI Factory central registry for service discovery.

### Agent Manifest

```python
from src.agent import registry

# Get manifest
manifest = registry.get_agent_manifest()

# Register with central registry
await registry.register()

# Send heartbeat
await registry.heartbeat(metrics={"requests": 100})
```

### Registry Schema

See `schemas/agent-manifest-v1.json` for the standardized manifest schema used across all DHG AI Factory agents.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agents/register` | POST | Register agent |
| `/api/v1/agents/{id}` | GET | Get agent details |
| `/api/v1/agents/{id}/heartbeat` | POST | Send heartbeat |
| `/api/v1/agents` | GET | List all agents |
| `/api/v1/models` | GET | List all models |
| `/api/v1/discover` | POST | Find agents by capability |

---

## Deploy to LangGraph Cloud

```bash
# Push to GitHub
git init && git add . && git commit -m "CME Research Agent"
git remote add origin https://github.com/your-org/dhg-cme-research-agent.git
git push -u origin main

# Deploy
langgraph deploy --project dhg-cme-research-agent
```

### Environment Variables

Set in LangGraph Cloud dashboard:

```
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
PERPLEXITY_API_KEY=pplx-...
NCBI_API_KEY=...  # Optional, increases rate limit

# For local Ollama (if available)
OLLAMA_BASE_URL=http://localhost:11434

# AI Factory Registry
AI_FACTORY_REGISTRY_URL=http://registry.ai-factory.local:8500
```

---

## Local Testing

```bash
pip install -r requirements.txt

# With cloud LLMs
python src/agent.py

# With local Qwen3
OLLAMA_BASE_URL=http://localhost:11434 python -c "
import asyncio
from src.agent import run_research
result = asyncio.run(run_research('chronic cough', 'pulmonology', use_local_llm=True))
print(result)
"
```

---

## Project Structure

```
dhg-cme-research-agent-cloud/
├── src/
│   ├── __init__.py
│   ├── agent.py              # Main agent (LLM router, graph, registry)
│   └── feedback_loop.py      # Feedback & evaluation system
├── schemas/
│   ├── agent-manifest-v1.json    # Agent manifest schema
│   └── registry-api-v1.json      # Registry API schema
├── langgraph.json            # LangGraph Cloud config
├── requirements.txt
├── .env.example
└── README.md
```

---

## Cost Comparison

| Config | Per Query | Monthly (1000 queries) |
|--------|-----------|------------------------|
| Claude Sonnet only | ~$0.22 | ~$220 |
| Claude + Gemini hybrid | ~$0.10 | ~$100 |
| **Qwen3 local only** | **$0.00** | **$0.00** |

---

## Feedback & Continuous Improvement Loop

Complete feedback cycle now implemented:

```
BUILD → DEPLOY → OBSERVE → EVALUATE → ITERATE
  ✅       ✅        ✅         ✅          ✅
```

### Components

| Component | Purpose | File |
|-----------|---------|------|
| `FeedbackCollector` | Collect feedback → LangSmith | feedback_loop.py |
| `EvaluationDataset` | Built-in test cases | feedback_loop.py |
| `QualityEvaluator` | Automated quality scoring | feedback_loop.py |
| `ImprovementTracker` | Trend analysis | feedback_loop.py |

### Quick Feedback

```python
from src.feedback_loop import thumbs_up, thumbs_down, submit_feedback

# Simple
thumbs_up(run_id="abc-123", comment="Great synthesis")
thumbs_down(run_id="xyz-789", comment="Missing citations")

# Detailed (0.0-1.0 scale)
submit_feedback(run_id="abc-123", score=0.8, comment="Good but missing RCTs")
```

### Multi-Dimension Expert Review

```python
from src.feedback_loop import feedback_collector, QualityDimension

feedback_collector.submit_multi_dimension(
    run_id="abc-123",
    scores={
        QualityDimension.EVIDENCE_QUALITY: 0.9,
        QualityDimension.SYNTHESIS_ACCURACY: 0.8,
        QualityDimension.GAP_IDENTIFICATION: 0.7,
        QualityDimension.CME_COMPLIANCE: 0.95
    },
    comment="Expert review by Dr. Smith"
)
```

### Auto-Evaluation on Every Run

```python
result = await run_research(
    topic="chronic cough",
    therapeutic_area="pulmonology",
    auto_evaluate=True  # ← Runs quality checks automatically
)

print(result["_evaluation"])
# {'overall': 0.85, 'passed': True, 'issues': [], 'scores': {...}}
```

### Evaluation Suite (CI/CD Quality Gate)

```python
from src.agent import run_evaluation_suite

# Run all built-in test cases
results = await run_evaluation_suite()

# Filter by therapeutic area
results = await run_evaluation_suite(tags=["pulmonology"])

print(f"Pass rate: {results['summary']['pass_rate']:.1%}")
# Pass rate: 80.0%
```

### Built-in Test Cases

| ID | Name | Difficulty | Tags |
|----|------|------------|------|
| cc-001 | Chronic Cough Gap Analysis | Medium | pulmonology, gsk-grant |
| dm-001 | Type 2 Diabetes Needs Assessment | Medium | endocrinology |
| onc-001 | Immunotherapy Literature Review | Hard | oncology, complex |
| edge-001 | Rare Disease (Limited Evidence) | Hard | rare_disease |
| fast-001 | Quick Podcast Content | Easy | cardiology, podcast |

### Improvement Reports

```python
from src.feedback_loop import get_improvement_report

report = get_improvement_report(days=14)

print(report["overall_health"]["trend_direction"])  # "improving"
print(report["action_items"])
# ['CITATION QUALITY: Expand PubMed search terms',
#  'GAP IDENTIFICATION: Review synthesis prompt']
```

### Quality Dimensions

| Dimension | Measures |
|-----------|----------|
| `overall` | Combined score |
| `evidence_quality` | High-quality citations (Level 1-2)? |
| `synthesis_accuracy` | Accurate to sources? |
| `gap_identification` | Gaps correctly identified? |
| `clinical_relevance` | Clinically relevant? |
| `citation_validity` | Citations accessible? |
| `completeness` | Response complete? |
| `cme_compliance` | Meets CME standards? |

---

## License

Proprietary - Digital Harmony Group
