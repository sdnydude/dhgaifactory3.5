#!/usr/bin/env bash
# backup-all.sh — nightly encrypted backups of every DHG AI Factory data store,
# mirrored to the Synology NAS. Cron on g700data1 (swebber64), 03:30 ET:
#   doppler run --project dhg-monitoring --config dev -- observability/scripts/backup-all.sh
#
# Usage: backup-all.sh [--all | --target <id>] [--dry-run] [--no-offsite]
#
# Layout: $BACKUP_ROOT/<target>/<UTC-run>/{*.gpg,manifest.json}; manifest is
# written last and is the commit marker. Every archive is gpg AES256 with
# BACKUP_GPG_PASSPHRASE (Doppler). Prometheus textfile is rewritten after every
# target. See docs-site/projects/dhg-ai-factory/backups.md.
set -euo pipefail
umask 077   # run dirs and archives are owner-only; the NAS mirror inherits it

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=backup-lib.sh
source "$SCRIPT_DIR/backup-lib.sh"

NAS_DEST="aifactory-backup@10.0.0.250::aifactory-backups/"

# ---- single instance (cron + a manual run must never overlap) ----
BACKUP_LOCK="${BACKUP_LOCK:-/run/user/$(id -u)/backup-all.lock}"
exec 8>"$BACKUP_LOCK"
if ! flock -n 8; then
  echo "backup-all: already running (lock $BACKUP_LOCK held) - exiting 75" >&2
  exit 75
fi

MODE=all; ONLY=""; DRY_RUN=0; OFFSITE=1
while [ $# -gt 0 ]; do
  case "$1" in
    --all) MODE=all ;;
    --target) MODE=one; ONLY="${2:-}"; [ -n "$ONLY" ] || { echo "backup-all: --target needs an id" >&2; exit 2; }; shift ;;
    --dry-run) DRY_RUN=1 ;;
    --no-offsite) OFFSITE=0 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "backup-all: unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
# Validate here, in the main shell: an `exit` inside a process substitution
# only kills the subshell, and an empty loop would end as "all targets ok".
if [ "$MODE" = one ] && ! bl_target_field "$ONLY" kind > /dev/null; then
  echo "backup-all: unknown target: $ONLY" >&2; exit 2
fi

# ---- plan ----
selected_targets() {
  if [ "$MODE" = one ]; then bl_targets | awk -F'|' -v id="$ONLY" '$1==id'; else bl_targets; fi
}

if [ "$DRY_RUN" = 1 ]; then
  while IFS='|' read -r id kind ctx container _extra; do
    echo "plan $id $kind $ctx $container"
  done < <(selected_targets)
  [ "$OFFSITE" = 1 ] && [ "$MODE" = all ] && echo "plan offsite rsync nas $NAS_DEST"
  exit 0
fi

# Progress goes to stderr: producers use stdout for manifest key=value pairs.
log() { printf '%s backup-all: %s\n' "$(date -u +%FT%TZ)" "$*" >&2; }

# ---- guards: fail before touching anything ----
if [ -z "${BACKUP_GPG_PASSPHRASE:-}" ]; then
  log "ABORT: BACKUP_GPG_PASSPHRASE not set - run under: doppler run --project dhg-monitoring --config dev --"; exit 1
fi
mkdir -p "$BACKUP_ROOT" "$BACKUP_STATE_DIR"
BACKUP_MIN_FREE_GB="${BACKUP_MIN_FREE_GB:-10}"
free_gb=$(( $(df -Pk "$BACKUP_ROOT" | awk 'NR==2{print $4}') / 1048576 ))
if [ "$free_gb" -lt "$BACKUP_MIN_FREE_GB" ]; then
  log "ABORT: only ${free_gb} GB free under $BACKUP_ROOT (need $BACKUP_MIN_FREE_GB)"; exit 1
fi

# ---- producers: each writes its archives into $1 (the run's tmp dir) and prints
# manifest key=value pairs on stdout; non-zero exit marks the target failed. ----

