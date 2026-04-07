# Session Handoff — 2026-03-14 (VS Engine Plan Complete, Ready to Execute)

**Date:** 2026-03-14
**Branch:** `feature/langgraph-migration`
**Last Commit:** `d792e5d` (no new commits — planning phase only)

---

<original_task>
Build the `dhg-vs-engine` — a standalone Docker service (FastAPI, port 8013) that provides divergent generation via Verbalized Sampling, integrated into the DHG AI Factory's LangGraph agent pipeline, frontend inbox, and Grafana observability stack.

This started as a brainstorming session where Stephen adopted Verbalized Sampling (from CHATS-lab, arXiv 2510.01171) as the core divergent-convergent mechanism for the DHG AI Factory. The brainstorming produced a 19-section design spec, which was then turned into a comprehensive implementation plan. Stephen explicitly required that LangGraph integration, the frontend inbox, and Grafana dashboards be included in a SINGLE plan — not deferred.

The plan was approved by Stephen on 2026-03-14 and execution was about to begin using the subagent-driven-development workflow when the session ended.
</original_task>

<work_completed>
## 1. Design Spec (COMPLETE)
- **File:** `docs/superpowers/specs/2026-03-14-verbalized-sampling-engine-design.md`
- 19 sections covering architecture, API contracts, error handling, evaluation framework, phase defaults, human review UX, testing strategy, and attribution
- Two-parameter tau design: `tau` (soft prompt ceiling) + `min_probability` (postprocess floor)
- DiversityEvaluator + TTCTEvaluator adopted; CreativityIndexEvaluator deferred
- Reviewed via spec-document-reviewer subagent, approved by Stephen

## 2. Implementation Plan (COMPLETE — review-clean)
- **File:** `docs/superpowers/plans/2026-03-14-vs-engine.md`
- 23 tasks (0-22) across 7 chunks, ~88 tests, 15 new files, 7 modified files
- Three rounds of plan review (3 parallel reviewer subagents per round)
- All critical/important/suggestion issues resolved across all chunks

### Chunk breakdown:
| Chunk | Tasks | Scope |
|-------|-------|-------|
| 1: Core Math | 0-4 | conftest.py, distribution.py, config.py, prompt_builder.py, selection.py (44 tests) |
| 2: API + Infra | 5-9 | llm_router.py, main.py, Dockerfile, requirements.txt, docker-compose, prometheus (16 tests) |
| 3: Evaluation | 10-12 | evaluators/diversity.py, evaluators/ttct.py, /vs/evaluate endpoint (18 tests) |
| 4: Cloudflare + Smoke | 13-14 | Cloudflare tunnel route, service smoke test |
| 5: LangGraph Integration | 15-17 | vs_client.py, gap_analysis_agent.py pilot, orchestrator passthrough (10 tests) |
| 6: Frontend Inbox | 18-20 | VS types, vs-alternatives.tsx component, ReviewPanel integration |
| 7: Grafana + E2E | 21-22 | vs-engine.json dashboard (10 panels), end-to-end smoke test |

## 3. Plan Review Issues Fixed (ALL RESOLVED)

### Chunks 1-4 (first review round — 12 issues):
- conftest.py ordering moved to Task 0
- repair_weight NaN/Inf behavior aligned with spec
- postprocess_responses return type documented
- Field naming convention documented (internal text/p/meta → API content/probability/metadata)
- Three-tier exception handling in main.py (ConnectError→503, TimeoutException→503, Exception→502)
- Error path tests added (4 tests)
- /vs/evaluate error handling (503 for TTCT-only failure, 200 partial for mixed)
- Evaluate tests expanded (4 more tests)
- DiscreteDist edge case tests added
- Metrics test assertions made strict
- TTCT response format aligned (combined justification string)
- Smoke test expanded with /vs/evaluate step

### Chunk 5 (second review round — 6 issues fixed):
- Client timeout: 30s → 120s to match server-side spec
- Token/cost tracking: documented as intentionally tracked via VS engine Prometheus, not agent-level
- vs_distribution flow: changed from dead top-level CMEPipelineState field to nested `gap_analysis_output["vs_distribution"]` path (Option A)
- Cloud deployment: added note about VS_ENGINE_URL=https://vs.digitalharmonyai.com for LangGraph Cloud
- Missing error tests: added 3 tests (HTTP 502, timeout, malformed JSON) — now 10 total
- Removed undocumented `seed` parameter from vs_select

