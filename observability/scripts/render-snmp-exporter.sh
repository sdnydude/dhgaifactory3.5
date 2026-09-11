#!/usr/bin/env bash
# Render observability/snmp-exporter/auths.yml — the SNMPv3 credential file
# dhg-snmp-exporter reads alongside the vendored snmp.yml (snmp_exporter accepts
# --config.file more than once; the auths section may live in its own file).
#
#   observability/scripts/render-snmp-exporter.sh
#   docker compose up -d snmp-exporter      # or: docker restart dhg-snmp-exporter
#
# Source of truth: Doppler project dhg-monitoring, config dev, secrets
# SNMP_V3_USER, SNMP_V3_AUTH_PASSWORD, SNMP_V3_PRIV_PASSWORD — the same values
# configured on the Synology (Control Panel > Terminal & SNMP > SNMPv3, SHA/AES).
# Missing values fail loudly rather than rendering an exporter that would poll
# the NAS with bad credentials forever. The rendered file is gitignored and
# mode 600. No secret value is ever echoed.
set -euo pipefail

cd "$(dirname "$0")/../.."
OUT="observability/snmp-exporter/auths.yml"

get() { doppler secrets get "$1" --project dhg-monitoring --config dev --plain --no-check-version 2>/dev/null || true; }
USER_="$(get SNMP_V3_USER)"; AUTH_="$(get SNMP_V3_AUTH_PASSWORD)"; PRIV_="$(get SNMP_V3_PRIV_PASSWORD)"
for pair in "SNMP_V3_USER:$USER_" "SNMP_V3_AUTH_PASSWORD:$AUTH_" "SNMP_V3_PRIV_PASSWORD:$PRIV_"; do
  [ -n "${pair#*:}" ] || { echo "render-snmp-exporter: ${pair%%:*} is not set in Doppler dhg-monitoring/dev" >&2; exit 1; }
done

umask 077
TMP="$(mktemp "${OUT}.XXXXXX")"
trap 'rm -f "$TMP"' EXIT
# Values are emitted as YAML double-quoted scalars; backslashes and quotes escaped.
yq_escape() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
cat > "$TMP" <<EOF
# RENDERED by observability/scripts/render-snmp-exporter.sh — do not edit, do not commit.
auths:
  dhg_v3:
    version: 3
    username: "$(yq_escape "$USER_")"
    security_level: authPriv
    auth_protocol: SHA
    password: "$(yq_escape "$AUTH_")"
    priv_protocol: AES
    priv_password: "$(yq_escape "$PRIV_")"
EOF
chmod 0600 "$TMP"
mv -f "$TMP" "$OUT"
trap - EXIT
echo "rendered $OUT (auth dhg_v3, SNMPv3 authPriv SHA/AES)"
