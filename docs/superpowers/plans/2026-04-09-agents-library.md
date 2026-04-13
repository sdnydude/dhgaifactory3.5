# Agents Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static `AssistantsRegistry` card grid on the Agents page with a rich, interactive Agents Library featuring three switchable views (grid, list, table), category filtering, search, sortable columns, live stats polling, and a detail slide-over panel with deep documentation for each of the 17 registered LangGraph graphs.

**Architecture:** A static catalog file (`agent-catalog.ts`) defines all 17 agents with metadata, descriptions, dependency graphs, I/O tags, and deep documentation sections derived from the agent spec files. A new `getGraphStats()` function queries LangGraph threads and computes per-graph run statistics. The main `AgentsLibrary` container merges static catalog data with live stats, applies toolbar filters/search/sort, and renders the active view. A separate `frontend_design_specs` table in PostgreSQL stores the design specification metadata with CRUD API endpoints. A detail slide-over panel provides drill-down into any agent.

**Tech Stack:** TypeScript, React, Next.js, Zustand, shadcn/ui (Sheet, Collapsible, Badge, Button, Input, Select, Tabs, Tooltip, Card, Progress, Skeleton), Tailwind CSS, CSS keyframe animations, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 15

**Spec:** This document serves as both plan and spec.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `registry/alembic/versions/006_add_frontend_design_specs.py` | Create | Alembic migration: create `frontend_design_specs` table + seed |
| `registry/models.py` | Modify | Add `FrontendDesignSpec` SQLAlchemy model |
| `registry/frontend_specs_endpoints.py` | Create | CRUD API endpoints at `/api/v1/frontend-specs` |
| `registry/api.py` | Modify | Include `frontend_specs_router` |
| `frontend/src/lib/agent-catalog.ts` | Create | Static catalog of all 17 agents with deep docs |
| `frontend/src/lib/agentsApi.ts` | Modify | Add `getGraphStats()` function and `GraphStats` interface |
| `frontend/src/components/agents/agents-library-toolbar.tsx` | Create | Toolbar: category pills, search, sort, view toggle |
| `frontend/src/components/agents/agents-library-grid.tsx` | Create | Grid view: 3-col cards grouped by category |
| `frontend/src/components/agents/agents-library-list.tsx` | Create | List view: compact grouped rows |
| `frontend/src/components/agents/agents-library-table.tsx` | Create | Table view: sortable columns, sticky header |
| `frontend/src/components/agents/agent-slide-over.tsx` | Create | Detail slide-over with stats, deps, deep docs |
| `frontend/src/components/agents/agents-library.tsx` | Create | Main container: state, polling, filter/sort, CSS animations |
| `frontend/src/app/agents/page.tsx` | Modify | Swap `AssistantsRegistry` for `AgentsLibrary` |

---

### Task 1: Database Migration (006)

**Files:**
- Create: `registry/alembic/versions/006_add_frontend_design_specs.py`

- [ ] **Step 1: Create the Alembic migration file**

```python
"""Add frontend_design_specs table

Revision ID: 006
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "frontend_design_specs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("feature_name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("spec_path", sa.String(512), nullable=False),
        sa.Column("comp_path", sa.String(512), nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("components", JSONB, server_default="[]"),
        sa.Column("design_tokens", JSONB, server_default="{}"),
        sa.Column("visual_polish", JSONB, server_default="{}"),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("implemented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.execute("""
        INSERT INTO frontend_design_specs (
            feature_name, slug, status, spec_path, comp_path, description,
            components, design_tokens, visual_polish
        ) VALUES (
            'Agents Library',
            'agents-library',
            'approved',
            'docs/superpowers/specs/2026-04-09-agents-library-design.md',
            'frontend/src/components/agents/',
            'Interactive agent catalog with grid/list/table views, category filtering, search, live stats, and detail slide-over panel for all 17 LangGraph graphs.',
            '["agents-library.tsx","agents-library-toolbar.tsx","agents-library-grid.tsx","agents-library-list.tsx","agents-library-table.tsx","agent-slide-over.tsx"]'::jsonb,
            '{"category_colors":{"content":"#663399","recipe":"#F77E2D","qa":"#22c55e","infra":"#71717a"},"animation_stagger_ms":40,"animation_duration_ms":350}'::jsonb,
            '{"card_entry_animation":true,"category_hover_shadows":true,"radial_gradient_bg":true,"health_indicator_border":true,"micro_success_bar":true,"table_sticky_header":true}'::jsonb
        );
    """)


def downgrade():
    op.drop_table("frontend_design_specs")
```

- [ ] **Step 2: Run the migration and verify**

```bash
docker exec dhg-registry-db psql -U dhg -d dhg_registry -c "SELECT current_setting('server_version');"
# Expected: PostgreSQL 15.x

docker exec dhg-registry-api alembic upgrade head
# Expected: INFO  [alembic.runtime.migration] Running upgrade 005 -> 006, Add frontend_design_specs table

docker exec dhg-registry-db psql -U dhg -d dhg_registry -c "\d frontend_design_specs"
# Expected: Table columns listed

docker exec dhg-registry-db psql -U dhg -d dhg_registry -c "SELECT feature_name, slug, status FROM frontend_design_specs;"
# Expected:
#  feature_name   |      slug       | status
# ----------------+-----------------+---------
#  Agents Library | agents-library  | approved
```

- [ ] **Step 3: Commit**

```bash
git add registry/alembic/versions/006_add_frontend_design_specs.py
git commit -m "feat(db): add frontend_design_specs table (migration 006)"
```

---

### Task 2: SQLAlchemy Model

**Files:**
- Modify: `registry/models.py`

- [ ] **Step 1: Add `FrontendDesignSpec` model to models.py**

Add the following class at the end of `registry/models.py`, after the `SecurityAuditLog` class:

```python
# =============================================================================
# FRONTEND DESIGN SPEC MODELS
# =============================================================================

class FrontendDesignSpec(Base):
    """Tracks frontend feature design specs with component lists and visual polish config."""
    __tablename__ = "frontend_design_specs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    status = Column(String(50), default="draft")  # draft / approved / implemented
    spec_path = Column(String(512), nullable=False)
    comp_path = Column(String(512), nullable=True)
    description = Column(Text, nullable=False)
    components = Column(JSONB, default=[])
    design_tokens = Column(JSONB, default={})
    visual_polish = Column(JSONB, default={})
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    implemented_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

- [ ] **Step 2: Verify the model imports work**

```bash
docker exec dhg-registry-api python -c "from models import FrontendDesignSpec; print(FrontendDesignSpec.__tablename__)"
# Expected: frontend_design_specs
```

- [ ] **Step 3: Commit**

```bash
git add registry/models.py
git commit -m "feat(models): add FrontendDesignSpec SQLAlchemy model"
```

---

### Task 3: API Endpoints

**Files:**
- Create: `registry/frontend_specs_endpoints.py`

- [ ] **Step 1: Create `frontend_specs_endpoints.py` with CRUD endpoints**

```python
"""
Frontend Design Specs API — CRUD for design spec tracking.
"""
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from models import FrontendDesignSpec

logger = logging.getLogger("dhg.frontend_specs")

router = APIRouter(prefix="/api/v1/frontend-specs", tags=["frontend-specs"])


# =============================================================================
# SCHEMAS
# =============================================================================

class SpecCreate(BaseModel):
    feature_name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    status: str = Field(default="draft", max_length=50)
    spec_path: str = Field(..., max_length=512)
    comp_path: Optional[str] = Field(default=None, max_length=512)
    description: str
    components: list = Field(default_factory=list)
    design_tokens: dict = Field(default_factory=dict)
    visual_polish: dict = Field(default_factory=dict)


class SpecUpdate(BaseModel):
    feature_name: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = Field(default=None, max_length=50)
    spec_path: Optional[str] = Field(default=None, max_length=512)
    comp_path: Optional[str] = Field(default=None, max_length=512)
    description: Optional[str] = None
    components: Optional[list] = None
    design_tokens: Optional[dict] = None
    visual_polish: Optional[dict] = None
    approved_by: Optional[str] = Field(default=None, max_length=255)
    approved_at: Optional[datetime] = None
    implemented_at: Optional[datetime] = None


class SpecResponse(BaseModel):
    id: UUID
    feature_name: str
    slug: str
    status: str
    spec_path: str
    comp_path: Optional[str]
    description: str
    components: list
    design_tokens: dict
    visual_polish: dict
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    implemented_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=List[SpecResponse])
async def list_specs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """List all frontend design specs."""
    specs = db.query(FrontendDesignSpec).offset(skip).limit(limit).all()
    return specs


