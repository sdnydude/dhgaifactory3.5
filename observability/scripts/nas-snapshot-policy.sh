#!/usr/bin/env bash
# Snapshot policy for the NAS mirror share (plan .claude/plans/outstanding-2026-09-13.md, 4.1).
# Sets, on the Synology DS1618+ (DSM 7.1) share aifactory-backups:
#   - Snapshot Replication schedule: daily at 04:30 (after the 03:30 ET backup + mirror)
#   - Retention: keep the latest 14 snapshots (RTT_DEL_OLD = 20, recently = 14)
# and reads both back. Idempotent. Field names come from the Snapshot Replication
# UI (disaster_recovery.js): SYNO.Core.Share.Snapshot set_schedule/get_schedule v1
# and SYNO.DisasterRecovery.Retention set/get v1 with type "Share".
#
# Run under Doppler so the DSM credentials never touch the command line:
#   doppler run --project dhg-monitoring --config dev -- observability/scripts/nas-snapshot-policy.sh
set -euo pipefail

: "${SYNOLOGY_HOST:=10.0.0.250}"
: "${SYNOLOGY_OPS_USER:?}" "${SYNOLOGY_OPS_PASSWORD:?}"
SHARE="${1:-aifactory-backups}"
HOUR="${SNAP_HOUR:-4}"; MIN="${SNAP_MIN:-30}"; KEEP="${SNAP_KEEP:-14}"
H="https://$SYNOLOGY_HOST:5001/webapi"

api() {   # api <api> <version> <method> [--data-urlencode k=v ...]
  local a=$1 v=$2 m=$3; shift 3
  curl -sk --fail-with-body "$H/entry.cgi" --data-urlencode "api=$a" --data-urlencode "version=$v" \
       --data-urlencode "method=$m" --data-urlencode "_sid=$SID" "$@"
}

SID=$(curl -sk "$H/auth.cgi" --data-urlencode api=SYNO.API.Auth --data-urlencode version=7 \
      --data-urlencode method=login --data-urlencode "account=$SYNOLOGY_OPS_USER" \
      --data-urlencode "passwd=$SYNOLOGY_OPS_PASSWORD" --data-urlencode format=sid | jq -er .data.sid)
trap 'curl -sk "$H/auth.cgi" --data-urlencode api=SYNO.API.Auth --data-urlencode version=7 --data-urlencode method=logout --data-urlencode "_sid=$SID" >/dev/null' EXIT

today=$(date +%Y/%-m/%-d)
sched=$(jq -nc --arg d "$today" --argjson h "$HOUR" --argjson m "$MIN" \
  '{date:$d,date_type:0,hour:$h,min:$m,repeat:0,repeat_hour:0,repeat_min:0,last_work_hour:0,week_name:"0,1,2,3,4,5,6"}')

echo "set_schedule ($SHARE daily $HOUR:$(printf %02d "$MIN")):"
api SYNO.Core.Share.Snapshot 1 set_schedule --data-urlencode "name=$SHARE" \
    --data-urlencode enable_snapshot_schedule=true --data-urlencode "schedule=$sched" \
    --data-urlencode task_id=-1 | jq -c .
echo "get_schedule:"
api SYNO.Core.Share.Snapshot 1 get_schedule --data-urlencode "name=$SHARE" \
  | jq -c '{enabled:.data.enable_snapshot_schedule, next:.data.schedule.next_trigger_time, hour:.data.schedule.hour, min:.data.schedule.min, task_id:.data.task_id}'

echo "retention set (keep latest $KEEP):"
api SYNO.DisasterRecovery.Retention 1 set --data-urlencode type=Share --data-urlencode "name=$SHARE" \
    --data-urlencode policyType=20 --data-urlencode "recently=$KEEP" --data-urlencode retainDay=7 \
    --data-urlencode advRetainDay=1 --data-urlencode advHourly=24 --data-urlencode advDaily=7 \
    --data-urlencode advWeekly=2 --data-urlencode advMonthly=1 --data-urlencode advYearly=1 \
    --data-urlencode advMinimum=5 --data-urlencode advPolicyType=127 --data-urlencode tid=-1 | jq -c .
echo "retention get:"
api SYNO.DisasterRecovery.Retention 1 get --data-urlencode type=Share --data-urlencode "name=$SHARE" \
  | jq -c '{policyType:.data.policyType, keep_latest:.data.recently, retainDay:.data.retainDay}'
