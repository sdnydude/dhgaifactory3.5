#!/usr/bin/env bash
# backup-lib.sh — pure functions shared by backup-all.sh and restore-drill.sh.
# Sourced, never executed. Tested by observability/tests/backup-lib.bats.

bl_run_id() {
  date -u +%Y%m%dT%H%M%SZ
}

# ---- target table ----
# id | kind | ctx | container | extra
#   kind pg:         extra = user:db1,db2:pghost   (pghost empty = socket default; plane needs /var/run/postgresql)
#   kind clickhouse: extra = user:database
#   kind minio:      extra = path inside the container holding the xl-single tree
#   kind volume:     extra = container:path[:exclude],...  (tar inside the container; exclude is relative to path)
#   kind files:      extra = name of the config-file list (resolved by backup-all.sh)
# ctx is "local" or a docker context name. The offsite mirror is not a row.
bl_targets() {
  cat <<'EOF'
registry-db|pg|local|dhg-registry-db|dhg:dhg_registry,snap2list:
medkb-db|pg|local|dhg-medkb-db|medkb:medkb:
eval-db|pg|local|dhg-eval-db|evalviewer:evalviewer,evalviewer_test:
audio-postgres|pg|local|dhg-audio-postgres|user:audio_agent:
transcribe-db|pg|local|dhg-transcribe-db|transcribe:transcribe:
portage-db|pg|local|portage-db|portage:portage:
plane-db|pg|local|plane-app-plane-db-1|plane:plane:/var/run/postgresql
langfuse-postgres|pg|dh40801|dhg-langfuse-postgres|postgres:postgres:
langfuse-clickhouse|clickhouse|dh40801|dhg-langfuse-clickhouse|clickhouse:default
langfuse-minio|minio|dh40801|dhg-langfuse-minio|/data
plane-minio|minio|local|plane-app-plane-minio-1|/export
volumes|volume|local|-|dhg-grafana:/var/lib/grafana/grafana.db,dhg-registry-api:/exports,dhg-open-webui:/app/backend/data:cache
config|files|local|-|config-layer
EOF
}

# Per-table row counts as "schema.table=N" lines, one query, works under a
# REPEATABLE READ snapshot (backup) and against a restored database (drill).
BL_PG_COUNTS_SQL="SELECT format('%I.%I', schemaname, relname) || '=' || (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I.%I', schemaname, relname), false, true, '')))[1]::text FROM pg_stat_user_tables ORDER BY 1;"

# bl_target_field <id> <id|kind|ctx|container|extra> — one field of one row; exit 1 if the id is unknown
bl_target_field() {
  local row; row="$(bl_targets | awk -F'|' -v id="$1" '$1==id')"
  [ -n "$row" ] || return 1
  case "$2" in
    id) cut -d'|' -f1 <<<"$row" ;; kind) cut -d'|' -f2 <<<"$row" ;; ctx) cut -d'|' -f3 <<<"$row" ;;
    container) cut -d'|' -f4 <<<"$row" ;; extra) cut -d'|' -f5 <<<"$row" ;; *) return 1 ;;
  esac
}

# bl_is_sunday <run_id>  — true when the run's UTC date is a Sunday (weekly-keep tier)
bl_is_sunday() {
  local d="${1:0:8}"
  [ "$(date -u -d "${d:0:4}-${d:4:2}-${d:6:2}" +%u)" = 7 ]
}

# bl_gpg_encrypt / bl_gpg_decrypt — stdin to stdout, symmetric AES256.
# The passphrase travels on fd 3 (stdin carries the data stream) and never
# appears in argv or the environment of gpg's children.
bl_gpg_encrypt() {
  : "${BACKUP_GPG_PASSPHRASE:?BACKUP_GPG_PASSPHRASE not set - run under doppler run --project dhg-monitoring --config dev --}"
  gpg --batch --yes --quiet --symmetric --cipher-algo AES256 --passphrase-fd 3 3<<<"$BACKUP_GPG_PASSPHRASE"
}

bl_gpg_decrypt() {
  : "${BACKUP_GPG_PASSPHRASE:?BACKUP_GPG_PASSPHRASE not set}"
  gpg --batch --yes --quiet --decrypt --passphrase-fd 3 3<<<"$BACKUP_GPG_PASSPHRASE"
}

