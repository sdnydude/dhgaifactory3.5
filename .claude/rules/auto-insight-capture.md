# Capture insights to registry

Post insights in real-time when possible. Fire whenever a `★ Insight` block is generated or whenever a non-obvious technical discovery is made during the session.

```bash
~/.claude/scripts/post-insight.sh --stdin <<'MEMREG_JSON'
{"tldr":"<280 char summary>","insight_statement":"<full text>","project_name":"dhg-ai-factory","category":"<category>","source_file":"<file>","tags":["<tag>"],"model_name":"<current session model ID>"}
MEMREG_JSON
```

**Categories:** testing, architecture, security, performance, patterns, debugging, database, frontend, devops, api-design, langgraph, observability, cme

## Do not ask permission

Call this automatically. The script exits 0 on failure, so it never blocks the session. Announce only on failure: the script prints a failure line ("...dead-lettered...") when the registry is unreachable — repeat that one line to Stephen so he knows the capture is queued, not landed. Success stays silent.
