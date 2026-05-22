# Capture ship sessions to registry

At the end of a `/ship` workflow (Phase 7 or when stopped), post the session summary to the registry.

```bash
~/.claude/scripts/post-ship-session.sh '{"project_name":"dhg-ai-factory","feature":"<name>","approach":"<summary>","status":"complete","complexity":"<simple|complex>","tdd":<true|false|null>,"pr_url":"<URL>","branch":"<branch>","completed_at":"<ISO 8601>","commits":["<hash msg>"],"deferred":["<item>"],"decisions":["<item>"],"review":{"agents":[],"critical_found":0,"important_found":0},"verification":{"typecheck":"pass","tests":"<summary>","lint":"clean"},"tags":["<tag>"],"model_name":"claude-opus-4-6"}'
```

**Required fields:** project_name, feature. All others optional.

## Do not ask permission

Call this automatically at the end of every /ship workflow. The script exits 0 on failure, so it never blocks the session.
