#!/usr/bin/env bats
# Tests for observability/scripts/restore-drill.sh — restores the newest
# completed run of a target into an ephemeral container and verifies it
# against the manifest. Docker is a shim on PATH; the config-layer target is
# exercised for real (files only) via a real backup-all.sh run first.
#
# Run: python3 observability/tests/bats-tdd-reporter.py observability/tests/restore-drill.bats

load test_helper
DRILL="$BATS_TEST_DIRNAME/../scripts/restore-drill.sh"
BACKUP="$BATS_TEST_DIRNAME/../scripts/backup-all.sh"

setup() {
  common_setup
  export BACKUP_DRILL_TMP="$TEST_ROOT/drill-scratch"
  mkdir -p "$TEST_ROOT/etc"
  printf 'A=1
' > "$TEST_ROOT/etc/one.env"; printf 'B=2
' > "$TEST_ROOT/etc/two.env"
  printf '%s
%s
' "$TEST_ROOT/etc/one.env" "$TEST_ROOT/etc/two.env" > "$TEST_ROOT/config.list"
  export BACKUP_CONFIG_LIST="$TEST_ROOT/config.list"
}
teardown() { common_teardown; }

@test "a manifest missing a required key fails the drill with a 'manifest missing' message, not a null comparison" {
  "$BACKUP" --target config --no-offsite
  rundir="$(ls -d "$BACKUP_ROOT"/config/*/ | head -1)"; rundir="${rundir%/}"
  jq 'del(.members)' "$rundir/manifest.json" > "$rundir/m.tmp" && mv "$rundir/m.tmp" "$rundir/manifest.json"
  run "$DRILL" config
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'manifest missing: members'
}

@test "the drill takes the same lock as backup-all.sh and exits 75 while a backup holds it" {
  "$BACKUP" --target config --no-offsite
  exec 9>"$BACKUP_LOCK"; flock -x 9
  run "$DRILL" config
  exec 9>&-
  [ "$status" -eq 75 ]
  printf '%s\n' "$output" | grep -qi 'already running'
  ! grep -q 'backup_restore_drill_success_timestamp{name="config"}' "$BACKUP_TEXTFILE"
}

@test "config drill: the newest completed run decrypts, its tar lists exactly manifest.members entries, and the drill stamp is written" {
  "$BACKUP" --target config --no-offsite
  run "$DRILL" config
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" | grep -q 'config .*PASS'
  grep -q '^backup_restore_drill_success_timestamp{name="config"} ' "$BACKUP_TEXTFILE"
}

@test "a count mismatch fails the drill (exit 1, FAIL line, no drill stamp); a run without a manifest is never chosen" {
  "$BACKUP" --target config --no-offsite
  rundir="$(ls -d "$BACKUP_ROOT"/config/*/ | head -1)"; rundir="${rundir%/}"
  jq '.members = 99' "$rundir/manifest.json" > "$rundir/m.tmp" && mv "$rundir/m.tmp" "$rundir/manifest.json"
  mkdir -p "$BACKUP_ROOT/config/29990101T000000Z"      # newer, but no manifest: must be ignored
  run "$DRILL" config
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q "config $(basename "$rundir") FAIL"
  ! grep -q 'backup_restore_drill_success_timestamp{name="config"}' "$BACKUP_TEXTFILE"
}

