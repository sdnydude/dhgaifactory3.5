# Agents Library — Design Spec

**Date:** 2026-04-09
**Status:** Approved
**Comp:** `.superpowers/brainstorm/1592178-1775783086/content/agent-library-comp.html` (dark), `agent-library-light.html` (light)

## Goal

Replace the static, non-interactive `AssistantsRegistry` grid on the `/agents` page with an interactive **Agents Library** — a combined operations dashboard and reference hub for all 17 LangGraph agents. Cards are clickable, opening a slide-over panel with essentials (live stats), dependencies, inputs/outputs, and expandable deep documentation sourced from `DHG-CME-12-Agent-Docs/`.

## Architecture

The Agents Library replaces `AssistantsRegistry` as the default view when no agent is selected. It uses a **hybrid data model**: a static catalog file (`agent-catalog.ts`) provides metadata (name, icon, description, category, dependencies, inputs, outputs, deep docs sections), while live operational stats (run count, success rate, last run, avg duration) come from the existing LangGraph SDK via `agentsApi.ts`. The page supports three switchable layout views (grid, list, table), category filtering, search, and sorting.

## Data Model

### Static Catalog: `frontend/src/lib/agent-catalog.ts`

```typescript
export type AgentCategory = "content" | "recipe" | "qa" | "infra";

export interface AgentCatalogEntry {
  graphId: string;
  name: string;
  icon: string;            // emoji
  description: string;
  category: AgentCategory;
  pipelineOrder: number;   // for default sort
  upstream: string[];      // graphIds of upstream dependencies
  downstream: string[];    // graphIds of downstream dependencies
  inputs: string[];        // e.g. ["therapeutic_area", "disease_state"]
  outputs: string[];       // e.g. ["research_document", "epidemiology_data"]
  deepDocs: {
    executionFlow: string;    // markdown content
    qualityCriteria: string;
    errorHandling: string;
    inputSchema: string;
  };
}

export const AGENT_CATALOG: AgentCatalogEntry[];
```

All 17 agents are cataloged. Deep docs content is derived from `DHG-CME-12-Agent-Docs/` files.

### Live Stats: `frontend/src/lib/agentsApi.ts`

Add a new function to compute per-graph stats from existing thread data:

```typescript
export interface GraphStats {
  graphId: string;
  totalRuns: number;
  successCount: number;
  successRate: number;      // 0-100
  lastRunAt: string | null;
  avgDurationMs: number | null;
}

export async function getGraphStats(): Promise<GraphStats[]>;
```

This queries `client.threads.search()` (already used by `listAllAgents`) and aggregates by `graph_id` from thread metadata. No new API endpoints needed.

### Combined Type

```typescript
export interface AgentLibraryItem extends AgentCatalogEntry {
  stats: GraphStats | null;  // null if no runs yet
}
```

Built by joining `AGENT_CATALOG` entries with `getGraphStats()` results on `graphId`.

## Components

### File Structure

```
frontend/src/components/agents/
├── agents-library.tsx          # Main library component (replaces AssistantsRegistry usage)
├── agents-library-toolbar.tsx  # Filter pills, search, sort, view toggle
├── agents-library-grid.tsx     # Grid view (3-col cards grouped by category)
├── agents-library-list.tsx     # List view (compact rows grouped by category)
├── agents-library-table.tsx    # Table view (sortable columns)
├── agent-slide-over.tsx        # Detail slide-over panel
├── assistants-registry.tsx     # EXISTING — kept for reference, no longer imported
├── agent-tabs.tsx              # EXISTING — unchanged
├── agent-tree.tsx              # EXISTING — unchanged
├── stats-bar.tsx               # EXISTING — unchanged
├── output-slide-over.tsx       # EXISTING — unchanged
```

### agents-library.tsx (Main Component)

- State: `view` (grid | list | table), `category` filter, `search` query, `sort` key, `selectedAgent` (for slide-over), `graphStats` (fetched on mount + 30s poll)
- On mount: fetch `getGraphStats()`, merge with `AGENT_CATALOG`
- Passes filtered/sorted items to the active view component
- Renders `AgentSlideOver` when an agent is selected

### agents-library-toolbar.tsx

- Filter pills: All, Content (9), Recipes (4), QA Gates (2), Infra (2)
- Search input: filters by name and description (client-side)
- Sort dropdown: Pipeline order (default), Alphabetical, Most runs, Recent activity, Success rate
- View toggle: Grid / List / Table buttons

### agents-library-grid.tsx

- Groups items by category with colored category headers
- 3-column responsive grid (`md:grid-cols-2 lg:grid-cols-3`)
- Cards with:
  - Color-coded top border (purple=content, orange=recipe, green=QA, gray=infra)
  - Icon, name, description
  - Stats row: runs, success rate, last run time
- onClick: opens slide-over

### agents-library-list.tsx

- Groups items by category with colored category headers
- Compact rows: icon, name (fixed width), description (flex), run count, success rate
- onClick: opens slide-over

### agents-library-table.tsx

