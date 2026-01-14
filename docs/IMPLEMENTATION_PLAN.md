# Implementation Plan: Research Agent Enhancement with LangSmith Plus

## Goal

Transform the Research Agent from a simple FastAPI endpoint into a rich LangGraph workflow with tools, RAG, memory, and subagents. Use this as a **template** for all 16 agents. Leverage LangSmith Cloud Plus features wherever they provide value.

---

## LangSmith Plus Features to Leverage

| Feature | How We'll Use It | Status |
|---------|------------------|--------|
| **LangSmith Studio** | Visualize and debug Research Agent graph | ✅ Connected via Tailscale |
| **Agent Builder** | Chat-based agent creation for simpler agents | 🔜 Evaluate |
| **LangSmith Fetch CLI** | Pull traces into terminal for debugging | 🔜 Install |
| **Prompt Hub** | Version and share prompts across agents | 🔜 Set up |
| **Evaluations** | Offline/online eval for Research quality | 🔜 Configure |
| **Monitoring & Alerts** | Track Research Agent latency/errors | 🔜 Configure |
| **MCP (Model Context Protocol)** | Connect internal APIs as tools | 🔜 Evaluate |

---

## Research Agent Architecture

### Current State (Skeletal)
```
FastAPI /research endpoint
  └── Returns mock data or minimal API call
```

### Target State (Full LangGraph)
```
Research Agent Graph
├── Nodes
│   ├── query_router (decide which sources to query)
│   ├── pubmed_tool (ToolNode - PubMed API)
│   ├── clinical_trials_tool (ToolNode - ClinicalTrials.gov)
│   ├── cdc_tool (ToolNode - CDC WONDER)
│   ├── rag_retriever (search cached papers in vector store)
│   ├── evidence_grader (subagent - score relevance)
│   ├── citation_validator (subagent - verify URLs)
│   └── synthesizer (compile final evidence pack)
├── Memory
│   ├── Short-term: Conversation state via PostgresSaver
│   └── Long-term: Topic research history in registry
├── RAG
│   └── pgvector index on cached research papers
└── Edges
    ├── query_router → [pubmed, clinical_trials, cdc, rag] (parallel)
    ├── [tools] → evidence_grader
    ├── evidence_grader → citation_validator
    └── citation_validator → synthesizer → END
```

---

## Implementation Phases

### Phase 1: LangSmith Plus Setup (Day 1)

1. **Install LangSmith Fetch CLI** in orchestrator container (SDK v0.6.2 already installed)
   ```bash
   docker exec dhg-aifactory-orchestrator pip install langsmith-fetch
   ```

2. **Configure Prompt Hub**
   - Create `dhg-research/query-router` prompt
   - Create `dhg-research/evidence-grader` prompt
   - Create `dhg-research/synthesizer` prompt

3. **Set up Monitoring Dashboard**
   - Create "Research Agent" project in LangSmith
   - Configure latency/error alerts

### Phase 2: LangGraph Refactor (Days 2-3)

#### [MODIFY] agents/orchestrator/langgraph_integration.py

Add Research Agent as a proper subgraph instead of HTTP call.

#### [NEW] agents/research/graph.py

```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from .tools import pubmed_search, clinical_trials_search, cdc_search
from .rag import research_retriever
from .subagents import evidence_grader, citation_validator

class ResearchState(TypedDict):
    topic: str
    sources: List[str]
    raw_results: List[Dict]
    graded_results: List[Dict]
    validated_citations: List[Dict]
    evidence_pack: Dict

def build_research_graph():
    workflow = StateGraph(ResearchState)
    
    # Tool nodes
    workflow.add_node("pubmed", ToolNode([pubmed_search]))
    workflow.add_node("clinical_trials", ToolNode([clinical_trials_search]))
    workflow.add_node("cdc", ToolNode([cdc_search]))
    workflow.add_node("rag_search", research_retriever)
    
    # Processing nodes
    workflow.add_node("evidence_grader", evidence_grader)
    workflow.add_node("citation_validator", citation_validator)
    workflow.add_node("synthesizer", synthesizer)
    
    # Router
    workflow.add_node("query_router", query_router)
    workflow.set_entry_point("query_router")
    
    # Edges
    workflow.add_conditional_edges("query_router", route_to_sources)
    workflow.add_edge("pubmed", "evidence_grader")
    workflow.add_edge("clinical_trials", "evidence_grader")
    workflow.add_edge("cdc", "evidence_grader")
    workflow.add_edge("rag_search", "evidence_grader")
    workflow.add_edge("evidence_grader", "citation_validator")
    workflow.add_edge("citation_validator", "synthesizer")
    workflow.add_edge("synthesizer", END)
    
    return workflow.compile(checkpointer=postgres_saver)
```

