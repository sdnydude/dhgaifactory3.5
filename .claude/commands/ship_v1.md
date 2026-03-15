# /ship — Full Feature Shipping Workflow

You are running a 7-phase workflow to take a feature from idea to merged PR. This is the DHG AI Factory's production shipping process. Every phase builds on the previous one and carries context forward — do NOT re-explore or re-ask what was already established.

The user may have provided a feature description: $ARGUMENTS

If no arguments were provided, ask: **"What are we shipping?"** and wait.

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

## Phase 1: Brainstorm

**Goal:** Understand the problem, explore approaches, choose a direction.

1. Read CLAUDE.md to load full project context (architecture, known issues, tech stack).

2. **Feasibility check.** Before any design work, check if this feature conflicts with known critical issues:
   - C1: Port 8011 conflict (orchestrator vs registry-api)
   - C2: Web-UI cannot reach LangGraph (no integration code)
   - C3: LangGraph network isolation (wrong registry URL, separate Docker network)
   - C4: Infisical crash-looping
   - C5: Hardcoded IPs in web-ui
   - C7: No CI/CD
   - C8: Minimal test coverage
   - C10: Loki has no log ingestion
   If conflicts exist, flag them immediately: "This feature touches [issue]. Here's how we handle it: [approach]."

3. **Ask clarifying questions.** One at a time. Multiple choice where possible. Do not ask more than 3 questions total — use judgment for the rest.

4. **Propose 2-3 approaches** with tradeoffs. Include:
   - What each approach changes
   - Risk level (low / medium / high)
   - Which known issues it interacts with
   - Your recommendation and why

5. Get user approval on the approach. If the user says "you decide" or "whatever you think", state your recommendation explicitly and confirm: "Going with [approach]. Correct?"

**Output:** Chosen approach + key constraints identified.

> **Phase 1 complete. Continue to Phase 2 (Explore), or skip?**

---

## Phase 2: Explore

**Goal:** Map the relevant codebase once. Every later phase uses these findings — no re-exploration.

1. Launch 2-3 explorer agents in parallel using the Agent tool (subagent_type: Explore). Each agent targets a different area:
   - Agent 1: The files that will be modified (read them, understand current state)
   - Agent 2: Related patterns and utilities that can be reused
   - Agent 3: Tests, configs, and dependencies that will be affected

2. When agents return, synthesize into a **file map**:
   ```
   Files to modify:
     - path/to/file.py (what it does, what changes)
   Files to reuse:
     - path/to/util.py (function X does what we need)
   Files affected:
     - docker-compose.override.yml (needs new env var)
     - tests/test_x.py (needs new test case)
   ```

3. Flag anything surprising: "Expected X but found Y. This changes the approach because..."

**Output:** File map + pattern inventory + surprises.

> **Phase 2 complete. Continue to Phase 3 (Plan), or skip?**

---

## Phase 3: Plan

**Goal:** Break the work into bite-sized tasks with exact file paths, risk flags, and verification steps.

1. Write the plan as a numbered task list. Each task should take 2-5 minutes. Each task includes:
   - **Files:** Exact paths to read/modify/create
   - **Do:** What to implement (specific, not vague)
   - **Verify:** How to prove it works (command to run, output to expect)
   - **Risk:** low / medium / high + blast radius (local / service / cross-service)

   Example:
   ```
   Task 3: Add /sessions/stats endpoint
     Files: services/session-logger/main.py
     Do: Add GET endpoint that queries session_logs count, avg log size, date range
     Verify: curl -s http://localhost:8009/sessions/stats | python3 -m json.tool
     Risk: low (local — new endpoint, no existing behavior changed)
   ```

2. **Order tasks by dependency.** Independent tasks can be marked as parallelizable.

3. **Identify tasks that touch shared state** (database schemas, Docker configs, shared libraries). These get "medium" or "high" risk automatically.

4. Apply DRY, YAGNI. If something already exists in the codebase (found in Phase 2), reuse it. Do not build what you found.

**HARD GATE:** Present the plan and wait for user approval. Do not proceed to Phase 4 without explicit "go", "approved", "build it", or similar.

**Output:** Approved task list.

> **Phase 3 approved. Continue to Phase 4 (Build)?**

---

## Phase 4: Build

**Goal:** Execute the plan. Follow it exactly. Commit after each task.

1. **Branch check.** Run `git branch --show-current`. If on `master` or `main`, stop and ask: "You're on master. Create a feature branch, or proceed on master?" Do not proceed without explicit answer.

