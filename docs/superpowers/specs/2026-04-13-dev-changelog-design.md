# Dev Changelog — Design Spec

**Date:** 2026-04-13
**Route:** `/admin/reporting/dev-changelog`
**Status:** Approved for build
**Precedent commits:** `488ac41` (inbox editorial), `e4f4d08` / `28f369f` (mission control), `a4b6c46`..`221fb5f` (agents tabbed container + library)

---

## 1. Purpose

A living, editable, agent-assisted changelog of all development work on the DHG AI Factory. Replaces the lossy `docs/TODO.md` rewrite cycle with a queryable, filterable, diffable record that doesn't degrade under compaction and is the canonical place to see "what shipped, what's in flight, what's debt."

First deployment serves three jobs:

1. **Historical record** — the 30-day burndown that is now seeded in the `dev_changelog` table (migration 007, 16 entries).
2. **Proving ground for TanStack Table** — this is the first TanStack deployment in the product. The `<DataTable>` wrapper built here becomes the standard for all future tabular UI.
3. **Substrate for the 3am agent** — the field-ownership model in the schema (agent-owned vs human-owned columns) exists so a nightly agent can upsert without stomping on human edits. Agent lands in Build 5.

## 2. Context: what the audit found

From the frontend-design agent's audit of the existing product:

- **Fonts already loaded:** Fraunces (display serif with variable SOFT/opsz axes), Source Serif 4 (body serif), Inter (sans), IBM Plex Mono (editorial metadata), JetBrains Mono (mission-control telemetry). All via `next/font/google` in `frontend/src/app/layout.tsx`.
- **Editorial vocabulary** (from Apr 8 inbox redesign): triple-line `border-top` with `border-double`, Fraunces italic display at 3rem with `font-variation-settings "SOFT" 70 "opsz" 144`, Source Serif 4 justified prose with `hanging-punctuation: first last`, IBM Plex Mono small-caps metadata (`letter-spacing: 0.12em`, `font-variant-caps: all-small-caps`), drop caps, stamp-btn letterpress buttons, marginal footnotes.
- **Mission Control vocabulary** (from Apr 12-13 dashboards redesign): `--mc-*` token family (`--mc-bg #07090d`, `--mc-phosphor #6ee7b7`, `--mc-amber #fbbf24`, `--mc-alert #f87171`, `--mc-cyan #67e8f9`), JetBrains Mono telemetry type (`font-feature-settings "ss01" "zero" "tnum"`), corner-bracket panel frames, 11px labels at `0.14em` letter-spacing uppercase.
- **Admin nav status:** `/admin` route exists and is gated to admin role in `frontend/src/lib/permissions.ts`. No `/admin/reporting` subtree yet. Sidebar groups routes by section (`work`, `observe`, `manage`) via `SECTION_LABELS`. New routes auto-slot into the Manage section by adding to `ROUTE_PERMISSIONS`.
- **Existing table pattern:** `agents-library-table.tsx` is hand-rolled HTML `<table>`, sticky header, small-caps uppercase column labels, sortable via `ArrowUpDown` lucide icon. No TanStack currently in use. No reusable `<DataTable>` wrapper.

## 3. Aesthetic direction

**Editorial ledger.** The dev-changelog is a hybrid of the inbox's editorial print-journal voice and mission control's dense-data telemetry — a broadsheet with tabular financial-report underpinnings. It is not a SaaS data grid with toolbar chrome.

Bifurcated hierarchy:

- **Narrative layer (inbox voice):** Fraunces italic for the masthead title, Source Serif 4 for `key_insight` prose body text, IBM Plex Mono for editorial metadata labels. Triple-line double border-top opening the page.
- **Data layer (mission control voice):** JetBrains Mono tabular-nums for numeric columns (commit_count, dates, SHAs), 11px small-caps uppercase column labels, subtle row-stripe grid, corner-bracket accents on the detail slide-over.

