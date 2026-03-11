# Session Handoff — 2026-03-11 (Session 2)

<original_task>
Continue work on the `feat/human-review-loop` branch. This session covered:
1. Live-testing agents from the frontend chat UI
2. Diagnosing/fixing the "agents ignore user topic" bug (researched measles instead of obesity)
3. Creating shared modules (extract_topic.py, pubmed_client.py) and upgrading all 9 content agents
4. Updating the superpowers implementation plan to reflect all completed work
</original_task>

<work_completed>
## Agent Chat Integration (bulk of session)

### Bug: Agents Ignored User Topic
- User asked research agent about obesity, it researched measles instead
- Root cause: Frontend sends `messages[]` but agents read `disease_state` (empty string). PubMed query became generic "epidemiology prevalence incidence"
- Fix: Created shared `extract_topic_node` as entry point for all agents

### Created: `langgraph_workflows/dhg-agents-cloud/src/extract_topic.py`
- Shared topic extraction module using Claude Sonnet
- Parses free-text chat messages into: disease_state, therapeutic_area, target_audience, geographic_focus
- 23 therapeutic areas including obesity_medicine, orthopedics, pediatrics, geriatrics
- Explicit specialty mapping rules (obesity → obesity_medicine/endocrinology, NOT rheumatology)
- No-op when disease_state already populated (structured intake path)
- Tracks token usage and cost

### Created: `langgraph_workflows/dhg-agents-cloud/src/pubmed_client.py`
- Shared PubMed E-Utils client extracted from research_agent.py
- `search()` — searches PubMed, returns PMIDs
- `fetch_details()` — fetches full article metadata (journal_abbrev, volume, issue, pages, DOI, authors, pub_types)
- `format_ama()` — AMA citation formatting with DOI and PubMed URL

### Modified: All 9 Content Agents
Each agent received 4 changes:
1. **extract_topic_node wired as graph entry point** — `from extract_topic import extract_topic_node`
2. **Inline citation instructions in system prompts** — "Use numbered inline references [1], [2], [3] etc. Do NOT include a references list at the end of your section."
3. **generate_references_node added** — Regex-based citation extraction, PubMed search/verify, AMA formatting, [UNVERIFIED] flags. NO LLM call (avoids messages-tuple streaming leak)
4. **Full document emitted to chat** — Final node returns `"messages": [HumanMessage(content=f"---\n\n# Complete {Title}\n\n{document}")]`

Agents modified:
- `needs_assessment_agent.py` — doc field: `complete_document`, title: "Needs Assessment Document"
- `research_agent.py` — doc field: `research_document`, title: "Research Report"
- `clinical_practice_agent.py` — doc field: `clinical_practice_document`, title: "Clinical Practice Analysis"
- `gap_analysis_agent.py` — doc field: `gap_analysis_document`, title: "Gap Analysis"
- `learning_objectives_agent.py` — doc field: `learning_objectives_document`, title: "Learning Objectives"
- `curriculum_design_agent.py` — doc field: `curriculum_document`, title: "Curriculum Design"
- `research_protocol_agent.py` — doc field: `protocol_document`, title: "Research Protocol"
- `marketing_plan_agent.py` — doc field: `marketing_document`, title: "Marketing Plan"
- `grant_writer_agent.py` — doc field: `complete_document_markdown`, title: "Grant Package" (uses therapeutic_area for PubMed queries)

### Plan Update: `docs/superpowers/plans/2026-03-10-human-review-loop.md`
- Added Progress Status table with commit hashes and status
- Added Test Results section (67/67 passing, docker exec command)
- Marked all checkboxes [x] for Tasks 1-20
- Task 21 Steps 1-3 done, Steps 4-6 (merge/push/verify) left [ ]
- All Task and Chunk headers marked with ✅ or 🔄
- Added Chunk 5 (Tasks 22-24) for agent chat integration
- Updated File Map with new shared modules
- Updated Summary table with all 6 chunks
</work_completed>

<work_remaining>
## Immediate: Commit Uncommitted Work
```bash
git add langgraph_workflows/dhg-agents-cloud/src/extract_topic.py \
        langgraph_workflows/dhg-agents-cloud/src/pubmed_client.py \
        langgraph_workflows/dhg-agents-cloud/src/needs_assessment_agent.py \
        langgraph_workflows/dhg-agents-cloud/src/research_agent.py \
        langgraph_workflows/dhg-agents-cloud/src/clinical_practice_agent.py \
        langgraph_workflows/dhg-agents-cloud/src/gap_analysis_agent.py \
        langgraph_workflows/dhg-agents-cloud/src/learning_objectives_agent.py \
        langgraph_workflows/dhg-agents-cloud/src/curriculum_design_agent.py \
        langgraph_workflows/dhg-agents-cloud/src/research_protocol_agent.py \
        langgraph_workflows/dhg-agents-cloud/src/marketing_plan_agent.py \
        langgraph_workflows/dhg-agents-cloud/src/grant_writer_agent.py \
        docs/superpowers/plans/2026-03-10-human-review-loop.md
```

## Task 21: Merge (held per Stephen)
- Step 4: Merge feat/human-review-loop to master
- Step 5: Push to origin
- Step 6: Verify LangSmith Cloud

