#!/usr/bin/env bash
# Langfuse synthetic round-trip canary.
#
# Why: Langfuse v3 ingestion is asynchronous — the web tier accepts a trace and
# hands it to MinIO/S3, the worker drains it into ClickHouse. If MinIO is down or
# the bucket is missing, the HTTP POST still returns 207 Success and the trace is
# silently dropped. Neither /api/public/health nor a container healthcheck sees
# that. This canary writes a trace and then reads it back, so only a genuine
# end-to-end round-trip refreshes the freshness timestamp. The
# `LangfuseCanaryStale` alert (observability/prometheus/rules.d/dh40801.yml)
# fires when that timestamp stops moving.
#
# Output: Prometheus textfile metrics, collected by the g700data1 node-exporter
# from /mnt/4tb/observability/textfile (its --collector.textfile.directory).
#
# On failure the metrics file is left UNTOUCHED on purpose: the previous
# success timestamp then ages past the alert threshold. Rewriting it with a
# failure marker would hide the outage from a rule that watches age.
#
# Credentials come from Doppler and never touch disk:
#   doppler run --project dhg-monitoring --config dev -- observability/scripts/langfuse-canary.sh
# Required: LANGFUSE_CANARY_PUBLIC_KEY, LANGFUSE_CANARY_SECRET_KEY, LANGFUSE_HOST

set -euo pipefail

TEXTFILE_DIR="${LANGFUSE_CANARY_TEXTFILE_DIR:-/mnt/4tb/observability/textfile}"
OUT="${TEXTFILE_DIR}/langfuse_canary.prom"
POLL_TIMEOUT_SECONDS="${LANGFUSE_CANARY_TIMEOUT:-60}"
TRACE_NAME="canary"

die() { echo "langfuse-canary: $*" >&2; exit 1; }

: "${LANGFUSE_CANARY_PUBLIC_KEY:?not set - run under: doppler run --project dhg-monitoring --config dev --}"
: "${LANGFUSE_CANARY_SECRET_KEY:?not set - run under: doppler run --project dhg-monitoring --config dev --}"
: "${LANGFUSE_HOST:?not set - run under: doppler run --project dhg-monitoring --config dev --}"

AUTH="${LANGFUSE_CANARY_PUBLIC_KEY}:${LANGFUSE_CANARY_SECRET_KEY}"
[ -d "$TEXTFILE_DIR" ] || die "textfile dir $TEXTFILE_DIR does not exist"

# Unique per run so the read-back proves THIS trace made it through, not an old one.
TRACE_ID="canary-$(date -u +%Y%m%dT%H%M%S)-$$-${RANDOM}"
EVENT_ID="ev-${TRACE_ID}"
NOW_ISO="$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)"
START_EPOCH="$(date +%s)"

# ---- 1. write ----
INGEST_BODY=$(TRACE_ID="$TRACE_ID" EVENT_ID="$EVENT_ID" NOW_ISO="$NOW_ISO" TRACE_NAME="$TRACE_NAME" python3 -c '
import json, os
print(json.dumps({"batch": [{
    "id": os.environ["EVENT_ID"],
    "type": "trace-create",
    "timestamp": os.environ["NOW_ISO"],
    "body": {
        "id": os.environ["TRACE_ID"],
        "name": os.environ["TRACE_NAME"],
        "timestamp": os.environ["NOW_ISO"],
        "metadata": {"source": "langfuse-canary.sh", "host": "g700data1"},
    },
}]}))')

INGEST_OUT=$(curl -sS --max-time 20 -u "$AUTH" \
    -H 'Content-Type: application/json' \
    -w '\n%{http_code}' \
    -X POST -d "$INGEST_BODY" \
    "${LANGFUSE_HOST}/api/public/ingestion") || die "ingestion POST failed"

INGEST_CODE="${INGEST_OUT##*$'\n'}"
INGEST_JSON="${INGEST_OUT%$'\n'*}"
case "$INGEST_CODE" in
    200|207) ;;
    *) die "ingestion POST returned HTTP $INGEST_CODE" ;;
esac
# 207 is partial success: a per-event error still means the trace was rejected.
printf '%s' "$INGEST_JSON" | python3 -c '
import json, sys
errors = json.load(sys.stdin).get("errors") or []
if errors:
    sys.exit("ingestion reported %d event error(s)" % len(errors))
' || die "ingestion rejected the canary event"

# ---- 2. read back ----
FOUND=0
while [ "$(( $(date +%s) - START_EPOCH ))" -lt "$POLL_TIMEOUT_SECONDS" ]; do
    sleep 3
    LIST=$(curl -sS --max-time 15 -u "$AUTH" \
        "${LANGFUSE_HOST}/api/public/traces?name=${TRACE_NAME}&limit=1" || true)
    [ -n "$LIST" ] || continue
    if printf '%s' "$LIST" | TRACE_ID="$TRACE_ID" python3 -c '
import json, os, sys
try:
    rows = json.load(sys.stdin).get("data") or []
except json.JSONDecodeError:
    sys.exit(1)
sys.exit(0 if any(r.get("id") == os.environ["TRACE_ID"] for r in rows) else 1)
'; then
        FOUND=1
        break
    fi
done

[ "$FOUND" -eq 1 ] || die "trace $TRACE_ID not readable within ${POLL_TIMEOUT_SECONDS}s - ingestion accepted but never landed"

END_EPOCH="$(date +%s)"
ROUNDTRIP="$(( END_EPOCH - START_EPOCH ))"

# ---- 3. publish (atomic: node-exporter must never read a half-written file) ----
TMP="$(mktemp "${OUT}.XXXXXX")"
trap 'rm -f "$TMP"' EXIT
cat > "$TMP" <<EOF
# HELP langfuse_canary_success_timestamp Unix time of the last Langfuse write-then-read round-trip that completed.
# TYPE langfuse_canary_success_timestamp gauge
langfuse_canary_success_timestamp ${END_EPOCH}
# HELP langfuse_canary_roundtrip_seconds Seconds from posting the canary trace to reading it back.
# TYPE langfuse_canary_roundtrip_seconds gauge
langfuse_canary_roundtrip_seconds ${ROUNDTRIP}
EOF
chmod 0644 "$TMP"
mv -f "$TMP" "$OUT"
trap - EXIT

echo "langfuse-canary: ok, round-trip ${ROUNDTRIP}s -> $OUT"