Color restraint: stay on `--background` (warm off-white #FAF9F7), not mission-control's #07090d. Status tones borrow from `--mc-*` semantics but muted for light backgrounds:

| Status | Token | Visual |
|---|---|---|
| shipped | `--color-dhg-purple` #663399 | muted pill |
| in_progress | `--mc-amber` #fbbf24 | filled pill |
| debt | `--color-dhg-orange` #F77E2D | filled pill + underline |
| backlog | muted-foreground | outline pill |
| abandoned | muted + strikethrough | ghost pill |

## 4. Information architecture

```
/admin
  /reporting                    ← new section (layout + nav)
    /dev-changelog              ← this page (Build 1-4)
    /security-audit             ← future
    /agent-performance          ← future
    /vs-metrics-summary         ← future
```

`/admin/reporting` is designed up-front as a section, not a single page. Shell costs are amortized across future reports.

## 5. Page structure

```
┌────────────────────────────────────────────────────────────────────────┐
│  ═══════════════════════════════════════════════════════════════════   │ ← triple-line double border
│                                                                        │
│  Development Changelog                          (Fraunces italic 3rem) │
│  DHG AI FACTORY · ANNOTATED     (IBM Plex Mono small-caps 0.78rem)     │
│                                                                        │
│  Last run: 2026-04-13 03:00 UTC · 16 epics · 121 commits · 1 debt      │
│  ───────────────────────────────────────────────────────────────────   │ ← single rule
│                                                                        │
│ ┌──────────────┬─────────────────────────────────────────────────────┐ │
│ │              │                                                     │ │
│ │  FILTERS     │  [Table]  [Timeline]  [Kanban]      ⟐ Saved views  │ │
│ │  ──────      │  ─────────────────────────────────────────────────  │ │
│ │              │                                                     │ │
│ │  STATUS      │  SLUG          EPIC         CAT  STATUS  COMMITS    │ │
│ │  ☐ shipped   │  ─────────────────────────────────────────────────  │ │
│ │  ☐ in prog   │  vs-engine-w1  VS Engine... feat ●shipped    25    │ │
│ │  ☐ debt      │  monitoring... Monitori...  feat ●shipped     7    │ │
│ │  ☐ backlog   │  ...                                                │ │
│ │              │                                                     │ │
│ │  CATEGORY    │                                                     │ │
│ │  ☐ feature   │                                                     │ │
│ │  ☐ fix       │                                                     │ │
│ │  ☐ debt      │                                                     │ │
│ │              │                                                     │ │
│ │  WINDOW      │                                                     │ │
│ │  [date]      │                                                     │ │
│ │  [date]      │                                                     │ │
│ │              │                                                     │ │
│ │  SEARCH      │                                                     │ │
│ │  [_______]   │                                                     │ │
│ │              │                                                     │ │
│ └──────────────┴─────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

On row click: right slide-over panel (like Agents Library's `agent-slide-over.tsx`) shows commit list with GitHub links, sessions, and inline-editable `key_insight` + `notes` + `declared_status` + `priority`.

## 6. Data model — already built

Migration `007_add_dev_changelog.py` is live in registry DB (verified). Schema summary:

**Agent-owned fields** (read-only in UI):
- `slug`, `epic`, `category`, `detected_status`, `window_start`, `window_end`
- `commit_count`, `commits` (JSONB), `sessions` (JSONB)
- `detected_at`, `last_agent_run_at`

**Human-owned fields** (editable in UI):
- `declared_status`, `key_insight`, `notes`, `priority`, `locked`

**Mixed/metadata:**
- `source` (manual | agent | mixed)
- `last_human_edit_at`, `updated_at`

**Display status rule:** `COALESCE(declared_status, detected_status)`. Both shown in detail panel with provenance.

## 7. TanStack Table — the first deployment

### 7.1 Decision

TanStack Table (`@tanstack/react-table`) becomes the standard for all new tabular UI in the product. `agents-library-table.tsx` is not retrofitted now — migration is opportunistic when that file is next touched for other reasons.

### 7.2 Reusable wrapper

Build `frontend/src/components/ui/data-table.tsx` as a generic wrapper following the [shadcn DataTable recipe](https://ui.shadcn.com/docs/components/data-table). Do not invent a bespoke pattern.

```tsx
// frontend/src/components/ui/data-table.tsx
"use client";
import {
  ColumnDef, flexRender, getCoreRowModel,
  getFilteredRowModel, getSortedRowModel, getFacetedRowModel,
  useReactTable, SortingState, ColumnFiltersState, VisibilityState,
} from "@tanstack/react-table";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  onRowClick?: (row: TData) => void;
  // slot props for top-bar, empty-state, etc.
}

