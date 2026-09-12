#!/usr/bin/env bats
# Tests for observability/scripts/backup-all.sh — the nightly orchestrator.
# Everything runs in a temp tree; `docker` and `rsync` are replaced by shims on
# PATH so no container, host or NAS is touched.
#
# Run: python3 observability/tests/bats-tdd-reporter.py observability/tests/backup-all.bats

SCRIPT="$BATS_TEST_DIRNAME/../scripts/backup-all.sh"

setup() {
  TEST_ROOT="$(mktemp -d)"
  export BACKUP_ROOT="$TEST_ROOT/nightly"
  export BACKUP_STATE_DIR="$TEST_ROOT/state"
  export BACKUP_TEXTFILE="$TEST_ROOT/backups.prom"
  export BACKUP_LOCK="$TEST_ROOT/lock"
  export BACKUP_GPG_PASSPHRASE="bats-fixed-passphrase"
  export GNUPGHOME="$TEST_ROOT/gnupg"
  export BACKUP_MIN_FREE_GB=0
  mkdir -p "$BACKUP_ROOT" "$BACKUP_STATE_DIR" "$GNUPGHOME" "$TEST_ROOT/bin"
  chmod 700 "$GNUPGHOME"
  export PATH="$TEST_ROOT/bin:$PATH"
}

teardown() {
  rm -rf "$TEST_ROOT"
}

@test "--dry-run exits 0 and prints one plan line per data target plus the offsite mirror (14)" {
  run "$SCRIPT" --dry-run
  [ "$status" -eq 0 ]
  [ "$(printf '%s\n' "$output" | grep -c '^plan ')" -eq 14 ]
}

@test "an unknown --target id exits 2 before doing anything (no plan, no run, no mirror)" {
  run "$SCRIPT" --target bogus --dry-run
  [ "$status" -eq 2 ]
  printf '%s\n' "$output" | grep -q 'unknown target: bogus'
  ! printf '%s\n' "$output" | grep -q '^plan '
}

@test "a second run exits 75 within 2 s while another run holds the lock" {
  exec 9>"$BACKUP_LOCK"; flock -x 9
  start=$(date +%s)
  run "$SCRIPT" --dry-run
  end=$(date +%s)
  exec 9>&-
  [ "$status" -eq 75 ]
  [ $((end - start)) -le 2 ]
  printf '%s\n' "$output" | grep -qi 'already running'
}

