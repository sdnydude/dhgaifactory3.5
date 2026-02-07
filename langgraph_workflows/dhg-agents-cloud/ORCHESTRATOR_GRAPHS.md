# Recipe-Based Orchestrator - Graph Diagrams

These Mermaid diagrams visualize the CME Grant Pipeline workflows.

## Needs Package Graph

This recipe handles: Research → Gap Analysis → Learning Objectives → Needs Assessment → Prose QA → Human Review

```mermaid
graph TD;
    __start__(["__start__"]):::first
    early_research(early_research)
    gap_analysis(gap_analysis)
    learning_objectives(learning_objectives)
    needs_assessment(needs_assessment)
    prose_quality(prose_quality)
    human_review(human_review)
    failed(failed)
    __end__(["__end__"]):::last
    
    __start__ --> early_research;
    early_research --> gap_analysis;
    gap_analysis --> learning_objectives;
    learning_objectives --> needs_assessment;
    needs_assessment --> prose_quality;
    prose_quality -. "human_intervention" .-> failed;
    prose_quality -. "continue" .-> human_review;
    prose_quality -. "retry_needs" .-> needs_assessment;
    failed --> __end__;
    human_review --> __end__;
    
    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```

**Key Features:**
- `early_research` runs Research + Clinical agents **in parallel**
- Quality gate after Needs Assessment with retry logic
- Max 3 retries before human intervention

---

## Grant Package Graph (Full Pipeline)

This is the complete 11-agent pipeline with all quality gates.

```mermaid
graph TD;
    __start__(["__start__"]):::first
    early_research(early_research)
    gap_analysis(gap_analysis)
    learning_objectives(learning_objectives)
    needs_assessment(needs_assessment)
    prose_quality_1(prose_quality_1)
    design_phase(design_phase)
    grant_writer(grant_writer)
    prose_quality_2(prose_quality_2)
    compliance(compliance)
    human_review(human_review)
    complete(complete)
    failed(failed)
    __end__(["__end__"]):::last
    
    __start__ --> early_research;
    early_research --> gap_analysis;
    gap_analysis --> learning_objectives;
    learning_objectives --> needs_assessment;
    needs_assessment --> prose_quality_1;
    
    prose_quality_1 -. "continue" .-> design_phase;
    prose_quality_1 -. "human_intervention" .-> failed;
    prose_quality_1 -. "retry_needs" .-> needs_assessment;
    
    design_phase --> grant_writer;
    grant_writer --> prose_quality_2;
    
    prose_quality_2 -. "continue" .-> compliance;
    prose_quality_2 -. "human_intervention" .-> failed;
    prose_quality_2 -. "retry_grant" .-> grant_writer;
    
    compliance -. "revision_required" .-> grant_writer;
    compliance -. "continue" .-> human_review;
    
    human_review --> complete;
    complete --> __end__;
    failed --> __end__;
    
    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```

**Key Features:**
- `early_research` runs Research + Clinical agents **in parallel**
- `design_phase` runs Curriculum + Protocol + Marketing **in parallel**
- Two prose quality gates with retry logic
- Compliance gate with revision loop
- Human review as final gate

---

## Pipeline Flow Summary

```
INTAKE
    ↓
early_research (Research + Clinical PARALLEL)
    ↓
gap_analysis
    ↓
learning_objectives
    ↓
needs_assessment ←──────┐
    ↓                   │ retry
prose_quality_1 ────────┘
    ↓ pass
design_phase (Curriculum + Protocol + Marketing PARALLEL)
    ↓
grant_writer ←──────────┐
    ↓                   │ retry
prose_quality_2 ────────┘
    ↓ pass
compliance
    ↓ pass
human_review
    ↓ approved
complete
```

---

## Decision #10: Recipe-Based Orchestrator

**Confirmed:** 2026-02-04

**Key Implementation Details:**
- 4 composable recipes: needs_graph, curriculum_graph, grant_graph, full_graph
- Parallel execution using asyncio.gather for fan-out/fan-in
- PostgresSaver checkpointing (optional, with fallback)
- LangSmith tracing on all agent wrapper nodes
- Comprehensive error handling with retry matrix
- Human review routing for approval/revision/reject flows