### Chunk 6 (second review round — 8 issues fixed):
- Added `quality_score?: number | null` to VSItem.metadata
- Replaced Tailwind colors with DHG brand tokens (bg-dhg-purple/10, bg-dhg-orange/10, bg-dhg-graphite/10)
- Replaced unused `selectedIndex` with `onSelect` callback + `isAutoSelected` visual indicator
- Added explicit instruction to change local variable type in inboxApi.ts (line 33)
- Replaced additive char sum with djb2-style multiplicative hash for shuffle seed
- Added `onSelect` callback prop and click handler on cards
- CRITICAL: Moved VS alternatives panel OUTSIDE flex container (between line 83 and mobile sidebar)

### Chunk 7 (second review round — 6 issues fixed):
- Added datasource UID verification step
- Added `"refresh": "15s"` to dashboard JSON
- Fixed 4 diversity/TTCT queries: `sum(...) by (le, phase)` for correct histogram_quantile
- Fixed 3 generation duration queries: `sum(...) by (le)`
- Documented VS-vs-baseline panel as deferred in "Not included" section
- Expanded smoke test metrics grep to check 5 metrics

## 4. Memory Updated
- **File:** `~/.claude/projects/-home-swebber64-DHG-aifactory3-5-dhgaifactory3-5/memory/project_verbalized_sampling.md`
- Updated with two-parameter design, evaluation framework, implementation approach (~650 lines), LLM strategy, human review UX

## 5. CHATS-lab Source Code Analyzed
- Cloned to `/tmp/verbalized-sampling/` (temporary, not in repo)
- Key files read: `selection.py` (453 lines — Item, DiscreteDist, repair_weight, postprocess_responses), `api.py` (verbalize function, two-parameter design), `methods/prompt.py` (probability_tuning prompt), `analysis/evals/diversity.py` (DiversityEvaluator, 301 lines), `analysis/evals/quality.py` (TTCTEvaluator, 296 lines)
- TTCT weight discrepancy noted: prompt text says 20/30/30/20 but code uses 25/25/25/25 — DHG uses 25/25/25/25
</work_completed>

<work_remaining>
## EXECUTE THE PLAN — 23 tasks, none started

**Execution method:** Use `superpowers:subagent-driven-development` skill
- Fresh subagent per task + two-stage review (spec compliance, then code quality)
- Plan file: `docs/superpowers/plans/2026-03-14-vs-engine.md`
- Spec file: `docs/superpowers/specs/2026-03-14-verbalized-sampling-engine-design.md`

### Task-by-task (all pending):

**Chunk 1: Core Math**
- Task 0: Create `services/vs-engine/tests/__init__.py` + `conftest.py` (test infrastructure — MUST be first)
- Task 1: Create `services/vs-engine/distribution.py` + `tests/test_distribution.py` (29 unit tests)
- Task 2: Create `services/vs-engine/config.py` + `tests/test_config.py` (7 tests)
- Task 3: Create `services/vs-engine/prompt_builder.py` + `tests/test_prompt.py` (6 tests)
- Task 4: Create `services/vs-engine/selection.py` + `tests/test_selection.py` (6 tests)

**Chunk 2: API + Infra**
- Task 5: Create `services/vs-engine/llm_router.py` (no tests — tested via integration)
- Task 7: Create `services/vs-engine/main.py` + `tests/test_api.py` (16 tests including error paths)
- Task 8: Create `services/vs-engine/Dockerfile` + `requirements.txt`
- Task 9: Modify `docker-compose.override.yml` + `observability/prometheus/prometheus.yml`

**Chunk 3: Evaluation**
- Task 10: Create `services/vs-engine/evaluators/__init__.py` + `evaluators/diversity.py` + `tests/test_diversity.py` (6 tests)
- Task 11: Create `services/vs-engine/evaluators/ttct.py` + `tests/test_ttct.py` (6 tests)
- Task 12: Add `/vs/evaluate` endpoint to `main.py` + tests to `test_api.py` (6 tests)