@test "--target config produces an encrypted tar of the listed files, a manifest written last, and success in the textfile" {
  mkdir -p "$TEST_ROOT/etc"; printf 'A=1\n' > "$TEST_ROOT/etc/one.env"; printf 'B=2\n' > "$TEST_ROOT/etc/two.env"
  printf '%s\n%s\n' "$TEST_ROOT/etc/one.env" "$TEST_ROOT/etc/two.env" > "$TEST_ROOT/config.list"
  export BACKUP_CONFIG_LIST="$TEST_ROOT/config.list"
  run "$SCRIPT" --target config --no-offsite
  [ "$status" -eq 0 ]
  rundir="$(ls -d "$BACKUP_ROOT"/config/*/ | head -1)"; rundir="${rundir%/}"
  [[ "$(basename "$rundir")" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]
  [ -f "$rundir/config.tar.gpg" ]
  [ -f "$rundir/manifest.json" ]
  [ "$(jq -r '.target' "$rundir/manifest.json")" = "config" ]
  [ "$(jq -r '.files["config.tar.gpg"].bytes' "$rundir/manifest.json")" -gt 0 ]
  # archive decrypts and holds both files (paths relative to /)
  source "$BATS_TEST_DIRNAME/../scripts/backup-lib.sh"
  bl_gpg_decrypt < "$rundir/config.tar.gpg" | tar -t | grep -q 'etc/one.env$'
  bl_gpg_decrypt < "$rundir/config.tar.gpg" | tar -t | grep -q 'etc/two.env$'
  grep -q '^backup_last_attempt_timestamp{name="config"} ' "$BACKUP_TEXTFILE"
  grep -q '^backup_last_success_timestamp{name="config"} ' "$BACKUP_TEXTFILE"
  [ "$(ls "$BACKUP_ROOT"/config | grep -c '^tmp-')" -eq 0 ]
}

@test "a manifest write failure (jq broken) fails the target: no success stamp, no run dir, exit 1" {
  mkdir -p "$TEST_ROOT/etc"; printf 'A=1\n' > "$TEST_ROOT/etc/one.env"
  printf '%s\n' "$TEST_ROOT/etc/one.env" > "$TEST_ROOT/config.list"; export BACKUP_CONFIG_LIST="$TEST_ROOT/config.list"
  printf '#!/usr/bin/env bash\necho "jq: fake failure" >&2; exit 5\n' > "$TEST_ROOT/bin/jq"; chmod +x "$TEST_ROOT/bin/jq"
  run "$SCRIPT" --target config --no-offsite
  rm -f "$TEST_ROOT/bin/jq"
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'target config FAILED'
  ! grep -q 'backup_last_success_timestamp{name="config"}' "$BACKUP_TEXTFILE"
  [ "$(ls -A "$BACKUP_ROOT/config" 2>/dev/null | wc -l)" -eq 0 ]
}

@test "a tar failure inside the config producer fails the target (pipeline status is not discarded)" {
  mkdir -p "$TEST_ROOT/etc"; printf 'A=1\n' > "$TEST_ROOT/etc/one.env"
  printf '%s\n' "$TEST_ROOT/etc/one.env" > "$TEST_ROOT/config.list"; export BACKUP_CONFIG_LIST="$TEST_ROOT/config.list"
  printf '#!/usr/bin/env bash\necho "tar: fake failure" >&2; exit 2\n' > "$TEST_ROOT/bin/tar"; chmod +x "$TEST_ROOT/bin/tar"
  run "$SCRIPT" --target config --no-offsite
  rm -f "$TEST_ROOT/bin/tar"
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'tar: fake failure'
  printf '%s\n' "$output" | grep -q 'target config FAILED'
  [ "$(ls -A "$BACKUP_ROOT/config" 2>/dev/null | wc -l)" -eq 0 ]
}

@test "an archive that fails its integrity check (pg_restore --list) fails the target: no run dir, attempt but no success" {
  install_pg_docker_shim
  export PG_RESTORE_LIST_RC=1
  run "$SCRIPT" --target eval-db --no-offsite
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'integrity check failed'
  printf '%s\n' "$output" | grep -q 'target eval-db FAILED'
  grep -q '^backup_last_attempt_timestamp{name="eval-db"} ' "$BACKUP_TEXTFILE"
  ! grep -q 'backup_last_success_timestamp{name="eval-db"}' "$BACKUP_TEXTFILE"
  [ "$(ls -A "$BACKUP_ROOT/eval-db" 2>/dev/null | wc -l)" -eq 0 ]
}

@test "an unreadable file in the config list fails the target loudly: exit 1, attempt bumped, no success, no run dir left" {
  mkdir -p "$TEST_ROOT/etc"; printf 'A=1\n' > "$TEST_ROOT/etc/one.env"
  printf '%s\n%s\n' "$TEST_ROOT/etc/one.env" "$TEST_ROOT/etc/missing.env" > "$TEST_ROOT/config.list"
  export BACKUP_CONFIG_LIST="$TEST_ROOT/config.list"
  run "$SCRIPT" --target config --no-offsite
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'not readable: .*missing.env'
  printf '%s\n' "$output" | grep -q 'target config FAILED'
  grep -q '^backup_last_attempt_timestamp{name="config"} ' "$BACKUP_TEXTFILE"
  ! grep -q 'backup_last_success_timestamp{name="config"}' "$BACKUP_TEXTFILE"
  [ -z "$(ls -A "$BACKUP_ROOT/config" 2>/dev/null)" ]
}

# docker shim: answers the exact calls the pg producer makes and records them
install_pg_docker_shim() {
  cat > "$TEST_ROOT/bin/docker" <<'SHIM'
#!/usr/bin/env bash
echo "docker $*" >> "$SHIM_LOG"
case " $* " in
  *" psql "*)
    # snapshot-consistent session: one line per statement the producer sends
    while IFS= read -r line; do
      case "$line" in
        *pg_export_snapshot*) echo "00000003-0000000A-1" ;;
        *pg_stat_user_tables*) printf 'public.foo=3\npublic.bar=0\n' ;;
        *__END__*) echo "__END__" ;;
      esac
    done ;;
  *" pg_dump "*)   [[ " $* " == *" --snapshot=00000003-0000000A-1 "* ]] || { echo "no snapshot" >&2; exit 9; }
                   printf 'PGDMP-fake-%s' "$*" ;;
  *" pg_dumpall "*) printf -- '-- roles\nCREATE ROLE fake;\n' ;;
  *" inspect "*)   echo "pgvector/pgvector:pg15" ;;
  *" run "*" pg_restore --list "*) [ "${PG_RESTORE_LIST_RC:-0}" = 0 ] || echo "pg_restore: error: did not find magic string" >&2; exit "${PG_RESTORE_LIST_RC:-0}" ;;   # archive integrity check runs in the source image
  *) echo "unexpected docker call: $*" >&2; exit 9 ;;
