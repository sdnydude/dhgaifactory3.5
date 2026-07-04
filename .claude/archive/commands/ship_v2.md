# /ship — Full Feature Shipping Workflow

You are running an 8-phase workflow to take a feature from idea to merged PR. This is the DHG AI Factory's production shipping process. Every phase builds on the previous one and carries context forward — do NOT re-explore or re-ask what was already established.

The user may have provided a feature description: $ARGUMENTS

If no arguments were provided, ask: **"What are we shipping?"** and wait.

---

## Resume Check

Before starting Phase 1, check if `.claude/ship-state.md` exists and contains `status: in_progress` or `status: stopped`. If it does, read the file and ask:

**"A previous /ship run was in progress at Phase [N]: [feature description]. Resume or start fresh?"**

If resuming, load the state (approach, file map, plan, progress) and continue from the recorded phase. If starting fresh, version the old state file as `ship-state_v{N}.md` and begin Phase 0.

---

## Phase 0: Feedback Loop Briefing

**Goal:** Load correction patterns, deferred items, and decision history to inform the ship. This runs automatically before Phase 1 — no user input needed.

1. **Query corrections (7 days):**
   ```bash
   curl -s "http://10.0.0.251:8011/api/corrections/stats"
   ```
   If active repeat patterns exist (repeat_flag = true), note them: these are behaviors to actively avoid during this ship.

2. **Query deferred items:**
   ```bash
   curl -s "http://10.0.0.251:8011/api/deferred-items/stats"
   ```
   Note open count and stale candidates. Check if any deferred items relate to the feature being shipped.

3. **Query related deferred items by keyword:**
   ```bash
   curl -s -X POST "http://10.0.0.251:8011/api/deferred-items/search" \
     -H "Content-Type: application/json" \
     -d '{"query":"[feature keywords]","status":"open","limit":5}'
   ```
   Surface any open deferred items that relate to this feature — they may already describe work we're about to do.

4. **Query related decision logs:**
   ```bash
   curl -s -X POST "http://10.0.0.251:8011/api/decision-logs/search" \
     -H "Content-Type: application/json" \
     -d '{"query":"[feature keywords]","limit":5}'
   ```
   Surface prior architectural decisions that bear on this feature.

5. **Output briefing** (one block, not a conversation):
   ```
   === SHIP FEEDBACK BRIEFING ===
   Correction patterns: [top pattern] ([count]x in 7d) — [repeat flags if any]
   Deferred items: [open count] open, [stale count] stale — [related items if found]
   Related decisions: [titles of related decision logs if found]
   === END BRIEFING ===
   ```

6. **Proceed to Phase 1.** Do not pause for user input after Phase 0.

---

## Rules (non-negotiable)

These come from CLAUDE.md and .claude/rules/. The /ship workflow enforces them structurally:

- **Overhead IS the quality.** Standards, processes, rigor, and thorough planning are the product clients pay for. Never optimize for speed or convenience; always optimize for best outcome. Quality and accuracy are first priority. Fortune 500 execution.
- **PLANNING AND BUILDING ARE SEPARATE PHASES.** Do not write files, run commands, or generate code until the design/plan is fully worked through AND Stephen explicitly approves moving to implementation. Jumping to code before planning is complete produces half-finished work, abandoned sessions, and unnecessary refactors. When in doubt, keep planning. Phases 1-3 are PLANNING. Phase 4 is BUILDING. Never cross that boundary without explicit approval.
- **No placeholders, TODOs, or provisional logic.** Every file works on first deploy.
- **View files before editing.** Always.
- **Run verification after any change.** Show proof.
- **One fix per hypothesis.** If it fails, form a new hypothesis.
- **No silent refactors.** Every change has operational rationale.
- **No completion claims without fresh verification evidence.** Red flags: "should", "probably", "seems to".
- **Never commit secrets.** No .env values, no API keys, no passwords in any file.
- **LangGraph is the sole orchestration platform.** Do not build on legacy agents.
- **Version planning files before overwriting.**

---

## Phase 1: Brainstorm (Grounded Divergence)

**Goal:** Understand the problem, gather what the project already knows about it, diverge from accumulated knowledge, converge on an approach, and produce a spec.

**Philosophy:** Phase 1 diverges from *institutional memory* — the knowledge base, past decisions, corrections, park lists, and existing code patterns. Phase 2 diverges from *live codebase exploration*. Two complementary divergent-convergent cycles with different inputs.

### Load Context

1. Read CLAUDE.md to load full project context (architecture, known issues, tech stack).