# files: tar of the config layer. The list file holds one absolute path per line;
# every entry must be readable or the target fails loudly (a silently missing
# secrets file is exactly the kind of backup that lies).
BACKUP_CONFIG_LIST="${BACKUP_CONFIG_LIST:-$SCRIPT_DIR/config-layer.list}"
produce_files() {
  local out="$1" f n=0
  [ -r "$BACKUP_CONFIG_LIST" ] || { log "config list $BACKUP_CONFIG_LIST unreadable"; return 1; }
  while IFS= read -r f; do
    [ -z "$f" ] && continue; [[ "$f" == \#* ]] && continue
    [ -r "$f" ] || { log "config file not readable: $f"; return 1; }
    n=$((n+1))
  done < "$BACKUP_CONFIG_LIST"
  # pipefail is on: a tar or gpg failure fails the target here, not a week later at the drill
  # paths are made relative to / here (not via --transform) so tar has nothing to warn about
  sed -e '/^\s*$/d' -e '/^\s*#/d' -e 's|^/||' "$BACKUP_CONFIG_LIST" \
    | tar -C / -cf - --files-from=- \
    | bl_gpg_encrypt > "$out/config.tar.gpg" || { log "config tar/encrypt failed"; return 1; }
  echo "members=$n"
}

# pg: extra = user:db1,db2:pghost. Per database, one REPEATABLE READ session
# exports a snapshot, counts every user table under that snapshot, and pg_dump
# runs with --snapshot so the counts and the archive describe the same instant.
# The session is `docker exec -i ... psql` fed through a named pipe (fd 4).
produce_pg() {
  local out="$1" ctx="$2" container="$3" extra="$4"
  local user dbs pghost db snap line counts hostflag=() json='{}'
  IFS=: read -r user dbs pghost <<<"$extra"
  [ -n "$pghost" ] && hostflag=(-h "$pghost")
  for db in ${dbs//,/ }; do
    # psql session: requests via a named pipe on fd 4, answers in a file
    rm -f "$out/.psql-$db.in"; mkfifo "$out/.psql-$db.in"
    dk "$ctx" exec -i "$container" psql -X -q -At -v ON_ERROR_STOP=1 -U "$user" -d "$db" "${hostflag[@]}" \
      < "$out/.psql-$db.in" > "$out/.psql-$db.out" &
    local psql_pid=$!
    exec 4> "$out/.psql-$db.in"
    printf 'BEGIN ISOLATION LEVEL REPEATABLE READ;\nSELECT pg_export_snapshot();\n%s\nSELECT %s;\n' "$BL_PG_COUNTS_SQL" "'__END__'" >&4
    # wait for the session to publish snapshot + counts
    local waited=0
    until [ -s "$out/.psql-$db.out" ] && tail -1 "$out/.psql-$db.out" | grep -qx '__END__'; do
      sleep 0.2; waited=$((waited+1)); [ "$waited" -gt 300 ] && { log "psql session for $db never answered"; exec 4>&-; return 1; }
    done
    snap="$(head -1 "$out/.psql-$db.out")"
    counts="$(sed -n '2,$p' "$out/.psql-$db.out" | sed '/^__END__$/d')"
    dk "$ctx" exec "$container" pg_dump -Fc "--snapshot=$snap" -U "$user" -d "$db" "${hostflag[@]}" \
      | bl_gpg_encrypt > "$out/$db.dump.gpg" || { log "pg_dump $db failed"; exec 4>&-; return 1; }
    printf 'COMMIT;\n' >&4; exec 4>&-
    wait "$psql_pid" || { log "psql session for $db exited non-zero"; return 1; }
    rm -f "$out/.psql-$db.in" "$out/.psql-$db.out"
    json="$(jq -c --arg db "$db" --arg c "$counts" '. + {($db): ($c | split("\n") | map(select(length>0) | split("=") | {(.[0]): (.[1]|tonumber)}) | add // {})}' <<<"$json")"
  done
  dk "$ctx" exec "$container" pg_dumpall --roles-only -U "$user" "${hostflag[@]}" | bl_gpg_encrypt > "$out/roles.sql.gpg" \
    || { log "pg_dumpall --roles-only failed"; return 1; }
  echo "image=$(dk "$ctx" inspect -f '{{.Config.Image}}' "$container")"
  echo "counts=$json"
}

# clickhouse: extra = user:database. The password stays inside the container:
# the query runs through `sh -c` with positional args, so argv never carries it.
# Per table `SELECT * FORMAT Native` is self-describing; the drill counts rows
# from the stream itself, so no count is taken here (ReplacingMergeTree dedup
# is eventual anyway). Views are DDL-only.
ch_query() { # <ctx> <container> <user> <query>
  dk "$1" exec "$2" sh -c 'exec clickhouse-client --user "$1" --password "$CLICKHOUSE_PASSWORD" --query "$2"' sh "$3" "$4"
}
produce_clickhouse() {
  local out="$1" ctx="$2" container="$3" extra="$4" user db t n=0
  IFS=: read -r user db <<<"$extra"
  ch_query "$ctx" "$container" "$user" \
    "SELECT create_table_query FROM system.tables WHERE database='$db' ORDER BY engine IN ('View','MaterializedView'), name FORMAT TSVRaw" \
    | bl_gpg_encrypt > "$out/ddl.sql.gpg" || { log "clickhouse DDL export failed"; return 1; }
  for t in $(ch_query "$ctx" "$container" "$user" \
      "SELECT name FROM system.tables WHERE database='$db' AND engine NOT IN ('View','MaterializedView') ORDER BY name FORMAT TSVRaw"); do
    ch_query "$ctx" "$container" "$user" "SELECT * FROM $db.$t FORMAT Native" | gzip -1 | bl_gpg_encrypt > "$out/$t.native.gz.gpg" \
      || { log "clickhouse export of $t failed"; return 1; }
    n=$((n+1))
  done
  [ "$n" -gt 0 ] || { log "clickhouse: no tables found in $db"; return 1; }
  echo "image=$(dk "$ctx" inspect -f '{{.Config.Image}}' "$container")"
  echo "tables=$n"
}

# minio: extra = path of the xl-single tree inside the container. `docker cp`
# streams a tar of the whole tree (incl. .minio.sys) with nothing installed in
# the container; the member count is recorded for the drill's equality check.
produce_minio() {
  local out="$1" ctx="$2" container="$3" path="$4" members
  dk "$ctx" cp "$container:$path" - | bl_gpg_encrypt > "$out/data.tar.gpg"
  [ -s "$out/data.tar.gpg" ] || { log "docker cp $container:$path produced nothing"; return 1; }
  # member count from the archive itself (no plaintext on disk; one cheap decrypt pass)
  members="$(bl_gpg_decrypt < "$out/data.tar.gpg" | tar -t | wc -l)"
  [ "$members" -gt 0 ] || { log "docker cp $container:$path produced an empty tar"; return 1; }
  echo "image=$(dk "$ctx" inspect -f '{{.Config.Image}}' "$container")"
  echo "members=$members"
}

# volume: extra = container:path[:exclude],...  Each source is tarred INSIDE its
# container (every image here ships tar) so an exclusion (open-webui's
# regenerable model cache) is applied at the source, never via plaintext on disk.
produce_volume() {
  local out="$1" ctx="$2" spec c path excl parent base args members='{}' images='{}' n
  for spec in ${4//,/ }; do
    IFS=: read -r c path excl <<<"$spec"
    parent="$(dirname "$path")"; base="$(basename "$path")"
    args=(-C "$parent" -cf -); [ -n "$excl" ] && args+=("--exclude=$base/$excl"); args+=("$base")
    dk "$ctx" exec "$c" tar "${args[@]}" | bl_gpg_encrypt > "$out/$c.tar.gpg"
    [ -s "$out/$c.tar.gpg" ] || { log "tar of $c:$path produced nothing"; return 1; }
    n="$(bl_gpg_decrypt < "$out/$c.tar.gpg" | tar -t | wc -l)"
    members="$(jq -c --arg c "$c" --argjson n "$n" '. + {($c): $n}' <<<"$members")"
    images="$(jq -c --arg c "$c" --arg i "$(dk "$ctx" inspect -f '{{.Config.Image}}' "$c")" '. + {($c): $i}' <<<"$images")"
  done
  echo "members=$members"
  echo "images=$images"
}

# integrity: every archive must decrypt and parse with the reader the drill will use.
# Custom-format dumps are listed with pg_restore FROM THE SOURCE IMAGE (host
# pg_restore 16 cannot read pg17 archives); it needs a seekable file, hence tmp.
verify_archives() { # <dir> <source image or ''>
  local dir="$1" image="$2" f plain rc
  for f in "$dir"/*.gpg; do
    [ -f "$f" ] || continue
    case "$f" in
      *.tar.gpg)  bl_gpg_decrypt < "$f" | tar -t > /dev/null ;;
      *.dump.gpg) plain="$dir/.verify.dump"; rc=1
                  if bl_gpg_decrypt < "$f" > "$plain"; then
                    docker run --rm -v "$plain:/dump:ro" "$image" pg_restore --list /dump > /dev/null; rc=$?
                  fi
                  rm -f "$plain"; [ "$rc" -eq 0 ] ;;
      *.native.gz.gpg) bl_gpg_decrypt < "$f" | gzip -t ;;
      *)          bl_gpg_decrypt < "$f" > /dev/null ;;
    esac || { log "integrity check failed: $f"; return 1; }
  done
}

# ---- run one target: attempt -> produce -> verify -> manifest (last) -> rename -> success ----
run_target() {
  local id="$1" kind="$2" ctx="$3" container="$4" extra="$5"
  local run tmp final t0 t1 kv=() bytes
  run="$(bl_run_id)"; t0=$(date +%s)
  bl_state_set "$id" attempt "$t0"; bl_write_textfile
  tmp="$BACKUP_ROOT/$id/tmp-$run"; final="$BACKUP_ROOT/$id/$run"
  mkdir -p "$tmp"
  log "target $id ($kind, $ctx) -> $final"
  # producer stdout = manifest fields; its exit status must not be lost (mapfile
  # on a process substitution would return 0 regardless), so capture to a file.
  if "produce_$kind" "$tmp" "$ctx" "$container" "$extra" > "$tmp/.fields" \
     && verify_archives "$tmp" "$(sed -n 's/^image=//p' "$tmp/.fields")"; then
    mapfile -t kv < "$tmp/.fields"; rm -f "$tmp/.fields"
    t1=$(date +%s)
    bytes=$(du -sb "$tmp" | cut -f1)
    # errexit is off inside this if-body: every step that makes the run "real"
    # must be chained explicitly, or a jq/mv failure would still stamp success.
    if bl_write_manifest "$tmp" target="$id" kind="$kind" run="$run" ctx="$ctx" container="$container" \
         duration_seconds=$((t1 - t0)) "${kv[@]}" \
       && [ -s "$tmp/manifest.json" ] && mv "$tmp" "$final"; then
      bl_state_set "$id" success "$t1"; bl_state_set "$id" size_bytes "$bytes"; bl_state_set "$id" duration_seconds $((t1 - t0))
      bl_write_textfile
      log "target $id ok (${bytes} B, $((t1 - t0)) s)"
      return 0
    fi
    log "target $id: manifest or rename failed"
  fi
  rm -rf -- "$tmp"
  bl_write_textfile
  log "target $id FAILED"
  return 1
}

# ---- remote contexts: one bounded probe each; an unreachable host fails its
# targets up front (attempt stamped, so BackupFailed fires) instead of hanging
# a dump for the CLI's 30 s default per call. ----
declare -A ctx_ok=()
probe_ctx() {
  local ctx="$1"
  [ "$ctx" = local ] && return 0
  if [ -z "${ctx_ok[$ctx]+x}" ]; then
    local err
    if err="$(timeout 30 docker --context "$ctx" version 2>&1 >/dev/null)"; then ctx_ok[$ctx]=1
    else ctx_ok[$ctx]=0; log "context $ctx unreachable - its targets are marked failed: $(head -1 <<<"$err")"; fi
  fi
  [ "${ctx_ok[$ctx]}" = 1 ]
}

failed=0
while IFS='|' read -r id kind ctx container extra; do
  if ! probe_ctx "$ctx"; then
    bl_state_set "$id" attempt "$(date +%s)"; bl_write_textfile
    log "target $id FAILED (context $ctx unreachable)"; failed=$((failed+1)); continue
  fi
  run_target "$id" "$kind" "$ctx" "$container" "$extra" || failed=$((failed+1))
done < <(selected_targets)

# ---- offsite mirror: the NAS holds an exact copy of the local tree (full
# retention lives locally; Snapshot Replication on the NAS is the undo). ----
BACKUP_NAS_KEY="${BACKUP_NAS_KEY:-$HOME/.ssh/nas-backup_ed25519}"
if [ "$OFFSITE" = 1 ]; then
  # .state is local operational state (stamps), not backup data; it also changes
  # right after the mirror, so mirroring it would make every dry-run look dirty.
  if rsync -a --delete --delete-delay --delay-updates --exclude='tmp-*' --exclude='.state' \
       -e "ssh -p 22 -i $BACKUP_NAS_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o LogLevel=ERROR" \
       "$BACKUP_ROOT/" "$NAS_DEST"; then
    bl_state_set offsite success "$(date +%s)"; bl_write_textfile; log "offsite mirror ok -> $NAS_DEST"
  else
    log "offsite mirror FAILED (local tree intact)"; failed=$((failed+1))
  fi
fi

bl_prune_local

if [ "$failed" -gt 0 ]; then log "$failed step(s) failed"; exit 1; fi
log "all targets ok"
exit 0
