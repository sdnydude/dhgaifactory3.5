# Findings: /ship Workflow Research

**Date:** 2026-03-13

---

## 1. What Works in Existing Skills

### From superpowers:brainstorming
- One question at a time prevents overwhelm
- 2-3 approaches with recommendation forces real thinking
- Scope check catches multi-system projects early
- HARD GATE: no implementation until design approved

### From superpowers:writing-plans
- Bite-sized 2-5 min tasks make progress visible
- Test → implement → verify → commit cycle per task
- Exact file paths eliminate ambiguity
- DRY, YAGNI principles enforced

### From superpowers:executing-plans
- Follow plan steps exactly (don't improvise)
- Stop when blocked (don't guess)
- Never start on main/master without consent

### From superpowers:dispatching-parallel-agents
- Agent prompt structure: scope, goal, constraints, expected output
- 3+ independent tasks = dispatch in parallel
- No shared state between agents

### From superpowers:verification-before-completion
- "NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE"
- Red flags: "should", "probably", "seems to" without proof
- Fresh command output required, not cached results

### From feature-dev
- Clarifying questions AFTER codebase exploration (not before)
- 3-angle code review (simplicity, correctness, conventions)
- 2-3 architecture approaches with comparison table

### From workflow-review
- Config skepticism: "risky until proven safe"
- Multi-agent review (security, performance, config)
- Real-world outage pattern detection

---

## 2. What Breaks When Chained

1. **Triple codebase exploration** — brainstorming, writing-plans, and feature-dev all independently explore
2. **Three review loops** — spec review, plan review, code review (too heavy)
3. **Context loss at handoffs** — each skill starts fresh
4. **No verification gate** — verification is a pattern, not a phase
5. **No DHG awareness** — none know about Docker networks, port conflicts, CLAUDE.md

---

## 3. Gap Analysis

| Gap | Impact | Solution |
|---|---|---|
| No single-pass exploration | 3x wasted time | Dedicated Phase 2 |
| No risk assessment per task | Dangerous tasks treated same as safe | Risk flags in Phase 3 |
| No live progress feedback | User sees silence during builds | Updates in Phase 4 |
| No auto-test per task | Regressions found late | Auto-test in Phase 4 |
| No explicit verification gate | "Done" claimed without proof | Phase 5 |
| No DHG-specific review | Docker/port/network issues missed | Custom checks in Phase 6 |
| No session capture | Workflow knowledge lost | Auto-log in Phase 7 |

---

## 4. Custom Additions (my own, not from any skill)

| Addition | Rationale |
|---|---|
| **Feasibility check** against C1-C10 known issues | Don't build on broken foundations |
| **Explore phase** (dedicated, runs once) | Codebase exploration done once, carried forward |
| **Risk flags + blast radius** per task | Surfaces danger early, makes review faster |
| **Live progress ("Task 3/7...")** | User sees progress, not silence |
| **Auto-test after each task** | Catch regressions immediately |
| **Verify phase** (explicit gate) | Forces proof before "done" |
| **DHG-specific checks** (Docker, ports, CLAUDE.md) | Platform-aware review |
| **Fix-and-re-verify loop** | Don't just report issues — fix them |
| **Session log auto-capture** | Feeds workflow into knowledge base |