**Chunk 4: Cloudflare + Smoke**
- Task 13: Modify `/etc/cloudflared/config.yml` — add `vs.digitalharmonyai.com` route + DNS CNAME
- Task 14: Smoke test — build, start, verify health/generate/select/evaluate/metrics

**Chunk 5: LangGraph Integration**
- Task 15: Create `langgraph_workflows/dhg-agents-cloud/src/vs_client.py` + `tests/test_vs_client.py` (10 tests)
- Task 16: Modify `gap_analysis_agent.py` (VS in identify_gaps_node) + modify LangGraph `docker-compose.yml` (VS_ENGINE_URL env var)
- Task 17: Modify `orchestrator.py` (human_review_node reads VS from nested gap_analysis_output)

**Chunk 6: Frontend Inbox**
- Task 18: Modify `frontend/src/components/review/types.ts` (add VSItem, VSDistribution, ReviewPayloadWithVS)
- Task 19: Create `frontend/src/components/review/vs-alternatives.tsx` (shuffled cards, DHG brand badges, onSelect, isAutoSelected)
- Task 20: Modify `review-panel.tsx`, `inbox-item.tsx`, `inboxApi.ts` (wire VS alternatives into existing inbox)

**Chunk 7: Grafana + E2E**
- Task 21: Create `observability/grafana/provisioning/dashboards/json/vs-engine.json` (10 panels, 3 rows)
- Task 22: End-to-end integration smoke test (10 steps)

### Model selection guidance for subagents:
- Tasks 0-4: sonnet (pure math, well-specified, isolated files)
- Tasks 5-9: sonnet (API + infra, moderate integration)
- Tasks 10-12: sonnet (evaluation, well-specified)
- Tasks 13-14: sonnet (infra, straightforward)
- Tasks 15-17: opus (multi-file integration, LangGraph patterns, architectural judgment)
- Tasks 18-20: sonnet (frontend, clear component boundaries)
- Tasks 21-22: sonnet (Grafana JSON, smoke test)
</work_remaining>

<attempted_approaches>
## Approaches that succeeded:
1. **Brainstorming skill → writing-plans skill pipeline** — worked cleanly, produced a comprehensive spec and plan
2. **Three parallel reviewer subagents** — efficient, caught 12 issues in Chunks 1-4, 20 issues across Chunks 5-7
3. **Two-parameter tau design** — resolved CHATS-lab naming confusion (their `probability_tuning` ≠ their `tau`)
4. **Option A for VS distribution flow** — read from nested `gap_analysis_output["vs_distribution"]` instead of dead top-level field, scales to multiple agents

## Issues encountered and resolved:
1. **Stephen's frustration with deferred work** — initial plan deferred LangGraph/inbox/Grafana to "separate plans." Stephen: "why. dont we need langraph inegration to test? I am done with you putting off rhe inbox." Fixed by adding Chunks 5-7.
2. **CSS layout bug (Issue 8, Chunk 6)** — VS alternatives panel was placed INSIDE a `flex flex-1` row, creating a broken third column. Fixed by moving it outside the flex container.
3. **PromQL correctness (Issues 3-4, Chunk 7)** — histogram_quantile without `sum by (le)` produces incorrect results when histograms have labels. Fixed all 7 affected expressions.
4. **Client timeout mismatch** — vs_client defaulted to 30s but server timeout is 120s (Ollama qwen3:14b with k=5 takes 30-60s). Fixed to 120s.

## Dead ends to avoid:
- Do NOT add a top-level `vs_distribution` field to `CMEPipelineState` — it creates a dead field. Use nested path access instead.
- Do NOT use additive char code sums for shuffle seeds — use multiplicative hash (djb2-style).
- Do NOT use arbitrary Tailwind colors for confidence badges — must use DHG brand tokens per `.claude/rules/dhg-brand.md`.
- Do NOT put VS alternatives panel inside the ReviewPanel's `flex flex-1` container — it must go between the flex container and the mobile sidebar.
</attempted_approaches>

