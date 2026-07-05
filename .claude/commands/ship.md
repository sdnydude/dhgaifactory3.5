# /ship — Full Feature Shipping Workflow (with Dev Tools)

You are running an 8-phase workflow to take a feature from idea to merged PR. This is the DHG AI Factory's production shipping process. Every phase builds on the previous one and carries context forward — do NOT re-explore or re-ask what was already established.

**This is v5** — the canonical /ship. Lineage in one line: v3 introduced the 8-phase divergent-convergent design; v4 layered dev tools onto it (tdd-guard in Phases 3-4, AgentShield in Phase 5, claudekit doctor in Phase 4, ccpm on-demand, Dev tool results in the PR template); v5 promoted it to `/ship` with capture-path and URL fixes. Full details in Version History at the bottom. Core capabilities: Phase 0 feedback briefing, divergent-convergent apparatus, advisor reviews, Phase 7 documentation, full memreg read+write integration.

The user may have provided a feature description: $ARGUMENTS

If no arguments were provided, ask: **"What are we shipping?"** and wait.

---

## Resume Check

Before anything else (including Phase 0), check if `.claude/ship-state.md` exists. If it does, read it and branch on its frontmatter `status:`:

- **`in_progress` or `stopped`:** ask — **"A previous /ship run was [in progress/stopped] at Phase [N]: [feature description]. Resume or start fresh?"**
- **`deferred`:** this is a deliberately parked ship, not an abandoned one. Ask — **"A deferred ship exists: [feature description], paused at Phase [N] ([deferred_note if present]). Resume it, keep it parked and start fresh, or archive it?"** Never silently overwrite a deferred ship.
- **`complete`:** previous ship finished — start fresh (versioning still applies below).
- **Corrupt/unparseable** (status missing, phase missing or non-unique, frontmatter mangled): **halt.** Show Stephen the raw file contents and ask how to proceed. Never overwrite a state file you could not parse.

If resuming, load the state (approach, file map, plan, progress) and continue from the recorded phase. **Resuming into Phase 4 or later additionally requires:** verify the Phase 3 plan artifact actually exists in ship-state.md, and ask Stephen to reconfirm the Phase 3 approval before any code is written — a recorded phase number alone is not approval.

If starting fresh over ANY existing state file (in_progress, stopped, deferred, or complete), first version it as `ship-state_v{N}.md` (N = next unused number), then begin Phase 0. The versioning happens at fresh-start time, before Phase 1's state write — not only on the resume path.

**Compaction re-anchor rule:** after any context compaction mid-run, re-read `.claude/ship-state.md` before the next action — the state file, not compressed memory, is the source of truth for phase/progress.

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

