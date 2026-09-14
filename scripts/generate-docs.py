#!/usr/bin/env python3
"""
generate-docs.py — Generate the service inventory page from compose files and langgraph.json.

Reads docker-compose.yml, docker-compose.override.yml, the LangGraph compose
file and langgraph.json, merges same-named services the way docker compose
does, and renders docs-site/projects/dhg-ai-factory/service-inventory.md.
The committed page is the drift artifact CI checks.

Usage:
    python3 scripts/generate-docs.py              # Print the page to stdout
    python3 scripts/generate-docs.py --write      # Rewrite the committed page
    python3 scripts/generate-docs.py --check      # Exit 1 (with a diff) if the committed page is stale
"""

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MAIN_COMPOSE = ROOT / "docker-compose.yml"
OVERRIDE_COMPOSE = ROOT / "docker-compose.override.yml"
LANGGRAPH_COMPOSE = ROOT / "langgraph_workflows" / "dhg-agents-cloud" / "docker-compose.yml"
LANGGRAPH_JSON = ROOT / "langgraph_workflows" / "dhg-agents-cloud" / "langgraph.json"
INVENTORY_PAGE = ROOT / "docs-site" / "projects" / "dhg-ai-factory" / "service-inventory.md"


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def parse_host_port(port) -> str:
    """Host port of a compose port entry: '8011:8000', '0.0.0.0:8011:8000',
    '8011', or the long form {target: 8000, published: 8011}. Anything else
    (an unexpanded ${VAR}, a range) raises so drift is loud, not a garbage cell."""
    if isinstance(port, dict):
        published = port.get("published", port.get("target"))
        return _digits(str(published), port)
    parts = str(port).split(":")
    host = parts[1] if len(parts) == 3 else parts[0]
    return _digits(host, port)


def _digits(value: str, original) -> str:
    if not value.isdigit():
        raise ValueError(f"unsupported port mapping {original!r}: host port must be numeric")
    return value


def get_container_name(svc_name: str, svc_def: dict) -> str:
    return svc_def.get("container_name", svc_name)


def get_ports(svc_def: dict) -> list[str]:
    ports = svc_def.get("ports", [])
    return [parse_host_port(p) for p in ports]


def has_healthcheck(svc_def: dict) -> bool:
    return "healthcheck" in svc_def


def get_image_or_build(svc_def: dict) -> str:
    if "image" in svc_def:
        return svc_def["image"]
    build = svc_def.get("build", "")
    if isinstance(build, dict):
        return f"build:{build.get('context', '.')}"
    return f"build:{build}" if build else "build:."


def classify_service(svc_name: str, svc_def: dict, compose_file: str) -> str:
    """Classify a service into a category."""
    name = get_container_name(svc_name, svc_def)
    env = svc_def.get("environment", {}) or {}
    if isinstance(env, list):
        env = dict(item.split("=", 1) if "=" in item else (item, "") for item in env if isinstance(item, str))
    agent_type = env.get("AGENT_TYPE")

    if "langgraph" in compose_file.lower():
        return "langgraph"
    if agent_type == "master":
        return "legacy-orchestrator"
    if agent_type == "specialized":
        return "legacy-agent"
    if any(x in name for x in ["prometheus", "grafana", "loki", "tempo", "promtail",
                                 "alertmanager", "cadvisor", "node-exporter", "postgres-exporter"]):
        return "observability"
    if any(x in name for x in ["registry-db", "registry-api", "ollama", "session-logger",
                                 "logo-maker", "frontend", "vs-engine", "audio"]):
        return "infrastructure"
    if "web-ui" in name:
        return "legacy-ui"
    return "other"


def get_profiles(svc_def: dict) -> list[str]:
    profiles = svc_def.get("profiles", [])
    return [str(p) for p in profiles] if isinstance(profiles, list) else [str(profiles)]


def merge_service(base: dict, override: dict) -> dict:
    """Merge one service stanza onto another the way `docker compose` does for
    the keys this script reads: list-valued keys (ports, profiles, volumes, …)
    are unioned in order, mapping-valued keys (environment, labels, …) are
    merged, scalars are replaced."""
    out = dict(base)
    for key, value in override.items():
        current = out.get(key)
        if isinstance(current, list) and isinstance(value, list):
            out[key] = current + [v for v in value if v not in current]
        elif isinstance(current, dict) and isinstance(value, dict):
            out[key] = {**current, **value}
        else:
            out[key] = value
    return out


