# /ship Prompt — CME Pipeline & Web UI Production-Readiness Audit

**How to run:** Start a fresh session and invoke `/ship_v4` with this file as the feature brief:
`/ship_v4 CME pipeline production audit — follow docs/prompts/2026-06-12-cme-pipeline-production-audit-prompt.md`

**Before starting:** `ship-state_v2.md` (Memreg pipeline, phase 1) is in_progress. Version it per
`.claude/rules/planning-file-versioning.md` and park it — do NOT overwrite or silently abandon it.

---

## Mission

This is an **audit-only ship**. The deliverable is a review-and-critique report plus a phased refactor
plan — NOT the refactor itself. Stop at the end of /ship planning phases and present the report for
Stephen's approval. No code changes, no container rebuilds, no infra modifications. The only files you
write are the report, the refactor plan, and ship/planning state files.

The CME pipeline is a year-long project that has never been proven end-to-end. The goal of the
refactor this audit enables:

1. **Make the pipeline work end-to-end** — a real topic in, a complete reviewed grant package out.
2. **Evidence-based drafts** — every draft sent to human review must be grounded in verifiable
   citations (PubMed-checked), with citations surviving all the way into the final assembled documents.
3. **Temporary inline reviewer insights** — generated drafts must carry inline AI annotations
   (rationale, confidence, compliance flags, "this claim needs a source") embedded IN the document,
   visible during human review in the inbox, and mechanically stripped at final approval. Audit what
   exists today (prose-quality scoring, reflection panel — which are *sidebar* metadata, not in-document)
   versus this requirement, and specify the gap.
4. **Everything else** keeping the project from production: error handling, retries, checkpointing,
   dev-mode bypasses, cost controls, observability gaps, test coverage, docs/code drift.
5. **The web UI gets the same rigor** — it is in scope as a first-class audit target, not an afterthought.
6. **Own the trace data** — research how LangChain/LangGraph tracing integrates with memreg so DHG
   captures and owns pipeline trace data in the registry, in service of the DHG TRUTH foundation
   and policies (Scope C below).

## Scope A — CME Pipeline

- **13 agent graphs** in `langgraph_workflows/dhg-agents-cloud/src/`: needs_assessment, research,
  clinical_practice, gap_analysis, learning_objectives, curriculum_design, research_protocol,
  marketing_plan, grant_writer, prose_quality, compliance_review, citation_checker, registry agent.
- **3 orchestrator recipes** in `orchestrator.py`: needs_package, curriculum_package, grant_package —
  including the Prose QA retry loops, compliance gate, and human-review interrupts.
- **Citation path specifically:** research agent source gathering → citation_checker PubMed
  verification → registry gateway writes → do verified citations actually appear in grant_writer
  output? Trace the data flow node by node; this is goal 2's backbone.
- **Registry CME surface:** `registry/cme_endpoints.py`, related services/schemas, the
  `registry_request` gateway pattern, idempotency, dead-letter queue.
- **Export pipeline:** `services/pdf-renderer/` (renderer, bundler, drive_sync, worker),
  `registry/export_endpoints.py` + `export_signing.py`, print route, download_jobs lifecycle.
- **Cloud/local parity:** production is LangGraph Cloud; local dev is port 2026. Identify config,
  env-var, and network assumptions that differ (host.docker.internal, API keys, checkpointer).

## Scope B — Web UI (`frontend/src/`)

- **/inbox review workflow:** `components/review/`, `stores/review-store.ts`, `lib/inboxApi.ts` —
  interrupted-thread listing, resume-with-decision, 30s refresh. Does the full
  approve/revise/reject loop actually round-trip to LangGraph Cloud?
- **Files tab + downloads:** `lib/filesApi.ts`, `stores/files-tab-store.ts`, downloads tray + polling.
- **Auth/RBAC:** `middleware.ts`, `lib/permissions.ts`, session store, registry proxy route
  (`app/api/registry/[...path]/route.ts`), and every place `SECURITY_DEV_MODE` bypasses something —
  enumerate the bypasses; each is a production blocker.
- **Chat front page, role-aware sidebar, CopilotKit/assistant-ui wiring.**
- **Quality:** state bugs, error/empty/loading states, accessibility, DHG brand-token compliance
  (`.claude/rules/dhg-brand.md`), light/dark mode.

## Scope C — Research: LangChain/LangGraph × memreg trace capture

This is a research task inside the audit, with its own report section. **Motivation:** pipeline trace
data (agent runs, node inputs/outputs, token usage, QA scores, citation verifications, human-review
decisions) is critical to the DHG TRUTH foundation and policies — DHG must own, store, and be able
to audit this data, not rent visibility to it. Today the dual-tracing stack sends spans to LangSmith
Cloud (DHG does not own that data) and OTel→Tempo (owned, but ephemeral metrics-grade storage, not a
queryable knowledge store). Memreg (registry KB + capture pipeline) is the system of record — traces
should feed it.

