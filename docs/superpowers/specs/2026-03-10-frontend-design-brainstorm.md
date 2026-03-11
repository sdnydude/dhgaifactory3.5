# DHG AI Factory — Frontend Design Spec

**Date:** March 10, 2026
**Status:** APPROVED
**Owner:** Stephen Webber

---

## 1. Overview

A project-centric dashboard for managing CME and consumer health programs end-to-end. Replaces LibreChat as the primary interface to the LangGraph agent pipeline. Phase 1 is an internal team tool (2-5 users). Phase 2 extends to a client-facing portal.

### What It Solves
1. **Project visibility** — status at a glance across all active projects
2. **Review workflow** — clear "what needs my attention" per role
3. **Transparency** — version tracking between agent iterations (no more black box)
4. **Unified flow** — intake form → agent pipeline → review → delivery, all connected
5. **Agent monitoring** — live view of running agents and dynamically spawned subagents

### Design Principles
- Project is the organizing unit, not the chat thread
- Agents are first-class participants, not background processes
- Consistent layout pattern: list/tree on left, detail on right
- Frontend must handle dynamic agent hierarchies (agents spawning subagents)
- Designed for eventual AI agent project managers sitting on top

---

## 2. Tech Stack (Existing)

| Layer | Technology | Status |
|-------|-----------|--------|
| Framework | Next.js 16 (App Router) | Installed |
| Design System | shadcn/ui + Tailwind 4 | Installed |
| Chat Interface | assistant-ui | Installed |
| Generative UI | CopilotKit + AG-UI | Installed (not wired) |
| LangGraph Client | @langchain/langgraph-sdk | Installed |
| State | Zustand | Installed |
| Icons | Lucide React | Installed |
| Brand | DHG tokens in globals.css | Complete |

**Backend:** Registry API (port 8011) with CME CRUD endpoints, PostgreSQL (port 5432), LangGraph Server (port 2026).

---

## 3. Navigation & Layout

### Pattern: Collapsible Sidebar + Main Content

```
┌────┬──────────────────────────────────────────┐
│ AI │                                          │
│    │         Main Content Area                │
│ ── │                                          │
│ ▢4 │  (changes based on sidebar selection)    │
│ ✉2 │                                          │
│ ⚙3 │                                          │
│ 💬 │                                          │
│    │                                          │
│ ── │                                          │
│ ☼  │                                          │
└────┴──────────────────────────────────────────┘
```

- **Collapsed by default** — icon-only (60px), expands on hover/click
- DHG purple AI logo at top
- Badge counts: Projects (active), Inbox (pending reviews, orange), Agents (running)
- Dark/light mode toggle at bottom
- Settings at bottom

### Routes

| Route | Purpose | Layout Pattern |
|-------|---------|---------------|
| `/projects` | Project board — grid of all projects with progress bars | Full-width grid |
| `/projects/new` | New project intake — 10-section form (A-J) | Section nav left, form right |
| `/projects/[id]` | Project detail — pipeline + live content | Vertical pipeline left, content right |
| `/inbox` | Review queue — pending human reviews | Review list left, detail right |
| `/agents` | Agent monitor — running agents + subagent trees | Agent tree left, detail + logs right |
| `/chat` | Direct agent chat — existing functionality | Full-width chat thread |

---

## 4. Projects Board (`/projects`)

Grid of project cards showing all active projects. Each card displays:
- Project name
- Status indicator (green = running, orange = awaiting review, blue = queued)
- Current pipeline step (e.g., "Step 7/14 - Marketing Plan")
- Progress bar (purple fill)
- Status badge ("On track", "Review needed", "Queued")

**Actions:**
- "+ New Project" button (navigates to `/projects/new`)
- Click any card to open project detail (`/projects/[id]`)

---

## 5. Project Detail (`/projects/[id]`)

### Layout: Vertical Pipeline Left + Content Right

**Left panel (200px):** Full 14-step pipeline as a vertical list
- Completed steps: purple checkmark
- Review gates (steps 4, 8, 12, 14): green indicator when reviewed
- Active step: orange highlight with left border
- Pending steps: gray circles
- Click any completed step to view its output

**Right panel (main content):** Shows the currently selected/active step
- Step name + status + elapsed time
- Live streaming output (when agent is running)
- Real-time metrics: word count, subagents spawned, elapsed time
- "Pause" and "Chat with Agent" action buttons

**Header:** Breadcrumb (Projects / Project Name), project metadata (funder, disease state, start date)

**Tabs within content area:**
- Documents — all agent outputs with version history, word count, prose score
- Agent Activity — chronological log of agent events for this project
- Reviews — history of human review decisions for this project
- Settings — project configuration, assigned reviewers

### 14-Step Pipeline (sequential)

