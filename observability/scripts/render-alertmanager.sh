#!/usr/bin/env bash
# Render observability/alertmanager/alertmanager.yml from alertmanager.yml.tmpl.
#
# The Slack incoming-webhook URL is itself a credential, so the rendered file is
# gitignored and only the template is tracked. Re-run this script after editing
# the template, then reload Alertmanager:
#
#   observability/scripts/render-alertmanager.sh
#   curl -X POST http://10.0.0.251:9093/-/reload
#
# If SLACK_ALERT_WEBHOOK_URL is not in Doppler (dhg-monitoring/dev) the script
# renders a valid, Slack-free config and exits 0 — alerting keeps working
# through the registry webhook.
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)/alertmanager"
TMPL="$DIR/alertmanager.yml.tmpl"
OUT="$DIR/alertmanager.yml"

[ -f "$TMPL" ] || { echo "ERROR: template not found: $TMPL" >&2; exit 1; }

# Never echoed, never written anywhere but the gitignored $OUT.
SLACK_URL="$(doppler secrets get SLACK_ALERT_WEBHOOK_URL \
  --project dhg-monitoring --config dev --plain 2>/dev/null || true)"

HEADER="# GENERATED FILE — do not edit. Rendered from alertmanager.yml.tmpl by
# observability/scripts/render-alertmanager.sh. Gitignored: contains a secret."

# Marker patterns are anchored to column 0 (block markers) or to leading
# whitespace (inline markers) so the "# @DOC" lines that *describe* the markers
# are never mistaken for markers themselves.
if [ -n "$SLACK_URL" ]; then
  { echo "$HEADER"; sed -e '/^# @DOC/d' \
        -e '/^ *# @NO_SLACK /d' \
        -e '/^# @SLACK_BEGIN$/d' \
        -e '/^# @SLACK_END$/d' \
        -e 's/ # @SLACK_ONLY$//' "$TMPL"; } > "$OUT"
  SLACK_URL="$SLACK_URL" python3 - "$OUT" <<'PY'
import os, sys
p = sys.argv[1]
with open(p) as f:
    body = f.read()
with open(p, "w") as f:
    f.write(body.replace("__SLACK_WEBHOOK_URL__", os.environ["SLACK_URL"]))
PY
  echo "rendered $OUT (slack receiver included)"
else
  { echo "$HEADER"; sed -e '/^# @DOC/d' \
        -e '/ # @SLACK_ONLY$/d' \
        -e '/^# @SLACK_BEGIN$/,/^# @SLACK_END$/d' \
        -e 's/^\( *\)# @NO_SLACK /\1/' "$TMPL"; } > "$OUT"
  echo "WARN: SLACK_ALERT_WEBHOOK_URL not in Doppler; slack receiver omitted"
  echo "rendered $OUT (registry webhook only)"
fi

# 0644, not 0600: dhg-alertmanager runs as nobody (uid 65534) and reads this
# through a bind mount, so host permissions apply and it must be world-readable.
# Confidentiality here rests on the file being gitignored, not on file mode.
chmod 0644 "$OUT"
