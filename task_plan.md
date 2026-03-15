# Task Plan: Custom `/ship` Workflow

**Date:** 2026-03-13
**Goal:** Build a single cohesive `/ship` command that takes a feature from idea to merged PR — cherry-picking the best patterns from superpowers, feature-dev, and review tools while eliminating redundancy. Add custom steps that fill gaps in the existing skills.

---

## Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Single command file, not skill chaining | Eliminates redundant codebase exploration, carries context end-to-end |
| D2 | 7 phases (not 5) — added Explore and Verify | Explore separates codebase understanding from brainstorming; Verify prevents false "done" claims |
| D3 | Parallel agents where possible | Codebase exploration + architecture options can run in parallel |
| D4 | Hard gates at Phase 2→3 and 4→5 | No building without approved plan; no shipping without passing review |
| D5 | Auto-log to session-logger on completion | Captures the full workflow for knowledge base |
| D6 | Stack-aware (DHG conventions baked in) | Knows LangGraph, FastAPI, Docker, PostgreSQL patterns |

---

## The 7 Phases

### Phase 1: Brainstorm
**Source:** superpowers:brainstorming (core patterns)
**What we keep:**
- One question at a time, multiple choice preferred
- 2-3 approaches with tradeoffs and recommendation
- Scope check (flag multi-subsystem projects immediately)
**What we drop:**
- Spec document writing (overkill for most features)
- Spec review loop (5 iterations is too heavy)
**What we add:**
- Quick feasibility check against known critical issues (C1-C10 from CLAUDE.md)

### Phase 2: Explore
**Source:** feature-dev:code-explorer (parallel agents)
**This is new — separated from brainstorming to avoid redundant exploration later.**
- Launch 2-3 explorer agents in parallel targeting different parts of the codebase
- Map relevant files, existing patterns, dependencies
- Identify what exists that can be reused
- Output: file map + pattern inventory
**Why added:** Every existing skill does its own exploration. Do it once, carry it forward.

### Phase 3: Plan
**Source:** superpowers:writing-plans (bite-sized tasks)
**What we keep:**
- Bite-sized tasks (2-5 minutes each)
- Exact file paths for every task
- Test → implement → verify → commit cycle per task
- DRY, YAGNI principles
**What we drop:**
- Chunk-based plan review loop (too slow for most features)
- Full code in plan (descriptions + file paths is enough)
**What we add:**
- Risk flags per task (touches shared state? changes config? modifies DB schema?)
- Estimated blast radius (local, service, cross-service)

**HARD GATE: User must approve plan before Phase 4.**

### Phase 4: Build
**Source:** superpowers:executing-plans + dispatching-parallel-agents
**What we keep:**
- Follow plan steps exactly
- Stop when blocked (don't guess)
- Parallel agents for independent tasks
- Commit after each completed task
**What we drop:**
- TodoWrite overhead (progress tracked in conversation)
**What we add:**
- Live progress updates ("Task 3/7: adding migration... done")
- Auto-run tests after each task that touches testable code

### Phase 5: Verify
**Source:** superpowers:verification-before-completion
**This is new as an explicit phase — not just a pattern.**
- Run full test suite fresh
- Check every claim against actual output
- Verify no regressions (if tests existed before)
- Health check affected services (curl endpoints, docker ps)
- NO completion claims without evidence
**Why added:** The #1 failure mode is claiming "done" without proof. Making it a phase forces it.

### Phase 6: Review
**Source:** workflow-review + pr-review-toolkit patterns
**What we keep:**
- Multi-agent review (security, performance, config safety)
- Configuration skepticism ("risky until proven safe")
- Severity levels (critical blocks, important blocks before merge, minor noted)
**What we drop:**
- Separate invocation of 6 different review agents (too slow)
**What we add:**
- DHG-specific checks: Docker network isolation, port conflicts, CLAUDE.md compliance
- Fix-and-re-verify loop (don't just report issues — fix them)

**HARD GATE: Critical issues must be resolved before Phase 7.**

### Phase 7: Ship
**Source:** commit-commands:commit-push-pr
**What we keep:**
- Atomic: branch → commit → push → PR in one shot
- Auto-generated PR description with summary + test plan
**What we add:**
- Auto-submit session log to session-logger API
- PR description includes phases completed and key decisions made

---

## Custom Additions (not from any existing skill)

| Addition | Phase | Why |
|---|---|---|
| **Feasibility check** against known issues (C1-C10) | 1 | Prevents building on broken foundations |
| **Dedicated Explore phase** | 2 | Do codebase exploration once, not 3 times |
| **Risk flags + blast radius** per task | 3 | Makes review faster, surfaces danger early |
| **Live progress updates** | 4 | User sees "Task 3/7" not silence |
| **Auto-run tests per task** | 4 | Catch regressions immediately, not at end |
| **Explicit Verify phase** | 5 | Forces proof before claiming done |
| **DHG-specific checks** | 6 | Docker networks, port conflicts, CLAUDE.md |
| **Fix-and-re-verify loop** | 6 | Don't just report issues — resolve them |
| **Session log capture** | 7 | Auto-logs workflow to knowledge base |

---

## Build Order

### Step 1: Write the `/ship` command file
- File: `.claude/commands/ship.md`
- Contains all 7 phases with full instructions
- ~300-400 lines

### Step 2: Write the explorer agent prompt template
- Reusable prompt for Phase 2 explorer agents
- File: `.claude/commands/ship-agents/explore.md`

### Step 3: Write the reviewer agent prompt template
- DHG-specific review checklist
- File: `.claude/commands/ship-agents/review.md`

### Step 4: Test with a real feature
- Pick a small real task and run `/ship` on it
- Verify each phase works, gates hold, context carries forward

### Step 5: Iterate based on test run

---

## Verification Plan

1. Run `/ship add a /sessions/stats endpoint to session-logger`
2. Confirm: brainstorm asks questions, doesn't jump to code
3. Confirm: explore runs agents, produces file map
4. Confirm: plan has bite-sized tasks with file paths
5. Confirm: build follows plan, commits per task
6. Confirm: verify runs tests, checks endpoints
7. Confirm: review catches issues, fix loop works
8. Confirm: PR created with full description
9. Confirm: session logged to session-logger API
