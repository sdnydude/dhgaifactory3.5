# LSP Setup for Claude Code in DHG AI Factory

**Status:** Design approved, pending spec review
**Author:** Stephen Webber + Claude (pair)
**Date:** 2026-04-14

## Goal

Give Claude Code precise, type-aware navigation and cross-reference data for this repo via the built-in LSP tool, and use the same configuration as a local quality gate that catches real bugs before they reach runtime.

Two values from one configuration:

1. **Intel for Claude** — `goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `prepareCallHierarchy` / `incomingCalls` / `outgoingCalls`, `goToImplementation`. Nine operations that replace grep-guessing with compiler-grade answers.
2. **Quality gate** — `npx pyright` and `tsc --noEmit` at the CLI catch type errors, None-safety bugs, and API drift locally, reproducible in CI later.

## Non-goals

- Not setting up pyright / tsc in CI in this spec. CI integration is a follow-up once the baseline is clean.
- Not modifying any Docker container.
- Not modifying any existing `.venv`.
- Not attempting to run LSP servers inside containers. Claude Code's LSP tool spawns pyright-langserver and typescript-language-server as host subprocesses over stdio JSON-RPC; there is no supported path to route that at a container.
- Not fixing the ~15 findings surfaced by the noise-floor measurement. Those become a separate backlog once the config is in place.

## Repo shape that drives the design

Python lives in several subtrees with different dependency sources:

| Subtree | Has local venv? | Deps source | Include in pyright? |
|---|---|---|---|
| `langgraph_workflows/dhg-agents-cloud/` | Yes — `.venv` (live, langchain 1.2.11, langgraph 1.1.0, pydantic 2.12.5, sqlalchemy 2.0.48, anthropic 0.84.0) | Host venv | **Yes** — use its venv |
| `registry/` | **No host venv** | `dhg-registry-api` container | **Yes** — use docker-cp snapshot |
| `services/vs-engine/` | No | `dhg-vs-engine` container | Deferred (not actively edited) |
| `services/*` (session-logger, logo-maker, pdf-renderer) | No | Containers | Deferred |
| `scripts/` | Yes — `.venv` (minimal, httpx only) | Host venv | Low priority — can add later |
| `.venv` at repo root | **Broken** — python symlink points to nonexistent python3.14 | — | **Ignore** (dead) |
| `website/` | — | Last Python touch 2026-03-12, last md touch 2026-04-08. Static site generator output directory. | **Exclude** |
| `langgraph-dev/` | — | Pre-rename-to-dhg-agents-cloud snapshot, legacy | **Exclude** |

TypeScript lives in `frontend/` with an existing `tsconfig.json` (strict mode, bundler resolution, paths configured). No changes needed — typescript-language-server auto-discovers tsconfig.json.

## Approach

### 1. Host prerequisites (once per machine)

```bash
npm install -g pyright
npm install -g typescript-language-server typescript
```

Both servers run as host subprocesses. The Claude Code `pyright-lsp` and `typescript-lsp` plugins (already enabled in `~/.claude/settings.json` and `.claude/settings.json`) register the LSP tool against them.

### 2. Container site-packages snapshots for the registry subtree

Because `registry/` has no host venv and its deps live only in `dhg-registry-api`, extract the container's site-packages to a host directory that pyright treats as an `extraPaths` source. This is a read-only copy — the container is untouched.

```bash
mkdir -p .pyright-stubs/registry
docker cp dhg-registry-api:/usr/local/lib/python3.12/site-packages/. .pyright-stubs/registry/
```

Rerun this command whenever `registry/requirements.txt` changes or the container is rebuilt. That's the full upkeep.

`.pyright-stubs/` is gitignored — it's a regeneratable cache, same pattern as `.codegraph/`.

### 3. `pyrightconfig.json` at repo root

```jsonc
{
  "include": [
    "langgraph_workflows/dhg-agents-cloud/src",
    "langgraph_workflows/dhg-agents-cloud/tests",
    "registry"
  ],
  "exclude": [
    "**/__pycache__",
    "**/.venv",
    "**/node_modules",
    ".pyright-stubs",
    "website",
    "langgraph-dev",
    "agents",
    "docs/archive"
  ],
  "executionEnvironments": [
    {
      "root": "langgraph_workflows/dhg-agents-cloud",
      "venvPath": "langgraph_workflows/dhg-agents-cloud",
      "venv": ".venv",
      "pythonVersion": "3.11"
    },
    {
      "root": "registry",
      "extraPaths": [".pyright-stubs/registry"],
      "pythonVersion": "3.12"
    }
  ],
  "reportMissingImports": "error",
  "reportOptionalMemberAccess": "none",
  "reportGeneralTypeIssues": "error",
  "typeCheckingMode": "basic"
}
```

Why these specific settings:

- `reportOptionalMemberAccess: "none"` — measured noise floor showed 29/40 errors on the orchestrator were defensive `asyncio.gather(return_exceptions=True)` patterns where the code already handles the None case. Muting drops the orchestrator from 40 → ~11 actionable errors without losing signal, per the noise-floor measurement captured in this session.
- `typeCheckingMode: "basic"` — strict mode is aspirational for a codebase that's never been type-checked. Start at basic, tighten per-file via `# pyright: strict` comments on new modules.
- The `agents/` subtree is excluded because it's the legacy decommissioned Docker-based agent system — no point spending cycles on code that's being retired.

