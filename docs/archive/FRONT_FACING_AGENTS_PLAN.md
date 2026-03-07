# Front-Facing Agent Completions Plan

**Goal:** 2 fully operational, front-facing agents in LibreChat

---

## Platform Role Summary

| Platform | Role | Status | RAG Integration |
|----------|------|--------|-----------------|
| **LibreChat** | Chat UI for all agents | ✅ Running :3010 | MCP/Tools |
| **Dify** | Workflow builder, no-code AI apps | ✅ Running :3000 | Built-in RAG |
| **RAGFlow** | Enterprise RAG pipeline | ✅ Running :8585 | Native |
| **LangSmith** | Agent tracing/debugging | ✅ Cloud | N/A (observability) |
| **LangGraph** | Multi-agent orchestration | Ready | Via tools |
| **Ollama** | Local LLM inference | ✅ Running :11434 | N/A |

### How They Interact

```
User → LibreChat → Agent (LangGraph) → RAGFlow/Dify for knowledge
                         ↓
                   LangSmith (tracing)
```

---

## Priority 1: CME Research Agent

**Current State:** Research agent exists at :8003, connected to registry

### What's Missing
1. [ ] LibreChat form/input UI (structured research request)
2. [ ] RAG integration (medical literature via RAGFlow)
3. [ ] Output templates (proposals, gap reports, podcast scripts)
4. [ ] End-to-end test in LibreChat

### Implementation Steps

#### A. LibreChat Form Integration
- Use LibreChat's **Artifacts** feature for structured input
- Create a research request form artifact
- Agent reads form data and processes

#### B. RAG Integration
- Connect to RAGFlow API for PubMed/medical literature
- Endpoint: `http://10.0.0.251:8585/api/v1/chat`
- Index CME content in RAGFlow knowledge base

#### C. Output Templates
- Already partially done (cme-agent-context.md)
- Templates: CME Proposal, Podcast Script, Gap Report, PowerPoint Outline

### Verification
- User submits research request in LibreChat
- Agent retrieves relevant literature via RAGFlow
- Agent generates formatted output
- Trace visible in LangSmith

---

## Priority 2: Visuals Agent with Control Panel

**Current State:** Visuals agent has XMP metadata, artifact registration

### What's Missing
1. [ ] Control panel UI for generation settings
2. [ ] Integration with LibreChat
3. [ ] Gallery for viewing generated images

### Streamlit in LibreChat?

**Answer:** Not directly. LibreChat doesn't embed Streamlit apps. 

**Better Options:**

| Option | Pros | Cons |
|--------|------|------|
| **LibreChat Artifacts** | Native, no extra infra | Limited customization |
| **Streamlit standalone** | Full control, rich widgets | Separate URL (e.g. :8501) |
| **Dify workflow** | Visual builder, embeddable | Learning curve |

**Recommendation:** 
1. **Quick win:** Use LibreChat's built-in UI + slash commands
2. **Full panel:** Deploy Streamlit at :8501, link from LibreChat

### Implementation Steps

#### A. LibreChat Integration
- Register Visuals agent as LibreChat endpoint
- `/visuals [prompt]` command for quick generation
- Use Artifacts panel for settings (style, size, compliance mode)

#### B. Streamlit Control Panel (optional)
- Standalone app at :8501
- Controls: style presets, dimensions, compliance mode
- Gallery view of generated images
- Metadata viewer (XMP details)

#### C. RAG for Brand Guidelines (future)
- Index brand guidelines in RAGFlow
- Agent queries for style consistency

---

## Suggested Execution Order

1. **CME Research Agent** (highest value)
   - Form in LibreChat
   - RAGFlow connection
   - Test end-to-end

2. **Visuals Agent**
   - Basic LibreChat integration first
   - Streamlit panel later

---

## Decision Required

1. **CME first or Visuals first?**
2. **Streamlit for Visuals: yes/no/later?**
3. **RAGFlow knowledge base: what content to index first?**
