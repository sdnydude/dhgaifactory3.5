# 12 CME Agent Implementation

**Goal:** Implement 12 specialized CME grant agents in LangGraph

**Status:** Planning

**Source Docs:** `/DHG-CME-12-Agent-Docs/`

---

## Phase 1: Core Agent Implementation

### 1.1 Needs Assessment Agent (#5) - START HERE
- [ ] Read spec from `DHG-CME-12-Agent-Docs/agents/05-needs-assessment.md` <!-- id: 100 -->
- [ ] Create agent using `create_agent()` pattern <!-- id: 101 -->
- [ ] Implement cold open framework from shared resources <!-- id: 102 -->
- [ ] Add 3,100+ word output validation <!-- id: 103 -->
- [ ] Add Docker service definition <!-- id: 104 -->
- [ ] Test with sample intake <!-- id: 105 -->

### 1.2 Prose Quality Agent (#11) - Second
- [ ] Read spec from `DHG-CME-12-Agent-Docs/agents/11-prose-quality.md` <!-- id: 106 -->
- [ ] Implement de-AI-ification patterns <!-- id: 107 -->
- [ ] Add banned word list from `writing-style-guide.md` <!-- id: 108 -->
- [ ] Test prose quality scoring <!-- id: 109 -->

### 1.3 Orchestrator Agent (#1)
- [ ] Read spec from `DHG-CME-12-Agent-Docs/agents/01-orchestrator.md` <!-- id: 110 -->
- [ ] Implement LangGraph StateGraph <!-- id: 111 -->
- [ ] Wire up PostgresSaver for checkpointing <!-- id: 112 -->
- [ ] Add QA gates between phases <!-- id: 113 -->

---

## Phase 2: Research & Analysis Agents

### 2.1 Research Agent (#2)
- [ ] Read spec from `agents/02-research.md` <!-- id: 114 -->
- [ ] Implement PubMed/CDC/CMS queries <!-- id: 115 -->
- [ ] Add 30+ source requirement validation <!-- id: 116 -->

### 2.2 Clinical Practice Agent (#3)
- [ ] Read spec from `agents/03-clinical-practice.md` <!-- id: 117 -->
- [ ] Implement barrier identification <!-- id: 118 -->

### 2.3 Gap Analysis Agent (#4)
- [ ] Read spec from `agents/04-gap-analysis.md` <!-- id: 119 -->
- [ ] Implement 5+ evidence-based gaps <!-- id: 120 -->

---

## Phase 3: Curriculum & Planning Agents

### 3.1 Learning Objectives Agent (#6)
- [ ] Read spec from `agents/06-learning-objectives.md` <!-- id: 121 -->
- [ ] Implement Moore's Framework <!-- id: 122 -->

### 3.2 Curriculum Design Agent (#7)
- [ ] Read spec from `agents/07-curriculum-design.md` <!-- id: 123 -->

### 3.3 Research Protocol Agent (#8)
- [ ] Read spec from `agents/08-research-protocol.md` <!-- id: 124 -->

### 3.4 Marketing Plan Agent (#9)
- [ ] Read spec from `agents/09-marketing-plan.md` <!-- id: 125 -->

---

## Phase 4: Output & Quality Agents

### 4.1 Grant Writer Agent (#10)
- [ ] Read spec from `agents/10-grant-writer.md` <!-- id: 126 -->
- [ ] Assemble complete grant package <!-- id: 127 -->

### 4.2 Compliance Review Agent (#12)
- [ ] Read spec from `agents/12-compliance-review.md` <!-- id: 128 -->
- [ ] Implement ACCME verification <!-- id: 129 -->

---

## Phase 5: Integration & Testing

- [ ] Wire all 12 agents in LangGraph flow <!-- id: 130 -->
- [ ] Add LangSmith tracing <!-- id: 131 -->
- [ ] End-to-end test with sample intake <!-- id: 132 -->
- [ ] Validate prose quality score >8/10 <!-- id: 133 -->
- [ ] Validate compliance pass rate >95% <!-- id: 134 -->

---

## Backlog (Project System - Deferred)

- [-] Project Workspace UI <!-- id: 1-20 -->
- [-] Command Bar (/commands) <!-- id: 21-32 -->
- [-] Chat Mention (@agent) <!-- id: 33-42 -->
- [-] Agents Page <!-- id: 43-53 -->

---

## The 12 Agents

| # | Agent | Purpose | Key Output |
|---|-------|---------|------------|
| 1 | Orchestrator | Workflow control | Routing decisions |
| 2 | Research | Literature review | 30+ sources report |
| 3 | Clinical Practice | Barriers analysis | Clinical analysis |
| 4 | Gap Analysis | Prioritize gaps | 5+ evidence-based gaps |
| 5 | **Needs Assessment** | Cold open + narrative | 3,100+ word narrative |
| 6 | Learning Objectives | Moore's Framework | 6+ measurable objectives |
| 7 | Curriculum Design | Educational design | Curriculum spec |
| 8 | Research Protocol | IRB-ready protocol | Research protocol |
| 9 | Marketing Plan | Audience strategy | Channel + timeline |
| 10 | Grant Writer | Assemble package | All grant documents |
| 11 | **Prose Quality** | De-AI-ification | Quality report |
| 12 | Compliance Review | ACCME verification | Certification |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Grant approval rate | >60% |
| Time to draft | <5 days |
| Prose quality score | >8/10 |
| Human revision rate | <20% |
| Compliance pass rate | >95% |
