# DHG AI Factory — Frontend Architecture

**Stack:** Next.js 16 + shadcn/ui + assistant-ui + CopilotKit + LangGraph SDK
**Location:** `frontend/`
**Port:** 3000 (dev), standalone Docker build for production
**Last Updated:** April 8, 2026

---

## Technology Choices

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | Next.js 16 (App Router) | SSR, routing, standalone builds |
| Design System | shadcn/ui + Tailwind 4 | DHG-branded components |
| Chat Interface | assistant-ui | Composable chat with LangGraph bridge |
| LangGraph Client | @langchain/langgraph-sdk | Thread management, streaming |
| State | Zustand | Client-side state management |
| Auth | Cloudflare Access JWT + RBAC | 4-layer defense-in-depth |
| Icons | Lucide React | Consistent icon set |
| Markdown | remark-gfm | GitHub-flavored markdown rendering |
| Generative UI | CopilotKit + AG-UI | Agent-rendered panels via LangGraph bridge |

---

## Directory Structure

```
frontend/src/
  app/
    layout.tsx              — Root layout (Inter font, TooltipProvider, session init)
    providers.tsx           — Client providers (session initialization on mount)
    page.tsx                — Home page (graph selector + chat)
    globals.css             — Tailwind 4 + DHG brand tokens
    inbox/
      page.tsx              — LLManager Review Inbox
    api/
      auth/me/route.ts      — Session endpoint (proxies to registry /api/v1/security/users/me)
      registry/[...path]/route.ts — Registry proxy (forwards Cloudflare JWT)
  components/
    layout/
      sidebar.tsx           — Role-aware sidebar (Work/Observe/Manage sections)
    dhg/                    — DHG-branded components
      header.tsx            — Nav bar with logo + graph selector + status
      assistant.tsx         — LangGraph runtime wrapper
      graph-selector.tsx    — 15-graph dropdown (agents + orchestrators)
    assistant-ui/           — Chat framework components
      thread.tsx            — Conversation thread
      markdown-text.tsx     — Rich markdown rendering
      attachment.tsx        — File/image handling
      tool-fallback.tsx     — Tool call visualization
      tooltip-icon-button.tsx
    review/                 — LLManager human review components
      inbox-master-detail.tsx — Master list + detail layout, polling
      review-panel.tsx      — Document viewer + comments + VS + decision bar
      reflection-panel.tsx  — AI quality signals + recommendation
      metrics-bar.tsx       — Compact metrics badges
      decision-bar.tsx      — Approve / Revise / Reject buttons
      document-viewer.tsx   — Markdown renderer with text selection
      comments-sidebar.tsx  — Comment list with scroll-to
      use-annotations.ts    — Text selection + comment state hook
      vs-alternatives.tsx   — Verbalized Sampling alternatives display
      types.ts              — TypeScript interfaces for review data
    generative-ui/          — CopilotKit generative panels
      needs-assessment-panel.tsx — Structured needs assessment output
      gap-analysis-panel.tsx     — Gap analysis with severity badges
    ui/                     — shadcn base components
  hooks/
    use-session.ts          — Auth session hook (fetches /api/auth/me, provides roles)
    use-theme.ts            — Dark/light mode toggle
  stores/
    session-store.ts        — Zustand auth state (user, roles, permissions, dev fallback)
    review-store.ts         — Zustand inbox state (reviews, selection, loading)
    app-store.ts            — Zustand app state (sidebar, badge counts)
  lib/
    permissions.ts          — Route-role matrix, getVisibleRoutes(), canAccessRoute()
    decode-jwt.ts           — Client-side Cloudflare JWT decode utility
    chatApi.ts              — LangGraph client (createThread, sendMessage, etc.)
    inboxApi.ts             — Inbox API (list interrupted threads, resume)
    copilot-runtime.ts      — CopilotKit configuration
    graphs.ts               — Static graph registry (15 graphs)
    utils.ts                — cn() utility
  middleware.ts             — Next.js Edge middleware (JWT check, route guard)
```

---

## Authentication & Authorization

See `docs/AUTH_AND_RBAC.md` for the full auth system. Frontend-specific details:

**Session flow:**
1. Cloudflare Access authenticates the user and sets a `CF_Authorization` JWT cookie
2. Next.js middleware (`middleware.ts`) checks the cookie and passes email via `x-user-email` header
3. `useSession()` hook calls `/api/auth/me` to resolve full user profile (roles, permissions)
4. Session stored in Zustand (`session-store.ts`) — available app-wide

**Route guards:** Defined in `lib/permissions.ts` and mirrored in `middleware.ts`:

| Route | Allowed Roles |
|-------|--------------|
| /projects | admin, operations, finance, editor, viewer |
| /inbox | admin, operations, editor, viewer |
| /chat | admin, operations, editor |
| /search | admin, operations, editor |
| /agents | admin, operations |
| /dashboards | admin, operations, finance |
| /monitoring | admin, operations |
| /studio | admin, operations |
| /admin | admin |

**Dev mode:** Set `NEXT_PUBLIC_SECURITY_DEV_MODE=true` to bypass all auth. The session store provides a dev user with admin permissions.

---

## Sidebar Navigation

The sidebar (`components/layout/sidebar.tsx`) is role-aware and grouped into three sections:

| Section | Routes | Purpose |
|---------|--------|---------|
| **Work** | Projects, Inbox, Chat, Search | Day-to-day tasks |
| **Observe** | Agents, Dashboards, Monitoring, Studio | System visibility |
| **Manage** | Admin Console | User/role management |

Features:
- Collapsible (persisted in app store)
- LangGraph Cloud connection status indicator (polls `/api/langgraph/ok` every 60s)
- Dark/light mode toggle
- Badge counts on Projects and Inbox
- Tooltips in collapsed mode

---

## LangGraph Integration

The frontend connects to LangGraph via `@langchain/langgraph-sdk`:

```
NEXT_PUBLIC_LANGGRAPH_API_URL=<LangGraph Cloud URL>  # Production
NEXT_PUBLIC_LANGGRAPH_API_URL=http://localhost:2026   # Dev only
```

**Flow:**
1. User selects a graph (agent/orchestrator) from the dropdown
2. `createThread()` creates a new thread on LangGraph Server
3. `sendMessage()` streams responses via `client.runs.stream()`
4. assistant-ui renders messages with markdown, tool calls, and attachments

**Supported graphs:** All 15 from `langgraph.json` — 11 individual agents + 4 orchestrator recipes.

---

## LLManager Review Inbox

The `/inbox` route is the human-in-the-loop review workflow. See `docs/LLMANAGER_REVIEW.md` for full documentation.

**Summary:** Master-detail layout showing interrupted LangGraph threads. Reviewers see AI quality signals (prose quality, banned patterns, ACCME compliance), can annotate documents with inline comments, view VS alternatives, and approve/revise/reject. Decisions resume the LangGraph thread.

---

## Brand Tokens

CSS variables defined in `globals.css` following `.claude/rules/dhg-brand.md`:

- Light: `--dhg-background: #FAF9F7` (warm off-white), `--dhg-purple: #663399`
- Dark: `--dhg-background: #1A1D24`, `--dhg-purple-light: #A78BFA`
- Font: Inter (loaded via next/font)

---

## CopilotKit + AG-UI Protocol

CopilotKit provides generative UI — agents render structured panels instead of plain text.
API route at `/api/copilotkit` bridges to LangGraph via `LangGraphAgent` from `@copilotkit/runtime/langgraph`.
Two initial panels: `NeedsAssessmentPanel` (quality metrics) and `GapAnalysisPanel` (severity badges).
Registered agents: needs_assessment, gap_analysis, needs_package, grant_package.

---

## Development

```bash
cd frontend
npm install
npm run dev          # localhost:3000
npm run build        # Production build (standalone output)
```

**Environment variables:**
- `NEXT_PUBLIC_LANGGRAPH_API_URL` — LangGraph endpoint
- `NEXT_PUBLIC_SECURITY_DEV_MODE` — Set `true` to bypass auth
- `REGISTRY_API_URL` — Backend registry API (used by API routes)

---

## Planned Enhancements

- **React Flow** — Visual LangGraph workflow editor
- **Tremor** — Token usage and agent performance dashboards
- **Refine** — Admin console with FastAPI data providers