5. **Output briefing** (one block, not a conversation). **[Failure protocol]** If any of the four curls above failed (timeout, connection refused, non-JSON response), that line of the briefing must read **"unavailable — registry down"**, never "no corrections" / "0 deferred items". An outage is an unknown, not an absence. Like Phase 1's KB search, this is not blocking — note it and proceed.
   ```
   === SHIP FEEDBACK BRIEFING ===
   Correction patterns: [top pattern] ([count]x in 7d) — [repeat flags if any] | or: unavailable — registry down
   Deferred items: [open count] open, [stale count] stale — [related items if found] | or: unavailable — registry down
   Related decisions: [titles of related decision logs if found] | or: unavailable — registry down
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
- **tdd-guard is active.** The tdd-guard plugin enforces test-first development via PreToolUse hooks. When TDD is enabled (Phase 3 decision), write tests before implementation — tdd-guard will block code edits that lack corresponding tests.

---

## Advisor Dispatch (shared definition)

All three advisor reviews (Phase 1 step 9, Phase 2 step 4, Phase 3 step 9) use the same dispatch — do not improvise the executor:

- **Agent tool, `subagent_type: general-purpose`** (no dedicated "advisor" agent type exists; general-purpose gets full tool access for verification).
- **Prompt template:** "You are an independent advisor reviewing a /ship [phase name] output. You did not produce this work — challenge it. Inputs: [the phase-specific inputs listed at the dispatch site]. Your brief: [the phase-specific brief listed at the dispatch site]. Verify claims against the actual codebase where possible instead of taking the inputs' word. Return: numbered advisor notes, each tagged AGREE / CHALLENGE / GAP, with a one-line justification grounded in something specific (code, KB finding, or the input's own text). End with a one-paragraph verdict: is this output ready to present to Stephen?"
- A failed/empty advisor return is handled per the Failure Protocol (never silently skipped).

---

## Failure Protocol (applies to every external call and agent dispatch)

Every tool step and agent dispatch in this workflow has exactly three possible outcomes — report the one that actually happened:

- **RAN-WITH-FINDINGS** — the step executed and surfaced items to act on.
- **RAN-CLEAN** — the step executed and genuinely found nothing.
- **FAILED-TO-RUN** — the invocation itself failed (network error, missing binary, non-zero exit before output, empty/garbage return, agent never returned).

**The rule: FAILED-TO-RUN is never reported as clean.** A failed check is an unknown, not a pass. Default handling unless a site says otherwise: retry once; if it fails again, surface **"STEP FAILED — output unavailable"** in the phase verdict and to Stephen, and record it in ship-state.md. Site-specific handling is marked **[Failure protocol]** at each call site.

---

## Phase 1: Brainstorm (Grounded Divergence)

**Goal:** Understand the problem, gather what the project already knows about it, diverge from accumulated knowledge, converge on an approach, and produce a spec.

**Philosophy:** Phase 1 diverges from *institutional memory* — the knowledge base, past decisions, corrections, park lists, and existing code patterns. Phase 2 diverges from *live codebase exploration*. Two complementary divergent-convergent cycles with different inputs.

### Load Context

1. Read CLAUDE.md to load full project context (architecture, known issues, tech stack).

2. **Feasibility check.** Read the CONSTRAINTS block in project CLAUDE.md and the `reference_port_map.md` auto-memory file (`~/.claude/projects/-home-swebber64-DHG-aifactory3-5-dhgaifactory3-5/memory/reference_port_map.md`) — these two are the authoritative sources for constraints and port assignments (CLAUDE.md has no other issues section). Check if this feature conflicts with any documented constraint or port assignment. If conflicts exist, flag them immediately: "This feature touches [constraint]. Here's how we handle it: [approach]."

### Gather Institutional Knowledge

3. **Knowledge base query.** Query accumulated project knowledge for anything relevant to this feature.

   **Current (keyword search):** Hit the registry's KB search endpoint (POST — the GET /api/v1 form does not exist and 404s):
   ```bash
   curl -s -X POST "http://10.0.0.251:8011/api/kb/search" \
     -H "Content-Type: application/json" \
     -d '{"query":"[feature keywords]","limit":10}'
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

