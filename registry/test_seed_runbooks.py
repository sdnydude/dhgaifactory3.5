"""seed_runbooks loads observability/runbooks/*.yml into incident_runbooks
rows whose every step passes the remediator allowlist."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import seed_runbooks

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "services" / "remediator"))
from allowlist import check_command  # noqa: E402


@pytest.fixture(scope="module")
def rows():
    return seed_runbooks.load_runbooks(REPO / "observability" / "runbooks")


def test_loads_every_yaml(rows):
    assert len(rows) == 17
    assert len({r["trigger_rule"] for r in rows}) == 17


def test_rows_have_runbook_columns_only(rows):
    for row in rows:
        assert set(row) == {
            "trigger_rule", "title", "description", "severity",
            "remediation_mode", "container_allowlist", "steps", "enabled",
        }
        assert row["remediation_mode"] == "notify"
        assert row["severity"] in ("critical", "high", "warning")
        assert row["enabled"] is True


def test_steps_are_ordered_diagnostics_with_allowlisted_commands(rows):
    for row in rows:
        orders = [s["order"] for s in row["steps"]]
        assert orders == sorted(orders) and len(orders) == len(set(orders)), row["trigger_rule"]
        for step in row["steps"]:
            assert set(step) == {"order", "action", "command"}
            allowed, why = check_command(step["command"])
            assert allowed, f"{row['trigger_rule']} step {step['order']}: {why}"


def test_human_steps_are_not_seeded(rows):
    for row in rows:
        for step in row["steps"]:
            assert step["command"], "a step without a command would be a human step"


def test_rejects_unknown_mode(tmp_path):
    (tmp_path / "X.yml").write_text(
        "alert: X\ntrigger_rule: T99\nseverity: high\nmode: auto\ntitle: t\n"
        "diagnostics:\n  - {order: 1, description: d, command: docker ps}\n"
    )
    with pytest.raises(ValueError, match="mode"):
        seed_runbooks.load_runbooks(tmp_path)


def test_rejects_alert_file_name_mismatch(tmp_path):
    (tmp_path / "Y.yml").write_text(
        "alert: X\ntrigger_rule: T99\nseverity: high\nmode: notify\ntitle: t\n"
        "diagnostics:\n  - {order: 1, description: d, command: docker ps}\n"
    )
    with pytest.raises(ValueError, match="match the file name"):
        seed_runbooks.load_runbooks(tmp_path)


def test_rejects_duplicate_trigger(tmp_path):
    for name in ("A", "B"):
        (tmp_path / f"{name}.yml").write_text(
            f"alert: {name}\ntrigger_rule: T99\nseverity: high\nmode: notify\ntitle: t\n"
            "diagnostics:\n  - {order: 1, description: d, command: docker ps}\n"
        )
    with pytest.raises(ValueError, match="already used"):
        seed_runbooks.load_runbooks(tmp_path)


def test_seed_all_upserts_and_disables_rows_without_yaml(monkeypatch, rows):
    monkeypatch.setattr(seed_runbooks, "load_runbooks", lambda: rows[:2])
    db = MagicMock()
    existing = MagicMock(trigger_rule=rows[0]["trigger_rule"])
    stale = MagicMock(trigger_rule="T10", enabled=True)
    db.query.return_value.filter.return_value.first.side_effect = [existing, None]
    db.query.return_value.filter.return_value.all.return_value = [existing, stale]

    result = seed_runbooks.seed_all(db)

    assert result == {"created": 1, "updated": 1, "disabled": 1}
    assert stale.enabled is False
    assert existing.remediation_mode == "notify"
    db.add.assert_called_once()
    db.commit.assert_called_once()
