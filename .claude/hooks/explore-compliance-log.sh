#!/usr/bin/env bash
# PostToolUse hook: measure whether Explore subagent reports honor the
# return-format contract in .claude/rules/codegraph.md (summaries, not source).
#
# NON-BLOCKING BY DESIGN. This hook only observes and logs. It never emits a
# permissionDecision and always exits 0. PostToolUse fires after the subagent's
# payload has already landed in main context, so blocking here would be
# theatre — the bloat has happened. The job is measurement: how often does a
# report actually carry source dumps, and does the contract's presence in the
# spawn prompt change that?
#
# Rationale for measure-before-enforce: decision log 2026-07-05
# ("enforce-capture-sweep.sh blocking hook rejected") — a blocking gate was
# rejected for bricking defects and a substring-match bypass found only by
# execution testing. Do not add a blocking variant without that same review.
#
# No `set -e`: partial telemetry beats a hook that dies and logs nothing.

LOG_DIR="${CLAUDE_PROJECT_DIR:-$HOME/DHG/aifactory3.5/dhgaifactory3.5}/.claude/logs"
LOG_FILE="$LOG_DIR/explore-compliance.log"

mkdir -p "$LOG_DIR" 2>/dev/null

INPUT=$(cat 2>/dev/null || echo "")
[ -n "$INPUT" ] || exit 0

printf '%s' "$INPUT" | LOG_FILE="$LOG_FILE" python3 -c '
import json, os, re, sys, datetime

def main():
    raw = sys.stdin.read()
    d = json.loads(raw)

    ti = d.get("tool_input") or {}
    if not isinstance(ti, dict):
        return

    # Scope: Explore subagents only. Every other agent type is none of our business.
    subagent = str(ti.get("subagent_type") or "")
    if subagent.strip().lower() != "explore":
        return

    prompt = str(ti.get("prompt") or "")

    # tool_response shape varies by version: str, dict, or list of content blocks.
    resp = d.get("tool_response")
    if isinstance(resp, str):
        text = resp
    elif isinstance(resp, dict):
        text = resp.get("content") or resp.get("text") or json.dumps(resp)
        if isinstance(text, list):
            text = "\n".join(
                b.get("text", "") if isinstance(b, dict) else str(b) for b in text
            )
    elif isinstance(resp, list):
        text = "\n".join(
            b.get("text", "") if isinstance(b, dict) else str(b) for b in resp
        )
    else:
        text = ""
    text = str(text)

    fences = re.findall(r"^```", text, flags=re.MULTILINE)
    fence_count = len(fences)
    # Lines sitting inside fenced blocks — the actual bloat measure.
    fenced_lines = 0
    inside = False
    for line in text.splitlines():
        if line.startswith("```"):
            inside = not inside
            continue
        if inside:
            fenced_lines += 1

    words = len(text.split())

    # Did the spawn prompt carry the contract? This is the experiment: correlate
    # contract presence against actual source-dumping. NOT used as a gate —
    # a substring check is trivially satisfiable and proves nothing on its own.
    contract = bool(re.search(r"never paste source blocks", prompt, re.IGNORECASE))

    rec = {
        "ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "session": os.environ.get("CLAUDE_CODE_SESSION_ID", "unknown"),
        "subagent_type": subagent,
        "words": words,
        "code_fences": fence_count // 2,
        "fenced_lines": fenced_lines,
        "prompt_had_contract": contract,
        "violation": fence_count >= 2 or words > 700,
    }

    with open(os.environ["LOG_FILE"], "a") as fh:
        fh.write(json.dumps(rec) + "\n")

try:
    main()
except Exception:
    # Fail silent, fail open. A telemetry hook must never disrupt a session.
    pass
' 2>/dev/null

exit 0
