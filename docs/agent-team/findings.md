# 12 CME Agent - Findings

## Source Documentation

**Location:** `/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/DHG-CME-12-Agent-Docs/`

### Agent Specs (all 12 complete)
```
agents/
├── 01-orchestrator.md      (12KB)
├── 02-research.md          (13KB)
├── 03-clinical-practice.md (17KB)
├── 04-gap-analysis.md      (18KB)
├── 05-needs-assessment.md  (21KB) ← START HERE
├── 06-learning-objectives.md (16KB)
├── 07-curriculum-design.md (19KB)
├── 08-research-protocol.md (18KB)
├── 09-marketing-plan.md    (18KB)
├── 10-grant-writer.md      (18KB)
├── 11-prose-quality.md     (17KB)
├── 12-compliance-review.md (21KB)
```

### Shared Resources
- `writing-style-guide.md` - Prose requirements, banned AI patterns
- `moores-expanded-framework.md` - Outcomes taxonomy
- `cold-open-framework.md` - Narrative hook specs
- `audience-context.md` - Grant reviewer psychology

### Technical
- `state-schema.py` - LangGraph state definition
- `graph-definition.py` - Workflow graph code
- `intake-form-schema.yaml` - Complete intake spec

---

## Key Concepts

### Cold Opens
50-100 word narrative hook (60 Minutes style). Character introduced must reappear throughout documents.

### Moore's Expanded Outcomes Framework
Primary taxonomy (not Bloom's). 7 levels from Participation (1) to Community Health (7). CME targets Level 4-5.

### De-AI-ification
Eliminate: em dashes, "delve into", "furthermore/moreover", "it's important to note", colons in titles.
Target: 80%+ flowing prose, minimum 4-sentence paragraphs.

---

## Current Agents (Docker)

### Running
| Agent | Container | Port |
|-------|-----------|------|
| SAGE (Medical-LLM) | dhg-medical-llm | 8002 |
| HAWK (Competitor-Intel) | dhg-competitor-intel | 8006 |
| LENS (Visuals) | dhg-visuals-media | 8008 |
| SCOUT (Session-Logger) | dhg-session-logger | 8009 |
| BRAND (Logo-Maker) | dhg-logo-maker | 8012 |
| Orchestrator | dhg-aifactory-orchestrator | 8000 |

### Stopped (Disabled Feb 3)
- DOC (Research) - 8003
- PROF (Curriculum) - 8004
- CHART (Outcomes) - 8005
- ACE (QA-Compliance) - 8007

---

## Technology Stack (from docs)

| Component | Choice |
|-----------|--------|
| Orchestration | LangGraph StateGraph |
| Observability | LangSmith |
| Checkpointing | PostgresSaver |
| Agent Pattern | create_agent() with tools |
| Evaluation | LLM-as-judge (offline first) |

---

## Implementation Order (from README)

1. **Needs Assessment Agent (#5)** - Highest complexity, proves pattern
2. **Prose Quality Agent (#11)** - Validates output quality
3. **Remaining agents** - Follow dependency order
4. **LangGraph orchestration** - Wire up state-schema.py
5. **LangSmith tracing** - Add observability
6. **Evaluation datasets** - For QA
