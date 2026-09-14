#!/usr/bin/env python3
"""
bats-tdd-reporter.py — run bats and publish results where tdd-guard reads them.

tdd-guard only sees test results written to .claude/tdd-guard/data/test.json
by a reporter (pytest and vitest reporters exist; bats has none). Without one,
every shell edit is refused as "premature implementation" because the guard
never sees a red. This wrapper runs bats with the TAP formatter and writes the
same JSON shape the pytest reporter produces:

  {"testModules": [{"moduleId": "<file>", "tests": [
      {"name": ..., "fullName": "<file>::<name>", "state": "passed|failed|skipped",
       "errors": [{"message": ...}]}]}]}

Usage: bats-tdd-reporter.py [bats args...] <file-or-dir>...
Exit code is bats' exit code. Project root = the git top level of the cwd.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

TAP_RESULT = re.compile(r"^(ok|not ok) (\d+) (.*?)(?: # (SKIP|skip)(.*))?$")
BATS_TEST_LINE = re.compile(r"^#\s*\(in test file (.+?), line \d+\)")


def project_root() -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
        ).stdout.strip()
        return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        # Outside a git checkout the guard would never see this test.json; say so.
        print(f"bats-tdd-reporter: not in a git repo ({exc}); writing under {Path.cwd()}", file=sys.stderr)
        return Path.cwd()


def run_bats(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(["bats", "--formatter", "tap", *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout + ("\n" + proc.stderr if proc.stderr.strip() else "")


def parse_tap(tap: str, default_module: str) -> dict:
    modules: dict[str, dict] = {}
    current: dict | None = None
    for line in tap.splitlines():
        m = TAP_RESULT.match(line)
        if m:
            status, _num, name, skip, _reason = m.groups()
            state = "skipped" if skip else ("passed" if status == "ok" else "failed")
            current = {"name": name.strip(), "fullName": f"{default_module}::{name.strip()}", "state": state}
            if state == "failed":
                current["errors"] = [{"message": ""}]
            modules.setdefault(default_module, {"moduleId": default_module, "tests": []})["tests"].append(current)
            continue
        if current is not None and line.startswith("#"):
            mf = BATS_TEST_LINE.match(line)
            if mf:
                mod = mf.group(1)
                # re-home the test under the real file bats reported
                if mod != default_module:
                    modules.setdefault(mod, {"moduleId": mod, "tests": []})
                    modules[default_module]["tests"].remove(current)
                    current["fullName"] = f"{mod}::{current['name']}"
                    modules[mod]["tests"].append(current)
                    if not modules[default_module]["tests"]:
                        del modules[default_module]
            if current.get("state") == "failed":
                current["errors"][0]["message"] += line[1:].strip() + "\n"
    return {"testModules": list(modules.values())}


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    root = project_root()
    targets = [a for a in args if not a.startswith("-")]
    default_module = os.path.relpath(targets[-1], root) if targets else "bats"
    rc, tap = run_bats(args)
    result = parse_tap(tap, default_module)
    if not result["testModules"]:
        # bats itself failed (syntax error, missing file) or found no tests:
        # surface it as a failed module AND a non-zero exit, never a green shell.
        result["testModules"] = [{
            "moduleId": default_module,
            "tests": [{"name": "bats", "fullName": f"{default_module}::bats", "state": "failed",
                       "errors": [{"message": tap.strip()[-2000:] or "no tests parsed"}]}],
        }]
        rc = rc or 1
    out_dir = root / ".claude" / "tdd-guard" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "test.json").write_text(json.dumps(result, indent=2))
    sys.stdout.write(tap)
    failed = sum(1 for m in result["testModules"] for t in m["tests"] if t["state"] == "failed")
    passed = sum(1 for m in result["testModules"] for t in m["tests"] if t["state"] == "passed")
    print(f"\nbats-tdd-reporter: {passed} passed, {failed} failed -> {out_dir / 'test.json'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
