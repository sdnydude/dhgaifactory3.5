# P1 Implementation Design: Human Review Loop + Observability

**Date:** 2026-03-10
**Status:** Approved
**Approach:** Vertical Slice — `needs_package` end-to-end first, then replicate
**Branch:** `feat/human-review-loop`

---

## Decisions

| Decision | Choice |
|----------|--------|
| Frontend strategy | Evolve custom Next.js (no LangChain open-source tools) |
| Deployment model | Local dev (`:2026`) → GitHub → LangSmith Cloud LangGraph (prod) |
| Priority order | Human Review Loop → Frontend Polish → Observability |
| Interrupt scope | All 4 recipes get `interrupt()` at human review gates |
| Observability scope | Infrastructure monitoring + local dev tracing (Tempo) |
| Agent analytics | LangSmith dashboard directly (no custom integration) |
| Review UX | Text annotation — highlight to comment, agent receives positioned feedback |
| Branch strategy | Feature branch `feat/human-review-loop`, merge to master when verified |

---

## Architecture Context

- **Repo:** monorepo `dhgaifactory3.5` — agents, frontend, registry, observability all in one
- **Agent deployment:** Push to GitHub → webhook → LangSmith Cloud LangGraph (production)
- **Frontend deployment:** Docker container on g700data1 (port 3002)
- **Local dev:** LangGraph server on port 2026, frontend on port 3002
- **Production tracing:** LangSmith dashboard (smith.langchain.com)
- **Local tracing:** Tempo (dev debugging only)

---

## Phase 0: Housekeeping

- Commit all uncommitted work from previous session (migration work on master)
- Create feature branch `feat/human-review-loop` from master
- Run existing tests to establish baseline (68 tests in test_needs_assessment.py + test_orchestrator.py)
- Verify PostgresSaver checkpointer is active locally — `interrupt()` requires persistence. If not running, configure `langgraph-checkpoint-postgres` against `dhg-registry-db` on port 5432. Test with a simple graph that interrupts and resumes.

**Exit criteria:** Feature branch created, tests passing, checkpointer verified.

---

## Phase 1: Agent Interrupt — `needs_package`

**File:** `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py`

- Import `interrupt` from `langgraph.types`
- Replace `human_review_gate` node with `interrupt(review_payload)` in `needs_package` recipe
- Review payload contains: complete document, quality metrics (word count, prose density, QA pass/fail, banned patterns), agent metadata
- Resume handler reads `Command(resume=...)` value, routes to END (approved), revision agent (revision), or FAILED (rejected)
- Add `review_comments: List[Dict]` and `review_round: int` to `CMEPipelineState`
- Update existing orchestrator tests — `test_orchestrator.py` tests for `human_review_gate`, routing functions, and graph construction will break. Rewrite to test `interrupt()` behavior, resume with mock Command values, and verify routing on resume data instead of state fields.

**Verify:** LangGraph SDK call → thread enters `interrupted` → resume → correct routing.

**Exit criteria:** `needs_package` graph pauses at review point, resumes with all 3 decision types, tests updated and passing.

---

## Phase 2: Frontend Annotation UI

**Directory:** `frontend/src/components/`

**Component architecture:**
```
/inbox (page)
  └── InboxList                    (existing — polls interrupted threads)
       └── InboxItem               (existing — card with metadata)
            └── ReviewPanel        (NEW — full review experience)
                 ├── DocumentViewer (NEW — renders CME document as rich HTML)
                 │    └── AnnotationLayer (NEW — text selection → comment)
                 ├── CommentsSidebar (NEW — list of positioned comments)
                 ├── MetricsBar    (NEW — word count, prose density, QA badge)
                 └── DecisionBar   (existing buttons, enhanced)
```

**DocumentViewer:** Renders interrupt payload's `complete_document` (markdown) as styled HTML using existing `MarkdownText` component. Wraps in container listening for `mouseup` / `selectionchange`.

**AnnotationLayer:**
- On text selection, shows floating "Add Comment" button near selection
- On click, opens comment input popover
- Stores: `{ id, selectedText, startOffset, endOffset, comment, timestamp }`
- Highlights annotated text with colored background
- Multiple annotations supported

**CommentsSidebar:** Lists comments in document order. Click scrolls to annotated text. Editable/deletable before submission.

**MetricsBar:** Word count, prose density, QA pass/fail badges from interrupt payload.

**DecisionBar:** Approve/revise/reject. Packages annotations into resume command:
```typescript
Command(resume: {
  decision: "revision",
  comments: [
    { selectedText: "...", comment: "...", startOffset: 1240, endOffset: 1285 },
    ...
  ]
})
```

**Desktop/mobile:** Text selection annotation targets desktop browsers. On viewports < 768px, fall back to simpler review mode: full document view with comment list below (no inline annotation, just textarea per comment referencing a quoted passage). Progressive enhancement.

**No new dependencies** — Selection API is native browser, highlights via CSS.

**Verify:** Desktop: select text → add comment → highlight → submit. Mobile: readable document + comment list.

**Exit criteria:** ReviewPanel renders interrupt payload, annotations work on desktop, comments packaged into resume command.

---

## Phase 3: Agent Revision Loop

**File:** `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py`

- Build `process_review_feedback` node
- Formats positioned comments into structured prompt section:
```
## Reviewer Comments (address each one):
1. At "The prevalence of Type 2 diabetes...": "Strengthen this claim with data"
2. At "current treatment guidelines recommend...": "Wrong therapeutic area"
```
- Insert node between interrupt resume and revision agent
- Revision agent re-runs with comments in context
- Pipeline hits `interrupt()` again after revision for re-review
- Max 3 revision cycles, then FAILED

