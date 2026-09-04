#!/usr/bin/env bash
# Render observability/alertmanager/alertmanager.yml from alertmanager.yml.tmpl.
#
# The Telegram bot token is itself a credential, so the rendered file is
# gitignored and only the template is tracked. Re-run this script after editing
# the template, then reload Alertmanager:
#
#   observability/scripts/render-alertmanager.sh
#   curl -X POST http://10.0.0.251:9093/-/reload
#
# If TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not in Doppler (dhg-monitoring/dev)
# the script renders a valid, Telegram-free config and exits 0 — alerting keeps working
# through the registry webhook.
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)/alertmanager"
TMPL="$DIR/alertmanager.yml.tmpl"
OUT="$DIR/alertmanager.yml"

[ -f "$TMPL" ] || { echo "ERROR: template not found: $TMPL" >&2; exit 1; }

# Never echoed, never written anywhere but the gitignored $OUT.
TG_TOKEN="$(doppler secrets get TELEGRAM_BOT_TOKEN \
  --project dhg-monitoring --config dev --plain 2>/dev/null || true)"
TG_CHAT="$(doppler secrets get TELEGRAM_CHAT_ID \
  --project dhg-monitoring --config dev --plain 2>/dev/null || true)"

HEADER="# GENERATED FILE — do not edit. Rendered from alertmanager.yml.tmpl by
# observability/scripts/render-alertmanager.sh. Gitignored: contains a secret."

# Marker patterns are anchored to column 0 (block markers) or to leading
# whitespace (inline markers) so the "# @DOC" lines that *describe* the markers
# are never mistaken for markers themselves.
if [ -n "$TG_TOKEN" ] && [ -n "$TG_CHAT" ]; then
  { echo "$HEADER"; sed -e '/^# @DOC/d' \
        -e '/^ *# @NO_TG /d' \
        -e '/^# @TG_BEGIN$/d' \
        -e '/^# @TG_END$/d' \
        -e 's/ # @TG_ONLY$//' "$TMPL"; } > "$OUT"
  TG_TOKEN="$TG_TOKEN" TG_CHAT="$TG_CHAT" python3 - "$OUT" <<'PY'
import os, sys
p = sys.argv[1]
with open(p) as f:
    body = f.read()
with open(p, "w") as f:
    body = body.replace("__TELEGRAM_BOT_TOKEN__", os.environ["TG_TOKEN"])
    body = body.replace("__TELEGRAM_CHAT_ID__", os.environ["TG_CHAT"])
    f.write(body)
PY
  echo "rendered $OUT (telegram receiver included)"
else
  { echo "$HEADER"; sed -e '/^# @DOC/d' \
        -e '/ # @TG_ONLY$/d' \
        -e '/^# @TG_BEGIN$/,/^# @TG_END$/d' \
        -e 's/^\( *\)# @NO_TG /\1/' "$TMPL"; } > "$OUT"
  echo "WARN: TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not in Doppler; telegram receiver omitted"
  echo "rendered $OUT (registry webhook only)"
fi

# 0644, not 0600: dhg-alertmanager runs as nobody (uid 65534) and reads this
# through a bind mount, so host permissions apply and it must be world-readable.
# Confidentiality here rests on the file being gitignored, not on file mode.
chmod 0644 "$OUT"
