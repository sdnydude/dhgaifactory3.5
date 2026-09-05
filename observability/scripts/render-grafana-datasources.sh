#!/usr/bin/env bash
# Render the Grafana datasource provisioning files that embed a credential.
#
# Today that is exactly one: the read-only registry Postgres datasource. Grafana
# provisioning offers no indirection for a datasource password (secureJsonData
# takes a literal), so the rendered file is gitignored and only the .tmpl is
# tracked — the same pattern as render-alertmanager.sh and
# postgres-exporter/render-postgres-exporter.sh.
#
#   observability/scripts/render-grafana-datasources.sh
#   docker compose up -d grafana     # datasources are provisioned at startup only
#
# Source of truth: Doppler project dhg-monitoring, config dev, secret
# REGISTRY_GRAFANA_RO_PASSWORD (the password of the grafana_ro role on
# dhg-registry-db). If it is missing the script fails loudly rather than writing
# a datasource that would make Grafana retry a bad login against production.
#
# No secret value is ever echoed.
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)/grafana/provisioning/datasources"
TMPL="$DIR/registry-postgres.yml.tmpl"
OUT="$DIR/registry-postgres.yml"
PROJECT="dhg-monitoring"
CONFIG="dev"

[ -f "$TMPL" ] || { echo "ERROR: template not found: $TMPL" >&2; exit 1; }
command -v doppler >/dev/null || { echo "ERROR: doppler CLI not found" >&2; exit 1; }

PW="$(doppler secrets get REGISTRY_GRAFANA_RO_PASSWORD \
  --project "$PROJECT" --config "$CONFIG" --plain 2>/dev/null || true)"
[ -n "$PW" ] || {
  echo "ERROR: REGISTRY_GRAFANA_RO_PASSWORD not readable from Doppler ${PROJECT}/${CONFIG}" >&2
  exit 1
}

umask 077
tmp="$(mktemp "${OUT}.XXXXXX")"
trap 'rm -f "$tmp"' EXIT

{
  echo "# GENERATED FILE — do not edit, do not commit. Rendered from"
  echo "# registry-postgres.yml.tmpl by observability/scripts/render-grafana-datasources.sh."
  echo "# Gitignored: contains the grafana_ro role password."
  # Drop the template's own "this is a template" preamble marker line so the
  # rendered file does not claim to be the source of truth.
  sed -e 's/^# TEMPLATE — this is the tracked source of truth\./# Source of truth is the tracked registry-postgres.yml.tmpl./' "$TMPL"
} >"$tmp"

PW="$PW" python3 - "$tmp" <<'PY'
import os, sys
p = sys.argv[1]
with open(p) as f:
    body = f.read()
if "__REGISTRY_GRAFANA_RO_PASSWORD__" not in body:
    sys.exit("ERROR: placeholder __REGISTRY_GRAFANA_RO_PASSWORD__ not found in template")
# YAML double-quoted scalar: escape backslash and double quote. The generated
# password is base64 (A-Za-z0-9+/=) so neither occurs today, but the render must
# not silently corrupt a rotated password that does.
pw = os.environ["PW"].replace("\\", "\\\\").replace('"', '\\"')
with open(p, "w") as f:
    f.write(body.replace("__REGISTRY_GRAFANA_RO_PASSWORD__", pw))
PY

mv "$tmp" "$OUT"
# 0644, not 0600: dhg-grafana runs as uid 472 and reads this through the
# provisioning bind mount, so host permissions apply. Confidentiality rests on
# the file being gitignored, not on its mode — same as the rendered
# alertmanager.yml.
chmod 0644 "$OUT"
trap - EXIT
echo "wrote $OUT (datasource 'Registry DB', uid registry-pg, user grafana_ro)"
