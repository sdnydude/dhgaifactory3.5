"""Add dev_changelog table

Revision ID: 007
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dev_changelog",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("epic", sa.String(500), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, comment="feature|infra|fix|refactor|docs|debt"),
        sa.Column("detected_status", sa.String(50), nullable=False, comment="agent-owned: shipped|in_progress|backlog|abandoned"),
        sa.Column("declared_status", sa.String(50), nullable=True, comment="human override; display uses COALESCE(declared, detected)"),
        sa.Column("window_start", sa.Date, nullable=False),
        sa.Column("window_end", sa.Date, nullable=True),
        sa.Column("commit_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("commits", JSONB, nullable=False, server_default="[]", comment="agent-owned: [{sha, date, subject, author}]"),
        sa.Column("sessions", JSONB, nullable=False, server_default="[]", comment="agent-owned: [{session_id, chunk_idx, note}]"),
        sa.Column("key_insight", sa.Text, nullable=True, comment="human-owned: narrative/context"),
        sa.Column("notes", sa.Text, nullable=True, comment="human-owned: freeform"),
        sa.Column("priority", sa.Integer, nullable=True, comment="human-owned"),
        sa.Column("locked", sa.Boolean, nullable=False, server_default=sa.text("false"), comment="if true, agent skips this row entirely"),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual", comment="manual|agent|mixed"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_agent_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_human_edit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_dev_changelog_detected_status", "dev_changelog", ["detected_status"])
    op.create_index("ix_dev_changelog_declared_status", "dev_changelog", ["declared_status"])
    op.create_index("ix_dev_changelog_category", "dev_changelog", ["category"])
    op.create_index("ix_dev_changelog_window_start", "dev_changelog", ["window_start"])

    op.get_bind().exec_driver_sql("""
INSERT INTO dev_changelog (slug, epic, category, detected_status, window_start, window_end, commit_count, commits, sessions, key_insight, notes, source) VALUES

('vs-engine-wave-1',
 'Verbalized Sampling Engine + Wave 1 integration',
 'feature', 'shipped', '2026-03-13', '2026-03-15', 25,
 '[{"sha":"845b4e6","date":"2026-03-14","subject":"feat(vs-engine): add spread and selection_delta Prometheus metrics"},{"sha":"e302b58","date":"2026-03-14","subject":"feat(agents): integrate VS into needs assessment agent (5 nodes)"},{"sha":"0b0cab3","date":"2026-03-14","subject":"feat(agents): integrate VS into research, clinical practice, learning objectives, curriculum design"},{"sha":"87a2590","date":"2026-03-14","subject":"feat(agents): integrate VS into research protocol, marketing plan, grant writer"},{"sha":"dafb8a6","date":"2026-03-14","subject":"refactor(agents): migrate gap_analysis_agent from vs_distribution to vs_distributions dict"},{"sha":"476f8cd","date":"2026-03-14","subject":"feat(orchestrator): collect VS distributions from all 9 agents"},{"sha":"15d5f87","date":"2026-03-14","subject":"feat(observability): add VS engine Grafana dashboard"},{"sha":"85bf0f7","date":"2026-03-14","subject":"feat(frontend): integrate VS alternatives into inbox review panel"}]'::jsonb,
 '[]'::jsonb,
 'Core divergent-convergent mechanism for all 9 content agents. spread + selection_delta Prometheus metrics, orchestrator aggregation, frontend panel in inbox.',
 NULL, 'manual'),