2. **Feasibility check.** Read CLAUDE.md's "Known Issues" section (both Open and Resolved). Check if this feature conflicts with any open issues. If conflicts exist, flag them immediately: "This feature touches [issue]. Here's how we handle it: [approach]."

### Gather Institutional Knowledge

3. **Knowledge base query.** Query accumulated project knowledge for anything relevant to this feature.

   **Current (keyword search):** Hit the registry's KB search endpoint:
   ```bash
   curl -s "http://10.0.0.251:8011/api/v1/kb/search?q=[feature keywords]&limit=10"
   ```

   **Future (RAG — when medkb ingestor pipeline is live):** Replace the keyword search above with a semantic RAG query against medkb's `engineering` corpus:
   ```bash
   curl -s -X POST "http://10.0.0.251:8015/v1/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "[feature description]", "corpus": "engineering", "strategy": "hybrid", "top_k": 10}'
   ```
   Semantic retrieval finds meaning matches, not just keyword matches — "add async job queue" will surface the export pipeline ship sessions even when exact words don't overlap.

   Either way, surface anything relevant:
   - "We shipped something similar in session #N — here's what we learned"
   - "A correction was logged about this pattern — don't repeat it"
   - "This was parked in session #N — exploration findings already exist"
   - "A deferred item from session #N is directly related"

   If the endpoint is unavailable, note it and proceed — this input is valuable but not blocking.

4. **Quick CodeGraph scan.** Run `codegraph_search` (main-session safe) on key terms from the feature description. Not a deep explore — just "what symbols and files exist near this problem?" This grounds the approach proposals in actual code, not abstract architecture.

5. **Prior art from docs-site.** Check if `docs-site/projects/dhg-ai-factory/` has existing pages covering the area this feature touches. If there's an architecture page, API reference, or ship log entry for the affected service, read it. Documentation captures design decisions that may not be in the code.

### Divergent Thinking (with lenses)

6. **Structured divergence.** Before converging on approaches, explore through these specific lenses:
   - **Composition:** What if we composed existing pieces instead of building new? What services, utilities, or patterns found in steps 3-5 could be assembled differently?
   - **Adjacent problem:** What if the real problem is adjacent to what was stated? Would solving a neighboring problem also solve this one?
   - **Extension:** What existing service or agent could be extended rather than building net-new?
   - **Lessons learned:** What do past corrections, park list items, and deferred items tell us to avoid or pursue?
   - **Simplification:** What if this needs 50% less code than we think? What's the simplest version that delivers the value?

   Not every lens will produce useful output. Use the ones that generate genuine alternatives. Skip lenses that produce forced answers.

7. **Ask clarifying questions.** One at a time. Multiple choice where possible. Do not ask more than 3 questions total — use judgment for the rest.

### Converge

8. **Propose 2-3 approaches** with tradeoffs. Each approach must reference specific code, past decisions, or knowledge base findings — no abstract proposals. Include:
   - What each approach changes (with file paths or service names)
   - What existing code/patterns it builds on (from steps 3-5)
   - Risk level (low / medium / high)
   - Which known issues it interacts with
   - What past corrections or decisions inform this choice
   - Your recommendation and why

9. **Advisor review (mandatory).** Before presenting approaches to Stephen, dispatch an independent advisor agent. The advisor receives: the feature description, the KB findings, the CodeGraph scan results, the divergent lens output, and the 2-3 proposed approaches. The advisor's brief:
   - Challenge the approaches — what was missed, what's underestimated, what alternative wasn't considered?
   - Evaluate whether KB findings (corrections, past decisions, park list items) were properly incorporated or ignored
   - Assess whether the recommended approach is genuinely the strongest, or whether the recommendation is defaulting to the most obvious option
   - Flag any concerns as "advisor notes"

   Incorporate the advisor's feedback into the approaches. If the advisor identified a genuinely better alternative or a critical gap, update the approaches before presenting to Stephen. Present the advisor's key challenges alongside the approaches — Stephen sees both the recommendation and the independent pushback.

10. Get user approval on the approach. If the user says "you decide" or "whatever you think", state your recommendation explicitly and confirm: "Going with [approach]. Correct?"

11. **Complexity check.** Flag the feature as **complex** if any of these are true:
    - Crosses 3+ services
    - Touches database schema
    - Will likely produce >5 tasks
    If complex, the spec (step 12) must be detailed. If simple, a light spec is sufficient.

12. **Write a spec.**
    - **Light spec (simple features):** 3-5 bullet points covering what it does, acceptance criteria, and edge cases.
    - **Detailed spec (complex features):** What it does, what it doesn't do, acceptance criteria, edge cases, affected services, data flow, error scenarios.

