# DHG CME 12-Agent System
## Technical Architecture Document

**Version:** 1.0  
**Date:** January 31, 2026  
**Classification:** Technical Reference  
**Audience:** Engineers, Architects, DevOps

---

# Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [System Components](#2-system-components)
3. [Agent Architecture](#3-agent-architecture)
4. [Orchestration Layer](#4-orchestration-layer)
5. [Data Architecture](#5-data-architecture)
6. [API Architecture](#6-api-architecture)
7. [Integration Patterns](#7-integration-patterns)
8. [Security Architecture](#8-security-architecture)
9. [Observability Architecture](#9-observability-architecture)
10. [Deployment Architecture](#10-deployment-architecture)
11. [Scalability & Performance](#11-scalability--performance)
12. [Disaster Recovery](#12-disaster-recovery)
13. [Architecture Decision Records](#13-architecture-decision-records)

---

# 1. Architecture Overview

## 1.1 System Context

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL CONTEXT                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Users      │    │  Anthropic   │    │   PubMed     │    │  LangSmith   │  │
│  │  (LibreChat) │    │   Claude API │    │     API      │    │  (Traces)    │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │                   │           │
│         │                   │                   │                   │           │
│  ┌──────▼───────────────────▼───────────────────▼───────────────────▼───────┐  │
│  │                                                                           │  │
│  │                    DHG CME 12-AGENT SYSTEM                                │  │
│  │                                                                           │  │
│  │   ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │   │                     Application Layer                            │    │  │
│  │   │  • FastAPI REST Services                                        │    │  │
│  │   │  • LangGraph Orchestration                                      │    │  │
│  │   │  • 12 Specialized Agents                                        │    │  │
│  │   └─────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                           │  │
│  │   ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │   │                       Data Layer                                 │    │  │
│  │   │  • PostgreSQL (State, Checkpoints)                              │    │  │
│  │   │  • pgvector (Embeddings)                                        │    │  │
│  │   │  • Redis (Cache, Queues)                                        │    │  │
│  │   │  • MinIO (Documents)                                            │    │  │
│  │   └─────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 1.2 Architecture Principles

| Principle | Description | Implementation |
|-----------|-------------|----------------|
| **Modularity** | Agents are independent, replaceable units | Each agent in separate module with defined interface |
| **Stateless Services** | Application tier holds no state | All state in PostgreSQL, Redis for ephemeral |
| **Event-Driven** | Async processing where possible | Redis Streams for task queuing |
| **Observability-First** | Every operation is traceable | LangSmith traces, Prometheus metrics, structured logs |
| **Fail-Safe** | Graceful degradation on failures | Checkpointing, retries, human escalation |
| **Security by Design** | Defense in depth | Encryption, RBAC, audit logging |

## 1.3 High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 PRESENTATION                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐              │
│   │   LibreChat     │   │  Admin Portal   │   │  API Clients    │              │
│   │   (User UI)     │   │  (Operations)   │   │  (Integrations) │              │
│   └────────┬────────┘   └────────┬────────┘   └────────┬────────┘              │
│            │                     │                     │                        │
└────────────┼─────────────────────┼─────────────────────┼────────────────────────┘
             │                     │                     │
             ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 API GATEWAY                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                          FastAPI Application                             │   │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐   │   │
│   │  │    Auth      │  │   Routes     │  │  Middleware  │  │   CORS     │   │   │
│   │  │  (OAuth/JWT) │  │  (REST API)  │  │  (Logging)   │  │            │   │   │
│   │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘   │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ORCHESTRATION                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                      LangGraph StateGraph Engine                         │   │
│   │                                                                          │   │
│   │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        │   │
│   │  │   State    │  │  Routing   │  │  Quality   │  │ Checkpoint │        │   │
│   │  │ Management │  │   Logic    │  │   Gates    │  │  Manager   │        │   │
│   │  └────────────┘  └────────────┘  └────────────┘  └────────────┘        │   │
│   │                                                                          │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                AGENT LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ Agent 2 │ │ Agent 3 │ │ Agent 4 │ │ Agent 5 │ │ Agent 6 │ │ Agent 7 │       │
│  │Research │ │Clinical │ │  Gap    │ │ Needs   │ │Learning │ │Curricul.│       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
│                                                                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                   │
│  │ Agent 8 │ │ Agent 9 │ │Agent 10 │ │Agent 11 │ │Agent 12 │                   │
│  │Protocol │ │Marketing│ │ Grant   │ │ Prose   │ │Complian.│                   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘                   │
│                                                                                  │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               TOOL LAYER                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   PubMed    │  │  Guidelines │  │   Market    │  │  Registry   │            │
│  │   Search    │  │   Lookup    │  │   Intel     │  │    Data     │            │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                                  │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                DATA LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │
│  │   PostgreSQL    │  │     Redis       │  │     MinIO       │                 │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │                 │
│  │  │   State   │  │  │  │   Cache   │  │  │  │ Documents │  │                 │
│  │  │   Store   │  │  │  │           │  │  │  │           │  │                 │
│  │  ├───────────┤  │  │  ├───────────┤  │  │  ├───────────┤  │                 │
│  │  │Checkpoints│  │  │  │  Queues   │  │  │  │  Assets   │  │                 │
│  │  ├───────────┤  │  │  ├───────────┤  │  │  ├───────────┤  │                 │
│  │  │ pgvector  │  │  │  │ Sessions  │  │  │  │  Exports  │  │                 │
│  │  └───────────┘  │  │  └───────────┘  │  │  └───────────┘  │                 │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                 │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# 2. System Components

## 2.1 Component Inventory

| Component | Technology | Purpose | Scaling Model |
|-----------|------------|---------|---------------|
| API Gateway | FastAPI | REST API, auth, routing | Horizontal (replicas) |
| Orchestrator | LangGraph | Workflow management | Single-threaded per pipeline |
| Agents (12) | LangChain + Claude | Content generation | Concurrent execution |
| State Store | PostgreSQL 16 | Persistent state, checkpoints | Vertical + read replicas |
| Vector Store | pgvector | Semantic search | Embedded in PostgreSQL |
| Cache | Redis 7 | Session cache, rate limiting | Cluster mode |
| Queue | Redis Streams | Async task processing | Cluster mode |
| Object Store | MinIO | Document storage | Distributed mode |
| Observability | LangSmith + Prometheus | Tracing, metrics | SaaS + self-hosted |

## 2.2 Component Communication

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          COMMUNICATION PATTERNS                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  SYNCHRONOUS (Request/Response)                                                 │
│  ─────────────────────────────────                                              │
│  • Client → API: REST/JSON over HTTPS                                           │
│  • API → PostgreSQL: TCP/5432 (pgbouncer pooling)                              │
│  • API → Redis: TCP/6379                                                        │
│  • Agent → Claude API: HTTPS/REST                                               │
│  • Agent → PubMed: HTTPS/REST                                                   │
│                                                                                  │
│  ASYNCHRONOUS (Event-Driven)                                                    │
│  ─────────────────────────────────                                              │
│  • Pipeline Execution: Redis Streams                                            │
│  • Progress Updates: WebSocket                                                  │
│  • Human Review: Webhook callbacks                                              │
│                                                                                  │
│  DATA FLOWS                                                                      │
│  ─────────────────────────────────                                              │
│  • State: API ↔ PostgreSQL (read/write)                                        │
│  • Cache: API ↔ Redis (ephemeral)                                              │
│  • Documents: API ↔ MinIO (blob storage)                                       │
│  • Traces: All → LangSmith (write-only)                                        │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 2.3 Component Dependencies

```
                                ┌─────────────┐
                                │  LibreChat  │
                                │    (UI)     │
                                └──────┬──────┘
                                       │
                                       ▼
                                ┌─────────────┐
                                │   FastAPI   │
                                │  (Gateway)  │
                                └──────┬──────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
             ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
             │  LangGraph  │   │    Redis    │   │   MinIO     │
             │(Orchestrator)│   │   (Cache)   │   │  (Storage)  │
             └──────┬──────┘   └─────────────┘   └─────────────┘
                    │
         ┌──────────┼──────────┐
         │          │          │
         ▼          ▼          ▼
   ┌───────────┐ ┌───────────┐ ┌───────────┐
   │  Agents   │ │PostgreSQL │ │ LangSmith │
   │  (1-12)   │ │  (State)  │ │ (Traces)  │
   └─────┬─────┘ └───────────┘ └───────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│Claude │ │PubMed │
│  API  │ │  API  │
└───────┘ └───────┘

Legend:
────▶  Runtime dependency
```

---

# 3. Agent Architecture

## 3.1 Agent Design Pattern

Each agent follows a consistent architectural pattern:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            AGENT INTERNAL STRUCTURE                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                           BaseAgent (Abstract)                           │   │
│   │                                                                          │   │
│   │  Properties:                                                             │   │
│   │  • name: str                                                             │   │
│   │  • llm: ChatAnthropic                                                    │   │
│   │  • tools: List[BaseTool]                                                 │   │
│   │  • prompt: ChatPromptTemplate                                            │   │
│   │                                                                          │   │
│   │  Methods:                                                                │   │
│   │  • run(state) → state                                                    │   │
│   │  • validate_input(state) → bool                                          │   │
│   │  • validate_output(output) → bool                                        │   │
│   │  • handle_error(error) → state                                           │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                       │
│                                          │ extends                               │
│                                          ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                         ConcreteAgent (e.g., Research)                   │   │
│   │                                                                          │   │
│   │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐               │   │
│   │  │    Prompt     │  │    Tools      │  │   Output      │               │   │
│   │  │   Template    │  │   Binding     │  │   Schema      │               │   │
│   │  └───────────────┘  └───────────────┘  └───────────────┘               │   │
│   │                                                                          │   │
│   │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│   │  │                     AgentExecutor                                │    │   │
│   │  │  • Manages tool calling loop                                     │    │   │
│   │  │  • Handles intermediate steps                                    │    │   │
│   │  │  • Enforces iteration limits                                     │    │   │
│   │  └─────────────────────────────────────────────────────────────────┘    │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 3.2 Agent Class Hierarchy

```python
# Agent Class Structure

BaseAgent (ABC)
│
├── ResearchAgent          # Agent 2: Literature, epidemiology
├── ClinicalAgent          # Agent 3: Practice patterns, barriers
├── GapAnalysisAgent       # Agent 4: Gap synthesis, prioritization
├── NeedsAssessmentAgent   # Agent 5: 3,100+ word narrative
├── LearningObjectivesAgent # Agent 6: Moore's Framework objectives
├── CurriculumAgent        # Agent 7: Educational design
├── ProtocolAgent          # Agent 8: Research protocol
├── MarketingAgent         # Agent 9: Audience generation
├── GrantWriterAgent       # Agent 10: Package assembly
├── ProseQualityAgent      # Agent 11: Writing enforcement
└── ComplianceAgent        # Agent 12: ACCME verification
```

## 3.3 Agent Execution Model

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AGENT EXECUTION FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────┐                                                                   │
│   │  State  │                                                                   │
│   │  Input  │                                                                   │
│   └────┬────┘                                                                   │
│        │                                                                         │
│        ▼                                                                         │
│   ┌─────────────────┐                                                           │
│   │ Input Validation│──── Invalid ────▶ Raise ValidationError                   │
│   └────────┬────────┘                                                           │
│            │ Valid                                                               │
│            ▼                                                                     │
│   ┌─────────────────┐                                                           │
│   │ Format Prompt   │                                                           │
│   │ with State Data │                                                           │
│   └────────┬────────┘                                                           │
│            │                                                                     │
│            ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                        AGENT EXECUTOR LOOP                               │   │
│   │                                                                          │   │
│   │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                │   │
│   │   │   LLM Call  │───▶│ Parse Action│───▶│Execute Tool │                │   │
│   │   │             │    │             │    │  (if needed)│                │   │
│   │   └─────────────┘    └─────────────┘    └──────┬──────┘                │   │
│   │         ▲                                      │                        │   │
│   │         │                                      │                        │   │
│   │         └──────────── Continue ◀───────────────┘                        │   │
│   │                                                                          │   │
│   │   Exit conditions:                                                       │   │
│   │   • "Final Answer" action type                                          │   │
│   │   • Max iterations reached (10)                                         │   │
│   │   • Error threshold exceeded                                            │   │
│   │                                                                          │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│            │                                                                     │
│            ▼                                                                     │
│   ┌─────────────────┐                                                           │
│   │ Parse Output to │                                                           │
│   │ Schema Structure│                                                           │
│   └────────┬────────┘                                                           │
│            │                                                                     │
│            ▼                                                                     │
│   ┌─────────────────┐                                                           │
│   │Output Validation│──── Invalid ────▶ Retry (max 2) or Error                 │
│   └────────┬────────┘                                                           │
│            │ Valid                                                               │
│            ▼                                                                     │
│   ┌─────────────────┐                                                           │
│   │  Update State   │                                                           │
│   │  with Output    │                                                           │
│   └────────┬────────┘                                                           │
│            │                                                                     │
│            ▼                                                                     │
│   ┌─────────┐                                                                   │
│   │  State  │                                                                   │
│   │ Output  │                                                                   │
│   └─────────┘                                                                   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 3.4 Agent Tool Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              TOOL ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                           BaseTool (LangChain)                           │   │
│   │                                                                          │   │
│   │  • name: str                                                             │   │
│   │  • description: str                                                      │   │
│   │  • args_schema: BaseModel                                                │   │
│   │  • _run() / _arun(): Implementation                                      │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   RESEARCH TOOLS                        CLINICAL TOOLS                          │
│   ───────────────                       ──────────────                          │
│   ┌─────────────────┐                   ┌─────────────────┐                    │
│   │ PubMedSearch    │                   │ RegistryQuery   │                    │
│   │ • query         │                   │ • condition     │                    │
│   │ • date_range    │                   │ • metrics       │                    │
│   │ • max_results   │                   │ • population    │                    │
│   └─────────────────┘                   └─────────────────┘                    │
│   ┌─────────────────┐                   ┌─────────────────┐                    │
│   │ GuidelinesSearch│                   │ ClaimsAnalysis  │                    │
│   │ • organization  │                   │ • procedure     │                    │
│   │ • topic         │                   │ • diagnosis     │                    │
│   │ • year          │                   │ • timeframe     │                    │
│   └─────────────────┘                   └─────────────────┘                    │
│   ┌─────────────────┐                   ┌─────────────────┐                    │
│   │ EpidemiologyLookup│                 │ PracticeSurvey  │                    │
│   │ • condition     │                   │ • specialty     │                    │
│   │ • geography     │                   │ • question_set  │                    │
│   └─────────────────┘                   └─────────────────┘                    │
│   ┌─────────────────┐                   ┌─────────────────┐                    │
│   │ MarketIntel     │                   │ QualityMeasures │                    │
│   │ • product       │                   │ • measure_set   │                    │
│   │ • competitor    │                   │ • population    │                    │
│   └─────────────────┘                   └─────────────────┘                    │
│                                                                                  │
│   TOOL-AGENT MAPPING                                                            │
│   ──────────────────                                                            │
│   Agent 2 (Research)  → PubMedSearch, GuidelinesSearch, EpidemiologyLookup,    │
│                         MarketIntel, ClinicalTrialsSearch                       │
│   Agent 3 (Clinical)  → RegistryQuery, ClaimsAnalysis, PracticeSurvey,         │
│                         QualityMeasures, DisparityData                          │
│   Agents 4-12         → No external tools (LLM-only reasoning)                  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 3.5 Agent Configuration

```yaml
# config/agents.yaml

agents:
  research:
    name: "research_agent"
    model: "claude-3-5-sonnet-20241022"
    temperature: 0.1
    max_tokens: 8192
    max_iterations: 10
    tools:
      - pubmed_search
      - guidelines_search
      - epidemiology_lookup
      - market_intel
    retry_policy:
      max_retries: 3
      backoff_factor: 2

  clinical:
    name: "clinical_agent"
    model: "claude-3-5-sonnet-20241022"
    temperature: 0.1
    max_tokens: 8192
    max_iterations: 10
    tools:
      - registry_query
      - claims_analysis
      - practice_survey
      - quality_measures
    retry_policy:
      max_retries: 3
      backoff_factor: 2

  needs_assessment:
    name: "needs_assessment_agent"
    model: "claude-3-5-sonnet-20241022"
    temperature: 0.3  # Slightly higher for creative writing
    max_tokens: 16384  # Larger for long-form content
    max_iterations: 5
    tools: []  # No tools - pure generation
    retry_policy:
      max_retries: 3
      backoff_factor: 2

  prose_quality:
    name: "prose_quality_agent"
    model: "claude-3-5-sonnet-20241022"
    temperature: 0.0  # Deterministic analysis
    max_tokens: 4096
    max_iterations: 1  # Single pass analysis
    tools: []
    retry_policy:
      max_retries: 2
      backoff_factor: 1
```

---

# 4. Orchestration Layer

## 4.1 LangGraph StateGraph Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         LANGGRAPH STATEGRAPH ENGINE                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                            StateGraph                                    │   │
│   │                                                                          │   │
│   │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│   │  │                         State Schema                             │    │   │
│   │  │                     (CMEGrantState TypedDict)                    │    │   │
│   │  │                                                                  │    │   │
│   │  │  • Immutable during node execution                              │    │   │
│   │  │  • Updated atomically after node completion                      │    │   │
│   │  │  • Checkpointed after each transition                           │    │   │
│   │  └─────────────────────────────────────────────────────────────────┘    │   │
│   │                                                                          │   │
│   │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│   │  │                           Nodes                                  │    │   │
│   │  │                                                                  │    │   │
│   │  │  • Each node is a function: (state) → state                     │    │   │
│   │  │  • Nodes wrap agent execution                                    │    │   │
│   │  │  • Nodes can execute in parallel (fan-out)                      │    │   │
│   │  │  • Nodes synchronize at join points (fan-in)                    │    │   │
│   │  └─────────────────────────────────────────────────────────────────┘    │   │
│   │                                                                          │   │
│   │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│   │  │                           Edges                                  │    │   │
│   │  │                                                                  │    │   │
│   │  │  • Normal edges: A → B (unconditional)                          │    │   │
│   │  │  • Conditional edges: A → {B, C, D} (based on state)            │    │   │
│   │  │  • Entry point: START → first node                              │    │   │
│   │  │  • Terminal: node → END                                         │    │   │
│   │  └─────────────────────────────────────────────────────────────────┘    │   │
│   │                                                                          │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                          Checkpointer                                    │   │
│   │                       (PostgresSaver)                                    │   │
│   │                                                                          │   │
│   │  • Persists state after each node execution                            │   │
│   │  • Enables resume from any checkpoint                                   │   │
│   │  • Thread-based isolation (thread_id = project_id)                     │   │
│   │  • Supports time-travel debugging                                       │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 4.2 Graph Topology

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              GRAPH TOPOLOGY                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│                              ┌─────────┐                                        │
│                              │  START  │                                        │
│                              └────┬────┘                                        │
│                                   │                                              │
│                    ┌──────────────┴──────────────┐                              │
│                    │                             │                              │
│                    ▼                             ▼                              │
│              ┌──────────┐                  ┌──────────┐                         │
│              │ research │                  │ clinical │                         │
│              └────┬─────┘                  └────┬─────┘                         │
│                   │                             │                              │
│                   └──────────────┬──────────────┘                              │
│                                  │ (fan-in: both complete)                     │
│                                  ▼                                              │
│                           ┌─────────────┐                                       │
│                           │gap_analysis │                                       │
│                           └──────┬──────┘                                       │
│                                  │                                              │
│                                  ▼                                              │
│                       ┌──────────────────┐                                      │
│                       │needs_assessment  │◀──────────┐                          │
│                       └────────┬─────────┘           │                          │
│                                │                     │ (retry)                  │
│                                ▼                     │                          │
│                        ┌──────────────┐              │                          │
│                        │prose_quality │──── fail ────┘                          │
│                        └──────┬───────┘                                         │
│                          pass │                                                 │
│                               ▼                                                 │
│                    ┌───────────────────┐                                        │
│                    │learning_objectives│                                        │
│                    └─────────┬─────────┘                                        │
│                              │                                                  │
│               ┌──────────────┼──────────────┐                                  │
│               │              │              │                                  │
│               ▼              ▼              ▼                                  │
│         ┌──────────┐  ┌──────────┐  ┌──────────┐                              │
│         │curriculum│  │ protocol │  │marketing │                              │
│         └────┬─────┘  └────┬─────┘  └────┬─────┘                              │
│              │              │              │                                  │
│              └──────────────┼──────────────┘                                  │
│                             │ (fan-in: all complete)                          │
│                             ▼                                                  │
│                      ┌─────────────┐                                           │
│                      │grant_writer │◀──────────┐                               │
│                      └──────┬──────┘           │                               │
│                             │                  │ (retry)                       │
│                             ▼                  │                               │
│                      ┌──────────────┐          │                               │
│                      │prose_quality │── fail ──┘                               │
│                      └──────┬───────┘                                          │
│                        pass │                                                  │
│                             ▼                                                  │
│                      ┌──────────────┐                                          │
│                      │ compliance   │◀─────────┐                               │
│                      └──────┬───────┘          │                               │
│                             │                  │ (fix)                         │
│                   compliant │ non-compliant ───┘                               │
│                             ▼                                                  │
│                      ┌──────────────┐                                          │
│                      │human_review  │                                          │
│                      └──────┬───────┘                                          │
│                             │                                                  │
│               ┌─────────────┼─────────────┐                                    │
│               │             │             │                                    │
│               ▼             ▼             ▼                                    │
│            ┌─────┐     ┌─────────┐   ┌─────────┐                              │
│            │ END │     │revision │   │rejected │                              │
│            │(done)│     │(route)  │   │ (END)   │                              │
│            └─────┘     └─────────┘   └─────────┘                              │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

EDGE TYPES:
  ────▶  Normal edge (unconditional)
  ─ ─ ▶  Conditional edge (based on state evaluation)
```

## 4.3 Routing Logic

```python
# Routing Decision Matrix

ROUTING_DECISIONS = {
    "prose_quality": {
        "conditions": {
            "pass_1_success": "learning_objectives",
            "pass_1_fail_retry": "needs_assessment",
            "pass_2_success": "compliance",
            "pass_2_fail_retry": "grant_writer",
            "max_retries_exceeded": "human_escalation",
        },
        "decision_factors": [
            "state.status",           # Which pass are we on?
            "latest_score.passed",    # Did it pass?
            "state.retry_count",      # How many retries?
        ]
    },
    
    "compliance": {
        "conditions": {
            "compliant": "human_review",
            "commercial_bias": "grant_writer",
            "missing_disclosure": "grant_writer",
            "objective_format": "learning_objectives",
            "gap_evidence": "gap_analysis",
            "max_retries_exceeded": "human_escalation",
        },
        "decision_factors": [
            "compliance_score.compliant",
            "compliance_score.primary_issue_type",
            "state.retry_count",
        ]
    },
    
    "human_review": {
        "conditions": {
            "approved": "END",
            "rejected": "END",
            "revision_requested": "grant_writer",  # Or specific agent
        },
        "decision_factors": [
            "state.human_review_status",
            "state.human_review_notes",
        ]
    }
}
```

## 4.4 Checkpointing Strategy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CHECKPOINT STRATEGY                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   CHECKPOINT POINTS (14 total):                                                 │
│   ─────────────────────────────                                                 │
│   1.  After intake validation                                                   │
│   2.  After research completion                                                 │
│   3.  After clinical completion                                                 │
│   4.  After gap analysis                                                        │
│   5.  After needs assessment                                                    │
│   6.  After prose quality pass 1                                                │
│   7.  After learning objectives                                                 │
│   8.  After curriculum                                                          │
│   9.  After protocol                                                            │
│   10. After marketing                                                           │
│   11. After grant writer                                                        │
│   12. After prose quality pass 2                                                │
│   13. After compliance                                                          │
│   14. After human review                                                        │
│                                                                                  │
│   CHECKPOINT DATA:                                                              │
│   ─────────────────                                                             │
│   • thread_id: Project identifier                                               │
│   • checkpoint_id: UUID for this checkpoint                                     │
│   • parent_id: Previous checkpoint UUID                                         │
│   • state: Complete CMEGrantState                                               │
│   • metadata: Timing, token usage, etc.                                         │
│   • created_at: Timestamp                                                       │
│                                                                                  │
│   RECOVERY SCENARIOS:                                                           │
│   ────────────────────                                                          │
│   • System crash → Resume from last checkpoint                                  │
│   • Human review pause → Resume after approval                                  │
│   • Manual intervention → Load specific checkpoint                              │
│   • Debugging → Time-travel to any checkpoint                                   │
│                                                                                  │
│   STORAGE:                                                                       │
│   ─────────                                                                      │
│   • PostgreSQL table: langgraph_checkpoints                                     │
│   • Indexed by: thread_id, created_at                                           │
│   • Retention: 90 days (configurable)                                           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. Data Architecture

## 5.1 Data Model Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA MODEL                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐          │
│   │    projects     │     │  checkpoints    │     │   documents     │          │
│   ├─────────────────┤     ├─────────────────┤     ├─────────────────┤          │
│   │ id (PK)         │     │ id (PK)         │     │ id (PK)         │          │
│   │ name            │     │ thread_id (FK)  │────▶│ project_id (FK) │          │
│   │ status          │◀────│ state (JSONB)   │     │ type            │          │
│   │ intake (JSONB)  │     │ parent_id       │     │ path            │          │
│   │ created_at      │     │ created_at      │     │ metadata        │          │
│   │ updated_at      │     │ metadata        │     │ created_at      │          │
│   └────────┬────────┘     └─────────────────┘     └─────────────────┘          │
│            │                                                                     │
│            │ 1:N                                                                │
│            ▼                                                                     │
│   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐          │
│   │ agent_outputs   │     │   audit_log     │     │     users       │          │
│   ├─────────────────┤     ├─────────────────┤     ├─────────────────┤          │
│   │ id (PK)         │     │ id (PK)         │     │ id (PK)         │          │
│   │ project_id (FK) │     │ project_id (FK) │     │ email           │          │
│   │ agent_name      │     │ action          │     │ role            │          │
│   │ output (JSONB)  │     │ user_id (FK)    │     │ created_at      │          │
│   │ version         │     │ timestamp       │     │ last_login      │          │
│   │ created_at      │     │ details         │     └─────────────────┘          │
│   └─────────────────┘     └─────────────────┘                                   │
│                                                                                  │
│   ┌─────────────────┐                                                           │
│   │   embeddings    │     (pgvector extension)                                  │
│   ├─────────────────┤                                                           │
│   │ id (PK)         │                                                           │
│   │ source_type     │     • research_citations                                  │
│   │ source_id       │     • clinical_findings                                   │
│   │ content         │     • gap_statements                                      │
│   │ embedding       │     • needs_assessment_sections                           │
│   │ metadata        │                                                           │
│   └─────────────────┘                                                           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 5.2 PostgreSQL Schema

```sql
-- Core Tables

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'intake',
    intake JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    
    CONSTRAINT valid_status CHECK (
        status IN ('intake', 'processing', 'review', 'complete', 'failed')
    )
);

CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);

-- LangGraph Checkpoints (managed by PostgresSaver)
CREATE TABLE langgraph_checkpoints (
    thread_id VARCHAR(255) NOT NULL,
    checkpoint_id UUID NOT NULL,
    parent_id UUID,
    state JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (thread_id, checkpoint_id),
    FOREIGN KEY (thread_id, parent_id) 
        REFERENCES langgraph_checkpoints(thread_id, checkpoint_id)
);

CREATE INDEX idx_checkpoints_thread ON langgraph_checkpoints(thread_id);
CREATE INDEX idx_checkpoints_created ON langgraph_checkpoints(created_at DESC);

-- Agent Outputs (denormalized for query performance)
CREATE TABLE agent_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    agent_name VARCHAR(50) NOT NULL,
    output JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    execution_time_ms INTEGER,
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (project_id, agent_name, version)
);

CREATE INDEX idx_agent_outputs_project ON agent_outputs(project_id);

-- Vector Embeddings (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(50) NOT NULL,
    source_id UUID NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI embedding dimension
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_embeddings_source ON embeddings(source_type, source_id);
CREATE INDEX idx_embeddings_vector ON embeddings 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Audit Log
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    ip_address INET,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_project ON audit_log(project_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);

-- Document Storage References
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    type VARCHAR(50) NOT NULL,  -- 'intake', 'output', 'export'
    filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,  -- MinIO path
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    checksum VARCHAR(64),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_project ON documents(project_id);
```

## 5.3 State Schema (TypedDict)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            CMEGrantState Structure                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  CMEGrantState                                                                  │
│  ├── project_id: str                                                            │
│  ├── project_name: str                                                          │
│  ├── created_at: str                                                            │
│  ├── updated_at: str                                                            │
│  ├── status: ProjectStatus                                                      │
│  │                                                                               │
│  ├── intake: IntakeData                                                         │
│  │   ├── section_a: ProjectBasics (5 fields)                                   │
│  │   ├── section_b: EducationalContext (6 fields)                              │
│  │   ├── section_c: SupporterInfo (4 fields)                                   │
│  │   ├── section_d: ActivityFormat (5 fields)                                  │
│  │   ├── section_e: Accreditation (4 fields)                                   │
│  │   ├── section_f: ClinicalContent (6 fields)                                 │
│  │   ├── section_g: FacultySpecs (4 fields)                                    │
│  │   ├── section_h: AudienceDetails (5 fields)                                 │
│  │   ├── section_i: Timeline (4 fields)                                        │
│  │   └── section_j: SpecialRequirements (4 fields)                             │
│  │                                                                               │
│  ├── research_output: Optional[ResearchOutput]                                  │
│  │   ├── epidemiology: dict                                                     │
│  │   ├── economic_burden: dict                                                  │
│  │   ├── treatment_landscape: dict                                              │
│  │   ├── market_intelligence: dict                                              │
│  │   ├── literature_synthesis: str                                              │
│  │   └── citations: List[Citation]                                              │
│  │                                                                               │
│  ├── clinical_output: Optional[ClinicalOutput]                                  │
│  ├── gap_analysis_output: Optional[GapAnalysisOutput]                           │
│  ├── needs_assessment_output: Optional[NeedsAssessmentOutput]                   │
│  ├── learning_objectives_output: Optional[LearningObjectivesOutput]             │
│  ├── curriculum_output: Optional[CurriculumOutput]                              │
│  ├── protocol_output: Optional[ProtocolOutput]                                  │
│  ├── marketing_output: Optional[MarketingOutput]                                │
│  ├── grant_package_output: Optional[GrantPackageOutput]                         │
│  │                                                                               │
│  ├── prose_quality_scores: List[ProseQualityScore]                              │
│  ├── compliance_score: Optional[ComplianceScore]                                │
│  │                                                                               │
│  ├── current_agent: Optional[str]                                               │
│  ├── execution_history: List[ExecutionRecord]                                   │
│  ├── errors: List[ErrorRecord]                                                  │
│  ├── retry_count: int                                                           │
│  │                                                                               │
│  ├── human_review_status: Optional[HumanReviewStatus]                           │
│  ├── human_review_notes: Optional[str]                                          │
│  ├── human_reviewer: Optional[str]                                              │
│  └── human_review_timestamp: Optional[str]                                      │
│                                                                                  │
│  Total: ~150 fields across all nested structures                                │
│  Estimated size: 50-200 KB per project state                                    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 5.4 Redis Data Structures

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           REDIS DATA STRUCTURES                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  SESSION CACHE (Hash)                                                           │
│  ────────────────────                                                           │
│  Key: session:{session_id}                                                      │
│  Fields:                                                                         │
│    user_id: UUID                                                                │
│    project_id: UUID (current)                                                   │
│    last_activity: timestamp                                                     │
│    metadata: JSON string                                                        │
│  TTL: 24 hours                                                                  │
│                                                                                  │
│  RATE LIMITING (Sorted Set)                                                     │
│  ──────────────────────────                                                     │
│  Key: ratelimit:{user_id}:{endpoint}                                            │
│  Members: request timestamps                                                    │
│  Score: timestamp                                                               │
│  TTL: 1 hour                                                                    │
│                                                                                  │
│  TASK QUEUE (Stream)                                                            │
│  ────────────────────                                                           │
│  Key: tasks:pipeline                                                            │
│  Fields per entry:                                                              │
│    project_id: UUID                                                             │
│    action: string                                                               │
│    payload: JSON string                                                         │
│    created_at: timestamp                                                        │
│  Consumer groups: workers                                                       │
│                                                                                  │
│  PROGRESS TRACKING (Hash)                                                       │
│  ─────────────────────────                                                      │
│  Key: progress:{project_id}                                                     │
│  Fields:                                                                         │
│    status: string                                                               │
│    current_agent: string                                                        │
│    percent_complete: int                                                        │
│    started_at: timestamp                                                        │
│    last_updated: timestamp                                                      │
│  TTL: 7 days                                                                    │
│                                                                                  │
│  PUBSUB CHANNELS                                                                │
│  ────────────────                                                               │
│  Channel: project:{project_id}:updates                                          │
│  Messages:                                                                       │
│    { type: "progress", data: {...} }                                            │
│    { type: "complete", data: {...} }                                            │
│    { type: "error", data: {...} }                                               │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 5.5 MinIO Object Storage

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          MINIO BUCKET STRUCTURE                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  dhg-cme-documents/                                                             │
│  │                                                                               │
│  ├── intake/                                                                    │
│  │   └── {project_id}/                                                          │
│  │       ├── intake-form.json                                                   │
│  │       └── attachments/                                                       │
│  │           └── *.pdf, *.docx                                                  │
│  │                                                                               │
│  ├── outputs/                                                                   │
│  │   └── {project_id}/                                                          │
│  │       ├── research-output.json                                               │
│  │       ├── clinical-output.json                                               │
│  │       ├── needs-assessment.md                                                │
│  │       ├── learning-objectives.json                                           │
│  │       ├── grant-package.json                                                 │
│  │       └── ...                                                                │
│  │                                                                               │
│  ├── exports/                                                                   │
│  │   └── {project_id}/                                                          │
│  │       ├── grant-package-v1.docx                                              │
│  │       ├── grant-package-v1.pdf                                               │
│  │       └── grant-package-v2.docx                                              │
│  │                                                                               │
│  └── templates/                                                                 │
│      ├── grant-template.docx                                                    │
│      ├── budget-template.xlsx                                                   │
│      └── disclosure-template.docx                                               │
│                                                                                  │
│  BUCKET POLICIES:                                                               │
│  ─────────────────                                                              │
│  • intake/: Write once, read many                                               │
│  • outputs/: Versioned, append-only                                             │
│  • exports/: User-downloadable (presigned URLs)                                 │
│  • templates/: Read-only for application                                        │
│                                                                                  │
│  LIFECYCLE RULES:                                                               │
│  ─────────────────                                                              │
│  • Delete incomplete multipart uploads after 7 days                             │
│  • Archive exports/ older than 90 days to cold storage                          │
│  • Retain intake/ and outputs/ for compliance (configurable)                    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# 6. API Architecture

## 6.1 API Design

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              REST API DESIGN                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  BASE URL: https://api.dhg-cme.com/v2                                           │
│                                                                                  │
│  AUTHENTICATION                                                                 │
│  ──────────────                                                                 │
│  Header: Authorization: Bearer {jwt_token}                                      │
│  Token contains: user_id, roles, exp                                            │
│                                                                                  │
│  ENDPOINTS                                                                       │
│  ─────────                                                                       │
│                                                                                  │
│  Projects                                                                        │
│  POST   /projects              Create project (submit intake)                   │
│  GET    /projects              List user's projects                             │
│  GET    /projects/{id}         Get project details                              │
│  DELETE /projects/{id}         Delete project (soft delete)                     │
│                                                                                  │
│  Pipeline                                                                        │
│  POST   /projects/{id}/start   Start pipeline execution                         │
│  GET    /projects/{id}/status  Get execution status                             │
│  POST   /projects/{id}/pause   Pause execution                                  │
│  POST   /projects/{id}/resume  Resume execution                                 │
│  POST   /projects/{id}/cancel  Cancel execution                                 │
│                                                                                  │
│  Outputs                                                                         │
│  GET    /projects/{id}/outputs              List all outputs                    │
│  GET    /projects/{id}/outputs/{agent}      Get specific agent output           │
│  GET    /projects/{id}/outputs/{agent}/download  Download as file              │
│                                                                                  │
│  Human Review                                                                    │
│  GET    /projects/{id}/review              Get review status                    │
│  POST   /projects/{id}/review/approve      Approve                              │
│  POST   /projects/{id}/review/reject       Reject                               │
│  POST   /projects/{id}/review/revise       Request revision                     │
│                                                                                  │
│  Admin                                                                           │
│  GET    /admin/projects                    List all projects                    │
│  GET    /admin/metrics                     System metrics                       │
│  GET    /admin/agents/{name}/metrics       Agent-specific metrics               │
│                                                                                  │
│  Health                                                                          │
│  GET    /health                            Liveness check                       │
│  GET    /ready                             Readiness check                      │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 6.2 Request/Response Schemas

```python
# API Schemas (Pydantic)

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    INTAKE = "intake"
    PROCESSING = "processing"
    REVIEW = "review"
    COMPLETE = "complete"
    FAILED = "failed"


# Intake Submission
class IntakeSubmission(BaseModel):
    section_a: dict
    section_b: dict
    section_c: dict
    section_d: dict
    section_e: dict
    section_f: dict
    section_g: dict
    section_h: dict
    section_i: dict
    section_j: dict


class ProjectCreateResponse(BaseModel):
    project_id: str
    status: ProjectStatus
    message: str
    created_at: datetime


# Project Details
class ProjectDetail(BaseModel):
    id: str
    name: str
    status: ProjectStatus
    current_agent: Optional[str]
    progress_percent: int
    created_at: datetime
    updated_at: datetime
    outputs_available: List[str]
    human_review_status: Optional[str]


# Execution Status
class ExecutionStatus(BaseModel):
    project_id: str
    status: ProjectStatus
    current_agent: Optional[str]
    progress_percent: int
    agents_completed: List[str]
    agents_pending: List[str]
    errors: List[dict]
    started_at: Optional[datetime]
    estimated_completion: Optional[datetime]


# Human Review
class ReviewDecision(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject|revise)$")
    notes: Optional[str] = None
    revision_target: Optional[str] = None  # Agent to revise


# Error Response
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None
    request_id: str
```

## 6.3 WebSocket API

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            WEBSOCKET API                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ENDPOINT: wss://api.dhg-cme.com/v2/ws                                          │
│                                                                                  │
│  CONNECTION                                                                      │
│  ──────────                                                                      │
│  Query params: ?token={jwt_token}&project_id={project_id}                       │
│                                                                                  │
│  SERVER → CLIENT MESSAGES                                                        │
│  ─────────────────────────                                                       │
│                                                                                  │
│  Progress Update:                                                               │
│  {                                                                               │
│    "type": "progress",                                                          │
│    "data": {                                                                     │
│      "project_id": "uuid",                                                      │
│      "current_agent": "needs_assessment",                                       │
│      "progress_percent": 45,                                                    │
│      "message": "Generating needs assessment document..."                       │
│    }                                                                             │
│  }                                                                               │
│                                                                                  │
│  Agent Complete:                                                                │
│  {                                                                               │
│    "type": "agent_complete",                                                    │
│    "data": {                                                                     │
│      "agent": "needs_assessment",                                               │
│      "duration_ms": 45000,                                                      │
│      "output_preview": "..."                                                    │
│    }                                                                             │
│  }                                                                               │
│                                                                                  │
│  Quality Gate:                                                                  │
│  {                                                                               │
│    "type": "quality_gate",                                                      │
│    "data": {                                                                     │
│      "gate": "prose_quality_1",                                                 │
│      "passed": false,                                                           │
│      "score": 72,                                                               │
│      "issues": ["Low prose density in section 3"]                              │
│    }                                                                             │
│  }                                                                               │
│                                                                                  │
│  Human Review Required:                                                         │
│  {                                                                               │
│    "type": "human_review_required",                                             │
│    "data": {                                                                     │
│      "project_id": "uuid",                                                      │
│      "review_url": "https://..."                                                │
│    }                                                                             │
│  }                                                                               │
│                                                                                  │
│  Pipeline Complete:                                                             │
│  {                                                                               │
│    "type": "complete",                                                          │
│    "data": {                                                                     │
│      "project_id": "uuid",                                                      │
│      "duration_ms": 3600000,                                                    │
│      "download_url": "https://..."                                              │
│    }                                                                             │
│  }                                                                               │
│                                                                                  │
│  Error:                                                                         │
│  {                                                                               │
│    "type": "error",                                                             │
│    "data": {                                                                     │
│      "agent": "research",                                                       │
│      "error_type": "api_error",                                                 │
│      "message": "PubMed API rate limit exceeded",                               │
│      "recoverable": true                                                        │
│    }                                                                             │
│  }                                                                               │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# 7. Integration Patterns

## 7.1 External Service Integrations

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL INTEGRATIONS                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ANTHROPIC CLAUDE API                                                           │
│  ─────────────────────                                                          │
│  Purpose: LLM inference for all agents                                          │
│  Protocol: HTTPS/REST                                                           │
│  Authentication: API key (Bearer token)                                         │
│  Rate limits: 4000 req/min, 400K tokens/min                                     │
│  Retry strategy: Exponential backoff (1s, 2s, 4s, 8s)                           │
│  Fallback: OpenAI GPT-4 (if available)                                          │
│                                                                                  │
│  ┌─────────────┐     HTTPS/443     ┌─────────────┐                             │
│  │   Agent     │ ─────────────────▶│  Claude API │                             │
│  │  Executor   │◀───────────────── │             │                             │
│  └─────────────┘    JSON Response  └─────────────┘                             │
│                                                                                  │
│  PUBMED API (NCBI E-utilities)                                                  │
│  ─────────────────────────────                                                  │
│  Purpose: Literature search, citation retrieval                                 │
│  Protocol: HTTPS/REST                                                           │
│  Authentication: API key (optional, higher limits)                              │
│  Rate limits: 3 req/sec (with key: 10 req/sec)                                 │
│  Caching: Results cached 24 hours                                               │
│                                                                                  │
│  ┌─────────────┐     HTTPS/443     ┌─────────────┐                             │
│  │  PubMed     │ ─────────────────▶│ NCBI        │                             │
│  │   Tool      │◀───────────────── │ E-utilities │                             │
│  └─────────────┘    XML Response   └─────────────┘                             │
│                                                                                  │
│  LANGSMITH                                                                       │
│  ─────────                                                                       │
│  Purpose: Trace collection, debugging, analytics                                │
│  Protocol: HTTPS/REST                                                           │
│  Authentication: API key                                                        │
│  Data flow: Write-only (traces, feedback)                                       │
│  Async: Background thread, non-blocking                                         │
│                                                                                  │
│  ┌─────────────┐     HTTPS/443     ┌─────────────┐                             │
│  │ Application │ ─────────────────▶│  LangSmith  │                             │
│  │  (Traces)   │    Fire-and-forget│             │                             │
│  └─────────────┘                   └─────────────┘                             │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 7.2 Integration Patterns

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          INTEGRATION PATTERNS                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  1. CIRCUIT BREAKER                                                             │
│  ──────────────────                                                             │
│  Applied to: All external APIs                                                  │
│                                                                                  │
│  States:                                                                         │
│  • CLOSED: Normal operation                                                     │
│  • OPEN: Failing, reject immediately                                            │
│  • HALF-OPEN: Testing if service recovered                                      │
│                                                                                  │
│  Thresholds:                                                                    │
│  • Failure threshold: 5 failures in 60s → OPEN                                  │
│  • Recovery timeout: 30s → HALF-OPEN                                            │
│  • Success threshold: 3 successes → CLOSED                                      │
│                                                                                  │
│  ┌──────────┐    success    ┌──────────┐    failures    ┌──────────┐           │
│  │  CLOSED  │◀─────────────│HALF-OPEN │──────────────▶│   OPEN   │           │
│  └────┬─────┘              └──────────┘               └────┬─────┘           │
│       │ failures                ▲                          │                    │
│       └─────────────────────────┴──────────────────────────┘                    │
│                              timeout                                            │
│                                                                                  │
│  2. RETRY WITH BACKOFF                                                          │
│  ─────────────────────                                                          │
│  Applied to: Transient failures                                                 │
│                                                                                  │
│  Strategy:                                                                       │
│  • Max retries: 3                                                               │
│  • Base delay: 1 second                                                         │
│  • Multiplier: 2 (exponential)                                                  │
│  • Max delay: 30 seconds                                                        │
│  • Jitter: ±25%                                                                 │
│                                                                                  │
│  Retry 1: 1s (±0.25s)                                                           │
│  Retry 2: 2s (±0.5s)                                                            │
│  Retry 3: 4s (±1s)                                                              │
│                                                                                  │
│  3. CACHING                                                                     │
│  ──────────                                                                      │
│  Applied to: PubMed results, guidelines                                         │
│                                                                                  │
│  Strategy:                                                                       │
│  • Cache key: Hash of query parameters                                          │
│  • TTL: 24 hours (PubMed), 7 days (guidelines)                                 │
│  • Invalidation: Manual or on-demand                                            │
│  • Storage: Redis                                                               │
│                                                                                  │
│  4. FALLBACK                                                                    │
│  ───────────                                                                     │
│  Applied to: LLM provider                                                       │
│                                                                                  │
│  Primary: Anthropic Claude                                                      │
│  Fallback: OpenAI GPT-4 (if configured)                                         │
│  Trigger: Circuit breaker OPEN or rate limit                                    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# 8. Security Architecture

## 8.1 Security Layers

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SECURITY ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  LAYER 1: PERIMETER                                                             │
│  ──────────────────                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  • TLS 1.3 termination at load balancer                                 │   │
│  │  • WAF (Web Application Firewall)                                       │   │
│  │  • DDoS protection                                                      │   │
│  │  • IP allowlisting for admin endpoints                                  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  LAYER 2: AUTHENTICATION                                                        │
│  ───────────────────────                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  • OAuth 2.0 / OpenID Connect                                           │   │
│  │  • JWT tokens (RS256 signed)                                            │   │
│  │  • Token expiration: 1 hour (access), 7 days (refresh)                  │   │
│  │  • API key authentication for service accounts                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  LAYER 3: AUTHORIZATION                                                         │
│  ──────────────────────                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  • Role-Based Access Control (RBAC)                                     │   │
│  │  • Roles: admin, reviewer, user                                         │   │
│  │  • Resource-level permissions (project ownership)                       │   │
│  │  • Policy enforcement at API layer                                      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  LAYER 4: DATA PROTECTION                                                       │
│  ────────────────────────                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  • Encryption at rest: AES-256 (PostgreSQL, MinIO)                      │   │
│  │  • Encryption in transit: TLS 1.3                                       │   │
│  │  • Field-level encryption for PII                                       │   │
│  │  • Key management: Infisical vault                                      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  LAYER 5: AUDIT & MONITORING                                                    │
│  ───────────────────────────                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  • Comprehensive audit logging                                          │   │
│  │  • Log immutability (append-only)                                       │   │
│  │  • Real-time security alerting                                          │   │
│  │  • Anomaly detection                                                    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 8.2 RBAC Model

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              RBAC MODEL                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ROLES                                                                           │
│  ─────                                                                           │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  admin     │ Full system access, user management, configuration         │  │
│  │  reviewer  │ Review/approve projects, view all projects                 │  │
│  │  user      │ Create/manage own projects, view own outputs               │  │
│  │  service   │ API access only, specific endpoints                        │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  PERMISSIONS MATRIX                                                             │
│  ──────────────────                                                             │
│  ┌────────────────────────────────────────────────────────────────────────────┐│
│  │  Resource          │ admin │ reviewer │ user  │ service │                  ││
│  │  ────────────────────────────────────────────────────────                  ││
│  │  projects:create   │   ✓   │    ✓     │   ✓   │    ✓    │                  ││
│  │  projects:read_own │   ✓   │    ✓     │   ✓   │    ✓    │                  ││
│  │  projects:read_all │   ✓   │    ✓     │   ✗   │    ✗    │                  ││
│  │  projects:delete   │   ✓   │    ✗     │  own  │    ✗    │                  ││
│  │  review:approve    │   ✓   │    ✓     │   ✗   │    ✗    │                  ││
│  │  review:reject     │   ✓   │    ✓     │   ✗   │    ✗    │                  ││
│  │  admin:users       │   ✓   │    ✗     │   ✗   │    ✗    │                  ││
│  │  admin:config      │   ✓   │    ✗     │   ✗   │    ✗    │                  ││
│  │  admin:metrics     │   ✓   │    ✓     │   ✗   │    ✗    │                  ││
│  └────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 8.3 Secrets Management

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          SECRETS MANAGEMENT                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  SECRET TYPES                                                                    │
│  ────────────                                                                    │
│  • API keys (Anthropic, OpenAI, LangSmith, PubMed)                             │
│  • Database credentials                                                         │
│  • JWT signing keys                                                             │
│  • Encryption keys                                                              │
│  • OAuth client secrets                                                         │
│                                                                                  │
│  MANAGEMENT: Infisical                                                          │
│  ──────────────────────                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                          │   │
│  │  ┌────────────┐     Sync      ┌────────────┐                            │   │
│  │  │  Infisical │ ────────────▶ │   Redis    │  (runtime cache)           │   │
│  │  │   Vault    │               │            │                            │   │
│  │  └────────────┘               └────────────┘                            │   │
│  │        │                                                                 │   │
│  │        │ Inject at startup                                              │   │
│  │        ▼                                                                 │   │
│  │  ┌────────────┐                                                          │   │
│  │  │ Application│  Secrets as env vars                                    │   │
│  │  │ Container  │  Never logged or exposed                                │   │
│  │  └────────────┘                                                          │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ROTATION POLICY                                                                │
│  ────────────────                                                               │
│  • API keys: 90 days                                                            │
│  • Database passwords: 30 days                                                  │
│  • JWT signing keys: 7 days                                                     │
│  • Encryption keys: Annual                                                      │
│                                                                                  │
│  EMERGENCY ROTATION                                                             │
│  ────────────────────                                                           │
│  1. Generate new secret in Infisical                                           │
│  2. Deploy updated secret to running containers                                 │
│  3. Verify application health                                                   │
│  4. Revoke old secret                                                           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# 9. Observability Architecture

## 9.1 Observability Stack

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         OBSERVABILITY ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                          COLLECTION LAYER                                │   │
│  │                                                                          │   │
│  │  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐     │   │
│  │  │  LangSmith │   │ Prometheus │   │    Loki    │   │  Sentry    │     │   │
│  │  │  (Traces)  │   │ (Metrics)  │   │   (Logs)   │   │ (Errors)   │     │   │
│  │  └─────┬──────┘   └─────┬──────┘   └─────┬──────┘   └─────┬──────┘     │   │
│  │        │                │                │                │            │   │
│  └────────┼────────────────┼────────────────┼────────────────┼────────────┘   │
│           │                │                │                │                │
│           │                │                │                │                │
│  ┌────────┼────────────────┼────────────────┼────────────────┼────────────┐   │
│  │        ▼                ▼                ▼                ▼            │   │
│  │                       STORAGE LAYER                                    │   │
│  │                                                                         │   │
│  │  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐    │   │
│  │  │ LangSmith  │   │ Prometheus │   │    Loki    │   │  Sentry    │    │   │
│  │  │   Cloud    │   │    TSDB    │   │   Storage  │   │   Cloud    │    │   │
│  │  └────────────┘   └────────────┘   └────────────┘   └────────────┘    │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                           │
│                                    ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        VISUALIZATION LAYER                               │   │
│  │                                                                          │   │
│  │  ┌────────────┐   ┌────────────┐   ┌────────────┐                      │   │
│  │  │  Grafana   │   │ LangSmith  │   │  Sentry    │                      │   │
│  │  │ Dashboards │   │    UI      │   │    UI      │                      │   │
│  │  └────────────┘   └────────────┘   └────────────┘                      │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 9.2 Metrics

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              KEY METRICS                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  SYSTEM METRICS (Prometheus)                                                    │
│  ───────────────────────────                                                    │
│  • dhg_cme_api_requests_total{method, endpoint, status}                        │
│  • dhg_cme_api_request_duration_seconds{method, endpoint}                      │
│  • dhg_cme_api_requests_in_flight                                              │
│  • dhg_cme_db_connections_active                                               │
│  • dhg_cme_redis_connections_active                                            │
│                                                                                  │
│  PIPELINE METRICS                                                               │
│  ────────────────                                                               │
│  • dhg_cme_pipeline_executions_total{status}                                   │
│  • dhg_cme_pipeline_duration_seconds{status}                                   │
│  • dhg_cme_pipeline_active_count                                               │
│                                                                                  │
│  AGENT METRICS                                                                  │
│  ─────────────                                                                  │
│  • dhg_cme_agent_executions_total{agent, status}                               │
│  • dhg_cme_agent_duration_seconds{agent}                                       │
│  • dhg_cme_agent_tokens_used{agent, type}                                      │
│  • dhg_cme_agent_retries_total{agent}                                          │
│                                                                                  │
│  QUALITY METRICS                                                                │
│  ───────────────                                                                │
│  • dhg_cme_prose_quality_score{pass_number}                                    │
│  • dhg_cme_prose_quality_pass_rate{pass_number}                                │
│  • dhg_cme_compliance_score                                                     │
│  • dhg_cme_compliance_pass_rate                                                 │
│  • dhg_cme_human_review_outcome{outcome}                                       │
│                                                                                  │
│  EXTERNAL API METRICS                                                           │
│  ────────────────────                                                           │
│  • dhg_cme_external_api_requests_total{service, status}                        │
│  • dhg_cme_external_api_duration_seconds{service}                              │
│  • dhg_cme_external_api_errors_total{service, error_type}                      │
│                                                                                  │
│  BUSINESS METRICS                                                               │
│  ────────────────                                                               │
│  • dhg_cme_grants_completed_total                                              │
│  • dhg_cme_grants_first_pass_approval_rate                                     │
│  • dhg_cme_average_grant_duration_hours                                        │
│  • dhg_cme_cost_per_grant_usd                                                  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 9.3 Logging Strategy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            LOGGING STRATEGY                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  LOG FORMAT (Structured JSON)                                                   │
│  ────────────────────────────                                                   │
│  {                                                                               │
│    "timestamp": "2026-01-31T14:30:00.123Z",                                    │
│    "level": "info",                                                             │
│    "logger": "dhg_cme.agents.research",                                        │
│    "message": "Agent execution completed",                                      │
│    "project_id": "uuid",                                                        │
│    "agent": "research",                                                         │
│    "duration_ms": 45000,                                                        │
│    "tokens_used": 8500,                                                         │
│    "trace_id": "abc123",                                                        │
│    "span_id": "def456"                                                          │
│  }                                                                               │
│                                                                                  │
│  LOG LEVELS                                                                     │
│  ──────────                                                                      │
│  • DEBUG: Detailed debugging info (dev only)                                    │
│  • INFO: Normal operations, agent completions                                   │
│  • WARNING: Retries, degraded performance                                       │
│  • ERROR: Failures, exceptions                                                  │
│  • CRITICAL: System failures, data loss risks                                   │
│                                                                                  │
│  CORRELATION                                                                    │
│  ───────────                                                                     │
│  • trace_id: Links to LangSmith trace                                          │
│  • project_id: Links all logs for a project                                    │
│  • request_id: Links logs within single request                                │
│                                                                                  │
│  SENSITIVE DATA                                                                 │
│  ──────────────                                                                  │
│  • Never log: API keys, passwords, PII                                         │
│  • Mask: Email addresses, phone numbers                                        │
│  • Truncate: Large payloads (>1KB)                                             │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 9.4 Alerting Rules

```yaml
# alerting/rules.yaml

groups:
  - name: dhg-cme-critical
    rules:
      - alert: APIDown
        expr: up{job="dhg-cme-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "API server is down"
          
      - alert: PipelineFailureRate
        expr: rate(dhg_cme_pipeline_executions_total{status="failed"}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Pipeline failure rate exceeds 10%"
          
      - alert: ClaudeAPIErrors
        expr: rate(dhg_cme_external_api_errors_total{service="anthropic"}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Claude API error rate elevated"
          
      - alert: DatabaseConnectionsHigh
        expr: dhg_cme_db_connections_active > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database connections approaching limit"
          
      - alert: QualityScoreLow
        expr: avg(dhg_cme_prose_quality_score) < 70
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Average prose quality score below threshold"
```

---

# 10. Deployment Architecture

## 10.1 Container Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          CONTAINER ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                           APPLICATION CONTAINERS                         │   │
│  │                                                                          │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │   │
│  │  │   dhg-cme-api   │  │ dhg-cme-worker  │  │   librechat     │         │   │
│  │  │                 │  │                 │  │                 │         │   │
│  │  │ • FastAPI       │  │ • Pipeline exec │  │ • User UI       │         │   │
│  │  │ • REST API      │  │ • Agent runner  │  │ • Chat interface│         │   │
│  │  │ • WebSocket     │  │ • Background    │  │                 │         │   │
│  │  │                 │  │   tasks         │  │                 │         │   │
│  │  │ Port: 8000      │  │                 │  │ Port: 3080      │         │   │
│  │  │ Replicas: 2     │  │ Replicas: 3     │  │ Replicas: 2     │         │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘         │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                            DATA CONTAINERS                               │   │
│  │                                                                          │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │   │
│  │  │   postgresql    │  │     redis       │  │     minio       │         │   │
│  │  │                 │  │                 │  │                 │         │   │
│  │  │ • State store   │  │ • Cache         │  │ • Object store  │         │   │
│  │  │ • Checkpoints   │  │ • Sessions      │  │ • Documents     │         │   │
│  │  │ • pgvector      │  │ • Task queue    │  │                 │         │   │
│  │  │                 │  │                 │  │                 │         │   │
│  │  │ Port: 5432      │  │ Port: 6379      │  │ Port: 9000/9001 │         │   │
│  │  │ Replicas: 1     │  │ Replicas: 1     │  │ Replicas: 1     │         │   │
│  │  │ (primary)       │  │ (or cluster)    │  │ (or distributed)│         │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘         │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        OBSERVABILITY CONTAINERS                          │   │
│  │                                                                          │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │   │
│  │  │   prometheus    │  │    grafana      │  │      loki       │         │   │
│  │  │                 │  │                 │  │                 │         │   │
│  │  │ • Metrics       │  │ • Dashboards    │  │ • Log aggregation│        │   │
│  │  │ • Alerting      │  │ • Alerting UI   │  │                 │         │   │
│  │  │                 │  │                 │  │                 │         │   │
│  │  │ Port: 9090      │  │ Port: 3000      │  │ Port: 3100      │         │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘         │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 10.2 Network Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           NETWORK ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│                              ┌─────────────┐                                    │
│                              │  Internet   │                                    │
│                              └──────┬──────┘                                    │
│                                     │                                           │
│                              ┌──────▼──────┐                                    │
│                              │ Load Balancer│                                   │
│                              │  (TLS term)  │                                   │
│                              └──────┬──────┘                                    │
│                                     │                                           │
│  ┌──────────────────────────────────┼──────────────────────────────────┐       │
│  │                           PUBLIC SUBNET                              │       │
│  │                         (10.0.1.0/24)                               │       │
│  │                                  │                                   │       │
│  │   ┌──────────────┐    ┌─────────▼─────────┐    ┌──────────────┐    │       │
│  │   │  LibreChat   │    │    API Gateway    │    │   Grafana    │    │       │
│  │   │  :3080       │    │      :8000        │    │    :3000     │    │       │
│  │   └──────────────┘    └─────────┬─────────┘    └──────────────┘    │       │
│  │                                 │                                   │       │
│  └─────────────────────────────────┼───────────────────────────────────┘       │
│                                    │                                           │
│  ┌─────────────────────────────────┼───────────────────────────────────┐       │
│  │                         PRIVATE SUBNET                               │       │
│  │                        (10.0.2.0/24)                                │       │
│  │                                 │                                   │       │
│  │   ┌──────────────┐    ┌────────▼────────┐    ┌──────────────┐      │       │
│  │   │   Worker 1   │    │    Worker 2     │    │   Worker 3   │      │       │
│  │   └──────────────┘    └─────────────────┘    └──────────────┘      │       │
│  │                                                                      │       │
│  │   ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐      │       │
│  │   │  Prometheus  │    │      Loki       │    │  Alertmanager│      │       │
│  │   └──────────────┘    └─────────────────┘    └──────────────┘      │       │
│  │                                                                      │       │
│  └─────────────────────────────────┬───────────────────────────────────┘       │
│                                    │                                           │
│  ┌─────────────────────────────────┼───────────────────────────────────┐       │
│  │                        DATABASE SUBNET                               │       │
│  │                       (10.0.3.0/24)                                 │       │
│  │                                 │                                   │       │
│  │   ┌──────────────┐    ┌────────▼────────┐    ┌──────────────┐      │       │
│  │   │  PostgreSQL  │    │     Redis       │    │    MinIO     │      │       │
│  │   │   :5432      │    │     :6379       │    │  :9000/:9001 │      │       │
│  │   └──────────────┘    └─────────────────┘    └──────────────┘      │       │
│  │                                                                      │       │
│  └──────────────────────────────────────────────────────────────────────┘       │
│                                                                                  │
│  FIREWALL RULES                                                                 │
│  ──────────────                                                                 │
│  • Internet → Public: 443 (HTTPS), 3080 (LibreChat), 3000 (Grafana)           │
│  • Public → Private: All traffic                                               │
│  • Private → Database: 5432, 6379, 9000                                        │
│  • Database → Internet: Blocked                                                 │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 10.3 CI/CD Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             CI/CD PIPELINE                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐      │
│  │  Code   │───▶│  Build  │───▶│  Test   │───▶│ Deploy  │───▶│ Monitor │      │
│  │  Push   │    │         │    │         │    │         │    │         │      │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘      │
│                                                                                  │
│  STAGES                                                                          │
│  ──────                                                                          │
│                                                                                  │
│  1. CODE PUSH (GitHub)                                                          │
│     • PR created/updated                                                        │
│     • Branch: feature/* → main                                                  │
│                                                                                  │
│  2. BUILD                                                                        │
│     • Docker image build                                                        │
│     • Dependency installation                                                   │
│     • Image tagging (git SHA)                                                   │
│     • Push to registry                                                          │
│                                                                                  │
│  3. TEST                                                                         │
│     • Unit tests (pytest)                                                       │
│     • Integration tests                                                         │
│     • Linting (ruff)                                                            │
│     • Type checking (mypy)                                                      │
│     • Coverage report                                                           │
│                                                                                  │
│  4. DEPLOY                                                                       │
│     • Staging (automatic on main)                                               │
│     • Production (manual approval)                                              │
│     • Database migrations                                                       │
│     • Rolling update                                                            │
│                                                                                  │
│  5. MONITOR                                                                      │
│     • Deployment verification                                                   │
│     • Health check validation                                                   │
│     • Smoke tests                                                               │
│     • Rollback if needed                                                        │
│                                                                                  │
│  ENVIRONMENTS                                                                    │
│  ────────────                                                                    │
│  • Development: Local Docker Compose                                            │
│  • Staging: Auto-deploy on main merge                                           │
│  • Production: Manual approval required                                         │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# 11. Scalability & Performance

## 11.1 Scaling Strategy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SCALING STRATEGY                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  HORIZONTAL SCALING                                                             │
│  ──────────────────                                                             │
│                                                                                  │
│  API Layer:                                                                     │
│  • Stateless design enables horizontal scaling                                  │
│  • Load balancer distributes requests                                           │
│  • Scale trigger: CPU > 70% or requests > 100/s                                │
│  • Min: 2, Max: 10 replicas                                                     │
│                                                                                  │
│  Worker Layer:                                                                  │
│  • Each worker handles one pipeline at a time                                   │
│  • Scale based on queue depth                                                   │
│  • Scale trigger: Queue depth > 5 per worker                                    │
│  • Min: 3, Max: 20 replicas                                                     │
│                                                                                  │
│  VERTICAL SCALING                                                               │
│  ────────────────                                                               │
│                                                                                  │
│  PostgreSQL:                                                                    │
│  • Primary scaling approach for database                                        │
│  • Read replicas for query distribution                                         │
│  • Connection pooling via pgbouncer                                             │
│                                                                                  │
│  Redis:                                                                         │
│  • Cluster mode for high availability                                           │
│  • Memory scaling as needed                                                     │
│                                                                                  │
│  BOTTLENECK ANALYSIS                                                            │
│  ────────────────────                                                           │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  Component      │ Bottleneck          │ Mitigation                     │    │
│  │  ────────────────────────────────────────────────────────────────────  │    │
│  │  Claude API     │ Rate limits         │ Request queuing, backoff       │    │
│  │  PubMed API     │ Rate limits         │ Caching, batch requests        │    │
│  │  PostgreSQL     │ Write throughput    │ Connection pooling, batching   │    │
│  │  Worker         │ Memory (large docs) │ Streaming, chunking            │    │
│  │  Network        │ Egress bandwidth    │ Compression, CDN               │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 11.2 Performance Targets

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          PERFORMANCE TARGETS                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  LATENCY TARGETS                                                                │
│  ───────────────                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  Operation                    │ P50     │ P95     │ P99     │ Max     │    │
│  │  ────────────────────────────────────────────────────────────────────  │    │
│  │  API health check             │ 5ms     │ 20ms    │ 50ms    │ 100ms   │    │
│  │  Project create               │ 100ms   │ 300ms   │ 500ms   │ 1s      │    │
│  │  Project status               │ 20ms    │ 50ms    │ 100ms   │ 200ms   │    │
│  │  Agent execution (avg)        │ 30s     │ 60s     │ 90s     │ 120s    │    │
│  │  Full pipeline                │ 2h      │ 3h      │ 4h      │ 6h      │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  THROUGHPUT TARGETS                                                             │
│  ──────────────────                                                             │
│  • Concurrent pipelines: 10                                                     │
│  • API requests: 100/second                                                     │
│  • Completed grants: 20/day                                                     │
│                                                                                  │
│  RESOURCE LIMITS                                                                │
│  ───────────────                                                                │
│  • Worker memory: 8GB max per pipeline                                          │
│  • API memory: 2GB max per instance                                             │
│  • Database connections: 100 max                                                │
│  • Redis memory: 4GB max                                                        │
│                                                                                  │
│  TOKEN BUDGETS                                                                  │
│  ─────────────                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  Agent                        │ Input (avg) │ Output (avg) │ Max      │    │
│  │  ────────────────────────────────────────────────────────────────────  │    │
│  │  Research                     │ 2,000       │ 6,000        │ 15,000   │    │
│  │  Clinical                     │ 2,000       │ 5,000        │ 12,000   │    │
│  │  Gap Analysis                 │ 12,000      │ 3,000        │ 20,000   │    │
│  │  Needs Assessment             │ 8,000       │ 8,000        │ 20,000   │    │
│  │  Learning Objectives          │ 5,000       │ 2,000        │ 10,000   │    │
│  │  Curriculum                   │ 6,000       │ 4,000        │ 15,000   │    │
│  │  Protocol                     │ 4,000       │ 4,000        │ 12,000   │    │
│  │  Marketing                    │ 3,000       │ 3,000        │ 10,000   │    │
│  │  Grant Writer                 │ 30,000      │ 15,000       │ 50,000   │    │
│  │  Prose Quality                │ 15,000      │ 2,000        │ 20,000   │    │
│  │  Compliance                   │ 20,000      │ 3,000        │ 30,000   │    │
│  │  ────────────────────────────────────────────────────────────────────  │    │
│  │  TOTAL PER GRANT              │ ~100,000    │ ~55,000      │ 200,000  │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# 12. Disaster Recovery

## 12.1 Backup Strategy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            BACKUP STRATEGY                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  POSTGRESQL                                                                     │
│  ──────────                                                                      │
│  • Full backup: Daily at 02:00 UTC                                             │
│  • WAL archiving: Continuous                                                    │
│  • Retention: 30 days                                                           │
│  • Storage: S3-compatible (separate region)                                     │
│  • RTO: 1 hour                                                                  │
│  • RPO: 5 minutes                                                               │
│                                                                                  │
│  REDIS                                                                          │
│  ─────                                                                          │
│  • RDB snapshots: Every 15 minutes                                              │
│  • AOF persistence: Always                                                      │
│  • Retention: 7 days                                                            │
│  • Note: Cache is reconstructable                                               │
│                                                                                  │
│  MINIO                                                                          │
│  ─────                                                                          │
│  • Versioning: Enabled                                                          │
│  • Replication: Cross-region (if configured)                                    │
│  • Retention: Per bucket policy                                                 │
│                                                                                  │
│  RECOVERY PROCEDURES                                                            │
│  ────────────────────                                                           │
│  1. Database corruption:                                                        │
│     • Stop application                                                          │
│     • Restore from latest backup                                                │
│     • Apply WAL logs to point-in-time                                          │
│     • Verify data integrity                                                     │
│     • Resume application                                                        │
│                                                                                  │
│  2. Complete site failure:                                                      │
│     • Provision new infrastructure                                              │
│     • Restore database from backup                                              │
│     • Restore MinIO from replication                                            │
│     • Update DNS                                                                │
│     • Verify and resume                                                         │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 12.2 High Availability

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          HIGH AVAILABILITY                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FAILURE SCENARIOS                                                              │
│  ─────────────────                                                              │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  Scenario              │ Detection    │ Recovery        │ RTO        │    │
│  │  ────────────────────────────────────────────────────────────────────  │    │
│  │  API instance fails    │ Health check │ Auto-replace    │ 30 seconds │    │
│  │  Worker fails          │ Heartbeat    │ Auto-replace    │ 1 minute   │    │
│  │  Database primary fails│ Streaming    │ Promote replica │ 5 minutes  │    │
│  │  Redis fails           │ Sentinel     │ Failover        │ 30 seconds │    │
│  │  Region outage         │ External mon │ Manual failover │ 1 hour     │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  PIPELINE RESILIENCE                                                            │
│  ───────────────────                                                            │
│  • Checkpoints after every agent                                                │
│  • Resume from last checkpoint on failure                                       │
│  • Idempotent agent execution                                                   │
│  • Distributed lock for pipeline execution                                      │
│                                                                                  │
│  DATA DURABILITY                                                                │
│  ───────────────                                                                │
│  • PostgreSQL: Synchronous replication (if configured)                          │
│  • MinIO: Erasure coding                                                        │
│  • All writes acknowledged after persistence                                    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# 13. Architecture Decision Records

## ADR-001: LangGraph for Orchestration

**Status:** Accepted  
**Date:** 2026-01-15

**Context:**  
Need workflow orchestration for multi-agent pipeline with complex routing, checkpointing, and parallel execution.

**Decision:**  
Use LangGraph StateGraph for orchestration.

**Rationale:**
- Native support for stateful agent workflows
- Built-in checkpointing with PostgreSQL
- Conditional routing capabilities
- Fan-out/fan-in for parallel execution
- LangSmith integration for observability

**Consequences:**
- Learning curve for team
- Tied to LangChain ecosystem
- Limited to Python runtime

---

## ADR-002: PostgreSQL for State Storage

**Status:** Accepted  
**Date:** 2026-01-15

**Context:**  
Need reliable, queryable storage for pipeline state and checkpoints.

**Decision:**  
Use PostgreSQL with JSONB for state and pgvector for embeddings.

**Rationale:**
- ACID compliance for state integrity
- JSONB for flexible schema
- pgvector eliminates separate vector DB
- Mature ecosystem and tooling
- LangGraph native checkpointer support

**Consequences:**
- Single database for multiple concerns
- May need to scale vertically
- JSONB queries can be complex

---

## ADR-003: Claude as Primary LLM

**Status:** Accepted  
**Date:** 2026-01-15

**Context:**  
Need high-quality LLM for medical content generation.

**Decision:**  
Use Anthropic Claude (claude-3-5-sonnet) as primary LLM.

**Rationale:**
- Strong performance on medical/scientific content
- Large context window (200K tokens)
- Reliable API with good rate limits
- Constitutional AI for safety

**Consequences:**
- Single vendor dependency
- Cost at scale (~$15/grant)
- Need fallback strategy

---

## ADR-004: LibreChat for User Interface

**Status:** Accepted  
**Date:** 2026-01-20

**Context:**  
Need user interface for intake forms and pipeline monitoring.

**Decision:**  
Use LibreChat with custom plugins.

**Rationale:**
- Open source, customizable
- Chat-based interface familiar to users
- Plugin architecture for extensions
- Active development community

**Consequences:**
- Custom development for intake forms
- May need significant customization
- Self-hosted maintenance burden

---

## ADR-005: Two-Pass Prose Quality

**Status:** Accepted  
**Date:** 2026-01-20

**Context:**  
Ensure writing quality throughout pipeline, not just at end.

**Decision:**  
Run Prose Quality Agent twice: after Needs Assessment and after Grant Assembly.

**Rationale:**
- Catch issues early (before downstream agents use content)
- Different scope per pass (single doc vs. full package)
- Reduce rework cycles
- Gate progression on quality

**Consequences:**
- Longer pipeline execution
- Potential retry loops
- Need clear pass/fail criteria

---

*Document Version: 1.0*  
*Last Updated: January 31, 2026*  
*Classification: Technical Reference*
