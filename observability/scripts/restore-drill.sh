#!/usr/bin/env bash
# restore-drill.sh — prove a backup restores. For each target it takes the newest
# completed run (manifest.json present), restores it into an EPHEMERAL container
# (no ports, --network none, removed on every exit path) and checks the result
# against the manifest exactly. Never touches a production container.
#
# Usage: restore-drill.sh <target-id> [run-id] | --all
# Cron (Sundays 04:00 ET): doppler run --project dhg-monitoring --config dev -- restore-drill.sh --all
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=backup-lib.sh
source "$SCRIPT_DIR/backup-lib.sh"

log() { printf '%s restore-drill: %s\n' "$(date -u +%FT%TZ)" "$*" >&2; }
[ -n "${BACKUP_GPG_PASSPHRASE:-}" ] || { log "ABORT: BACKUP_GPG_PASSPHRASE not set"; exit 1; }

# ---- drills: <run_dir> ; exit 0 = verified ----

# files/config: every member must be present and countable; the count is the contract.
drill_files() {
  local rundir="$1" want got
  want="$(jq -r '.members' "$rundir/manifest.json")"
  got="$(bl_gpg_decrypt < "$rundir/config.tar.gpg" | tar -t | wc -l)"
  [ "$got" = "$want" ] || { log "config: tar lists $got entries, manifest says $want"; return 1; }
  log "config: $got entries verified"
}

# ---- ephemeral container plumbing ----
DRILL_CONTAINER=""
cleanup() { [ -n "$DRILL_CONTAINER" ] && docker rm -f "$DRILL_CONTAINER" > /dev/null 2>&1 || true; DRILL_CONTAINER=""; }
trap cleanup EXIT INT TERM

# wait_for <seconds> <cmd...>  — poll a command until it succeeds
wait_for() { local n="$1"; shift; local i=0; until "$@" > /dev/null 2>&1; do i=$((i+1)); [ "$i" -ge "$n" ] && return 1; sleep 1; done; }