# One docker shim for both the backup (pg producer) and the drill. DRILL_COUNTS
# controls what the restored database "contains".
install_pg_shim() {
  install_shim docker <<'SHIM'
#!/usr/bin/env bash
echo "docker $*" >> "$SHIM_LOG"
case " $* " in
  *" version "*) exit 0 ;;
  *" inspect "*) echo "pgvector/pgvector:pg15" ;;
  # ---- backup side ----
  *" exec -i dhg-eval-db psql "*)
    while IFS= read -r line; do case "$line" in
      *pg_export_snapshot*) echo "00000003-0000000A-1" ;;
      *pg_stat_user_tables*) printf 'public.user_x=3\npublic.users=0\n' ;;   # names that a locale sort orders differently from byte order
      *__END__*) echo "__END__" ;; esac; done ;;
  *" exec dhg-eval-db pg_dump "*) printf 'PGDMP-fake' ;;
  *" exec dhg-eval-db pg_dumpall "*) printf 'CREATE ROLE fake;\n' ;;
  *" run --rm "*" pg_restore --list "*) exit 0 ;;
  # ---- drill side ----
  *" run -d "*) echo "deadbeefcafe" ;;
  *" exec dhg-restore-drill-eval-db mkdir -p /restore "*) exit 0 ;;
  *" exec dhg-restore-drill-eval-db pg_isready "*) exit 0 ;;
  *" cp "*" dhg-restore-drill-eval-db:/restore/"*) [ -f "${@: -2:1}" ] || { echo "cp source missing: ${@: -2:1}" >&2; exit 9; } ;;
  *" exec dhg-restore-drill-eval-db pg_restore "*) exit 0 ;;
  *" exec -i dhg-restore-drill-eval-db psql "*) cat > /dev/null ;;      # roles
  *" exec dhg-restore-drill-eval-db psql "*"pg_stat_user_tables"*) printf '%b' "$DRILL_COUNTS" ;;
  *" exec dhg-restore-drill-eval-db psql "*) exit 0 ;;                    # CREATE DATABASE
  *" rm -f -v dhg-restore-drill-eval-db "*) exit 0 ;;
  *) echo "unexpected docker call: $*" >&2; exit 9 ;;
esac
SHIM
  export DRILL_COUNTS='public.users=0\npublic.user_x=3\n'   # emitted in locale order on purpose; the drill must sort in byte order
}

