#!/usr/bin/env bash
# One-shot edit of docker-compose.override.yml for the two Wave 1 leftovers
# (plan .claude/plans/outstanding-2026-09-13.md tasks 5.1 and 5.2):
#   5.1 drop LANGGRAPH_API_URL / LANGCHAIN_API_KEY from every service (LangGraph
#       is gone; only registry-api still carried them as of 2026-09-13)
#   5.2 add --no-collector.thermal_zone to node-exporter's command list
# The override is permission-denied to Claude, so this script is run by the
# operator. It backs the file up, validates the merged config, shows a masked
# before/after diff of the affected keys, and only then recreates the two
# services.
set -euo pipefail
cd "$(dirname "$0")/../.."

F=docker-compose.override.yml
[ -f "$F" ] || { echo "no $F" >&2; exit 1; }
BAK="$F.bak.$(date -u +%Y%m%dT%H%M%SZ)"
cp -p "$F" "$BAK"
echo "backup: $BAK"

masked_keys() {   # service + key names only, never values
  docker compose config 2>/dev/null \
    | awk '/^  [a-z-]+:$/{svc=$1} /^\s+(LANGGRAPH_API_URL|LANGCHAIN_API_KEY):/{print svc, $1} /^\s+- --no-collector.thermal_zone/{print svc, $2}'
}
before="$(masked_keys)"

# 5.1 — both `- KEY=value` (list) and `KEY: value` (map) forms
sed -i -E '/^[[:space:]]*-?[[:space:]]*(LANGGRAPH_API_URL|LANGCHAIN_API_KEY)[=:]/d' "$F"
# 5.2 — duplicate the textfile flag line (keeps indentation and "- " prefix) and
#       turn the copy into the new flag; idempotent
if ! grep -q -- '--no-collector.thermal_zone' "$F"; then
  sed -i -E '/--collector\.textfile\.directory=/{p;s#(['"'"'"]?)--collector\.textfile\.directory=[^'"'"'"]*(['"'"'"]?)#\1--no-collector.thermal_zone\2#}' "$F"
fi

if ! docker compose config --quiet; then
  echo "merged config invalid — restoring $BAK" >&2
  cp -p "$BAK" "$F"; exit 1
fi
after="$(masked_keys)"
echo "--- before"; echo "${before:-<none>}"
echo "--- after";  echo "${after:-<none>}"
echo "$after" | grep -q 'LANG' && { echo "LangGraph keys still present — restoring $BAK" >&2; cp -p "$BAK" "$F"; exit 1; }
echo "$after" | grep -q 'no-collector.thermal_zone' || { echo "thermal_zone flag missing — restoring $BAK" >&2; cp -p "$BAK" "$F"; exit 1; }

docker compose up -d --no-deps registry-api node-exporter
sleep 15
docker inspect dhg-registry-api --format 'registry-api: {{.State.Health.Status}}'
docker inspect dhg-node-exporter --format 'node-exporter: {{.State.Status}}'
echo "thermal_zone errors in last 60s: $(docker logs --since 60s dhg-node-exporter 2>&1 | grep -c thermal_zone || true)"