13. **Spec review.** Iterate on the spec with Stephen. Up to 5 iterations until the spec accurately reflects intent. Do not rush past this — the spec is the contract for everything that follows.

14. **Explore scope recommendation.** Based on the complexity check and the nature of the feature, recommend an exploration scope for Phase 2:
    - **Full divergent explore** (default for complex features, or when the problem space is ambiguous): 3 parallel agents with divergent discovery prompts. This is where cross-pollination, assumption challenges, and unexpected connections surface. Recommend this unless there's a clear reason not to.
    - **Targeted read** (only when the feature is a well-understood change to 1-2 known files with no ambiguity): Skip the full explore, do a focused read of the specific files in Phase 3 planning.

    Present the recommendation with reasoning and **pause for user decision.** Do not assume.

**Output:** Chosen approach + approved spec + explore scope decision + KB findings summary.

Write initial `.claude/ship-state.md`:
```
status: in_progress
phase: 1
feature: [description]
approach: [chosen approach]
complexity: [simple/complex]
explore_scope: [full/targeted]
kb_findings: [related ship sessions, corrections, park list items found]
codegraph_scan: [key symbols/files identified near the problem]
spec: [approved spec content]
```

> **Phase 1 complete. Continue to Phase 2 (Explore)?**

---

## Phase 2: Explore (Divergent Discovery)

**Goal:** Discover what the codebase knows that we haven't connected to this problem yet. This phase produces *thinking*, not inventory. Every later phase uses these findings — no re-exploration.

**Philosophy:** Divergent-convergent exploration is the core of this phase. The agents are structured to surface non-obvious connections, challenge assumptions, and reveal opportunities — not just catalog files. The file map is a byproduct, not the point.

If Phase 1 set `explore_scope: targeted`, skip the 3-agent launch and do a focused read of the specific files identified in the spec. Proceed to Phase 3.

### Divergent Discovery (Full Explore)

1. **Launch 3 explorer agents in parallel** using the Agent tool (subagent_type: Explore). Each agent receives: the feature description, the approved spec, the chosen approach from Phase 1, and any relevant KB/RAG findings from Phase 1 step 3 (so agents start informed, not cold). Each agent is driven by a question, not a task:

   **Agent 1 — Analogous Solutions:** "How has this codebase solved analogous problems before?" Find patterns, abstractions, and prior design decisions that bear on this feature — even in unrelated subsystems. Explicitly search for **prior attempts that were started and abandoned** — legacy code in `agents/`, archived docs, resolved issues, reverted commits. Failed approaches encode decisions that aren't documented anywhere else.

   **Agent 2 — Assumption Audit:** "What does our chosen approach assume, and is each assumption true?" Verify every assumption against actual code state. Probe these categories specifically:
   - Data model assumptions (cardinality, uniqueness, nullability the approach takes for granted)
   - Concurrency and ordering assumptions (what happens if two things run simultaneously)
   - Error handling assumptions (what the approach assumes about failure modes)
   - Scale assumptions (what volume/size the current code handles vs. what this feature implies)
   Each verified or broken assumption is a finding. Each broken assumption is a potential fork in the design.

   **Agent 3 — Adjacent Systems:** "What adjacent systems connect to this work, and what does touching them surface?" Trace the blast radius outward — not just "what breaks" but "what opportunities does this connection create?" Look at upstream consumers, downstream dependencies, shared infrastructure, and parallel workstreams.

2. **Synthesize into 5 outputs.** When agents return, produce:

   **A. File map** — what exists, what changes, what can be reused:
   ```
   Files to modify:
     - path/to/file.py (what it does, what changes)
   Files to reuse:
     - path/to/util.py (function X does what we need)
   Files affected:
     - docker-compose.override.yml (needs new env var)
     - tests/test_x.py (needs new test case)
   ```

   **B. Assumption audit** — what we assumed vs. what's actually true. Each entry ends with a prescriptive statement:
   ```
   Assumption: [what we assumed]
   Reality: [what the code actually does]
   This means we should: [specific implication for the approach]
   ```

   **C. Unexpected connections** — things found that weren't anticipated, grounded in specific code references. Each entry ends with:
   ```
   This means we should: [specific implication]
   ```

   **D. Approach pressure test** — does the Phase 1 approach still hold given what exploration revealed? State clearly: "Approach confirmed" or "Exploration suggests modifying the approach because [specific finding]."

   **E. Park list** — insights that are interesting but should not influence *this* feature. Explicitly separate from findings that matter now. The park list is not a graveyard — it is a named backlog that preserves divergent discoveries for future work. Each parked item includes why it's interesting and a suggested future context.