@test "pg drill: ephemeral container with --network none, roles + dumps restored from copied files, per-table counts equal the manifest, container removed" {
  install_pg_shim
  "$BACKUP" --target eval-db --no-offsite
  run "$DRILL" eval-db
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" | grep -q 'eval-db .*PASS'
  grep -q '^docker run -d --network none --name dhg-restore-drill-eval-db -e POSTGRES_PASSWORD=drill pgvector/pgvector:pg15$' "$SHIM_LOG"
  grep -q '^docker exec dhg-restore-drill-eval-db mkdir -p /restore$' "$SHIM_LOG"     # docker cp - needs an existing dir
  grep -q '^docker exec dhg-restore-drill-eval-db pg_restore -U postgres -d evalviewer /restore/evalviewer.dump$' "$SHIM_LOG"
  grep -q '^docker exec dhg-restore-drill-eval-db pg_restore -U postgres -d evalviewer_test /restore/evalviewer_test.dump$' "$SHIM_LOG"
  grep -q '^docker rm -f -v dhg-restore-drill-eval-db$' "$SHIM_LOG"
  grep -q '^backup_restore_drill_success_timestamp{name="eval-db"} ' "$BACKUP_TEXTFILE"
  # plaintext scratch never lives inside the mirrored tree: the copied file's
  # path is outside BACKUP_ROOT and nothing is left behind anywhere
  src="$(grep -o '^docker cp [^ ]* dhg-restore-drill-eval-db:/restore/evalviewer.dump$' "$SHIM_LOG" | awk '{print $3}')"
  [ -n "$src" ]
  case "$src" in "$BACKUP_ROOT"/*) false ;; esac
  [ "$(find "$BACKUP_ROOT" "$BACKUP_DRILL_TMP" -name '.drill*' -o -name '*.dump' -o -name '*.env-file*' 2>/dev/null | wc -l)" -eq 0 ]
}

@test "pg drill: a restored table count that differs from the manifest fails the drill, and the container is still removed" {
  install_pg_shim
  "$BACKUP" --target eval-db --no-offsite
  export DRILL_COUNTS='public.user_x=2\npublic.users=0\n'
  run "$DRILL" eval-db
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'row counts differ'
  printf '%s\n' "$output" | grep -q 'eval-db .*FAIL'
  grep -q '^docker rm -f -v dhg-restore-drill-eval-db$' "$SHIM_LOG"
  ! grep -q 'backup_restore_drill_success_timestamp{name="eval-db"}' "$BACKUP_TEXTFILE"
}

@test "--all removes a failed target's container before moving to the next target (not only at script exit)" {
  install_pg_shim
  "$BACKUP" --target eval-db --no-offsite
  # a second completed run so --all has a "next target" after the failing one
  mkdir -p "$BACKUP_ROOT/volumes/20260906T033000Z"; printf '{"target":"volumes","members":{},"images":{}}' > "$BACKUP_ROOT/volumes/20260906T033000Z/manifest.json"
  export DRILL_COUNTS='public.user_x=2\npublic.users=0\n'
  run "$DRILL" --all
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'eval-db .*FAIL'
  printf '%s\n' "$output" | grep -q 'volumes .*'          # the next target was reached
  # the rm for eval-db must appear BEFORE the next target's log line, i.e. inside drill_target
  rm_line="$(grep -n '^docker rm -f dhg-restore-drill-eval-db$' "$SHIM_LOG" | head -1 | cut -d: -f1)"
  [ -n "$rm_line" ]
  rm_pos="$(printf '%s\n' "$output" | grep -n 'eval-db .*FAIL' | head -1 | cut -d: -f1)"
  next_pos="$(printf '%s\n' "$output" | grep -n 'volumes: drilling' | head -1 | cut -d: -f1)"
  [ -n "$next_pos" ] && [ "$rm_pos" -lt "$next_pos" ]
}

install_ch_shim() {
  install_shim docker <<'SHIM'
#!/usr/bin/env bash
echo "docker $*" >> "$SHIM_LOG"
q="${@: -1}"
case " $* " in
  *" version "*) exit 0 ;;
  *" inspect "*) echo "clickhouse/clickhouse-server:25.12" ;;
  # ---- backup side (query is the last positional arg of `sh -c ... sh user query`) ----
  *" --context dh40801 exec dhg-langfuse-clickhouse "*)
    case "$q" in
      *create_table_query*) printf 'CREATE TABLE default.traces (id String) ENGINE = MergeTree ORDER BY id\nCREATE TABLE default.scores (id String) ENGINE = MergeTree ORDER BY id\n' ;;
      *"FROM system.tables"*) printf 'scores\ntraces\n' ;;
      *"default.scores FORMAT Native"*) : ;;                       # empty table: 0-byte Native stream
      *"FORMAT Native"*) printf 'NATIVE-fake-traces' ;;
    esac ;;
  # ---- drill side ----
  *" run -d "*) echo "deadbeefcafe" ;;
  *" exec dhg-restore-drill-langfuse-clickhouse mkdir -p /restore "*) exit 0 ;;
  *" exec dhg-restore-drill-langfuse-clickhouse clickhouse-client --query SELECT 1 "*) exit 0 ;;
  *" exec -i dhg-restore-drill-langfuse-clickhouse clickhouse-client --multiquery "*) cat > /dev/null ;;
  *" exec -i dhg-restore-drill-langfuse-clickhouse clickhouse-client --query INSERT INTO default.traces FORMAT Native "*) cat > /dev/null ;;
  *" cp "*" dhg-restore-drill-langfuse-clickhouse:/restore/"*) [ -f "${@: -2:1}" ] || { echo "cp source missing" >&2; exit 9; } ;;
  *" clickhouse local "*) printf '%s\n' "${DRILL_CH_FILE_COUNT:-5}" ;;
  *" exec dhg-restore-drill-langfuse-clickhouse clickhouse-client --query SELECT count() FROM default.scores "*) echo 0 ;;
  *" exec dhg-restore-drill-langfuse-clickhouse clickhouse-client --query SELECT count() FROM default.traces "*) printf '%s\n' "${DRILL_CH_COUNT:-5}" ;;
  *" rm -f -v dhg-restore-drill-langfuse-clickhouse "*) exit 0 ;;
  *) echo "unexpected docker call: $*" >&2; exit 9 ;;
esac
SHIM
}

@test "clickhouse drill: DDL replayed, each Native stream inserted, restored count equals the count clickhouse-local reads from the file itself" {
  install_ch_shim
  "$BACKUP" --target langfuse-clickhouse --no-offsite
  run "$DRILL" langfuse-clickhouse
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" | grep -q 'langfuse-clickhouse .*PASS'
  grep -q '^docker run -d --network none --name dhg-restore-drill-langfuse-clickhouse clickhouse/clickhouse-server:25.12$' "$SHIM_LOG"
  grep -q '^docker exec dhg-restore-drill-langfuse-clickhouse mkdir -p /restore$' "$SHIM_LOG"   # docker cp needs the dir
  grep -q 'clickhouse-client --query INSERT INTO default.traces FORMAT Native' "$SHIM_LOG"
  grep -q "clickhouse local --query SELECT count() FROM file('/restore/traces.native', Native)" "$SHIM_LOG"
  grep -q '^docker rm -f -v dhg-restore-drill-langfuse-clickhouse$' "$SHIM_LOG"
  printf '%s\n' "$output" | grep -q 'langfuse-clickhouse/scores: 0 rows verified'   # empty table branch (0-byte Native)
}

@test "clickhouse drill: a corrupted (undecryptable) Native archive fails the drill instead of passing as an empty table" {
  install_ch_shim
  "$BACKUP" --target langfuse-clickhouse --no-offsite
  rundir="$(ls -d "$BACKUP_ROOT"/langfuse-clickhouse/*/ | head -1)"; rundir="${rundir%/}"
  head -c 40 "$rundir/traces.native.gz.gpg" > "$rundir/t.tmp" && mv "$rundir/t.tmp" "$rundir/traces.native.gz.gpg"
  export DRILL_CH_COUNT=0
  run "$DRILL" langfuse-clickhouse
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'decrypt of traces failed'
  grep -q '^docker rm -f -v dhg-restore-drill-langfuse-clickhouse$' "$SHIM_LOG"
}