- Sortable columns: Agent, Category, Runs, Last Run, Success Rate, Avg Duration
- Success rate includes a mini progress bar
- Category shown as colored badge
- Click any row: opens slide-over
- Click column header: toggles sort direction

### agent-slide-over.tsx

Uses shadcn `Sheet` (same pattern as existing `OutputSlideOver`). Width: 55vw.

Sections (top to bottom):
1. **Header**: Large icon, agent name, description, close button
2. **Essentials** (2x2 grid of stat cards): Total Runs, Success Rate, Avg Duration, Category
3. **Dependencies**: Upstream/downstream agent names (clickable — opens that agent's slide-over)
4. **Inputs**: Tag pills listing input field names
5. **Outputs**: Tag pills listing output field names
6. **Deep Documentation**: Expandable accordion sections:
   - Execution Flow
   - Quality Criteria
   - Error Handling
   - Input Schema
7. **Run Agent** button (future — initially disabled with tooltip "Coming soon")

## Styling

DHG brand tokens throughout. Both light and dark mode supported via existing Tailwind dark mode classes.

| Element | Light | Dark |
|---------|-------|------|
| Page background | `bg-background` (#FAF9F7) | (#1A1D24) |
| Cards/surfaces | `bg-card` (#FFFFFF) | (#27272A) |
| Borders | `border-border` (#E4E4E7) | (#3F3F46) |
| Text primary | `text-foreground` (#32374A) | (#FAF9F7) |
| Text secondary | `text-muted-foreground` | |
| Content accent | `text-[#663399]` / `bg-[#663399]/10` | `text-[#a78bfa]` / `bg-[#663399]/20` |
| Recipe accent | `text-[#F77E2D]` / `bg-[#F77E2D]/10` | `text-[#fb923c]` / `bg-[#F77E2D]/20` |
| QA accent | `text-[#16a34a]` / `bg-[#22c55e]/10` | `text-[#4ade80]` / `bg-[#22c55e]/20` |
| Infra accent | `text-muted-foreground` / `bg-muted` | |

Category color-coded top borders on cards use gradients matching the comp.

### Visual Polish (Frontend Design Review)

These refinements elevate the comp from functional dashboard to polished product.

#### Typography Precision

Inter is the brand font — exploit its full range:
- **Page title**: Inter Display, weight 600, `letter-spacing: -0.02em`
- **Agent names on cards**: 14px, weight 650 — must pop above descriptions
- **Stats numbers** (runs, rates, durations): weight 700, `font-variant-numeric: tabular-nums` — numbers should feel like instruments, not labels
- **Category headers**: 10px uppercase tracking with a subtle horizontal rule extending to the right edge for visual rhythm

#### Depth & Atmosphere

- **Subtle radial gradient** behind the content area: `radial-gradient(ellipse at 30% 0%, rgba(102,51,153,0.03) 0%, transparent 60%)` — faint purple glow from upper-left. Dark mode uses 0.06 opacity. Subtle enough to be felt, not seen.
- **Noise texture on cards**: CSS-only `::after` pseudo-element with ~1.5% opacity grain pattern. Gives cards physical presence.

#### Motion (3 Key Moments)

1. **Staggered card entry** on page load and view switch: `translateY(8px) → 0` over 350ms, 40ms stagger per card. Tight, fast, professional.
2. **Category-colored hover shadows**: Card hover lifts 2px with shadow picking up the category accent color — purple cards get purple shadow, orange cards get orange shadow. Reinforces taxonomy.
3. **Slide-over content cascade**: Header at 0ms, stat cards stagger at 50ms intervals, dependencies at 200ms, deep docs at 250ms. Creates a reading rhythm.

#### Card Enhancements

- **Health indicator left border**: 3px left border — green if active (run within 24h), amber if stale (no runs in 24h+), transparent if no runs. At-a-glance health status without reading text.
- **Micro success bar**: 3px bar at card bottom showing success rate fill width. Always visible, immediately scannable.

#### Table View — Power User Instrument Panel

- `font-feature-settings: 'tnum'` on all numeric columns for vertical alignment
- Faint alternating row tint for scanability
- Sticky `<thead>` so headers remain visible when scrolling
- Active sort column gets a faint background tint

## Integration with Existing Page

In `frontend/src/app/agents/page.tsx`, replace:

```tsx
// Before
{showRegistry ? (
  <AssistantsRegistry assistants={assistants} />
) : (
  <AgentTabs agent={selectedAgent} state={selectedState} />
)}

// After
{showRegistry ? (
  <AgentsLibrary />
) : (
  <AgentTabs agent={selectedAgent} state={selectedState} />
)}
```

`AgentsLibrary` manages its own data fetching (graph stats) and local UI state (view mode, filters, search, sort, slide-over). It does not modify the Zustand `agents-store` — the existing `AgentTree` sidebar and `StatsBar` continue working as before.

## What Is NOT Changing

- `AgentTree` left sidebar — unchanged
- `StatsBar` top bar — unchanged  
- `AgentTabs` detail view (selected running agent) — unchanged
- `agents-store.ts` Zustand store — unchanged
- `agentsApi.ts` existing functions — unchanged (only adding `getGraphStats`)
- Polling intervals — unchanged
- Output slide-over — unchanged

## Registry Database: Frontend Design Specs

New table `frontend_design_specs` in the registry database stores approved design specs for frontend features. This creates an auditable, queryable record of all UI design decisions.

### Table: `frontend_design_specs`

```sql
CREATE TABLE frontend_design_specs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  feature_name    VARCHAR(255) NOT NULL,         -- e.g. "Agents Library"
  slug            VARCHAR(255) NOT NULL UNIQUE,  -- e.g. "agents-library"
  status          VARCHAR(50)  NOT NULL DEFAULT 'draft',  -- draft | approved | implemented | superseded
  spec_path       VARCHAR(512) NOT NULL,         -- path to spec file in repo
  comp_path       VARCHAR(512),                  -- path to HTML comp file(s)
  description     TEXT NOT NULL,                  -- one-paragraph summary
  components      JSONB NOT NULL DEFAULT '[]',   -- list of component file paths
  design_tokens   JSONB NOT NULL DEFAULT '{}',   -- color/typography/spacing tokens used
  visual_polish   JSONB NOT NULL DEFAULT '{}',   -- motion, depth, texture details
  approved_by     VARCHAR(255),                  -- who approved
  approved_at     TIMESTAMP WITH TIME ZONE,
  implemented_at  TIMESTAMP WITH TIME ZONE,
  created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
```

### Alembic Migration: `006_add_frontend_design_specs.py`

- Revision: `006`
- Down revision: `005`
- Creates `frontend_design_specs` table
- Seeds the first row for the Agents Library spec

### SQLAlchemy Model

Add `FrontendDesignSpec` class to `registry/models.py` following existing patterns.

### API Endpoints (on registry)

Add to a new or existing endpoint file:
- `GET /api/v1/frontend-specs` — list all specs
- `GET /api/v1/frontend-specs/{slug}` — get spec by slug
- `POST /api/v1/frontend-specs` — create new spec
- `PATCH /api/v1/frontend-specs/{slug}` — update spec (e.g., mark implemented)

### First Record (Seeded in Migration)

```json
{
  "feature_name": "Agents Library",
  "slug": "agents-library",
  "status": "approved",
  "spec_path": "docs/superpowers/specs/2026-04-09-agents-library-design.md",
  "comp_path": ".superpowers/brainstorm/1592178-1775783086/content/agent-library-comp.html",
  "description": "Interactive Agents Library replacing static AssistantsRegistry. Three layout views (grid/list/table), category filtering, search, sorting, slide-over detail panel with live stats and deep documentation. Hybrid data model: static catalog + live LangGraph stats.",
  "components": [
    "frontend/src/components/agents/agents-library.tsx",
    "frontend/src/components/agents/agents-library-toolbar.tsx",
    "frontend/src/components/agents/agents-library-grid.tsx",
    "frontend/src/components/agents/agents-library-list.tsx",
    "frontend/src/components/agents/agents-library-table.tsx",
    "frontend/src/components/agents/agent-slide-over.tsx",
    "frontend/src/lib/agent-catalog.ts"
  ],
  "design_tokens": {
    "content_accent": "#663399",
    "recipe_accent": "#F77E2D",
    "qa_accent": "#22c55e",
    "infra_accent": "#71717a",
    "font": "Inter Display + Inter",
    "card_entry_stagger_ms": 40,
    "card_entry_duration_ms": 350
  },
  "visual_polish": {
    "background_gradient": "radial-gradient(ellipse at 30% 0%, rgba(102,51,153,0.03), transparent 60%)",
    "card_noise_texture": true,
    "staggered_entry_animation": true,
    "category_colored_hover_shadows": true,
    "slideover_content_cascade": true,
    "health_indicator_left_border": true,
    "micro_success_bar": true,
    "table_sticky_header": true,
    "table_sort_column_highlight": true
  },
  "approved_by": "Stephen Webber",
  "approved_at": "2026-04-09T21:00:00Z"
}
```

## Dependencies

- shadcn/ui components: `Sheet`, `Badge`, `Button`, `Input`, `Select`, `Collapsible`
- lucide-react icons (already installed)
- No new npm packages required

## Testing

### Frontend
- Verify all 17 agents render in grid, list, and table views
- Verify category filter reduces visible agents correctly
- Verify search filters by name and description
- Verify sort options reorder agents
- Verify slide-over opens with correct agent data
- Verify slide-over expandable sections toggle
- Verify dependency links in slide-over navigate to the correct agent
- Verify live stats update on 30s poll interval
- Verify graceful fallback when LangGraph API is unavailable (show catalog without stats)
- Verify both light and dark mode rendering
- Verify staggered card entry animation on page load and view switch
- Verify category-colored hover shadows match card category
- Verify slide-over content cascade animation

### Database
- Verify `frontend_design_specs` table exists after migration
- Verify Agents Library seed record is present
- Verify CRUD API endpoints work (list, get by slug, create, update)
- Verify slug uniqueness constraint
