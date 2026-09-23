---
name: add-new-capture-module-or-feature-to-registry
description: Workflow command scaffold for add-new-capture-module-or-feature-to-registry in dhgaifactory3.5.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-new-capture-module-or-feature-to-registry

Use this workflow when working on **add-new-capture-module-or-feature-to-registry** in `dhgaifactory3.5`.

## Goal

Adds a new domain-specific capture module or feature to the registry, including endpoints, schemas, services, migrations, models, and tests.

## Common Files

- `registry/<feature>_endpoints.py`
- `registry/<feature>_schemas.py`
- `registry/<feature>_service.py`
- `registry/models.py`
- `registry/alembic/versions/*.py`
- `registry/migrations/*.sql`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Create or update endpoint file(s) for the new feature (e.g., <feature>_endpoints.py)
- Create or update schema file(s) (e.g., <feature>_schemas.py)
- Create or update service file(s) (e.g., <feature>_service.py)
- Update registry/models.py to add new models or fields
- Add or update migration file(s) (e.g., alembic/versions/ or migrations/NNN_<desc>.sql/py)

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.