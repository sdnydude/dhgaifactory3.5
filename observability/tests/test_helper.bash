# Shared fixture for the backups suite (backup-lib, backup-all, restore-drill).
# Loaded by each .bats file with `load test_helper`.
#
# Every test runs in its own temp tree: backup root, state dir, textfile, lock,
# a throwaway GNUPGHOME with a fixed passphrase, and a bin/ directory that is
# prepended to PATH so shims for docker/rsync/pg_restore shadow the real ones.

common_setup() {
  TEST_ROOT="$(mktemp -d)"
  export BACKUP_ROOT="$TEST_ROOT/nightly"
  export BACKUP_STATE_DIR="$TEST_ROOT/state"
  export BACKUP_TEXTFILE="$TEST_ROOT/backups.prom"
  export BACKUP_LOCK="$TEST_ROOT/lock"
  export BACKUP_GPG_PASSPHRASE="bats-fixed-passphrase"
  export GNUPGHOME="$TEST_ROOT/gnupg"
  export BACKUP_MIN_FREE_GB=0
  export SHIM_LOG="$TEST_ROOT/shim.log"
  mkdir -p "$BACKUP_ROOT" "$BACKUP_STATE_DIR" "$GNUPGHOME" "$TEST_ROOT/bin"
  chmod 700 "$GNUPGHOME"
  export PATH="$TEST_ROOT/bin:$PATH"
}

common_teardown() {
  rm -rf "$TEST_ROOT"
}

# install_shim <name> <<'SHIM' ... SHIM
# Writes the script on stdin to $TEST_ROOT/bin/<name>, makes it executable and
# resets $SHIM_LOG so assertions only see calls made by the current test.
install_shim() {
  cat > "$TEST_ROOT/bin/$1"
  chmod +x "$TEST_ROOT/bin/$1"
  : > "$SHIM_LOG"
}