export function DataTable<TData, TValue>({ columns, data, onRowClick }: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({});

  const table = useReactTable({
    data, columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    state: { sorting, columnFilters, columnVisibility },
  });

  return (
    <Table>
      <TableHeader>
        {table.getHeaderGroups().map(hg => (
          <TableRow key={hg.id}>
            {hg.headers.map(h => (
              <TableHead key={h.id} className="font-mono text-[0.72rem] uppercase tracking-[0.14em] text-muted-foreground">
                {flexRender(h.column.columnDef.header, h.getContext())}
              </TableHead>
            ))}
          </TableRow>
        ))}
      </TableHeader>
      <TableBody>
        {table.getRowModel().rows.map(row => (
          <TableRow
            key={row.id}
            onClick={() => onRowClick?.(row.original)}
            className="cursor-pointer hover:bg-muted/30"
          >
            {row.getVisibleCells().map(cell => (
              <TableCell key={cell.id}>
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

Note: the actual shadcn `<Table>` primitive doesn't exist yet either — add via `npx shadcn@latest add table` as part of Build 1.

### 7.3 Inline edit cell pattern

Human-owned cells use a custom renderer:

```tsx
// frontend/src/components/reporting/editable-cell.tsx
function EditableCell({ value, onSave, multiline = false }: EditableCellProps) {
  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState(value);
  // hover → pen icon appears
  // click → input field, blur or Enter saves, Esc cancels
  // optimistic update, PATCH call, rollback on 4xx/5xx
}
```

Agent-owned cells render as plain `<span>` with a subtle `bg-muted/20` tint and no hover affordance. The visual distinction between editable and read-only cells is the user's primary signal for the ownership model — it must be unambiguous at a glance.

## 8. Files to create

### 8.1 Backend (registry/)

| File | Purpose |
|---|---|
| `registry/models.py` (append) | `DevChangelog` SQLAlchemy model matching migration 007 |
| `registry/dev_changelog_schemas.py` | Pydantic: `DevChangelogEntry`, `DevChangelogPatch`, `DevChangelogList` |
| `registry/dev_changelog_endpoints.py` | `GET /api/dev-changelog`, `GET /{slug}`, `PATCH /{slug}` |
| `registry/api.py` (append) | Mount the new router |
| `registry/test_dev_changelog_endpoints.py` | list + get + patch + ownership enforcement (4-6 tests) |

`PATCH` must reject writes to agent-owned fields with 400. Human-owned fields only: `declared_status`, `key_insight`, `notes`, `priority`, `locked`. On successful PATCH, bump `last_human_edit_at = now()` and `updated_at = now()` server-side.

### 8.2 Frontend (frontend/src/)

| File | Purpose |
|---|---|
| `components/ui/data-table.tsx` | TanStack wrapper (Section 7.2) |
| `components/ui/table.tsx` | shadcn `Table` primitive via `npx shadcn add table` |
| `app/admin/reporting/layout.tsx` | Shell for reporting section, masthead-family container |
| `app/admin/reporting/dev-changelog/page.tsx` | Server component: fetch initial data, render `<DevChangelogView>` |
| `components/reporting/dev-changelog-masthead.tsx` | Fraunces italic title + IBM Plex Mono subtitle + metadata bar |
| `components/reporting/dev-changelog-view.tsx` | Client component: holds filter state + view switcher + table |
| `components/reporting/dev-changelog-table.tsx` | Column defs + uses `<DataTable>` wrapper |
| `components/reporting/dev-changelog-filters.tsx` | Left rail: faceted filters (status, category, window) + search + saved views |
| `components/reporting/dev-changelog-detail.tsx` | Right slide-over: commits list, sessions, editable narrative |
| `components/reporting/editable-cell.tsx` | Inline edit primitive used by human-owned columns |
| `components/reporting/commit-list.tsx` | Commits array renderer with GitHub links (used in detail panel) |
| `lib/devChangelogApi.ts` | `listDevChangelog()`, `getDevChangelog(slug)`, `patchDevChangelog(slug, patch)` |
| `stores/dev-changelog-store.ts` | Zustand: filter state, selected slug, optimistic patches, saved views |
| `lib/permissions.ts` (append) | Add `{ path: "/admin/reporting", label: "Reporting", section: "manage", roles: ["admin"] }` |

### 8.3 Column definitions

```tsx
// frontend/src/components/reporting/dev-changelog-table.tsx columns:
const columns: ColumnDef<DevChangelogEntry>[] = [
  // Agent-owned — read-only
  { accessorKey: "slug",            header: "Slug",     cell: MonoCell },
  { accessorKey: "epic",            header: "Epic",     cell: SerifTitleCell }, // Source Serif 4
  { accessorKey: "category",        header: "Cat",      cell: CategoryBadge },
  { accessorKey: "window_start",    header: "Start",    cell: DateCell },
  { accessorKey: "commit_count",    header: "Commits",  cell: TabularNumCell },
  // Display status — COALESCE(declared, detected)
  { id: "display_status",           header: "Status",   cell: StatusPill },
  // Human-owned — editable
  { accessorKey: "declared_status", header: "Override", cell: EditableStatusCell },
  { accessorKey: "priority",        header: "Pri",      cell: EditablePriorityCell },
  { accessorKey: "locked",          header: "🔒",       cell: EditableLockCell },
];
```

`key_insight` and `notes` are edited in the detail slide-over, not inline in the table — they're too long for a row.

## 9. API surface

```
GET  /api/dev-changelog
      query params: status, category, window_start, window_end, q, limit, offset
      returns: DevChangelogList { entries, total }

GET  /api/dev-changelog/{slug}
      returns: DevChangelogEntry (full)

PATCH /api/dev-changelog/{slug}
      body: DevChangelogPatch (human-owned fields only; 400 if agent-owned fields present)
      returns: DevChangelogEntry (with bumped last_human_edit_at, updated_at)
```

The future 3am agent does not use these endpoints. It writes via the existing Registry Agent gateway (`registry_agent.py`) with idempotency keyed on `slug` — same pattern as content agents use for `cme_source_references`, `cme_agent_outputs`, etc. This keeps write paths uniform and reuses the dead-letter queue.

## 10. Build sequence

| Build | Scope | Done when |
|---|---|---|
| **1** | DataTable wrapper + shadcn Table primitive + backend endpoints (GET only) + read-only table view with all 16 rows | Page renders at `/admin/reporting/dev-changelog`, role-gated to admin, shows all 16 seeded entries sorted by `window_start DESC` |
| **2** | Detail slide-over + commit list with GitHub links + session references rendered | Clicking a row opens the detail panel; commits are linkable to `https://github.com/sdnydude/dhgaifactory3.5/commit/{sha}` |
| **3** | PATCH endpoint + inline edit cells + optimistic updates + server-side ownership enforcement | Human-owned fields editable; agent-owned fields render with the read-only tint; 400 errors on attempted agent-field writes; `last_human_edit_at` bumps on save |
| **4** | Faceted filters + search + saved views + Timeline and Kanban view modes | Filters work; saved views persist per-user (localStorage first, DB later); three view modes share one data hook |
| **5** *(future)* | 3am agent that upserts new commits + sessions into `dev_changelog` via Registry Agent gateway; dry-run staging table `dev_changelog_proposed` for the first month | Nightly run produces a diff email; once trustworthy, flip to live writes |

Builds 1-3 can complete in one working session. Build 4 is a second session. Build 5 is a separate feature that depends on the LangGraph telemetry pipeline repair being complete (so the agent's traces are visible).

## 11. Explicit non-goals

- Not retrofitting `agents-library-table.tsx` to TanStack in this feature.
- Not rewriting `docs/TODO.md` yet — it remains the v8 archive; future work updates `dev_changelog` and regenerates TODO as a derived view only if needed.
- No Markdown rendering for `key_insight` in Build 1-4. Plain text with line breaks preserved. Rich editing can come later once the field is used enough to justify it.
- No comment threads, no @mentions, no email notifications on edit. This is a reporting page, not a collaboration surface.
- No export (CSV, JSON) in initial builds. Trivial to add if requested; not prioritized.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Agent overwrites human edits on 3am runs (Build 5) | Schema field-ownership split + `last_human_edit_at` check. Agent only writes agent-owned fields. `locked=true` skips entirely. |
| TanStack adds 40kb to bundle for one page | Accepted; pays back on every future table. Dynamic-import the page if initial load measurably regresses. |
| Inline edit UX feels like a spreadsheet (violating the editorial voice) | Edit affordance is subtle (hover-only pen icon), not omnipresent. Heavy narrative edits happen in the slide-over, not inline. |
| JSONB commits array grows unbounded for long-running epics | Acceptable through 500 commits/epic; at that scale we'd split to a child `dev_changelog_commits` table. Not a Build 1 concern. |
| Migration 007 only lives in a running container; gets lost on rebuild | File is on disk at `registry/alembic/versions/007_add_dev_changelog.py` and will be baked into next image build. Verified. |

## 13. Open questions — resolved or deferred

- ✅ TanStack vs hand-rolled: **TanStack**, first deployment, reusable wrapper.
- ✅ Field ownership model: **split, baked in schema**, `declared_status` overrides `detected_status` via `COALESCE`.
- ✅ Aesthetic direction: **editorial ledger**, hybrid of inbox + mission control vocabularies.
- ⏸ Saved views storage: **localStorage** for Build 4, migrate to DB table when second user (non-Stephen) exists.
- ⏸ 3am agent scheduling: **LangGraph Cloud scheduled runs** (`crons` in `langgraph.json`) — confirmed feature, designed in Build 5.
- ⏸ Timeline view Gantt implementation: **vis-timeline** or **Recharts custom shape** — decided in Build 4.

---

**Next action after approval:** Build 1. Start with `npx shadcn@latest add table` + `npm install @tanstack/react-table`, then backend endpoints (read-only), then frontend read-only table view. All 16 seeded rows should render in the product by end of Build 1.
