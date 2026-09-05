# DHG Agent Boilerplate

Starting point for a new DHG agent, built on **Pydantic AI** and traced with the
self-hosted **Langfuse**. LangGraph and LangSmith are retired (ADR-001); nothing
in this template imports `langgraph`, `langsmith`, or `langchain_*`.

```
agent-boilerplate/
  requirements.txt            runtime pins
  requirements-dev.txt        + pytest
  src/agent.py                the agent, registry client, CLI
  src/tracing.py              Langfuse/OTel wiring (no-op without keys)
  src/prompts/template_agent.py   prompt constants
  tests/test_smoke.py         imports the agent with no keys set
```

## Make it yours

1. `TEMPLATE-AGENT` / `template_agent` -> your agent name, everywhere.
2. Rename `src/prompts/template_agent.py` and its constants; edit the prompt
   text **there**. Agent code imports prompt constants and never inlines a
   prompt literal (`.claude/rules/llm-prompts.md`).
3. Replace the `AgentOutput` fields with your real output contract. Pydantic AI
   validates the model's response against it and retries on a mismatch, so this
   is the schema, not a suggestion.
4. Fill in `capabilities` and `io_schema` in the registry manifest.
5. Add tools with `@agent.tool_plain` / `@agent.tool` as needed.

## Run it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python src/agent.py "your topic here"
.venv/bin/python -m pytest tests -q
```

## Model selection (LLM-agnostic)

The model is one env var, `AGENT_MODEL`, in Pydantic AI's `<provider>:<model>`
form. No code change is needed to switch providers.

| Target | Env |
|---|---|
| Default (Claude) | unset -> `anthropic:claude-opus-5`, needs `ANTHROPIC_API_KEY` |
| Cheaper Claude | `AGENT_MODEL=anthropic:claude-sonnet-5` |
| Local Ollama | `AGENT_MODEL=ollama:qwen3:27b` plus `OLLAMA_BASE_URL=http://10.0.0.251:11434/v1` |

The Ollama path needs no API key; the provider substitutes a placeholder. Verify
a local model resolves before you rely on it:

```bash
OLLAMA_BASE_URL=http://10.0.0.251:11434/v1 python -c \
  "from pydantic_ai.models import infer_model; print(infer_model('ollama:qwen3:27b'))"
```

## Tracing

`src/tracing.py` is called once at import. With `LANGFUSE_PUBLIC_KEY` **and**
`LANGFUSE_SECRET_KEY` set it builds the OTLP exporter environment
(`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS` =
`Authorization=Basic <base64 pk:sk>`, `OTEL_EXPORTER_OTLP_PROTOCOL`), installs a
`TracerProvider` with the OTLP HTTP span exporter, and calls
`Agent.instrument_all()` so every Pydantic AI run emits spans.

**Without both keys it is a documented no-op**: no OTEL env is set, no
OpenTelemetry module is imported, no exporter or background thread starts,
`Agent.instrument_all()` is never called, and no network call is made. The agent
runs untraced. This is the expected state on a laptop and in CI, and the smoke
tests assert it.

Endpoint defaults to the self-hosted Langfuse v3 OTLP ingest,
`http://10.0.0.179:3000/api/public/otel` (dh40801); override with
`LANGFUSE_OTLP_ENDPOINT`. The exporter appends `/v1/traces`.

In Doppler the AI Factory keys are `LANGFUSE_AIFACTORY_PUBLIC_KEY` /
`LANGFUSE_AIFACTORY_SECRET_KEY`; map them onto the runtime names when injecting:

```bash
LANGFUSE_PUBLIC_KEY=$(doppler secrets get LANGFUSE_AIFACTORY_PUBLIC_KEY --plain) \
LANGFUSE_SECRET_KEY=$(doppler secrets get LANGFUSE_AIFACTORY_SECRET_KEY --plain) \
python src/agent.py "your topic here"
```

## Registry heartbeat

`AIFactoryRegistry.register()` posts the agent manifest (id, version, model,
whether tracing is on, and the JSON schema of `AgentOutput`) to
`/api/v1/agents/register`; `log_request` / `update_request` bracket each run.
Every call is best-effort — a registry outage degrades observability, never the
run. Default base URL is `http://dhg-registry-api:8000` (container name on
`dhgaifactory35_dhg-network`); from the host set
`AI_FACTORY_REGISTRY_URL=http://10.0.0.251:8011`.

## Surface

Library module plus a CLI — the same surface the previous LangGraph boilerplate
had. It serves no HTTP, so there is no `/metrics` endpoint here. If you wrap the
agent in a FastAPI service, add `prometheus_client` and a `/metrics` route in
that service, the way `services/vs-engine` and `services/session-logger` do.

## Environment

| Variable | Required | Purpose |
|---|---|---|
| `AGENT_MODEL` | no | model string; default `anthropic:claude-opus-5` |
| `ANTHROPIC_API_KEY` | for the default model | provider credential |
| `AI_FACTORY_REGISTRY_URL` | no | registry base URL |
| `AGENT_TIMEOUT_SECONDS` | no | per-run timeout, default 300 |
| `LANGFUSE_PUBLIC_KEY` | no | enables tracing (with the secret key) |
| `LANGFUSE_SECRET_KEY` | no | enables tracing (with the public key) |
| `LANGFUSE_OTLP_ENDPOINT` | no | override the Langfuse OTLP endpoint |
| `LOG_LEVEL` | no | default `INFO` |
