# DHG AI Factory - Master To-Do List
**Last Updated:** Jan 25, 2026 11:42 AM

## System Status
- **Running Containers:** 12 (11 healthy + 1 no healthcheck)
- **Key Services:** All healthy (8011, 8002, 8003, 3010 responding)
- **Agents Implemented:** 3 Docker agents + 1 LangGraph agent
- **Total Endpoints:** 23 Docker + LangGraph workflow
- **LangGraph Dev Server:** Running on port 2026
- **Current Branch:** feature/langgraph-migration
- **Latest Commit:** 0e7b095 (LangGraph Research Agent)

---

## P0: Blockers - CLEAR

No blockers.

---

## P1: This Sprint - LangGraph Migration & CME Agent

### LangGraph Cloud Research Agent ✅ **IN PROGRESS** (Jan 21-25, 2026)

**Completed:**
- [x] Agent.py (1,057 lines) - Full implementation
- [x] Multi-LLM routing (Claude, Gemini, Ollama)
- [x] PubMed integration with evidence grading
- [x] Perplexity integration for web research
- [x] Template renderer system (5 output formats)
- [x] Feedback loop integration
- [x] LangSmith tracing (@traceable decorators)
- [x] LangGraph dev server running on port 2026
- [x] Connected to LangSmith Studio (tested)

**Pending:**
- [ ] Database flows (registry integration)
- [x] Full LangSmith Cloud Suite setup (parallel graph implemented)
- [ ] Assistants configuration
- [ ] Production deployment verification

### Template System ✅ **COMPLETE** (Jan 24, 2026)
- [x] renderer.py - 5 output formats
  - JSON (default)
  - CME Proposal
  - Podcast Script  
  - Gap Report
  - PowerPoint Outline
- [x] AgentState includes output_format field
- [x] Auto-rendering on agent completion

### CME Pipeline (Docker Agents)

**Step 1: Research Agent** ✅ **COMPLETE** (Jan 20, 2026)
- [x] All 6 endpoints implemented and tested
- [x] Perplexity API integration
- [x] PubMed integration
- [x] URL validation and cache management

**Step 2: Curriculum Agent** ✅ **COMPLETE** (Jan 20, 2026)
- [x] 7 endpoints implemented

**Step 3: Competitor Intelligence Agent** ✅ **COMPLETE** (Jan 20, 2026)
- [x] 10 endpoints implemented

---

## P1.5: LangSmith Cloud Suite Setup

### Required for Research Agent Operations
- [ ] **LangSmith Studio verification** - Test all nodes in playground
- [ ] **Assistants API setup** - Configure via LangSmith
- [ ] **Tracing dashboard** - Verify traces appearing
- [ ] **Evaluation datasets** - Create test cases
- [ ] **Feedback collection** - Enable user feedback

### Database Integration
- [ ] **Registry research schemas** - registry_research_schemas.py deployed
- [ ] **Migrations** - 001_add_agents.sql, 002_add_research_requests.sql
- [ ] **Research endpoints** - registry/research_endpoints.py integration
- [ ] **Agent endpoints** - registry/agent_endpoints.py integration

---

## P2: DHG Agent Template & SOPs

### Agent Development Templates
- [ ] **Create base agent template** - Standardized structure
- [ ] **LangGraph agent template** - Cloud-ready boilerplate
- [ ] **Docker agent template** - FastAPI-based template

### SOPs (Markdown for AI use)
- [ ] **AGENT_CREATION_SOP.md** - Step-by-step agent creation guide
- [ ] **LANGGRAPH_CLOUD_SOP.md** - LangSmith Cloud deployment guide
- [ ] **TESTING_SOP.md** - Agent testing protocol
- [ ] **DEBUGGING_SOP.md** - Troubleshooting guide

---

## P3: Support Agent Endpoints

### Next Agents to Implement
**Priority Order:**
1. **Outcomes Agent** - Measure CME effectiveness (Moore Level 5-7)
2. **QA/Compliance Agent** - ACCME compliance checking
3. **Scribe Agent** - Documentation generation

---

## P4: Security & Maintenance

- [ ] **Build DHG Security Agent** (2 hrs)
- [ ] **Address GitHub security vulnerabilities** (17 flagged)
- [ ] **Publish Google OAuth App**
- [ ] **Consensus API** - Application submitted, awaiting approval

---

## P5: Documentation & Help

### LibreChat Help Integration
- [ ] **Footer Links** - Link to /docs/help/
- [ ] **Slash Commands** - /help [agent-name]
- [ ] **Help Index Page** - README.md with all agents

### User Help Files
- [x] Research Agent - Complete
- [x] Curriculum Agent - Complete
- [x] Competitor Intel Agent - Complete
- [ ] Medical LLM Agent
- [ ] Visuals Agent
- [ ] Outcomes Agent
- [ ] QA Compliance Agent
- [ ] Orchestrator Agent
- [ ] Transcription Agent

---

## Recent Accomplishments (Jan 21-25, 2026)

### LangGraph Migration
- [x] Created LangGraph Cloud-ready Research Agent (agent.py - 1,057 lines)
- [x] Implemented multi-LLM routing (Claude/Gemini/Ollama)
- [x] Added template rendering system (5 output formats)
- [x] Set up LangGraph dev server on port 2026
- [x] Connected to LangSmith Studio
- [x] Added feedback loop integration
- [x] Transferred all Mac session files to .251 server

### Architecture Documentation
- [x] DHG_LANGSMITH_ARCHITECTURE.md
- [x] GRAPH_VISUALIZATION_GUIDE.md
- [x] DHG_Architecture_Diagram.png
- [x] ANTIGRAVITY_MCP_SETUP.md

### Files Organized on Server
- docs/architecture/ - Architecture docs and diagrams
- tools/mcp-servers/ - MCP server implementations
- langgraph_workflows/dhg-cme-research-agent-cloud/src/ - LangGraph agent
- registry/ - Database schemas and endpoints
- scripts/ - Deployment scripts

---

## Key Metrics
- **Docker Agents:** 3 complete (Research, Curriculum, Competitor Intel)
- **LangGraph Agents:** 1 in progress (CME Research Agent)
- **Docker Endpoints:** 23 working
- **Containers Healthy:** 11/12
- **LangGraph Dev Server:** Running
- **Git Branch:** feature/langgraph-migration
- **Uncommitted Files:** 25+ (ready for commit)

---

## Next Session Priorities
1. ✅ Update TODO.md (this update)
2. Complete LangSmith Cloud Suite setup
3. Finish database integration for Research Agent
4. Create DHG agent templates
5. Write agent creation SOPs