('monitoring-dashboard-phase3',
 'Monitoring Dashboard (Phase 3, PR #11)',
 'feature', 'shipped', '2026-03-14', '2026-03-15', 7,
 '[{"sha":"8edd542","date":"2026-03-14","subject":"feat(frontend): add Recharts dependency and monitoring TypeScript types"},{"sha":"ad86685","date":"2026-03-14","subject":"feat(frontend): add API proxy routes for session-logger and Alertmanager"},{"sha":"db073e9","date":"2026-03-14","subject":"feat(frontend): add monitoring API client and Zustand store"},{"sha":"b9662f3","date":"2026-03-14","subject":"feat(frontend): add monitoring dashboard UI components"},{"sha":"6133b78","date":"2026-03-14","subject":"feat(frontend): add monitoring page with tab navigation and polling"},{"sha":"adf5d40","date":"2026-03-14","subject":"feat(frontend): add Monitoring nav item to sidebar"},{"sha":"d792e5d","date":"2026-03-14","subject":"fix(frontend): address review findings in monitoring dashboard"}]'::jsonb,
 '[{"session_id":"170b094c-d629-4abb-b2a0-3ae86137a72e","chunk_idx":0,"note":"First /ship v2 production run: 8 commits, 4 review agents, 5 issues found and fixed"}]'::jsonb,
 'First production run of the /ship v2 7-phase workflow. Merged via PR #11 on Mar 15. 4 tabs (Overview, Services, Alerts, Metrics), Zustand store with 15s polling, Recharts charts, Prometheus metrics parsing.',
 NULL, 'manual'),

('session-capture-pipeline-v2',
 'Session Capture Pipeline v2.0.0',
 'feature', 'shipped', '2026-03-10', '2026-03-14', 8,
 '[{"sha":"d9113d6","date":"2026-03-14","subject":"feat(session-logger): add 3 stats endpoints (overview, daily, concepts)"},{"sha":"ba37593","date":"2026-03-14","subject":"fix(session-logger): sanitize error responses, add Field constraints, consolidate queries"},{"sha":"03c739c","date":"2026-03-14","subject":"feat(session-logger): replace per-request connections with ThreadedConnectionPool"},{"sha":"e08e63b","date":"2026-03-14","subject":"feat(session-logger): add Prometheus instrumentation for stats endpoints"},{"sha":"c6d99ee","date":"2026-03-14","subject":"test(session-logger): add 14 tests for stats + metrics endpoints"}]'::jsonb,
 '[]'::jsonb,
 'Ollama embeddings (nomic-embed-text 768d), summarization, PDF export, knowledge graph. Used to run this very burndown''s session-log audit (48 sessions, 502 chunks, 660 concepts, 3664 graph edges).',
 NULL, 'manual'),

('phase3-foundation-llmanager',
 'Phase 3 Foundation: auth + LLManager inbox',
 'feature', 'shipped', '2026-04-06', '2026-04-08', 12,
 '[{"sha":"2d3f609","date":"2026-04-08","subject":"Merge feature/phase3-foundation-llmanager: auth foundation + LLManager inbox"},{"sha":"b3ba416","date":"2026-04-08","subject":"fix(auth): correct registry API path to /api/v1/security/users/me"},{"sha":"cfeeb76","date":"2026-04-08","subject":"feat(auth): initialize session on app mount"},{"sha":"8a7818d","date":"2026-04-08","subject":"feat(nav): grouped sidebar sections with role-based filtering"},{"sha":"5336d04","date":"2026-04-08","subject":"feat(auth): add Next.js middleware for route guards"},{"sha":"a7d0a6f","date":"2026-04-08","subject":"feat(llmanager): add review store for inbox workflow state"},{"sha":"6b2e376","date":"2026-04-08","subject":"feat(llmanager): add AI reflection panel with quality signals and recommendations"},{"sha":"289df70","date":"2026-04-08","subject":"feat(llmanager): add master-detail inbox layout with review list and detail panel"},{"sha":"5cdc03d","date":"2026-04-08","subject":"feat(llmanager): replace inbox page with master-detail layout"},{"sha":"6a1429b","date":"2026-04-08","subject":"feat(auth): forward Cloudflare JWT through registry proxy"}]'::jsonb,
 '[]'::jsonb,
 'Cloudflare JWT + RBAC + middleware, plus LLManager master-detail inbox. This is the integration point the first-pass burndown missed by filtering --no-merges.',
 NULL, 'manual'),

