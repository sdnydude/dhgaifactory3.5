---
description: AI-assisted planning and tracking for long, complex multi-phase builds
---

# Project Planning Workflow

// turbo-all

> **Use this workflow when starting any complex build that will span multiple sessions or phases.**

---

## When to Use

✅ Projects with 5+ phases or 2+ weeks timeline  
✅ Multi-component builds (frontend + backend + database)  
✅ Agent systems with multiple modules  
✅ Any work requiring coordination across sessions  

❌ Simple bug fixes or single-file changes  
❌ Quick Q&A or research tasks  

---

## Phase 0: Initialize Project

### 0.1 Create Artifact Directory

All planning files go in the Antigravity artifacts directory:
```
~/.gemini/antigravity/brain/<conversation-id>/
```

### 0.2 Create Core Planning Files

| File | Purpose | Template |
|------|---------|----------|
| `task.md` | Checklist of all work items | See below |
| `implementation_plan.md` | Detailed technical plan | User approval required |
| `decisions.md` | All user decisions tracked | Reference for consistency |
| `progress.md` | Session-by-session log | Context recovery |

### 0.3 Get User Approval

Before ANY implementation:
1. Create `implementation_plan.md` with full scope
2. Use `notify_user` with `BlockedOnUser: true`
3. Wait for explicit approval
4. Update `decisions.md` with outcomes

---

## Phase 1: Task Breakdown

### Task.md Format

```markdown
# Project Name

## Phase 1: [Phase Name]
- [ ] Task 1 <!-- id: 1 -->
- [ ] Task 2 <!-- id: 2 -->
    - [ ] Sub-task 2a <!-- id: 3 -->

## Phase 2: [Phase Name]
- [ ] Task 3 <!-- id: 4 -->

## Backlog
- [ ] Future consideration <!-- id: 99 -->
```

### Status Markers

| Marker | Meaning |
|--------|---------|
| `[ ]` | Not started |
| `[/]` | In progress |
| `[x]` | Complete |
| `[-]` | Blocked or deferred |

### ID Rules

- Every task has a unique `<!-- id: N -->` comment
- IDs are never reused, even after deletion
- Enables tracking across sessions

---

## Phase 2: Session Management

### Starting a New Session

1. **Read** `task.md` — What's pending?
2. **Read** `implementation_plan.md` — What's the approach?
3. **Read** `progress.md` — What happened last session?
4. **Update** `task_boundary` with current phase and status

### During Session

Every 5-10 tool calls:
1. Update `task.md` — Mark items `[/]` or `[x]`
2. Update `task_boundary` — New status/summary
3. If discoveries made → Update `progress.md`

### Ending a Session

Before `notify_user`:
1. Update `task.md` — All in-progress items marked
2. Update `progress.md` — Session summary
3. Note any blockers or decisions needed

---

## Phase 3: Decision Tracking

### Decisions.md Format

```markdown
# Project Decisions

## Architecture Decisions

| # | Decision | Options | Choice | Date | Rationale |
|---|----------|---------|--------|------|-----------|
| 1 | State Schema | Replace/Extend/Separate | **Replace** | 2026-02-01 | User confirmed |

## Open Questions

- [ ] Question 1? (Waiting for user input)
- [x] Question 2? → Answered: [answer]
```

### Decision Rules

1. **Never assume** — If uncertain, ask
2. **Log everything** — Even "obvious" choices
3. **Reference decisions** — When implementing, cite decision #

---

## Phase 4: Progress Logging

### Progress.md Format

```markdown
# Project Progress

## Session: 2026-02-01 08:00

### Work Done
- Created `CMEIntakeForm.tsx` (150 lines)
- Implemented form validation for sections A-C

### Discoveries
- LibreChat right panel uses `SidePanel` component
- Need to register custom panel in `panelConfig.ts`

### Blockers
- ❌ Missing Google Workspace API credentials

### Next Session
- Continue with sections D-J
- Resolve Google Workspace blocker
```

---

## Phase 5: Verification Checkpoints

### Per-Phase Verification

Before marking a phase complete:
1. [ ] All tasks in phase marked `[x]`
2. [ ] Code compiles/runs without errors
3. [ ] Tests pass (if applicable)
4. [ ] User notified of completion (if major phase)

### End-to-End Verification

At project completion:
1. [ ] All phases complete in `task.md`
2. [ ] `walkthrough.md` created with summary
3. [ ] User has approved final deliverable

---

## Debug Integration

When errors occur, invoke `/debug-protocol`:

1. **PAUSE** — Don't immediately fix
2. **LOG** — Record error in `progress.md`
3. **RESEARCH** — Check logs, recent changes
4. **PLAN** — Form hypothesis, get user approval
5. **FIX** — One attempt per hypothesis
6. **VERIFY** — Confirm fix worked

---

## File Templates

### Minimal task.md

```markdown
# [Project Name]

## Phase 1: Foundation
- [ ] Task 1 <!-- id: 1 -->
- [ ] Task 2 <!-- id: 2 -->

## Phase 2: Implementation
- [ ] Task 3 <!-- id: 3 -->
```

### Minimal decisions.md

```markdown
# Project Decisions

| # | Decision | Choice | Date |
|---|----------|--------|------|
| 1 | [Decision] | **[Choice]** | [Date] |

## Open Questions
- [ ] [Question]?
```

### Minimal progress.md

```markdown
# Project Progress

## Session: [Date]

### Work Done
- [Item]

### Next Session
- [Item]
```

---

## Quick Reference

| Action | Location |
|--------|----------|
| What's left to do? | `task.md` |
| How do I do it? | `implementation_plan.md` |
| What did we decide? | `decisions.md` |
| What happened before? | `progress.md` |
| Did it work? | `walkthrough.md` |

---

## Anti-Patterns

| ❌ Don't | ✅ Do Instead |
|----------|---------------|
| Start coding immediately | Create plan, get approval |
| Keep decisions in memory | Log to `decisions.md` |
| Skip session boundaries | Update `progress.md` |
| Mark multiple phases `[/]` | One phase in-progress at a time |
| Ignore errors | Log and invoke debug protocol |
