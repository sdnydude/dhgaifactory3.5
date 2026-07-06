# Capture ship sessions to registry

At the end of a `/ship` workflow (Phase 7 or when stopped), post the session summary to the registry.

```bash
~/.claude/scripts/post-ship-session.sh --stdin <<'MEMREG_JSON'
{"project_name":"dhg-ai-factory","feature":"<name>","approach":"<summary>","status":"complete","complexity":"<simple|complex>","tdd":<true|false|null>,"pr_url":"<URL>","branch":"<branch>","completed_at":"<ISO 8601>","commits":["<hash msg>"],"deferred":["<item>"],"decisions":["<item>"],"review":{"agents":[],"critical_found":0,"important_found":0},"verification":{"typecheck":"pass","tests":"<summary>","lint":"clean"},"tags":["<tag>"],"model_name":"<current session model ID>"}
MEMREG_JSON
```

**Required fields:** project_name, feature. All others optional.

## Do not ask permission

Call this automatically at the end of every /ship workflow. The script exits 0 on failure, so it never blocks the session. Announce only on failure: the script prints a failure line ("...dead-lettered...") when the registry is unreachable — repeat that one line to Stephen so he knows the capture is queued, not landed. Success stays silent. Ship-complete reports say "capture queued" on failure — never imply the record landed.
