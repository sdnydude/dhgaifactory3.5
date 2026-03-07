# DHG AI Factory - Agent Model Canvas

**Generated:** January 15, 2026

---

## 1. Medical LLM Agent

| Attribute | Value |
|-----------|-------|
| **Port** | 8002 |
| **Container** | dhg-medical-llm |
| **Primary Model** | Ollama medllama2 |
| **Fallback Models** | OpenAI GPT-4, Anthropic Claude (not configured) |
| **Purpose** | Medical content generation, ICD-10 extraction, clinical NER |
| **Capabilities** | Extract ICD-10 codes, suggest quality measures, summarize guidelines, identify SDOH |
| **Status** | ✅ Working - Returns real LLM responses |

### Sample Use Cases
- Generate needs assessments for CME topics
- Extract clinical entities from text
- Summarize medical guidelines (ACR, ACC/AHA, ADA)

---

## 2. Research Agent

| Attribute | Value |
|-----------|-------|
| **Port** | 8003 |
| **Container** | dhg-research |
| **Primary Sources** | PubMed, ClinicalTrials.gov, CDC WONDER (not connected) |
| **Fallback** | Perplexity API, Consensus |
| **Purpose** | Literature search and evidence synthesis |
| **Status** | ⚠️ Stub - Returns "Agent received" (APIs not connected) |

### Sample Use Cases
- Search PubMed for recent studies on a topic
- Find active clinical trials
- Synthesize evidence from multiple sources

---

## 3. Curriculum Agent

| Attribute | Value |
|-----------|-------|
| **Port** | 8004 |
| **Container** | dhg-curriculum |
| **Purpose** | CME curriculum design and learning objective generation |
| **Capabilities** | Moore Levels mapping, ICD-10 alignment, QI measures mapping |
| **Status** | ⚠️ Stub - Returns "Agent received" |

### Sample Use Cases
- Generate learning objectives for a CME activity
- Map content to Moore Levels (1-7)
- Align curriculum with quality measures

---

## 4. Outcomes Agent

| Attribute | Value |
|-----------|-------|
| **Port** | 8005 |
| **Container** | dhg-outcomes |
| **Purpose** | Assessment design and outcomes measurement |
| **Moore Levels** | Supports all 7 levels |
| **Assessment Types** | Pre, Post, 6-week follow-up |
| **Status** | ⚠️ Stub - Returns "Agent received" |

### Sample Use Cases
- Design pre/post assessments
- Create follow-up surveys
- Measure knowledge retention

---

## 5. Competitor Intel Agent

| Attribute | Value |
|-----------|-------|
| **Port** | 8006 |
| **Container** | dhg-competitor-intel |
| **Configured Sources** | ACCME, Medscape, WebMD |
| **Purpose** | Competitive intelligence gathering |
| **Status** | ⚠️ Stub - Scrapers not implemented |

### Sample Use Cases
- Monitor competitor CME offerings
- Track ACCME accreditation status
- Alert on new competitor activities

---

## 6. QA Compliance Agent

| Attribute | Value |
|-----------|-------|
| **Port** | 8007 |
| **Container** | dhg-qa-compliance |
| **Rules Loaded** | 9 ACCME rules |
| **Strict Mode** | Enabled |
| **Purpose** | Content validation and compliance checking |
| **Status** | ⚠️ Partial - Rules loaded, validation not fully implemented |

### Sample Use Cases
- Validate content against ACCME standards
- Check for commercial bias
- Ensure fair balance in presentations

---

## 7. Visuals Agent

| Attribute | Value |
|-----------|-------|
| **Port** | 8008 |
| **Container** | dhg-visuals-media |
| **Primary Model** | Nano Banana Pro (Gemini 3 Pro Image) |
| **Visual Types** | 20 (infographic, slide, chart, diagram, etc.) |
| **Purpose** | Medical visualization and image generation |
| **Status** | ✅ Working - Generates images via Gemini API |

### Sample Use Cases
- Generate medical infographics
- Create presentation slides
- Design anatomical diagrams

---

## 8. Orchestrator

| Attribute | Value |
|-----------|-------|
| **Port** | 8011 |
| **Container** | dhg-aifactory-orchestrator |
| **LangGraph** | Ready |
| **Purpose** | Multi-agent workflow coordination |
| **Status** | ⚠️ Missing /v1/chat/completions endpoint |

### Sample Use Cases
- Coordinate full CME pipeline
- Route requests to appropriate agents
- Manage multi-step workflows

---

## 9. LogoMaker Agent

| Attribute | Value |
|-----------|-------|
| **Port** | 8012 |
| **Container** | dhg-logo-maker |
| **Primary Model** | Nano Banana Pro (Gemini 3 Pro Image) |
| **Storage** | /mnt/4tb/dhg-storage/logo-maker |
| **Purpose** | Premium logo and icon set generation |
| **Status** | ✅ Working - Fortune 500 quality outputs |

### Sample Use Cases
- Generate brand logos
- Create icon sets for apps
- Design visual identities

---

## 10. Perplexity (External)

| Attribute | Value |
|-----------|-------|
| **Type** | External API |
| **Models** | sonar, sonar-pro, sonar-reasoning-pro |
| **Purpose** | Web search with citations |
| **Status** | ✅ Working (message alternation required) |

### Sample Use Cases
- Real-time web research
- Fact-checking with citations
- Current events queries

---

## Summary Status

| Agent | Direct API | LibreChat Integration | Full Functionality |
|-------|------------|----------------------|-------------------|
| Medical LLM | ✅ | ✅ (forcePrompt) | ✅ |
| Research | ✅ | ✅ (forcePrompt) | ⚠️ Stub |
| Curriculum | ✅ | ✅ (forcePrompt) | ⚠️ Stub |
| Outcomes | ✅ | ✅ (forcePrompt) | ⚠️ Stub |
| Competitor | ✅ | ✅ (forcePrompt) | ⚠️ Stub |
| QA | ✅ | ✅ (forcePrompt) | ⚠️ Partial |
| Visuals | ✅ | ✅ (forcePrompt) | ✅ |
| Orchestrator | ✅ (health) | ⚠️ Missing endpoint | ⚠️ |
| LogoMaker | ✅ | ✅ (forcePrompt) | ✅ |
| Perplexity | ✅ | ⚠️ Message format | ✅ |