## Known Issues
1. **PubMed search quality** — Full sentence context queries return generic/wrong articles (e.g., vegetarian nutrition for CKD). Need to extract key medical terms only.
2. **Duplicate references** — Same PMID matched to multiple citation contexts appears multiple times. Need deduplication by PMID.
3. **No tests for new functionality** — 67 orchestrator tests pass, but no tests for extract_topic, pubmed_client, or generate_references_node.
4. **Pytest only runs inside container** — `docker exec dhg-cme-research-agent python3 -m pytest`
</work_remaining>

<attempted_approaches>
## Bug Diagnosis: Measles Instead of Obesity
1. Read container logs → saw PubMed queries without topic terms
2. Traced data flow: frontend chatApi.ts → messages-tuple → agent state → `state.get("disease_state", "")` returning empty
3. Hypothesis 1 (approved by user): Add extraction node to parse messages into structured fields
4. First extraction returned wrong specialty (rheumatology for obesity). Fixed by expanding THERAPEUTIC_AREAS and adding explicit mapping rules in prompt.

## References Evolution (3 iterations)
1. **Per-section references** — Each agent section included its own REFERENCES block. User said "references should all appear at the end in one section." Fixed by changing prompts to "Do NOT include a references list" + dedicated generate_references_node.
2. **LLM-based citation extraction** — Used ChatAnthropic in generate_references_node to extract citation queries. Leaked raw JSON to chat UI via messages-tuple streaming. Fixed by switching to regex-based extraction (no LLM call).
3. **References disappeared from chat** — After removing LLM call, node had no mechanism to emit content. Thread state had the data but chat showed nothing. Fixed by adding `"messages": [HumanMessage(content=...)]` to return dict with full document.

## Plan Update Approaches
1. Individual checkbox edits — Too slow, user rejected after 8 edits
2. Python script bulk replacement — User rejected the bash execution
3. Edit tool with replace_all — Worked: `replace_all: true` to flip all `- [ ] **Step` to `- [x] **Step`

## Key Lesson
Stephen said: "do not ever ignore a direction from me or choose to do something else first." When directed to read session logs, do that FIRST before trying alternatives.
</attempted_approaches>

<critical_context>
## Branch Strategy
- Branch: `feat/human-review-loop` — 4 commits ahead of master + uncommitted work
- Stephen explicitly: "i dont want to merge this want to maintain the master as is and keep this on a branch until i see it working, beyond your tests"
- Merge ONLY when Stephen explicitly approves

## How to Run Tests
```bash
docker cp .../src/orchestrator.py dhg-cme-research-agent:/app/src/orchestrator.py
docker cp .../tests dhg-cme-research-agent:/app/tests
docker exec dhg-cme-research-agent rm -rf /app/src/__pycache__ /app/tests/__pycache__
docker exec dhg-cme-research-agent python3 -m pytest /app/tests/test_orchestrator.py -v --tb=short
```
Last result: 67 passed, 0 failed

## Messages-Tuple Streaming Leak
LangGraph `messages-tuple` streaming mode streams ALL ChatAnthropic LLM calls within nodes to the frontend — including internal/intermediate calls. This is why generate_references_node uses regex-based extraction instead of an LLM call.

## Commits on Branch
1. `314f75d` — Tasks 1-6: interrupt() in needs_package, process_review_feedback, tests (57→67)
2. `797b3f5` — Tasks 7-14: ReviewPanel, DocumentViewer, useAnnotations, CommentsSidebar, MetricsBar, DecisionBar
3. `7af1b9e` — Task 15: Replicated interrupt to all 4 recipes
4. `a7380bb` — Tasks 16-20: /studio route, alerts, webhook, frontend port fix

## Service Ports
- 2026: LangGraph (dhg-cme-research-agent) — healthy
- 3002: Frontend (Next.js) — healthy
- 8011: Registry API — healthy
- 9090: Prometheus — healthy
- 3001: Grafana — healthy

## User Preferences (reinforced this session)
- Never ignore a direct instruction or do something else first
- Don't ask for repeated approval during bulk work
- Bills at $450/hr
- Verify claims against evidence (session logs, git history), don't guess

## Session Log Location
JSONL files at: `/home/swebber64/.claude/projects/-home-swebber64-DHG-aifactory3-5-dhgaifactory3-5/`
- This session: `ccf6173a-12bc-4b27-a580-1c2357555261.jsonl`
- Implementation session: `6d70ba02-5ba3-4f86-a792-23ef3bcf2c1e.jsonl`
</critical_context>

<current_state>
## Git State
- Branch: `feat/human-review-loop`
- 4 commits ahead of master
- **Uncommitted:** 9 modified agents + 2 new files (extract_topic.py, pubmed_client.py) + updated plan
- Working tree is NOT clean

## What's Live
- All agent changes are live on LangGraph server via hot-reload (watchfiles)
- Frontend builds and serves on port 3002 (5 routes: /, /inbox, /studio, /api/copilotkit)
- 67/67 tests passing (orchestrator tests only)

## What's NOT Done
- Uncommitted work not committed
- No tests for extract_topic, pubmed_client, generate_references
- PubMed search quality issues (generic results, duplicates)
- Merge to master held

## Next Actions
1. Commit the uncommitted agent chat integration work
2. Run tests to verify no regressions
3. Address PubMed search quality and duplicate references
4. When Stephen approves: merge to master
</current_state>
