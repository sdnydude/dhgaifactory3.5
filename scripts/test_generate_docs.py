"""Tests for scripts/generate-docs.py (service inventory generator).

The script has a hyphenated filename, so it is loaded via importlib. Compose
inputs are written to a temp directory and the module's path constants are
pointed at them, so no real compose file is read.
"""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "generate-docs.py"


def load_module():
    spec = importlib.util.spec_from_file_location("generate_docs", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def compose_tree(tmp_path):
    """Base + override + langgraph compose files mimicking the real layout."""
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n"
        "  grafana:\n"
        "    image: grafana/grafana:10.2.0\n"
        "    container_name: dhg-grafana\n"
        "    ports: ['3001:3000']\n"
        "    healthcheck: {test: ['CMD', 'true']}\n"
        "  tempo:\n"
        "    image: grafana/tempo:2.3.0\n"
        "    container_name: dhg-tempo\n"
        "    profiles: ['retired']\n"
        "  registry-api:\n"
        "    build: ./registry\n"
        "    container_name: dhg-registry-api\n"
        "    ports: ['8011:8000']\n"
    )
    # Merge stanzas: same service names, no container_name, extra keys only.
    (tmp_path / "docker-compose.override.yml").write_text(
        "services:\n"
        "  grafana:\n"
        "    environment: {GF_X: '1'}\n"
        "  registry-api:\n"
        "    environment: {X: '1'}\n"
    )
    lg = tmp_path / "langgraph_workflows" / "dhg-agents-cloud"
    lg.mkdir(parents=True)
    (lg / "docker-compose.yml").write_text(
        "services:\n"
        "  langgraph-api:\n"
        "    image: langgraph:1\n"
        "    ports: ['2026:8000']\n"
    )
    (lg / "langgraph.json").write_text('{"graphs": {}}')
    return tmp_path


def point_at(mod, root):
    mod.ROOT = root
    mod.MAIN_COMPOSE = root / "docker-compose.yml"
    mod.OVERRIDE_COMPOSE = root / "docker-compose.override.yml"
    mod.LANGGRAPH_COMPOSE = root / "langgraph_workflows" / "dhg-agents-cloud" / "docker-compose.yml"
    mod.LANGGRAPH_JSON = root / "langgraph_workflows" / "dhg-agents-cloud" / "langgraph.json"


def test_collect_services_merges_same_named_services_across_compose_files(compose_tree):
    mod = load_module()
    point_at(mod, compose_tree)
    rows = {s["service"]: s for s in mod.collect_services()}
    assert sorted(rows) == ["grafana", "langgraph-api", "registry-api", "tempo"]
    assert rows["grafana"]["container"] == "dhg-grafana"
    assert rows["grafana"]["ports"] == ["3001"]
    assert rows["grafana"]["healthcheck"] is True
    assert rows["registry-api"]["container"] == "dhg-registry-api"
    assert rows["tempo"]["profiles"] == ["retired"]
    assert rows["grafana"]["profiles"] == []


def test_write_then_check_is_in_sync_and_page_has_profile_column(compose_tree):
    mod = load_module()
    point_at(mod, compose_tree)
    page = compose_tree / "docs-site" / "service-inventory.md"
    mod.INVENTORY_PAGE = page
    mod.write_inventory()
    text = page.read_text()
    assert text.startswith("---\ntitle:")
    assert "sidebar_position:" in text
    assert "do not edit" in text
    assert "| Profile |" in text
    assert "| dhg-tempo |" in text and "retired" in text
    assert mod.check_inventory() == []


def test_check_reports_a_diff_when_the_committed_page_is_stale(compose_tree):
    mod = load_module()
    point_at(mod, compose_tree)
    mod.INVENTORY_PAGE = compose_tree / "docs-site" / "service-inventory.md"
    mod.write_inventory()
    mod.INVENTORY_PAGE.write_text(mod.INVENTORY_PAGE.read_text().replace("| dhg-tempo |", "| dhg-tempo-renamed |"))
    diff = mod.check_inventory()
    assert any(line.startswith("-| dhg-tempo-renamed |") for line in diff)
    assert any(line.startswith("+| dhg-tempo |") for line in diff)


def test_two_writes_are_byte_identical(compose_tree):
    mod = load_module()
    point_at(mod, compose_tree)
    mod.INVENTORY_PAGE = compose_tree / "docs-site" / "service-inventory.md"
    mod.write_inventory()
    first = mod.INVENTORY_PAGE.read_bytes()
    mod.write_inventory()
    assert mod.INVENTORY_PAGE.read_bytes() == first
    assert b"20" not in first.split(b"# Service Inventory")[0].split(b"---")[1]  # no dates in front matter
