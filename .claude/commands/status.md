---
description: DHG AI Factory compact health status report across Docker stack, LangGraph, Registry API, observability, git, and CodeGraph index.
---

Run a DHG AI Factory health status report. Your job is to execute a battery of health checks in parallel, then print a compact status table. Do not narrate. Do not explain the checks. Run them and print the result.

## Checks to run

Execute all of these in a single Bash call where possible (chained with `;` not `&&` so one failure does not abort the rest). Use short timeouts — a dead service must not hang the whole report. Every HTTP check should use `curl -s -m 3` (3 second max).

1. **Main Docker stack** — `docker compose ps --format json 2>/dev/null | jq -s 'length as $total | map(select(.State == "running")) | length as $running | "\($running)/\($total)"'` (running vs total containers in the main `dhgaifactory3.5` compose project).
2. **LangGraph dev server** — `curl -s -m 3 -o /dev/null -w "%{http_code}" http://localhost:2026/ok`. Expect `200`.
3. **Registry API** — `curl -s -m 3 http://localhost:8011/healthz`. Expect JSON with `"status":"ok"` or similar.
4. **Frontend (Next.js)** — `curl -s -m 3 -o /dev/null -w "%{http_code}" http://localhost:3000`. Expect `200`.
5. **Prometheus** — `curl -s -m 3 http://localhost:9090/-/healthy` (expect `Prometheus Server is Healthy`) AND `curl -s -m 3 http://localhost:9090/api/v1/targets | jq '.data.activeTargets | [.[] | {job: .labels.job, health}] | group_by(.health) | map({(.[0].health): length}) | add'` (target health counts).
6. **Grafana** — `curl -s -m 3 http://localhost:3001/api/health | jq -r '.database'`. Expect `ok`.
7. **Loki** — `curl -s -m 3 -o /dev/null -w "%{http_code}" http://localhost:3100/ready`.
8. **Tempo** — `curl -s -m 3 -o /dev/null -w "%{http_code}" http://localhost:3200/ready`.
9. **Alertmanager health** — `curl -s -m 3 -o /dev/null -w "%{http_code}" http://localhost:9093/-/healthy`.
10. **Active alerts** — `curl -s -m 3 http://localhost:9093/api/v2/alerts | jq 'length'`. Report the count; promote to WARN if >0.
11. **Git state** — `git status --short | wc -l` (modified file count), `git rev-parse --abbrev-ref HEAD` (current branch), `git log --oneline -1` (last commit).
12. **CodeGraph index** — `codegraph status 2>/dev/null | grep -E "files|nodes|edges"` (report file/node/edge counts if available; mark WARN if command errors).

## Output format

Use this exact structure. Do NOT use emojis. Use plain text markers.

```
DHG Status — <UTC timestamp, ISO 8601>
────────────────────────────────────────────────────────────
 <status>  <service>              <detail>
 ...
────────────────────────────────────────────────────────────
 Summary: <green_count>/<total> green, <warn_count> warnings, <fail_count> failing
```

Status markers: `[ok]`, `[WARN]`, `[FAIL]` (left-aligned in brackets). Service name column should be left-padded to consistent width. Detail column is free-form but one line each.

**Ordering rule:** Any `[FAIL]` rows come FIRST, then `[WARN]`, then `[ok]`. Something broken should never be buried below ten green rows.

**Classification rules:**
- `[ok]` — check returned expected value (HTTP 200, healthy response, containers all running, git clean or only expected drift)
- `[WARN]` — check returned degraded-but-not-broken state (e.g. `N/N-1` containers running, git has uncommitted changes, active alerts > 0, CodeGraph status unavailable but index exists)
- `[FAIL]` — check errored, timed out, or returned an unhealthy/non-200 response

## Error handling

If `jq` is missing on the system, fall back to raw curl output and parse by eye. If `docker compose` is missing or not in the repo root, mark row 1 as `[FAIL]` with the error. If a port check times out, mark as `[FAIL]` with `timeout` as the detail. Never abort the entire report because one check failed — continue to the next check and report each independently.

## Do not

- Do not narrate what you are about to do. Run the checks and print the table.
- Do not explain healthy services in detail — `[ok]` + one-line detail is enough.
- Do not suggest fixes in the status report itself. If the user wants remediation, they will ask in a follow-up.
- Do not use emojis.
- Do not print raw command output. Format everything through the table.