#### [NEW] agents/research/tools/pubmed.py

```python
from langchain_core.tools import tool
import httpx

@tool
def pubmed_search(query: str, max_results: int = 10) -> List[Dict]:
    """Search PubMed for medical research papers."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    # ... full implementation
```

#### [NEW] agents/research/tools/clinical_trials.py

Clinical trials.gov API v2 integration.

#### [NEW] agents/research/tools/cdc.py

CDC WONDER data access.

#### [NEW] agents/research/rag.py

Vector search over cached research papers using pgvector.

#### [NEW] agents/research/subagents/evidence_grader.py

LLM-powered relevance scoring subgraph.

#### [NEW] agents/research/subagents/citation_validator.py

URL validation and reference formatting subgraph.

### Phase 3: Prompt Hub Integration (Day 4)

1. Store all prompts in LangSmith Prompt Hub
2. Pull prompts at runtime:
   ```python
   from langsmith import Client
   client = Client()
   prompt = client.pull_prompt("dhg-research/query-router")
   ```

### Phase 4: Evaluations Setup (Day 5)

1. Create evaluation dataset in LangSmith
   - 20 sample topics with expected sources
   - Gold-standard evidence packs

2. Define evaluators:
   - `source_coverage` - Did we query appropriate sources?
   - `citation_accuracy` - Are URLs valid?
   - `evidence_quality` - Is evidence relevant?

3. Run offline evaluations:
   ```bash
   langsmith evaluate --dataset research-eval --project research-agent
   ```

---

## Files to Create/Modify

### New Files
| Path | Purpose |
|------|---------|
| `agents/research/graph.py` | Main LangGraph workflow |
| `agents/research/state.py` | TypedDict state definitions |
| `agents/research/tools/pubmed.py` | PubMed API tool |
| `agents/research/tools/clinical_trials.py` | ClinicalTrials.gov tool |
| `agents/research/tools/cdc.py` | CDC WONDER tool |
| `agents/research/rag.py` | Vector retrieval |
| `agents/research/subagents/evidence_grader.py` | Grading subgraph |
| `agents/research/subagents/citation_validator.py` | Validation subgraph |

### Modified Files
| Path | Changes |
|------|---------|
| `agents/orchestrator/langgraph_integration.py` | Import Research subgraph instead of HTTP call |
| `agents/research/main.py` | Add `/graph` endpoint exposing the LangGraph |

---

## Verification Plan

### LangSmith Studio Verification
1. Open LangSmith Studio: `https://smith.langchain.com/studio/?baseUrl=http://100.107.14.51:2024`
2. Navigate to Research Agent graph
3. Verify all nodes appear: query_router, pubmed, clinical_trials, cdc, rag_search, evidence_grader, citation_validator, synthesizer

### API Testing
```bash
# Test PubMed tool directly
curl -X POST http://100.107.14.51:8003/tools/pubmed \
  -H "Content-Type: application/json" \
  -d '{"query": "type 2 diabetes management", "max_results": 5}'

# Test full research graph
curl -X POST http://100.107.14.51:8003/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "hypertension in elderly patients", "sources": ["pubmed", "clinical_trials"]}'
```

### LangSmith Evaluations
```bash
# Run offline evaluation
langsmith evaluate --dataset research-eval --project dhg-research-agent

# Expected: >80% source_coverage, >95% citation_accuracy
```

### Manual Testing
1. Run a research request from the Web UI
2. Check LangSmith traces for the Research Agent
3. Verify all tool nodes executed
4. Confirm evidence pack contains valid citations

---

