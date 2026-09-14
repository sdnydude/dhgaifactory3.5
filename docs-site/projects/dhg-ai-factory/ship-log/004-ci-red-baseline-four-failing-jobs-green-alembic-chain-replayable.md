---
title: "CI red baseline: four failing jobs green, alembic chain replayable on a clean database"
sidebar_label: "004 CI red baseline"
sidebar_position: 4
---

# CI red baseline: four failing jobs green, alembic chain replayable on a clean database

| Field | Value |
|-------|-------|
| **Status** | complete |
| **Complexity** | complex (task count), low risk |
| **TDD** | Yes for the docs generator; migrations verified by clean replay |
| **PR** | https://github.com/sdnydude/dhgaifactory3.5/pull/31 |
| **Completed** | 2026-09-13 |
| **Model** | Claude Fable 5.1 (`claude-fable-5-1`) |

## Approach

Four GitHub Actions jobs were red on every PR to master, so CI carried no
signal. Each got the narrowest correct fix: a CI-only placeholder for the one
variable the git-tracked override hard-requires; the documentation-drift check
retargeted from CLAUDE.md (an instruction file) to a generated, committed
service-inventory page; ruff pinned and its 62 findings cleared without
touching the ignore list; and the alembic chain made to replay on an empty
database, which it had never done because production's schema was partly
built by hand. The hard acceptance criterion was a clean replay under CI's
exact Python and pinned dependencies before anything was pushed.

## Spec

All four jobs green on PRs to master; generated `service-inventory.md`
(merged services, Profile column, sorted, no timestamps) checked by
`generate-docs.py --check`; ruff 0.15.11 with zero findings; migrations
self-contained on a clean database (extensions, hand-applied tables); live
registry suite unchanged. Not in scope: ruff rules/ignores, production
database, the override, CLAUDE.md.

## Exploration findings

- The `:?` guard lives in the git-tracked `docker-compose.override.yml`, not
  the base compose (which defaults `POSTGRES_PASSWORD` to `changeme`); it is
  the only hard-required variable.
- The generator iterated three compose files without merging, so override
  merge stanzas produced phantom rows (`grafana` and `dhg-grafana`) and
  profiles were ignored; its graph-count regex matched nothing in CLAUDE.md.
- 38 of the 47 unused-variable findings were `except Exception as e` beside an
  existing `logger.exception`; `ruff --fix` clears 53 of 62 safely.
- Production's `alembic_version` had been set past gaps: `cme_projects`,
  `cme_agent_outputs`, `cme_documents`, `cme_source_references`,
  `cme_intake_fields` and twelve legacy tables (agents, inference, research,
  done-gate, antigravity) exist only from `registry/migrations/*.sql` or psql.
  006's seed JSON carried `:40`/`:true` tokens that SQLAlchemy `text()` reads
  as bind parameters. 011 attaches triggers to a function only the legacy SQL
  defined. The chain runs in one transaction, so a failure anywhere leaves an
  empty database.
- The host runs Python 3.12 with newer libraries than CI's pinned set, so the
  replay had to run in a `python:3.11` container with `registry/requirements.txt`.

## Commits

- `37aba19` ci: CI-only POSTGRES_PASSWORD, ruff pin, generator tests
- `b75fb40` chore(agentshield): refresh baseline at branch start
- `c978447` docs(services): link the narrative page to the generated inventory
- `385d973` feat(docs): generated service inventory page replaces the CLAUDE.md drift check
- `f6db501` style(registry): clear the 62 ruff findings
- `f8ccb44` fix(alembic): create uuid-ossp and vector in the initial migration
- `58d5eb0` fix(alembic): make the migration chain replay on a clean database (002b, 002c, 003 rebase, 006 escapes)
- `33dafd7` fix(review): bootstrap fidelity, loud failures in the docs generator, in-repo alembic guards

## Verification

- **tests:** live registry suite 745 passed; clean-DB replay (fresh pgvector, `python:3.11` + pinned deps) head reached, 742 passed / 3 skipped / 0 failed; generator 9/9; `test_alembic_literals.py` 37 files clean and proven to flag master's 006.
- **CI:** PR #31 all 8 jobs green on the first run (the four former reds included).
- **health checks:** registry-api, registry-db, prometheus, node-exporter healthy; `/healthz` 200 in 2 ms, `/api/v1/projects` 3 ms, `/api/cme/projects` 4 ms, `/api/kb/search` 144 ms.
- **AgentShield:** 1103 findings, 0 new against the refreshed baseline.
- **performance baselines:** n/a (no new endpoints).

## Review findings

Six-agent panel plus a classification audit. Critical: the CME bootstrap
omitted the search-vector trigger functions, so full-text search would have
been silently empty on any bootstrapped database (fixed from production's
function bodies). Important, all fixed: per-table guards, logged skips,
offline `--sql` refused, generator rejects unknown flags and a missing main
compose, compose-style list/map merge, loud port parsing, in-repo alembic
guards, docstring corrections. Minor: nine done, five left as style.

## Deferred Items

- `.gitignore` lacks `langgraph_workflows/dhg-agents-cloud/.venv-prototype/`; a broad `git add` swept 10,057 files into a commit once (caught and rewound before push) — low — one line, needs approval to record.

## Park List

- Five style nits from review (TypedDict service rows, test fixture dedup, sort-then-filter, extra port-form tests); none hides a defect.
- `scripts/` beyond the generator has 411 ruff-fixable findings; not linted by CI, not this ship.
- Legacy `registry/migrations/*.sql` and `registry/init.sql` are now fully superseded by the alembic chain for fresh databases; removal belongs to the LangGraph-era cleanup.

**Tags:** `ci` `github-actions` `alembic` `migrations` `ruff` `docs-generator` `docusaurus` `tdd-guard`
