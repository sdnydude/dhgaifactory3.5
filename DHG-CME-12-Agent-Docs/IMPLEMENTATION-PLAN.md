# DHG CME 12-Agent System
## Full Implementation Plan

**Version:** 1.0  
**Date:** January 31, 2026  
**Owner:** Digital Harmony Group  
**Classification:** Internal Technical Documentation

---

# Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Infrastructure Requirements](#4-infrastructure-requirements)
5. [Phase 1: Foundation](#5-phase-1-foundation)
6. [Phase 2: Core Agents](#6-phase-2-core-agents)
7. [Phase 3: Quality & Compliance](#7-phase-3-quality--compliance)
8. [Phase 4: Integration & UI](#8-phase-4-integration--ui)
9. [Phase 5: Testing & Validation](#9-phase-5-testing--validation)
10. [Phase 6: Deployment](#10-phase-6-deployment)
11. [Operations & Maintenance](#11-operations--maintenance)
12. [Risk Mitigation](#12-risk-mitigation)
13. [Budget & Timeline](#13-budget--timeline)
14. [Appendices](#14-appendices)

---

# 1. Executive Summary

## 1.1 Project Overview

The DHG CME 12-Agent System automates pharmaceutical-grade continuing medical education (CME) grant documentation. The system transforms a 47-field intake form into complete, ACCME-compliant grant packages through orchestrated AI agents.

## 1.2 Business Objectives

| Objective | Target | Measurement |
|-----------|--------|-------------|
| Reduce grant development time | 80% reduction | Hours per grant |
| Maintain quality standards | 95% first-pass approval | Supporter acceptance rate |
| Scale grant capacity | 10x throughput | Grants per month |
| Ensure compliance | 100% ACCME compliant | Audit results |

## 1.3 Deliverables

1. **Production System** - Fully operational 12-agent pipeline
2. **User Interface** - LibreChat-based intake and monitoring
3. **Documentation** - Technical and operational guides
4. **Training Materials** - Staff onboarding resources

## 1.4 Success Criteria

- [ ] Complete grant package generated from intake in <4 hours
- [ ] Needs assessment passes prose quality on first attempt >80%
- [ ] Zero ACCME compliance failures in production
- [ ] Human review approval rate >90%

---

# 2. System Architecture

## 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  LibreChat UI  │  Admin Dashboard  │  API Clients  │  Webhook Receivers     │
└────────┬───────┴────────┬──────────┴───────┬───────┴──────────┬─────────────┘
         │                │                  │                  │
         ▼                ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API GATEWAY                                       │
│                     (FastAPI + Authentication)                               │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                  │
│                    (LangGraph StateGraph Engine)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  State Management  │  Routing Logic  │  Quality Gates  │  Checkpointing     │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  AGENT LAYER    │   │  AGENT LAYER    │   │  AGENT LAYER    │
│  (12 Agents)    │   │  (Parallel)     │   │  (Quality)      │
├─────────────────┤   ├─────────────────┤   ├─────────────────┤
│ Research        │   │ Curriculum      │   │ Prose Quality   │
│ Clinical        │   │ Protocol        │   │ Compliance      │
│ Gap Analysis    │   │ Marketing       │   │                 │
│ Needs Assess.   │   │                 │   │                 │
│ Objectives      │   │                 │   │                 │
│ Grant Writer    │   │                 │   │                 │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL     │  pgvector        │  Redis          │  S3/MinIO           │
│  (State Store)  │  (Embeddings)    │  (Cache/Queue)  │  (Documents)        │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OBSERVABILITY LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  LangSmith      │  Prometheus      │  Grafana        │  Loki               │
│  (Traces)       │  (Metrics)       │  (Dashboards)   │  (Logs)             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Agent Execution Flow

```
INTAKE FORM (47 fields)
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│                    PARALLEL EXECUTION 1                       │
│  ┌─────────────────┐          ┌─────────────────┐            │
│  │ Agent 2:        │          │ Agent 3:        │            │
│  │ Research        │          │ Clinical        │            │
│  │ (Literature,    │          │ (Practice,      │            │
│  │  Epidemiology)  │          │  Barriers)      │            │
│  └────────┬────────┘          └────────┬────────┘            │
│           │                            │                      │
│           └────────────┬───────────────┘                      │
└────────────────────────┼─────────────────────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Agent 4:            │
              │ Gap Analysis        │
              │ (5-8 prioritized    │
              │  educational gaps)  │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Agent 5:            │
              │ Needs Assessment    │
              │ (3,100+ word doc    │
              │  with cold open)    │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Agent 11:           │
              │ Prose Quality       │
              │ [PASS 1]            │
              └──────────┬──────────┘
                    Pass │ Fail → Retry (max 3)
                         ▼
              ┌─────────────────────┐
              │ Agent 6:            │
              │ Learning Objectives │
              │ (Moore's Framework) │
              └──────────┬──────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    PARALLEL EXECUTION 2                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ Agent 7:     │  │ Agent 8:     │  │ Agent 9:     │        │
│  │ Curriculum   │  │ Protocol     │  │ Marketing    │        │
│  │ Design       │  │ (IRB-ready)  │  │ Plan         │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                 │                 │                 │
│         └─────────────────┼─────────────────┘                 │
└───────────────────────────┼──────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────┐
              │ Agent 10:           │
              │ Grant Writer        │
              │ (Complete package   │
              │  assembly)          │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Agent 11:           │
              │ Prose Quality       │
              │ [PASS 2]            │
              └──────────┬──────────┘
                    Pass │ Fail → Retry (max 3)
                         ▼
              ┌─────────────────────┐
              │ Agent 12:           │
              │ Compliance Review   │
              │ (ACCME standards)   │
              └──────────┬──────────┘
                 Compliant│ Non-compliant → Route to fix
                         ▼
              ┌─────────────────────┐
              │ HUMAN REVIEW GATE   │
              │ (Required approval) │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ FINAL OUTPUT        │
              │ (Complete grant     │
              │  package)           │
              └─────────────────────┘
```

## 2.3 Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        STATE OBJECT                              │
│                    (CMEGrantState TypedDict)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  intake: IntakeData (47 fields)                                 │
│    ├── section_a: ProjectBasics                                 │
│    ├── section_b: EducationalContext                            │
│    ├── section_c: SupporterInfo                                 │
│    ├── section_d: ActivityFormat                                │
│    ├── section_e: Accreditation                                 │
│    ├── section_f: ClinicalContent                               │
│    ├── section_g: FacultySpecs                                  │
│    ├── section_h: AudienceDetails                               │
│    ├── section_i: Timeline                                      │
│    └── section_j: SpecialRequirements                           │
│                                                                  │
│  research_output: ResearchOutput                                │
│  clinical_output: ClinicalOutput                                │
│  gap_analysis_output: GapAnalysisOutput                         │
│  needs_assessment_output: NeedsAssessmentOutput                 │
│  learning_objectives_output: LearningObjectivesOutput           │
│  curriculum_output: CurriculumOutput                            │
│  protocol_output: ProtocolOutput                                │
│  marketing_output: MarketingOutput                              │
│  grant_package_output: GrantPackageOutput                       │
│                                                                  │
│  prose_quality_scores: List[ProseQualityScore]                  │
│  compliance_score: ComplianceScore                              │
│                                                                  │
│  execution_history: List[ExecutionRecord]                       │
│  errors: List[ErrorRecord]                                      │
│  human_review_status: HumanReviewStatus                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

# 3. Technology Stack

## 3.1 Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Orchestration | LangGraph | 0.2.x | StateGraph workflow management |
| LLM Provider | Anthropic Claude | claude-3-5-sonnet | Primary agent intelligence |
| LLM Backup | OpenAI GPT-4 | gpt-4-turbo | Fallback provider |
| Database | PostgreSQL | 16.x | State persistence, checkpointing |
| Vector Store | pgvector | 0.7.x | Semantic search, embeddings |
| Cache | Redis | 7.x | Session cache, rate limiting |
| Message Queue | Redis Streams | 7.x | Async task processing |
| Object Storage | MinIO | Latest | Document storage |
| Frontend | LibreChat | Latest | User interface |
| API Framework | FastAPI | 0.109.x | REST API layer |
| Containerization | Docker | 24.x | Service isolation |
| Container Orchestration | Docker Compose | 2.x | Local/staging deployment |
| Observability | LangSmith | Latest | Trace monitoring |
| Metrics | Prometheus | 2.x | System metrics |
| Dashboards | Grafana | 10.x | Visualization |
| Logs | Loki | 2.x | Log aggregation |

## 3.2 Python Dependencies

```toml
# pyproject.toml

[project]
name = "dhg-cme-agents"
version = "2.0.0"
requires-python = ">=3.11"

dependencies = [
    # Core
    "langgraph>=0.2.0",
    "langchain>=0.2.0",
    "langchain-anthropic>=0.1.0",
    "langchain-openai>=0.1.0",
    
    # Database
    "psycopg[binary]>=3.1.0",
    "sqlalchemy>=2.0.0",
    "pgvector>=0.2.0",
    "redis>=5.0.0",
    
    # API
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    
    # Utilities
    "httpx>=0.26.0",
    "tenacity>=8.2.0",
    "structlog>=24.1.0",
    "python-dotenv>=1.0.0",
    
    # Document processing
    "pypdf>=3.17.0",
    "python-docx>=1.1.0",
    "markdown>=3.5.0",
    
    # Observability
    "langsmith>=0.1.0",
    "prometheus-client>=0.19.0",
    "opentelemetry-api>=1.22.0",
    "opentelemetry-sdk>=1.22.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "black>=24.1.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]
```

## 3.3 Infrastructure Components

```yaml
# docker-compose.yml (overview)

services:
  # Application Services
  api:
    image: dhg-cme-api:latest
    ports: ["8000:8000"]
    
  worker:
    image: dhg-cme-worker:latest
    replicas: 3
    
  librechat:
    image: librechat:latest
    ports: ["3080:3080"]
  
  # Data Services
  postgres:
    image: postgres:16
    volumes: ["postgres_data:/var/lib/postgresql/data"]
    
  redis:
    image: redis:7-alpine
    volumes: ["redis_data:/data"]
    
  minio:
    image: minio/minio:latest
    volumes: ["minio_data:/data"]
  
  # Observability
  prometheus:
    image: prom/prometheus:latest
    
  grafana:
    image: grafana/grafana:latest
    
  loki:
    image: grafana/loki:latest
```

---

# 4. Infrastructure Requirements

## 4.1 Compute Requirements

### Development Environment
| Resource | Specification |
|----------|--------------|
| CPU | 4 cores |
| RAM | 16 GB |
| Storage | 100 GB SSD |
| GPU | Not required |

### Staging Environment
| Resource | Specification |
|----------|--------------|
| CPU | 8 cores |
| RAM | 32 GB |
| Storage | 250 GB SSD |
| GPU | Optional (for local embeddings) |

### Production Environment
| Resource | Specification |
|----------|--------------|
| API Server | 4 vCPU, 16 GB RAM × 2 (HA) |
| Worker Nodes | 8 vCPU, 32 GB RAM × 3 |
| Database | 4 vCPU, 32 GB RAM, 500 GB SSD |
| Redis | 2 vCPU, 8 GB RAM |
| Object Storage | 1 TB |

## 4.2 Network Requirements

```
┌─────────────────────────────────────────────────────────────────┐
│                        NETWORK TOPOLOGY                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│  │   Public    │     │   Private   │     │  Database   │       │
│  │   Subnet    │────▶│   Subnet    │────▶│   Subnet    │       │
│  │             │     │             │     │             │       │
│  │ • Load      │     │ • API       │     │ • PostgreSQL│       │
│  │   Balancer  │     │ • Workers   │     │ • Redis     │       │
│  │ • LibreChat │     │ • Internal  │     │ • MinIO     │       │
│  │             │     │   Services  │     │             │       │
│  └─────────────┘     └─────────────┘     └─────────────┘       │
│                                                                  │
│  Firewall Rules:                                                │
│  • Public → Private: 443 (HTTPS), 3080 (LibreChat)             │
│  • Private → Database: 5432 (PG), 6379 (Redis), 9000 (MinIO)   │
│  • Private → External: 443 (Anthropic API, LangSmith)          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 4.3 External Service Dependencies

| Service | Purpose | Estimated Usage | Cost Estimate |
|---------|---------|-----------------|---------------|
| Anthropic API | LLM inference | ~500K tokens/grant | $7-15/grant |
| LangSmith | Observability | Unlimited traces | $400/month |
| PubMed API | Literature search | 1000 req/day | Free |
| OpenAI API | Backup/embeddings | 50K tokens/grant | $1-2/grant |

## 4.4 Security Requirements

### Authentication & Authorization
- [ ] OAuth 2.0 / OIDC integration
- [ ] Role-based access control (RBAC)
- [ ] API key management with rotation
- [ ] JWT token validation

### Data Protection
- [ ] TLS 1.3 for all connections
- [ ] Encryption at rest (AES-256)
- [ ] PII handling compliance
- [ ] Audit logging

### Secrets Management
- [ ] Infisical vault integration
- [ ] Environment-based secret injection
- [ ] No secrets in code or logs

---

# 5. Phase 1: Foundation

**Duration:** 2 weeks  
**Goal:** Establish infrastructure and core framework

## 5.1 Tasks

### Week 1: Infrastructure Setup

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P1-001 | Provision development environment | DevOps | ☐ |
| P1-002 | Set up Docker Compose stack | DevOps | ☐ |
| P1-003 | Configure PostgreSQL with pgvector | DevOps | ☐ |
| P1-004 | Set up Redis for caching | DevOps | ☐ |
| P1-005 | Configure MinIO for document storage | DevOps | ☐ |
| P1-006 | Establish Infisical vault | DevOps | ☐ |
| P1-007 | Set up LangSmith project | DevOps | ☐ |

### Week 2: Framework Foundation

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P1-008 | Create Python project structure | Dev | ☐ |
| P1-009 | Implement state schema (TypedDict) | Dev | ☐ |
| P1-010 | Create base agent class | Dev | ☐ |
| P1-011 | Implement LangGraph skeleton | Dev | ☐ |
| P1-012 | Set up checkpoint persistence | Dev | ☐ |
| P1-013 | Create intake form validation | Dev | ☐ |
| P1-014 | Implement basic API endpoints | Dev | ☐ |

## 5.2 Deliverables

1. **Running Infrastructure**
   - Docker Compose stack operational
   - All services healthy and connected
   - Secrets management configured

2. **Code Foundation**
   - Project structure established
   - State schema implemented
   - Basic graph executing (placeholder nodes)

3. **Documentation**
   - Infrastructure setup guide
   - Development environment guide

## 5.3 Acceptance Criteria

- [ ] `docker-compose up` brings up all services
- [ ] PostgreSQL checkpoint table created
- [ ] Empty graph executes start-to-end
- [ ] LangSmith traces appear
- [ ] API health check returns 200

## 5.4 Project Structure

```
dhg-cme-agents/
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Settings and configuration
│   │
│   ├── state/
│   │   ├── __init__.py
│   │   ├── schema.py              # CMEGrantState TypedDict
│   │   └── validators.py          # State validation
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── definition.py          # StateGraph construction
│   │   ├── nodes.py               # Node function registry
│   │   └── routing.py             # Conditional edge logic
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                # BaseAgent class
│   │   ├── research.py            # Agent 2
│   │   ├── clinical.py            # Agent 3
│   │   ├── gap_analysis.py        # Agent 4
│   │   ├── needs_assessment.py    # Agent 5
│   │   ├── learning_objectives.py # Agent 6
│   │   ├── curriculum.py          # Agent 7
│   │   ├── protocol.py            # Agent 8
│   │   ├── marketing.py           # Agent 9
│   │   ├── grant_writer.py        # Agent 10
│   │   ├── prose_quality.py       # Agent 11
│   │   └── compliance.py          # Agent 12
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── pubmed.py              # PubMed search
│   │   ├── guidelines.py          # Guidelines lookup
│   │   ├── registry.py            # Registry data
│   │   └── market.py              # Market intelligence
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── research.py
│   │   ├── clinical.py
│   │   └── ...                    # One per agent
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── intake.py
│   │   │   ├── projects.py
│   │   │   └── health.py
│   │   └── middleware/
│   │       ├── auth.py
│   │       └── logging.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── db.py                  # Database utilities
│       ├── storage.py             # MinIO utilities
│       └── observability.py       # Metrics/logging
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_state.py
│   │   ├── test_agents/
│   │   └── test_tools/
│   ├── integration/
│   │   ├── test_graph.py
│   │   └── test_api.py
│   └── e2e/
│       └── test_pipeline.py
│
├── shared_resources/
│   ├── cold_open_framework.md
│   ├── moores_framework.md
│   └── writing_style_guide.md
│
├── docker/
│   ├── Dockerfile
│   ├── Dockerfile.worker
│   └── docker-compose.yml
│
├── scripts/
│   ├── setup_db.py
│   ├── seed_data.py
│   └── run_pipeline.py
│
├── pyproject.toml
├── README.md
└── .env.example
```

---

# 6. Phase 2: Core Agents

**Duration:** 4 weeks  
**Goal:** Implement all 12 agents with full functionality

## 6.1 Week 3-4: Research & Analysis Agents

### Agent 2: Research Agent

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P2-001 | Implement PubMed search tool | Dev | ☐ |
| P2-002 | Implement guidelines search tool | Dev | ☐ |
| P2-003 | Implement epidemiology lookup tool | Dev | ☐ |
| P2-004 | Implement market intelligence tool | Dev | ☐ |
| P2-005 | Create research agent prompt | Dev | ☐ |
| P2-006 | Implement research agent logic | Dev | ☐ |
| P2-007 | Create output schema validation | Dev | ☐ |
| P2-008 | Write unit tests | Dev | ☐ |

**Agent Implementation Template:**

```python
# src/agents/research.py

from typing import Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import BaseAgent
from src.state.schema import CMEGrantState, ResearchOutput
from src.tools.pubmed import PubMedSearchTool
from src.tools.guidelines import GuidelinesSearchTool
from src.tools.registry import EpidemiologyTool
from src.tools.market import MarketIntelligenceTool
from src.prompts.research import RESEARCH_SYSTEM_PROMPT


class ResearchAgent(BaseAgent):
    """Agent 2: Literature review, epidemiology, market intelligence."""
    
    name = "research_agent"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Initialize LLM
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=0.1,
            max_tokens=8192,
        )
        
        # Initialize tools
        self.tools = [
            PubMedSearchTool(),
            GuidelinesSearchTool(),
            EpidemiologyTool(),
            MarketIntelligenceTool(),
        ]
        
        # Create agent
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", RESEARCH_SYSTEM_PROMPT),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            return_intermediate_steps=True,
        )
    
    async def run(self, state: CMEGrantState) -> CMEGrantState:
        """Execute research agent."""
        # Extract relevant intake fields
        intake = state["intake"]
        input_data = {
            "therapeutic_area": intake["section_a"]["therapeutic_area"],
            "disease_state": intake["section_a"]["disease_state"],
            "target_audience": intake["section_a"]["target_audience_primary"],
            "clinical_topics": intake["section_f"]["key_clinical_topics"],
            "treatment_focus": intake["section_f"]["treatment_focus"],
            "guideline_references": intake["section_f"]["guideline_references"],
            "supporter_products": intake["section_c"]["supporter_products"],
            "competitor_products": intake["section_f"]["competitor_products"],
        }
        
        # Execute agent
        result = await self.executor.ainvoke({
            "input": self._format_input(input_data)
        })
        
        # Parse and validate output
        research_output = self._parse_output(result["output"])
        
        # Update state
        state["research_output"] = research_output
        
        return state
    
    def _format_input(self, data: Dict[str, Any]) -> str:
        """Format input data for agent prompt."""
        return f"""
        Conduct comprehensive research for a CME grant on:
        
        Therapeutic Area: {data['therapeutic_area']}
        Disease State: {data['disease_state']}
        Target Audience: {', '.join(data['target_audience'])}
        
        Clinical Topics to Address:
        {chr(10).join(f'- {topic}' for topic in data['clinical_topics'])}
        
        Treatment Focus:
        {chr(10).join(f'- {t}' for t in data['treatment_focus'])}
        
        Key Guidelines:
        {chr(10).join(f'- {g}' for g in data['guideline_references'])}
        
        Products to Include (for balance):
        - Supporter: {', '.join(data['supporter_products'])}
        - Competitors: {', '.join(data['competitor_products'])}
        
        Provide:
        1. Epidemiology data with citations
        2. Economic burden statistics
        3. Treatment landscape overview
        4. Market intelligence summary
        5. Literature synthesis
        
        Minimum 30 citations required, 70%+ from past 5 years.
        """
    
    def _parse_output(self, raw_output: str) -> ResearchOutput:
        """Parse agent output into structured format."""
        # Implementation would parse the LLM output
        # into the ResearchOutput TypedDict structure
        pass
```

### Agent 3: Clinical Practice Agent

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P2-009 | Implement registry data query tool | Dev | ☐ |
| P2-010 | Implement claims analysis tool | Dev | ☐ |
| P2-011 | Implement practice survey tool | Dev | ☐ |
| P2-012 | Create clinical agent prompt | Dev | ☐ |
| P2-013 | Implement clinical agent logic | Dev | ☐ |
| P2-014 | Create barrier classification logic | Dev | ☐ |
| P2-015 | Write unit tests | Dev | ☐ |

### Agent 4: Gap Analysis Agent

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P2-016 | Create gap synthesis logic | Dev | ☐ |
| P2-017 | Implement prioritization scoring | Dev | ☐ |
| P2-018 | Create gap validation checklist | Dev | ☐ |
| P2-019 | Implement gap agent prompt | Dev | ☐ |
| P2-020 | Write unit tests | Dev | ☐ |

## 6.2 Week 5-6: Document Generation Agents

### Agent 5: Needs Assessment Agent

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P2-021 | Implement cold open generator | Dev | ☐ |
| P2-022 | Create character thread tracker | Dev | ☐ |
| P2-023 | Implement section generators | Dev | ☐ |
| P2-024 | Create banned pattern detector | Dev | ☐ |
| P2-025 | Implement prose density calculator | Dev | ☐ |
| P2-026 | Create needs assessment prompt | Dev | ☐ |
| P2-027 | Implement iterative refinement | Dev | ☐ |
| P2-028 | Write unit tests | Dev | ☐ |

**Cold Open Implementation:**

```python
# src/agents/needs_assessment.py (partial)

class NeedsAssessmentAgent(BaseAgent):
    """Agent 5: 3,100+ word narrative with cold open."""
    
    async def generate_cold_open(
        self, 
        gaps: List[Gap],
        disease_state: str,
        target_population: str
    ) -> Dict[str, Any]:
        """Generate cold open following framework."""
        
        cold_open_prompt = f"""
        Generate a cold open (50-100 words) for a needs assessment about {disease_state}.
        
        Requirements:
        - Named character with age
        - One humanizing detail (hobby, family, occupation)
        - Present tense throughout
        - "The turn" connecting individual to population in final sentence
        - No header or title
        
        The gaps to be addressed:
        {chr(10).join(f'- {g["gap_statement"]}' for g in gaps)}
        
        Example structure:
        "[Name], [age], [humanizing detail]. [Present situation with disease].
        [Specific struggle related to gaps]. [The turn: She is one of X million Americans...]"
        
        Write the cold open now:
        """
        
        response = await self.llm.ainvoke(cold_open_prompt)
        
        cold_open = response.content.strip()
        
        # Validate
        words = cold_open.split()
        if not (50 <= len(words) <= 100):
            # Retry with feedback
            pass
        
        # Extract character name for thread tracking
        character_name = self._extract_character_name(cold_open)
        
        return {
            "text": cold_open,
            "word_count": len(words),
            "character_name": character_name,
        }
```

### Agent 6: Learning Objectives Agent

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P2-029 | Implement Moore's Framework validator | Dev | ☐ |
| P2-030 | Create action verb library | Dev | ☐ |
| P2-031 | Implement gap-objective alignment | Dev | ☐ |
| P2-032 | Create measurement plan generator | Dev | ☐ |
| P2-033 | Write unit tests | Dev | ☐ |

### Agents 7-9: Parallel Generation Agents

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P2-034 | Implement curriculum design agent | Dev | ☐ |
| P2-035 | Implement research protocol agent | Dev | ☐ |
| P2-036 | Implement marketing plan agent | Dev | ☐ |
| P2-037 | Create innovation section generator | Dev | ☐ |
| P2-038 | Create budget calculator | Dev | ☐ |
| P2-039 | Write unit tests for all three | Dev | ☐ |

### Agent 10: Grant Writer Agent

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P2-040 | Implement section assembler | Dev | ☐ |
| P2-041 | Create cross-reference validator | Dev | ☐ |
| P2-042 | Implement character thread maintainer | Dev | ☐ |
| P2-043 | Create budget table generator | Dev | ☐ |
| P2-044 | Implement appendix compiler | Dev | ☐ |
| P2-045 | Write unit tests | Dev | ☐ |

## 6.3 Deliverables

1. **10 Functional Agents** (2-10 + node wrappers)
2. **Tool Integrations** (PubMed, guidelines, etc.)
3. **Prompt Library** (all agent prompts)
4. **Unit Test Suite** (>80% coverage per agent)

## 6.4 Acceptance Criteria

- [ ] Each agent produces valid output schema
- [ ] Research agent returns 30+ citations
- [ ] Needs assessment generates 3,100+ words
- [ ] Learning objectives align to Moore's Framework
- [ ] Grant writer assembles complete package

---

# 7. Phase 3: Quality & Compliance

**Duration:** 2 weeks  
**Goal:** Implement quality gates and compliance verification

## 7.1 Week 7: Prose Quality Agent

### Agent 11: Prose Quality Agent

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P3-001 | Implement banned pattern detector | Dev | ☐ |
| P3-002 | Create prose density calculator | Dev | ☐ |
| P3-003 | Implement word count validator | Dev | ☐ |
| P3-004 | Create cold open validator | Dev | ☐ |
| P3-005 | Implement character thread tracker | Dev | ☐ |
| P3-006 | Create revision instruction generator | Dev | ☐ |
| P3-007 | Implement two-pass logic | Dev | ☐ |
| P3-008 | Write unit tests | Dev | ☐ |

**Banned Pattern Detection:**

```python
# src/agents/prose_quality.py (partial)

import re
from typing import List, Dict

BANNED_PATTERNS = {
    "em_dash": {
        "pattern": r"—",
        "description": "Em dash usage",
        "severity": "critical",
    },
    "delve": {
        "pattern": r"\bdelv(e|ing|ed|es)\b",
        "description": "'Delve' and variations",
        "severity": "critical",
    },
    "important_to_note": {
        "pattern": r"it['']?s important to note",
        "description": "'It's important to note' phrase",
        "severity": "critical",
    },
    "furthermore_starter": {
        "pattern": r"^Furthermore,",
        "description": "Paragraph starting with 'Furthermore,'",
        "severity": "major",
        "flags": re.MULTILINE,
    },
    "moreover_starter": {
        "pattern": r"^Moreover,",
        "description": "Paragraph starting with 'Moreover,'",
        "severity": "major",
        "flags": re.MULTILINE,
    },
    "additionally_starter": {
        "pattern": r"^Additionally,",
        "description": "Paragraph starting with 'Additionally,'",
        "severity": "major",
        "flags": re.MULTILINE,
    },
    "today_landscape": {
        "pattern": r"in today['']?s .{0,20} landscape",
        "description": "'In today's X landscape' phrase",
        "severity": "critical",
    },
    "colon_title": {
        "pattern": r"^#{1,6}\s+[^:\n]+:\s*[A-Z]",
        "description": "Colon in section title",
        "severity": "major",
        "flags": re.MULTILINE,
    },
    "robust_generic": {
        "pattern": r"\brobust\b(?!\s+(security|encryption|algorithm|validation))",
        "description": "'Robust' as generic intensifier",
        "severity": "major",
    },
    "leverage_verb": {
        "pattern": r"\bleverag(e|ing|ed)\b",
        "description": "'Leverage' used as verb",
        "severity": "major",
    },
    "holistic": {
        "pattern": r"\bholistic(ally)?\b",
        "description": "'Holistic' usage",
        "severity": "critical",
    },
    "paradigm": {
        "pattern": r"\bparadigm\b",
        "description": "'Paradigm' usage",
        "severity": "major",
    },
    "cutting_edge": {
        "pattern": r"\bcutting[- ]edge\b",
        "description": "'Cutting-edge' usage",
        "severity": "major",
    },
    "state_of_art": {
        "pattern": r"\bstate[- ]of[- ]the[- ]art\b",
        "description": "'State-of-the-art' usage",
        "severity": "major",
    },
    "myriad": {
        "pattern": r"\bmyriad\b",
        "description": "'Myriad' usage",
        "severity": "major",
    },
    "plethora": {
        "pattern": r"\bplethora\b",
        "description": "'Plethora' usage",
        "severity": "major",
    },
    "multifaceted": {
        "pattern": r"\bmultifaceted\b",
        "description": "'Multifaceted' usage",
        "severity": "major",
    },
    "navigate_metaphor": {
        "pattern": r"\bnavigate\b(?!\s+(the|a|to)\s+(website|page|menu|interface|screen))",
        "description": "'Navigate' used metaphorically",
        "severity": "major",
    },
    "landscape_metaphor": {
        "pattern": r"\b(treatment|healthcare|clinical|therapeutic|medical)\s+landscape\b",
        "description": "'X landscape' metaphor",
        "severity": "critical",
    },
    "studies_show_vague": {
        "pattern": r"\bstudies\s+(show|indicate|suggest|demonstrate)\b(?!\s*\()",
        "description": "Vague 'studies show' without citation",
        "severity": "major",
    },
    "research_indicates_vague": {
        "pattern": r"\bresearch\s+(shows|indicates|suggests)\b(?!\s*\()",
        "description": "Vague 'research indicates' without citation",
        "severity": "major",
    },
}


class ProseQualityAgent:
    """Agent 11: Writing quality enforcement."""
    
    def detect_banned_patterns(self, text: str) -> List[Dict]:
        """Detect all banned patterns in text."""
        violations = []
        
        for pattern_name, config in BANNED_PATTERNS.items():
            flags = config.get("flags", 0)
            matches = re.finditer(config["pattern"], text, flags | re.IGNORECASE)
            
            for match in matches:
                # Get context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                violations.append({
                    "pattern_name": pattern_name,
                    "description": config["description"],
                    "severity": config["severity"],
                    "instance": match.group(),
                    "position": match.start(),
                    "context": f"...{context}...",
                    "line_number": text[:match.start()].count('\n') + 1,
                })
        
        return violations
    
    def calculate_prose_density(self, text: str) -> Dict:
        """Calculate percentage of flowing prose vs lists/bullets."""
        lines = text.split('\n')
        prose_chars = 0
        list_chars = 0
        total_chars = 0
        
        list_patterns = [
            r'^\s*[-*•–]\s',           # Bullet points
            r'^\s*\d+[\.\)]\s',        # Numbered lists
            r'^\s*\|',                  # Table rows
            r'^\s*[a-z][\.\)]\s',      # Lettered lists
        ]
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            
            char_count = len(stripped)
            total_chars += char_count
            
            is_list = any(re.match(p, stripped) for p in list_patterns)
            
            if is_list:
                list_chars += char_count
            else:
                prose_chars += char_count
        
        density = (prose_chars / total_chars * 100) if total_chars > 0 else 0
        
        return {
            "prose_chars": prose_chars,
            "list_chars": list_chars,
            "total_chars": total_chars,
            "density_percentage": round(density, 2),
            "passed": density >= 80,
        }
```

## 7.2 Week 8: Compliance Agent & Quality Gates

### Agent 12: Compliance Review Agent

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P3-009 | Implement ACCME standard checkers | Dev | ☐ |
| P3-010 | Create commercial bias detector | Dev | ☐ |
| P3-011 | Implement fair balance analyzer | Dev | ☐ |
| P3-012 | Create disclosure verifier | Dev | ☐ |
| P3-013 | Implement off-label compliance check | Dev | ☐ |
| P3-014 | Create remediation router | Dev | ☐ |
| P3-015 | Write unit tests | Dev | ☐ |

### Quality Gate Implementation

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P3-016 | Implement Gate 1 (post-needs assessment) | Dev | ☐ |
| P3-017 | Implement Gate 2 (post-grant assembly) | Dev | ☐ |
| P3-018 | Implement Gate 3 (compliance) | Dev | ☐ |
| P3-019 | Implement Gate 4 (human review) | Dev | ☐ |
| P3-020 | Create retry logic with backoff | Dev | ☐ |
| P3-021 | Implement human escalation | Dev | ☐ |

**Quality Gate Implementation:**

```python
# src/graph/routing.py

from typing import Literal
from src.state.schema import CMEGrantState, ProjectStatus

def route_after_prose_quality(
    state: CMEGrantState
) -> Literal["learning_objectives", "needs_assessment", 
             "compliance", "grant_writer", "human_escalation"]:
    """
    Route based on prose quality results.
    
    Pass 1 (after needs assessment):
        - Pass → learning_objectives
        - Fail → needs_assessment (retry)
        
    Pass 2 (after grant assembly):
        - Pass → compliance
        - Fail → grant_writer (retry)
    """
    if not state["prose_quality_scores"]:
        raise ValueError("No prose quality scores in state")
    
    latest_score = state["prose_quality_scores"][-1]
    current_status = state["status"]
    retry_count = state["retry_count"]
    
    # Check if passed
    if latest_score["passed"]:
        if current_status == ProjectStatus.PROSE_REVIEW_1:
            return "learning_objectives"
        elif current_status == ProjectStatus.PROSE_REVIEW_2:
            return "compliance"
    
    # Failed - check retry limit
    if retry_count >= 3:
        return "human_escalation"
    
    # Route back for revision
    if current_status == ProjectStatus.PROSE_REVIEW_1:
        return "needs_assessment"
    else:
        return "grant_writer"


def route_after_compliance(
    state: CMEGrantState
) -> Literal["human_review", "grant_writer", "learning_objectives", 
             "gap_analysis", "human_escalation"]:
    """
    Route based on compliance review results.
    """
    compliance = state["compliance_score"]
    
    if compliance["compliant"]:
        return "human_review"
    
    if state["retry_count"] >= 2:
        return "human_escalation"
    
    # Route to agent that can fix the issue
    remediation = compliance.get("remediation_required", {})
    issues = remediation.get("issues", [])
    
    if not issues:
        return "grant_writer"
    
    # Find highest severity issue
    critical = [i for i in issues if i["severity"] == "critical"]
    primary_issue = critical[0] if critical else issues[0]
    
    routing_map = {
        "commercial_bias": "grant_writer",
        "fair_balance": "grant_writer",
        "missing_disclosure": "grant_writer",
        "objective_format": "learning_objectives",
        "gap_evidence": "gap_analysis",
    }
    
    return routing_map.get(primary_issue["category"], "grant_writer")
```

## 7.3 Deliverables

1. **Prose Quality Agent** with full pattern detection
2. **Compliance Agent** with ACCME verification
3. **Quality Gate Logic** with routing
4. **Human Escalation Workflow**

## 7.4 Acceptance Criteria

- [ ] All banned patterns detected (zero false negatives)
- [ ] Prose density calculation accurate to ±1%
- [ ] ACCME standards verified completely
- [ ] Commercial bias detection functional
- [ ] Retry logic executes correctly
- [ ] Human escalation triggers appropriately

---

# 8. Phase 4: Integration & UI

**Duration:** 2 weeks  
**Goal:** Complete system integration and user interface

## 8.1 Week 9: Graph Integration

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P4-001 | Wire all agents into StateGraph | Dev | ☐ |
| P4-002 | Implement parallel execution groups | Dev | ☐ |
| P4-003 | Configure checkpoint persistence | Dev | ☐ |
| P4-004 | Implement state recovery | Dev | ☐ |
| P4-005 | Create pipeline execution API | Dev | ☐ |
| P4-006 | Implement progress streaming | Dev | ☐ |
| P4-007 | Add comprehensive error handling | Dev | ☐ |

**Complete Graph Definition:**

```python
# src/graph/definition.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from src.state.schema import CMEGrantState
from src.graph.nodes import (
    research_node, clinical_node, gap_analysis_node,
    needs_assessment_node, prose_quality_node,
    learning_objectives_node, curriculum_node,
    protocol_node, marketing_node, grant_writer_node,
    compliance_node, human_review_node,
)
from src.graph.routing import (
    route_after_prose_quality,
    route_after_compliance,
    route_after_human_review,
)


def create_cme_graph() -> StateGraph:
    """Create the complete CME grant generation graph."""
    
    graph = StateGraph(CMEGrantState)
    
    # Add all nodes
    graph.add_node("research", research_node)
    graph.add_node("clinical", clinical_node)
    graph.add_node("gap_analysis", gap_analysis_node)
    graph.add_node("needs_assessment", needs_assessment_node)
    graph.add_node("prose_quality", prose_quality_node)
    graph.add_node("learning_objectives", learning_objectives_node)
    graph.add_node("curriculum", curriculum_node)
    graph.add_node("protocol", protocol_node)
    graph.add_node("marketing", marketing_node)
    graph.add_node("grant_writer", grant_writer_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("human_review", human_review_node)
    
    # Entry: fan out to parallel group 1
    graph.set_entry_point("research")
    graph.add_edge("research", "gap_analysis")
    graph.add_edge("clinical", "gap_analysis")
    
    # Sequential flow
    graph.add_edge("gap_analysis", "needs_assessment")
    graph.add_edge("needs_assessment", "prose_quality")
    
    # Conditional: prose quality pass 1
    graph.add_conditional_edges(
        "prose_quality",
        route_after_prose_quality,
        {
            "learning_objectives": "learning_objectives",
            "needs_assessment": "needs_assessment",
            "compliance": "compliance",
            "grant_writer": "grant_writer",
            "human_escalation": END,
        }
    )
    
    # Fan out to parallel group 2
    graph.add_edge("learning_objectives", "curriculum")
    graph.add_edge("learning_objectives", "protocol")
    graph.add_edge("learning_objectives", "marketing")
    
    # Fan in
    graph.add_edge("curriculum", "grant_writer")
    graph.add_edge("protocol", "grant_writer")
    graph.add_edge("marketing", "grant_writer")
    
    # Grant writer to prose quality pass 2
    graph.add_edge("grant_writer", "prose_quality")
    
    # Conditional: compliance
    graph.add_conditional_edges(
        "compliance",
        route_after_compliance,
        {
            "human_review": "human_review",
            "grant_writer": "grant_writer",
            "learning_objectives": "learning_objectives",
            "gap_analysis": "gap_analysis",
            "human_escalation": END,
        }
    )
    
    # Conditional: human review
    graph.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "complete": END,
            "rejected": END,
            "revision_routing": "grant_writer",
        }
    )
    
    return graph


def compile_graph(connection_string: str) -> Any:
    """Compile graph with PostgreSQL checkpointing."""
    graph = create_cme_graph()
    checkpointer = PostgresSaver.from_conn_string(connection_string)
    return graph.compile(checkpointer=checkpointer)
```

## 8.2 Week 10: User Interface

### LibreChat Integration

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P4-008 | Configure LibreChat instance | Dev | ☐ |
| P4-009 | Create intake form endpoint | Dev | ☐ |
| P4-010 | Implement custom UI components | Dev | ☐ |
| P4-011 | Create project dashboard | Dev | ☐ |
| P4-012 | Implement human review interface | Dev | ☐ |
| P4-013 | Add progress visualization | Dev | ☐ |
| P4-014 | Create document preview/download | Dev | ☐ |

### Admin Dashboard

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P4-015 | Create pipeline monitoring view | Dev | ☐ |
| P4-016 | Implement agent metrics display | Dev | ☐ |
| P4-017 | Add error investigation tools | Dev | ☐ |
| P4-018 | Create user management | Dev | ☐ |
| P4-019 | Implement audit logging view | Dev | ☐ |

## 8.3 API Endpoints

```python
# src/api/routes/intake.py

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
import uuid

from src.state.schema import IntakeData, create_initial_state
from src.graph.definition import compile_graph
from src.config import settings

router = APIRouter(prefix="/api/v2", tags=["intake"])


class IntakeSubmission(BaseModel):
    """Intake form submission."""
    section_a: Dict[str, Any]
    section_b: Dict[str, Any]
    section_c: Dict[str, Any]
    section_d: Dict[str, Any]
    section_e: Dict[str, Any]
    section_f: Dict[str, Any]
    section_g: Dict[str, Any]
    section_h: Dict[str, Any]
    section_i: Dict[str, Any]
    section_j: Dict[str, Any]


class IntakeResponse(BaseModel):
    """Response after intake submission."""
    project_id: str
    status: str
    message: str


@router.post("/intake", response_model=IntakeResponse)
async def submit_intake(
    submission: IntakeSubmission,
    background_tasks: BackgroundTasks,
):
    """Submit intake form and start pipeline."""
    
    # Generate project ID
    project_id = str(uuid.uuid4())
    project_name = submission.section_a.get("project_name", "Untitled")
    
    # Validate intake data
    try:
        intake_data = IntakeData(**submission.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Create initial state
    initial_state = create_initial_state(
        project_id=project_id,
        project_name=project_name,
        intake_data=intake_data,
    )
    
    # Start pipeline in background
    background_tasks.add_task(
        run_pipeline_async,
        project_id=project_id,
        initial_state=initial_state,
    )
    
    return IntakeResponse(
        project_id=project_id,
        status="processing",
        message="Pipeline initiated successfully",
    )


async def run_pipeline_async(project_id: str, initial_state: Dict):
    """Run pipeline asynchronously."""
    graph = compile_graph(settings.database_url)
    
    config = {
        "configurable": {"thread_id": project_id},
        "recursion_limit": 50,
    }
    
    try:
        await graph.ainvoke(initial_state, config=config)
    except Exception as e:
        # Log error and update state
        pass
```

## 8.4 Deliverables

1. **Complete LangGraph Pipeline** - All agents wired and executing
2. **REST API** - Full CRUD for projects
3. **LibreChat UI** - Intake forms, monitoring
4. **Admin Dashboard** - Operations view
5. **WebSocket Progress** - Real-time updates

## 8.5 Acceptance Criteria

- [ ] Full pipeline executes from intake to output
- [ ] Checkpoints persist and recovery works
- [ ] Parallel execution functions correctly
- [ ] UI allows intake submission
- [ ] Progress updates stream to client
- [ ] Human review interface functional

---

# 9. Phase 5: Testing & Validation

**Duration:** 2 weeks  
**Goal:** Comprehensive testing and quality assurance

## 9.1 Week 11: Test Suite Development

### Unit Tests

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P5-001 | State schema validation tests | QA | ☐ |
| P5-002 | Individual agent unit tests | QA | ☐ |
| P5-003 | Tool function tests | QA | ☐ |
| P5-004 | Routing logic tests | QA | ☐ |
| P5-005 | Quality gate tests | QA | ☐ |
| P5-006 | Pattern detection tests | QA | ☐ |

### Integration Tests

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P5-007 | Agent chain tests | QA | ☐ |
| P5-008 | Parallel execution tests | QA | ☐ |
| P5-009 | Checkpoint/recovery tests | QA | ☐ |
| P5-010 | API endpoint tests | QA | ☐ |
| P5-011 | Database integration tests | QA | ☐ |

### End-to-End Tests

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P5-012 | Full pipeline happy path | QA | ☐ |
| P5-013 | Retry scenario tests | QA | ☐ |
| P5-014 | Human review workflow | QA | ☐ |
| P5-015 | Error recovery tests | QA | ☐ |

**Test Configuration:**

```python
# tests/conftest.py

import pytest
import asyncio
from typing import Generator, Dict, Any
from unittest.mock import MagicMock, AsyncMock

from src.state.schema import CMEGrantState, create_initial_state
from src.config import settings


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_intake_data() -> Dict[str, Any]:
    """Sample intake data for testing."""
    return {
        "section_a": {
            "project_name": "Test SGLT2 CME Project",
            "therapeutic_area": "Cardiology",
            "disease_state": "Heart Failure with Reduced Ejection Fraction",
            "target_audience_primary": ["Cardiologists", "Internal Medicine"],
            "target_audience_secondary": ["Pharmacists"],
        },
        "section_b": {
            "identified_gaps": [
                "Underutilization of SGLT2 inhibitors",
                "Knowledge gaps in patient selection",
            ],
            "gap_evidence_sources": ["Published literature", "Registry data"],
            "desired_outcomes": [
                "Identify appropriate candidates",
                "Initiate therapy appropriately",
            ],
            "moore_level_target": "5",
            "practice_change_goals": ["Increase SGLT2i prescribing by 25%"],
            "patient_impact_goals": ["Reduce HF hospitalizations"],
        },
        # ... remaining sections
    }


@pytest.fixture
def sample_state(sample_intake_data: Dict) -> CMEGrantState:
    """Create sample state for testing."""
    return create_initial_state(
        project_id="test-project-001",
        project_name="Test Project",
        intake_data=sample_intake_data,
    )


@pytest.fixture
def mock_llm() -> MagicMock:
    """Mock LLM for unit tests."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value=MagicMock(content="Mock response"))
    return mock


@pytest.fixture
def mock_pubmed_tool() -> MagicMock:
    """Mock PubMed tool."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value={
        "results": [
            {
                "pmid": "12345678",
                "title": "Test Article",
                "abstract": "Test abstract content",
                "authors": "Smith J, Doe A",
                "journal": "Test Journal",
                "year": 2024,
            }
        ]
    })
    return mock
```

## 9.2 Week 12: Validation & Performance

### Quality Validation

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P5-016 | Validate against 5 real grants | QA | ☐ |
| P5-017 | Expert review of generated content | SME | ☐ |
| P5-018 | ACCME compliance verification | Compliance | ☐ |
| P5-019 | Prose quality audit | Editor | ☐ |

### Performance Testing

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P5-020 | Measure end-to-end latency | QA | ☐ |
| P5-021 | Token usage analysis | QA | ☐ |
| P5-022 | Concurrent execution test | QA | ☐ |
| P5-023 | Memory usage profiling | QA | ☐ |

### Test Scenarios

**Scenario 1: Cardiology HF Grant**
```yaml
name: SGLT2 Inhibitors in Heart Failure
therapeutic_area: Cardiology
disease_state: Heart Failure with Reduced Ejection Fraction
expected_output:
  needs_assessment_words: ">3100"
  citations: ">30"
  learning_objectives: "6"
  moore_distribution:
    level_5: "40-60%"
    level_4: "30-40%"
```

**Scenario 2: Oncology Immunotherapy**
```yaml
name: Checkpoint Inhibitors in NSCLC
therapeutic_area: Oncology
disease_state: Non-Small Cell Lung Cancer
expected_output:
  needs_assessment_words: ">3100"
  citations: ">35"
  learning_objectives: "5-7"
```

**Scenario 3: Neurology Multiple Sclerosis**
```yaml
name: Disease-Modifying Therapies in MS
therapeutic_area: Neurology
disease_state: Relapsing Multiple Sclerosis
expected_output:
  needs_assessment_words: ">3100"
  citations: ">30"
```

## 9.3 Deliverables

1. **Test Suite** - >85% code coverage
2. **Test Reports** - Automated CI/CD reports
3. **Validation Results** - Expert review documentation
4. **Performance Baseline** - Metrics and benchmarks

## 9.4 Acceptance Criteria

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests complete successfully
- [ ] 5 validation grants meet quality standards
- [ ] Performance within acceptable limits
- [ ] No critical bugs open

---

# 10. Phase 6: Deployment

**Duration:** 2 weeks  
**Goal:** Production deployment and go-live

## 10.1 Week 13: Staging Deployment

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P6-001 | Deploy to staging environment | DevOps | ☐ |
| P6-002 | Configure production secrets | DevOps | ☐ |
| P6-003 | Set up monitoring dashboards | DevOps | ☐ |
| P6-004 | Configure alerting | DevOps | ☐ |
| P6-005 | Load testing | QA | ☐ |
| P6-006 | Security audit | Security | ☐ |
| P6-007 | UAT with stakeholders | Product | ☐ |

## 10.2 Week 14: Production Go-Live

| Task ID | Task | Owner | Status |
|---------|------|-------|--------|
| P6-008 | Production infrastructure setup | DevOps | ☐ |
| P6-009 | Database migration | DevOps | ☐ |
| P6-010 | DNS configuration | DevOps | ☐ |
| P6-011 | SSL certificate setup | DevOps | ☐ |
| P6-012 | Production deployment | DevOps | ☐ |
| P6-013 | Smoke testing | QA | ☐ |
| P6-014 | Go-live approval | Product | ☐ |
| P6-015 | User training | Training | ☐ |

### Deployment Architecture

```yaml
# kubernetes/deployment.yaml (example structure)

apiVersion: apps/v1
kind: Deployment
metadata:
  name: dhg-cme-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: dhg-cme-api
  template:
    metadata:
      labels:
        app: dhg-cme-api
    spec:
      containers:
      - name: api
        image: ghcr.io/dhg/cme-agents:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: dhg-cme-secrets
              key: database-url
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: dhg-cme-secrets
              key: anthropic-api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dhg-cme-worker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dhg-cme-worker
  template:
    spec:
      containers:
      - name: worker
        image: ghcr.io/dhg/cme-agents-worker:latest
        resources:
          requests:
            memory: "4Gi"
            cpu: "2000m"
          limits:
            memory: "8Gi"
            cpu: "4000m"
```

### Rollback Plan

```
ROLLBACK PROCEDURE
==================

1. DETECTION
   - Automated: Error rate >5% for 5 minutes
   - Manual: Critical bug reported

2. DECISION
   - On-call engineer assesses severity
   - If P0/P1: Immediate rollback
   - If P2+: Schedule fix or rollback

3. EXECUTION
   kubectl rollout undo deployment/dhg-cme-api
   kubectl rollout undo deployment/dhg-cme-worker

4. VERIFICATION
   - Check all pods healthy
   - Run smoke tests
   - Verify no errors in logs

5. COMMUNICATION
   - Notify stakeholders
   - Update incident channel
   - Schedule post-mortem
```

## 10.3 Deliverables

1. **Production System** - Fully deployed and operational
2. **Monitoring** - Dashboards and alerts configured
3. **Documentation** - Runbooks and procedures
4. **Training** - Users trained on system

## 10.4 Acceptance Criteria

- [ ] Production system accessible
- [ ] All health checks passing
- [ ] Monitoring operational
- [ ] First production grant completed
- [ ] No critical issues in first 48 hours

---

# 11. Operations & Maintenance

## 11.1 Monitoring Strategy

### Key Metrics

| Category | Metric | Alert Threshold |
|----------|--------|-----------------|
| Availability | API uptime | <99.5% |
| Latency | P95 response time | >5s |
| Throughput | Grants completed/day | <target |
| Quality | First-pass approval rate | <80% |
| Errors | Error rate | >2% |
| Cost | Token usage per grant | >150% baseline |

### Dashboards

```
GRAFANA DASHBOARD STRUCTURE
===========================

Dashboard: DHG CME System Overview
├── Row: System Health
│   ├── API availability
│   ├── Worker status
│   └── Database connections
├── Row: Pipeline Metrics
│   ├── Grants in progress
│   ├── Completion rate
│   └── Average duration
├── Row: Agent Performance
│   ├── Agent execution times
│   ├── Agent error rates
│   └── Retry counts
├── Row: Quality Metrics
│   ├── Prose quality scores
│   ├── Compliance pass rate
│   └── Human review outcomes
└── Row: Costs
    ├── Token usage
    ├── API costs
    └── Infrastructure costs
```

## 11.2 Maintenance Procedures

### Daily Tasks
- [ ] Review overnight alerts
- [ ] Check pipeline completion status
- [ ] Monitor error logs
- [ ] Verify backup completion

### Weekly Tasks
- [ ] Review quality metrics
- [ ] Analyze failed grants
- [ ] Update prompts if needed
- [ ] Team sync on issues

### Monthly Tasks
- [ ] Performance review
- [ ] Cost analysis
- [ ] Security audit
- [ ] Capacity planning

## 11.3 Incident Response

```
INCIDENT SEVERITY LEVELS
========================

P0 - Critical
- System completely down
- Data loss/corruption
- Security breach
Response: Immediate, all hands

P1 - High
- Major feature broken
- Significant performance degradation
- Pipeline failures affecting SLAs
Response: Within 1 hour

P2 - Medium
- Minor feature broken
- Intermittent issues
- Non-critical errors
Response: Within 4 hours

P3 - Low
- UI glitches
- Documentation issues
- Enhancement requests
Response: Next sprint
```

---

# 12. Risk Mitigation

## 12.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM API outage | Medium | High | Implement fallback to OpenAI |
| Poor output quality | Medium | High | Iterative prompt refinement, human review |
| Token cost overrun | Medium | Medium | Implement token budgets, caching |
| Database failure | Low | High | Multi-AZ deployment, regular backups |
| Security breach | Low | Critical | Regular audits, encryption, access controls |

## 12.2 Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Low adoption | Medium | High | User training, change management |
| Quality rejection | Medium | High | Expert review process, continuous improvement |
| Regulatory changes | Low | Medium | Monitor ACCME updates, flexible architecture |
| Staff turnover | Medium | Medium | Documentation, cross-training |

## 12.3 Contingency Plans

### LLM Provider Failure
1. Automatic failover to backup provider (OpenAI)
2. Alert on-call engineer
3. Monitor quality with backup
4. Revert when primary restored

### Quality Gate Failure Loop
1. After 3 retries, escalate to human
2. Human reviews and provides guidance
3. System incorporates feedback
4. Track patterns for prompt improvement

---

# 13. Budget & Timeline

## 13.1 Timeline Summary

```
GANTT CHART
===========

Phase 1: Foundation        ████████░░░░░░░░░░░░░░░░░░░░░░ Week 1-2
Phase 2: Core Agents       ░░░░░░░░████████████████░░░░░░ Week 3-6
Phase 3: Quality           ░░░░░░░░░░░░░░░░░░░░████████░░ Week 7-8
Phase 4: Integration       ░░░░░░░░░░░░░░░░░░░░░░░░████░░ Week 9-10
Phase 5: Testing           ░░░░░░░░░░░░░░░░░░░░░░░░░░████ Week 11-12
Phase 6: Deployment        ░░░░░░░░░░░░░░░░░░░░░░░░░░░░██ Week 13-14

Total Duration: 14 weeks (3.5 months)
```

## 13.2 Resource Allocation

| Role | Hours/Week | Weeks | Total Hours |
|------|------------|-------|-------------|
| Lead Developer | 40 | 14 | 560 |
| Backend Developer | 40 | 12 | 480 |
| DevOps Engineer | 20 | 14 | 280 |
| QA Engineer | 30 | 8 | 240 |
| UI Developer | 30 | 4 | 120 |
| Technical Writer | 10 | 6 | 60 |
| Project Manager | 15 | 14 | 210 |
| **Total** | | | **1,950 hours** |

## 13.3 Budget Estimate

### Development Costs
| Item | Cost |
|------|------|
| Development labor (1,950 hrs × $150/hr avg) | $292,500 |
| Infrastructure (14 weeks) | $5,000 |
| LLM API costs (development) | $3,000 |
| Tools & licenses | $2,000 |
| **Subtotal** | **$302,500** |

### Ongoing Monthly Costs
| Item | Monthly Cost |
|------|--------------|
| Infrastructure (production) | $2,500 |
| LLM API (est. 20 grants/month) | $300 |
| LangSmith | $400 |
| Maintenance (20 hrs × $150) | $3,000 |
| **Monthly Total** | **$6,200** |

## 13.4 ROI Analysis

| Metric | Manual Process | Automated | Savings |
|--------|----------------|-----------|---------|
| Hours per grant | 80 | 8 | 72 hrs |
| Cost per grant | $12,000 | $1,500 | $10,500 |
| Grants per month | 3 | 20 | +17 |
| Monthly capacity | $36,000 | $300,000 | +733% |

**Payback Period:** ~3 months after go-live

---

# 14. Appendices

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| ACCME | Accreditation Council for Continuing Medical Education |
| CME | Continuing Medical Education |
| GDMT | Guideline-Directed Medical Therapy |
| HFrEF | Heart Failure with Reduced Ejection Fraction |
| KOL | Key Opinion Leader |
| LangGraph | Framework for building stateful LLM applications |
| Moore's Framework | Educational outcomes framework (Levels 1-7) |
| MOC | Maintenance of Certification |
| StateGraph | LangGraph's graph structure for state machines |

## Appendix B: Reference Documents

1. [Agent Documentation](/agents/) - All 12 agent specifications
2. [State Schema](/technical/state-schema.py) - TypedDict definitions
3. [Graph Definition](/technical/graph-definition.py) - LangGraph structure
4. [Intake Form Schema](/technical/intake-form-schema.yaml) - 47-field specification
5. [Writing Style Guide](/shared-resources/writing-style-guide.md) - Prose standards
6. [Cold Open Framework](/shared-resources/cold-open-framework.md) - Narrative technique
7. [Moore's Framework](/shared-resources/moores-expanded-framework.md) - Outcomes levels

## Appendix C: Contact Information

| Role | Name | Contact |
|------|------|---------|
| Project Owner | Stephen Webber | stephen@digitalharmonygroup.com |
| Technical Lead | TBD | |
| DevOps Lead | TBD | |

---

*Document Version: 1.0*  
*Last Updated: January 31, 2026*  
*Classification: DHG Internal*