## Template for Other Agents

This Research Agent pattern becomes the template:

| Agent | Tools | RAG | Subagents |
|-------|-------|-----|-----------|
| Research | PubMed, ClinicalTrials, CDC | Cached papers | Evidence grader, Citation validator |
| Medical LLM | Ollama, OpenAI, Anthropic | Clinical guidelines | Fact checker, Bias detector |
| Curriculum | Moore mapper, ICD-10 lookup | Learning objective examples | Objective validator |
| Outcomes | Assessment generator | Moore Levels templates | Assessment scorer |
| Competitor-Intel | ACCME scraper, Medscape, WebMD | Competitor database | Differentiation analyzer |
| QA-Compliance | ACCME rules checker | Compliance examples | Violation reporter |
| Visuals | Gemini image API | Style templates | Metadata embedder |

---

## Finalized Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Agent Builder vs Code** | All in code | Consistency, version control, full customization |
| **MCP Integration** | Yes | Claude skills, cross-tool composability |
| **Subgraph Depth** | Max 2 levels | Debuggability, testability |

---

## MCP Integration Architecture

### DHG Agents as MCP Servers

Expose each agent as an MCP server so Claude Desktop/Code and other MCP clients can call them:

```python
# agents/research/mcp_server.py
from mcp import Server

server = Server("dhg-research")

@server.tool()
async def search_medical_literature(topic: str, sources: list[str] = ["pubmed"]):
    """Search medical literature across multiple sources."""
    return await research_graph.invoke({"topic": topic, "sources": sources})

@server.tool()
async def validate_citations(citations: list[str]):
    """Validate and format citations in AMA style."""
    return await citation_validator.invoke({"citations": citations})
```

### External Skills as MCP Clients

Your ADHD Adaptive AI skills (when built) connect as MCP clients:

```
┌─────────────────────────────────────────────────────┐
│              SHARED CENTRAL REGISTRY                │
│              (PostgreSQL + pgvector)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ dhg_registry│  │ adhd_data   │  │ future_prod │  │
│  │ (CME tables)│  │ (ADHD tbls) │  │             │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────┘
         ▲                  ▲                  ▲
         │ MCP              │ MCP              │ MCP
┌────────┴────────┐ ┌───────┴───────┐ ┌────────┴────────┐
│ DHG AI Factory  │ │ ADHD Adaptive │ │ Future Product  │
│ (CME Agents)    │ │ AI Platform   │ │                 │
│ Port: 8001-8011 │ │ Port: 8050+   │ │                 │
└─────────────────┘ └───────────────┘ └─────────────────┘
```

### MCP Use Cases

| Pattern | Example |
|---------|---------|
| Claude → DHG | Claude Code calls Research Agent for medical lit search |
| Claude → ADHD | Claude calls ADHD Focus Coach skill |
| DHG → ADHD | Orchestrator uses ADHD cognitive load analyzer |
| ADHD → DHG | ADHD platform uses Medical LLM for content |

---

## Multi-Product Architecture (Shared Registry)

> [!IMPORTANT]
> All products share the SAME PostgreSQL instance to prevent database sprawl.

### Registry Schema Strategy

```sql
-- Central registry tables (existing)
dhg_registry.references
dhg_registry.events
dhg_registry.segments

-- ADHD platform tables (future, same DB instance)
adhd_platform.users
adhd_platform.sessions
adhd_platform.adaptations

-- Shared tables
shared.api_cache
shared.vector_embeddings
```

### Docker Compose Strategy

```yaml
# Single registry, multiple product services
services:
  registry-db:
    # ONE database instance for all products
    
  # DHG AI Factory services
  orchestrator:
    depends_on: [registry-db]
    
  # ADHD Platform services (future)
  adhd-coach:
    depends_on: [registry-db]  # Same DB
    environment:
      - REGISTRY_DB_URL=postgresql://dhg:pass@registry-db:5432/dhg_registry
```

---

**Executable as delivered in the stated environment.**

Intentionally omitted:
- Actual API credentials for PubMed, ClinicalTrials, CDC (user must configure)
- ADHD platform skill implementations (currently planned, not built)
- Full MCP server implementation (shown as pattern)
