#!/usr/bin/env bash
# Grant the built-in Viewer (View) and Editor (Edit) roles on every Grafana folder.
#
# WHY THIS EXISTS
# Grafana 10.2 OSS applies default folder permissions (Admin to the creator,
# Edit to the built-in Editor role, View to the built-in Viewer role) only when
# a folder is created through the UI or the folder API. A folder created by the
# *dashboard file provisioner* is created under a background identity and gets
# no managed permissions at all. Because a Viewer's dashboard access in Grafana
# is entirely folder-scoped — the OSS basic Viewer role carries datasources:read
# but no global dashboards:read — every provisioned folder is invisible to every
# non-Admin identity, including the dhg-verify service account, until a Viewer
# grant is added. File-based provisioning of folder permissions (the
# `apiVersion: 2` access-control provisioning files) is Grafana Enterprise only,
# so this script is the OSS equivalent.
#
# WHEN TO RUN IT
# After `docker compose up -d grafana` (and after any Grafana restart that adds
# a new dashboard provider folder). It is idempotent: existing user/team grants
# are preserved and re-posted unchanged.
#
# Usage: grant-folder-viewer.sh [--dry-run]
# Env:   GRAFANA_URL       (default http://10.0.0.251:3001)
#        GF_ADMIN_USER     (default: read from `docker inspect dhg-grafana`)
#        GF_ADMIN_PASSWORD (default: Doppler dhg-monitoring/dev GF_SECURITY_ADMIN_PASSWORD)
set -euo pipefail

GRAFANA_URL="${GRAFANA_URL:-http://10.0.0.251:3001}"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

if [ -z "${GF_ADMIN_USER:-}" ]; then
  GF_ADMIN_USER="$(docker inspect dhg-grafana \
    --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null \
    | sed -n 's/^GF_SECURITY_ADMIN_USER=//p')"
fi
GF_ADMIN_USER="${GF_ADMIN_USER:-admin}"

if [ -z "${GF_ADMIN_PASSWORD:-}" ]; then
  GF_ADMIN_PASSWORD="$(doppler secrets get GF_SECURITY_ADMIN_PASSWORD \
    --project dhg-monitoring --config dev --plain 2>/dev/null)" || true
fi
[ -n "${GF_ADMIN_PASSWORD:-}" ] || {
  echo "grant-folder-viewer: no admin password (set GF_ADMIN_PASSWORD or log in to Doppler)" >&2
  exit 2
}

AUTH="$GF_ADMIN_USER:$GF_ADMIN_PASSWORD"
CODE="$(curl -sS -o /dev/null -w '%{http_code}' -u "$AUTH" "$GRAFANA_URL/api/org")"
[ "$CODE" = "200" ] || { echo "grant-folder-viewer: admin auth failed (HTTP $CODE)" >&2; exit 2; }

FOLDERS="$(curl -sS -u "$AUTH" "$GRAFANA_URL/api/folders?limit=1000" \
  | python3 -c 'import sys,json; [print(f["uid"], f["title"], sep="\t") for f in json.load(sys.stdin)]')"
[ -n "$FOLDERS" ] || { echo "grant-folder-viewer: no folders returned"; exit 0; }

RC=0
while IFS=$'\t' read -r UID_ TITLE; do
  [ -n "$UID_" ] || continue
  CUR="$(curl -sS -u "$AUTH" "$GRAFANA_URL/api/folders/$UID_/permissions")"
  # Rebuild the ACL: keep every non-inherited entry as-is, then force the
  # built-in Viewer to View (1) and Editor to Edit (2). 4 = Admin.
  BODY="$(UID_="$UID_" python3 -c '
import json, sys
cur = json.load(sys.stdin)
items, seen = [], set()
for p in cur:
    if p.get("inherited"):
        continue
    if p.get("userId"):
        items.append({"userId": p["userId"], "permission": p["permission"]})
    elif p.get("teamId"):
        items.append({"teamId": p["teamId"], "permission": p["permission"]})
    elif p.get("role"):
        seen.add(p["role"])
        items.append({"role": p["role"], "permission": p["permission"]})
for role, perm in (("Viewer", 1), ("Editor", 2)):
    if role not in seen:
        items.append({"role": role, "permission": perm})
print(json.dumps({"items": items, "_missing": sorted({"Viewer","Editor"} - seen)}))
' <<<"$CUR")"
  MISSING="$(python3 -c 'import json,sys; print(",".join(json.load(sys.stdin)["_missing"]) or "-")' <<<"$BODY")"
  if [ "$DRY_RUN" = "1" ]; then
    echo "$UID_ ($TITLE): would add [$MISSING]"
    continue
  fi
  if [ "$MISSING" = "-" ]; then
    echo "$UID_ ($TITLE): Viewer/Editor already granted, unchanged"
    continue
  fi
  PAYLOAD="$(python3 -c 'import json,sys; d=json.load(sys.stdin); d.pop("_missing"); print(json.dumps(d))' <<<"$BODY")"
  HTTP="$(curl -sS -o /dev/null -w '%{http_code}' -u "$AUTH" -X POST \
    -H 'Content-Type: application/json' -d "$PAYLOAD" \
    "$GRAFANA_URL/api/folders/$UID_/permissions")"
  if [ "$HTTP" = "200" ]; then
    echo "$UID_ ($TITLE): granted [$MISSING] HTTP 200"
  else
    echo "$UID_ ($TITLE): FAILED HTTP $HTTP" >&2
    RC=1
  fi
done <<<"$FOLDERS"
exit $RC