esac
SHIM
  chmod +x "$TEST_ROOT/bin/docker"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$TEST_ROOT/bin/pg_restore"; chmod +x "$TEST_ROOT/bin/pg_restore"
  export SHIM_LOG="$TEST_ROOT/shim.log"; : > "$SHIM_LOG"
}

@test "pg producer dumps each database with pg_dump --snapshot from one REPEATABLE READ session, dumps roles, and records row counts in the manifest" {
  install_pg_docker_shim
  run "$SCRIPT" --target eval-db --no-offsite       # evalviewer + evalviewer_test
  [ "$status" -eq 0 ]
  rundir="$(ls -d "$BACKUP_ROOT"/eval-db/*/ | head -1)"; rundir="${rundir%/}"
  [ -f "$rundir/evalviewer.dump.gpg" ]
  [ -f "$rundir/evalviewer_test.dump.gpg" ]
  [ -f "$rundir/roles.sql.gpg" ]
  [ -f "$rundir/manifest.json" ]
  [ "$(jq -r '.counts.evalviewer["public.foo"]' "$rundir/manifest.json")" = "3" ]
  [ "$(jq -r '.counts.evalviewer_test["public.bar"]' "$rundir/manifest.json")" = "0" ]
  [ "$(jq -r '.image' "$rundir/manifest.json")" != "null" ]
  source "$BATS_TEST_DIRNAME/../scripts/backup-lib.sh"
  bl_gpg_decrypt < "$rundir/evalviewer.dump.gpg" | grep -q 'PGDMP-fake-.*-d evalviewer'
  bl_gpg_decrypt < "$rundir/roles.sql.gpg" | grep -q 'CREATE ROLE fake'
  grep -q 'exec -i dhg-eval-db psql' "$SHIM_LOG"
  grep -q 'pg_dump -Fc --snapshot=00000003-0000000A-1 -U evalviewer -d evalviewer' "$SHIM_LOG"
  grep -q 'pg_dumpall --roles-only -U evalviewer' "$SHIM_LOG"
  ! grep -q -- '--context' "$SHIM_LOG"                  # local target: no context flag
}

install_clickhouse_docker_shim() {
  cat > "$TEST_ROOT/bin/docker" <<'SHIM'
#!/usr/bin/env bash
echo "docker $*" >> "$SHIM_LOG"
# producer calls: docker --context dh40801 exec <c> sh -c '<script>' sh <user> <query>
q="${@: -1}"
case " $* " in
  *" version "*) exit 0 ;;                       # context reachability probe
  *" inspect "*) echo "clickhouse/clickhouse-server:25.12" ;;
  *" exec "*)
    case "$q" in
      *create_table_query*) printf 'CREATE TABLE default.traces (id String) ENGINE = ReplacingMergeTree ORDER BY id\nCREATE VIEW default.analytics_traces AS SELECT * FROM default.traces\n' ;;
      *"FROM system.tables"*) printf 'scores\ntraces\n' ;;
      *"FORMAT Native"*) printf 'NATIVE-fake-%s' "$q" ;;
      *) echo "unexpected query: $q" >&2; exit 9 ;;
    esac ;;
  *) echo "unexpected docker call: $*" >&2; exit 9 ;;
esac
SHIM
  chmod +x "$TEST_ROOT/bin/docker"
  export SHIM_LOG="$TEST_ROOT/shim.log"; : > "$SHIM_LOG"
}