3. **Resolve agent conflicts.** If agents produced contradictory findings (e.g., Agent 1 says "pattern X worked well" and Agent 3 says "pattern X creates blast radius risk"), identify the contradiction and resolve it with reasoning. Do not present unreconciled conflicts.

### Advisor Review (mandatory)

4. **Dispatch an independent advisor agent.** The advisor receives: the feature description, the chosen approach, and the 5 synthesis outputs. The advisor's brief:
   - Is the approach pressure test (output D) honest? Does the exploration genuinely confirm the approach, or is the synthesis unconsciously rubber-stamping the Phase 1 decision?
   - Is the assumption audit thorough? Were the 4 categories probed seriously, or did the audit surface only obvious assumptions?
   - Is the park list properly separating now from later? Are items parked that should actually influence this feature, or items kept active that should be parked?
   - Are there contradictions between agents that the synthesis glossed over?

   If the advisor disagrees with the approach pressure test — e.g., the synthesis says "approach confirmed" but the advisor sees broken assumptions that should force a modification — flag this to Stephen with both perspectives before proceeding to the feedback loop.

### Feedback Loop (bounded)

5. **If the approach pressure test (output D) OR the advisor review suggests modifying the Phase 1 approach:**
   - Present the modification and reasoning to the user.
   - If approved, update the approach in `.claude/ship-state.md`.
   - Run **one more exploration pass** on the modified approach — same 3 agents, same structure.
   - If the second pass also wants to modify the approach, **stop.** This is a signal the feature is not well-enough understood for this workflow. Escalate: "Two exploration passes both want to change the approach. This needs more design conversation before we can plan."
   - **Maximum two passes.** No oscillation.

**Output:** File map + assumption audit + unexpected connections + approach pressure test + park list.

Update `.claude/ship-state.md`: add all 5 synthesis outputs, exploration pass count, park list.

> **Phase 2 complete. Continue to Phase 3 (Plan)?**

---

## Phase 3: Plan

**Goal:** Break the work into bite-sized tasks with exact file paths, code, risk flags, and verification steps.

1. **Architecture step (complex features only).** If Phase 1 flagged the feature as complex, start with a component/data flow design before breaking into tasks. Which services talk to which? What's the request path? What data crosses boundaries? Present this for approval before proceeding to the task list.

2. Write the plan as a numbered task list. Each task should take 2-5 minutes. Each task includes:
   - **Files:** Exact paths to read/modify/create
   - **Do:** What to implement — include function signatures, SQL queries, and any logic where multiple valid implementations exist. If the builder would have to make a design decision during implementation, the code goes in the plan.
   - **Verify:** How to prove it works (command to run, output to expect)
   - **Risk:** low / medium / high + blast radius (local / service / cross-service)
   - **Rollback:** For tasks that touch shared state (DB, config, Docker), include the rollback command (e.g., `git revert <commit>`, `DROP COLUMN`, `docker compose up -d <previous-image>`)

   Example:
   ```
   Task 3: Add GET /sessions/stats/overview endpoint
     Files: services/session-logger/main.py
     Do: Add endpoint with this implementation:
       @app.get("/sessions/stats/overview")
       def stats_overview():
           # SQL:
           # SELECT count(*) as total_sessions FROM session_logs;
           # SELECT count(*) as total_chunks FROM session_chunks;
           # SELECT min(created_at), max(created_at) FROM session_logs;
           # SELECT count(*) FILTER (WHERE embedding IS NOT NULL) * 100.0 / count(*)
           #   FROM session_chunks;
           # Return StatsOverview response model
     Verify: curl -s http://localhost:8009/sessions/stats/overview | python3 -m json.tool
     Risk: low (local — new read-only endpoint, no existing behavior changed)
     Rollback: git revert <commit> (no shared state touched)
   ```

3. **Deploy order (multi-service only).** If tasks span multiple services, specify the rebuild/restart order and why. Which service must be healthy before the next is rebuilt?

4. **Order tasks by dependency.** Independent tasks can be marked as parallelizable.

5. **Identify tasks that touch shared state** (database schemas, Docker configs, shared libraries). These get "medium" or "high" risk automatically.

6. Apply DRY, YAGNI. If something already exists in the codebase (found in Phase 2), reuse it. Do not build what you found.

7. **Chunk review (>5 tasks).** If the plan has more than 5 tasks, present them in groups of 3 for review. Get approval per chunk before showing the next. Do not present all tasks at once.

8. **TDD decision.** Ask: "Do you want TDD for this feature?" If yes, Phase 4 writes tests before implementation for each task.

