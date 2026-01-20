# DHG AI Factory - Master To-Do List
**Last Updated:** Jan 20, 2026 12:27 PM

## System Status
- **Running Containers:** 38
- **Stopped Containers:** 16
- **Key Services:** All healthy
- **Code Audit:** Passed (Jan 20)

---

## P0: Blockers - CLEAR

No blockers.

---

## P1: This Sprint

### CME Pipeline Endpoints

**Step 1: Research Agent** ✅ COMPLETE
- [x] All 6 endpoints implemented and tested

**Step 2: Curriculum Agent** (IN PROGRESS)
- [ ] /design - Full curriculum design
- [ ] /objectives/generate - Learning objectives
- [ ] /map - Objective mapping to Moore/ICD-10/QI
- [ ] /outline - Activity outline
- [ ] /faculty-brief - Instructor brief
- [ ] /assessment - Assessment design
- [ ] /templates - Template retrieval

### LibreChat Features
- [x] **Web Search (Tavily)** - Configured Jan 18
- [x] **Memory** - Enabled Jan 20 (Claude backend)
- [x] **MCP Integration** - Enabled Jan 20
- [ ] **Artifacts** - Verify CSP headers

### Security
- [ ] **Build DHG Security Agent** (2 hrs)

### LibreChat Enhancements
- [ ] **Publish Google OAuth App**

### Pending API Keys
- [ ] **Consensus API** - Application submitted, awaiting approval

### LibreChat Help Integration
- [ ] **Footer Links** - Link to /docs/help/
- [ ] **Slash Commands** - /help [agent-name]
- [ ] **Help Index Page** - README.md with all agents

### User Help Files (Complete as agents are built)
- [x] Research Agent - Complete
- [ ] Medical LLM Agent
- [ ] Curriculum Agent
- [ ] Visuals Agent
- [ ] Outcomes Agent
- [ ] QA Compliance Agent
- [ ] Competitor Intel Agent
- [ ] Orchestrator Agent
- [ ] Transcription Agent

---

## P2: Support Agent Endpoints

**Competitor Intel Agent** (10 endpoints)
**Orchestrator** /registry/log

---

## P3: Video Content Pipeline (7 items)

## P4: Creator Harmony Platform (4 items)

## P5: Backlog (11 items)

---

## Standard Requirements for All New Agents/Features

Going forward, every agent or feature must include:
1. ✅ Production-ready code (no stubs, no TODOs)
2. ✅ Non-technical user guide in /docs/help/
3. ✅ Example prompts tested in LibreChat
4. ✅ Integration with help system (footer + slash commands)

---

## Completed (Jan 20, 2026)

- [x] **Research Agent fully implemented** (6 endpoints)
  - Perplexity API integration
  - PubMed/NCBI API integration
  - Source status monitoring
  - URL validation with retry
  - Cache stats and clear
- [x] **Research Agent User Guide** created
- [x] **Help File Implementation Plan** approved
- [x] Code Quality Audit - Passed
- [x] Memory feature enabled
- [x] MCP Servers enabled
- [x] Committed 12+ changes

## Previously Completed

- [x] LibreChat custom endpoints
- [x] All DHG agents configured in LibreChat (10)
- [x] Tavily Web Search, Google OAuth
- [x] Infisical secrets management
- [x] Registry database tables created
