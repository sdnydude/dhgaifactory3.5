# CME rebuild input: what carries forward from the first pipeline

Date: 2026-09-16. Source: read-only inventory of `langgraph_workflows/dhg-agents-cloud/src/prompts/`, `registry/models.py`, the CME service and endpoint layer, and both test trees. Graph-builder and registration facts re-verified in the main session (three builders at orchestrator.py:1651, :1695, :1792; three registered graphs).

## Prompts: 17 constants in 12 modules, 546 lines

| Prompt | Verdict | Why |
|---|---|---|
| Learning objectives | Keep | Moore levels 3A/3B/4/5 with allowed verb lists per level, objective sentence template, six banned patterns, 6 to 10 objectives, at least 60 percent at level 4 or above. Highest-value prompt in the repo. |
| Gap analysis | Keep | Five gap-validity predicates (evidence-based, quantifiable, addressable, outcome-linked, barrier-analyzed), four barrier categories, 5 to 8 gaps. |
| Clinical practice | Keep | Practice-versus-guideline distinction, five-way barrier taxonomy (knowledge, skill, attitude, system, patient), real-world evidence sourcing. |
| Research | Keep | At least 30 citations, three-year recency preference, five-year flag. |
| Research protocol | Keep | Moore levels 3 to 6 mapped to measurement methods; 40 to 60 percent attrition expectation. |
| Curriculum design | Keep | Adult-learning principles, 40:60 active-to-passive floor, prohibited patterns. |
| Grant writer | Keep | Integration and consistency rules, cold-open thread, banned phrases. |
| Cold open (needs assessment) | Keep | 50 to 100 word four-beat narrative: moment, person, stakes, turn. |
| Banned patterns guidance | Keep as a linter | No em dashes, no prose colons, 17 banned words with mandated substitutions, three banned paragraph openers, seven exact section headers, never "studies show". Deterministic, not prompt text. |
| Intake prefill user template | Keep as a schema | Sections B through H field by field with per-section confidence. This is the intake contract. |
| Compliance review | Keep content, rewrite | Six ACCME standards named and numbered, but each compressed to one line. |
| Citation checker system | Keep as rules | AMA format, ten-year staleness with landmark exception, retraction is a hard fail, five verification states. |
| Citation verification | Rewrite | Real matching logic wrapped in JSON-shape boilerplate. |
| Citation summary | Rewrite | Thin. |
| Marketing plan | Rewrite | Contains stale hardcoded economics: cost per registration in dollars and channel splits. |
| Intake prefill system, citation extraction | Drop | "Return JSON only" instructions a structured-output model makes unnecessary. |
| Citation format block | Drop as prose | Identical five-line block pasted into eight prompts; becomes one shared output contract. |

No prompt hardcodes a drug, guideline year or trial. The needs assessment prompt tells the model to choose trials relevant to the disease state. That choice is deliberate and should be preserved.

## Domain knowledge to turn into typed schemas and evals

ACCME's six standards; Moore's outcomes levels 3A through 6 with per-level verb lists and per-level measurement methods (level 6 flagged as rarely achievable); the five-category barrier taxonomy; gap validity as five booleans; numeric bounds (5 to 8 gaps, 6 to 10 objectives, 60 percent at level 4 plus, 30 citations, 40:60 active ratio, 50 to 100 word cold open); the citation policy (AMA, ten-year rule, landmark exception, retraction fail, five-value enum, three-year preference); the house style rulebook. Nearly all of it is mechanically checkable and belongs in validators and evals, not prose.

## Registry data model: eight CME tables, mostly sound

- `CMEProject` (models.py:327): intake as one JSON blob of 10 sections and 47 fields, status enum, outputs, agent progress, LangGraph thread and run ids, Drive sync columns, plus four legacy single-reviewer columns superseded by the assignment table.
- `CMEPipelineRun` (:396): one row per run with a monotonic run number.
- `CMEAgentOutput` (:436): per-agent JSON content, quality score, 768-dimension embedding and full-text vector.
- `CMEReviewerConfig` (:469): reviewer identity, active flag, concurrency cap, notification preferences, rolling stats. The cap and stats are stored but no code was found enforcing or updating them (not exhaustively verified).
- `CMEReviewAssignment` (:499): reviewer order 1 to 3, status, SLA deadline, annotations, reminder and escalation timestamps.
- `CMEDocument` (:542): immutable versioned documents, delete restricted, seven-year retention date for ACCME, quality fields, embedding, Drive sync. Well designed.
- `CMEIntakeField` (:598): the intake JSON exploded into searchable rows.
- `CMESourceReference` (:633): PubMed, DOI and URL citations with cached content and a verification status. Well designed.

Endpoint layer: 32 routes in `cme_endpoints.py` covering projects, pipeline control, outputs, webhooks, reviewers, review workflow, search and RAG, agent-gateway writes.

Review and SLA machinery: sequential three-reviewer assignment with 24-hour windows is implemented (`cme_review_service.py:62`, `:110`); the SLA scheduler with 15-minute checks, four-hour warnings, timeout promotion and daily hold reminders is implemented and feature-flagged (`timeout_handler.py:43`, `:80`, `:161`, flag at `:27`). Three gaps: submitting for review never calls the notification layer, so reviewers are assigned silently; the review submission takes the reviewer's email as a plain parameter; the reviewer concurrency cap and stats appear unenforced.

## Tests

LangGraph side: 7 files, 166 tests, heavily mocked, no golden outputs and no eval corpus. Nothing asserts that a generated objective sits at Moore level 4 or that a needs assessment obeys the style rules against real model output.

Registry side: 283 CME and review tests in 9 files. The review-service and SLA-scheduler tests look genuine. `test_review_workflow.py` is largely self-asserting (it recomputes local arithmetic and asserts it equals itself) and should not be counted as coverage.

## Reuse verdict

Carry forward as-is: the `CMEDocument`, `CMESourceReference` and `CMEIntakeField` schemas; run numbering; the SLA scheduler shape and its feature flag; the domain content of the eight keep prompts.

Carry forward as typed schema and eval material: the intake template as Pydantic models; Moore verb lists as enums plus a verb-membership eval; the banned-patterns guidance as a deterministic linter; count bounds and the 60 percent rule as validators; the citation policy as a typed verification result; the six ACCME standards as a scored rubric.

Leave behind: the duplicated citation block; the JSON-shape prompts; JSON skeletons inside prompt strings; the marketing dollar figures; the self-asserting workflow tests; the legacy single-reviewer columns; the unauthenticated reviewer-email parameter.

## Tooling note

The CodeGraph index does not include `src/prompts/`, and its explore tool drifted to unrelated frontend files on a review-SLA query. The prompt inventory came from direct reads. Re-indexing the prompts directory is a small maintenance item for the CodeGraph setup.
