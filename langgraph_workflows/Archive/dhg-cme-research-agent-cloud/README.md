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
│   └── agent.py              # Main agent (LLM router, graph, registry)
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

## License

Proprietary - Digital Harmony Group
