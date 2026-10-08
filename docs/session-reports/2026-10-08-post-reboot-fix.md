# 2026-10-08 — Post-reboot container failures fixed (g700data1 + dh40801)

## Problem
After the 10-07 boot, dhg-prometheus (.251) and the dh40801 exporters stayed down and were started by hand.

## Root causes
1. `docker kill -s HUP dhg-prometheus` (old reload idiom) sets HasBeenManuallyStopped; `unless-stopped` then skips the container at boot (moby v29 daemon/kill.go, restartmanager).
2. dh40801 dockerd bound 10.0.0.179 before the DHCP lease arrived; restore-path start failures never retry.
3. DOCKER-USER guard blocked dh40801 -> :9093, so dhg-power notify from 4080 failed (HTTP 000).
4. dhg-power shutdown ran ssh to 4080 as root, which has no host trust (rc=255).

## Fixes
- restart: always for prometheus, alertmanager, grafana (override, 43ce4fa3); reload via `docker compose restart prometheus` (docs, cd98fc8f).
- 4080 `net.ipv4.ip_nonlocal_bind=1` in /etc/sysctl.d/90-dhg-nonlocal-bind.conf.
- docker-user-fw.sh RETURN rule for dh40801 -> 9093 + bats assertion (cd98fc8f).
- dhg-power-ops Task 7 installed on both hosts; notify labels job/instance for registry PowerEvent; peer ssh via PEER_SSH_USER (ebcdfbe, 46/46 bats).

## Verification
Restart policies always (runtime + compose config); 4080 -> 9093 HTTP 200; Prometheus 0/34 down; both `dhg-power drill` clean; root -> 4080 ssh rc=0; registry PowerEvent seen for startup runs.

## Not verified
No controlled reboot (Stephen's choice). Next real boot is the acceptance test (registry deferred ac619489).