@test "clickhouse producer saves the DDL of every default.* object and one gzipped Native stream per non-View table via the dh40801 context" {
  install_clickhouse_docker_shim
  run "$SCRIPT" --target langfuse-clickhouse --no-offsite
  [ "$status" -eq 0 ]
  rundir="$(ls -d "$BACKUP_ROOT"/langfuse-clickhouse/*/ | head -1)"; rundir="${rundir%/}"
  [ -f "$rundir/ddl.sql.gpg" ]
  [ -f "$rundir/traces.native.gz.gpg" ]
  [ -f "$rundir/scores.native.gz.gpg" ]
  [ "$(jq -r '.tables' "$rundir/manifest.json")" = "2" ]
  [ "$(jq -r '.image' "$rundir/manifest.json")" = "clickhouse/clickhouse-server:25.12" ]
  source "$BATS_TEST_DIRNAME/../scripts/backup-lib.sh"
  bl_gpg_decrypt < "$rundir/ddl.sql.gpg" | grep -q 'CREATE VIEW default.analytics_traces'
  bl_gpg_decrypt < "$rundir/traces.native.gz.gpg" | gunzip | grep -q 'NATIVE-fake-SELECT \* FROM default.traces FORMAT Native'
  grep -q '^docker --context dh40801 exec dhg-langfuse-clickhouse ' "$SHIM_LOG"
  grep -q '"\$CLICKHOUSE_PASSWORD"' "$SHIM_LOG"   # argv carries the unexpanded reference: the value is read inside the container
}

# docker shim for `cp <container>:<path> -` : streams a real tar of $SHIM_TREE
install_cp_docker_shim() {
  mkdir -p "$TEST_ROOT/tree/langfuse/obj1" "$TEST_ROOT/tree/.minio.sys/buckets"
  printf 'x' > "$TEST_ROOT/tree/langfuse/obj1/xl.meta"; printf 'y' > "$TEST_ROOT/tree/.minio.sys/buckets/meta"
  cat > "$TEST_ROOT/bin/docker" <<'SHIM'
#!/usr/bin/env bash
echo "docker $*" >> "$SHIM_LOG"
case " $* " in
  *" version "*) exit 0 ;;                       # context reachability probe
  *" inspect "*) echo "cgr.dev/chainguard/minio:latest" ;;
  *" cp "*":"*" - "*) tar -C "$SHIM_TREE" -cf - . ;;
  *) echo "unexpected docker call: $*" >&2; exit 9 ;;
esac
SHIM
  chmod +x "$TEST_ROOT/bin/docker"
  export SHIM_LOG="$TEST_ROOT/shim.log" SHIM_TREE="$TEST_ROOT/tree"; : > "$SHIM_LOG"
}

@test "minio producer streams the whole data tree with docker cp and records the tar member count" {
  install_cp_docker_shim
  run "$SCRIPT" --target langfuse-minio --no-offsite
  [ "$status" -eq 0 ]
  rundir="$(ls -d "$BACKUP_ROOT"/langfuse-minio/*/ | head -1)"; rundir="${rundir%/}"
  [ -f "$rundir/data.tar.gpg" ]
  expected="$(tar -C "$SHIM_TREE" -cf - . | tar -t | wc -l)"
  [ "$(jq -r '.members' "$rundir/manifest.json")" = "$expected" ]
  [ "$(jq -r '.image' "$rundir/manifest.json")" = "cgr.dev/chainguard/minio:latest" ]
  source "$BATS_TEST_DIRNAME/../scripts/backup-lib.sh"
  bl_gpg_decrypt < "$rundir/data.tar.gpg" | tar -t | grep -q 'langfuse/obj1/xl.meta$'
  grep -q '^docker --context dh40801 cp dhg-langfuse-minio:/data -$' "$SHIM_LOG"
}