**The DHG TRUTH Commitment (canonical — provided verbatim by Stephen 2026-06-12; do not re-derive
or reword the pillars):**

> **T — Technology you can understand.** AI shouldn't be mysterious. We build systems that explain
> their reasoning in plain language. No black boxes. No "trust us, it just works." You'll always know
> why our AI reached its conclusions.
>
> **R — Rights to your data and insights stay with you.** Your data is yours. Your discoveries are
> yours. Your competitive advantage is yours. We never claim ownership of what you create or learn
> using our tools. Always.
>
> **U — Universal access.** We believe AI belongs in the hands of the many, not just the elite few
> with enterprise budgets. Small businesses deserve the same powerful tools that Fortune 500
> companies use. That's not idealism — it's our business model.
>
> **T — Transparency about how we build, train, and recommend.** We'll tell you who builds our AI,
> what data trains it, and how our algorithms reach their recommendations. No trade-secret excuses.
> No fine-print surprises.
>
> **H — Honest policies.** We advocate for government data policies that prioritize openness,
> fairness, and equity. We're committed to democratizing AI — because technology this powerful
> shouldn't be gatekept by the privileged few.

No formal TRUTH foundation document exists yet (the long-referenced `TRUTH.md` was never written —
confirmed by this prep session and independently by the March 2026 brand-voice discovery, Drive file
`brand-voice-guidelines.md` id `13EXVpq97Ln5MPtCJhQiFUAIaufRPG4oc`, Open Questions §1). Supporting
fragments to weave in: the "TRUST Ethos" brand note (`docs/archive/BRAND_COLORS.md:250`),
digital-harmony-studio's CLAUDE.md ETHOS ("favor determinism, auditability, and recovery"), the
DHG-Reliability-v1 standard and "validated truth substrate" division charter
(`~/DHG/Zips/dhg_agents_depot/dhg_agent_framework_doc_3_narrative_writing.md`), and the
evidence/citation governance rules in `brand-voice-guidelines.md` §5.

**Deliverable (in addition to the research below): draft the DHG TRUTH foundation document** —
the verbatim commitment above as its core, plus operational policies that make each pillar
enforceable in the platform: data-ownership and provenance policies, what data sources feed the
authoritative record (pipeline traces, registry KB, citation verifications, human-review outcomes),
and where it lives (proposal: registry as system of record with a published TRUTH.md view). Submit
inside the report for Stephen's approval. Map every Scope C recommendation to a named pillar — trace
capture serves **T** (a queryable record of why each agent reached its conclusions), **R** (DHG and
its clients own the trace data rather than renting visibility from LangSmith Cloud), and
**Transparency** (documented, auditable evidence of how drafts and recommendations are produced).

**Research questions — evaluate each option with evidence (Context7/official docs, not training
knowledge; cite versions):**

1. **Custom LangChain callback handlers / BaseTracer** — write run trees directly to registry
   Postgres alongside LangSmith. Effort, fidelity, maintenance burden across langchain-core upgrades.
2. **LangSmith API export** — scheduled pull of runs/feedback into memreg tables. Rate limits, data
   completeness, lag, cost tier required.
3. **OTel-native route** — point the existing 85 `@traced_node` spans (or LangSmith's OTel endpoint)
   at a collector that fans out to Tempo AND a registry ingestion worker. Reuses what's built.
4. **PostgresSaver checkpointer mining** — LangGraph checkpoints already persist full state
   transitions; assess extracting trace-grade data from checkpoint history vs adding new
   instrumentation.
5. **Self-hosted LangSmith** — licensing, infra cost on g700data1, whether it actually transfers data
   ownership or just data location.

**Memreg empowerment angle:** beyond capture, how trace-derived facts (which agents fail where, prose
QA score trends, citation-verification pass rates, human reviewer overrides) flow into the existing KB
tables so future sessions and the memreg daemon learn from pipeline history — the same
ReasoningBank-style loop Debug Ops uses, applied to the CME pipeline.

**Deliverable:** comparison table of the five options (data ownership, completeness, effort, cost,
maintenance, TRUTH alignment), a single recommendation with rationale, and where it lands in the
phased refactor plan. This is research only — no implementation this session.

## Method — non-negotiable tool discipline

1. **kb-search FIRST.** Run the `kb-search` skill before exploring: prior decisions, deferred items,
   bug fixes, and insights for cme/langgraph/frontend/registry. Prior sessions already found problems —
   do not re-derive them; verify whether they're still open.
2. **CodeGraph and Serena before grep.** Symbol lookups go through `codegraph_search`/`_callers`/
   `_impact`/`_node` or Serena `find_symbol`/`find_referencing_symbols`. Open-ended "how does X work"
   questions go to Explore subagents built with the `codegraph-explore` skill prompt template. Grep
   only for string literals and non-code files. Run `codegraph sync` if results look stale.
3. **Docs are a primary source — and docs/code drift is a finding.** Use `docs-site/` (Docusaurus),
   `DHG-CME-12-Agent-Docs/`, `docs/superpowers/specs/` and `plans/`, `docs/TODO.md`,
   `docs/resolved-issues.md`. Where documentation claims behavior the code doesn't have (or vice
   versa), record it in the report.