| Step | Agent | Human Review Gate |
|------|-------|-------------------|
| 1 | Research | |
| 2 | Clinical Practice | |
| 3 | Gap Analysis | |
| 4 | Learning Objectives | Gate 1 |
| 5 | Needs Assessment | |
| 6 | Curriculum Design | |
| 7 | Marketing Plan | |
| 8 | Outcomes Design | Gate 2 |
| 9 | Research Protocol | |
| 10 | Grant Writer (pass 1) | |
| 11 | Prose Quality (pass 1) | |
| 12 | Compliance Review | Gate 3 |
| 13 | Grant Writer (pass 2) | |
| 14 | Prose Quality (pass 2) | Gate 4 |

---

## 6. Review Inbox (`/inbox`)

### Layout: List Left + Detail Right

**Left panel (280px):** Pending review items
- Role-based filter tabs: All | Mine | Clinical | Compliance
- Each item shows: step name, project name, gate number, time ago
- Color-coded gate badges (Gate 1-4)
- Selected item highlighted with purple left border

**Right panel (main content):** Selected review detail
- Step name + project + gate number
- Quality metrics bar: prose score, word count, banned patterns, version number
- Document preview with version comparison toggle (Current v2 | Compare v1 | Full screen)
- Feedback textarea for revision notes
- Action buttons: Reject (red outline), Request Revision (neutral), Approve (green fill)

---

## 7. Agent Monitor (`/agents`)

### Layout: Agent Tree Left + Detail + Log Stream Right

**Left panel (240px):**
- Filter tabs: Running | All | Errors
- Running/completed count
- Agent tree showing parent → child hierarchy
  - Parent agents with pulsing orange dots (running) or green (complete)
  - Indented subagents with connecting border line
  - Project name + elapsed time under each parent
- Click any agent to view its detail

**Right panel (main content):**
- Selected agent name + project + elapsed time
- Subagent cards (grid): each shows name, status, progress bar, token count, elapsed time
- Dark terminal-style live log stream at bottom
  - Color-coded by source: `[parent]` purple, `[subagent-name]` orange/green
  - Filter log by agent source tabs
- "Pause" and "Logs" action buttons

---

## 8. New Project Intake (`/projects/new`)

### Layout: Section Nav Left + Form Right

**Left panel (180px):** Vertical list of all 10 sections (A through J)
- Completion status: purple checkmark (done), purple letter (active), gray letter (pending)
- Active section highlighted with purple left border
- Progress bar at bottom: "2 of 10 sections complete"
- Note: "Only Section A is required to save"

**Right panel (main content):** Active section's form fields
- Section title + description
- Form fields appropriate to the section
- "Save Draft" and "Next: [Section Name]" buttons at top
- Back/Next navigation at bottom

### Form Sections (47 fields total, order follows natural idea development)

| Section | Fields | Content |
|---------|--------|---------|
| A. Project Basics | 5 | project_name, therapeutic_area (14 options), disease_state, target_audience_primary, target_audience_secondary |
| B. Supporter Information | 5 | supporter_name, contact_name, contact_email, grant_amount_requested, grant_submission_deadline |
| C. Educational Design | 5 | learning_format, duration_minutes, include_pre_test, include_post_test, faculty_count |
| D. Clinical Focus | 5 | clinical_topics, treatment_modalities, patient_population, stage_of_disease, comorbidities |
| E. Educational Gaps | 5 | knowledge_gaps, competence_gaps, performance_gaps, gap_evidence_sources, gap_priority |
| F. Outcomes & Measurement | 5 | primary_outcomes, secondary_outcomes, measurement_approach, moore_levels_target, follow_up_timeline |
| G. Content Requirements | 5 | key_messages, required_references, excluded_topics, competitor_products_to_mention, regulatory_considerations |
| H. Logistics | 5 | target_launch_date, expiration_date, distribution_channels, geo_restrictions, language_requirements |
| I. Compliance & Disclosure | 4 | accme_compliant, financial_disclosure_required, off_label_discussion, commercial_support_acknowledgment |
| J. Additional Information | 3 | special_instructions, reference_materials, internal_notes |

**After creation:** Option to "Start Pipeline" (run all 14 steps) or "Save Draft" (configure later). Navigates to `/projects/[id]` on create.

**Backend:** POST to `/api/cme/projects` (existing endpoint in `registry/cme_endpoints.py`). Stored as JSONB in `CMEProject.intake` column.

---

## 9. Chat (`/chat`)

Existing functionality preserved. Full-width chat thread with:
- Graph selector dropdown (all 15 LangGraph graphs)
- assistant-ui chat interface with markdown, code blocks, tool call visualization
- LangGraph SDK streaming (threads, runs)

No layout change needed — this already works.

---

## 10. Existing Code to Preserve/Adapt

