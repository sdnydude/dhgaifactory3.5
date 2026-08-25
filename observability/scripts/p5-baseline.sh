#!/usr/bin/env bash
# P5 T1 — pre-migration baselines + Loki store backup (read-only + backup; deletes nothing).
# Usage: ./p5-baseline.sh   (writes baselines/ next to itself, tar to /mnt/4tb/backups)
set -euo pipefail
LOKI=http://10.0.0.251:3100
AM=http://10.0.0.251:9093
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$DIR/baselines"
mkdir -p "$OUT"
fail() { echo "BASELINE FAIL: $*" >&2; exit 1; }

echo "== 1. Retention floor query (29d, container=dhg-registry-api)"
FLOOR=$(curl -sf --max-time 60 "$LOKI/loki/api/v1/query" \
  --data-urlencode 'query=sum(count_over_time({container="dhg-registry-api"}[29d]))' \
  | python3 -c 'import sys,json; r=json.load(sys.stdin)["data"]["result"]; print(int(float(r[0]["value"][1])) if r else 0)')
[ "$FLOOR" -gt 0 ] || fail "29d floor query returned 0 lines"
echo "floor lines (29d): $FLOOR"
echo "{\"floor_29d_registry_api\": $FLOOR, \"at\": \"$(date -u +%FT%TZ)\"}" > "$OUT/floor-pre.json"

echo "== 2. Label snapshot"
python3 - "$LOKI" "$OUT/labels-pre.json" <<'PY'
import sys, json, urllib.request
loki, out = sys.argv[1], sys.argv[2]
snap = {}
for lbl in ("container", "level", "job", "compose_service", "compose_project"):
    with urllib.request.urlopen(f"{loki}/loki/api/v1/label/{lbl}/values", timeout=30) as r:
        snap[lbl] = sorted(json.load(r).get("data") or [])
json.dump(snap, open(out, "w"), indent=1)
print({k: len(v) for k, v in snap.items()})
PY

echo "== 3. Alertmanager v2 silence round-trip"
NOW=$(date -u +%FT%TZ); END=$(date -u -d '+2 minutes' +%FT%TZ)
SIL=$(curl -sf -X POST "$AM/api/v2/silences" -H 'Content-Type: application/json' -d "{
  \"matchers\": [{\"name\": \"alertname\", \"value\": \"P5BaselineProbe\", \"isRegex\": false, \"isEqual\": true}],
  \"startsAt\": \"$NOW\", \"endsAt\": \"$END\",
  \"createdBy\": \"p5-baseline\", \"comment\": \"T1 silence round-trip probe\"}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["silenceID"])')
[ -n "$SIL" ] || fail "silence create returned no id"
curl -sf -X DELETE "$AM/api/v2/silence/$SIL" || fail "silence expire failed"
echo "silence round-trip OK ($SIL)"

echo "== 4. Loki store backup (volume mounted read-only)"
TAR="loki-data-pre-p5-$(date +%F).tar.gz"
docker run --rm -v dhgaifactory35_loki_data:/loki:ro -v /mnt/4tb/backups:/backup alpine \
  tar czf "/backup/$TAR" -C / loki
SIZE=$(stat -c%s "/mnt/4tb/backups/$TAR")
[ "$SIZE" -gt 100000000 ] || fail "backup smaller than 100MB ($SIZE bytes)"
echo "backup OK: /mnt/4tb/backups/$TAR ($SIZE bytes)"
echo "== T1 baselines complete"