9. **Advisor review (complex features only).** If Phase 1 flagged the feature as complex, dispatch an independent advisor agent before presenting the plan for approval. The advisor receives: the feature description, the approved spec, the Phase 2 synthesis outputs, and the full task list. The advisor's brief:
   - Are there missing tasks? Gaps between tasks where something needs to happen but isn't listed?
   - Is risk underestimated on any task? Especially tasks marked "low" that touch shared state or cross service boundaries.
   - Are rollback plans realistic? Would the rollback command actually work, or does it leave orphaned state?
   - Is the deploy order correct? Would rebuilding in this sequence actually work?
   - Are there Phase 2 findings (assumption audit, unexpected connections) that the plan ignores?

   Incorporate advisor findings into the plan before presenting to Stephen. Note which items came from the advisor review.

**HARD GATE:** Present the plan (or final chunk) and wait for user approval. Do not proceed to Phase 4 without explicit "go", "approved", "build it", or similar.

**Output:** Approved task list.

Update `.claude/ship-state.md`: add full plan, TDD decision, deploy order.

> **Phase 3 approved. Continue to Phase 4 (Build)?**

---

## Phase 4: Build

**Goal:** Execute the plan. Follow it exactly. Commit after each task.

1. **Branch check.** Run `git branch --show-current`. If on `master` or `main`, suggest a branch name derived from the feature description and ask:
   - Derive a slug from the feature description (lowercase, hyphens, ≤40 chars)
   - Prefix with `feat/` for new features, `fix/` for bug fixes, `refactor/` for refactors
   - Example: "Suggested branch: `feat/phase2-divergent-explore`. Create this branch, use a different name, or proceed on master?"
   Do not proceed without explicit answer.

2. **Create TodoWrite tasks** for each plan item. This provides persistent in-session state that survives context compression.

3. For each task in the plan:
   a. Announce: **"Task N/total: [description]"**
   b. Read the files listed in the task (view before edit — always)
   c. Implement exactly what the plan says
   d. Run the verification command from the plan
   e. If verification passes, commit with a descriptive message
   f. If verification fails, diagnose (one fix per hypothesis), fix, re-verify
   g. **Debugging escalation:** If verification fails twice (two hypotheses tested and failed), stop. State the problem clearly, form ranked hypotheses, and present them to Stephen before attempting a third fix. Invoke the systematic-debugging protocol.
   h. If tests exist for the affected code, run them. Report result.
   i. Update TodoWrite task status and `.claude/ship-state.md` with progress.

4. **Scope creep guard.** When discovering an unrelated issue during build (e.g., "this file also has a bug in line 200"):
   - **Unrelated issues:** Log to the **defer list** in `.claude/ship-state.md`. Do NOT fix. Do NOT stop to ask. Log it and keep building.
   - **Related blockers** (e.g., "the table I need doesn't exist"): Stop and ask Stephen. This is not scope creep — it's a blocker.

5. **Parallel execution.** If the plan marked tasks as parallelizable, dispatch them as parallel agents using the Agent tool. Each agent gets: the task description, file paths, verification command, and the instruction "commit when done."

6. **Subagent reconciliation.** After parallel agents return, diff their changes against each other. Look for logical conflicts: duplicate functions, inconsistent naming, overlapping concerns — not just merge conflicts. If conflicts exist, resolve them before proceeding.

7. **Stop when blocked.** If something unexpected happens, do not guess or force through. State what's wrong and ask the user.

8. After all tasks complete, show a summary:
   ```
   Built: N/N tasks complete
   Commits: [list of commit messages]
   Tests: X passed, Y failed, Z skipped
   Deferred: [count of items in defer list]
   ```

**Output:** All tasks implemented, verified, and committed.

Update `.claude/ship-state.md`: mark all tasks complete, list commits.

> **Phase 4 complete. Continue to Phase 5 (Verify)?**

---

## Phase 5: Verify

**Goal:** Prove everything works. No claims without evidence.

This phase exists because "it should work" is not verification. Run every check fresh.

1. **Run the full test suite** (if tests exist):
   ```bash
   pytest / npm test / whatever applies
   ```
   Show the full output. Do not summarize. If tests fail, fix them before proceeding.

2. **Verify each task's verification command** from the plan. Run them all again, fresh. Show output.

3. **Health check affected services:**
   - `docker ps` — all relevant containers healthy?
   - `curl` health endpoints — responding?
   - Any database changes applied correctly?

4. **Regression check.** Did existing functionality break? Spot-check endpoints/features that existed before this work.

5. **Performance baseline.** For each new endpoint, capture response time:
   ```bash
   curl -s -o /dev/null -w "%{time_total}" http://localhost:<port>/<endpoint>
   ```
   Record these baselines for future comparison.