9. **Advisor review (complexity-gated — same gate as Phase 3's advisor).** Assess complexity NOW using step 11's criteria (3+ services, schema change, >5 likely tasks). If **complex**: dispatch an independent advisor agent per the **Advisor Dispatch** definition (`subagent_type: general-purpose`, shared prompt template). If **simple**: skip the dispatch — instead run a main-session feasibility check against the same brief below and record its outcome in ship-state.md as `advisor: main-session check (simple)`. A dispatched advisor receives: the feature description, the KB findings, the CodeGraph scan results, the divergent lens output, and the 2-3 proposed approaches. The advisor's brief:
   - Challenge the approaches — what was missed, what's underestimated, what alternative wasn't considered?
   - Evaluate whether KB findings (corrections, past decisions, park list items) were properly incorporated or ignored
   - Assess whether the recommended approach is genuinely the strongest, or whether the recommendation is defaulting to the most obvious option
   - Flag any concerns as "advisor notes"

   Incorporate the advisor's feedback into the approaches. If the advisor identified a genuinely better alternative or a critical gap, update the approaches before presenting to Stephen. Present the advisor's key challenges alongside the approaches — Stephen sees both the recommendation and the independent pushback.

   **[Failure protocol]** When the advisor is dispatched (complex path): if the dispatch errors, times out, or returns empty/off-topic output, retry once; if it fails again, HALT and tell Stephen — "Phase 1 advisor failed twice; proceed without independent review, or retry?" Do not present approaches as advisor-reviewed when no advisor ran.

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

Write initial `.claude/ship-state.md` (if an old state file exists and wasn't already versioned by the Resume Check, version it as `ship-state_v{N}.md` first — never overwrite in place). Frontmatter keys must stay single-line and occur exactly once each — enforce-ship.sh parses them:
```
status: in_progress
phase: 1
feature: [description]
approach: [chosen approach]
complexity: [simple/complex]
explore_scope: [full/targeted]
branch: [not yet created — recorded at Phase 4 step 1]
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

2. **Synthesize into 5 outputs.** When agents return, first verify **N dispatched == N returned with usable output**. **[Failure protocol]** An agent that errored, timed out, or returned empty/off-topic output counts as FAILED-TO-RUN: re-dispatch it once; if it fails again, the synthesis must name the missing perspective ("Assumption Audit did not run — assumptions are UNAUDITED, not verified") rather than synthesizing around the hole. A failed Assumption Audit is never reported as "assumptions verified."

   Then produce:

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

4. **Dispatch an independent advisor agent** per the **Advisor Dispatch** definition (`subagent_type: general-purpose`, shared prompt template). The advisor receives: the feature description, the chosen approach, and the 5 synthesis outputs. The advisor's brief:
   - Is the approach pressure test (output D) honest? Does the exploration genuinely confirm the approach, or is the synthesis unconsciously rubber-stamping the Phase 1 decision?
   - Is the assumption audit thorough? Were the 4 categories probed seriously, or did the audit surface only obvious assumptions?
   - Is the park list properly separating now from later? Are items parked that should actually influence this feature, or items kept active that should be parked?
   - Are there contradictions between agents that the synthesis glossed over?

   If the advisor disagrees with the approach pressure test — e.g., the synthesis says "approach confirmed" but the advisor sees broken assumptions that should force a modification — flag this to Stephen with both perspectives before proceeding to the feedback loop.

   **[Failure protocol]** Same as the Phase 1 advisor: retry once on failure; on second failure, report the synthesis as UN-REVIEWED to Stephen and let him decide — never imply advisor sign-off that didn't happen.

### Feedback Loop (bounded)

5. **If the approach pressure test (output D) OR the advisor review suggests modifying the Phase 1 approach:**
   - Present the modification and reasoning to the user.
   - If approved, update the approach in `.claude/ship-state.md`.
   - Run **one more exploration pass** on the modified approach — same 3 agents, same structure.
   - If the second pass also wants to modify the approach, **stop.** This is a signal the feature is not well-enough understood for this workflow. Escalate: "Two exploration passes both want to change the approach. This needs more design conversation before we can plan."
   - **Maximum two passes.** No oscillation.

**Output:** File map + assumption audit + unexpected connections + approach pressure test + park list.

Update `.claude/ship-state.md`: add all 5 synthesis outputs, exploration pass count, park list; **set `phase: 3`**.

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
     Verify: curl -s http://10.0.0.251:8009/sessions/stats/overview | python3 -m json.tool
     Risk: low (local — new read-only endpoint, no existing behavior changed)
     Rollback: git revert <commit> (no shared state touched)
   ```

3. **Deploy order (multi-service only).** If tasks span multiple services, specify the rebuild/restart order and why. Which service must be healthy before the next is rebuilt?

4. **Order tasks by dependency.** Independent tasks can be marked as parallelizable.

5. **Identify tasks that touch shared state** (database schemas, Docker configs, shared libraries). These get "medium" or "high" risk automatically.

6. Apply DRY, YAGNI. If something already exists in the codebase (found in Phase 2), reuse it. Do not build what you found.

7. **Chunk review (>5 tasks).** If the plan has more than 5 tasks, present them in groups of 3 for review. Get approval per chunk before showing the next. Do not present all tasks at once.

8. **TDD decision.** Ask: "Do you want TDD for this feature?" If yes, Phase 4 writes tests before implementation for each task. Note: **tdd-guard hooks are active** and will enforce test-first ordering when TDD is enabled.

9. **Advisor review (complex features only).** If Phase 1 flagged the feature as complex, dispatch an independent advisor agent per the **Advisor Dispatch** definition (`subagent_type: general-purpose`, shared prompt template) before presenting the plan for approval. The advisor receives: the feature description, the approved spec, the Phase 2 synthesis outputs, and the full task list. The advisor's brief:
   - Are there missing tasks? Gaps between tasks where something needs to happen but isn't listed?
   - Is risk underestimated on any task? Especially tasks marked "low" that touch shared state or cross service boundaries.
   - Are rollback plans realistic? Would the rollback command actually work, or does it leave orphaned state?
   - Is the deploy order correct? Would rebuilding in this sequence actually work?
   - Are there Phase 2 findings (assumption audit, unexpected connections) that the plan ignores?

   Incorporate advisor findings into the plan before presenting to Stephen. Note which items came from the advisor review.

**HARD GATE:** Present the plan (or final chunk) and wait for user approval. The accepted approval tokens are exactly: **"go"**, **"approved"**, **"build it"**, **"ship it"**. Neutral acknowledgments — "ok", "sounds good", "makes sense", "sure" — do NOT cross this gate (per the explicit-approval rule in Rules: Stephen must explicitly approve moving to implementation). If the response is ambiguous, ask: "Is that approval to build? (go / approved / build it / ship it)"

Upon approval, write the approval record into `.claude/ship-state.md` frontmatter as a single line:
```
approved: "[exact token Stephen used]" [ISO 8601 timestamp]
```
enforce-ship.sh requires this `approved:` line before it permits code edits at phase ≥ 4 — a phase number alone no longer opens the Build gate.

**Output:** Approved task list.

Update `.claude/ship-state.md`: add full plan, TDD decision, deploy order; **set `phase: 4`** (this write happens only after the HARD GATE approval above).

> **Phase 3 approved. Continue to Phase 4 (Build)?**

---

## Phase 4: Build

**Goal:** Execute the plan. Follow it exactly. Commit after each task.

1. **Branch check.** Run `git branch --show-current`. If on `master` or `main`, suggest a branch name derived from the feature description and ask:
   - Derive a slug from the feature description (lowercase, hyphens, ≤40 chars)
   - Prefix with `feat/` for new features, `fix/` for bug fixes, `refactor/` for refactors
   - Example: "Suggested branch: `feat/phase2-divergent-explore`. Create this branch, use a different name, or proceed on master?"
   Do not proceed without explicit answer. Note: enforce-ship.sh denies code edits on master/main during an active build — a feature branch is the working default.
   Once on the working branch, record it in `.claude/ship-state.md`: **set `branch: [name]`** (replaces the Phase 1 placeholder) — resume after a crash needs it.

2. **Pre-build health check.** First check the binary exists: `command -v claudekit`. **[Failure protocol]** If missing, or if `claudekit doctor` itself crashes/errors, report "pre-build health check FAILED-TO-RUN (claudekit missing/errored)" to Stephen and ask whether to proceed — a tool that didn't run found nothing; do not treat it as a clean bill of health. If it runs and flags issues, fix them before building.

2b. **AgentShield baseline check.** Verify `.claude/agentshield-baseline.json` exists and predates this branch's changes. If missing or stale (master has moved since it was generated), regenerate it from the base branch state: run `npx ecc-agentshield@1.4.0 scan` on master (or against the pre-branch tree), save the findings as `.claude/agentshield-baseline.json`, and commit it. Phase 5 compares against this artifact — without it the "new findings introduced by this feature" gate cannot be evaluated.

3. **Create TodoWrite tasks** for each plan item. This provides persistent in-session state that survives context compression.

4. For each task in the plan:
   a. Announce: **"Task N/total: [description]"**
   b. Read the files listed in the task (view before edit — always)
   c. If TDD is enabled: write the test first, run it (expect failure), then implement. tdd-guard enforces this ordering via PreToolUse hooks.
   d. Implement exactly what the plan says
   e. Run the verification command from the plan
   f. If verification passes, commit with a descriptive message
   g. If verification fails, diagnose (one fix per hypothesis), fix, re-verify
   h. **Debugging escalation:** If verification fails twice (two hypotheses tested and failed), stop. State the problem clearly, form ranked hypotheses, and present them to Stephen before attempting a third fix. Invoke the systematic-debugging protocol.
   i. If tests exist for the affected code, run them. Report result.
   j. Update TodoWrite task status and `.claude/ship-state.md` with progress.

5. **Scope creep guard.** When discovering an unrelated issue during build (e.g., "this file also has a bug in line 200"):
   - **Unrelated issues:** Log to the **defer list** in `.claude/ship-state.md`. Do NOT fix. Do NOT stop to ask. Log it and keep building.
   - **Related blockers** (e.g., "the table I need doesn't exist"): Stop and ask Stephen. This is not scope creep — it's a blocker.

6. **Parallel execution (worktree-isolated).** If the plan marked tasks as parallelizable AND there are ≥3 such tasks, dispatch them as parallel agents using the Agent tool with **each agent in its own git worktree** under `.claude/worktrees/` (use the installed using-git-worktrees skill, or `Agent` with `isolation: "worktree"`). Shared-working-tree parallel commits race on the git index — never run parallel build agents in one tree. Each agent gets: the task description, file paths, verification command, and the instruction "commit when done on your worktree branch."

   **Serial fallback:** for ≤2 parallelizable tasks, run them serially in the main tree — worktree setup overhead isn't worth it.

7. **Subagent reconciliation (before merge).** After parallel agents return, reconciliation happens **on the worktree branches, before merging into the ship branch** — not as post-hoc history rewrite. Diff the worktree branches against each other; look for logical conflicts: duplicate functions, inconsistent naming, overlapping concerns — not just merge conflicts. Resolve conflicts on the branches, then merge each into the ship branch and remove the worktrees.

   **[Failure protocol]** An agent that never returns, errors out, or returns without committing counts as FAILED-TO-RUN: put its task back on the TodoWrite list and either re-dispatch or do it in the main session. The completion summary (step 9) must cross-check dispatched-agent count against actual commits (`git log` since the branch point) — "Built: N/N" is only claimable when the commit count corroborates it.

8. **Stop when blocked.** If something unexpected happens, do not guess or force through. State what's wrong and ask the user.

9. After all tasks complete, show a summary:
   ```
   Built: N/N tasks complete
   Commits: [list of commit messages]
   Tests: X passed, Y failed, Z skipped
   Deferred: [count of items in defer list]
   ```

**Output:** All tasks implemented, verified, and committed.

Update `.claude/ship-state.md`: mark all tasks complete, list commits; **set `phase: 5`**.

> **Checkpoint cadence:** `complexity: complex` — pause here as usual. `complexity: simple` — ask once: **"Phase 4 complete. Continue through Phase 5 (Verify) AND Phase 6 (Review)?"** — one approval covers both phases; do not pause again at the 5→6 boundary.
>
> **Phase 4 complete. Continue to Phase 5 (Verify)?**

---

## Phase 5: Verify

**Goal:** Prove everything works. No claims without evidence.

This phase exists because "it should work" is not verification. Run every check fresh.

1. **Run the owning test suite(s)** — select by changed paths, not "whatever applies":

   | Changed paths | Suite to run |
   |---|---|
   | `registry/` | registry pytest suite |
   | `frontend/` | vitest (`npm test` in frontend/) |
   | `langgraph_workflows/` | that workflow package's pytest suite |
   | multiple of the above | each owning suite |

   **Output discipline (context budget):** show the FULL output for any failure; for passing suites show the summary line only (e.g. `514 passed in 42.1s`). Write the complete run log to the scratchpad and cite its path in the verdict — auditability is preserved in the file, not by dumping thousands of lines into context at the exact point (pre-Phase 6) where compaction risk peaks. If tests fail, fix them before proceeding.

2. **Verify each task's verification command** from the plan. Run them all again, fresh. Show output.

3. **Health check affected services:**
   - `docker ps` — all relevant containers healthy?
   - `curl` health endpoints — responding?
   - Any database changes applied correctly?

4. **Regression check.** Did existing functionality break? Spot-check endpoints/features that existed before this work.

5. **AgentShield security scan.** Run the security audit on the project config and capture the exit code:
   ```bash
   npx ecc-agentshield@1.4.0 scan; echo "exit=$?"
   ```
   **[Failure protocol]** Check the exit code and require an actual findings report before interpreting anything. If npx fails (ENOTFOUND, non-zero exit before a report, empty output), the Phase 5 verdict and the Phase 8 PR "Dev tool results" line must say **"SCAN FAILED — security posture unverified"**, never "no findings". Retry once, then surface to Stephen.

   **Baseline comparison:** the project baseline is the committed `.claude/agentshield-baseline.json` (generated at Phase 4 step 2b). Compare finding identity — rule id + file — via jq set-difference: findings in this scan but not in the baseline are **new**. If any new Critical or High findings were introduced by this feature, fix them before proceeding. Pre-existing findings are acceptable and may be documented as deferred items.

6. **Performance baseline.** For each new endpoint, capture response time:
   ```bash
   curl -s -o /dev/null -w "%{time_total}" http://10.0.0.251:<port>/<endpoint>
   ```
   Record these baselines for future comparison.

7. **Meta-verify ship-state.md.** Quick check: does the state file accurately reflect the current reality? Tasks completed, commits made, verification results. If it's stale or inaccurate, update it.

8. **State the verdict with evidence:**
   - "All N verification commands pass. Output: [shown above]"
   - "Tests: X/Y pass. Failures: [list with details]. Full log: [scratchpad path]"
   - "Services: all healthy. Evidence: [docker ps output]"
   - "AgentShield: no new findings / N new findings [details]"
   - "Performance baselines: [endpoint: Xms, endpoint: Yms]"

   If anything fails, go back to Phase 4 for that specific task. Do not proceed to review with known failures.

**Output:** Verification evidence showing everything works.

Update `.claude/ship-state.md`: add all verification results and performance baselines; **set `phase: 6`**.

> **Phase 5 complete. All checks pass. Continue to Phase 6 (Review)?**

---

## Phase 6: Review

**Goal:** Catch issues before shipping. Fix them, don't just report them.

1. **Scale review depth to the ship-state `complexity` flag** (written at Phase 1) — file count is the escalation input, not the router. Read `complexity:` from `.claude/ship-state.md` and run `git diff --stat` against the base branch:

   **`complexity: complex`:** always the 6-agent panel below, regardless of file count.

   **`complexity: simple`:** a single unified code-reviewer agent covering all concerns (silent failures, types, style, comments, test coverage, complexity) — **escalating to the full 6-agent panel if** the diff touches ≥8 files OR any schema/auth/migration path (a mis-classified "simple" ship still gets the heavy gate when the diff says otherwise).

   The 6-agent panel: dispatch 6 specialized review agents in parallel, each reviewing the full diff (`git diff` against the base branch). These six agents are provided by the **pr-review-toolkit plugin** — a named dependency of this workflow alongside tdd-guard/AgentShield/claudekit. **Fallback:** if the plugin is disabled or the named agent types don't resolve, dispatch `general-purpose` agents instead, giving each the corresponding Focus description below as its prompt:

   | Agent (pr-review-toolkit) | Focus |
   |-------|-------|
   | silent-failure-hunter | Swallowed errors, empty catches, bad fallbacks, `return None` in error paths |
   | type-design-analyzer | Weak types, missing invariants, poor encapsulation |
   | code-reviewer | Style violations, convention mismatches, best practice gaps |
   | comment-analyzer | Stale comments, inaccurate docstrings, comment rot |
   | pr-test-analyzer | Test coverage gaps, missing edge cases, untested paths |
   | code-simplifier | Unnecessary complexity, duplication, readability issues |

   Apply the **Karpathy review lens** (`.claude/review-lenses/karpathy-review.md`) across the review: assumptions surfaced, simplicity-first, surgical diff, verified success criteria. On the single-reviewer path, cite that file in the reviewer's prompt; on the 6-agent path, code-reviewer and code-simplifier carry it.

2. **Grep-based silent-failure scan** (runs in parallel with agents). Fast first pass:
   - `except.*pass` or bare `except:` with no re-raise
   - Empty `catch {}` blocks
   - `return None` after error conditions
   - `# TODO` or `# FIXME` in new code

3. **Unify agent findings.** When agents return, synthesize into a single prioritized recommendation. If agents conflict (e.g., code-simplifier says "remove this" but code-reviewer says "this follows project patterns"), resolve the conflict and present the unified recommendation with reasoning. Stephen gets a clean view, not 6 competing reports.

   **[Failure protocol]** Each agent's report must state which files it covered. A report that is empty, malformed, truncated, or covers less than the changed-file set counts as FAILED-TO-RUN for that agent: re-dispatch it once before synthesizing. The Phase 6 hard gate may only be evaluated when every dispatched reviewer produced a usable, full-coverage report — a missing report is unreviewed code, not clean code.

4. **Test coverage check.** For each new function added, verify a test exists. If not, flag as Important severity: "Function X is untested."

5. **DHG-specific checks:**
   - Docker: Does this need a new container? Network membership correct? Port conflict with anything in the `reference_port_map.md` memory file (the authoritative port map — not CLAUDE.md)?
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

8b. **Classification audit (before the gate is evaluated).** The severity assignments must not be self-attested by whoever produced them. On the multi-agent path, dispatch one audit agent (`subagent_type: general-purpose`) that receives the findings list and the three severity definitions verbatim, and validates each Critical/Important/Minor assignment against the definitions. On the single-reviewer path, do an explicit main-session re-check of each assignment against the definitions. Any down-classification (Critical→Important, Important→Minor) must be justified in the audit verdict with a specific reason; unjustified down-classifications revert to the higher severity. The Phase 6 hard gate is evaluated against the audited classifications.

9. **Fix-and-re-verify loop.** For each Critical and Important issue:
   a. State the issue and the fix
   b. Apply the fix
   c. Re-run the relevant verification from Phase 5
   d. Confirm it passes

**HARD GATE:** All Critical issues must be resolved. Important issues should be resolved. Only proceed with unresolved Important issues if the user explicitly approves.

**Output:** Review complete, all issues resolved (or user-approved exceptions).

Update `.claude/ship-state.md`: add review findings, resolutions, and any approved exceptions; **set `phase: 7`**.

> **Checkpoint cadence:** `complexity: complex` — pause here as usual. `complexity: simple` — ask once: **"Phase 6 complete. Continue through Phase 7 (Document) AND Phase 8 (Ship)?"** — one approval covers docs + finalize; do not pause again at the 7→8 boundary. (Simple ships thus need ~4 approvals total: after Phases 1, 2, the Phase 3 HARD GATE, 4→5/6, and 6→7/8.)
>
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

4. **Sidebar: no edit needed (or possible).** The docs-site sidebar is the single autogenerated `docs-site/sidebars.ts` (`{type:'autogenerated', dirName:...}`) — per-project sidebar files do not exist. New pages are auto-included: just create the doc page under the correct directory in `docs-site/projects/dhg-ai-factory/` and Docusaurus picks it up. Do NOT create a manual sidebar .ts file — Docusaurus never loads it.

### Memory Pipeline Ingest

5. **Push ship session to the registry** (single capture path — per `.claude/rules/auto-ship-session-capture.md`; do NOT also POST /api/v1/ship_sessions directly):
   ```bash
   ~/.claude/scripts/post-ship-session.sh '{"project_name":"dhg-ai-factory","feature":"[description]","approach":"[chosen approach summary]","status":"complete","complexity":"[simple|complex]","tdd":[true|false|null],"pr_url":"[PR URL or null]","branch":"[branch]","completed_at":"[ISO 8601]","commits":["[hash] [msg]"],"deferred":["[item]"],"decisions":["[item]"],"review":{"agents":["[agents used]"],"critical_found":[N],"important_found":[N]},"verification":{"typecheck":"[result]","tests":"[summary]","lint":"[result]"},"tags":["[tag]"],"model_name":"[current session model ID — never hardcode]"}'
   ```
   The script is fire-and-forget (exits 0 on failure) — if the registry is down, note it in the Phase 8 summary; the ship log markdown is the primary record.

6. **Present documentation summary:**
   ```
   Documented:
   - Ship log: docs-site/projects/dhg-ai-factory/ship-log/NNN-slug.md
   - Feature docs: [list of pages created/updated, or "none needed"]
   - Sidebar: [updated / no changes]
   - Registry: [ingested / failed (warning shown)]
   ```

**Output:** Ship log entry + feature docs (if applicable) + sidebar update + registry ingest.

Update `.claude/ship-state.md`: add documentation outputs; **set `phase: 8`**.

> **Phase 7 complete. Continue to Phase 8 (Ship)?**

---

## Phase 8: Ship

**Goal:** Get it merged.

1. **Stage and commit** all remaining changes from Phase 6 fixes and Phase 7 documentation.

2. **Apply CLAUDE.md update** (if drafted in Phase 6 and approved). Include in the final commit.

3. **Push and create PR:**
   - If not already pushed, push the branch with `-u`
   - **[Failure protocol]** If the push is rejected (diverged remote): `git fetch`, then rebase onto the updated remote if the divergence is trivial; if the rebase conflicts or the divergence is not trivial, HALT and show Stephen the situation. If `gh pr create` fails (auth, duplicate PR, rate limit): show the exact stderr and HALT for Stephen — do not retry blindly and do not report the ship as complete without a PR URL (mirror the session-logger failure handling in step 5).
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

     ## Dev tool results
     - tdd-guard: [active/inactive, enforcement events during build]
     - AgentShield: [grade, new findings vs baseline]
     - claudekit doctor: [pass/issues found and resolved]

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
   RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://10.0.0.251:8009/sessions/ingest-log \
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

**Gate exception for skip:** skipping INTO Phase 4 or beyond (from "skip" at Phase 3 or "skip to N≥4") is only valid when `.claude/ship-state.md` already contains BOTH the Phase 3 plan artifact AND an `approved:` frontmatter line. If either is missing, refuse: **"Phase 3 gate not crossed — there is no approved plan. Complete Phase 3 or give explicit build approval first."** Skip is navigation, not approval; it cannot cross the hard gate on its own.

---

## Dev Tools Reference

| Tool | Integrated At | What It Does |
|------|--------------|--------------|
| **tdd-guard** | Phase 3 (TDD decision), Phase 4 (build enforcement) | PreToolUse hooks block code edits without corresponding tests when TDD is enabled |
| **AgentShield** | Phase 5 (verify) | Security audit of `.claude/` config — catches permission gaps, secret exposure, hook issues. Compares against project baseline. |
| **claudekit doctor** | Phase 4 (pre-build health check) | Validates project hook/command configuration |
| **ccpm** | On-demand | Spec-driven PM skill — PRDs, epics, GitHub issue sync. Invoke with `/ccpm` if the feature warrants formal PM tracking |

---

## Version History
- **v1** (2026-03-13): Initial 7-phase workflow. Saved as `ship_v1.md`.
- **v2** (2026-03-13): Full capability restoration + 14 additions. Restored: spec iterations, divergent thinking, 6 review agents, code in plans, chunk review, TodoWrite, subagent reconciliation. Added: resume detection, state persistence, scope creep guard, rollback fields, debugging escalation, complexity-conditional spec, architecture step, TDD toggle, CLAUDE.md update check, observability check, deploy order, post-merge monitoring, performance baselines, actionable monitor section.
- **v3** (2026-05-19): Divergent-convergent redesign + documentation phase + grounded brainstorm + advisor review gates. Now 8 phases. Phase 1: dynamic feasibility (reads CLAUDE.md, no hardcoded issues), explore scope gating with recommendation + pause. Phase 2: full rewrite — 3 agents shift from inventory to divergent discovery (analogous solutions + abandoned prior art, assumption audit with 4 category probes, adjacent systems + opportunities), 5 synthesis outputs (file map, assumption audit, unexpected connections, approach pressure test, park list), bounded feedback loop to Phase 1 (2-pass max circuit breaker), prescriptive endings ("This means we should..."), agent conflict resolution. Phase 4: branch naming auto-suggestion (feat/fix/refactor prefix + slug). Phase 6: review depth scales by diff size (single reviewer ≤3 files, 6-agent army for 4+). **Phase 7 (NEW): Document** — auto-generates ship log entry (Portage format), feature documentation (API, architecture, frontend, monitoring pages when warranted), updates docs-site sidebar, pushes to registry memory pipeline. Phase 8 (was 7): session-logger POST error handling (warns on failure, no silent audit trail loss), PR template now includes Explore + Document phases, defer list + park list surfaced together.
- **v4** (2026-05-24): Dev tools integration on top of the v3 design (the file aifactory stored as `ship_v2.md` contained the v3 design; v4 built directly on it). Added: tdd-guard rule + Phase 3 TDD-decision awareness + Phase 4 step 4c PreToolUse enforcement; `claudekit doctor` as Phase 4 step 2 (pre-build health check); AgentShield (`npx ecc-agentshield scan`) as Phase 5 step 5 with baseline comparison; AgentShield line in Phase 5 verdict; "Dev tool results" section added to Phase 8 PR template; ccpm referenced as on-demand skill in Dev Tools Reference. **Dependencies:** tdd-guard plugin, ecc-agentshield (npm), claudekit, and the **pr-review-toolkit plugin** (Phase 6's six named review agents) must be installed/enabled in aifactory for these steps to run; ccpm skill is already installed.
- **v5** (2026-07-04): Promoted to `/ship` (canonical). ship_v1/v2/v4 + prior ship.md (v2-baseline) archived to `.claude/archive/commands/` — no longer invocable. Fixes: single ship-session capture path via `post-ship-session.sh` with the `auto-ship-session-capture.md` schema (removed raw /api/v1/ship_sessions curl and its drifted field names); `localhost:8009` → `10.0.0.251:8009` (session-logger, verified live) plus remaining localhost URLs; pinned `ecc-agentshield@1.4.0`; renumbered Phase 4 duplicate step 5s (steps now 1–9); capture `model_name` = current session model ID, never a literal.
