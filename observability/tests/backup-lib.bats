#!/usr/bin/env bats
# Tests for observability/scripts/backup-lib.sh — the pure functions behind
# backup-all.sh and restore-drill.sh. No docker, no network, no /mnt/4tb:
# every test works in a temp dir with a fixed passphrase.
#
# Run: python3 observability/tests/bats-tdd-reporter.py observability/tests/backup-lib.bats

setup() {
  TEST_ROOT="$(mktemp -d)"
  export BACKUP_ROOT="$TEST_ROOT/nightly"
  export BACKUP_STATE_DIR="$TEST_ROOT/state"
  export BACKUP_TEXTFILE="$TEST_ROOT/backups.prom"
  export BACKUP_GPG_PASSPHRASE="bats-fixed-passphrase"
  export GNUPGHOME="$TEST_ROOT/gnupg"
  mkdir -p "$BACKUP_ROOT" "$BACKUP_STATE_DIR" "$GNUPGHOME"
  chmod 700 "$GNUPGHOME"
  # shellcheck source=../scripts/backup-lib.sh
  source "$BATS_TEST_DIRNAME/../scripts/backup-lib.sh"
}

teardown() {
  rm -rf "$TEST_ROOT"
}

@test "bl_run_id is a UTC stamp of the form YYYYMMDDTHHMMSSZ" {
  run bl_run_id
  [ "$status" -eq 0 ]
  [[ "$output" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]
}

@test "bl_is_sunday recognises a Sunday run id and rejects a Monday" {
  run bl_is_sunday 20260906T033000Z   # 2026-09-06 is a Sunday
  [ "$status" -eq 0 ]
  run bl_is_sunday 20260907T033000Z   # Monday
  [ "$status" -ne 0 ]
}

@test "bl_gpg_encrypt / bl_gpg_decrypt round-trip a byte stream, wrong passphrase fails, no passphrase refuses" {
  head -c 4096 /dev/urandom > "$TEST_ROOT/in.bin"
  bl_gpg_encrypt < "$TEST_ROOT/in.bin" > "$TEST_ROOT/in.bin.gpg"
  [ -s "$TEST_ROOT/in.bin.gpg" ]
  bl_gpg_decrypt < "$TEST_ROOT/in.bin.gpg" > "$TEST_ROOT/out.bin"
  cmp "$TEST_ROOT/in.bin" "$TEST_ROOT/out.bin"
  BACKUP_GPG_PASSPHRASE=wrong run bl_gpg_decrypt < "$TEST_ROOT/in.bin.gpg"
  [ "$status" -ne 0 ]
  unset BACKUP_GPG_PASSPHRASE
  run bl_gpg_encrypt < /dev/null
  [ "$status" -ne 0 ]
}

@test "bl_write_manifest writes valid JSON with the given fields plus bytes and sha256 per file" {
  d="$TEST_ROOT/run"; mkdir -p "$d"
  printf 'abc' > "$d/a.gpg"; printf 'defg' > "$d/b.gpg"
  bl_write_manifest "$d" target=registry-db run=20260906T033000Z image=pgvector/pgvector:pg15 duration_seconds=12 \
    counts='{"public.foo":3,"public.bar":0}'
  [ -f "$d/manifest.json" ]
  run jq -r '.target, .run, .image, .duration_seconds, .counts["public.foo"], (.files|length), .files["a.gpg"].bytes, .files["b.gpg"].sha256' "$d/manifest.json"
  [ "${lines[0]}" = "registry-db" ]
  [ "${lines[1]}" = "20260906T033000Z" ]
  [ "${lines[2]}" = "pgvector/pgvector:pg15" ]
  [ "${lines[3]}" = "12" ]
  [ "${lines[4]}" = "3" ]
  [ "${lines[5]}" = "2" ]
  [ "${lines[6]}" = "3" ]
  [ "${lines[7]}" = "$(printf 'defg' | sha256sum | cut -d' ' -f1)" ]
}

@test "bl_state_set + bl_write_textfile emit HELP/TYPE and one labelled series per recorded state, atomically, mode 0644" {
  bl_state_set registry-db attempt 1700000000
  bl_state_set registry-db success 1700000010
  bl_state_set registry-db size_bytes 12345
  bl_state_set registry-db duration_seconds 10
  bl_state_set registry-db drill_success 1700000050
  bl_state_set medkb-db attempt 1700000020
  bl_state_set offsite success 1700000030
  bl_write_textfile
  bl_write_textfile
  [ -f "$BACKUP_TEXTFILE" ]
  [ "$(stat -c '%a' "$BACKUP_TEXTFILE")" = "644" ]
  [ "$(ls "$TEST_ROOT"/backups.prom.* 2>/dev/null | wc -l)" = "0" ]
  [ "$(grep -c '^# HELP backup_' "$BACKUP_TEXTFILE")" -ge 6 ]
  [ "$(grep -c '^# TYPE backup_.* gauge$' "$BACKUP_TEXTFILE")" -ge 6 ]
  grep -q '^backup_last_attempt_timestamp{name="registry-db"} 1700000000$' "$BACKUP_TEXTFILE"
  grep -q '^backup_last_success_timestamp{name="registry-db"} 1700000010$' "$BACKUP_TEXTFILE"
  grep -q '^backup_last_size_bytes{name="registry-db"} 12345$' "$BACKUP_TEXTFILE"
  grep -q '^backup_last_duration_seconds{name="registry-db"} 10$' "$BACKUP_TEXTFILE"
  grep -q '^backup_restore_drill_success_timestamp{name="registry-db"} 1700000050$' "$BACKUP_TEXTFILE"
  grep -q '^backup_last_attempt_timestamp{name="medkb-db"} 1700000020$' "$BACKUP_TEXTFILE"
  grep -q '^backup_offsite_last_success_timestamp 1700000030$' "$BACKUP_TEXTFILE"
  # medkb-db never succeeded: no success series (absent(), never a 0)
  ! grep -q 'backup_last_success_timestamp{name="medkb-db"}' "$BACKUP_TEXTFILE"
  # idempotent: one series per target/metric after two writes
  [ "$(grep -c 'backup_last_attempt_timestamp{name="registry-db"}' "$BACKUP_TEXTFILE")" = "1" ]
}

# helper: make a run dir dated N days before NOW (epoch), optionally with a manifest
mkrun() { # id days_ago with_manifest(1|0)
  local ts run; ts=$(( NOW - $2*86400 )); run="$(date -u -d "@$ts" +%Y%m%dT%H%M%SZ)"
  mkdir -p "$BACKUP_ROOT/$1/$run"
  [ "$3" = 1 ] && printf '{}' > "$BACKUP_ROOT/$1/$run/manifest.json"
  printf '%s' "$run"
}

@test "bl_prune_local keeps <30d, drops old weekdays, keeps Sundays <84d, drops Sundays >84d, and never touches manifest-less/tmp/.state/outside dirs" {
  NOW=$(date -u -d '2026-09-11T03:30:00Z' +%s)      # a Friday
  keep_recent="$(mkrun registry-db 10 1)"
  drop_weekday="$(mkrun registry-db 31 1)"          # 2026-08-11 Tuesday
  keep_sunday="$(mkrun registry-db 47 1)"           # 2026-07-26 Sunday
  drop_old_sunday="$(mkrun registry-db 89 1)"       # 2026-06-14 Sunday
  half="$(mkrun medkb-db 200 0)"                     # old but no manifest: not ours
  mkdir -p "$BACKUP_ROOT/medkb-db/tmp-20260101T000000Z"; printf '{}' > "$BACKUP_ROOT/medkb-db/tmp-20260101T000000Z/manifest.json"
  mkdir -p "$BACKUP_ROOT/.state/medkb-db"; printf '1' > "$BACKUP_ROOT/.state/medkb-db/attempt"
  mkdir -p "$TEST_ROOT/outside/20250101T000000Z"; printf '{}' > "$TEST_ROOT/outside/20250101T000000Z/manifest.json"
  bl_prune_local "$NOW"
  [ -d "$BACKUP_ROOT/registry-db/$keep_recent" ]
  [ ! -d "$BACKUP_ROOT/registry-db/$drop_weekday" ]
  [ -d "$BACKUP_ROOT/registry-db/$keep_sunday" ]
  [ ! -d "$BACKUP_ROOT/registry-db/$drop_old_sunday" ]
  [ -d "$BACKUP_ROOT/medkb-db/$half" ]
  [ -d "$BACKUP_ROOT/medkb-db/tmp-20260101T000000Z" ]
  [ -f "$BACKUP_ROOT/.state/medkb-db/attempt" ]
  [ -d "$TEST_ROOT/outside/20250101T000000Z" ]
}

@test "bl_latest_run returns the newest run dir that has a manifest, fails when none" {
  NOW=$(date -u +%s)
  mkrun portage-db 3 1 >/dev/null
  b="$(mkrun portage-db 1 1)"
  mkrun portage-db 0 0 >/dev/null     # newest but no manifest
  run bl_latest_run portage-db
  [ "$status" -eq 0 ]
  [ "$output" = "$BACKUP_ROOT/portage-db/$b" ]
  run bl_latest_run never-ran
  [ "$status" -ne 0 ]
}

@test "bl_targets lists 13 unique data targets with known kinds, and bl_target_field resolves fields" {
  run bl_targets
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 13 ]
  for l in "${lines[@]}"; do [ "$(awk -F'|' '{print NF}' <<<"$l")" -eq 5 ]; done
  [ -z "$(bl_targets | cut -d'|' -f1 | sort | uniq -d)" ]
  [ "$(bl_targets | cut -d'|' -f2 | sort -u | tr '\n' ' ')" = "clickhouse files minio pg volume " ]
  [ "$(bl_targets | cut -d'|' -f3 | sort | uniq -c | awk '{print $2"="$1}' | tr '\n' ' ')" = "dh40801=3 local=10 " ]
  run bl_target_field registry-db container; [ "$output" = "dhg-registry-db" ]
  run bl_target_field langfuse-minio ctx;    [ "$output" = "dh40801" ]
  run bl_target_field plane-db extra;        [ "$output" = "plane:plane:/var/run/postgresql" ]
  run bl_target_field nope kind;             [ "$status" -ne 0 ]
}
