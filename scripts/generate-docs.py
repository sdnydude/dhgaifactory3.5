#!/usr/bin/env python3
"""
generate-docs.py — Generate documentation tables from compose files and langgraph.json.

Reads docker-compose.yml, docker-compose.override.yml, LangGraph compose,
and langgraph.json to produce markdown tables that can be diffed against
CLAUDE.md. Run in CI to detect documentation drift.

Usage:
    python3 scripts/generate-docs.py              # Print tables to stdout
    python3 scripts/generate-docs.py --check      # Exit 1 if CLAUDE.md is stale
"""

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MAIN_COMPOSE = ROOT / "docker-compose.yml"
OVERRIDE_COMPOSE = ROOT / "docker-compose.override.yml"
LANGGRAPH_COMPOSE = ROOT / "langgraph_workflows" / "dhg-agents-cloud" / "docker-compose.yml"
LANGGRAPH_JSON = ROOT / "langgraph_workflows" / "dhg-agents-cloud" / "langgraph.json"
CLAUDE_MD = ROOT / "CLAUDE.md"


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def parse_host_port(port_str: str) -> str:
    """Extract host port from a port mapping like '8011:8000' or '0.0.0.0:8011:8000'."""
    parts = str(port_str).split(":")
    if len(parts) == 3:
        return parts[1]
    if len(parts) == 2:
        return parts[0]
    return str(port_str)


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
    env_vars = svc_def.get("environment", [])
    agent_type = None
    for var in env_vars:
        if isinstance(var, str) and var.startswith("AGENT_TYPE="):
            agent_type = var.split("=", 1)[1]

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