### 4. `.gitignore` addition

```
.pyright-stubs/
```

### 5. `frontend/tsconfig.json`

No change. Existing config is already correct for LSP purposes (strict, paths wired, modern moduleResolution).

## How Claude will actually use this

After the config is in place:

- **Exploration queries** (`how does X work?`, `where else do we Z?`) continue to use CodeGraph Explore subagents — that tool remains the right one for open-ended discovery because it returns full source sections in one hop.
- **Precision queries during editing** (where does this function get called from? what's this symbol's definition? what are this type's members?) use the LSP tool directly — single operation, exact answer, no grep guessing.
- **Before committing** (and before merging, once CI is added) run `npx pyright` and `npm --prefix frontend run typecheck` to catch type errors. This is a local quality gate, not a hook — it runs when explicitly invoked.

The division of labor:

| Need | Tool |
|---|---|
| "How does this system work?" | CodeGraph Explore subagent |
| "What are all the callers of `create_registry_record`?" | `LSP findReferences` |
| "Jump to the definition of this symbol" | `LSP goToDefinition` |
| "What methods does this object expose?" | `LSP hover` / `documentSymbol` |
| "Catch bugs before commit" | `npx pyright` at CLI |

## What this explicitly protects against breaking

Enumerated because Stephen asked "NOTHING GETS BROKEN?":

- **Docker containers** — untouched. `docker cp` is a read-only extract.
- **Existing venvs** — untouched. Pyright reads them via `venvPath`, it does not write to them.
- **Running services** — untouched. No restart, no rebuild.
- **CodeGraph** — unaffected. LSP is additive, CodeGraph sync hooks keep running.
- **CI** — unaffected. This spec is local only. CI integration is a follow-up.
- **Existing tsconfig.json** — untouched.
- **.gitignore** — one line added. Existing entries preserved.

The only files this spec creates or modifies:

1. `pyrightconfig.json` (new, repo root)
2. `.gitignore` (one line added)
3. `.pyright-stubs/registry/` (new, gitignored, regeneratable)

## Latent bug already surfaced

The noise-floor measurement against `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py` surfaced a real production bug at line 1795:

```python
checkpointer = await AsyncPostgresSaver.from_conn_string(DATABASE_URL)
```

`AsyncPostgresSaver.from_conn_string` returns an `_AsyncGeneratorContextManager`, not an awaitable. The correct shape is:

```python
async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
    await checkpointer.setup()
    ...
```

The current code almost certainly falls into the `except Exception` branch every time and logs "using in-memory", meaning production orchestrator runs have been running without PostgresSaver checkpointing.

**This is not part of this spec.** It is a separate debug task, flagged here so it doesn't get lost. Fixing it requires understanding whether the surrounding code path actually needs a context-managed checkpointer or a pool-based one.

## Measurement summary (what we actually saw)

Ran `npx pyright` against real code, not hypothetically:

| Target | Errors | Time | Notes |
|---|---|---|---|
| `langgraph_workflows/.../orchestrator.py` (1,889 LOC) with existing venv | 40 | 0.85s | 29 `reportOptionalMemberAccess` (mutable in config), 1 real latent bug (above), ~10 signal |
| `registry/api.py` with `reportMissingImports: none` | 4 | 1.07s | All 4 look real: Media.status assignment, None-safety on client_id, 2× API-drift kwargs |

Total actionable signal on sampled code: ~15 real findings. Noise after config tuning: near zero.

## Acceptance criteria

- [ ] `which pyright-langserver` returns a path
- [ ] `which typescript-language-server` returns a path
- [ ] `pyrightconfig.json` exists at repo root with the content above
- [ ] `.gitignore` contains `.pyright-stubs/`
- [ ] `.pyright-stubs/registry/` contains registry container site-packages
- [ ] `npx pyright` completes without configuration errors
- [ ] `npx pyright registry/api.py` surfaces real findings (target: ~4 from the measurement survive once imports resolve; exact count may shift as pyright sees full types)
- [ ] `npx pyright langgraph_workflows/dhg-agents-cloud/src/orchestrator.py` runs in under 3 seconds and surfaces the line-1795 AsyncPostgresSaver bug in the output
- [ ] Claude Code's `LSP goToDefinition` returns a result when invoked on a symbol in `registry/api.py` imported from `fastapi`
- [ ] Claude Code's `LSP goToDefinition` returns a result when invoked on a symbol in `orchestrator.py` imported from `langgraph`
- [ ] No Docker container has been restarted or rebuilt during implementation
- [ ] No existing `.venv` has been modified during implementation

## Out of scope (deliberate)

- Fixing the ~15 findings surfaced by the measurement
- Fixing the AsyncPostgresSaver bug (separate task)
- Adding pyright/tsc to CI
- Covering `services/vs-engine/`, `services/session-logger/`, `services/logo-maker/`, `services/pdf-renderer/` — defer until one of them becomes actively edited
- Covering `scripts/` — deps are trivial, can add later
- Removing the broken root `.venv` — not this spec's job
- Stub snapshots for the `dhg-agents-cloud` container (we use its host venv instead)

## Rollback

Every step is reversible in one command:

```bash
rm pyrightconfig.json
rm -rf .pyright-stubs
# revert .gitignore line
```

No state lives in Docker, no state lives in venvs. The full blast radius is three paths.
