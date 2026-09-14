#!/usr/bin/env bash
# verify-runbooks.sh — run every observability/runbooks/*.yml diagnostic
# through the remediator's allowlist and, for the allowlisted ones, live from
# inside the remediator image on the compose network with the YAML's fixture
# labels substituted for {container} {instance} {service} {job}.
#
# Fails (exit 1) on: a non-allowlisted command in any YAML, an unresolved
# placeholder, or a non-zero exit from any live command. Prints a per-alert
# table.
#
# Usage: observability/scripts/verify-runbooks.sh [--static]
#   --static   allowlist + placeholder check only, nothing executed
set -euo pipefail
cd "$(dirname "$0")/../.."

IMAGE="${REMEDIATOR_IMAGE:-dhgaifactory35-dhg-remediator}"
NETWORK="${DHG_NETWORK:-dhgaifactory35_dhg-network}"
DOCKER_GID="${DOCKER_GID:-$(stat -c %g /var/run/docker.sock)}"
STATIC=0
[ "${1:-}" = "--static" ] && STATIC=1

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 1. Static pass: resolve placeholders from fixtures, allowlist every command.
PYTHONPATH=services/remediator python3 - "$TMP/batch.jsonl" <<'PY'
import glob, json, re, sys, yaml
from allowlist import check_command
out = open(sys.argv[1], "w")
placeholder = re.compile(r"\{(container|instance|service|job)\}")
bad = 0
for path in sorted(glob.glob("observability/runbooks/*.yml")):
    doc = yaml.safe_load(open(path))
    fixture = doc.get("fixture") or {}
    for step in doc["diagnostics"]:
        cmd = placeholder.sub(lambda m: fixture.get(m.group(1), m.group(0)), step["command"])
        unresolved = placeholder.findall(cmd)
        allowed, why = check_command(cmd)
        if unresolved:
            print(f"UNRESOLVED {doc['alert']} step {step['order']}: {unresolved} (add to fixture:)")
            bad += 1
        elif not allowed:
            print(f"REFUSED    {doc['alert']} step {step['order']}: {why}\n           {cmd}")
            bad += 1
        out.write(json.dumps({"id": f"{doc['alert']}#{step['order']}", "command": cmd}) + "\n")
out.close()
print(f"static: {sum(1 for _ in open(sys.argv[1]))} diagnostics across "
      f"{len(glob.glob('observability/runbooks/*.yml'))} runbooks, {bad} problems")
sys.exit(1 if bad else 0)
PY

if [ "$STATIC" = 1 ]; then
  echo "static check only (--static); nothing executed"
  exit 0
fi

# 2. Live pass inside the remediator image (same allowlist, same executor).
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "image $IMAGE not built; run: docker compose build dhg-remediator" >&2
  exit 1
fi
docker run --rm -i --network "$NETWORK" \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  --group-add "$DOCKER_GID" \
  "$IMAGE" python allowlist.py exec-batch < "$TMP/batch.jsonl" > "$TMP/results.jsonl" || true

# 3. Per-alert table.
python3 - "$TMP/results.jsonl" <<'PY'
import json, sys
from collections import OrderedDict
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
by_alert: "OrderedDict[str, list]" = OrderedDict()
for r in rows:
    by_alert.setdefault(r["id"].split("#")[0], []).append(r)
failed = 0
print(f"{'alert':<26} {'steps':>5} {'ok':>3} {'fail':>4}  detail")
for alert, items in by_alert.items():
    bad = [r for r in items if not r["allowed"] or r["returncode"] != 0]
    failed += len(bad)
    detail = "; ".join(f"#{r['id'].split('#')[1]} rc={r['returncode']} {(r.get('reason') or r.get('output') or '')[:60]!r}" for r in bad)
    print(f"{alert:<26} {len(items):>5} {len(items)-len(bad):>3} {len(bad):>4}  {detail}")
print(f"\n{len(rows)} diagnostics executed live in the remediator image, {failed} failed")
sys.exit(1 if failed or not rows else 0)
PY
