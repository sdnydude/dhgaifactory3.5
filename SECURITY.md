# Security Guidelines for DHG AI Factory

## Secret Management

- **All API keys and credentials must be stored in the `.env` file** (or injected via Docker environment variables). The project’s `.gitignore` already excludes `.env` to prevent accidental commits.
- **Never hard‑code secrets** in source code. Every secret is accessed via `os.getenv("KEY_NAME")` (or Docker `${KEY_NAME}` syntax).
- Example pattern used throughout the codebase:
  ```python
  import os
  GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
  OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
  ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
  ```

## Runtime Validation (Optional)

A small helper can be added to the orchestrator or a shared config module to verify that required keys are present at startup:
```python
required_keys = ["GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
missing = [k for k in required_keys if not os.getenv(k)]
if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
```
This will abort the service early if a key is missing, preventing obscure downstream errors.

## Key Rotation

When a key is compromised or needs rotation:
1. Generate a new key from the provider.
2. Update the value in `.env` (or the secret store used by Docker).
3. Restart the affected containers (`docker compose restart <service>`).

## Auditing

- Periodically run a grep for `os.getenv` to ensure no new hard‑coded secrets appear.
- Review the `.gitignore` to confirm `.env` and any other secret files remain excluded.

---
*This document is intended for developers and DevOps engineers working on the DHG AI Factory project.*
