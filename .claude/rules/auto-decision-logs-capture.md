# Auto-capture decision logs to registry

Whenever you make or document an **architectural or implementation decision** where:
1. An alternative was explicitly considered and rejected
2. A future session could plausibly make the opposite choice
3. The reasoning is non-obvious from the code alone

Immediately make a Bash call to post it to the registry:

```bash
~/.claude/scripts/post-decision-logs.sh --stdin <<'MEMREG_JSON'
{"title":"<short decision title>","choice":"<what was decided>","alternatives_rejected":"<what was considered and rejected>","rationale":"<why this choice was made>","domain":"<domain>","project_name":"dhg-ai-factory","source_file":"<file being discussed>","tags":["<tag1>","<tag2>"],"model_name":"<current session model ID>"}
MEMREG_JSON
```

## Domain values
Use one of: `registry`, `frontend`, `langgraph`, `cme`, `infra`, `observability`, `auth`, `ops`

## Rules
- Keep title under 280 chars
- Include source_file when the decision relates to a specific file
- Include alternatives_rejected whenever alternatives were discussed
- Include supersedes if this decision replaces a previous one (use the slug)
- Shared mechanics (fire-and-forget, announce-only-on-failure, planning-gate exemption, no quote-escaping, `model_name`, `session_id`, LAN IP, tags): see [capture-common.md](capture-common.md)