| Component | Path | Action |
|-----------|------|--------|
| Chat thread | `components/assistant-ui/thread.tsx` | Move to `/chat` route |
| Graph selector | `components/dhg/graph-selector.tsx` | Reuse in chat route |
| Assistant runtime | `components/dhg/assistant.tsx` | Reuse in chat route |
| Inbox list | `components/agent-inbox/inbox-list.tsx` | Adapt for new inbox layout |
| Inbox item | `components/agent-inbox/inbox-item.tsx` | Adapt for split-pane detail view |
| Markdown renderer | `components/assistant-ui/markdown-text.tsx` | Reuse for document preview |
| Tool fallback | `components/assistant-ui/tool-fallback.tsx` | Reuse in agent monitor |
| Chat API | `lib/chatApi.ts` | Reuse (thread/run management) |
| Inbox API | `lib/inboxApi.ts` | Extend with role filtering |
| Graphs metadata | `lib/graphs.ts` | Reuse throughout |
| Brand CSS | `app/globals.css` | Keep as-is |
| CopilotKit route | `app/api/copilotkit/route.ts` | Keep for generative UI panels |
| shadcn components | `components/ui/*` | Keep, add more as needed |
| Header | `components/dhg/header.tsx` | Replace with collapsible sidebar |

---

## 11. New Components Needed

| Component | Purpose |
|-----------|---------|
| `components/layout/sidebar.tsx` | Collapsible sidebar with nav links + badges |
| `components/layout/app-shell.tsx` | Sidebar + main content wrapper |
| `components/projects/project-card.tsx` | Grid card with progress bar + status |
| `components/projects/project-board.tsx` | Grid layout of project cards |
| `components/projects/pipeline-nav.tsx` | Vertical 14-step pipeline list |
| `components/projects/pipeline-step.tsx` | Individual step with status indicator |
| `components/projects/step-content.tsx` | Right panel showing step output/streaming |
| `components/projects/document-viewer.tsx` | Document preview with version comparison |
| `components/intake/intake-form.tsx` | 10-section form container |
| `components/intake/section-nav.tsx` | Left-panel section navigator |
| `components/intake/section-*.tsx` | One component per form section (A-J) |
| `components/inbox/review-list.tsx` | Left-panel review list with filters |
| `components/inbox/review-detail.tsx` | Right-panel review with metrics + actions |
| `components/agents/agent-tree.tsx` | Left-panel agent hierarchy tree |
| `components/agents/agent-detail.tsx` | Right-panel subagent cards + metrics |
| `components/agents/log-stream.tsx` | Terminal-style live log viewer |
| `components/agents/subagent-card.tsx` | Individual subagent status card |
| `lib/projectsApi.ts` | Registry API client for project CRUD |
| `lib/agentsApi.ts` | LangGraph API client for agent status |

---

## 12. Data Flow

```
Registry API (port 8011)         LangGraph Server (port 2026)
        │                                    │
        ├── GET /api/cme/projects ───────────┤── GET /threads
        ├── POST /api/cme/projects ──────────┤── POST /threads
        ├── GET /api/cme/projects/:id ───────┤── POST /runs/stream
        ├── POST /api/cme/projects/:id/start─┤── GET /threads/search?status=interrupted
        │                                    │── POST /runs (Command resume)
        │                                    │
        └──── Next.js Frontend (port 3002) ──┘
```

- **Project CRUD:** Registry API (PostgreSQL)
- **Agent execution:** LangGraph Server (threads, runs, streaming)
- **Review queue:** LangGraph `threads.search({ status: "interrupted" })`
- **Agent monitoring:** LangGraph thread/run status polling

---

## 13. Rejected Approaches

### Inbox-First Workspace
Main view is "what needs my attention." Projects accessed through activity feed.
- **Rejected because:** Harder to get big picture across projects. Better for reviewers than for the project orchestrator.

### Chat-First with Side Panels
Keep current chat as primary interface with collapsible side panels.
- **Rejected because:** Doesn't solve "status at a glance." Repeats LibreChat limitation.

### Simplified intake form
Custom-designed shorter form with fewer fields.
- **Rejected because:** Existing 10-section, 47-field form follows the natural order of developing a new idea. Keep the structure Stephen designed.

### Stacked expandable review cards
Full-width accordion cards for reviews.
- **Rejected because:** Doesn't scale when multiple projects have pending reviews. List + detail split matches the rest of the app and allows role-based filtering.

### Activity timeline for agent monitoring
Chronological feed of agent events.
- **Rejected because:** Doesn't show parent/child agent hierarchy or allow live log streaming. Tree + detail view supports the dynamic subagent spawning model.

---

## 14. Future Considerations (Not In This Spec)

- **AI Agent Project Managers** — agents that monitor project status, flag delays, route reviews, re-run low-quality outputs
- **Client-facing portal (Phase 2)** — project submission and tracking for external medical education professionals
- **React Flow** — visual LangGraph workflow editor for designing custom pipelines
- **Tremor dashboards** — token usage, agent performance metrics, cost tracking
- **Per-project pipeline customization** — multi-step wizard for selecting which agents to run and assigning reviewers per gate
