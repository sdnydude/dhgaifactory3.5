"""
Remediator command allowlist
============================
The single rule for what the remediator may execute. A command is executable
only if its first token names an allowlisted read-only prefix; anything else
is never run, whatever the runbook's mode or step wording says.

Allowlisted prefixes
    docker inspect ...
    docker logs --tail N ...          (--tail is mandatory, no -f/--follow)
    docker stats --no-stream ...      (--no-stream is mandatory)
    docker ps ...
    curl -s http://dhg-*              (GET only; -G/--data-urlencode allowed)
    wget -qO- http://dhg-*

Rejected outright: shell operators (| ; & > < backtick $( newline) anywhere
in the command, so pipes, redirects and chaining can never be executed.
Commands run with shell=False on the token list, never through a shell.

Shared by remediator.py, its tests, registry/test_seed_runbooks.py and
observability/scripts/verify-runbooks.sh (which runs it inside the
remediator image), so all four agree on the same verdict.
"""
from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys

SHELL_OPERATORS = re.compile(r"[|;&<>`\n]|\$\(")
DHG_HTTP_URL = re.compile(r"^http://dhg-[a-z0-9-]+(:\d+)?(/\S*)?$")

# curl short flags that are read-only and harmless in any combination.
CURL_SHORT_FLAGS = set("sSfGL")
# curl long/valued options and the number of values they take.
CURL_VALUED = {"-m": 1, "--max-time": 1, "-w": 1, "-o": 1, "--data-urlencode": 1}
TIMEOUT_SECONDS = 60
MAX_OUTPUT = 2000


def check_command(command: str) -> tuple[bool, str]:
    """Return (allowed, kind_or_reason).

    `kind` is the allowlist entry that admitted the command (for metrics and
    reports); `reason` says why it was refused.
    """
    if not command or not command.strip():
        return False, "empty command"
    if SHELL_OPERATORS.search(command):
        return False, "shell operator (| ; & > < ` $( or newline) is not allowed"
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return False, f"unparseable command: {exc}"
    if not tokens:
        return False, "empty command"

    head = tokens[0]
    if head == "docker":
        return _check_docker(tokens)
    if head == "curl":
        return _check_curl(tokens)
    if head == "wget":
        return _check_wget(tokens)
    return False, f"'{head}' is not an allowlisted program"


def _check_docker(tokens: list[str]) -> tuple[bool, str]:
    if len(tokens) < 2:
        return False, "docker needs a subcommand"
    sub = tokens[1]
    rest = tokens[2:]
    if sub == "inspect":
        return True, "docker inspect"
    if sub == "ps":
        return True, "docker ps"
    if sub == "logs":
        if "--tail" not in rest:
            return False, "docker logs requires --tail"
        if any(t in ("-f", "--follow") for t in rest):
            return False, "docker logs --follow would never return"
        idx = rest.index("--tail")
        if idx + 1 >= len(rest) or not rest[idx + 1].isdigit():
            return False, "docker logs --tail needs a numeric line count"
        return True, "docker logs --tail"
    if sub == "stats":
        if "--no-stream" not in rest:
            return False, "docker stats requires --no-stream"
        return True, "docker stats --no-stream"
    return False, f"'docker {sub}' is not an allowlisted subcommand"


def _check_curl(tokens: list[str]) -> tuple[bool, str]:
    rest = tokens[1:]
    urls: list[str] = []
    has_s = False
    has_G = False
    has_urlencode = False
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok in CURL_VALUED:
            if i + 1 >= len(rest):
                return False, f"curl {tok} needs a value"
            value = rest[i + 1]
            if tok == "-o" and value != "/dev/null":
                return False, "curl -o may only write to /dev/null"
            if tok == "--data-urlencode":
                has_urlencode = True
            i += 2
            continue
        if tok.startswith("--"):
            return False, f"curl option {tok} is not allowlisted"
        if tok.startswith("-") and len(tok) > 1:
            flags = set(tok[1:])
            if not flags <= CURL_SHORT_FLAGS:
                return False, f"curl option {tok} is not allowlisted"
            has_s = has_s or "s" in flags
            has_G = has_G or "G" in flags
            i += 1
            continue
        urls.append(tok)
        i += 1
    if not has_s:
        return False, "curl requires -s"
    if has_urlencode and not has_G:
        return False, "curl --data-urlencode requires -G (GET); without it curl POSTs"
    if len(urls) != 1:
        return False, "curl needs exactly one URL"
    if not DHG_HTTP_URL.match(urls[0]):
        return False, f"curl URL must be http://dhg-<service>[:port][/path], got {urls[0]}"
    return True, "curl -s http://dhg-*"


def _check_wget(tokens: list[str]) -> tuple[bool, str]:
    if len(tokens) != 3 or tokens[1] != "-qO-":
        return False, "wget must be exactly: wget -qO- <url>"
    if not DHG_HTTP_URL.match(tokens[2]):
        return False, f"wget URL must be http://dhg-<service>[:port][/path], got {tokens[2]}"
    return True, "wget -qO- http://dhg-*"


def run_allowlisted(command: str) -> tuple[int, str]:
    """Execute an already-checked command without a shell. Refuses if the
    allowlist says no, so a caller cannot bypass the check by accident."""
    allowed, reason = check_command(command)
    if not allowed:
        return -2, f"refused: {reason}"
    try:
        result = subprocess.run(
            shlex.split(command),
            shell=False,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return -1, f"Command timed out after {TIMEOUT_SECONDS}s"
    except FileNotFoundError as exc:
        return -1, f"Execution error: {exc}"
    output = (result.stdout + result.stderr).strip()
    if len(output) > MAX_OUTPUT:
        output = output[:MAX_OUTPUT] + "\n... (truncated)"
    return result.returncode, output


def _main(argv: list[str]) -> int:
    """CLI used by verify-runbooks.sh.

    allowlist.py check "<cmd>"      -> prints JSON {allowed, kind|reason}
    allowlist.py exec-batch         -> reads JSON lines {"id":..,"command":..}
                                       on stdin, prints one JSON line per
                                       command with {id, allowed, kind|reason,
                                       returncode, output}
    """
    if len(argv) >= 3 and argv[1] == "check":
        allowed, info = check_command(argv[2])
        print(json.dumps({"allowed": allowed, "kind" if allowed else "reason": info}))
        return 0 if allowed else 1
    if len(argv) == 2 and argv[1] == "exec-batch":
        worst = 0
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            allowed, info = check_command(item["command"])
            out: dict = {"id": item.get("id"), "command": item["command"], "allowed": allowed}
            if allowed:
                rc, output = run_allowlisted(item["command"])
                out.update({"kind": info, "returncode": rc, "output": output[:400]})
                worst = worst or (rc != 0)
            else:
                out.update({"reason": info, "returncode": -2, "output": ""})
                worst = 1
            print(json.dumps(out), flush=True)
        return worst
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