6. **Meta-verify ship-state.md.** Quick check: does the state file accurately reflect the current reality? Tasks completed, commits made, verification results. If it's stale or inaccurate, update it.

7. **State the verdict with evidence:**
   - "All N verification commands pass. Output: [shown above]"
   - "Tests: X/Y pass. Failures: [list with details]"
   - "Services: all healthy. Evidence: [docker ps output]"
   - "Performance baselines: [endpoint: Xms, endpoint: Yms]"

   If anything fails, go back to Phase 4 for that specific task. Do not proceed to review with known failures.

**Output:** Verification evidence showing everything works.

Update `.claude/ship-state.md`: add all verification results and performance baselines.

> **Phase 5 complete. All checks pass. Continue to Phase 6 (Review)?**

---

## Phase 6: Review

**Goal:** Catch issues before shipping. Fix them, don't just report them.

1. **Scale review depth to diff size.** Run `git diff --stat` against the base branch to measure the change.

   **Small diff (≤3 files changed):** Dispatch a single unified code-reviewer agent that covers all concerns: silent failures, types, style, comments, test coverage, and complexity. One agent, one synthesized report.

   **Large diff (4+ files changed):** Dispatch 6 specialized review agents in parallel, each reviewing the full diff (`git diff` against the base branch):

   | Agent | Focus |
   |-------|-------|
   | silent-failure-hunter | Swallowed errors, empty catches, bad fallbacks, `return None` in error paths |
   | type-design-analyzer | Weak types, missing invariants, poor encapsulation |
   | code-reviewer | Style violations, convention mismatches, best practice gaps |
   | comment-analyzer | Stale comments, inaccurate docstrings, comment rot |
   | pr-test-analyzer | Test coverage gaps, missing edge cases, untested paths |
   | code-simplifier | Unnecessary complexity, duplication, readability issues |

2. **Grep-based silent-failure scan** (runs in parallel with agents). Fast first pass:
   - `except.*pass` or bare `except:` with no re-raise
   - Empty `catch {}` blocks
   - `return None` after error conditions
   - `# TODO` or `# FIXME` in new code

3. **Unify agent findings.** When agents return, synthesize into a single prioritized recommendation. If agents conflict (e.g., code-simplifier says "remove this" but code-reviewer says "this follows project patterns"), resolve the conflict and present the unified recommendation with reasoning. Stephen gets a clean view, not 6 competing reports.

4. **Test coverage check.** For each new function added, verify a test exists. If not, flag as Important severity: "Function X is untested."

5. **DHG-specific checks:**
   - Docker: Does this need a new container? Network membership correct? Port conflict with anything in CLAUDE.md's port table?
   - Database: Migration needed? Backward compatible? ON DELETE behavior correct?
   - CLAUDE.md compliance: Does the change align with documented architecture?
   - Brand: If UI work, does it use semantic tokens (not raw hex)?

6. **CLAUDE.md update check.** If new ports, services, endpoints, or architecture changes were made, draft the CLAUDE.md update. Do not apply yet — present for approval in Phase 8.

7. **Observability check.** If new endpoints were added:
   - Do they have Prometheus counters/histograms? If not, flag as Important.
   - Are they included in a Grafana dashboard? If not, note it.
   - Are they covered by an Alertmanager rule? If not, note it.

8. **Severity classification:**
   - **Critical** — blocks shipping (security vulnerability, data loss risk, broken functionality)
   - **Important** — should fix before merge (code quality, missing validation, config concern, untested functions, missing observability)
   - **Minor** — note for later (style nit, optimization opportunity)

9. **Fix-and-re-verify loop.** For each Critical and Important issue:
   a. State the issue and the fix
   b. Apply the fix
   c. Re-run the relevant verification from Phase 5
   d. Confirm it passes

**HARD GATE:** All Critical issues must be resolved. Important issues should be resolved. Only proceed with unresolved Important issues if the user explicitly approves.

**Output:** Review complete, all issues resolved (or user-approved exceptions).

Update `.claude/ship-state.md`: add review findings, resolutions, and any approved exceptions.

> **Phase 6 complete. Ready to document. Continue to Phase 7 (Document)?**

---

## Phase 7: Document

**Goal:** Generate comprehensive project documentation while all context is fresh. Documentation written at ship time is 10x better than documentation written later.

This phase produces two categories of output: a **ship log entry** (always) and **feature documentation** (when warranted).

### Ship Log Entry (always generated)

