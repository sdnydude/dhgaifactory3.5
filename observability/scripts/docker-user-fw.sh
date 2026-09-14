#!/usr/bin/env bash
# docker-user-fw.sh — LAN guard for the Docker-published observability ports
# (Prometheus 9090, Alertmanager 9093, Loki 3100, cAdvisor 8080). Rebuild plan
# WP9 / outstanding plan 5.3.
#
# Why not ufw: Docker DNATs a published port in nat PREROUTING, so LAN traffic
# to 10.0.0.251:9090 traverses FORWARD and never INPUT. ufw writes INPUT rules
# and would not see it. DOCKER-USER is the one FORWARD chain Docker leaves to
# the operator. Rules there see the packet after DNAT, so the port is matched on
# the conntrack ORIGINAL destination (--ctorigdstport): cAdvisor's container port
# is 8080, the same as open-webui's (published on 3080), so a plain --dport 8080
# would catch both.
#
# Replies must pass: Prometheus on this host scrapes dh40801:8080 and :9100, and
# those reply packets arrive on eno1 from 10.0.0.179 with ORIGINAL dst port 8080.
# The RELATED,ESTABLISHED RETURN before the DROP rules lets them through; an
# unauthorised LAN host's SYN is NEW and is dropped, so it never establishes.
#
# IPv6: daemon.json sets no "ipv6", so the [::] listeners are docker-proxy
# userland sockets. Those packets hit INPUT, not FORWARD, so the v6 guard is an
# ip6tables INPUT rule on the published ports (no DNAT, so --dport is exact).
#
# Idempotent: owns one chain, DHG-LAN-GUARD, in the v4 filter table (jumped to
# from DOCKER-USER position 1) and in the v6 filter table (jumped to from INPUT
# position 1). Every run flushes and rebuilds the chain, so editing the
# constants below and re-running is the whole change procedure.
#
# Installed copy: /usr/local/sbin/docker-user-fw.sh (root-owned; a root systemd
# unit must not execute a user-writable file). Unit: dhg-docker-user-fw.service.
#
# Usage: docker-user-fw.sh [--dry-run | --status | --remove]
#   (no flag)  apply the rules (needs root)
#   --dry-run  print the iptables/ip6tables commands, execute nothing
#   --status   list the guard chains
#   --remove   unhook and delete the guard chains
set -euo pipefail

IFACE="${IFACE:-eno1}"
MAC_LAN_IP="${MAC_LAN_IP:-10.0.0.238}"   # Stephen's Mac; pin it with a DHCP reservation
DH40801_IP="${DH40801_IP:-10.0.0.179}"   # Alloy on dh40801 pushes logs to :3100
GUARDED_PORTS=(9090 9093 3100 8080)
CHAIN=DHG-LAN-GUARD
IPT="${IPTABLES:-iptables}"
IP6T="${IP6TABLES:-ip6tables}"

mode=apply
case "${1:-}" in
  "") ;;
  --dry-run) mode=dry ;;
  --status)  mode=status ;;
  --remove)  mode=remove ;;
  *) echo "usage: $0 [--dry-run|--status|--remove]" >&2; exit 64 ;;
esac

run() {
  if [[ $mode == dry ]]; then
    printf '+ %s\n' "$*"
  else
    "$@"
  fi
}

# ensure_chain <tool> <parent-chain>: create the guard chain if missing, flush
# it, and make sure exactly one jump sits at position 1 of the parent.
ensure_chain() {
  local tool=$1 parent=$2
  if [[ $mode == dry ]]; then
    printf '+ %s -w -N %s (if missing)\n' "$tool" "$CHAIN"
    printf '+ %s -w -F %s\n' "$tool" "$CHAIN"
    printf '+ %s -w -I %s 1 -j %s (if no jump yet)\n' "$tool" "$parent" "$CHAIN"
    return
  fi
  "$tool" -w -N "$CHAIN" 2>/dev/null || true
  "$tool" -w -F "$CHAIN"
  "$tool" -w -C "$parent" -j "$CHAIN" 2>/dev/null || "$tool" -w -I "$parent" 1 -j "$CHAIN"
}

remove_chain() {
  local tool=$1 parent=$2
  while "$tool" -w -C "$parent" -j "$CHAIN" 2>/dev/null; do
    "$tool" -w -D "$parent" -j "$CHAIN"
  done
  "$tool" -w -F "$CHAIN" 2>/dev/null || true
  "$tool" -w -X "$CHAIN" 2>/dev/null || true
}

apply_v4() {
  local p
  ensure_chain "$IPT" DOCKER-USER
  run "$IPT" -w -A "$CHAIN" ! -i "$IFACE" -j RETURN
  run "$IPT" -w -A "$CHAIN" -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN
  for p in "${GUARDED_PORTS[@]}"; do
    run "$IPT" -w -A "$CHAIN" -s "$MAC_LAN_IP" -p tcp -m conntrack --ctorigdstport "$p" -j RETURN
  done
  run "$IPT" -w -A "$CHAIN" -s "$DH40801_IP" -p tcp -m conntrack --ctorigdstport 3100 -j RETURN
  for p in "${GUARDED_PORTS[@]}"; do
    run "$IPT" -w -A "$CHAIN" -p tcp -m conntrack --ctorigdstport "$p" -j DROP
  done
}

apply_v6() {
  local ports
  ports=$(IFS=,; echo "${GUARDED_PORTS[*]}")
  ensure_chain "$IP6T" INPUT
  run "$IP6T" -w -A "$CHAIN" ! -i "$IFACE" -j RETURN
  run "$IP6T" -w -A "$CHAIN" -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN
  run "$IP6T" -w -A "$CHAIN" -p tcp -m multiport --dports "$ports" -j DROP
}

case $mode in
  apply|dry)
    apply_v4
    apply_v6
    ;;
  status)
    echo "# ${IPT} (filter, hooked from DOCKER-USER)"
    "$IPT" -w -S "$CHAIN"
    echo "# ${IP6T} (filter, hooked from INPUT)"
    "$IP6T" -w -S "$CHAIN"
    ;;
  remove)
    remove_chain "$IPT" DOCKER-USER
    remove_chain "$IP6T" INPUT
    ;;
esac