@test "clickhouse drill: restored count differing from the file count fails the drill" {
  install_ch_shim
  "$BACKUP" --target langfuse-clickhouse --no-offsite
  export DRILL_CH_COUNT=4 DRILL_CH_FILE_COUNT=5
  run "$DRILL" langfuse-clickhouse
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'restored 4 rows, file holds 5'
  grep -q '^docker rm -f -v dhg-restore-drill-langfuse-clickhouse$' "$SHIM_LOG"
}

install_minio_shim() {
  mkdir -p "$TEST_ROOT/tree/data/langfuse/obj1" "$TEST_ROOT/tree/data/.minio.sys/config"
  printf 'x' > "$TEST_ROOT/tree/data/langfuse/obj1/xl.meta"; printf 'c' > "$TEST_ROOT/tree/data/.minio.sys/config/config.json"
  install_shim docker <<'SHIM'
#!/usr/bin/env bash
echo "docker $*" >> "$SHIM_LOG"
case " $* " in
  *" version "*) exit 0 ;;
  *" inspect -f {{.Config.Image}} "*) echo "cgr.dev/chainguard/minio:latest" ;;
  *" inspect -f "*"Env"*) printf 'MINIO_ROOT_USER=minio\nMINIO_ROOT_PASSWORD=shim-secret\nPATH=/usr/bin\n' ;;
  *" cp dhg-langfuse-minio:/data - "*) tar -C "$SHIM_TREE" -cf - data ;;
  # ---- drill side ----
  *" create --network none --name dhg-restore-drill-langfuse-minio -v /data --env-file "*) echo "deadbeefcafe" ;;
  *" cp - dhg-restore-drill-langfuse-minio:/ "*) cat > /dev/null ;;
  *" start dhg-restore-drill-langfuse-minio "*) exit 0 ;;
  *" exec dhg-restore-drill-langfuse-minio sh -c exec mc alias set "*) exit 0 ;;
  *" exec dhg-restore-drill-langfuse-minio mc ls local "*) echo "[2026-09-10 00:00:00 UTC]     0B langfuse/" ;;
  *" cp dhg-restore-drill-langfuse-minio:/data - "*) tar -C "$SHIM_TREE" -cf - data ;;
  *" rm -f -v dhg-restore-drill-langfuse-minio "*) exit 0 ;;
  *) echo "unexpected docker call: $*" >&2; exit 9 ;;
esac
SHIM
  export SHIM_TREE="$TEST_ROOT/tree"
}

@test "minio drill: server started from the archived tree with the source's root credentials (env-file, never argv), buckets listed, member count equals the manifest" {
  install_minio_shim
  "$BACKUP" --target langfuse-minio --no-offsite
  run "$DRILL" langfuse-minio
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" | grep -q 'langfuse-minio .*PASS'
  grep -q '^docker create --network none --name dhg-restore-drill-langfuse-minio -v /data --env-file .* cgr.dev/chainguard/minio:latest server /data$' "$SHIM_LOG"
  ! grep -q 'shim-secret' "$SHIM_LOG"
  grep -q '^docker exec dhg-restore-drill-langfuse-minio mc ls local/$' "$SHIM_LOG"
  grep -q '^docker rm -f -v dhg-restore-drill-langfuse-minio$' "$SHIM_LOG"
  [ "$(find "$TEST_ROOT" -name '*.env-file*' | wc -l)" -eq 0 ]      # env-file removed after create
  # the member count is taken BEFORE the server starts (MinIO rewrites .minio.sys on boot)
  count_line="$(grep -n '^docker cp dhg-restore-drill-langfuse-minio:/data -$' "$SHIM_LOG" | head -1 | cut -d: -f1)"
  start_line="$(grep -n '^docker start dhg-restore-drill-langfuse-minio$' "$SHIM_LOG" | head -1 | cut -d: -f1)"
  [ -n "$count_line" ] && [ -n "$start_line" ] && [ "$count_line" -lt "$start_line" ]
}