('langgraph-telemetry-pipeline',
 'LangGraph Telemetry Pipeline (OTel/Tempo)',
 'debt', 'in_progress', '2026-03-06', NULL, 14,
 '[{"sha":"497a44d","date":"2026-03-06","subject":"feat(observability): add Promtail log shipping, Tempo tracing, API tests"},{"sha":"5aeb0aa","date":"2026-03-12","subject":"fix(tracing): graceful degradation when OTel not installed [KILL]"},{"sha":"3140b87","date":"2026-04-06","subject":"feat(infra): healthchecks, OTel tracing, doc consolidation, API tests"},{"sha":"c7b46e6","date":"2026-04-12","subject":"fix(tracing): swap OTLP gRPC exporter for HTTP exporter"},{"sha":"1f6e323","date":"2026-04-12","subject":"feat(tracing): add OTLP/HTTP exporter to cloud requirements"},{"sha":"fe6c617","date":"2026-04-12","subject":"feat(tracing): set OTEL_EXPORTER_OTLP_ENDPOINT in runtime.env"},{"sha":"617a307","date":"2026-04-12","subject":"fix(otel): add opentelemetry deps to pyproject.toml for LangGraph Cloud build"},{"sha":"4153902","date":"2026-04-12","subject":"fix(otel): pass CF Access headers to OTLPSpanExporter explicitly"},{"sha":"54f40d3","date":"2026-04-12","subject":"chore(otel): trigger rebuild to pick up LangSmith OTel secrets"},{"sha":"4073720","date":"2026-04-12","subject":"chore(otel): trigger rebuild to apply LANGSMITH_OTEL_ONLY + /v1/traces endpoint"},{"sha":"e608b8d","date":"2026-04-12","subject":"fix(otel): hardcode tunnel endpoint as fallback, pass explicitly to exporter"},{"sha":"f236196","date":"2026-04-12","subject":"fix(tracing): attach BatchSpanProcessor to langsmith''s TracerProvider in Cloud"}]'::jsonb,
 '[{"session_id":"7c34d257-f6f8-4f59-ae58-dada4b360c75","chunk_idx":7,"note":"Previous session offered three observability options including (A) drop Tempo/OTel"},{"session_id":"871f2db3-bdff-4f4d-906b-bc46d8a92e7d","chunk_idx":6,"note":"Stephen: I had OTEL in the original observability plan and you said we did not need it. Previous session apologized without checking git."}]'::jsonb,
 'DEBT, not feature. Timeline: Mar 6 built (497a44d, Tempo tracing via OTLP gRPC) → Mar 12 KILLED 6 days later (5aeb0aa wrapped OTel imports in try/except, made @traced_node a no-op because LangGraph Cloud couldn''t import opentelemetry-exporter-otlp-proto-grpc) → Apr 6 re-added (3140b87) → Apr 10-12 properly fixed by swapping gRPC for HTTP exporter (c7b46e6). The correct fix (OTLP/HTTP) was available the entire time. A month of tracing blindness because a previous session picked "graceful degradation" over "use the exporter that Cloud supports." Phase 1 Tasks 1-5 done on remote (Cloudflare tunnel + OTLP/HTTP + CF Access headers + deps + LangSmith TracerProvider fix). Tasks 6-13 open: Gate A end-to-end verification, dhg-langgraph-exporter service, compose wiring, Prometheus scrape job, 6 alert rules, Gate B.',
 NULL, 'manual'),

('agents-library',
 'Agents Library (grid/list/table/slide-over)',
 'feature', 'shipped', '2026-04-09', '2026-04-09', 6,
 '[{"sha":"a4b6c46","date":"2026-04-09","subject":"feat(frontend): add AgentsLibrary main container with stats polling and CSS animations"},{"sha":"d72d0fe","date":"2026-04-09","subject":"feat(frontend): swap AssistantsRegistry for AgentsLibrary on agents page"},{"sha":"6037aec","date":"2026-04-09","subject":"feat(frontend): add toolbar, grid, list, table, and slide-over components for Agents Library"},{"sha":"9d8f180","date":"2026-04-09","subject":"feat(agents-library): add backend data layer, catalog, and fix tooltip compatibility"}]'::jsonb,
 '[]'::jsonb,
 'Second iteration. Original agents page enhancement spec+plan landed Mar 15 (c2c8674, cda92e6, e570fb0). Hand-rolled HTML table pattern (agents-library-table.tsx) is the current precedent for tabular UI in the product.',
 NULL, 'manual'),

