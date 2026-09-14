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
    assert first.startswith(b"---\ntitle: Service Inventory\nsidebar_position: 5\n---\n")  # fixed front matter, no dates


def test_merge_unions_list_keys_and_merges_environment(compose_tree):
    # An override stanza that adds a port and a profile must not drop the base ones.
    (compose_tree / "docker-compose.override.yml").write_text(
        "services:\n"
        "  grafana:\n"
        "    ports: ['3002:3000']\n"
        "    profiles: ['ops']\n"
        "    environment: {GF_Y: '2'}\n"
        "  tempo:\n"
        "    profiles: ['retired']\n"
    )
    mod = load_module()
    point_at(mod, compose_tree)
    rows = {s["service"]: s for s in mod.collect_services()}
    assert rows["grafana"]["ports"] == ["3001", "3002"]
    assert rows["grafana"]["profiles"] == ["ops"]
    assert rows["tempo"]["profiles"] == ["retired"]


def test_missing_main_compose_is_an_error(compose_tree):
    (compose_tree / "docker-compose.yml").unlink()
    mod = load_module()
    point_at(mod, compose_tree)
    with pytest.raises(FileNotFoundError):
        mod.collect_services()


def test_long_form_and_bad_ports_fail_loudly():
    mod = load_module()
    assert mod.parse_host_port({"target": 8000, "published": 8011}) == "8011"
    assert mod.parse_host_port("0.0.0.0:8011:8000") == "8011"
    assert mod.parse_host_port("8011:8000") == "8011"
    with pytest.raises(ValueError):
        mod.parse_host_port("${PORT:-8011}:8000")


def test_unknown_flag_is_rejected(compose_tree, capsys):
    mod = load_module()
    point_at(mod, compose_tree)
    mod.INVENTORY_PAGE = compose_tree / "docs-site" / "service-inventory.md"
    with pytest.raises(SystemExit) as e:
        mod.main(["--chekc"])
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        mod.main(["--check", "--write"])
    assert e.value.code == 2


def test_check_exit_codes(compose_tree, capsys):
    mod = load_module()
    point_at(mod, compose_tree)
    mod.INVENTORY_PAGE = compose_tree / "docs-site" / "service-inventory.md"
    with pytest.raises(SystemExit) as e:
        mod.main(["--check"])          # page absent -> stale
    assert e.value.code == 1
    mod.main(["--write"])
    with pytest.raises(SystemExit) as e:
        mod.main(["--check"])
    assert e.value.code == 0
    text = mod.INVENTORY_PAGE.read_text()
    assert text.startswith("---\ntitle: Service Inventory\nsidebar_position: 5\n---\n")
    assert "| Service | Port | Profile | Image |" in text   # infrastructure header names the column truthfully
    assert "BEING DECOMMISSIONED" not in text               # empty legacy section is skipped