# docker shim for `exec <c> tar -C <dir> -cf - [--exclude=...] <base>` : runs real tar on $SHIM_TREE
install_tar_docker_shim() {
  mkdir -p "$TEST_ROOT/tree/data/cache/models" "$TEST_ROOT/tree/data/vector_db" "$TEST_ROOT/tree/exports"
  printf 'db' > "$TEST_ROOT/tree/data/webui.db"; printf 'big' > "$TEST_ROOT/tree/data/cache/models/blob"; printf 'v' > "$TEST_ROOT/tree/data/vector_db/index"
  printf 'g' > "$TEST_ROOT/tree/grafana.db"; printf 'e' > "$TEST_ROOT/tree/exports/report.pdf"
  cat > "$TEST_ROOT/bin/docker" <<'SHIM'
#!/usr/bin/env bash
echo "docker $*" >> "$SHIM_LOG"
case " $* " in
  *" inspect "*) echo "shim-image:1" ;;
  *" exec "*" tar "*)
    args=(); skip=0
    for a in "$@"; do
      [ "$skip" = 1 ] && { args+=("$SHIM_TREE"); skip=0; continue; }
      case "$a" in exec|tar) continue ;; -C) args+=(-C); skip=1 ;; *) args+=("$a") ;; esac
    done
    args=("${args[@]:1}")    # drop the container name
    exec tar "${args[@]}" ;;
  *) echo "unexpected docker call: $*" >&2; exit 9 ;;
esac
SHIM
  chmod +x "$TEST_ROOT/bin/docker"
  export SHIM_LOG="$TEST_ROOT/shim.log" SHIM_TREE="$TEST_ROOT/tree"; : > "$SHIM_LOG"
}

@test "volume producer tars each source inside its container, honours the cache exclusion for open-webui, and records members per archive" {
  install_tar_docker_shim
  run "$SCRIPT" --target volumes --no-offsite
  [ "$status" -eq 0 ]
  rundir="$(ls -d "$BACKUP_ROOT"/volumes/*/ | head -1)"; rundir="${rundir%/}"
  [ -f "$rundir/dhg-grafana.tar.gpg" ]
  [ -f "$rundir/dhg-registry-api.tar.gpg" ]
  [ -f "$rundir/dhg-open-webui.tar.gpg" ]
  source "$BATS_TEST_DIRNAME/../scripts/backup-lib.sh"
  bl_gpg_decrypt < "$rundir/dhg-open-webui.tar.gpg" | tar -t | grep -q 'data/webui.db$'
  ! bl_gpg_decrypt < "$rundir/dhg-open-webui.tar.gpg" | tar -t | grep -q 'cache'
  bl_gpg_decrypt < "$rundir/dhg-grafana.tar.gpg" | tar -t | grep -qx 'grafana.db'
  [ "$(jq -r '.members["dhg-open-webui"]' "$rundir/manifest.json")" = "$(bl_gpg_decrypt < "$rundir/dhg-open-webui.tar.gpg" | tar -t | wc -l)" ]
  grep -q '^docker exec dhg-grafana tar -C /var/lib/grafana -cf - grafana.db$' "$SHIM_LOG"
  grep -q '^docker exec dhg-registry-api tar -C / -cf - exports$' "$SHIM_LOG"
  grep -q '^docker exec dhg-open-webui tar -C /app/backend -cf - --exclude=data/cache data$' "$SHIM_LOG"
}

@test "an unreachable docker context fails its targets after one probe, with no dump attempted and attempt stamps bumped" {
  cat > "$TEST_ROOT/bin/docker" <<'SHIM'
#!/usr/bin/env bash
echo "docker $*" >> "$SHIM_LOG"
case " $* " in
  *" --context dh40801 version "*) echo "error during connect: dial tcp 10.0.0.179:22: i/o timeout" >&2; exit 1 ;;
  *) echo "unexpected docker call: $*" >&2; exit 9 ;;
esac
SHIM
  chmod +x "$TEST_ROOT/bin/docker"; export SHIM_LOG="$TEST_ROOT/shim.log"; : > "$SHIM_LOG"
  run "$SCRIPT" --target langfuse-postgres --no-offsite
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'context dh40801 unreachable'
  [ "$(grep -c '^docker --context dh40801 version' "$SHIM_LOG")" -eq 1 ]
  ! grep -q ' exec ' "$SHIM_LOG"
  grep -q '^backup_last_attempt_timestamp{name="langfuse-postgres"} ' "$BACKUP_TEXTFILE"
  ! grep -q 'backup_last_success_timestamp{name="langfuse-postgres"}' "$BACKUP_TEXTFILE"
  [ -z "$(ls -A "$BACKUP_ROOT/langfuse-postgres" 2>/dev/null)" ]
}