('intake-prefill-agent',
 'Intake Prefill Agent (PubMed-backed Section B-H draft)',
 'feature', 'shipped', '2026-04-10', '2026-04-10', 13,
 '[{"sha":"6b3cc01","date":"2026-04-10","subject":"feat(intake-prefill): add agent skeleton with state, LLM client, and 4-node graph"},{"sha":"39f4ce6","date":"2026-04-10","subject":"feat(intake-prefill): implement search_literature node with PubMed client"},{"sha":"4742ad2","date":"2026-04-10","subject":"feat(intake-prefill): implement build_context node"},{"sha":"d6671fc","date":"2026-04-10","subject":"feat(intake-prefill): implement generate_prefill node with structured JSON output"},{"sha":"e4d0121","date":"2026-04-10","subject":"feat(intake-prefill): implement validate_output node with type coercion and schema validation"},{"sha":"729f2f2","date":"2026-04-10","subject":"feat(intake-prefill): register intake_prefill graph in langgraph.json"},{"sha":"91776bb","date":"2026-04-10","subject":"feat(intake-prefill): add POST /api/cme/intake/prefill registry endpoint"},{"sha":"c35d697","date":"2026-04-10","subject":"feat(intake-prefill): add PrefillResponse type and prefillIntake API function"},{"sha":"d61fefe","date":"2026-04-10","subject":"feat(intake-prefill): add prefill state, accept/clear actions to intake store"},{"sha":"dad9286","date":"2026-04-10","subject":"feat(intake-prefill): add AI Draft indicators and per-section accept/clear to section nav"},{"sha":"0f957f0","date":"2026-04-10","subject":"feat(intake-prefill): add Research & Prefill button, animated banner, accept/clear controls"},{"sha":"4ca2164","date":"2026-04-10","subject":"feat(intake-prefill): add additional context field, convert therapeutic area and disease state to multiselect"}]'::jsonb,
 '[]'::jsonb,
 '4-node LangGraph agent: search_literature → build_context → generate_prefill → validate_output. PubMed-backed research + structured LLM JSON output. UI accept/clear per-section.',
 NULL, 'manual'),

('inbox-demo-mode',
 'Inbox Demo Mode (sample review data for empty state)',
 'feature', 'shipped', '2026-04-09', '2026-04-09', 2,
 '[{"sha":"504b25e","date":"2026-04-09","subject":"feat(inbox): add demo review data for empty inbox state"},{"sha":"58e5cfc","date":"2026-04-09","subject":"feat(inbox): show demo data when inbox is empty, with banner and action guard"}]'::jsonb,
 '[]'::jsonb,
 'Empty-state visibility — reviewers see sample review data instead of blank inbox. Banner + action guard prevents destructive operations on demo rows.',
 NULL, 'manual'),

('orchestrator-intake-passthrough',
 'Orchestrator intake passthrough fix',
 'fix', 'shipped', '2026-04-11', '2026-04-11', 7,
 '[{"sha":"df73d58","date":"2026-04-11","subject":"spec: orchestrator intake data passthrough fix design"},{"sha":"1834ab1","date":"2026-04-11","subject":"plan: orchestrator intake passthrough implementation — 5 tasks, TDD"},{"sha":"2e93828","date":"2026-04-11","subject":"feat: add flatten_intake aliases (known_gaps, outcome_goals, educational_format, competitor_products) with tests"},{"sha":"ad15992","date":"2026-04-11","subject":"fix: use shallow copies for list aliases in flatten_intake to prevent mutation hazards"},{"sha":"420ed56","date":"2026-04-11","subject":"feat: expand 5 agent wrappers to pass disease_state and all intake fields, with tests"},{"sha":"4f5dba7","date":"2026-04-11","subject":"feat: add disease_state to pipeline initialization log"},{"sha":"d7efb26","date":"2026-04-11","subject":"fix: convert disease_state and therapeutic_area from lists to comma-joined strings in flatten_intake"}]'::jsonb,
 '[]'::jsonb,
 'disease_state was not reaching downstream agents. Fix: flatten_intake aliases + 5 wrapper expansions + list-to-string coercion for agents expecting strings. TDD.',
 NULL, 'manual'),

