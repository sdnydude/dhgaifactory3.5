# 12 CME Agent - Decisions

## Architecture Decisions

| # | Decision | Options | Choice | Date | Rationale |
|---|----------|---------|--------|------|-----------|
| 1 | Agent UI Pattern | A: Side Panel, B: Project Workspace, C: Commands, D: Agents Page, E: Mentions | **B + C + E + D** | 2026-02-03 | User wants all except side panel (A) |
| 2 | Implementation Order | Various | **B → C → E → D** | 2026-02-03 | User specified |
| 3 | Disabled Agents | Delete vs Stop | **Stop (preserve containers)** | 2026-02-03 | User specified "disable, don't delete" |
| 4 | Scope Priority | Agents first vs UI first | **Agents first** | 2026-02-03 | User backlogged project system |
| 5 | Agent Source Docs | Create new vs Use existing | **DHG-CME-12-Agent-Docs** | 2026-02-03 | Complete specs already exist |
| 6 | Implementation Order | All at once vs Incremental | **Start with Needs Assessment (#5)** | 2026-02-03 | Per README: "Highest complexity, proves pattern" |

---

## Open Questions

- [x] What are the 12 agents? → Found in DHG-CME-12-Agent-Docs (Orchestrator, Research, Clinical Practice, Gap Analysis, Needs Assessment, Learning Objectives, Curriculum Design, Research Protocol, Marketing Plan, Grant Writer, Prose Quality, Compliance Review)
- [ ] Should agents have different access levels per user role?
- [ ] External intake: email, web form, API, all?
- [ ] Should projects be scoped to users or shared across team?

---

## Constraints

- Must use LangGraph StateGraph for orchestration
- Must use PostgresSaver for checkpointing
- Prose quality must achieve >8/10 score
- Target 80%+ flowing prose in all outputs
- Must eliminate AI writing patterns (de-AI-ification)
