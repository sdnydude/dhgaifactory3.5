# Planning File Versioning

## Rule
ALWAYS version planning files before overwriting them. Save the current version as `{filename}_v{N}.md` before writing updates.

Applies to:
- `task_plan.md`
- `findings.md`
- `progress.md`
- Any other planning or tracking files

## Process
1. Copy current file to `{filename}_v{N}.md` (increment N from last version)
2. Only THEN write the updated content to the original filename
3. Add version history section to the bottom of the updated file

## Never Expose Secrets
NEVER write actual API key values, tokens, passwords, or credentials into ANY file in the repo. GitHub Actions secret scanning will detect and flag them. Use env var references like `os.getenv("LANGCHAIN_API_KEY")` or `process.env.LANGCHAIN_API_KEY` — never the actual value.
