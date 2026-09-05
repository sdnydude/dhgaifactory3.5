#!/usr/bin/env bash
# Verify a provisioned Grafana dashboard: replay every panel query through
# /api/ds/query, then render the board to PNG.
# Usage: verify-dashboard.sh <uid> [--out DIR]
# Exit 0 only when every non-row Prometheus/Loki/Postgres panel answered without
# error and returned at least one series (or its panel id is listed in
# observability/verify/allow-empty/<uid>.txt).
#
# Replay window: Prometheus and Loki panels are replayed over now-1h, which is
# ample for scraped metrics. Postgres panels are replayed over the dashboard's
# own time.from instead, because their $__timeFilter() is expanded server-side
# against that window and registry capture rows are sparse — a now-1h replay of
# a 30-day board would report every SQL panel empty and be wrong about it.
set -uo pipefail
GRAFANA_URL="${GRAFANA_URL:-http://10.0.0.251:3001}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="$REPO_ROOT/observability/verify"
UID_ARG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT_DIR="$2"; shift 2 ;;
    *) UID_ARG="$1"; shift ;;
  esac
done
[ -n "$UID_ARG" ] || { echo "usage: $(basename "$0") <uid> [--out DIR]" >&2; exit 2; }
if [ -z "${GRAFANA_SA_TOKEN:-}" ]; then
  GRAFANA_SA_TOKEN="$(doppler secrets get GRAFANA_SA_TOKEN \
    --project dhg-monitoring --config dev --plain 2>/dev/null)" || true
fi
[ -n "${GRAFANA_SA_TOKEN:-}" ] || { echo "GRAFANA_SA_TOKEN unset and not readable from Doppler" >&2; exit 2; }
export GRAFANA_SA_TOKEN GRAFANA_URL
mkdir -p "$OUT_DIR"
ALLOW_FILE="$REPO_ROOT/observability/verify/allow-empty/$UID_ARG.txt"
[ -f "$ALLOW_FILE" ] || ALLOW_FILE=""
DASH_JSON="$(mktemp)"; trap 'rm -f "$DASH_JSON"' EXIT
HTTP="$(curl -sS -H "Authorization: Bearer $GRAFANA_SA_TOKEN" \
  -o "$DASH_JSON" -w '%{http_code}' "$GRAFANA_URL/api/dashboards/uid/$UID_ARG")"
[ "$HTTP" = "200" ] || { echo "$UID_ARG: FAIL fetch /api/dashboards/uid/$UID_ARG -> HTTP $HTTP"; exit 1; }

UID_ARG="$UID_ARG" ALLOW_FILE="$ALLOW_FILE" DASH_JSON="$DASH_JSON" python3 - <<'PY'
import json, os, re, sys, time, urllib.request, urllib.error

url, tok = os.environ["GRAFANA_URL"], os.environ["GRAFANA_SA_TOKEN"]
uid, allow_file = os.environ["UID_ARG"], os.environ["ALLOW_FILE"]
dash = json.load(open(os.environ["DASH_JSON"]))["dashboard"]

allow = set()
if allow_file:
    for line in open(allow_file):
        line = line.split("#")[0].strip()
        if line.isdigit():
            allow.add(int(line))
subs = {}
for v in dash.get("templating", {}).get("list", []):
    cur = (v.get("current") or {}).get("value")
    if isinstance(cur, list):
        cur = "|".join(str(c) for c in cur)
    if cur in (None, "$__all", "All"):
        cur = ".*"
    subs[v["name"]] = str(cur)

def interpolate(s):
    for name, val in subs.items():
        for form in ("${%s}" % name, "[[%s]]" % name, "$" + name):
            s = s.replace(form, val)
    return s
def flatten(panels):
    for p in panels:
        if p.get("type") == "row":
            yield from flatten(p.get("panels") or [])
        else:
            yield p
now = int(time.time() * 1000)
frm = now - 3600 * 1000

_UNIT_MS = {"s": 1000, "m": 60000, "h": 3600000, "d": 86400000,
            "w": 604800000, "M": 2592000000, "y": 31536000000}

def relative_ms(expr, default_ms):
    """'now-30d' -> 2592000000. Anything else (absolute epochs, odd syntax)
    falls back to default_ms so an unparseable range never silently passes."""
    m = re.match(r"^now-(\d+)([smhdwMy])$", str(expr or ""))
    return int(m.group(1)) * _UNIT_MS[m.group(2)] if m else default_ms

