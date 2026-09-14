#!/usr/bin/env bats
# docker-user-fw.sh: dry-run executes nothing; apply issues the guard rules
# through iptables/ip6tables (shimmed here); remove unhooks both chains.

setup() {
  TEST_ROOT="$(mktemp -d)"
  export SHIM_LOG="$TEST_ROOT/shim.log"
  mkdir -p "$TEST_ROOT/bin"
  for tool in iptables ip6tables; do
    cat > "$TEST_ROOT/bin/$tool" <<SHIM
#!/usr/bin/env bash
echo "$tool \$*" >> "\$SHIM_LOG"
# -C (check) reports "no such rule" so the script inserts the jump exactly once
[[ "\$*" == *" -C "* ]] && exit 1
exit 0
SHIM
    chmod +x "$TEST_ROOT/bin/$tool"
  done
  export PATH="$TEST_ROOT/bin:$PATH"
  SCRIPT="$BATS_TEST_DIRNAME/../scripts/docker-user-fw.sh"
}

teardown() { rm -rf "$TEST_ROOT"; }

@test "dry-run prints every rule and calls no binary" {
  run "$SCRIPT" --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" == *"iptables -w -I DOCKER-USER 1 -j DHG-LAN-GUARD"* ]]
  [[ "$output" == *"ip6tables -w -I INPUT 1 -j DHG-LAN-GUARD"* ]]
  [[ "$output" == *"-s 10.0.0.179 -p tcp -m conntrack --ctorigdstport 3100 -j RETURN"* ]]
  [ ! -e "$SHIM_LOG" ]
}

@test "apply: interface and established-connection bypass precede the drops" {
  run "$SCRIPT"
  [ "$status" -eq 0 ]
  mapfile -t v4 < <(grep '^iptables -w -A' "$SHIM_LOG")
  [[ "${v4[0]}" == *"! -i eno1 -j RETURN" ]]
  [[ "${v4[1]}" == *"--ctstate RELATED,ESTABLISHED -j RETURN" ]]
  [[ "${v4[-1]}" == *"--ctorigdstport 8080 -j DROP" ]]
  [ "$(grep -c -- '-j DROP' "$SHIM_LOG")" -eq 5 ]   # 4 v4 ports + 1 v6 multiport
  [ "$(grep -c -- '-I DOCKER-USER 1 -j DHG-LAN-GUARD' "$SHIM_LOG")" -eq 1 ]
  [ "$(grep -c -- '-I INPUT 1 -j DHG-LAN-GUARD' "$SHIM_LOG")" -eq 1 ]
}

@test "remove: flushes and deletes both chains" {
  run "$SCRIPT" --remove
  [ "$status" -eq 0 ]
  grep -q '^iptables -w -F DHG-LAN-GUARD' "$SHIM_LOG"
  grep -q '^iptables -w -X DHG-LAN-GUARD' "$SHIM_LOG"
  grep -q '^ip6tables -w -X DHG-LAN-GUARD' "$SHIM_LOG"
}

@test "unknown flag exits 64" {
  run "$SCRIPT" --bogus
  [ "$status" -eq 64 ]
}
