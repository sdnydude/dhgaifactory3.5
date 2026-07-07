# Capture insights to registry

Post insights in real-time when possible. Fire whenever a `★ Insight` block is generated or whenever a non-obvious technical discovery is made during the session.

```bash
~/.claude/scripts/post-insight.sh --stdin <<'MEMREG_JSON'
{"tldr":"<280 char summary>","insight_statement":"<full text>","project_name":"dhg-ai-factory","category":"<category>","source_file":"<file>","tags":["<tag>"],"model_name":"<current session model ID>"}
MEMREG_JSON
```

**Categories:** testing, architecture, security, performance, patterns, debugging, database, frontend, devops, api-design, langgraph, observability, cme

## Do not ask permission

Call this automatically whenever an insight is generated — see [capture-common.md](capture-common.md) for the shared mechanics (automated fire-and-forget, announce-only-on-failure, planning-gate exemption, `model_name`, LAN IP).