# bl_write_manifest <run_dir> key=value...  — writes <run_dir>/manifest.json LAST.
# The manifest is the commit marker: prune and drills ignore run dirs without one.
# Scalar values become strings, except a value that parses as JSON (counts='{...}')
# or as an integer. Every file already in the dir is recorded with bytes + sha256.
bl_write_manifest() {
  local dir="$1"; shift
  local args=() kv k v
  for kv in "$@"; do
    k="${kv%%=*}"; v="${kv#*=}"
    if [[ "$v" =~ ^-?[0-9]+$ ]] || { [[ "$v" == \{* || "$v" == \[* ]] && jq -e . >/dev/null 2>&1 <<<"$v"; }; then
      args+=(--argjson "$k" "$v")
    else
      args+=(--arg "$k" "$v")
    fi
  done
  local files='{}' f name bytes sha
  for f in "$dir"/*; do
    [ -f "$f" ] || continue
    name="$(basename "$f")"; [ "$name" = manifest.json ] && continue
    bytes="$(stat -c %s "$f")"; sha="$(sha256sum "$f" | cut -d' ' -f1)"
    files="$(jq -c --arg n "$name" --argjson b "$bytes" --arg s "$sha" '. + {($n): {bytes: $b, sha256: $s}}' <<<"$files")"
  done
  local tmp; tmp="$(mktemp "$dir/.manifest.XXXXXX")"
  jq -n "${args[@]}" --argjson files "$files" --arg written_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '$ARGS.named + {files: $files, written_at: $written_at}' > "$tmp" \
    && mv -f "$tmp" "$dir/manifest.json"
}

# ---- per-target state and the Prometheus textfile ----
# State lives as one small file per key under $BACKUP_STATE_DIR/<name>/<key>
# so it survives across runs and a killed run still leaves the last values.
BACKUP_STATE_DIR="${BACKUP_STATE_DIR:-/mnt/4tb/backups/nightly/.state}"
BACKUP_TEXTFILE="${BACKUP_TEXTFILE:-/mnt/4tb/observability/textfile/backups.prom}"

# bl_state_set <name> <key> <value>
bl_state_set() {
  mkdir -p "$BACKUP_STATE_DIR/$1"
  printf '%s\n' "$3" > "$BACKUP_STATE_DIR/$1/$2"
}

# bl_write_textfile — rewrites $BACKUP_TEXTFILE atomically from the state dir.
# Called after EVERY target so a run killed mid-way still bumps attempt stamps.
# A metric is emitted only when its state file exists: absent, never 0.
bl_write_textfile() {
  local out="$BACKUP_TEXTFILE" tmp d name key
  tmp="$(mktemp "${out}.XXXXXX")"
  {
    echo '# HELP backup_last_attempt_timestamp Unix time backup-all.sh last started this target.'
    echo '# TYPE backup_last_attempt_timestamp gauge'
    echo '# HELP backup_last_success_timestamp Unix time this target last completed with a verified archive and manifest.'
    echo '# TYPE backup_last_success_timestamp gauge'
    echo '# HELP backup_last_size_bytes Encrypted bytes written for the last successful run of this target.'
    echo '# TYPE backup_last_size_bytes gauge'
    echo '# HELP backup_last_duration_seconds Wall seconds of the last successful run of this target.'
    echo '# TYPE backup_last_duration_seconds gauge'
    echo '# HELP backup_restore_drill_success_timestamp Unix time restore-drill.sh last restored and verified this target in an ephemeral container.'
    echo '# TYPE backup_restore_drill_success_timestamp gauge'
    echo '# HELP backup_offsite_last_success_timestamp Unix time the local backup tree was last mirrored to the NAS.'
    echo '# TYPE backup_offsite_last_success_timestamp gauge'
    for d in "$BACKUP_STATE_DIR"/*/; do
      [ -d "$d" ] || continue
      name="$(basename "$d")"
      if [ "$name" = offsite ]; then
        [ -f "$d/success" ] && echo "backup_offsite_last_success_timestamp $(<"$d/success")"
        continue
      fi
      for key in attempt success size_bytes duration_seconds drill_success; do
        [ -f "$d/$key" ] || continue
        case "$key" in
          attempt)          echo "backup_last_attempt_timestamp{name=\"$name\"} $(<"$d/$key")" ;;
          success)          echo "backup_last_success_timestamp{name=\"$name\"} $(<"$d/$key")" ;;
          size_bytes)       echo "backup_last_size_bytes{name=\"$name\"} $(<"$d/$key")" ;;
          duration_seconds) echo "backup_last_duration_seconds{name=\"$name\"} $(<"$d/$key")" ;;
          drill_success)    echo "backup_restore_drill_success_timestamp{name=\"$name\"} $(<"$d/$key")" ;;
        esac
      done
    done
  } > "$tmp"
  chmod 0644 "$tmp"
  mv -f "$tmp" "$out"
}

# ---- retention ----
BACKUP_ROOT="${BACKUP_ROOT:-/mnt/4tb/backups/nightly}"
BACKUP_KEEP_DAILY_DAYS="${BACKUP_KEEP_DAILY_DAYS:-30}"
BACKUP_KEEP_SUNDAY_DAYS="${BACKUP_KEEP_SUNDAY_DAYS:-84}"

# bl_prune_local [now_epoch] — deletes completed run dirs under $BACKUP_ROOT/<target>/
# older than the daily window, keeping Sunday runs for the weekly window.
# Only dirs named like a run id AND holding manifest.json are ever removed:
# tmp-* dirs, half-written runs, .state and anything outside the root are untouched.
bl_prune_local() {
  local now="${1:-$(date -u +%s)}" tdir rdir run d ts age_days
  for tdir in "$BACKUP_ROOT"/*/; do
    [ -d "$tdir" ] || continue
    for rdir in "$tdir"*/; do
      [ -d "$rdir" ] || continue
      run="$(basename "$rdir")"
      [[ "$run" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] || continue
      [ -f "$rdir/manifest.json" ] || continue
      d="${run:0:8}"
      ts="$(date -u -d "${d:0:4}-${d:4:2}-${d:6:2}T${run:9:2}:${run:11:2}:${run:13:2}Z" +%s)"
      age_days=$(( (now - ts) / 86400 ))
      if bl_is_sunday "$run"; then
        [ "$age_days" -gt "$BACKUP_KEEP_SUNDAY_DAYS" ] && rm -rf -- "$rdir"
      else
        [ "$age_days" -gt "$BACKUP_KEEP_DAILY_DAYS" ] && rm -rf -- "$rdir"
      fi
    done
  done
  return 0
}

# bl_latest_run <target> — prints the newest completed (manifest-bearing) run dir; exit 1 if none.
bl_latest_run() {
  local rdir run
  for rdir in $(ls -1d "$BACKUP_ROOT/$1"/*/ 2>/dev/null | sort -r); do
    run="$(basename "$rdir")"
    [[ "$run" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] || continue
    if [ -f "$rdir/manifest.json" ]; then printf '%s\n' "${rdir%/}"; return 0; fi
  done
  return 1
}
