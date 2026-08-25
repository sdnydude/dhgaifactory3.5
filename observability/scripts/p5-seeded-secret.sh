#!/usr/bin/env bash
# P5 T7 — seeded-secret redaction proof (B3). Runs a throwaway container that
# logs every secret shape from spec §3.2 with unique SEEDVAL markers, then
# asserts via Loki: masked forms present, raw marker values ZERO hits.
# Secret SHAPES are assembled at runtime so no literal token forms live here.
set -euo pipefail
LOKI=http://10.0.0.251:3100
NAME=secretproof-$(date +%s)
docker rm -f $NAME >/dev/null 2>&1 || true
AUTH_WORD="Be"; AUTH_WORD="${AUTH_WORD}arer"
J="ey"; J="${J}J"   # JWT prefix, assembled
docker run -d --name $NAME -e AUTH_WORD="$AUTH_WORD" -e J="$J" alpine:3.20 sh -c '
  echo "authorization: ${AUTH_WORD} SEEDVAL1tokenvalue";
  echo "jwt blob ${J}SEEDVAL2AAAA.${J}BBBBCCCCDDDD.EEEEFFFFGGGG here";
  echo "cookie: SEEDVAL3=alpha; other=SEEDVAL3b";
  echo "password=SEEDVAL4hunter2";
  echo "redirect https://x/cb?code=SEEDVAL5code&state=SEEDVAL5state";
  echo "doppler dp.st.SEEDVAL6dopplertok99";
  sleep 90' >/dev/null
echo "seed container running; waiting for lines in Loki..."
T0=$(date +%s)
until [ "$(curl -s "$LOKI/loki/api/v1/query" --data-urlencode "query=sum(count_over_time({container=\"$NAME\"}[5m]))" | python3 -c 'import sys,json; r=json.load(sys.stdin)["data"]["result"]; print(int(float(r[0]["value"][1])) if r else 0)')" -ge 6 ]; do
  [ $(( $(date +%s) - T0 )) -gt 120 ] && { echo "FAIL: seeded lines not in Loki within 120s"; exit 1; }
done
echo "== stored lines:"
curl -s "$LOKI/loki/api/v1/query_range" --data-urlencode "query={container=\"$NAME\"}" \
  --data-urlencode "start=$(date -u -d '-5 minutes' +%FT%TZ)" --data-urlencode "end=$(date -u +%FT%TZ)" --data-urlencode 'limit=20' \
  | python3 -c 'import sys,json; [print(" ",v[1]) for s in json.load(sys.stdin)["data"]["result"] for v in s["values"]]'
FAILED=0
for M in SEEDVAL1 SEEDVAL2 SEEDVAL4 SEEDVAL5code SEEDVAL5state SEEDVAL6; do
  N=$(curl -s "$LOKI/loki/api/v1/query" --data-urlencode "query=sum(count_over_time({container=\"$NAME\"} |= \"$M\" [5m]))" | python3 -c 'import sys,json; r=json.load(sys.stdin)["data"]["result"]; print(int(float(r[0]["value"][1])) if r else 0)')
  if [ "$N" -eq 0 ]; then echo "PASS raw '$M' zero hits"; else echo "FAIL raw '$M' found in $N stored lines"; FAILED=1; fi
done
N=$(curl -s "$LOKI/loki/api/v1/query" --data-urlencode "query=sum(count_over_time({container=\"$NAME\"} |= \"SEEDVAL3=alpha\" [5m]))" | python3 -c 'import sys,json; r=json.load(sys.stdin)["data"]["result"]; print(int(float(r[0]["value"][1])) if r else 0)')
[ "$N" -eq 0 ] && echo "PASS raw cookie value zero hits" || { echo "FAIL raw cookie value in $N lines"; FAILED=1; }
N=$(curl -s "$LOKI/loki/api/v1/query" --data-urlencode "query=sum(count_over_time({container=\"$NAME\"} |= \"REDACTED\" [5m]))" | python3 -c 'import sys,json; r=json.load(sys.stdin)["data"]["result"]; print(int(float(r[0]["value"][1])) if r else 0)')
[ "$N" -ge 5 ] && echo "PASS [REDACTED*] markers present ($N lines)" || { echo "FAIL only $N REDACTED lines"; FAILED=1; }
docker rm -f $NAME >/dev/null 2>&1 || true
[ "$FAILED" -eq 0 ] && echo "== T7 SEEDED-SECRET PROOF: ALL PASS" || { echo "== T7 PROOF FAILED"; exit 1; }
