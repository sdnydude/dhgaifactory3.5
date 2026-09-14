#!/usr/bin/env python3
"""
gen-runbooks.py — runbooks-as-code generator.

Reads observability/runbooks/*.yml (the source) and:
  (a) refreshes the incident_runbooks cache through the registry
      (POST /api/incidents/runbooks/seed, which loads the same directory
      bind-mounted into the container) and checks every YAML trigger is
      present and enabled;
  (b) appends or refreshes an "Automation" block under the matching
      `### <alert>` section of docs-site/projects/dhg-ai-factory/runbooks/alerts.md
      between {/* automation:begin <alert> */} … {/* automation:end */} markers;
  (c) writes the "## Automation coverage" section (all 45 rules, automated
      diagnostics or human-only) between {/* coverage:begin */} … {/* coverage:end */}.

Re-running is idempotent. The hand-written page is never regenerated; only the
marked blocks change.

Usage: gen-runbooks.py [--registry http://10.0.0.251:8011] [--no-seed] [--check]
  --check   exit 1 if the docs page would change (CI-style drift check)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
RUNBOOKS_DIR = REPO / "observability" / "runbooks"
DOCS_PAGE = REPO / "docs-site" / "projects" / "dhg-ai-factory" / "runbooks" / "alerts.md"
RULE_FILES = (
    [REPO / "observability" / "prometheus" / "alerts.yml"]
    + sorted((REPO / "observability" / "prometheus" / "rules.d").glob("*.yml"))
    + [REPO / "observability" / "loki" / "rules" / "fake" / "alerts.yml"]
)

AUTO_BEGIN = "{/* automation:begin %s */}"
AUTO_END = "{/* automation:end */}"
COV_BEGIN = "{/* coverage:begin */}"
COV_END = "{/* coverage:end */}"
SECTION_END = re.compile(r"^(## |### |---\s*$)")


def load_runbooks() -> dict[str, dict]:
    books = {}
    for path in sorted(RUNBOOKS_DIR.glob("*.yml")):
        doc = yaml.safe_load(open(path))
        if doc["alert"] != path.stem:
            sys.exit(f"{path.name}: alert '{doc['alert']}' must match the file name")
        books[doc["alert"]] = doc
    return books


def load_rules() -> list[tuple[str, str, str]]:
    """(alertname, severity, source file) in rule-file order."""
    rules = []
    for path in RULE_FILES:
        doc = yaml.safe_load(open(path))
        for group in doc["groups"]:
            for rule in group["rules"]:
                rules.append((rule["alert"], rule["labels"]["severity"], str(path.relative_to(REPO))))
    return rules


# ── (a) seed through the registry ──────────────────────────────────────

def seed_via_registry(registry: str, books: dict[str, dict]) -> None:
    req = urllib.request.Request(f"{registry}/api/incidents/runbooks/seed", method="POST", data=b"")
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.load(resp)
    print(f"seed: {result}")
    with urllib.request.urlopen(f"{registry}/api/incidents/runbooks?enabled_only=true", timeout=30) as resp:
        rows = {r["trigger_rule"]: r for r in json.load(resp)}
    missing = [b["trigger_rule"] for b in books.values() if b["trigger_rule"] not in rows]
    if missing:
        sys.exit(f"seed did not produce enabled rows for {missing}")
    extra = sorted(set(rows) - {b["trigger_rule"] for b in books.values()})
    if extra:
        sys.exit(f"enabled rows without YAML: {extra}")
    for b in books.values():
        row = rows[b["trigger_rule"]]
        if row["remediation_mode"] != "notify" or len(row["steps"]) != len(b["diagnostics"]):
            sys.exit(f"{b['alert']}: DB row does not match YAML ({row['remediation_mode']}, {len(row['steps'])} steps)")
    print(f"registry: {len(rows)} enabled runbooks, all match YAML")


# ── (b) automation blocks ──────────────────────────────────────────────

def automation_block(book: dict) -> list[str]:
    alert = book["alert"]
    lines = [
        AUTO_BEGIN % alert,
        f"**Automation** — `observability/runbooks/{alert}.yml`, trigger `{book['trigger_rule']}`, "
        f"mode `{book['mode']}`. When this alert opens an incident, dhg-remediator runs the "
        "read-only diagnostics below once per incident state change and records each result as "
        "an action on the incident (Actions tab). Nothing is restarted, stopped, or changed.",
        "",
        "| # | Diagnostic | Command |",
        "|---|---|---|",
    ]
    for step in sorted(book["diagnostics"], key=lambda s: s["order"]):
        cmd = step["command"].replace("|", "\\|")
        lines.append(f"| {step['order']} | {step['description']} | `{cmd}` |")
    if book["severity"] == "warning":
        lines += ["", "Severity `warning`: the registry webhook opens no incident, so these diagnostics "
                  "run only if the severity is raised."]
    if book.get("notes"):
        lines += ["", f"Notes: {book['notes']}"]
    lines.append(AUTO_END)
    return lines


def upsert_block(lines: list[str], alert: str, block: list[str]) -> list[str]:
    heading = f"### {alert}"
    try:
        start = lines.index(heading)
    except ValueError:
        sys.exit(f"{DOCS_PAGE.name}: no section '{heading}' — every YAML runbook needs a human section")
    end = start + 1
    while end < len(lines) and not SECTION_END.match(lines[end]):
        end += 1
    section = lines[start:end]

    begin_marker = AUTO_BEGIN % alert
    if begin_marker in section:
        b = section.index(begin_marker)
        e = section.index(AUTO_END, b)
        section = section[:b] + block + section[e + 1:]
    else:
        while section and section[-1].strip() == "":
            section.pop()
        section += [""] + block + [""]
    return lines[:start] + section + lines[end:]


# ── (c) coverage table ─────────────────────────────────────────────────

def coverage_section(books: dict[str, dict], rules: list[tuple[str, str, str]]) -> list[str]:
    automated = sum(1 for a, _, _ in rules if a in books)
    lines = [
        COV_BEGIN,
        "## Automation coverage",
        "",
        f"{len(rules)} rules: **{automated} with automated diagnostics** "
        f"(`observability/runbooks/<alert>.yml`, read-only, run by dhg-remediator when the "
        f"incident opens) and **{len(rules) - automated} human-only** (the section on this page "
        "is the whole runbook). Only `critical` and `high` alerts open incidents, so the "
        "`warning` rows marked automated never actually reach the remediator; they are "
        "documented for the harness and for the day the severity changes. Generated by "
        "`observability/scripts/gen-runbooks.py`; edit the YAML, not this table.",
        "",
        "| Alert | Severity | Coverage | Trigger | Diagnostics |",
        "|---|---|---|---|---|",
    ]
    for alert, severity, _ in rules:
        anchor = f"[{alert}](#{alert.lower()})"
        if alert in books:
            b = books[alert]
            gate = " (warning: no incident)" if severity == "warning" else ""
            lines.append(f"| {anchor} | `{severity}` | automated diagnostics{gate} | `{b['trigger_rule']}` | {len(b['diagnostics'])} |")
        else:
            lines.append(f"| {anchor} | `{severity}` | human-only | — | — |")
    lines.append(COV_END)
    return lines


def upsert_coverage(lines: list[str], section: list[str]) -> list[str]:
    if COV_BEGIN in lines:
        b = lines.index(COV_BEGIN)
        e = lines.index(COV_END, b)
        return lines[:b] + section + lines[e + 1:]
    anchor = lines.index("## Infrastructure")
    return lines[:anchor] + section + ["", "---", ""] + lines[anchor:]


# ── main ───────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", default="http://10.0.0.251:8011")
    ap.add_argument("--no-seed", action="store_true", help="skip the registry seed")
    ap.add_argument("--check", action="store_true", help="exit 1 if the docs page would change")
    args = ap.parse_args()

    books = load_runbooks()
    rules = load_rules()
    rule_names = {a for a, _, _ in rules}
    unknown = sorted(set(books) - rule_names)
    if unknown:
        sys.exit(f"runbook YAML for alerts that do not exist in any rule file: {unknown}")

    if not args.no_seed and not args.check:
        seed_via_registry(args.registry, books)

    original = DOCS_PAGE.read_text()
    lines = original.split("\n")
    for alert in sorted(books):
        lines = upsert_block(lines, alert, automation_block(books[alert]))
    lines = upsert_coverage(lines, coverage_section(books, rules))
    rendered = "\n".join(lines)

    if args.check:
        if rendered != original:
            print(f"{DOCS_PAGE} is out of date; run gen-runbooks.py")
            return 1
        print("docs page up to date")
        return 0

    if rendered != original:
        DOCS_PAGE.write_text(rendered)
        print(f"docs: wrote {len(books)} automation blocks + coverage table to {DOCS_PAGE.relative_to(REPO)}")
    else:
        print("docs: no change")
    return 0


if __name__ == "__main__":
    sys.exit(main())