1. **Generate a structured ship log entry** from the ship-state.md data. Write it to:
   ```
   docs-site/projects/dhg-ai-factory/ship-log/NNN-[slug].md
   ```
   where NNN is the next sequential number and slug is derived from the feature description.

   Use this template (matches Portage ship log format):
   ```markdown
   ---
   title: "[feature description]"
   sidebar_label: "[truncated feature description]"
   sidebar_position: [NNN]
   ---

   # [feature description]

   | Field | Value |
   |-------|-------|
   | **Status** | complete |
   | **Complexity** | [simple/complex] |
   | **TDD** | [Yes/No] |
   | **PR** | [PR URL] |
   | **Completed** | [date] |
   | **Model** | [model used] |

   ## Approach

   [Chosen approach from Phase 1, 2-3 sentences]

   ## Spec

   [Approved spec from Phase 1]

   ## Exploration Findings

   [Key findings from Phase 2 — assumption audit results, unexpected connections, approach pressure test outcome. Only the findings that influenced the build, not the full exploration dump.]

   ## Commits

   - `[hash] [message]`

   ## Verification

   - **tests:** [result]
   - **health checks:** [result]
   - **performance baselines:** [endpoint: Xms]

   ## Review Findings

   [Issues found and resolved in Phase 6, with severity]

   ## Deferred Items

   - [item] — [why it matters] — [suggested priority]

   ## Park List

   [Divergent discoveries from Phase 2 that were parked for future work]

   **Tags:** `[relevant tags]`
   ```

### Feature Documentation (when warranted)

2. **Assess documentation scope.** Generate feature docs if ANY of these are true:
   - New API endpoints were added → generate/update API reference page
   - New service or container was added → generate/update architecture page
   - Database schema changed → generate/update database page
   - New frontend routes or components were added → generate/update frontend page
   - New observability (dashboards, alerts) was added → generate/update monitoring page
   - Configuration or environment variables changed → update environment-variables page

   If none are true (e.g., pure bug fix, internal refactor), skip feature docs.

3. **Write feature documentation** following the Portage doc structure. Place files in the appropriate subdirectory under `docs-site/projects/dhg-ai-factory/`:

   | Change Type | Doc Location |
   |-------------|-------------|
   | New/changed API endpoints | `api/[endpoint-group].md` |
   | Architecture changes | `architecture/[component].md` |
   | Frontend changes | `frontend/[feature].md` |
   | Database schema changes | `architecture/database.md` |
   | New service/container | `services.md` or `architecture/[service].md` |
   | Config/env changes | `environment-variables.md` |
   | Monitoring/observability | `monitoring.md` |

   Each doc page follows this structure:
   - **Purpose** — what this component does and why it exists (2-3 sentences)
   - **Usage** — how to use it (endpoints with request/response examples, CLI commands, UI flows)
   - **Configuration** — env vars, config files, feature flags
   - **Architecture** — how it fits into the system (data flow, dependencies, network)
   - **Troubleshooting** — common issues and fixes (only if known)

4. **Update the sidebar.** If new doc pages were created, update `docs-site/sidebars/dhg-ai-factory.ts` to include them in the correct category. Create new categories as needed following the Portage sidebar pattern (Architecture, API Reference, Frontend, Ship Log, etc.).

### Memory Pipeline Ingest

5. **Push ship session to the registry** for the knowledge base:
   ```bash
   curl -s -X POST http://10.0.0.251:8011/api/v1/ship_sessions \
     -H "Content-Type: application/json" \
     -d '{
       "project": "dhg-ai-factory",
       "feature": "[description]",
       "approach": "[chosen approach]",
       "complexity": "[simple/complex]",
       "phase_count": 8,
       "task_count": [N],
       "commit_count": [N],
       "deferred_count": [N],
       "park_list_count": [N],
       "exploration_findings": "[key findings summary]",
       "review_findings": "[issues found and resolved]",
       "pr_url": "[PR URL or null]",
       "status": "complete"
     }'
   ```
   If this fails, log the warning but do not block — the ship log markdown is the primary record.

6. **Present documentation summary:**
   ```
   Documented:
   - Ship log: docs-site/projects/dhg-ai-factory/ship-log/NNN-slug.md
   - Feature docs: [list of pages created/updated, or "none needed"]
   - Sidebar: [updated / no changes]
   - Registry: [ingested / failed (warning shown)]
   ```

**Output:** Ship log entry + feature docs (if applicable) + sidebar update + registry ingest.

Update `.claude/ship-state.md`: add documentation outputs.

> **Phase 7 complete. Continue to Phase 8 (Ship)?**

---

## Phase 8: Ship

**Goal:** Get it merged.

1. **Stage and commit** all remaining changes from Phase 6 fixes and Phase 7 documentation.