def collect_services() -> list[dict]:
    """Collect all services from all compose files."""
    services = []
    for compose_path in [MAIN_COMPOSE, OVERRIDE_COMPOSE, LANGGRAPH_COMPOSE]:
        if not compose_path.exists():
            continue
        data = load_yaml(compose_path)
        for svc_name, svc_def in data.get("services", {}).items():
            if not isinstance(svc_def, dict):
                continue
            container = get_container_name(svc_name, svc_def)
            ports = get_ports(svc_def)
            category = classify_service(svc_name, svc_def, str(compose_path))
            services.append({
                "service": svc_name,
                "container": container,
                "ports": ports,
                "healthcheck": has_healthcheck(svc_def),
                "category": category,
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


def generate_infrastructure_table(services: list[dict]) -> str:
    lines = ["### Infrastructure Services", "",
             "| Service | Port | Purpose |",
             "|---------|------|---------|"]
    for s in sorted(services, key=lambda x: (x["ports"][0] if x["ports"] else "99999")):
        if s["category"] != "infrastructure":
            continue
        port = ", ".join(s["ports"]) if s["ports"] else "—"
        hc = " (healthcheck)" if s["healthcheck"] else ""
        lines.append(f"| {s['container']} | {port} | {s['image']}{hc} |")
    return "\n".join(lines)


def generate_legacy_table(services: list[dict]) -> str:
    lines = ["### Legacy Agent System (BEING DECOMMISSIONED)", "",
             "| Container | Port | Type |",
             "|-----------|------|------|"]
    for s in sorted(services, key=lambda x: (x["ports"][0] if x["ports"] else "99999")):
        if s["category"] not in ("legacy-agent", "legacy-orchestrator", "legacy-ui"):
            continue
        port = ", ".join(s["ports"]) if s["ports"] else "—"
        lines.append(f"| {s['container']} | {port} | {s['category']} |")
    return "\n".join(lines)


def generate_observability_table(services: list[dict]) -> str:
    lines = ["### Observability Stack", "",
             "| Service | Port | Healthcheck |",
             "|---------|------|-------------|"]
    for s in sorted(services, key=lambda x: (x["ports"][0] if x["ports"] else "99999")):
        if s["category"] != "observability":
            continue
        port = ", ".join(s["ports"]) if s["ports"] else "—"
        hc = "Yes" if s["healthcheck"] else "No"
        lines.append(f"| {s['container']} | {port} | {hc} |")
    return "\n".join(lines)


def generate_langgraph_table(graphs: list[dict]) -> str:
    agents = [g for g in graphs if "orchestrator" not in g["file"]]
    orchestrators = [g for g in graphs if "orchestrator" in g["file"]]

    lines = [f"### LangGraph Agent System ({len(graphs)} graphs)", "",
             f"**{len(agents)} Individual Agent Graphs:**", "",
             "| Graph | File |",
             "|-------|------|"]
    for g in sorted(agents, key=lambda x: x["name"]):
        lines.append(f"| {g['name']} | {g['file']} |")

    lines.extend(["",
                   f"**{len(orchestrators)} Orchestrator Composition Graphs:**", "",
                   "| Recipe | Export |",
                   "|--------|--------|"])
    for g in sorted(orchestrators, key=lambda x: x["name"]):
        lines.append(f"| {g['name']} | {g['export']} |")

    return "\n".join(lines)


def generate_port_map(services: list[dict]) -> str:
    lines = ["### Port Map", "",
             "| Port | Service |",
             "|------|---------|"]
    port_entries = []
    for s in services:
        for p in s["ports"]:
            port_entries.append((int(p) if p.isdigit() else 99999, p, s["container"]))
    for _, port, container in sorted(set(port_entries)):
        lines.append(f"| {port} | {container} |")
    return "\n".join(lines)


def generate_healthcheck_summary(services: list[dict]) -> str:
    with_hc = [s for s in services if s["healthcheck"]]
    without_hc = [s for s in services if not s["healthcheck"]]
    lines = ["### Healthcheck Coverage", "",
             f"**With healthcheck ({len(with_hc)}):** {', '.join(s['container'] for s in sorted(with_hc, key=lambda x: x['container']))}",
             "",
             f"**Without healthcheck ({len(without_hc)}):** {', '.join(s['container'] for s in sorted(without_hc, key=lambda x: x['container']))}"]
    return "\n".join(lines)


def generate_all() -> str:
    services = collect_services()
    graphs = collect_langgraph_graphs()

    sections = [
        "# DHG AI Factory — Generated Documentation",
        f"Auto-generated from compose files and langgraph.json.",
        f"Total services: {len(services)} | LangGraph graphs: {len(graphs)}",
        "",
        generate_langgraph_table(graphs),
        "",
        generate_infrastructure_table(services),
        "",
        generate_legacy_table(services),
        "",
        generate_observability_table(services),
        "",
        generate_port_map(services),
        "",
        generate_healthcheck_summary(services),
    ]
    return "\n".join(sections)


def check_claude_md(generated: str) -> list[str]:
    """Check if CLAUDE.md contains key facts from the generated docs."""
    if not CLAUDE_MD.exists():
        return ["CLAUDE.md not found"]

    claude_text = CLAUDE_MD.read_text()
    drift = []

    services = collect_services()
    graphs = collect_langgraph_graphs()

    # Check graph count
    graph_match = re.search(r"(\d+) graphs? registered", claude_text)
    if graph_match:
        documented = int(graph_match.group(1))
        if documented != len(graphs):
            drift.append(f"Graph count: CLAUDE.md says {documented}, actual is {len(graphs)}")

    # Check each infrastructure service is mentioned
    for s in services:
        if s["category"] == "infrastructure" and s["container"] not in claude_text:
            drift.append(f"Missing infrastructure service: {s['container']}")

    # Check each observability service is mentioned
    for s in services:
        if s["category"] == "observability" and s["container"] not in claude_text:
            drift.append(f"Missing observability service: {s['container']}")

    # Check port accuracy for key services
    for s in services:
        if s["category"] in ("infrastructure", "observability") and s["ports"]:
            for port in s["ports"]:
                pattern = rf"{re.escape(s['container'])}.*{re.escape(port)}|{re.escape(port)}.*{re.escape(s['container'])}"
                if not re.search(pattern, claude_text):
                    # Check if at least the port is mentioned near the service name
                    container_idx = claude_text.find(s["container"])
                    if container_idx >= 0:
                        nearby = claude_text[max(0, container_idx - 100):container_idx + 200]
                        if port not in nearby:
                            drift.append(f"Port mismatch: {s['container']} should be on :{port}")

    return drift


def main():
    check_mode = "--check" in sys.argv

    generated = generate_all()

    if check_mode:
        drift = check_claude_md(generated)
        if drift:
            print("Documentation drift detected:")
            for d in drift:
                print(f"  - {d}")
            print(f"\nRun 'python3 scripts/generate-docs.py' to see current state.")
            sys.exit(1)
        else:
            print("Documentation is in sync with compose files.")
            sys.exit(0)
    else:
        print(generated)


if __name__ == "__main__":
    main()
