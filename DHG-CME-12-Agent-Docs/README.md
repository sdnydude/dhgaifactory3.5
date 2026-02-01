# DHG CME Grant Multi-Agent System
## Documentation Package for Antigravity Implementation

**Version:** 1.0  
**Created:** January 2025  
**Purpose:** Complete documentation for implementing a 12-agent pipeline that generates pharmaceutical-grade CME grant request documentation

---

## System Overview

This system processes CME grant intake forms through 12 specialized AI agents orchestrated via LangGraph, producing complete grant packages that read as professionally written by experienced medical writers.

### Pipeline Architecture

```
INTAKE FORM
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                        │
│           (Workflow Control, State Management)               │
└─────────────────────────────────────────────────────────────┘
     │
     ├──────────────────┬──────────────────┐
     ▼                  ▼                  ▼
┌─────────┐      ┌─────────────┐    ┌──────────┐
│RESEARCH │      │  CLINICAL   │    │ AUDIENCE │
│  AGENT  │      │   AGENT     │    │  AGENT   │
└─────────┘      └─────────────┘    └──────────┘
     │                  │                  │
     └──────────────────┼──────────────────┘
                        ▼
              ┌─────────────────┐
              │  GAP ANALYSIS   │
              │     AGENT       │
              └─────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │NEEDS ASSESSMENT │
              │(Cold Open+Prose)│
              └─────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  PROSE QUALITY  │
              │   (Pass 1)      │
              └─────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │   LEARNING      │
              │  OBJECTIVES     │
              └─────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌───────────┐   ┌───────────┐   ┌───────────┐
│CURRICULUM │   │ PROTOCOL  │   │ MARKETING │
│  DESIGN   │   │   AGENT   │   │   PLAN    │
└───────────┘   └───────────┘   └───────────┘
        │               │               │
        └───────────────┼───────────────┘
                        ▼
              ┌─────────────────┐
              │  GRANT WRITER   │
              │     AGENT       │
              └─────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  PROSE QUALITY  │
              │   (Pass 2)      │
              └─────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │   COMPLIANCE    │
              │     REVIEW      │
              └─────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  HUMAN REVIEW   │
              │      GATE       │
              └─────────────────┘
                        │
                        ▼
                 FINAL OUTPUT
```

---

## The 12 Agents

| # | Agent | Purpose | Complexity | Key Output |
|---|-------|---------|------------|------------|
| 1 | Orchestrator | Workflow control, state management, QA gates | High | State updates, routing decisions |
| 2 | Research | Literature review, epidemiology, market intel | Medium | Research report (30+ sources) |
| 3 | Clinical Practice | Standard of care, practice patterns, barriers | Medium | Clinical analysis |
| 4 | Gap Analysis | Synthesize gaps, quantify, prioritize | Medium | 5+ evidence-based gaps |
| 5 | Needs Assessment | Cold open + narrative document | High | 3,100+ word narrative |
| 6 | Learning Objectives | Moore's Framework objectives | Medium | 6+ measurable objectives |
| 7 | Curriculum Design | Educational design + innovation section | Medium | Complete curriculum spec |
| 8 | Research Protocol | IRB-ready outcomes research protocol | Medium | Full research protocol |
| 9 | Marketing Plan | Audience generation strategy + budget | Medium | Channel strategy + timeline |
| 10 | Grant Writer | Assemble complete grant package | High | All grant documents |
| 11 | Prose Quality | De-AI-ification, style enforcement | Medium | Quality report + revisions |
| 12 | Compliance Review | ACCME standards verification | Low | Compliance certification |

---

## Key Concepts

### Cold Opens
Every Needs Assessment opens with a 50-100 word narrative hook (60 Minutes style) that humanizes the clinical gap before any statistics appear. The character introduced must reappear throughout all documents as a narrative thread.

### Moore's Expanded Outcomes Framework
Primary taxonomy for learning objectives (replaces Bloom's). Seven levels from Participation (1) through Community Health (7), with most CME targeting Level 4 (Competence) or Level 5 (Performance).

### De-AI-ification
The Prose Quality Agent eliminates AI writing patterns: em dashes, "delve into," "furthermore/moreover," "it's important to note," colons in titles, and other tells. Target is 80%+ flowing prose with minimum 4-sentence paragraphs.

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Grant approval rate | >60% | Funded/submitted |
| Time to draft | <5 days | Intake to first draft |
| Prose quality score | >8/10 | Prose Quality Agent |
| Human revision rate | <20% | Drafts requiring manual rewrite |
| Compliance pass rate | >95% | First-pass compliance approval |

---

## Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Orchestration | LangGraph StateGraph | Explicit control flow, battle-tested |
| Observability | LangSmith | Production-ready tracing, evaluation |
| Checkpointing | PostgresSaver | Production persistence |
| Agent Pattern | create_agent() with tools | Standard, reliable pattern |
| Evaluation | LLM-as-judge (offline first) | Stable, well-documented |

---

## Folder Structure

```
DHG-CME-12-Agent-Docs/
├── README.md                          # This file
├── shared-resources/
│   ├── writing-style-guide.md         # Prose requirements, banned patterns
│   ├── moores-expanded-framework.md   # Outcomes taxonomy
│   ├── cold-open-framework.md         # Narrative hook specifications
│   └── audience-context.md            # Grant reviewer psychology
├── agents/
│   ├── 01-orchestrator.md
│   ├── 02-research.md
│   ├── 03-clinical-practice.md
│   ├── 04-gap-analysis.md
│   ├── 05-needs-assessment.md
│   ├── 06-learning-objectives.md
│   ├── 07-curriculum-design.md
│   ├── 08-research-protocol.md
│   ├── 09-marketing-plan.md
│   ├── 10-grant-writer.md
│   ├── 11-prose-quality.md
│   └── 12-compliance-review.md
├── technical/
│   ├── state-schema.py                # LangGraph state definition
│   ├── graph-definition.py            # Workflow graph code
│   └── intake-form-schema.yaml        # Complete intake form spec
└── implementation-guide.md            # Phased implementation plan
```

---

## Quick Start for Implementation

1. **Read shared resources first** - These are referenced by multiple agents
2. **Implement Needs Assessment Agent first** - Highest complexity, proves the pattern
3. **Add Prose Quality Agent second** - Validates output quality
4. **Build remaining agents** - Follow dependency order in architecture
5. **Wire up LangGraph orchestration** - Use state-schema.py and graph-definition.py
6. **Add LangSmith tracing** - For observability and debugging
7. **Create evaluation datasets** - For quality assurance

---

## Document Conventions

- Word count minimums are STRICTLY ENFORCED
- Character counts for summaries must be EXACT (with spaces)
- All prose sections must achieve 80%+ narrative density
- Cold open character must appear in 4+ sections minimum
- Moore's Framework is PRIMARY; Bloom's is secondary only

---

*For questions or clarifications, refer to the source specification or contact the DHG AI development team.*