2. For each task in the plan:
   a. Announce: **"Task N/total: [description]"**
   b. Read the files listed in the task (view before edit — always)
   c. Implement exactly what the plan says
   d. Run the verification command from the plan
   e. If verification passes, commit with a descriptive message
   f. If verification fails, diagnose (one fix per hypothesis), fix, re-verify
   g. If tests exist for the affected code, run them. Report result.

3. **Parallel execution.** If the plan marked tasks as parallelizable, dispatch them as parallel agents using the Agent tool. Each agent gets: the task description, file paths, verification command, and the instruction "commit when done."

4. **Stop when blocked.** If something unexpected happens, do not guess or force through. State what's wrong and ask the user.

5. After all tasks complete, show a summary:
   ```
   Built: N/N tasks complete
   Commits: [list of commit messages]
   Tests: X passed, Y failed, Z skipped
   ```

**Output:** All tasks implemented, verified, and committed.

> **Phase 4 complete. Continue to Phase 5 (Verify), or skip?**

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

5. **State the verdict with evidence:**
   - "All N verification commands pass. Output: [shown above]"
   - "Tests: X/Y pass. Failures: [list with details]"
   - "Services: all healthy. Evidence: [docker ps output]"

   If anything fails, go back to Phase 4 for that specific task. Do not proceed to review with known failures.

**Output:** Verification evidence showing everything works.

> **Phase 5 complete. All checks pass. Continue to Phase 6 (Review), or skip?**

---

## Phase 6: Review

**Goal:** Catch issues before shipping. Fix them, don't just report them.

1. **Run a diff review.** Look at the full diff (`git diff` against the base branch) and check:
   - Security: SQL injection, XSS, command injection, exposed secrets
   - Performance: N+1 queries, missing indexes, unbounded loops
   - Config safety: magic numbers, hardcoded values, missing env vars
   - Conventions: matches existing patterns in the codebase

2. **DHG-specific checks:**
   - Docker: Does this need a new container? Network membership correct? Port conflict with anything in CLAUDE.md's port table?
   - Database: Migration needed? Backward compatible? ON DELETE behavior correct?
   - CLAUDE.md compliance: Does the change align with documented architecture?
   - Brand: If UI work, does it use semantic tokens (not raw hex)?

3. **Severity classification:**
   - **Critical** — blocks shipping (security vulnerability, data loss risk, broken functionality)
   - **Important** — should fix before merge (code quality, missing validation, config concern)
   - **Minor** — note for later (style nit, optimization opportunity)

4. **Fix-and-re-verify loop.** For each Critical and Important issue:
   a. State the issue and the fix
   b. Apply the fix
   c. Re-run the relevant verification from Phase 5
   d. Confirm it passes

**HARD GATE:** All Critical issues must be resolved. Important issues should be resolved. Only proceed with unresolved Important issues if the user explicitly approves.

**Output:** Review complete, all issues resolved (or user-approved exceptions).

> **Phase 6 complete. Ready to ship. Continue to Phase 7?**

---

## Phase 7: Ship

**Goal:** Get it merged. Document what was done.

1. **Stage and commit** any remaining changes from Phase 6 fixes.

2. **Push and create PR:**
   - If not already pushed, push the branch with `-u`
   - Create PR using `gh pr create` with this structure:
     ```
     Title: [concise description, under 70 chars]

     ## Summary
     [2-3 bullet points of what was built]

     ## Phases completed
     - Brainstorm: [approach chosen]
     - Plan: [N tasks]
     - Build: [N commits]
     - Verify: [all checks pass]
     - Review: [N issues found and fixed]

     ## Test plan
     - [ ] [verification steps someone else can follow]

     ## Risk
     [blast radius: local/service/cross-service]
     [what to monitor after merge]
     ```

3. **Log to session-logger.** Submit a summary of this workflow:
   ```bash
   curl -s -X POST http://localhost:8009/sessions/ingest-log \
     -H "Content-Type: application/json" \
     -d '{"hostname":"g700data1","username":"swebber64","raw_log":"[summary of phases, tasks, decisions, PR URL]"}'
   ```

4. **Present the PR URL** to the user.

> **Shipped. PR: [URL]**

---

## Navigation Commands

The user can say these at any time:
- **"skip"** — jump to the next phase
- **"skip to N"** — jump directly to phase N
- **"stop"** — exit the workflow
- **"back"** — return to the previous phase
- **"status"** — show which phase we're in and what's done