<critical_context>
## Key architectural decisions:
1. **VS engine is a standalone Docker service** (port 8013), NOT a Python library — bolt-on module for AI Factory
2. **Local-first LLM strategy** — Ollama via httpx for brainstorm/review/gap, Claude via SDK for high-stakes CME content
3. **Graceful degradation** — vs_client returns None when VS engine is unavailable, agents fall back to standard generation
4. **Two-parameter design:** `tau` = soft prompt ceiling (nudge LLM toward uniform), `min_probability` = postprocess floor (filter junk). DHG defaults: tau=0.08, min_p=0.03
5. **Evaluation framework:** DiversityEvaluator (embedding pairwise cosine via Ollama nomic-embed-text) + TTCTEvaluator (fluency/flexibility/originality/elaboration, 1-5 scale, LLM-as-judge). CreativityIndexEvaluator deferred.
6. **Human review UX:** Auto-select one output → "Show alternatives" expands unordered cards with confidence badges (conventional/novel/exploratory) + quality gate scores. Shuffled order eliminates center-stage bias.
7. **Token/cost tracking:** VS engine tracks its own LLM costs via Prometheus. Agent-level token tracking only covers non-VS generation. No double-counting.

## Cloud deployment:
- LangGraph agents run in cloud at `*.us.langgraph.app` — they CANNOT resolve Docker container names
- VS engine must be exposed via Cloudflare tunnel at `vs.digitalharmonyai.com`
- LangGraph Cloud env var: `VS_ENGINE_URL=https://vs.digitalharmonyai.com`
- Local dev env var: `VS_ENGINE_URL=http://dhg-vs-engine:8000`

## Source code reference:
- CHATS-lab repo cloned to `/tmp/verbalized-sampling/` (temporary, not in git)
- Apache 2.0 license — code is ported, not imported as dependency
- ~650 lines total ported: ~300 core math + ~350 evaluation

## Important field naming convention:
- Internal (Python): `Item.text`, `Item.p`, `Item.meta`
- API (JSON): `content`, `probability`, `metadata`
- This mapping is documented in the plan at Task 1

## Grafana datasource UID:
- Dashboard uses `"uid": "prometheus"` (lowercase)
- Existing dashboards are inconsistent (core-golden=lowercase, docker-overview=capitalized)
- Plan includes a verification step to normalize UID in provisioning YAML

## Stephen's preferences (from this session):
- "Overhead IS the quality" — never defer integration work to separate plans
- Fortune 500 execution standard
- Planning and building are SEPARATE PHASES — don't start coding until plan is approved
- He was specifically frustrated about the inbox being deferred — it was previously described as "not working"
- He explicitly reminded about Cloudflare setup — don't forget it
</critical_context>

<current_state>
## Status of deliverables:
- Design spec: **COMPLETE** (committed in prior session)
- Implementation plan: **COMPLETE, REVIEW-CLEAN, APPROVED** (in working tree, not yet committed)
- Implementation: **NOT STARTED** — 0 of 23 tasks begun
- No task tracking (TaskCreate) has been set up yet

## Git state:
- Branch: `feature/langgraph-migration`
- Modified files include: `CLAUDE.md`, `docs/TODO.md`, `findings.md`, `progress.md`, `task_plan.md`, `whats-next.md`, and several frontend files from prior monitoring dashboard work
- The plan file `docs/superpowers/plans/2026-03-14-vs-engine.md` is modified but not committed
- The spec file `docs/superpowers/specs/2026-03-14-verbalized-sampling-engine-design.md` was committed in a prior session

## What to do next (in order):
1. **Start fresh session** — context is nearly full
2. **Read plan file:** `docs/superpowers/plans/2026-03-14-vs-engine.md`
3. **Read spec file:** `docs/superpowers/specs/2026-03-14-verbalized-sampling-engine-design.md`
4. **Invoke skill:** `superpowers:subagent-driven-development`
5. **Create TaskCreate todos** for all 23 tasks with dependencies
6. **Begin dispatching implementer subagents** starting with Task 0
7. **Two-stage review after each task:** spec compliance → code quality
8. **After all 23 tasks:** dispatch final code reviewer, then use `superpowers:finishing-a-development-branch`

## Open questions:
- None — all design decisions are settled, plan is approved
</current_state>