# Dashboard's own window, used for SQL panels only.
dash_frm = now - relative_ms((dash.get("time") or {}).get("from"), 3600 * 1000)

def post_query(q, q_frm=None):
    body = json.dumps({"from": str(q_frm if q_frm is not None else frm),
                       "to": str(now), "queries": [q]}).encode()
    req = urllib.request.Request(url + "/api/ds/query", data=body, method="POST",
                                 headers={"Authorization": "Bearer " + tok,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw or b"{}")
        except ValueError:
            return e.code, {"message": raw.decode("utf-8", "replace")[:200]}
    except Exception as e:                                     # network/timeout
        return 0, {"message": type(e).__name__ + ": " + str(e)[:160]}
checked = failed = 0
for panel in flatten(dash.get("panels") or []):
    pds = panel.get("datasource") or {}
    targets = [t for t in (panel.get("targets") or []) if not t.get("hide")]
    queries = []
    for i, t in enumerate(targets):
        ds = t.get("datasource") or pds
        if not isinstance(ds, dict) or ds.get("type") not in ("prometheus", "loki", "postgres"):
            continue
        if str(ds.get("uid", "")).startswith("$"):
            ds = {"type": ds["type"], "uid": subs.get(ds["uid"].strip("${}"), ds["uid"])}
        q = {k: v for k, v in t.items() if k not in ("datasource", "hide")}
        q["datasource"] = {"type": ds["type"], "uid": ds["uid"]}
        q["refId"] = t.get("refId") or chr(65 + i)
        q["intervalMs"] = 60000
        q["maxDataPoints"] = 200
        if ds["type"] == "loki":
            q.setdefault("queryType", "range")
        if ds["type"] == "postgres":
            # The SQL datasource needs the raw statement and an explicit result
            # format; without rawQuery it falls back to the visual builder and
            # returns nothing.
            q["rawQuery"] = True
            q.setdefault("format", "table")
        for key in ("expr", "query", "rawSql"):
            if isinstance(q.get(key), str):
                q[key] = interpolate(q[key])
        queries.append(q)
    if not queries:
        continue
    checked += 1
    pid, title = panel.get("id"), (panel.get("title") or "").strip() or "(untitled)"
    series, errs, codes = 0, [], []
    for q in queries:
        q_frm = dash_frm if q["datasource"]["type"] == "postgres" else frm
        code, resp = post_query(q, q_frm)
        codes.append(str(code))
        res = (resp.get("results") or {}).get(q["refId"], {})
        err = res.get("error") or resp.get("message")
        if err or code >= 400:
            errs.append(str(err or "HTTP %s" % code)[:160])
            continue
        for f in res.get("frames") or []:
            vals = (f.get("data") or {}).get("values") or []
            if vals and len(vals[0]) > 0:
                series += 1
    if errs:
        failed += 1
        print("panel %-4s %-42.42s http=%s ERROR %s" % (pid, title, ",".join(codes), errs[0]))
    elif series == 0 and pid not in allow:
        failed += 1
        print("panel %-4s %-42.42s http=%s series=0 EMPTY" % (pid, title, ",".join(codes)))
    else:
        note = " (allowed empty)" if series == 0 else ""
        print("panel %-4s %-42.42s http=%s series=%d%s" % (pid, title, ",".join(codes), series, note))

if checked == 0:
    print("no Prometheus/Loki/Postgres panel to replay — nothing was verified")
print("PANELS_CHECKED=%d PANELS_FAILED=%d" % (checked, failed))
sys.exit(1 if failed or checked == 0 else 0)
PY
QUERY_RC=$?
PNG="$OUT_DIR/$UID_ARG.png"
RHTTP="$(curl -sS -H "Authorization: Bearer $GRAFANA_SA_TOKEN" -o "$PNG" -w '%{http_code}' \
  "$GRAFANA_URL/render/d/$UID_ARG?width=1600&height=1200&kiosk")"
RSIZE=$(stat -c %s "$PNG" 2>/dev/null || echo 0)
RENDER_RC=0
if [ "$RHTTP" != "200" ] || [ "$RSIZE" -lt 20480 ]; then RENDER_RC=1; fi
STATUS=OK; [ $QUERY_RC -eq 0 ] && [ $RENDER_RC -eq 0 ] || STATUS=FAIL
echo "$UID_ARG: $STATUS queries_rc=$QUERY_RC render_http=$RHTTP render_bytes=$RSIZE png=$PNG"
[ "$STATUS" = "OK" ] || exit 1