def collect_services() -> list[dict]:
    """Collect all services from all compose files.

    Same-named services are merged in file order (MAIN, OVERRIDE, LANGGRAPH)
    via merge_service, so an override merge stanza never produces a second
    row. The main compose file is required; the override and the LangGraph
    compose are optional.
    """
    if not MAIN_COMPOSE.exists():
        raise FileNotFoundError(f"main compose file not found: {MAIN_COMPOSE}")
    merged: dict[str, dict] = {}
    origin: dict[str, Path] = {}
    for compose_path in [MAIN_COMPOSE, OVERRIDE_COMPOSE, LANGGRAPH_COMPOSE]:
        if not compose_path.exists():
            continue
        data = load_yaml(compose_path)
        for svc_name, svc_def in data.get("services", {}).items():
            if not isinstance(svc_def, dict):
                continue
            if svc_name in merged:
                merged[svc_name] = merge_service(merged[svc_name], svc_def)
            else:
                merged[svc_name] = dict(svc_def)
                origin[svc_name] = compose_path
    services = []
    for svc_name, svc_def in merged.items():
        compose_path = origin[svc_name]
        services.append({
            "service": svc_name,
            "container": get_container_name(svc_name, svc_def),
            "ports": get_ports(svc_def),
            "healthcheck": has_healthcheck(svc_def),
            "profiles": get_profiles(svc_def),
            "category": classify_service(svc_name, svc_def, str(compose_path)),
            "compose": compose_path.name,
            "image": get_image_or_build(svc_def),
        })
    return services


def collect_langgraph_graphs() -> list[dict]:
    """Collect graphs from langgraph.json."""
    if not LANGGRAPH_JSON.exists():
        return []
    data = load_json(LANGGRAPH_JSON)
    graphs = data.get("graphs", {})
    result = []
    if isinstance(graphs, dict):
        for name, path_ref in graphs.items():
            file_path, var_name = path_ref.rsplit(":", 1) if ":" in path_ref else (path_ref, "graph")
            result.append({"name": name, "file": file_path, "export": var_name})
    return result


def _profile(s: dict) -> str:
    return ", ".join(s["profiles"]) if s["profiles"] else "—"


def _port_key(s: dict):
    return (int(s["ports"][0]) if s["ports"] and s["ports"][0].isdigit() else 99999, s["container"])