**Verify:** Resume with revision + comments → revised document → re-interrupts.

**Exit criteria:** Revision loop produces targeted edits based on comments, re-interrupts for review, respects 3-cycle limit.

---

## Phase 4: End-to-End Verification (`needs_package`)

- Run full cycle: invoke `needs_package` → generates document → interrupts → review in UI → approve or revise → completes
- Test all 3 paths: approve, revise (with comments), reject
- Test revision cycle limit (3 rounds)
- Verify on local LangGraph server (`:2026`)

**Exit criteria:** All 3 decision paths work through the UI. Revision with positioned comments produces targeted agent edits. 3-cycle limit enforced.

---

## Phase 5: Replicate to Remaining Recipes

**File:** `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py`

**`curriculum_package`:**
- Interrupt after curriculum + protocol + marketing assembled
- Comments carry `document_id` field (curriculum/protocol/marketing)
- Revision routes to relevant agent based on `document_id`

**Multi-document review UI:**
- Build document switcher/tabs in `ReviewPanel` for multi-document review
- `curriculum_package` interrupt payload contains 3 labeled sections
- `DocumentViewer` gets tab bar to switch between documents
- Each document has its own annotation layer
- Comments include `document_id` field

**`grant_package`:**
- Interrupt after Prose QA Pass 2 + compliance gate
- Revision routes to `grant_writer`

**`full_pipeline`:**
- Single interrupt point before existing 3-way router
- Replace `human_review_gate` with `interrupt()`

**Scope:** ~20-30 lines per recipe in orchestrator. Multi-document tabs in frontend.

**Tests:** Update/add tests for each recipe's interrupt + resume pattern.

**Verify:** Each recipe interrupts and resumes correctly. Multi-document tabs work for `curriculum_package`.

**Exit criteria:** All 4 recipes use `interrupt()`, all resume correctly, multi-document review works.

---

## Phase 6: CopilotKit Generative UI

**Directory:** `frontend/src/`

- Wire `NeedsAssessmentPanel` and `GapAnalysisPanel` into chat interface
- Build `/studio` route wrapping content in `<CopilotKit runtimeUrl="/api/copilotkit">` with agent selector (avoids "default agent" error from global wrapping)
- Register generative UI panels as CopilotKit actions on `/studio` page
- When agent run produces structured output (therapeutic area, word count, gaps), panel renders inline in chat stream
- Add panels for other agents as needed (curriculum, compliance)

**Verify:** Run `needs_assessment` on `/studio` → NeedsAssessmentPanel renders inline with metrics. Run `gap_analysis` → GapAnalysisPanel renders with severity badges.

**Exit criteria:** `/studio` route works, generative panels render inline during agent execution.

---

## Phase 7: Observability

**Directories:** `observability/`, `registry/`

**7a. Fix alert rules** (`observability/prometheus/alerts.yml`):
- Replace phantom metrics (asr_latency, gpu_utilization, registry_errors_total) with real ones
- New rules: container restart count > 3 in 15m, registry-api down > 1m, disk > 80%, memory > 90%, PostgreSQL pool exhaustion

**7b. Verify Loki log ingestion:**
- Query Promtail targets (`localhost:9080/targets`)
- Query Loki for `{job="docker"}`
- Debug pipeline if broken

**7c. Build Grafana dashboards** (`observability/grafana/provisioning/dashboards/json/`):
- Container Health — per-container CPU, memory, restart count, uptime
- Registry API — request rate, latency percentiles, error rate
- PostgreSQL — active connections, transaction rate, table sizes
- Host Resources — disk usage, network I/O, load average
- Organize in "DHG Operations" folder

**7d. Webhook endpoint** (`registry/api.py`):
- `POST /webhooks/alertmanager` — logs payloads, stores in `alert_history` table

**7e. Verify Tempo tracing:**
- Confirm LangGraph agents reach `dhg-tempo:4317` on shared network
- Run agent locally, query trace in Tempo/Grafana

**Verify:** Dashboards show data, alerts fire on test conditions, logs queryable, traces visible.

**Exit criteria:** All 5 sub-tasks verified working.

---

## Phase 8: Production Readiness

**Files:** `docker-compose.override.yml`, `.env`

- Add `dhg-frontend` service to `docker-compose.override.yml` (port 3002, `dhg-network`, restart `unless-stopped`)
- Add env toggle: `LANGGRAPH_DEPLOYMENT=local|cloud` + `LANGGRAPH_CLOUD_URL` in `.env`
- Frontend reads `NEXT_PUBLIC_LANGGRAPH_API_URL` at build time
- Kill `nohup` dev process, start containerized frontend

**Verify:** Frontend at `:3002`, connects to LangGraph, inbox + studio work.

**Exit criteria:** Frontend running as Docker container, survives reboot, env toggle works.

---

## Phase 9: Merge

- Run full test suite
- Merge `feat/human-review-loop` → master
- Push triggers LangSmith Cloud webhook for agent deployment
- Verify production agents on LangSmith Cloud interrupt correctly

**Exit criteria:** Master updated, LangSmith Cloud agents verified, all services healthy.

---

## Out of Scope

- CI/CD pipeline (C7)
- Authentication layer
- SSL/domain configuration
- LangSmith API integration into frontend (future `/analytics` page)
- Open Agent Platform, Agent Inbox, Open Canvas (LangChain open-source tools)
- Node-RED (fully deprecated)