@test "minio drill uses the target's own data path (plane-minio serves and verifies /export, not /data)" {
  install_minio_shim
  sed -i 's#dhg-langfuse-minio:/data#plane-app-plane-minio-1:/export#; s#dhg-restore-drill-langfuse-minio#dhg-restore-drill-plane-minio#g; s#-v /data --env-file#-v /export --env-file#' "$TEST_ROOT/bin/docker"
  sed -i 's#--context dh40801 ##' "$TEST_ROOT/bin/docker"
  mv "$TEST_ROOT/tree/data" "$TEST_ROOT/tree/export"; sed -i 's#-cf - data#-cf - export#g' "$TEST_ROOT/bin/docker"
  sed -i 's#cp dhg-restore-drill-plane-minio:/data - #cp dhg-restore-drill-plane-minio:/export - #' "$TEST_ROOT/bin/docker"
  "$BACKUP" --target plane-minio --no-offsite
  run "$DRILL" plane-minio
  [ "$status" -eq 0 ]
  grep -q ' minio/minio:latest server /export$\| cgr.dev/chainguard/minio:latest server /export$' "$SHIM_LOG"
  grep -q '^docker cp dhg-restore-drill-plane-minio:/export -$' "$SHIM_LOG"
}

install_volumes_shim() {
  mkdir -p "$TEST_ROOT/tree/data/vector_db" "$TEST_ROOT/tree/exports"
  printf 'db' > "$TEST_ROOT/tree/data/webui.db"; printf 'v' > "$TEST_ROOT/tree/data/vector_db/index"
  printf 'g' > "$TEST_ROOT/tree/grafana.db"; printf 'e' > "$TEST_ROOT/tree/exports/report.pdf"
  install_shim docker <<'SHIM'
#!/usr/bin/env bash
echo "docker $*" >> "$SHIM_LOG"
case " $* " in
  *" version "*) exit 0 ;;
  *" inspect "*) echo "shim-image:1" ;;
  *" exec "*" tar "*)
    args=(); skip=0
    for a in "$@"; do
      [ "$skip" = 1 ] && { args+=("$SHIM_TREE"); skip=0; continue; }
      case "$a" in exec|tar) continue ;; -C) args+=(-C); skip=1 ;; *) args+=("$a") ;; esac
    done
    args=("${args[@]:1}"); exec tar "${args[@]}" ;;
  # ---- drill side: sqlite integrity check in the prebuilt image ----
  *" run --rm -i dhg-drill-sqlite:3.20 "*) cat > /dev/null; printf '%s\n' "${DRILL_SQLITE:-ok}" ;;
  *) echo "unexpected docker call: $*" >&2; exit 9 ;;
esac
SHIM
  export SHIM_TREE="$TEST_ROOT/tree"
}

@test "volumes drill: every archive lists exactly its manifest member count and grafana.db passes PRAGMA integrity_check in the sqlite drill image" {
  install_volumes_shim
  "$BACKUP" --target volumes --no-offsite
  run "$DRILL" volumes
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" | grep -q 'volumes .*PASS'
  grep -q '^docker run --rm -i dhg-drill-sqlite:3.20 sh -c cat > /x.db && sqlite3 /x.db "PRAGMA integrity_check"$' "$SHIM_LOG"
}

@test "volumes drill: a grafana.db that fails PRAGMA integrity_check fails the drill" {
  install_volumes_shim
  "$BACKUP" --target volumes --no-offsite
  export DRILL_SQLITE='*** in database main *** Page 3: btreeInitPage() returns error code 11'
  run "$DRILL" volumes
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'integrity_check:'
  ! grep -q 'backup_restore_drill_success_timestamp{name="volumes"}' "$BACKUP_TEXTFILE"
}