2. **Apply CLAUDE.md update** (if drafted in Phase 6 and approved). Include in the final commit.

3. **Push and create PR:**
   - If not already pushed, push the branch with `-u`
   - Create PR using `gh pr create` with this structure:
     ```
     Title: [concise description, under 70 chars]

     ## Summary
     [2-3 bullet points of what was built]

     ## Phases completed
     - Brainstorm: [approach chosen]
     - Explore: [full divergent / targeted, key findings]
     - Spec: [light/detailed, N iterations]
     - Plan: [N tasks, TDD: yes/no]
     - Build: [N commits]
     - Verify: [all checks pass, performance baselines]
     - Review: [N issues found and fixed, agents used]
     - Document: [ship log + N feature doc pages]

     ## Test plan
     - [ ] [verification steps someone else can follow]

     ## Monitor
     - Dashboard: [Grafana dashboard URL or name]
     - Key metric: [what to watch]
     - Alert threshold: [what value means rollback]
     - Alert rule: [exists / needs creation]
     - Watch period: [how long to monitor after merge]

     ## Risk
     [blast radius: local/service/cross-service]
     [rollback plan if issues detected]

     ## Deferred items
     [Items discovered during build but intentionally not fixed]
     - [what] in [where] — [why it matters] — [suggested priority]
     ```

4. **Present defer list + park list.** Show both the defer list (Phase 4, build-time discoveries) and the park list (Phase 2, exploration discoveries). Everything not addressed in this run, formatted as actionable items. This is the seed for the next `/ship` run.

5. **Log to session-logger.** Submit a summary of this workflow and verify it succeeded:
   ```bash
   RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8009/sessions/ingest-log \
     -H "Content-Type: application/json" \
     -d '{"hostname":"g700data1","username":"swebber64","raw_log":"[summary of phases, tasks, decisions, PR URL]"}')
   HTTP_CODE=$(echo "$RESPONSE" | tail -1)
   ```
   If `HTTP_CODE` is not 200/201, warn: **"Session logger failed (HTTP [code]). Audit trail was NOT recorded. Check if dhg-session-logger is healthy."** Do not silently continue — this is the workflow's audit trail.

6. **Finalize `.claude/ship-state.md`:**
   ```
   status: complete
   pr: [PR URL]
   completed_at: [timestamp]
   ```
   Do not delete the file — it serves as a record of the last ship run.

7. **Present the PR URL** to the user.

> **Shipped. PR: [URL]**

---

## Navigation Commands

The user can say these at any time:
- **"skip"** — jump to the next phase
- **"skip to N"** — jump directly to phase N
- **"stop"** — update `.claude/ship-state.md` with `status: stopped` and current phase, then exit the workflow
- **"back"** — return to the previous phase
- **"status"** — show which phase we're in and what's done

---

## Version History
- **v1** (2026-03-13): Initial 7-phase workflow. Saved as `ship_v1.md`.
- **v2** (2026-03-13): Full capability restoration + 14 additions. Restored: spec iterations, divergent thinking, 6 review agents, code in plans, chunk review, TodoWrite, subagent reconciliation. Added: resume detection, state persistence, scope creep guard, rollback fields, debugging escalation, complexity-conditional spec, architecture step, TDD toggle, CLAUDE.md update check, observability check, deploy order, post-merge monitoring, performance baselines, actionable monitor section.
- **v3** (2026-05-19): Divergent-convergent redesign + documentation phase + grounded brainstorm + advisor review gates. Now 8 phases. Phase 1: dynamic feasibility (reads CLAUDE.md, no hardcoded issues), explore scope gating with recommendation + pause. Phase 2: full rewrite — 3 agents shift from inventory to divergent discovery (analogous solutions + abandoned prior art, assumption audit with 4 category probes, adjacent systems + opportunities), 5 synthesis outputs (file map, assumption audit, unexpected connections, approach pressure test, park list), bounded feedback loop to Phase 1 (2-pass max circuit breaker), prescriptive endings ("This means we should..."), agent conflict resolution. Phase 4: branch naming auto-suggestion (feat/fix/refactor prefix + slug). Phase 6: review depth scales by diff size (single reviewer ≤3 files, 6-agent army for 4+). **Phase 7 (NEW): Document** — auto-generates ship log entry (Portage format), feature documentation (API, architecture, frontend, monitoring pages when warranted), updates docs-site sidebar, pushes to registry memory pipeline. Phase 8 (was 7): session-logger POST error handling (warns on failure, no silent audit trail loss), PR template now includes Explore + Document phases, defer list + park list surfaced together.