def _table(title: str, header: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return ""
    lines = [f"### {title}", "", "| " + " | ".join(header) + " |", "|" + "|".join("-" * (len(h) + 2) for h in header) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def _port(s: dict) -> str:
    return ", ".join(s["ports"]) if s["ports"] else "—"


def generate_infrastructure_table(services: list[dict]) -> str:
    rows = [[s["container"], _port(s), _profile(s), s["image"] + (" (healthcheck)" if s["healthcheck"] else "")]
            for s in sorted(services, key=_port_key) if s["category"] == "infrastructure"]
    return _table("Infrastructure Services", ["Service", "Port", "Profile", "Image"], rows)


def generate_observability_table(services: list[dict]) -> str:
    rows = [[s["container"], _port(s), _profile(s), "Yes" if s["healthcheck"] else "No"]
            for s in sorted(services, key=_port_key) if s["category"] == "observability"]
    return _table("Observability Stack", ["Service", "Port", "Profile", "Healthcheck"], rows)


def generate_other_table(services: list[dict]) -> str:
    rows = [[s["container"], _port(s), _profile(s), s["image"]]
            for s in sorted(services, key=_port_key) if s["category"] in ("other", "langgraph")]
    return _table("Other Services", ["Service", "Port", "Profile", "Image"], rows)


def generate_legacy_table(services: list[dict]) -> str:
    rows = [[s["container"], _port(s), _profile(s), s["category"]]
            for s in sorted(services, key=_port_key) if s["category"] in ("legacy-agent", "legacy-orchestrator", "legacy-ui")]
    return _table("Legacy Agent System (BEING DECOMMISSIONED)", ["Container", "Port", "Profile", "Type"], rows)


def generate_langgraph_table(graphs: list[dict]) -> str:
    agents = [g for g in graphs if "orchestrator" not in g["file"]]
    orchestrators = [g for g in graphs if "orchestrator" in g["file"]]
    lines = [f"### LangGraph Agent System ({len(graphs)} graphs, deprecated — migrating to Pydantic AI)", "",
             f"**{len(agents)} Individual Agent Graphs:**", "",
             "| Graph | File |", "|-------|------|"]
    lines += [f"| {g['name']} | {g['file']} |" for g in sorted(agents, key=lambda x: x["name"])]
    lines += ["", f"**{len(orchestrators)} Orchestrator Composition Graphs:**", "",
              "| Recipe | Export |", "|--------|--------|"]
    lines += [f"| {g['name']} | {g['export']} |" for g in sorted(orchestrators, key=lambda x: x["name"])]
    return "\n".join(lines)


def generate_port_map(services: list[dict]) -> str:
    entries = sorted({(int(p) if p.isdigit() else 99999, p, s["container"]) for s in services for p in s["ports"]})
    return _table("Port Map", ["Port", "Service"], [[p, c] for _, p, c in entries])


def generate_healthcheck_summary(services: list[dict]) -> str:
    with_hc = sorted(s["container"] for s in services if s["healthcheck"])
    without_hc = sorted(s["container"] for s in services if not s["healthcheck"])
    return "\n".join(["### Healthcheck Coverage", "",
                       f"**With healthcheck ({len(with_hc)}):** {', '.join(with_hc)}", "",
                       f"**Without healthcheck ({len(without_hc)}):** {', '.join(without_hc)}"])


def render_inventory() -> str:
    """Render the full inventory page. Deterministic: no timestamps, sorted rows."""
    services = collect_services()
    graphs = collect_langgraph_graphs()
    sections = [
        "---", "title: Service Inventory", "sidebar_position: 5", "---", "",
        "# Service Inventory", "",
        "Generated by `scripts/generate-docs.py` from `docker-compose.yml`, `docker-compose.override.yml`, "
        "the LangGraph compose file and `langgraph.json` — do not edit by hand. Regenerate with "
        "`python3 scripts/generate-docs.py --write`; CI runs `--check` and fails when this page no longer matches the compose files.",
        "",
        f"Total services: {len(services)} | LangGraph graphs: {len(graphs)}", "",
        generate_infrastructure_table(services), "",
        generate_observability_table(services), "",
        generate_other_table(services), "",
        generate_legacy_table(services), "",
        generate_langgraph_table(graphs), "",
        generate_port_map(services), "",
        generate_healthcheck_summary(services), "",
    ]
    return "\n".join(section for section in sections if section is not None and section != "") + "\n"


def write_inventory() -> Path:
    INVENTORY_PAGE.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY_PAGE.write_text(render_inventory())
    return INVENTORY_PAGE


def check_inventory() -> list[str]:
    """Unified-diff lines between the committed page and a fresh render; [] when in sync."""
    import difflib
    current = INVENTORY_PAGE.read_text().splitlines() if INVENTORY_PAGE.exists() else []
    fresh = render_inventory().splitlines()
    return list(difflib.unified_diff(current, fresh, fromfile=str(INVENTORY_PAGE), tofile="generated", lineterm=""))


def main(argv: list[str] | None = None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Generate or check the service inventory page.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="rewrite the committed page")
    mode.add_argument("--check", action="store_true", help="exit 1 with a diff if the committed page is stale")
    args = parser.parse_args(argv)   # unknown flags -> exit 2, never a silent pass
    if args.check:
        diff = check_inventory()
        if diff:
            print(f"Documentation drift detected in {INVENTORY_PAGE}:")
            print("\n".join(diff))
            print("\nRun 'python3 scripts/generate-docs.py --write' and commit the page.")
            sys.exit(1)
        print("Service inventory is in sync with compose files.")
        sys.exit(0)
    if args.write:
        print(f"wrote {write_inventory()}")
        return
    print(render_inventory(), end="")


if __name__ == "__main__":
    main()
