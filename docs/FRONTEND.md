# DHG AI Factory — Frontend Architecture

**Stack:** Next.js 16 + shadcn/ui + assistant-ui + CopilotKit + LangGraph SDK
**Location:** `frontend/`
**Port:** 3000 (dev), standalone Docker build for production

---

## Technology Choices

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | Next.js 16 (App Router) | SSR, routing, standalone builds |
| Design System | shadcn/ui + Tailwind 4 | DHG-branded components |
| Chat Interface | assistant-ui | Composable chat with LangGraph bridge |
| LangGraph Client | @langchain/langgraph-sdk | Thread management, streaming |
| State | Zustand | Client-side state management |
| Icons | Lucide React | Consistent icon set |
| Markdown | remark-gfm | GitHub-flavored markdown rendering |
| Generative UI | CopilotKit + AG-UI | Agent-rendered panels via LangGraph bridge |

---

## Directory Structure

```
frontend/src/
  app/
    layout.tsx          — Root layout (Inter font, TooltipProvider)
    page.tsx            — Home page (graph selector + chat)
    globals.css         — Tailwind 4 + DHG brand tokens
    inbox/
      page.tsx          — Agent Inbox (human review)
  components/
    dhg/                — DHG-branded components
      header.tsx        — Nav bar with logo + graph selector + status
      assistant.tsx     — LangGraph runtime wrapper
      graph-selector.tsx — 15-graph dropdown (agents + orchestrators)
    assistant-ui/       — Chat framework components
      thread.tsx        — Conversation thread
      markdown-text.tsx — Rich markdown rendering
      attachment.tsx    — File/image handling
      tool-fallback.tsx — Tool call visualization
      tooltip-icon-button.tsx
    agent-inbox/        — Human review inbox
      inbox-list.tsx    — Pending reviews list with polling
      inbox-item.tsx    — Individual review card (approve/revise/reject)
    generative-ui/      — CopilotKit generative panels
      needs-assessment-panel.tsx — Structured needs assessment output
      gap-analysis-panel.tsx     — Gap analysis with severity badges
    ui/                 — shadcn base components
  lib/
    chatApi.ts          — LangGraph client (createThread, sendMessage, etc.)
    inboxApi.ts         — Inbox API (list interrupted threads, resume)
    copilot-runtime.ts  — CopilotKit configuration
    graphs.ts           — Static graph registry (15 graphs)
    utils.ts            — cn() utility
```

---

## LangGraph Integration

The frontend connects to LangGraph Server via `@langchain/langgraph-sdk`:

```
NEXT_PUBLIC_LANGGRAPH_API_URL=http://localhost:2026
```

**Flow:**
1. User selects a graph (agent/orchestrator) from the dropdown
2. `createThread()` creates a new thread on LangGraph Server
3. `sendMessage()` streams responses via `client.runs.stream()`
4. assistant-ui renders messages with markdown, tool calls, and attachments

**Supported graphs:** All 15 from `langgraph.json` — 11 individual agents + 4 orchestrator recipes.

---

## Brand Tokens

CSS variables defined in `globals.css` following `.claude/rules/dhg-brand.md`:

- Light: `--dhg-background: #FAF9F7` (warm off-white), `--dhg-purple: #663399`
- Dark: `--dhg-background: #1A1D24`, `--dhg-purple-light: #A78BFA`
- Font: Inter (loaded via next/font)

---

## Development

```bash
cd frontend
npm install
npm run dev          # localhost:3000
npm run build        # Production build (standalone output)
```

---

## Agent Inbox (Human Review)

The `/inbox` route displays threads that have been interrupted at human review gates.
Uses `client.threads.search({ status: "interrupted" })` to find paused threads.
Reviewers can approve, request revision, or reject via `Command({ resume: { decision, feedback } })`.
Auto-refreshes every 30 seconds.

## CopilotKit + AG-UI Protocol

CopilotKit provides generative UI — agents render structured panels instead of plain text.
API route at `/api/copilotkit` bridges to LangGraph via `LangGraphAgent` from `@copilotkit/runtime/langgraph`.
Two initial panels: `NeedsAssessmentPanel` (quality metrics) and `GapAnalysisPanel` (severity badges).
Registered agents: needs_assessment, gap_analysis, needs_package, grant_package.

## Planned Enhancements

- **React Flow** — Visual LangGraph workflow editor
- **Tremor** — Token usage and agent performance dashboards
- **Refine** — Admin console with FastAPI data providers