# pg: fresh server from the manifest's image, roles, one database per dump
# restored from a file copied into the container (pg_restore needs a seekable
# custom-format archive), then the same count query as the backup took.
drill_pg() {
  local rundir="$1" id image db dumps want got f
  id="$(jq -r '.target' "$rundir/manifest.json")"; image="$(jq -r '.image' "$rundir/manifest.json")"
  DRILL_CONTAINER="dhg-restore-drill-$id"
  docker rm -f "$DRILL_CONTAINER" > /dev/null 2>&1 || true
  docker run -d --network none --name "$DRILL_CONTAINER" -e POSTGRES_PASSWORD=drill "$image" > /dev/null
  wait_for 60 docker exec "$DRILL_CONTAINER" pg_isready -U postgres || { log "$id: server never became ready"; return 1; }
  bl_gpg_decrypt < "$rundir/roles.sql.gpg" | docker exec -i "$DRILL_CONTAINER" psql -X -q -U postgres -d postgres > /dev/null 2>&1 || true  # roles may already exist
  docker exec "$DRILL_CONTAINER" mkdir -p /restore      # `docker cp -` refuses a destination that does not exist
  for f in "$rundir"/*.dump.gpg; do
    db="$(basename "$f" .dump.gpg)"
    # decrypt into a tar stream so `docker cp -` can place the file without a host temp file
    bl_gpg_decrypt < "$f" > "$rundir/.drill.$db.dump"
    tar -C "$rundir" -cf - --transform="s|^\.drill\.$db\.dump$|$db.dump|" ".drill.$db.dump" | docker cp - "$DRILL_CONTAINER:/restore"
    rm -f "$rundir/.drill.$db.dump"
    docker exec "$DRILL_CONTAINER" psql -X -q -U postgres -d postgres -c "CREATE DATABASE \"$db\"" > /dev/null
    docker exec "$DRILL_CONTAINER" pg_restore -U postgres -d "$db" "/restore/$db.dump" || { log "$id: pg_restore $db failed"; return 1; }
    # both sides sorted in byte order: jq's sort is codepoint order, and a locale
    # `sort` collates "user_badges" and "users" differently (false mismatch)
    want="$(jq -r --arg db "$db" '.counts[$db] | to_entries | map("\(.key)=\(.value)") | sort | join("\n")' "$rundir/manifest.json")"
    got="$(docker exec "$DRILL_CONTAINER" psql -X -q -At -U postgres -d "$db" -c "$BL_PG_COUNTS_SQL" | LC_ALL=C sort)"
    [ "$got" = "$want" ] || { log "$id/$db: row counts differ from manifest"; printf 'want:\n%s\ngot:\n%s\n' "$want" "$got" >&2; return 1; }
    log "$id/$db: $(wc -l <<<"$got") tables, counts match"
  done
  cleanup
}

# clickhouse: fresh server (default user, no password inside the drill), DDL
# replayed, every Native stream inserted, then the restored row count must
# equal what clickhouse-local counts in the Native file itself (self-describing
# format), which is the only count that survives ReplacingMergeTree's eventual
# dedup on the source side.
drill_clickhouse() {
  local rundir="$1" id image f t db want got
  id="$(jq -r '.target' "$rundir/manifest.json")"; image="$(jq -r '.image' "$rundir/manifest.json")"
  db="$(bl_target_field "$id" extra | cut -d: -f2)"
  DRILL_CONTAINER="dhg-restore-drill-$id"
  docker rm -f "$DRILL_CONTAINER" > /dev/null 2>&1 || true
  docker run -d --network none --name "$DRILL_CONTAINER" "$image" > /dev/null
  wait_for 90 docker exec "$DRILL_CONTAINER" clickhouse-client --query "SELECT 1" || { log "$id: server never became ready"; return 1; }
  bl_gpg_decrypt < "$rundir/ddl.sql.gpg" | sed 's/$/;/' \
    | docker exec -i "$DRILL_CONTAINER" clickhouse-client --multiquery || { log "$id: DDL replay failed"; return 1; }
  docker exec "$DRILL_CONTAINER" mkdir -p /restore      # `docker cp -` refuses a destination that does not exist
  for f in "$rundir"/*.native.gz.gpg; do
    t="$(basename "$f" .native.gz.gpg)"
    bl_gpg_decrypt < "$f" | gunzip > "$rundir/.drill.$t.native"
    if [ -s "$rundir/.drill.$t.native" ]; then
      docker exec -i "$DRILL_CONTAINER" clickhouse-client --query "INSERT INTO $db.$t FORMAT Native" < "$rundir/.drill.$t.native" \
        || { rm -f "$rundir/.drill.$t.native"; log "$id: insert into $t failed"; return 1; }
      tar -C "$rundir" -cf - --transform="s|^\.drill\.$t\.native$|$t.native|" ".drill.$t.native" | docker cp - "$DRILL_CONTAINER:/restore"
      want="$(docker exec "$DRILL_CONTAINER" clickhouse local --query "SELECT count() FROM file('/restore/$t.native', Native)")"
    else
      want=0   # empty table: 0-byte Native stream is legitimate
    fi
    rm -f "$rundir/.drill.$t.native"
    got="$(docker exec "$DRILL_CONTAINER" clickhouse-client --query "SELECT count() FROM $db.$t")"
    [ "$got" = "$want" ] || { log "$id/$t: restored $got rows, file holds $want"; return 1; }
    log "$id/$t: $got rows verified"
  done
  cleanup
}

# minio: the xl tree is untarred into a CREATED (not yet started) container so
# the server boots on the restored data. .minio.sys/config is encrypted with the
# root credential, so the drill reads MINIO_ROOT_USER/PASSWORD from the SOURCE
# container's env and hands them over through a mode-600 env-file that is
# deleted right after `docker create` (never argv, never the shim log).
drill_minio() {
  local rundir="$1" id image ctx container path envfile want got
  id="$(jq -r '.target' "$rundir/manifest.json")"; image="$(jq -r '.image' "$rundir/manifest.json")"
  ctx="$(bl_target_field "$id" ctx)"; container="$(bl_target_field "$id" container)"
  path="$(bl_target_field "$id" extra)"          # /data for Langfuse, /export for plane
  want="$(jq -r '.members' "$rundir/manifest.json")"
  DRILL_CONTAINER="dhg-restore-drill-$id"
  docker rm -f "$DRILL_CONTAINER" > /dev/null 2>&1 || true
  envfile="$(mktemp "$rundir/.drill.XXXXXX.env-file")"; chmod 600 "$envfile"
  if [ "$ctx" = local ]; then docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$container"
  else docker --context "$ctx" inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$container"; fi \
    | sed -n '/^MINIO_ROOT_\(USER\|PASSWORD\)=/p' > "$envfile"
  [ "$(wc -l < "$envfile")" -eq 2 ] || { rm -f "$envfile"; log "$id: could not read MINIO_ROOT_* from $container"; return 1; }
  docker create --network none --name "$DRILL_CONTAINER" --env-file "$envfile" "$image" server "$path" > /dev/null
  rm -f "$envfile"
  # the archive's entries are rooted at the path's basename (docker cp semantics), so untar into its parent
  bl_gpg_decrypt < "$rundir/data.tar.gpg" | docker cp - "$DRILL_CONTAINER:$(dirname "$path")" || { log "$id: docker cp into the drill container failed"; return 1; }
  # equality is measured on the restored tree BEFORE the server starts: MinIO
  # rewrites .minio.sys (tmp, multipart, format) on first boot.
  got="$(docker cp "$DRILL_CONTAINER:$path" - | tar -t | wc -l)"
  [ "$got" = "$want" ] || { log "$id: restored tree has $got entries, manifest says $want"; return 1; }
  docker start "$DRILL_CONTAINER" > /dev/null
  # credentials expand INSIDE the container (sh -c), so they never reach argv here
  wait_for 60 docker exec "$DRILL_CONTAINER" sh -c 'exec mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"' \
    || { log "$id: server never accepted the restored credentials"; return 1; }
  docker exec "$DRILL_CONTAINER" mc ls local/ | sed 's/^/  /' >&2
  log "$id: $got entries verified, server up on the restored tree"
  cleanup
}

# volume: one tar per source container; each must list exactly the member count
# the backup recorded. grafana.db is a live-copied sqlite file, so it is also
# opened in the prebuilt drill image (alpine + sqlite, --network none at build
# time) and must pass PRAGMA integrity_check.
drill_volume() {
  local rundir="$1" id f c want got verdict
  id="$(jq -r '.target' "$rundir/manifest.json")"
  for f in "$rundir"/*.tar.gpg; do
    c="$(basename "$f" .tar.gpg)"
    want="$(jq -r --arg c "$c" '.members[$c]' "$rundir/manifest.json")"
    got="$(bl_gpg_decrypt < "$f" | tar -t | wc -l)"
    [ "$got" = "$want" ] || { log "$id/$c: tar lists $got entries, manifest says $want"; return 1; }
    log "$id/$c: $got entries verified"
    if [ "$c" = dhg-grafana ]; then
      verdict="$(bl_gpg_decrypt < "$f" | tar -xOf - grafana.db \
        | docker run --rm -i dhg-drill-sqlite:3.20 sh -c 'cat > /x.db && sqlite3 /x.db "PRAGMA integrity_check"')"
      [ "$verdict" = ok ] || { log "$id/$c: grafana.db integrity_check: $verdict"; return 1; }
      log "$id/$c: grafana.db integrity_check ok"
    fi
  done
}

# ---- driver ----
drill_target() {
  local id="$1" run="${2:-}" kind rundir
  kind="$(bl_target_field "$id" kind)" || { log "unknown target: $id"; return 2; }
  if [ -n "$run" ]; then rundir="$BACKUP_ROOT/$id/$run"; [ -f "$rundir/manifest.json" ] || { log "$id: run $run has no manifest"; return 1; }
  else rundir="$(bl_latest_run "$id")" || { log "$id: no completed run to drill"; return 1; }
  fi
  log "$id: drilling $(basename "$rundir")"
  if "drill_$kind" "$rundir"; then
    bl_state_set "$id" drill_success "$(date +%s)"; bl_write_textfile
    echo "$id $(basename "$rundir") PASS"
  else
    cleanup          # a failed target must not leave its container for the EXIT trap of a --all run
    echo "$id $(basename "$rundir") FAIL"; return 1
  fi
}

case "${1:-}" in
  "") sed -n '2,8p' "$0" >&2; exit 2 ;;
  --all)
    failed=0
    while IFS='|' read -r id _rest; do drill_target "$id" || failed=$((failed+1)); done < <(bl_targets)
    [ "$failed" -eq 0 ] || { log "$failed target(s) failed"; exit 1; }
    ;;
  *) drill_target "$1" "${2:-}" ;;
esac
