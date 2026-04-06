# CME Research Agent - Complete Context Document

> **Last Updated**: January 26, 2026, 10:35 AM

> **CRITICAL**: ALL LangGraph/LangSmith work is in THE CLOUD ONLY.
> - NO local LangGraph servers
> - NO local LangSmith
> - Everything runs at https://smith.langchain.com
> - Code edits on server → push to GitHub → triggers cloud deployment


## 1. DEPLOYMENT INFO

| Property | Value |
|----------|-------|
| **Platform** | LangSmith Cloud (LangGraph) |
| **Deployment Name** | `dhg-agents` |
| **Graph Name** | `cme_research` |
| **Deployment URL** | `https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app` |
| **API Docs** | `https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app/docs` |
| **Repository** | `sdnydude/dhgaifactory3.5` |
| **Branch** | `feature/langgraph-migration` |
| **Last Deployed** | 1/25/2026, 9:53:31 PM |
| **Status** | Active |

---

## 2. SOURCE FILES (on server 10.0.0.251)

```
/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/langgraph_workflows/dhg-agents-cloud/
├── src/
│   ├── agent.py          # Main agent code (46KB)
│   ├── agent.py.backup   # Backup copy
│   └── integrations/     # External API integrations
├── langgraph.json        # {"graphs": {"cme_research": "./src/agent.py:graph"}}
├── pyproject.toml        # Dependencies
├── .env                  # Local env vars (NOT deployed to cloud)
├── outputs/              # Local file outputs
└── venv/                 # Python virtual environment (broken pip)
```

---

## 3. KNOWN ISSUES

### Issue A: Output Not Showing in Studio
- **Symptom**: Perplexity returns results in trace, but Studio shows no output
- **Root Cause**: `finalize_node` (line ~824) returns empty `{}`
- **Fix**: Change `return {}` to return synthesis, gaps, citations

### Issue B: PubMed Not Working
- **Symptom**: PubMed searches fail
- **Root Causes**:
  1. `NCBI_API_KEY` not in LangSmith Cloud deployment secrets
  2. EvidenceLevel enum fails on string input "2" (expects "cohort_case_control")
- **Fix**: Add key to deployment + fix enum conversion at line ~667

---

## 4. API KEYS

### NCBI API Key (PubMed)
```
c4b8342072bcb0ee455fca68179a7d6d6408
```
- **Status**: VALID (10 req/sec)
- **Location**: Local `.env` only
- **Action**: MUST add to LangSmith Cloud deployment secrets

### Other Required Keys (check deployment secrets)
- `ANTHROPIC_API_KEY` - Claude
- `GOOGLE_API_KEY` - Gemini
- `PERPLEXITY_API_KEY` - Perplexity (working)
- `LANGCHAIN_API_KEY` - LangSmith tracing

---

## 5. HOW TO ADD SECRETS TO DEPLOYMENT

### Method 1: LangSmith UI
1. Go to https://smith.langchain.com
2. Navigate to Deployments → dhg-agents
3. Click Settings/Environment
4. Add `NCBI_API_KEY` as a secret

### Method 2: LangGraph SDK (Python)
```python
from langgraph_sdk import get_client

client = get_client(url="https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app")
# Use deployment management API endpoints
```

### Method 3: Create New Revision with Secrets
Deploy a new revision with environment variables specified in the deployment config.

---

## 6. GRAPH STRUCTURE

```
log_request
    ├──→ pubmed_search ──────┐
    └──→ perplexity_search ──┤
                              ↓
                    combine_results
                              ↓
                    validate_sources
                              ↓
                       synthesize
                              ↓
                      extract_gaps
                              ↓
                        finalize
                              ↓
                            END
```

---

## 7. CODE FIXES NEEDED

### Fix 1: finalize_node (line ~824)
```python
# CURRENT (broken):
return {}

# FIXED:
return {
    "synthesis": state.get("synthesis", ""),
    "clinical_gaps": state.get("clinical_gaps", []),
    "validated_citations": state.get("validated_citations", []),
    "key_findings": state.get("key_findings", []),
    "errors": state.get("errors", []),
    "messages": [HumanMessage(content=state.get("synthesis", "No synthesis"))]
}
```

### Fix 2: EvidenceLevel conversion (line ~667)
```python
# CURRENT (broken):
min_level = EvidenceLevel(state.get("minimum_evidence_level", "cohort_case_control"))

# FIXED:
level_input = state.get("minimum_evidence_level", "cohort_case_control")
if isinstance(level_input, str) and level_input.isdigit():
    level_map = {"1": "systematic_review_meta_analysis", "2": "lower_quality_rct", 
                 "3": "case_series", "4": "expert_opinion", "5": "narrative_review"}
    level_input = level_map.get(level_input, "cohort_case_control")
min_level = EvidenceLevel(level_input)
```

---

## 8. TEST INPUT JSON

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

---

## 9. LLM PROVIDERS

| Model | Provider | Use Case | Cost |
|-------|----------|----------|------|
| Claude Sonnet 4 | Anthropic | Complex synthesis | $0.015/1K out |
| Claude Haiku | Anthropic | Extraction | $0.004/1K out |
| Gemini 2.5 Flash | Google | Fast tasks | $0.001/1K out |
| Qwen 3 14B | Ollama | Cost-free local | $0.00 |

---

## 10. LIBRECHAT INTEGRATION (Separate)

- LibreChat config expects `http://dhg-research:8000/v1`
- This is OLD Docker agent, NOT LangSmith Cloud
- To use LangSmith: Point LibreChat to deployment URL instead

---

## 11. ACTION STEPS

1. **Add NCBI_API_KEY to deployment secrets** (via UI or API)
2. **Fix agent.py**:
   - finalize_node return statement
   - EvidenceLevel enum conversion
3. **Deploy new revision** to apply code fixes
4. **Test in Studio** with JSON input above
5. **Verify in trace** that PubMed and Perplexity both return results
