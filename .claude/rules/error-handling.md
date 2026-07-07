# Error Handling — no raw exception text in API responses

Applies to the FastAPI registry (`registry/`) and any HTTP endpoint layer.

## The rule
- **Never return raw exception text to a client.** `HTTPException(detail=str(e))` and `detail=f"...{e}..."` are prohibited — a caught exception can carry stack fragments, SQL, file paths, or connection strings, and the exact string is a fragile API contract that silently changes when the underlying error changes.
- **Expected failures use explicit, controlled messages.** For a known failure mode (not-found, conflict, validation), raise `HTTPException` with a message you wrote by hand — derived from request data you already trust (`payload.slug`, `req.node_name`), never from the exception object. Interpolating a client-supplied identifier is fine (`detail=f"Spec '{payload.slug}' already exists"`); interpolating the exception is not.
- **Log the real error server-side.** Before raising the controlled HTTPException, `logger.warning(...)`/`logger.exception(...)` the caught exception so the detail isn't lost to operators.
- **Prefer typed exceptions.** Service layers should raise domain exception types (or `ValueError`/`RuntimeError` with controlled messages); endpoints catch the specific type — never a bare `except:` or broad `except Exception` that then echoes `str(e)`.
- **Unexpected exceptions belong to the global handler.** Don't catch-and-echo an exception you didn't anticipate; let it propagate to the app-level handler, which returns a generic 500 (optionally with a correlation ID for log lookup).

## Reviewer grep
The actual leak class is `detail=str(e)` and exception-interpolating f-strings:
```
grep -rn 'detail=str(e)' registry/            # must return zero
grep -rEn 'detail=f".*\{e[.}]' registry/      # exception in an f-string — must return zero
```
`detail=f"...<static text and trusted request fields>..."` (e.g. `detail=f"Agent {service_id} not found"`) is **not** a leak — those are intentional, safe messages and should not be flagged.