('inference-platform-api',
 'Local LLM Inference Platform API',
 'feature', 'shipped', '2026-04-11', '2026-04-11', 13,
 '[{"sha":"bea4efe","date":"2026-04-11","subject":"docs: add local LLM inference platform design spec"},{"sha":"6dfb7e7","date":"2026-04-11","subject":"docs: update inference platform spec with review fixes"},{"sha":"99c9dec","date":"2026-04-11","subject":"docs: add local LLM inference platform implementation plan"},{"sha":"72eed52","date":"2026-04-11","subject":"feat: add inference platform database tables"},{"sha":"981dd75","date":"2026-04-11","subject":"feat: add SQLAlchemy models for inference platform"},{"sha":"b4cb76a","date":"2026-04-11","subject":"feat: add Pydantic schemas for inference API"},{"sha":"1bceb62","date":"2026-04-11","subject":"feat: add inference platform API endpoints"},{"sha":"fa81344","date":"2026-04-11","subject":"feat: update LLMRouter to query registry for local models"}]'::jsonb,
 '[]'::jsonb,
 'DB tables + SQLAlchemy models + Pydantic schemas + FastAPI endpoints + LLMRouter registry integration. Scaffolding for the RTX 5090 + Nemotron target.',
 NULL, 'manual'),

('cme-edit-archive-workflow',
 'CME Project Edit + Archive workflow',
 'feature', 'shipped', '2026-04-13', '2026-04-13', 1,
 '[{"sha":"85b7a10","date":"2026-04-13","subject":"feat(cme): add project edit and archive workflow"}]'::jsonb,
 '[]'::jsonb,
 'PUT /api/cme/projects/{id} (edit while status=intake, 409 otherwise) + POST /.../archive (soft delete) + edit route + archive confirm dialog + archived filter tab. Section A therapeutic_area and disease_state narrowed from str to List[str] (DB verified already in target shape). +7 tests.',
 NULL, 'manual'),

('mission-control-dashboards',
 'Mission Control Dashboards redesign',
 'feature', 'shipped', '2026-04-12', '2026-04-13', 4,
 '[{"sha":"b8c8da8","date":"2026-04-12","subject":"feat(dashboards): add basic Grafana link grid placeholder"},{"sha":"e4f4d08","date":"2026-04-12","subject":"feat(dashboards): redesign as mission-control telemetry board"},{"sha":"1ff36f4","date":"2026-04-13","subject":"fix(monitoring): repair chart colors broken by HSL->hex token migration"},{"sha":"28f369f","date":"2026-04-13","subject":"fix(dashboards): readability pass for mission control"}]'::jsonb,
 '[]'::jsonb,
 'Defined the --mc-* token vocabulary (mc-bg, mc-phosphor, mc-amber, mc-alert, mc-cyan) + JetBrains Mono telemetry type + corner-bracket panel frames. Establishes the mission-control aesthetic that the dev-changelog page will hybrid with the inbox editorial aesthetic.',
 NULL, 'manual'),