@test "after the targets, the tree is mirrored to the NAS with rsync over the dedicated key, the offsite stamp is written, and local retention is pruned" {
  mkdir -p "$TEST_ROOT/etc"; printf 'A=1\n' > "$TEST_ROOT/etc/one.env"
  printf '%s\n' "$TEST_ROOT/etc/one.env" > "$TEST_ROOT/config.list"; export BACKUP_CONFIG_LIST="$TEST_ROOT/config.list"
  cat > "$TEST_ROOT/bin/rsync" <<'SHIM'
#!/usr/bin/env bash
echo "rsync $*" >> "$SHIM_LOG"; exit 0
SHIM
  chmod +x "$TEST_ROOT/bin/rsync"; export SHIM_LOG="$TEST_ROOT/shim.log"; : > "$SHIM_LOG"
  export BACKUP_NAS_KEY="$TEST_ROOT/nas_key"
  # a 40-day-old completed weekday run that retention must remove
  old="$(date -u -d '2026-08-04T03:30:00Z' +%Y%m%dT%H%M%SZ)"   # Tuesday
  mkdir -p "$BACKUP_ROOT/config/$old"; printf '{}' > "$BACKUP_ROOT/config/$old/manifest.json"
  run "$SCRIPT" --target config
  [ "$status" -eq 0 ]
  grep -q "^rsync -a --delete --delete-delay --delay-updates --exclude=tmp-\* --exclude=.state -e ssh -p 22 -i $TEST_ROOT/nas_key -o IdentitiesOnly=yes -o BatchMode=yes -o LogLevel=ERROR $BACKUP_ROOT/ aifactory-backup@10.0.0.250::aifactory-backups/$" "$SHIM_LOG"
  grep -q '^backup_offsite_last_success_timestamp ' "$BACKUP_TEXTFILE"
  [ ! -d "$BACKUP_ROOT/config/$old" ]
  [ "$(ls -d "$BACKUP_ROOT"/config/*/ | wc -l)" -eq 1 ]
}

@test "a failed mirror leaves the local run intact, writes no offsite stamp, and makes the run exit 1" {
  mkdir -p "$TEST_ROOT/etc"; printf 'A=1\n' > "$TEST_ROOT/etc/one.env"
  printf '%s\n' "$TEST_ROOT/etc/one.env" > "$TEST_ROOT/config.list"; export BACKUP_CONFIG_LIST="$TEST_ROOT/config.list"
  printf '#!/usr/bin/env bash\necho "rsync: connection refused" >&2; exit 10\n' > "$TEST_ROOT/bin/rsync"; chmod +x "$TEST_ROOT/bin/rsync"
  run "$SCRIPT" --target config
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'offsite mirror FAILED'
  grep -q '^backup_last_success_timestamp{name="config"} ' "$BACKUP_TEXTFILE"
  ! grep -q '^backup_offsite_last_success_timestamp' "$BACKUP_TEXTFILE"
  [ "$(ls -d "$BACKUP_ROOT"/config/*/ | wc -l)" -eq 1 ]
}

@test "without BACKUP_GPG_PASSPHRASE the run aborts before any target: exit 1, nothing written, no attempt stamped" {
  mkdir -p "$TEST_ROOT/etc"; printf 'A=1\n' > "$TEST_ROOT/etc/one.env"
  printf '%s\n' "$TEST_ROOT/etc/one.env" > "$TEST_ROOT/config.list"; export BACKUP_CONFIG_LIST="$TEST_ROOT/config.list"
  unset BACKUP_GPG_PASSPHRASE
  run "$SCRIPT" --target config --no-offsite
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'BACKUP_GPG_PASSPHRASE not set'
  [ -z "$(ls -A "$BACKUP_ROOT/config" 2>/dev/null)" ]
  [ ! -f "$BACKUP_TEXTFILE" ]
}

@test "too little free space under the backup root aborts before any target" {
  mkdir -p "$TEST_ROOT/etc"; printf 'A=1\n' > "$TEST_ROOT/etc/one.env"
  printf '%s\n' "$TEST_ROOT/etc/one.env" > "$TEST_ROOT/config.list"; export BACKUP_CONFIG_LIST="$TEST_ROOT/config.list"
  export BACKUP_MIN_FREE_GB=999999
  run "$SCRIPT" --target config --no-offsite
  [ "$status" -eq 1 ]
  printf '%s\n' "$output" | grep -q 'GB free'
  [ -z "$(ls -A "$BACKUP_ROOT/config" 2>/dev/null)" ]
  [ ! -f "$BACKUP_TEXTFILE" ]
}