@router.get("/{slug}", response_model=SpecResponse)
async def get_spec_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get a frontend design spec by slug."""
    spec = db.query(FrontendDesignSpec).filter(FrontendDesignSpec.slug == slug).first()
    if not spec:
        raise HTTPException(status_code=404, detail=f"Spec with slug '{slug}' not found")
    return spec


@router.post("", response_model=SpecResponse, status_code=status.HTTP_201_CREATED)
async def create_spec(payload: SpecCreate, db: Session = Depends(get_db)):
    """Create a new frontend design spec."""
    existing = db.query(FrontendDesignSpec).filter(FrontendDesignSpec.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Spec with slug '{payload.slug}' already exists")
    spec = FrontendDesignSpec(**payload.model_dump())
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return spec


@router.patch("/{slug}", response_model=SpecResponse)
async def update_spec(slug: str, payload: SpecUpdate, db: Session = Depends(get_db)):
    """Update an existing frontend design spec."""
    spec = db.query(FrontendDesignSpec).filter(FrontendDesignSpec.slug == slug).first()
    if not spec:
        raise HTTPException(status_code=404, detail=f"Spec with slug '{slug}' not found")
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(spec, field, value)
    db.commit()
    db.refresh(spec)
    return spec
```

- [ ] **Step 2: Verify syntax**

```bash
docker exec dhg-registry-api python -c "import frontend_specs_endpoints; print('OK')"
# Expected: OK
```

- [ ] **Step 3: Commit**

```bash
git add registry/frontend_specs_endpoints.py
git commit -m "feat(api): add frontend design specs CRUD endpoints"
```

---

### Task 4: Wire API Router

**Files:**
- Modify: `registry/api.py`

- [ ] **Step 1: Add the frontend specs router import and include**

In `registry/api.py`, add the import after line 269 (the `from security_endpoints import ...` line):

```python
from frontend_specs_endpoints import router as frontend_specs_router
```

Add the include after line 280 (the `app.include_router(security_router)` line):

```python
app.include_router(frontend_specs_router)
```

The resulting block (lines ~262-282) should read:

```python
# Import routers
from agent_endpoints import router as agent_router
from antigravity_endpoints import router as antigravity_router
from research_endpoints import router as research_router
from claude_endpoints import router as claude_router
from cme_endpoints import router as cme_router
from import_api import router as import_router
from search_api import router as search_router
from security_endpoints import router as security_router
from frontend_specs_endpoints import router as frontend_specs_router

# Include routers
app.include_router(agent_router)
app.include_router(antigravity_router)
app.include_router(research_router)
app.include_router(claude_router)
app.include_router(cme_router)
app.include_router(import_router)
app.include_router(search_router)
app.include_router(security_router)
app.include_router(frontend_specs_router)
```

- [ ] **Step 2: Verify the API starts and the endpoint responds**

```bash
docker compose restart dhg-registry-api
# Wait a few seconds for startup

curl -s http://localhost:8011/api/v1/frontend-specs | python3 -m json.tool
# Expected: JSON array with one object (the seeded Agents Library spec)

curl -s http://localhost:8011/api/v1/frontend-specs/agents-library | python3 -m json.tool
# Expected: JSON object with feature_name "Agents Library"
```

- [ ] **Step 3: Commit**

```bash
git add registry/api.py
git commit -m "feat(api): wire frontend-specs router into registry API"
```

---

### Task 5: Agent Catalog

**Files:**
- Create: `frontend/src/lib/agent-catalog.ts`

- [ ] **Step 1: Create the static agent catalog file**

```typescript
/**
 * Static catalog of all 17 registered LangGraph graphs.
 * graphId values match exactly the keys in langgraph.json.
 */

export type AgentCategory = "content" | "recipe" | "qa" | "infra";

export interface AgentDeepDocs {
  executionFlow: string;
  qualityCriteria: string;
  errorHandling: string;
  inputSchema: string;
}

export interface AgentCatalogEntry {
  graphId: string;
  name: string;
  icon: string;
  description: string;
  category: AgentCategory;
  pipelineOrder: number;
  upstream: string[];
  downstream: string[];
  inputs: string[];
  outputs: string[];
  deepDocs: AgentDeepDocs;
}

export const AGENT_CATALOG: AgentCatalogEntry[] = [
  // =========================================================================
  // CONTENT AGENTS
  // =========================================================================
  {
    graphId: "research",
    name: "Research Agent",
    icon: "\uD83D\uDD2C", // microscope
    description: "Literature review, epidemiology, and market intelligence gathering with 30+ citations.",
    category: "content",
    pipelineOrder: 1,
    upstream: [],
    downstream: ["gap_analysis", "needs_assessment", "grant_writer"],
    inputs: ["therapeutic_area", "disease_state", "target_audience", "geographic_focus", "supporter_company", "known_gaps"],
    outputs: ["research_output"],
    deepDocs: {
      executionFlow:
        "1. Parse intake form for therapeutic area and disease state\n" +
        "2. Execute PubMed and Perplexity literature searches (30+ sources target)\n" +
        "3. Compile epidemiology data: prevalence, incidence, demographics, burden\n" +
        "4. Analyze economic burden: direct costs, indirect costs, healthcare utilization\n" +
        "5. Map treatment landscape: current therapies, pipeline agents, guideline evolution\n" +
        "6. Identify market context: competitor products, supporter product positioning\n" +
        "7. Synthesize evidence gaps and emerging research directions\n" +
        "8. Assemble structured research report with full citation list",
      qualityCriteria:
        "- Minimum 30 unique cited sources\n" +
        "- All epidemiology data includes recency (within 3 years preferred)\n" +
        "- Economic data cites specific dollar amounts with source attribution\n" +
        "- Treatment landscape covers both guideline-recommended and real-world use\n" +
        "- No unsupported claims; every statistic has a citation",
      errorHandling:
        "- PubMed API timeout: retry up to 3 times with exponential backoff\n" +
        "- Insufficient sources (<15): log warning, proceed with available data, flag in metadata\n" +
        "- Perplexity unavailable: fall back to PubMed-only search\n" +
        "- 5-minute total execution timeout with graceful partial output",
      inputSchema:
        "therapeutic_area: string (required) -- Primary research domain\n" +
        "disease_state: string (required) -- Specific condition\n" +
        "target_audience: string -- Specialty context for relevance filtering\n" +
        "geographic_focus: string -- Regional epidemiology selection\n" +
        "supporter_company: string -- Market intelligence focus\n" +
        "supporter_products: string[] -- Product landscape context\n" +
        "known_gaps: string[] -- Directed research areas\n" +
        "competitor_products: string[] -- Competitive landscape",
    },
  },
  {
    graphId: "clinical_practice",
    name: "Clinical Practice Agent",
    icon: "\uD83C\uDFE5", // hospital
    description: "Standard-of-care analysis, practice patterns, and barrier identification.",
    category: "content",
    pipelineOrder: 1,
    upstream: [],
    downstream: ["gap_analysis"],
    inputs: ["therapeutic_area", "disease_state", "target_audience", "practice_settings", "known_barriers"],
    outputs: ["clinical_output"],
    deepDocs: {
      executionFlow:
        "1. Analyze current clinical guidelines for the therapeutic area\n" +
        "2. Map standard-of-care diagnostic and treatment pathways\n" +
        "3. Identify real-world practice deviations from guidelines\n" +
        "4. Categorize barriers: knowledge, competence, performance, system-level\n" +
        "5. Quantify practice-guideline deltas with supporting data\n" +
        "6. Assess geographic and setting-based variations\n" +
        "7. Compile barrier impact analysis on patient outcomes",
      qualityCriteria:
        "- Clear separation of guideline-recommended vs actual practice\n" +
        "- Each barrier categorized using established taxonomy\n" +
        "- Practice deviations quantified (percentages, frequencies)\n" +
        "- Quality metrics include established measures and benchmarks\n" +
        "- Regional/setting variations documented when available",
      errorHandling:
        "- Guideline data not found: use most recent available, note currency in metadata\n" +
        "- Practice pattern data sparse: flag confidence level in output\n" +
        "- 5-minute execution timeout with partial output capture",
      inputSchema:
        "therapeutic_area: string (required)\n" +
        "disease_state: string (required)\n" +
        "target_audience: string\n" +
        "practice_settings: string[] -- Care environment context\n" +
        "geographic_focus: string\n" +
        "known_gaps: string[]\n" +
        "known_barriers: string[]",
    },
  },
  {
    graphId: "gap_analysis",
    name: "Gap Analysis Agent",
    icon: "\uD83D\uDD0D", // magnifying glass
    description: "Synthesizes research and clinical data into 5+ evidence-based, prioritized educational gaps.",
    category: "content",
    pipelineOrder: 2,
    upstream: ["research", "clinical_practice"],
    downstream: ["needs_assessment", "learning_objectives"],
    inputs: ["research_output", "clinical_output", "known_gaps", "educational_priorities"],
    outputs: ["gap_analysis_output"],
    deepDocs: {
      executionFlow:
        "1. Ingest research output (epidemiology, evidence, treatment landscape)\n" +
        "2. Ingest clinical practice output (practice patterns, barriers, deviations)\n" +
        "3. Cross-reference evidence with practice to identify disconnects\n" +
        "4. Generate minimum 5 prioritized educational gaps\n" +
        "5. Quantify each gap: guideline recommendation vs current practice delta\n" +
        "6. Categorize barriers per gap (knowledge, competence, performance, system)\n" +
        "7. Assess patient impact for each gap\n" +
        "8. Prioritize by addressability through education and impact severity",
      qualityCriteria:
        "- Minimum 5 distinct gaps identified\n" +
        "- Each gap has quantified practice-guideline delta\n" +
        "- Barrier categorization uses established taxonomy\n" +
        "- Patient impact stated with supporting evidence\n" +
        "- Priority ranking justified with clear rationale",
      errorHandling:
        "- Missing upstream output: cannot proceed, return error with missing dependency\n" +
        "- Fewer than 5 gaps identified: retry with broadened scope up to 3 times\n" +
        "- Insufficient quantification: flag gaps as qualitative-only in metadata",
      inputSchema:
        "research_output: object (required) -- Full research agent output\n" +
        "clinical_output: object (required) -- Full clinical practice output\n" +
        "known_gaps: string[] -- Pre-identified gaps from intake\n" +
        "educational_priorities: string[] -- Supporter priorities\n" +
        "outcome_goals: string[] -- Desired impact areas",
    },
  },
  {
    graphId: "needs_assessment",
    name: "Needs Assessment Agent",
    icon: "\uD83D\uDCDD", // memo
    description: "Flagship 3,100+ word narrative document with cold open framework and character thread.",
    category: "content",
    pipelineOrder: 3,
    upstream: ["gap_analysis", "research", "clinical_practice"],
    downstream: ["learning_objectives", "prose_quality"],
    inputs: ["gap_analysis_output", "research_output", "clinical_output", "therapeutic_area", "activity_title"],
    outputs: ["needs_assessment_output"],
    deepDocs: {
      executionFlow:
        "1. Receive prioritized gaps, research evidence, and clinical practice data\n" +
        "2. Construct cold open: create character (patient or clinician), humanizing detail, turn statement\n" +
        "3. Weave character thread through minimum 4 document appearances\n" +
        "4. Write 3,100+ word narrative integrating all gaps with evidence\n" +
        "5. Ensure prose density >= 80% (flowing prose vs lists/bullets)\n" +
        "6. Embed citations throughout from research output\n" +
        "7. Assemble complete document with section structure\n" +
        "8. Compute quality metrics: word count, prose density, citation count, character appearances",
      qualityCriteria:
        "- Minimum 3,100 words total\n" +
        "- Cold open: 50-100 words with character name, age, humanizing detail, turn statement\n" +
        "- Character thread: minimum 4 appearances across sections\n" +
        "- Prose density >= 80%\n" +
        "- All gaps from gap analysis represented\n" +
        "- Pharmaceutical grant reviewer-ready quality",
      errorHandling:
        "- Word count below 3,100: retry generation with explicit expansion instructions\n" +
        "- Prose density below 80%: re-write list-heavy sections as flowing paragraphs\n" +
        "- Character thread < 4 appearances: add character references in revision pass\n" +
        "- 5-minute timeout with checkpoint save",
      inputSchema:
        "gap_analysis_output: object (required) -- Prioritized gaps with evidence\n" +
        "research_output: object (required) -- Epidemiology, literature, market context\n" +
        "clinical_output: object (required) -- Practice patterns, barriers\n" +
        "therapeutic_area: string\n" +
        "disease_state: string\n" +
        "target_audience: string\n" +
        "activity_title: string\n" +
        "accreditation_types: string[]",
    },
  },
  {
    graphId: "learning_objectives",
    name: "Learning Objectives Agent",
    icon: "\uD83C\uDFAF", // target
    description: "6+ measurable objectives mapped to Moore's Expanded Outcomes Framework.",
    category: "content",
    pipelineOrder: 4,
    upstream: ["needs_assessment", "gap_analysis"],
    downstream: ["curriculum_design", "research_protocol", "marketing_plan"],
    inputs: ["needs_assessment_output", "gap_analysis_output", "target_audience", "educational_format"],
    outputs: ["learning_objectives_output"],
    deepDocs: {
      executionFlow:
        "1. Receive revised needs assessment and prioritized gaps\n" +
        "2. Apply Moore's Expanded Outcomes Framework taxonomy\n" +
        "3. Generate minimum 6 measurable learning objectives\n" +
        "4. Map each objective to a specific gap\n" +
        "5. Assign Moore level (3a-6) with appropriate action verbs\n" +
        "6. Define measurement methodology for each objective\n" +
        "7. Distribute objectives across Moore levels with rationale\n" +
        "8. Verify gap coverage is complete",
      qualityCriteria:
        "- Minimum 6 objectives\n" +
        "- Each objective traces to an identified gap\n" +
        "- Moore level specified with correct action verb taxonomy\n" +
        "- Measurement methodology defined and practical\n" +
        "- Level distribution includes higher-order outcomes (Level 4+)",
      errorHandling:
        "- Fewer than 6 objectives: expand from highest-priority gaps\n" +
        "- Missing gap mapping: reject and retry with explicit gap-objective alignment\n" +
        "- Invalid Moore level verbs: auto-correct from framework verb list",
      inputSchema:
        "needs_assessment_output: object (required)\n" +
        "gap_analysis_output: object (required)\n" +
        "target_audience: string\n" +
        "educational_format: string\n" +
        "outcome_goals: string[]\n" +
        "moore_level_target: string -- Target outcome level",
    },
  },
  {
    graphId: "curriculum_design",
    name: "Curriculum Design Agent",
    icon: "\uD83D\uDCDA", // books
    description: "Educational design specification with format, structure, and innovation rationale.",
    category: "content",
    pipelineOrder: 5,
    upstream: ["learning_objectives", "gap_analysis", "needs_assessment"],
    downstream: ["grant_writer"],
    inputs: ["learning_objectives_output", "gap_analysis_output", "target_audience", "educational_format", "duration"],
    outputs: ["curriculum_output"],
    deepDocs: {
      executionFlow:
        "1. Review learning objectives with Moore levels and measurement\n" +
        "2. Select primary educational format and modality\n" +
        "3. Design session structure with time allocation\n" +
        "4. Specify instructional methods aligned to objective levels\n" +
        "5. Define faculty requirements and specifications\n" +
        "6. Create assessment strategy mapped to objectives\n" +
        "7. Write innovation section justifying educational approach\n" +
        "8. Compile complete curriculum specification",
      qualityCriteria:
        "- Format selection justified with pedagogical rationale\n" +
        "- Every learning objective has a corresponding instructional method\n" +
        "- Assessment strategy maps to measurement methodology\n" +
        "- Innovation section demonstrates differentiation from standard CME\n" +
        "- Faculty specs include specialty, experience level, and role",
      errorHandling:
        "- Objective-method mismatch: realign and regenerate affected sections\n" +
        "- Duration constraints violated: rebalance session structure\n" +
        "- Innovation section too generic: retry with specific pedagogical references",
      inputSchema:
        "learning_objectives_output: object (required)\n" +
        "gap_analysis_output: object (required)\n" +
        "needs_assessment_output: object\n" +
        "target_audience: string\n" +
        "practice_settings: string[]\n" +
        "educational_format: string\n" +
        "innovation_elements: string[]\n" +
        "duration: string\n" +
        "modality: string",
    },
  },
  {
    graphId: "research_protocol",
    name: "Research Protocol Agent",
    icon: "\uD83E\uDDEA", // test tube
    description: "IRB-ready educational outcomes research protocol with study design and endpoints.",
    category: "content",
    pipelineOrder: 5,
    upstream: ["learning_objectives", "gap_analysis", "curriculum_design"],
    downstream: ["grant_writer"],
    inputs: ["learning_objectives_output", "gap_analysis_output", "target_audience", "estimated_reach"],
    outputs: ["protocol_output"],
    deepDocs: {
      executionFlow:
        "1. Define study type as educational outcomes research\n" +
        "2. Establish primary and secondary endpoints from learning objectives\n" +
        "3. Design study methodology (pre-post, longitudinal, comparative)\n" +
        "4. Define study population from target audience\n" +
        "5. Calculate sample size from estimated reach\n" +
        "6. Create data collection instruments (surveys, knowledge assessments)\n" +
        "7. Define analysis plan with statistical methods\n" +
        "8. Write protocol narrative suitable for IRB review",
      qualityCriteria:
        "- Primary endpoint clearly defined and measurable\n" +
        "- Study design appropriate for educational intervention\n" +
        "- Sample size justified with rationale\n" +
        "- Data collection instruments described in detail\n" +
        "- Analysis plan includes specific statistical tests",
      errorHandling:
        "- Missing learning objectives: cannot proceed, return dependency error\n" +
        "- Sample size too small for significance: flag in protocol with limitations\n" +
        "- Endpoint measurement infeasible: propose alternative measurement approach",
      inputSchema:
        "learning_objectives_output: object (required)\n" +
        "gap_analysis_output: object (required)\n" +
        "curriculum_output: object\n" +
        "target_audience: string\n" +
        "estimated_reach: number\n" +
        "outcome_goals: string[]\n" +
        "moore_level_target: string\n" +
        "measurement_preferences: string[]",
    },
  },
  {
    graphId: "marketing_plan",
    name: "Marketing Plan Agent",
    icon: "\uD83D\uDCE3", // megaphone
    description: "Multi-channel audience generation strategy with budget allocation and timeline.",
    category: "content",
    pipelineOrder: 5,
    upstream: ["learning_objectives", "needs_assessment"],
    downstream: ["grant_writer"],
    inputs: ["learning_objectives_output", "needs_assessment_output", "target_audience", "marketing_budget"],
    outputs: ["marketing_output"],
    deepDocs: {
      executionFlow:
        "1. Define target audience profile from intake and upstream data\n" +
        "2. Estimate audience universe size by specialty and geography\n" +
        "3. Select marketing channels (digital, email, social, society, KOL)\n" +
        "4. Allocate budget across channels with ROI projection\n" +
        "5. Create channel-specific strategies and messaging\n" +
        "6. Build timeline from launch date backward\n" +
        "7. Define KPIs and measurement for each channel\n" +
        "8. Compile comprehensive marketing plan document",
      qualityCriteria:
        "- Channel selection justified with audience reach data\n" +
        "- Budget allocation totals match marketing_budget input\n" +
        "- Projected reach is realistic and supported by channel benchmarks\n" +
        "- Timeline includes specific milestones and deadlines\n" +
        "- KPIs defined for each channel with measurement method",
      errorHandling:
        "- Budget not specified: use industry benchmarks, flag assumption\n" +
        "- Audience universe too small: recommend broader targeting, document rationale\n" +
        "- Channel data unavailable: use conservative reach estimates",
      inputSchema:
        "learning_objectives_output: object\n" +
        "needs_assessment_output: object\n" +
        "target_audience: string (required)\n" +
        "practice_settings: string[]\n" +
        "geographic_focus: string\n" +
        "estimated_reach: number\n" +
        "marketing_budget: number\n" +
        "marketing_channels: string[]\n" +
        "launch_date: string",
    },
  },
  {
    graphId: "grant_writer",
    name: "Grant Writer Agent",
    icon: "\uD83D\uDCBC", // briefcase
    description: "Assembles all upstream outputs into a cohesive, submission-ready grant package.",
    category: "content",
    pipelineOrder: 6,
    upstream: ["needs_assessment", "learning_objectives", "curriculum_design", "research_protocol", "marketing_plan"],
    downstream: ["prose_quality"],
    inputs: ["needs_assessment_output", "learning_objectives_output", "curriculum_output", "protocol_output", "marketing_output"],
    outputs: ["grant_package_output"],
    deepDocs: {
      executionFlow:
        "1. Collect all upstream agent outputs\n" +
        "2. Verify completeness: all required sections present\n" +
        "3. Write cover letter with recipient, date, signatory\n" +
        "4. Assemble executive summary from across all sections\n" +
        "5. Integrate needs assessment, objectives, curriculum, protocol, marketing\n" +
        "6. Ensure cross-section consistency (terminology, data, narrative)\n" +
        "7. Add budget breakdown and organizational credentials\n" +
        "8. Produce final formatted grant package document",
      qualityCriteria:
        "- All upstream sections included without truncation\n" +
        "- Cross-section terminology is consistent\n" +
        "- Cover letter is 300-400 words, professional tone\n" +
        "- Narrative thread from needs assessment carries through\n" +
        "- Budget figures match requested amount",
      errorHandling:
        "- Missing upstream section: cannot proceed, return dependency list\n" +
        "- Inconsistent data across sections: flag conflicts, use most recent source\n" +
        "- Word count exceeds typical limits: summarize least critical sections",
      inputSchema:
        "needs_assessment_output: object (required)\n" +
        "learning_objectives_output: object (required)\n" +
        "curriculum_output: object (required)\n" +
        "protocol_output: object (required)\n" +
        "marketing_output: object (required)\n" +
        "gap_analysis_output: object -- For reference\n" +
        "research_output: object -- For citation reference\n" +
        "project_title: string\n" +
        "supporter_company: string\n" +
        "requested_amount: number\n" +
        "budget_breakdown: object",
    },
  },

  // =========================================================================
  // QA GATE AGENTS
  // =========================================================================
  {
    graphId: "prose_quality",
    name: "Prose Quality Agent",
    icon: "\u2728", // sparkles
    description: "De-AI-ification scoring, banned pattern detection, prose density validation.",
    category: "qa",
    pipelineOrder: 7,
    upstream: ["needs_assessment", "grant_writer"],
    downstream: ["compliance_review"],
    inputs: ["needs_assessment_output", "grant_package_output"],
    outputs: ["prose_quality_pass_1", "prose_quality_pass_2"],
    deepDocs: {
      executionFlow:
        "1. Receive document (needs assessment for Pass 1, full package for Pass 2)\n" +
        "2. Scan for banned AI writing patterns (e.g., 'delve', 'it is important to note')\n" +
        "3. Calculate prose density: ratio of flowing prose to lists/bullets\n" +
        "4. Verify word counts by section against minimums\n" +
        "5. Check cold open compliance (Pass 1 only): character, detail, turn statement\n" +
        "6. Verify character thread appearances (Pass 1 only): minimum 4\n" +
        "7. Score overall quality (0-100)\n" +
        "8. Return pass/fail with detailed per-issue feedback",
      qualityCriteria:
        "- Overall score >= 75 for pass\n" +
        "- Zero instances of banned patterns\n" +
        "- Prose density >= 80%\n" +
        "- Word count minimums met for all sections\n" +
        "- Cold open meets framework requirements (Pass 1)",
      errorHandling:
        "- Score below threshold: return detailed revision instructions per issue\n" +
        "- Banned patterns found: list each with location and suggested replacement\n" +
        "- Retry loop: up to 3 quality iterations before human escalation",
      inputSchema:
        "Pass 1: needs_assessment_output (object, required)\n" +
        "Pass 2: grant_package_output (object, required)\n" +
        "pass_number: 1 | 2\n" +
        "scope: 'needs_assessment' | 'full_package'",
    },
  },
  {
    graphId: "compliance_review",
    name: "Compliance Review Agent",
    icon: "\u2705", // check mark
    description: "ACCME standards verification, independence review, and fair balance assessment.",
    category: "qa",
    pipelineOrder: 8,
    upstream: ["prose_quality", "grant_writer"],
    downstream: [],
    inputs: ["grant_package_output", "prose_quality_pass_2", "supporter_company", "accreditation_types"],
    outputs: ["compliance_result"],
    deepDocs: {
      executionFlow:
        "1. Verify prose quality gate has passed (prerequisite)\n" +
        "2. Check ACCME Standard 1: Independence from commercial interest\n" +
        "3. Check ACCME Standard 2: Resolution of conflicts of interest\n" +
        "4. Check ACCME Standard 3: Content validation (fair balance)\n" +
        "5. Check ACCME Standard 4-6: Additional requirements as applicable\n" +
        "6. Verify off-label content has required disclosures\n" +
        "7. Confirm supporter/competitor product balanced coverage\n" +
        "8. Produce compliance assessment with pass/fail and remediation guidance",
      qualityCriteria:
        "- All applicable ACCME standards addressed\n" +
        "- Independence from supporter influence verified\n" +
        "- Fair balance confirmed: competitor products represented\n" +
        "- Off-label disclosures present where required\n" +
        "- Certification readiness determination made",
      errorHandling:
        "- Compliance failure: return specific standard violations with remediation steps\n" +
        "- Missing prose quality pass: block execution, return prerequisite error\n" +
        "- Ambiguous compliance: flag for human review with rationale",
      inputSchema:
        "grant_package_output: object (required) -- Complete grant package\n" +
        "prose_quality_pass_2: object (required) -- Must have passed\n" +
        "supporter_company: string\n" +
        "supporter_products: string[]\n" +
        "competitor_products: string[]\n" +
        "accreditation_types: string[]\n" +
        "off_label_content: boolean",
    },
  },

  // =========================================================================
  // INFRASTRUCTURE AGENTS
  // =========================================================================
  {
    graphId: "citation_checker",
    name: "Citation Checker Agent",
    icon: "\uD83D\uDCCE", // paperclip
    description: "PubMed verification of citations, outputs registry_request for gateway.",
    category: "infra",
    pipelineOrder: 0,
    upstream: [],
    downstream: ["registry"],
    inputs: ["citations_to_verify"],
    outputs: ["verification_results", "registry_request"],
    deepDocs: {
      executionFlow:
        "1. Receive list of citations to verify\n" +
        "2. Query PubMed API for each citation by PMID or title/author\n" +
        "3. Validate: title match, author match, publication date, journal\n" +
        "4. Classify each: verified, not_found, retracted, outdated, landmark\n" +
        "5. Generate registry_request with verification results\n" +
        "6. Output structured verification report",
      qualityCriteria:
        "- Every citation checked against PubMed\n" +
        "- Retracted papers flagged immediately\n" +
        "- Verification status recorded per citation\n" +
        "- Registry request formatted for gateway agent",
      errorHandling:
        "- PubMed API rate limit: implement backoff and retry\n" +
        "- Citation not found: mark as not_found, suggest alternatives\n" +
        "- API timeout: partial results returned with unverified list",
      inputSchema:
        "citations_to_verify: Array<{pmid?: string, title: string, authors?: string, journal?: string}>\n" +
        "project_id: string",
    },
  },
  {
    graphId: "registry",
    name: "Registry Agent",
    icon: "\uD83D\uDDC4\uFE0F", // file cabinet
    description: "Gateway for all agent writes to Registry API with idempotency and dead letter queue.",
    category: "infra",
    pipelineOrder: 0,
    upstream: ["citation_checker"],
    downstream: [],
    inputs: ["registry_request"],
    outputs: ["registry_response"],
    deepDocs: {
      executionFlow:
        "1. Receive registry_request from upstream agent\n" +
        "2. Validate request schema and required fields\n" +
        "3. Check idempotency key to prevent duplicate writes\n" +
        "4. Execute write to Registry API (POST/PATCH)\n" +
        "5. On success: return confirmation with entity ID\n" +
        "6. On failure: route to dead letter queue for manual review",
      qualityCriteria:
        "- All writes are idempotent (safe to retry)\n" +
        "- Failed writes captured in dead letter queue\n" +
        "- Response includes entity ID and status\n" +
        "- Request validation prevents malformed data reaching API",
      errorHandling:
        "- Registry API unavailable: retry 3 times, then dead letter queue\n" +
        "- Validation failure: return error with specific field issues\n" +
        "- Duplicate write detected: return existing entity without re-writing",
      inputSchema:
        "registry_request: {operation: 'create'|'update', entity_type: string, data: object, idempotency_key: string}\n" +
        "project_id: string",
    },
  },

  // =========================================================================
  // RECIPE GRAPHS
  // =========================================================================
  {
    graphId: "needs_package",
    name: "Needs Package",
    icon: "\uD83D\uDCE6", // package
    description: "Research + Clinical parallel, then Gap, LO, Needs, Prose QA Pass 1, Human Review.",
    category: "recipe",
    pipelineOrder: 10,
    upstream: [],
    downstream: ["curriculum_package"],
    inputs: ["intake_form"],
    outputs: ["research_output", "clinical_output", "gap_analysis_output", "learning_objectives_output", "needs_assessment_output", "prose_quality_pass_1"],
    deepDocs: {
      executionFlow:
        "1. Validate intake form completeness\n" +
        "2. Launch Research + Clinical Practice agents in parallel (asyncio.gather)\n" +
        "3. Merge parallel results into shared state\n" +
        "4. Run Gap Analysis (requires both upstream outputs)\n" +
        "5. Run Learning Objectives\n" +
        "6. Run Needs Assessment\n" +
        "7. Run Prose Quality Pass 1\n" +
        "8. If prose fails: retry loop (up to 3x) then human escalation\n" +
        "9. Route to Human Review checkpoint",
      qualityCriteria:
        "- All 6 agent outputs present in final state\n" +
        "- Prose quality Pass 1 has passed\n" +
        "- No error records in state\n" +
        "- Human review checkpoint reached",
      errorHandling:
        "- Parallel agent failure: capture error, continue with available output if possible\n" +
        "- Quality gate failure: retry loop with max 3 iterations\n" +
        "- Unrecoverable error: checkpoint state and escalate to human review",
      inputSchema:
        "intake_form: object (required) -- Full CME intake form (10 sections, 47 fields)\n" +
        "project_id: string\n" +
        "project_name: string",
    },
  },
  {
    graphId: "curriculum_package",
    name: "Curriculum Package",
    icon: "\uD83D\uDCE6", // package
    description: "Needs Package outputs + Curriculum, Protocol, Marketing in parallel, Human Review.",
    category: "recipe",
    pipelineOrder: 11,
    upstream: ["needs_package"],
    downstream: ["grant_package"],
    inputs: ["needs_package_outputs", "intake_form"],
    outputs: ["curriculum_output", "protocol_output", "marketing_output"],
    deepDocs: {
      executionFlow:
        "1. Receive completed needs package state\n" +
        "2. Launch Curriculum Design + Research Protocol + Marketing Plan in parallel\n" +
        "3. Merge parallel results into shared state\n" +
        "4. Validate all three outputs present\n" +
        "5. Route to Human Review checkpoint",
      qualityCriteria:
        "- All 3 parallel agent outputs present\n" +
        "- No conflicts between parallel outputs\n" +
        "- State includes all needs_package outputs plus new outputs",
      errorHandling:
        "- Parallel agent failure: other agents continue, failed agent retried\n" +
        "- All three fail: escalate to human review with partial state\n" +
        "- Timeout: 5 minutes per agent, 10 minutes total for parallel batch",
      inputSchema:
        "needs_package_outputs: object (required) -- All outputs from needs_package\n" +
        "intake_form: object (required)",
    },
  },
  {
    graphId: "grant_package",
    name: "Grant Package",
    icon: "\uD83C\uDFC6", // trophy
    description: "Full 11 agents, Prose QA 2 passes, Compliance gate, Human Review.",
    category: "recipe",
    pipelineOrder: 12,
    upstream: ["curriculum_package"],
    downstream: ["full_pipeline"],
    inputs: ["all_upstream_outputs", "intake_form"],
    outputs: ["grant_package_output", "prose_quality_pass_2", "compliance_result"],
    deepDocs: {
      executionFlow:
        "1. Receive all upstream outputs from needs + curriculum packages\n" +
        "2. Run Grant Writer agent (assembles full package)\n" +
        "3. Run Prose Quality Pass 2 on complete package\n" +
        "4. If prose fails: retry loop (up to 3x)\n" +
        "5. Run Compliance Review\n" +
        "6. If compliance fails: route revision instructions back\n" +
        "7. Route to Human Review checkpoint",
      qualityCriteria:
        "- Grant package assembled from all 9 content agent outputs\n" +
        "- Prose quality Pass 2 passed\n" +
        "- Compliance review passed\n" +
        "- Package ready for pharmaceutical submission",
      errorHandling:
        "- Grant assembly incomplete: return missing section list\n" +
        "- Prose quality failure after 3 retries: escalate with revision notes\n" +
        "- Compliance failure: return specific remediation steps",
      inputSchema:
        "all_upstream_outputs: object (required) -- Combined needs + curriculum package state\n" +
        "intake_form: object (required)",
    },
  },
  {
    graphId: "full_pipeline",
    name: "Full Pipeline",
    icon: "\uD83D\uDE80", // rocket
    description: "Complete end-to-end pipeline with 3-way human review routing (approved/revision/rejected).",
    category: "recipe",
    pipelineOrder: 13,
    upstream: [],
    downstream: [],
    inputs: ["intake_form"],
    outputs: ["grant_package_output", "compliance_result", "human_review_decision"],
    deepDocs: {
      executionFlow:
        "1. Execute needs_package recipe (agents 2-6 + prose QA pass 1)\n" +
        "2. Human Review Gate 1: approve to continue or request revision\n" +
        "3. Execute curriculum_package recipe (agents 7-9 in parallel)\n" +
        "4. Human Review Gate 2: approve to continue or request revision\n" +
        "5. Execute grant_package recipe (agent 10 + prose QA pass 2 + compliance)\n" +
        "6. Human Review Gate 3: 3-way routing\n" +
        "   - Approved: mark complete, store final outputs\n" +
        "   - Revision: route back to specified agent with notes\n" +
        "   - Rejected: mark cancelled with reason",
      qualityCriteria:
        "- All 11 content agents executed successfully\n" +
        "- Both prose quality passes passed\n" +
        "- Compliance review passed\n" +
        "- All human review gates cleared\n" +
        "- Final package submission-ready",
      errorHandling:
        "- Human review timeout: escalate via notification\n" +
        "- Revision requested: re-run from specified agent forward\n" +
        "- Rejected: archive state with reason, no further processing",
      inputSchema:
        "intake_form: object (required) -- Full CME intake form\n" +
        "project_id: string\n" +
        "project_name: string",
    },
  },
];

/** Lookup a single catalog entry by graphId. */
export function getCatalogEntry(graphId: string): AgentCatalogEntry | undefined {
  return AGENT_CATALOG.find((a) => a.graphId === graphId);
}

/** Category display metadata. */
export const CATEGORY_META: Record<AgentCategory, { label: string; order: number }> = {
  content: { label: "Content Agents", order: 1 },
  recipe: { label: "Recipe Graphs", order: 2 },
  qa: { label: "QA Gates", order: 3 },
  infra: { label: "Infrastructure", order: 4 },
};
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit src/lib/agent-catalog.ts
# Expected: no errors
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/agent-catalog.ts
git commit -m "feat(frontend): add static agent catalog with 17 graphs and deep docs"
```

---

### Task 6: Graph Stats API

**Files:**
- Modify: `frontend/src/lib/agentsApi.ts`

- [ ] **Step 1: Add `GraphStats` interface and `getGraphStats()` function**

Add the following after the existing `AgentStats` interface (around line 53):

```typescript
export interface GraphStats {
  graphId: string;
  totalRuns: number;
  succeeded: number;
  failed: number;
  running: number;
  successRate: number;
  lastRunAt: string | null;
}
```

Add the following function after the existing `getAgentStats()` function (around line 300):

```typescript
export async function getGraphStats(): Promise<GraphStats[]> {
  const client = createClient();
  const threads = await client.threads.search({ limit: 100 });

  const statsMap: Record<string, {
    totalRuns: number;
    succeeded: number;
    failed: number;
    running: number;
    lastRunAt: string | null;
  }> = {};

  for (const thread of threads) {
    const graphId = (thread.metadata?.graph_id as string) ?? "unknown";
    if (!statsMap[graphId]) {
      statsMap[graphId] = { totalRuns: 0, succeeded: 0, failed: 0, running: 0, lastRunAt: null };
    }
    const entry = statsMap[graphId];
    entry.totalRuns++;

    const s = thread.status;
    if (s === "busy") entry.running++;
    else if (s === "error") entry.failed++;
    else if (s === "idle" || s === "interrupted") entry.succeeded++;

    const updatedAt = thread.updated_at;
    if (updatedAt && (!entry.lastRunAt || updatedAt > entry.lastRunAt)) {
      entry.lastRunAt = updatedAt;
    }
  }

  return Object.entries(statsMap).map(([graphId, s]) => ({
    graphId,
    totalRuns: s.totalRuns,
    succeeded: s.succeeded,
    failed: s.failed,
    running: s.running,
    successRate: s.totalRuns > 0 ? Math.round((s.succeeded / s.totalRuns) * 100) : 0,
    lastRunAt: s.lastRunAt,
  }));
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit src/lib/agentsApi.ts
# Expected: no errors
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/agentsApi.ts
git commit -m "feat(frontend): add getGraphStats() for per-graph run statistics"
```

---

### Task 7: Agents Library Toolbar

**Files:**
- Create: `frontend/src/components/agents/agents-library-toolbar.tsx`

- [ ] **Step 1: Create the toolbar component**

```tsx
"use client";

import { LayoutGrid, List, Table2, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AgentCategory } from "@/lib/agent-catalog";

export type ViewMode = "grid" | "list" | "table";
export type SortField = "name" | "category" | "pipelineOrder" | "successRate" | "totalRuns";

const CATEGORIES: { value: AgentCategory | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "content", label: "Content" },
  { value: "recipe", label: "Recipes" },
  { value: "qa", label: "QA" },
  { value: "infra", label: "Infra" },
];

const CATEGORY_STYLES: Record<string, string> = {
  all: "border-zinc-300 dark:border-zinc-600",
  content: "border-[#663399] bg-[#663399]/10 text-[#663399] dark:text-[#a78bfa]",
  recipe: "border-[#F77E2D] bg-[#F77E2D]/10 text-[#F77E2D] dark:text-[#fb923c]",
  qa: "border-[#22c55e] bg-[#22c55e]/10 text-[#16a34a] dark:text-[#4ade80]",
  infra: "border-zinc-500 bg-zinc-500/10 text-zinc-500 dark:text-zinc-400",
};

interface ToolbarProps {
  view: ViewMode;
  onViewChange: (v: ViewMode) => void;
  category: AgentCategory | "all";
  onCategoryChange: (c: AgentCategory | "all") => void;
  search: string;
  onSearchChange: (s: string) => void;
  sort: SortField;
  onSortChange: (s: SortField) => void;
  categoryCounts: Record<AgentCategory | "all", number>;
}

export function AgentsLibraryToolbar({
  view,
  onViewChange,
  category,
  onCategoryChange,
  search,
  onSearchChange,
  sort,
  onSortChange,
  categoryCounts,
}: ToolbarProps) {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* Category filter pills */}
      <div className="flex items-center gap-1.5">
        {CATEGORIES.map((cat) => (
          <Badge
            key={cat.value}
            variant="outline"
            className={`cursor-pointer text-[11px] px-2.5 py-0.5 transition-colors ${
              category === cat.value
                ? CATEGORY_STYLES[cat.value]
                : "border-border text-muted-foreground hover:border-foreground/30"
            }`}
            onClick={() => onCategoryChange(cat.value)}
          >
            {cat.label} ({categoryCounts[cat.value]})
          </Badge>
        ))}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Search */}
      <div className="relative w-52">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <Input
          placeholder="Search agents..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-8 h-8 text-xs"
        />
      </div>

      {/* Sort */}
      <Select value={sort} onValueChange={(v) => onSortChange(v as SortField)}>
        <SelectTrigger className="w-36 h-8 text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="pipelineOrder">Pipeline Order</SelectItem>
          <SelectItem value="name">Name</SelectItem>
          <SelectItem value="category">Category</SelectItem>
          <SelectItem value="successRate">Success Rate</SelectItem>
          <SelectItem value="totalRuns">Total Runs</SelectItem>
        </SelectContent>
      </Select>

      {/* View toggle */}
      <div className="flex items-center border border-border rounded-md">
        <Button
          variant={view === "grid" ? "secondary" : "ghost"}
          size="sm"
          className="h-8 w-8 p-0 rounded-r-none"
          onClick={() => onViewChange("grid")}
        >
          <LayoutGrid className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant={view === "list" ? "secondary" : "ghost"}
          size="sm"
          className="h-8 w-8 p-0 rounded-none border-x border-border"
          onClick={() => onViewChange("list")}
        >
          <List className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant={view === "table" ? "secondary" : "ghost"}
          size="sm"
          className="h-8 w-8 p-0 rounded-l-none"
          onClick={() => onViewChange("table")}
        >
          <Table2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit src/components/agents/agents-library-toolbar.tsx
# Expected: no errors
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/agents/agents-library-toolbar.tsx
git commit -m "feat(frontend): add AgentsLibraryToolbar component"
```

---

### Task 8: Grid View

**Files:**
- Create: `frontend/src/components/agents/agents-library-grid.tsx`

- [ ] **Step 1: Create the grid view component**

```tsx
"use client";

import { Badge } from "@/components/ui/badge";
import type { AgentCategory } from "@/lib/agent-catalog";
import { CATEGORY_META } from "@/lib/agent-catalog";
import type { AgentLibraryItem } from "./agents-library";

const CATEGORY_BORDER: Record<AgentCategory, string> = {
  content: "border-t-[#663399]",
  recipe: "border-t-[#F77E2D]",
  qa: "border-t-[#22c55e]",
  infra: "border-t-zinc-500",
};

const CATEGORY_SHADOW: Record<AgentCategory, string> = {
  content: "hover:shadow-[0_4px_12px_rgba(102,51,153,0.15)] dark:hover:shadow-[0_4px_12px_rgba(167,139,250,0.15)]",
  recipe: "hover:shadow-[0_4px_12px_rgba(247,126,45,0.15)] dark:hover:shadow-[0_4px_12px_rgba(251,146,60,0.15)]",
  qa: "hover:shadow-[0_4px_12px_rgba(34,197,94,0.15)] dark:hover:shadow-[0_4px_12px_rgba(74,222,128,0.15)]",
  infra: "hover:shadow-[0_4px_12px_rgba(113,113,122,0.15)] dark:hover:shadow-[0_4px_12px_rgba(161,161,170,0.15)]",
};

function healthBorder(lastRunAt: string | null): string {
  if (!lastRunAt) return "border-l-transparent";
  const hoursSince = (Date.now() - new Date(lastRunAt).getTime()) / (1000 * 60 * 60);
  if (hoursSince <= 24) return "border-l-green-500";
  return "border-l-amber-500";
}

interface GridViewProps {
  items: AgentLibraryItem[];
  onSelect: (item: AgentLibraryItem) => void;
}

export function AgentsLibraryGrid({ items, onSelect }: GridViewProps) {
  // Group by category, sorted by CATEGORY_META order
  const groups = new Map<AgentCategory, AgentLibraryItem[]>();
  for (const item of items) {
    const list = groups.get(item.category) ?? [];
    list.push(item);
    groups.set(item.category, list);
  }
  const sortedGroups = [...groups.entries()].sort(
    (a, b) => CATEGORY_META[a[0]].order - CATEGORY_META[b[0]].order
  );

  let globalIndex = 0;

  return (
    <div className="space-y-6">
      {sortedGroups.map(([cat, catItems]) => (
        <div key={cat}>
          <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            {CATEGORY_META[cat].label} ({catItems.length})
          </h4>
          <div className="grid grid-cols-3 gap-3">
            {catItems.map((item) => {
              const idx = globalIndex++;
              return (
                <button
                  key={item.graphId}
                  onClick={() => onSelect(item)}
                  className={`
                    text-left rounded-lg border border-border border-t-2 border-l-2
                    ${CATEGORY_BORDER[item.category]}
                    ${healthBorder(item.lastRunAt)}
                    ${CATEGORY_SHADOW[item.category]}
                    bg-card p-3 transition-all duration-200
                    hover:translate-y-[-1px]
                    agents-library-card-enter
                  `}
                  style={{ animationDelay: `${idx * 40}ms` }}
                >
                  <div className="flex items-start gap-2">
                    <span className="text-lg leading-none mt-0.5">{item.icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-medium truncate">{item.name}</span>
                      </div>
                      <p className="text-[10px] text-muted-foreground mt-0.5 leading-snug line-clamp-2">
                        {item.description}
                      </p>
                    </div>
                  </div>

                  {/* Stats row */}
                  <div className="flex items-center gap-2 mt-2.5 pt-2 border-t border-border/50">
                    <span className="text-[10px] text-muted-foreground">
                      {item.totalRuns} runs
                    </span>
                    {item.totalRuns > 0 && (
                      <>
                        <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-green-500 transition-all duration-500"
                            style={{ width: `${item.successRate}%` }}
                          />
                        </div>
                        <span className="text-[10px] font-medium tabular-nums">
                          {item.successRate}%
                        </span>
                      </>
                    )}
                    {item.totalRuns === 0 && (
                      <span className="text-[10px] text-muted-foreground italic">no data</span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit src/components/agents/agents-library-grid.tsx
# Expected: no errors (may require agents-library.tsx to exist for the type import — see Task 12)
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/agents/agents-library-grid.tsx
git commit -m "feat(frontend): add AgentsLibraryGrid view component"
```

---

### Task 9: List View

**Files:**
- Create: `frontend/src/components/agents/agents-library-list.tsx`

- [ ] **Step 1: Create the list view component**

```tsx
"use client";

import { ChevronRight } from "lucide-react";
import type { AgentCategory } from "@/lib/agent-catalog";
import { CATEGORY_META } from "@/lib/agent-catalog";
import type { AgentLibraryItem } from "./agents-library";

const CATEGORY_DOT: Record<AgentCategory, string> = {
  content: "bg-[#663399]",
  recipe: "bg-[#F77E2D]",
  qa: "bg-[#22c55e]",
  infra: "bg-zinc-500",
};

interface ListViewProps {
  items: AgentLibraryItem[];
  onSelect: (item: AgentLibraryItem) => void;
}

export function AgentsLibraryList({ items, onSelect }: ListViewProps) {
  const groups = new Map<AgentCategory, AgentLibraryItem[]>();
  for (const item of items) {
    const list = groups.get(item.category) ?? [];
    list.push(item);
    groups.set(item.category, list);
  }
  const sortedGroups = [...groups.entries()].sort(
    (a, b) => CATEGORY_META[a[0]].order - CATEGORY_META[b[0]].order
  );

  return (
    <div className="space-y-4">
      {sortedGroups.map(([cat, catItems]) => (
        <div key={cat}>
          <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            {CATEGORY_META[cat].label}
          </h4>
          <div className="space-y-0.5">
            {catItems.map((item) => (
              <button
                key={item.graphId}
                onClick={() => onSelect(item)}
                className="w-full text-left grid grid-cols-[24px_1fr_80px_60px_60px_20px] items-center gap-2 px-3 py-2 rounded-md hover:bg-muted/50 transition-colors group"
              >
                {/* Icon */}
                <span className="text-sm">{item.icon}</span>

                {/* Name + description */}
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium truncate">{item.name}</span>
                    <span className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${CATEGORY_DOT[item.category]}`} />
                  </div>
                  <p className="text-[10px] text-muted-foreground truncate">{item.description}</p>
                </div>

                {/* Success bar */}
                <div className="flex items-center gap-1.5">
                  <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-green-500"
                      style={{ width: `${item.successRate}%` }}
                    />
                  </div>
                  <span className="text-[10px] tabular-nums w-7 text-right">{item.successRate}%</span>
                </div>

                {/* Total runs */}
                <span className="text-[10px] text-muted-foreground text-right tabular-nums">
                  {item.totalRuns} runs
                </span>

                {/* Running */}
                <span className="text-[10px] text-muted-foreground text-right tabular-nums">
                  {item.running > 0 ? `${item.running} active` : ""}
                </span>

                {/* Chevron */}
                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit src/components/agents/agents-library-list.tsx
# Expected: no errors
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/agents/agents-library-list.tsx
git commit -m "feat(frontend): add AgentsLibraryList view component"
```

---

### Task 10: Table View

**Files:**
- Create: `frontend/src/components/agents/agents-library-table.tsx`

- [ ] **Step 1: Create the table view component**

```tsx
"use client";

import { ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { AgentCategory } from "@/lib/agent-catalog";
import type { AgentLibraryItem } from "./agents-library";
import type { SortField } from "./agents-library-toolbar";

const CATEGORY_BADGE: Record<AgentCategory, string> = {
  content: "bg-[#663399]/10 text-[#663399] dark:text-[#a78bfa]",
  recipe: "bg-[#F77E2D]/10 text-[#F77E2D] dark:text-[#fb923c]",
  qa: "bg-[#22c55e]/10 text-[#16a34a] dark:text-[#4ade80]",
  infra: "bg-zinc-500/10 text-zinc-500 dark:text-zinc-400",
};

interface TableViewProps {
  items: AgentLibraryItem[];
  onSelect: (item: AgentLibraryItem) => void;
  sort: SortField;
  onSortChange: (s: SortField) => void;
}

function SortHeader({
  label,
  field,
  currentSort,
  onSort,
  align,
}: {
  label: string;
  field: SortField;
  currentSort: SortField;
  onSort: (s: SortField) => void;
  align?: "left" | "right";
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      className={`h-7 text-[10px] font-semibold uppercase tracking-wider px-1 ${
        align === "right" ? "justify-end" : ""
      } ${currentSort === field ? "text-foreground" : "text-muted-foreground"}`}
      onClick={() => onSort(field)}
    >
      {label}
      <ArrowUpDown className="ml-1 h-3 w-3" />
    </Button>
  );
}

export function AgentsLibraryTable({ items, onSelect, sort, onSortChange }: TableViewProps) {
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div className="overflow-auto max-h-[calc(100vh-220px)]">
        <table className="w-full text-xs">
          <thead className="sticky top-0 z-10 bg-muted/80 backdrop-blur-sm border-b border-border">
            <tr>
              <th className="text-left px-3 py-2 w-8" />
              <th className="text-left px-1 py-2">
                <SortHeader label="Agent" field="name" currentSort={sort} onSort={onSortChange} />
              </th>
              <th className="text-left px-1 py-2 w-24">
                <SortHeader label="Category" field="category" currentSort={sort} onSort={onSortChange} />
              </th>
              <th className="text-right px-1 py-2 w-16">
                <SortHeader label="Order" field="pipelineOrder" currentSort={sort} onSort={onSortChange} align="right" />
              </th>
              <th className="text-right px-1 py-2 w-20">
                <SortHeader label="Runs" field="totalRuns" currentSort={sort} onSort={onSortChange} align="right" />
              </th>
              <th className="text-right px-1 py-2 w-28">
                <SortHeader label="Success" field="successRate" currentSort={sort} onSort={onSortChange} align="right" />
              </th>
              <th className="text-right px-3 py-2 w-20">
                <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Active</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => (
              <tr
                key={item.graphId}
                onClick={() => onSelect(item)}
                className={`cursor-pointer border-b border-border/50 transition-colors hover:bg-muted/40 ${
                  idx % 2 === 1 ? "bg-muted/20" : ""
                }`}
              >
                <td className="px-3 py-2 text-center">
                  <span className="text-sm">{item.icon}</span>
                </td>
                <td className="px-1 py-2">
                  <div>
                    <span className="font-medium">{item.name}</span>
                    <p className="text-[10px] text-muted-foreground truncate max-w-xs">{item.description}</p>
                  </div>
                </td>
                <td className="px-1 py-2">
                  <span className={`inline-block text-[10px] px-2 py-0.5 rounded-full ${CATEGORY_BADGE[item.category]}`}>
                    {item.category}
                  </span>
                </td>
                <td className="px-1 py-2 text-right tabular-nums text-muted-foreground">
                  {item.pipelineOrder > 0 ? item.pipelineOrder : "\u2014"}
                </td>
                <td className="px-1 py-2 text-right tabular-nums">
                  {item.totalRuns}
                </td>
                <td className="px-1 py-2">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-green-500 transition-all duration-500"
                        style={{ width: `${item.successRate}%` }}
                      />
                    </div>
                    <span className="tabular-nums w-8 text-right">{item.successRate}%</span>
                  </div>
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {item.running > 0 && (
                    <span className="inline-flex items-center gap-1 text-green-600 dark:text-green-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                      {item.running}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit src/components/agents/agents-library-table.tsx
# Expected: no errors
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/agents/agents-library-table.tsx
git commit -m "feat(frontend): add AgentsLibraryTable view component"
```

---

### Task 11: Agent Slide-Over

**Files:**
- Create: `frontend/src/components/agents/agent-slide-over.tsx`

- [ ] **Step 1: Create the slide-over component**

```tsx
"use client";

import { ChevronDown, Play, ArrowLeft, ArrowRight } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { AgentCategory } from "@/lib/agent-catalog";
import { getCatalogEntry } from "@/lib/agent-catalog";
import type { AgentLibraryItem } from "./agents-library";

const CATEGORY_BADGE: Record<AgentCategory, string> = {
  content: "bg-[#663399]/10 text-[#663399] dark:text-[#a78bfa] border-[#663399]/30",
  recipe: "bg-[#F77E2D]/10 text-[#F77E2D] dark:text-[#fb923c] border-[#F77E2D]/30",
  qa: "bg-[#22c55e]/10 text-[#16a34a] dark:text-[#4ade80] border-[#22c55e]/30",
  infra: "bg-zinc-500/10 text-zinc-500 dark:text-zinc-400 border-zinc-500/30",
};

interface SlideOverProps {
  agent: AgentLibraryItem | null;
  onClose: () => void;
  onNavigate: (graphId: string) => void;
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3">
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</p>
      <p className="text-lg font-semibold tabular-nums mt-0.5">{value}</p>
      {sub && <p className="text-[10px] text-muted-foreground">{sub}</p>}
    </div>
  );
}

function DeepDocSection({ title, content }: { title: string; content: string }) {
  return (
    <Collapsible>
      <CollapsibleTrigger className="flex items-center justify-between w-full py-2 px-1 text-xs font-medium hover:text-foreground text-muted-foreground transition-colors group">
        {title}
        <ChevronDown className="h-3.5 w-3.5 transition-transform group-data-[state=open]:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="px-1 pb-3">
          <pre className="text-[11px] text-muted-foreground whitespace-pre-wrap font-[Inter] leading-relaxed">
            {content}
          </pre>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

export function AgentSlideOver({ agent, onClose, onNavigate }: SlideOverProps) {
  if (!agent) return null;

  const catalogEntry = getCatalogEntry(agent.graphId);
  const deepDocs = catalogEntry?.deepDocs;

  const lastRunLabel = agent.lastRunAt
    ? new Date(agent.lastRunAt).toLocaleString()
    : "Never";

  return (
    <Sheet open={!!agent} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-[480px] sm:max-w-none overflow-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-3">
            <span className="text-2xl">{agent.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate">{agent.name}</span>
                <Badge variant="outline" className={`text-[10px] ${CATEGORY_BADGE[agent.category]}`}>
                  {agent.category}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground font-normal mt-0.5">{agent.description}</p>
            </div>
          </SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-6 px-6 pb-8">
          {/* 2x2 Stats Grid */}
          <div className="grid grid-cols-2 gap-3">
            <StatCard label="Total Runs" value={agent.totalRuns} />
            <StatCard label="Success Rate" value={`${agent.successRate}%`} />
            <StatCard label="Active" value={agent.running} />
            <StatCard label="Last Run" value={lastRunLabel} />
          </div>

          {/* Dependencies */}
          {(agent.upstream.length > 0 || agent.downstream.length > 0) && (
            <div className="space-y-2">
              <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Dependencies</h4>
              {agent.upstream.length > 0 && (
                <div className="flex items-center gap-2 flex-wrap">
                  <ArrowLeft className="h-3 w-3 text-muted-foreground shrink-0" />
                  <span className="text-[10px] text-muted-foreground w-14">Upstream:</span>
                  {agent.upstream.map((id) => (
                    <Badge
                      key={id}
                      variant="outline"
                      className="text-[10px] cursor-pointer hover:bg-muted transition-colors"
                      onClick={() => onNavigate(id)}
                    >
                      {id.replace(/_/g, " ")}
                    </Badge>
                  ))}
                </div>
              )}
              {agent.downstream.length > 0 && (
                <div className="flex items-center gap-2 flex-wrap">
                  <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
                  <span className="text-[10px] text-muted-foreground w-14">Down:</span>
                  {agent.downstream.map((id) => (
                    <Badge
                      key={id}
                      variant="outline"
                      className="text-[10px] cursor-pointer hover:bg-muted transition-colors"
                      onClick={() => onNavigate(id)}
                    >
                      {id.replace(/_/g, " ")}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Inputs / Outputs tags */}
          <div className="space-y-2">
            <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Inputs</h4>
            <div className="flex flex-wrap gap-1">
              {agent.inputs.map((inp) => (
                <Badge key={inp} variant="secondary" className="text-[10px]">
                  {inp}
                </Badge>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Outputs</h4>
            <div className="flex flex-wrap gap-1">
              {agent.outputs.map((out) => (
                <Badge key={out} variant="secondary" className="text-[10px]">
                  {out}
                </Badge>
              ))}
            </div>
          </div>

          {/* Deep Docs */}
          {deepDocs && (
            <div className="space-y-1 border-t border-border pt-4">
              <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Documentation</h4>
              <DeepDocSection title="Execution Flow" content={deepDocs.executionFlow} />
              <DeepDocSection title="Quality Criteria" content={deepDocs.qualityCriteria} />
              <DeepDocSection title="Error Handling" content={deepDocs.errorHandling} />
              <DeepDocSection title="Input Schema" content={deepDocs.inputSchema} />
            </div>
          )}

          {/* Run Agent button (disabled) */}
          <div className="pt-4 border-t border-border">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button disabled className="w-full" variant="outline">
                    <Play className="h-4 w-4 mr-2" />
                    Run Agent
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  Agent execution is available through the pipeline recipes
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit src/components/agents/agent-slide-over.tsx
# Expected: no errors
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/agents/agent-slide-over.tsx
git commit -m "feat(frontend): add AgentSlideOver detail panel component"
```

---

### Task 12: Main Agents Library Container + CSS Animations

**Files:**
- Create: `frontend/src/components/agents/agents-library.tsx`

- [ ] **Step 1: Create the main container component**

```tsx
"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { AGENT_CATALOG, getCatalogEntry } from "@/lib/agent-catalog";
import type { AgentCategory, AgentCatalogEntry } from "@/lib/agent-catalog";
import { getGraphStats } from "@/lib/agentsApi";
import type { GraphStats } from "@/lib/agentsApi";
import { AgentsLibraryToolbar } from "./agents-library-toolbar";
import type { ViewMode, SortField } from "./agents-library-toolbar";
import { AgentsLibraryGrid } from "./agents-library-grid";
import { AgentsLibraryList } from "./agents-library-list";
import { AgentsLibraryTable } from "./agents-library-table";
import { AgentSlideOver } from "./agent-slide-over";

/** Merged catalog entry + live stats — the display type for all views. */
export interface AgentLibraryItem extends AgentCatalogEntry {
  totalRuns: number;
  succeeded: number;
  failed: number;
  running: number;
  successRate: number;
  lastRunAt: string | null;
}

function mergeStats(catalog: AgentCatalogEntry[], stats: GraphStats[]): AgentLibraryItem[] {
  const statsMap = new Map(stats.map((s) => [s.graphId, s]));
  return catalog.map((entry) => {
    const s = statsMap.get(entry.graphId);
    return {
      ...entry,
      totalRuns: s?.totalRuns ?? 0,
      succeeded: s?.succeeded ?? 0,
      failed: s?.failed ?? 0,
      running: s?.running ?? 0,
      successRate: s?.successRate ?? 0,
      lastRunAt: s?.lastRunAt ?? null,
    };
  });
}

function sortItems(items: AgentLibraryItem[], field: SortField): AgentLibraryItem[] {
  const sorted = [...items];
  sorted.sort((a, b) => {
    switch (field) {
      case "name":
        return a.name.localeCompare(b.name);
      case "category":
        return a.category.localeCompare(b.category) || a.pipelineOrder - b.pipelineOrder;
      case "pipelineOrder":
        return a.pipelineOrder - b.pipelineOrder;
      case "successRate":
        return b.successRate - a.successRate;
      case "totalRuns":
        return b.totalRuns - a.totalRuns;
      default:
        return 0;
    }
  });
  return sorted;
}

export function AgentsLibrary() {
  const [view, setView] = useState<ViewMode>("grid");
  const [category, setCategory] = useState<AgentCategory | "all">("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortField>("pipelineOrder");
  const [selectedAgent, setSelectedAgent] = useState<AgentLibraryItem | null>(null);
  const [graphStats, setGraphStats] = useState<GraphStats[]>([]);

  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);

  const fetchStats = useCallback(async () => {
    try {
      const stats = await getGraphStats();
      setGraphStats(stats);
    } catch (e) {
      console.error("Failed to fetch graph stats:", e);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    intervalRef.current = setInterval(fetchStats, 30_000);
    return () => clearInterval(intervalRef.current);
  }, [fetchStats]);

  // Merge catalog with stats
  const allItems = useMemo(() => mergeStats(AGENT_CATALOG, graphStats), [graphStats]);

  // Filter
  const filtered = useMemo(() => {
    let result = allItems;
    if (category !== "all") {
      result = result.filter((item) => item.category === category);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (item) =>
          item.name.toLowerCase().includes(q) ||
          item.description.toLowerCase().includes(q) ||
          item.graphId.toLowerCase().includes(q)
      );
    }
    return result;
  }, [allItems, category, search]);

  // Sort
  const sorted = useMemo(() => sortItems(filtered, sort), [filtered, sort]);

  // Category counts (from allItems, not filtered)
  const categoryCounts = useMemo(() => {
    const counts: Record<AgentCategory | "all", number> = {
      all: allItems.length,
      content: 0,
      recipe: 0,
      qa: 0,
      infra: 0,
    };
    for (const item of allItems) {
      counts[item.category]++;
    }
    return counts;
  }, [allItems]);

  const handleNavigate = useCallback(
    (graphId: string) => {
      const item = allItems.find((i) => i.graphId === graphId);
      if (item) setSelectedAgent(item);
    },
    [allItems]
  );

  return (
    <>
      {/* CSS keyframes injected via style tag */}
      <style>{`
        @keyframes agents-card-enter {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .agents-library-card-enter {
          animation: agents-card-enter 350ms ease-out both;
        }
      `}</style>

      <div
        className="p-4 space-y-4 overflow-auto h-full"
        style={{
          background: "radial-gradient(ellipse at top, var(--dhg-surface, hsl(var(--card))) 0%, transparent 70%)",
        }}
      >
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-sm font-semibold">Agents Library ({allItems.length})</h3>
        </div>

        <AgentsLibraryToolbar
          view={view}
          onViewChange={setView}
          category={category}
          onCategoryChange={setCategory}
          search={search}
          onSearchChange={setSearch}
          sort={sort}
          onSortChange={setSort}
          categoryCounts={categoryCounts}
        />

        {sorted.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
            No agents match your filters.
          </div>
        ) : view === "grid" ? (
          <AgentsLibraryGrid items={sorted} onSelect={setSelectedAgent} />
        ) : view === "list" ? (
          <AgentsLibraryList items={sorted} onSelect={setSelectedAgent} />
        ) : (
          <AgentsLibraryTable items={sorted} onSelect={setSelectedAgent} sort={sort} onSortChange={setSort} />
        )}
      </div>

      <AgentSlideOver
        agent={selectedAgent}
        onClose={() => setSelectedAgent(null)}
        onNavigate={handleNavigate}
      />
    </>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit src/components/agents/agents-library.tsx
# Expected: no errors
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/agents/agents-library.tsx
git commit -m "feat(frontend): add AgentsLibrary main container with stats polling and CSS animations"
```

---

### Task 13: Page Integration

**Files:**
- Modify: `frontend/src/app/agents/page.tsx`

- [ ] **Step 1: Replace `AssistantsRegistry` with `AgentsLibrary` in the agents page**

Replace the entire file content with:

```tsx
"use client";

import { useEffect, useRef } from "react";
import { AgentTree } from "@/components/agents/agent-tree";
import { AgentTabs } from "@/components/agents/agent-tabs";
import { StatsBar } from "@/components/agents/stats-bar";
import { AgentsLibrary } from "@/components/agents/agents-library";
import { useAgentsStore } from "@/stores/agents-store";

export default function AgentsPage() {
  const {
    selectedAgent,
    selectedState,
    stats,
    filter,
    fetchRunning,
    fetchAll,
    fetchStats,
    fetchThreadState,
  } = useAgentsStore();
  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    const fetch = filter === "all" ? fetchAll : fetchRunning;
    fetch();
    fetchStats();
    intervalRef.current = setInterval(() => {
      fetch();
      fetchStats();
    }, 5000);
    return () => clearInterval(intervalRef.current);
  }, [filter, fetchRunning, fetchAll, fetchStats]);

  useEffect(() => {
    if (!selectedAgent) return;
    fetchThreadState(selectedAgent.threadId);
    const id = setInterval(() => fetchThreadState(selectedAgent.threadId), 5000);
    return () => clearInterval(id);
  }, [selectedAgent, fetchThreadState]);

  const showLibrary = !selectedAgent;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <StatsBar stats={stats} />
      <div className="flex flex-1 overflow-hidden">
        <AgentTree />
        <div className="flex-1 overflow-hidden">
          {showLibrary ? (
            <AgentsLibrary />
          ) : (
            <AgentTabs agent={selectedAgent} state={selectedState} />
          )}
        </div>
      </div>
    </div>
  );
}
```

Key changes from the original:
- Replaced `import { AssistantsRegistry }` with `import { AgentsLibrary }`
- Removed `assistants` and `fetchAssistants` from the destructured store (no longer needed for the default view)
- Removed the `useEffect` that called `fetchAssistants()` on mount
- Changed `showRegistry` variable to `showLibrary`
- Replaced `<AssistantsRegistry assistants={assistants} />` with `<AgentsLibrary />`

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit src/app/agents/page.tsx
# Expected: no errors
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/agents/page.tsx
git commit -m "feat(frontend): swap AssistantsRegistry for AgentsLibrary on agents page"
```

---

### Task 14: Build Verification

**Files:** None (verification only)

- [ ] **Step 1: Run the frontend build**

```bash
cd frontend && npm run build
# Expected: Compiled successfully
# Watch for any TypeScript errors or import resolution failures
```

- [ ] **Step 2: Verify the registry API is healthy and new endpoint responds**

```bash
curl -s http://localhost:8011/healthz
# Expected: OK

curl -s http://localhost:8011/api/v1/frontend-specs | python3 -m json.tool | head -5
# Expected: JSON array with the agents-library spec
```

- [ ] **Step 3: Start the frontend dev server and visually verify**

```bash
cd frontend && npm run dev
# Open http://localhost:3000/agents in browser
# Verify:
#   1. Grid view loads with 17 agents grouped by category
#   2. Category pills show correct counts (9 content, 4 recipe, 2 QA, 2 infra)
#   3. Switching to list and table views works
#   4. Search filters agents by name/description
#   5. Clicking a card opens the slide-over with stats, deps, docs
#   6. Deep docs sections expand via Collapsible
#   7. Dependency badges in slide-over navigate to that agent
#   8. Card entry animation plays on initial load (staggered fade-in)
#   9. Run Agent button is disabled with tooltip
```

- [ ] **Step 4: Final commit with all remaining changes**

```bash
git add -A
git status
# Verify no secrets or .env files are staged
git commit -m "feat(agents): complete Agents Library with grid/list/table views, slide-over, and live stats"
```