4. **Memreg/Claude-managed sources:** registry KB, `.remember/`, memory directory, MEMORY.md,
   ship-state archives. These hold a year of context — use them.
5. **Verify, don't assert (honesty protocol).** Every finding carries an evidence pointer: file:line,
   test output, LangSmith trace ID, curl response, or screenshot. Run the real checks:
   - `npx pyright` and `npm --prefix frontend run typecheck`
   - registry pytest suite (`registry/test_*.py`) and LangGraph tests
     (`langgraph_workflows/dhg-agents-cloud/tests/`); record pass/fail counts
   - Frontend Playwright E2E where runnable without infra changes
   - **One bounded live pipeline run:** execute `needs_package` (NOT grant_package) against LangGraph
     Cloud or local 2026 with a cheap test topic, follow it in LangSmith, and document exactly where it
     succeeds, stalls, or breaks. State the estimated API cost before running and proceed only if it is
     trivial; a full grant_package burn is a recommendation for the refactor phase, not this audit.
   - Read-only infra checks are pre-authorized (docker ps, logs, curl healthz, psql SELECT, Grafana/
     Prometheus/LangSmith reads). Anything that mutates state is forbidden this session.
6. **Subagent fan-out is encouraged** (Explore for understanding, review agents for code quality), but
   verify any subagent *diagnosis* with a direct check before it enters the report.

## Report — required structure

Write to `docs/superpowers/reviews/2026-06-12-cme-pipeline-production-audit.md`:

1. **TL;DR** — ≤10 bullets. Lead with: can it run end-to-end today, yes/no, and the single biggest blocker.
2. **Narrative** — the honest story of where the pipeline stands: what demonstrably works (with proof),
   what's wired but unproven, what's broken, what's missing entirely, and why a year of work hasn't
   reached production. Written for Stephen — direct, no softening.
3. **Fully detailed comparison table** — one row per component (each of the 13 agents, each of the 3
   recipes, citation path, registry CME surface, export pipeline, each web-UI area, auth, observability,
   tests). Columns: **Component | Current state | Evidence (file:line / trace / test) | Gap vs
   production requirement | Effort (S/M/L) | Priority (P0–P3)**. No row may say "unknown" — if you
   couldn't verify it, the gap is "unverified" and that itself is a P-rated finding.
4. **Foreseeable blockers** — technical (LangGraph Cloud constraints, checkpointing, token costs at
   scale), compliance (ACCME requirements vs current compliance_review depth), operational (secrets
   management, dev-mode bypasses, single-server deployment), and process blockers.
5. **Open-source publishing assessment** — Stephen is considering publishing this repo open source.
   Assess concretely:
   - Secrets exposure: scan git **history**, not just HEAD (.env handling, keys, tokens)
   - Hardcoded internals: 10.0.0.251, digitalharmonyai.com hostnames, Cloudflare tunnel IDs,
     LangGraph Cloud deployment URLs, LangSmith org references
   - Business-sensitive content: CME client material, grant content, pricing, DHG-internal docs in
     `docs-site/`/`DHG-CME-12-Agent-Docs/`/memory files
   - License status (is there a LICENSE file?), dependency license compatibility
   - What to redact, what to split into a private repo, and a publish/don't-publish/publish-subset
     recommendation with reasoning
   - Weigh the TRUTH Commitment in the recommendation: pillars **U** (universal access) and **H**
     (honest policies) argue FOR open-sourcing the platform; pillars **R** (client data rights) and
     business-sensitive CME content argue for careful scoping of WHAT is published. The
     recommendation must reconcile these explicitly, not just list risks.
6. **Trace-capture research findings (Scope C)** — the five-option comparison table, the drafted
   DHG TRUTH foundation document (for Stephen's approval) with pillar mapping, and the single
   recommended architecture for routing LangChain/LangGraph trace data into memreg.
7. **Phased refactor plan** — sequenced for the actual refactor /ship sessions: P0 (make end-to-end
   work) → P1 (citations + inline reviewer insights) → P2 (production hardening + trace capture
   per Scope C recommendation) → P3 (polish).
   Each phase gets concrete acceptance criteria. **No deferrals** — every open question in the plan is
   resolved with a pinned decision or an explicit P-rating; "TBD" is not an acceptable entry.

## Constraints

- Audit is read-only against running systems. Report + plan files are the only writes.
- Version any planning file before overwriting (`_v{N}.md` rule).
- Never display secret values; masked existence checks only.
- Capture rules fire as normal during the session (deferred items, insights, decisions to registry).
- Match findings to evidence. A finding without proof gets labeled "assumption" and downgraded.
- Present the finished report and refactor plan, then STOP for Stephen's approval before any
  implementation phase begins.
