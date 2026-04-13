# Phase 3 Frontend Architecture — Design Spec

**Date:** 2026-04-07
**Status:** Approved
**Scope:** 5 features (#6 Generative UI, #9 LLManager, #10 React Flow, #11 Tremor Dashboards, #12 Refine Admin)

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Target audience | External users (CME reviewers at pharma companies) | Requires role separation, polished UX from the start |
| Navigation structure | Grouped sidebar (Work / Observe / Manage) with role-based filtering | Scales to 12+ items, roles hide entire sections |
| Architecture approach | Hybrid — auth foundation first, then incremental features | Auth is small (~3 files) but everything needs it; features ship independently after |
| LLManager (#9) | Evolve existing `/inbox` route with LLM reflection layer | Review components already exist; inbox is the natural "things needing attention" route |
| React Flow (#10) | Lightweight read-only pipeline status widget + "Open in Studio" link | LangGraph Studio already provides full visualization; widget gives reviewers compact status |
| Tremor (#11) | New `/dashboards` route for business analytics (not infrastructure) | Real gap is business-level metrics — token spend, agent performance, pipeline throughput |
| Generative UI (#6) | Panels move to Recipes tab on `/agents`; inline rendering in `/chat` | `/studio` reserved for future multimedia/livestreaming; Recipes tab is the agent-running context |
| Refine (#12) | Admin console in Manage sidebar section | Biggest scope, saved for last; leverages existing RBAC endpoints |

---

## Step 0: Foundation — Auth & Role-Based Navigation

### `hooks/use-session.ts`

Reads the Cloudflare Access JWT from the `Cf-Access-Jwt-Assertion` cookie. Decodes role and permissions. Caches in a Zustand store. Falls back to a dev-mode mock user when `SECURITY_DEV_MODE=true` (matching the backend pattern in `registry/auth.py`).

### `lib/permissions.ts`

Maps the 5 backend roles to frontend visibility:

| Role | Work section | Observe section | Manage section |
|------|-------------|-----------------|----------------|
| admin | all | all | all |
| operations | all | all | none |
| finance | Projects, Dashboards | Dashboards | none |
| editor | Projects, Inbox, Chat | none | none |
| viewer | Projects, Inbox | none | none |

### Sidebar update (`components/layout/sidebar.tsx`)

Modify existing sidebar to:
- Group `NAV_ITEMS` into labeled sections: Work, Observe, Manage
- Filter items based on `useSession().permissions`
- Render section labels (small uppercase text) between groups
- Preserve existing collapse/expand, dark mode toggle, LangGraph Cloud status indicator

### Route guard

Next.js middleware (`middleware.ts` at app root) that checks the user's role against the requested route. Reads the Cloudflare JWT from the request cookie, decodes the role, and checks against the permissions map. Unauthorized access redirects to `/projects` (the safe default visible to all roles). This runs server-side before the page renders — no flash of unauthorized content.

---

## Step 1: #9 LLManager — Inbox Review Workflow

### Review store (`stores/review-store.ts`)

- Fetches pending reviews from LangGraph Cloud (threads in `interrupted` state)
- Tracks current review item, comments, decision history
- Sends approve/revise/reject decisions back to LangGraph (resuming the interrupted thread via langgraph-sdk)

### LLM Reflection panel (`components/review/reflection-panel.tsx`)

When a reviewer opens a document, the system shows:
- **AI Summary** — what the agent produced and why (extracted from agent state)
- **Quality Signals** — prose quality score, compliance status, gap coverage (from agent quality gates)
- **Recommendation** — LLM's suggested decision with reasoning (e.g., "Recommend approve: all 5 gaps evidence-based, prose score 92/100, ACCME compliant")
- Reviewer can agree, override, or ask for more detail

### Inbox layout upgrade (`app/inbox/page.tsx`)

Master-detail layout:
- Left: list of pending reviews with status badges, priority, agent source
- Right: full review panel (document-viewer + reflection-panel + comments-sidebar + decision-bar)

### Decision flow

- `approved` — resumes LangGraph thread with approval, advances pipeline
- `revision` — resumes with feedback, agent re-runs with reviewer comments injected
- `rejected` — resumes with rejection, pipeline terminates with reason logged

### Backend endpoint

`GET /api/reviews/pending` — queries LangGraph Cloud for interrupted threads, enriches with project metadata from registry DB.

---

## Step 2: #6 Generative UI — Agent Panels on Recipes Tab

### Recipes tab (`components/agents/recipes-tab.tsx`)

New tab on `/agents` page. Shows a grid of runnable recipes and individual agents. Click one to run it and see structured output as a rich panel.

### 15 Generative UI panel components

**Individual agents (11):**
- `NeedsAssessmentPanel` (exists — move from `/studio`)
- `GapAnalysisPanel` (exists — move from `/studio`)
- `ResearchPanel` (new)
- `ClinicalPracticePanel` (new)
- `LearningObjectivesPanel` (new)
- `CurriculumDesignPanel` (new)
- `ResearchProtocolPanel` (new)
- `MarketingPlanPanel` (new)
- `GrantWriterPanel` (new)
- `ProseQualityPanel` (new)
- `ComplianceReviewPanel` (new)

**Recipes (4):**
- `NeedsPackagePanel` — composite view: Research + Clinical + Gap + LO + Needs
- `CurriculumPackagePanel` — Needs Package + Curriculum + Protocol + Marketing
- `GrantPackagePanel` — all 11 agents, 2 prose QA passes, compliance
- `FullPipelinePanel` — Grant Package + human review routing status

### Shared panel template (`components/generative-ui/agent-panel-template.tsx`)

All agents follow the same TypedDict state pattern. Shared structure:
- Header: agent name, status badge, duration, token count
- Sections: collapsible content blocks mapped from agent state fields
- Quality bar: score/validation indicators from quality gates
- VS alternatives: if Verbalized Sampling was used, show the distribution

Each panel maps its specific state fields to section labels. The 9 new individual panels are largely configuration over the template, not unique code.

### CopilotKit wiring

Recipes tab wraps selected agent in `<CopilotKit agent={selectedAgent}>`, uses `useCopilotAction` to register panel render functions. Structured agent output triggers the corresponding panel.

### Inline chat rendering

In `/chat`, register the same panels as CopilotKit render functions so structured agent output appears as rich UI in the conversation stream.

### Studio cleanup

Remove current CopilotKit/agent content from `app/studio/page.tsx`. Replace with placeholder: "Multimedia Studio — Coming Soon" with DHG brand styling. Route stays in sidebar for future use.

---

## Step 3: #10 Pipeline Status Widget (React Flow Lite)

### Pipeline status component (`components/pipeline/pipeline-status.tsx`)

Compact React Flow component that visualizes a single pipeline run's progress. Read-only, not an editor.

- Nodes represent agents, color-coded: grey=pending, blue=running, green=complete, red=failed
- Edges show execution order, parallel branches rendered as split paths
- Click a node to see summary (duration, token count, quality score)
- Animates as agents complete in real-time (polls thread state)

### Graph topology data (`lib/pipeline-topologies.ts`)

Static React Flow node/edge configs for the 4 orchestrator recipes:
- `needs_package` — Research + Clinical parallel, then Gap, LO, Needs, Prose QA, Human Review
- `curriculum_package` — Needs Package + Curriculum + Protocol + Marketing parallel, Human Review
- `grant_package` — all 11 agents, 2 prose QA passes, compliance gate, Human Review
- `full_pipeline` — grant_package + 3-way human review routing

Runtime status overlaid from LangGraph thread state.

### Where it appears

- `/agents` page — when viewing a running/completed run, shows in detail panel
- `/projects/[id]` — project detail page shows pipeline status for latest run
- `/inbox` review items — collapsed pipeline widget shows which stage produced the document under review

### "Open in Studio" link

Button on the widget that opens LangGraph Studio:
- Dev: `localhost:2026`
- Production: LangGraph Cloud Studio URL
- Visible only to admin/operations roles

### Package

`@xyflow/react` (React Flow v12)

---

## Step 4: #11 Business Dashboards (Tremor)

### New route: `/dashboards`

Lives in the "Observe" sidebar section. Focused on business-level agent analytics. Infrastructure monitoring stays in `/monitoring`.

### Dashboard tabs

- **Token & Cost** — spend per agent, spend per recipe, cost per grant package, daily/weekly/monthly trends, breakdown by model (Claude Sonnet vs Ollama)
- **Agent Performance** — success/failure rates per agent, average duration, retry frequency, quality gate pass rates, prose quality score distribution
- **Pipeline Throughput** — grant packages completed, average end-to-end time, bottleneck identification (which agent takes longest), human review turnaround time
- **Quality Trends** — prose quality scores over time, compliance pass rates, VS selection delta trends, gap coverage metrics

### Tremor components

- `BarChart`, `AreaChart`, `DonutChart` for spend/performance
- `Tracker` for pipeline stage status
- `BadgeDelta` for trend indicators
- `Table` for detailed breakdowns

### Data store (`stores/dashboards-store.ts`)

Fetches from registry API (new endpoints).

### Backend endpoints (3 new)

- `GET /api/analytics/token-usage` — aggregated token counts by agent/recipe/time period
- `GET /api/analytics/pipeline-runs` — run history with durations, outcomes, quality scores
- `GET /api/analytics/agent-performance` — per-agent success rates, retries, average duration

Data sources: LangGraph Cloud run history (via langgraph-sdk), agent state snapshots (quality scores, token counts from `CMEPipelineState`).

### Role visibility

Admin, operations, and finance roles see `/dashboards`. Editors and viewers do not.

### Package

`@tremor/react`

---

## Step 5: #12 Admin Console (Refine)

### Layout at `/admin`

Admin console uses the Manage sidebar section. Clicking "Admin Console" navigates to `/admin` with secondary sub-navigation for its pages.

### Refine resources (CRUD pages)

| Resource | Registry Endpoint | Operations |
|----------|------------------|------------|
| Users | `/api/admin/users` (exists) | List, create, edit, deactivate |
| Roles | `/api/admin/roles` (exists) | List, view, assign/remove |
| Projects | `/api/projects` (partial) | List, create, edit, archive |
| Audit Log | `/api/admin/audit` (exists) | List, filter, export |
| API Keys | `/api/admin/api-keys` (new) | List, create, revoke |
| System Settings | `/api/admin/settings` (new) | View, edit |

### Data provider (`lib/refine-data-provider.ts`)

Bridges Refine's data interface to the registry API. Maps Refine's `getList`, `getOne`, `create`, `update`, `deleteOne` to FastAPI endpoints. Includes Cloudflare JWT in all requests.

### Auth provider (`lib/refine-auth-provider.ts`)

Wraps `useSession` to provide Refine's `authProvider` interface (login, logout, check, getPermissions, getIdentity).

### Backend endpoints (2 new)

- `GET/POST/DELETE /api/admin/api-keys` — API key management
- `GET/PUT /api/admin/settings` — system configuration

Existing admin endpoints from Phase 6 security work: `/api/admin/users`, `/api/admin/roles`, `/api/admin/audit`.

### Role visibility

Admin only. The "Manage" sidebar section is completely hidden for all other roles.

### Packages

`@refinedev/core`, `@refinedev/nextjs-router`

---

## Build Sequence

```
Step 0: Foundation (auth + sidebar)
  |
  +-- Step 1: #9 LLManager (/inbox upgrade)
  |     needs: useSession, review-store, 1 new API endpoint
  |
  +-- Step 2: #6 GenUI Panels (recipes tab + chat inline)
  |     needs: CopilotKit wiring, 15 panel components
  |     CAN PARALLEL with Step 1 (independent routes)
  |
  +-- Step 3: #10 Pipeline Widget (React Flow lite)
  |     needs: @xyflow/react, pipeline-topologies.ts
  |     used BY Steps 1 & 2 (embedded in inbox + agents)
  |     can start after Step 0, integrated into 1 & 2 later
  |
  +-- Step 4: #11 Dashboards (Tremor)
  |     needs: 3 new API endpoints, @tremor/react
  |     independent of Steps 1-3
  |
  +-- Step 5: #12 Admin Console (Refine)
        needs: @refinedev/core, 2 new API endpoints
        depends on Step 0 (auth) only
        biggest scope, saved for last
```

## New Packages

- `@xyflow/react` (React Flow v12)
- `@tremor/react`
- `@refinedev/core`
- `@refinedev/nextjs-router`

## New Backend Endpoints (7 total)

| Endpoint | Step | Purpose |
|----------|------|---------|
| `GET /api/reviews/pending` | 1 | Interrupted threads enriched with project metadata |
| `GET /api/analytics/token-usage` | 4 | Token counts by agent/recipe/period |
| `GET /api/analytics/pipeline-runs` | 4 | Run history, durations, outcomes, quality scores |
| `GET /api/analytics/agent-performance` | 4 | Per-agent success rates, retries, durations |
| `GET/POST/DELETE /api/admin/api-keys` | 5 | API key management |
| `GET/PUT /api/admin/settings` | 5 | System configuration |

## Files Modified (Existing)

- `components/layout/sidebar.tsx` — grouped sections + role filtering
- `app/providers.tsx` — add session provider
- `app/inbox/page.tsx` — master-detail layout
- `app/agents/page.tsx` — add Recipes tab
- `app/studio/page.tsx` — gut, replace with multimedia placeholder
- `app/chat/page.tsx` — register GenUI panel renderers

## Estimated New Files (~45)

- ~8 shared infrastructure (hooks, stores, lib, permissions, providers)
- ~15 GenUI panel components (mostly templated from shared base)
- ~6 dashboard components (Tremor charts + store)
- ~4 pipeline widget components (React Flow + topologies)
- ~6 Refine admin pages (CRUD resources + providers)
- ~6 new API endpoint files in registry