('agents-tabbed-container',
 'Agents page tabbed container rebuild',
 'refactor', 'shipped', '2026-04-07', '2026-04-07', 12,
 '[{"sha":"8e9420f","date":"2026-04-07","subject":"feat(agents): extend ThreadState/agentsApi and show project name in tree"},{"sha":"973fef7","date":"2026-04-07","subject":"feat(agents): extend agentsApi with VS distributions, outputs, retry, project name"},{"sha":"89d0a75","date":"2026-04-07","subject":"feat(agents): add streaming API with SDK joinStream and event batching"},{"sha":"209fa2a","date":"2026-04-07","subject":"feat(agents): add stream events, token tracking, retry to Zustand store"},{"sha":"2ef26cc","date":"2026-04-07","subject":"feat(agents): add tabbed container with auto-selection and stub tabs"},{"sha":"c6cba28","date":"2026-04-07","subject":"feat(agents): implement detail tab and stream tab with scroll lock"},{"sha":"50aaf5f","date":"2026-04-07","subject":"feat(agents): add VS distribution tab with sparklines and expandable rows"},{"sha":"4a8c428","date":"2026-04-07","subject":"feat(agents): add outputs tab with slide-over viewer and diff toggle"},{"sha":"1dae65a","date":"2026-04-07","subject":"feat(agents): add timeline tab with Gantt bars and cost summary"},{"sha":"221fb5f","date":"2026-04-07","subject":"refactor(agents): remove old agent-detail, all functionality now in tabs"}]'::jsonb,
 '[]'::jsonb,
 'Tabbed detail view (detail, stream, VS distribution, outputs, timeline) replaced old agent-detail page. Distinct from the Apr 9 Agents Library — this is the per-agent detail page, that is the catalog.',
 NULL, 'manual'),

('frontend-docker-networking',
 'Frontend Docker networking fix cluster',
 'fix', 'shipped', '2026-03-15', '2026-03-15', 5,
 '[{"sha":"a4297f7","date":"2026-03-15","subject":"fix(frontend): healthcheck use 0.0.0.0 instead of localhost"},{"sha":"f9b32f8","date":"2026-03-15","subject":"fix(frontend): restore port 3000 mapping for Cloudflare tunnel"},{"sha":"c18044b","date":"2026-03-15","subject":"fix(frontend): resolve Docker networking for all API proxy routes"},{"sha":"06fbc8b","date":"2026-03-15","subject":"fix(frontend): eliminate localhost refs, add registry proxy, fix LangGraph SDK URL"},{"sha":"6795a84","date":"2026-03-15","subject":"docs: add DHG Active URLs reference document"}]'::jsonb,
 '[]'::jsonb,
 'Frontend container networking — healthcheck, port mapping, API proxy routes, localhost elimination. Unblocked Cloudflare tunnel access.',
 NULL, 'manual'),

('inbox-editorial-redesign',
 'Inbox redesign as editorial print journal',
 'feature', 'shipped', '2026-04-08', '2026-04-08', 1,
 '[{"sha":"488ac41","date":"2026-04-08","subject":"feat(inbox): redesign review workflow as editorial print journal"}]'::jsonb,
 '[]'::jsonb,
 'Introduced Fraunces display serif + Source Serif 4 body + IBM Plex Mono metadata. Masthead patterns (triple-line border-top, font-variation-settings SOFT 70), drop caps, stamp-btn letterpress aesthetic, marginal footnotes. This is the editorial vocabulary the dev-changelog page hybridizes.',
 NULL, 'manual'),

('market-intelligence-agent',
 'Market Intelligence Agent',
 'feature', 'backlog', '2026-04-13', NULL, 0,
 '[]'::jsonb,
 '[{"session_id":"d8d64b70-bfda-4e36-a4f0-3fe4a889574b","chunk_idx":12,"note":"Vision discussed in session but no implementation commits"}]'::jsonb,
 'Surfaced only in session logs (second-pass burndown). Not in any prior TODO. Candidate for backlog prioritization.',
 NULL, 'manual');
""")


def downgrade():
    op.drop_index("ix_dev_changelog_window_start", table_name="dev_changelog")
    op.drop_index("ix_dev_changelog_category", table_name="dev_changelog")
    op.drop_index("ix_dev_changelog_declared_status", table_name="dev_changelog")
    op.drop_index("ix_dev_changelog_detected_status", table_name="dev_changelog")
    op.drop_table("dev_changelog")
