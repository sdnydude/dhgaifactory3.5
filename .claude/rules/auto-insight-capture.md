# Capture insights to registry

Post insights in real-time when possible. Fire whenever a `★ Insight` block is generated or whenever a non-obvious technical discovery is made during the session.

```bash
~/.claude/scripts/post-insight.sh '{"tldr":"<280 char summary>","insight_statement":"<full text>","project_name":"dhg-ai-factory","category":"<category>","source_file":"<file>","tags":["<tag>"],"model_name":"claude-opus-4-6"}'
```

**Categories:** testing, architecture, security, performance, patterns, debugging, database, frontend, devops, api-design, langgraph, observability, cme

## Do not ask permission

Call this automatically. Do not announce it. The script exits 0 on failure, so it never blocks the session.
