"""ALERT_TRIGGER_MAP is checked against the rule files and the runbook YAML:
every key is a live alertname, every critical|high alert has an explicit
automated-or-human-only decision, and every trigger points at a runbook file
whose trigger_rule agrees."""
from pathlib import Path

import pytest
import yaml

from api import ALERT_TRIGGER_MAP
from incident_schemas import IncidentCategory

REPO = Path(__file__).resolve().parent.parent
RULE_FILES = (
    [REPO / "observability" / "prometheus" / "alerts.yml"]
    + sorted((REPO / "observability" / "prometheus" / "rules.d").glob("*.yml"))
    + [REPO / "observability" / "loki" / "rules" / "fake" / "alerts.yml"]
)
RUNBOOKS_DIR = REPO / "observability" / "runbooks"


def load_rules() -> dict[str, str]:
    """alertname -> severity across every rule file."""
    rules: dict[str, str] = {}
    for path in RULE_FILES:
        with open(path) as fh:
            doc = yaml.safe_load(fh)
        for group in doc["groups"]:
            for rule in group["rules"]:
                rules[rule["alert"]] = rule["labels"]["severity"]
    return rules


def load_runbooks() -> dict[str, dict]:
    return {p.stem: yaml.safe_load(open(p)) for p in sorted(RUNBOOKS_DIR.glob("*.yml"))}


RULES = load_rules()
RUNBOOKS = load_runbooks()


def test_rule_files_parsed():
    assert len(RULES) == 45
    assert len(RUNBOOKS) == 17


def test_every_key_is_a_live_alertname():
    unknown = sorted(set(ALERT_TRIGGER_MAP) - set(RULES))
    assert unknown == [], f"not in any rule file: {unknown}"


def test_zombie_processes_high_is_gone():
    assert "ZombieProcessesHigh" not in ALERT_TRIGGER_MAP


def test_every_incident_creating_alert_has_an_explicit_decision():
    """critical|high is what the webhook turns into incidents."""
    gated = sorted(a for a, sev in RULES.items() if sev in ("critical", "high"))
    missing = [a for a in gated if a not in ALERT_TRIGGER_MAP]
    assert missing == [], f"critical/high alerts with no map entry: {missing}"


def test_entry_shape():
    for alert, entry in ALERT_TRIGGER_MAP.items():
        assert set(entry) <= {"trigger", "category", "human_only"}, alert
        assert entry["category"] in IncidentCategory.__args__, alert
        if entry["trigger"] is None:
            assert entry.get("human_only") is True, f"{alert}: trigger None must be marked human_only"
        else:
            assert "human_only" not in entry, f"{alert}: a runbook trigger cannot also be human_only"


def test_every_trigger_has_a_runbook_file_with_the_same_alert_and_trigger():
    for alert, entry in ALERT_TRIGGER_MAP.items():
        if entry["trigger"] is None:
            assert alert not in RUNBOOKS, f"{alert} is human-only but has a runbook YAML"
            continue
        assert alert in RUNBOOKS, f"{alert} -> {entry['trigger']} has no observability/runbooks/{alert}.yml"
        assert RUNBOOKS[alert]["trigger_rule"] == entry["trigger"], alert


def test_every_runbook_file_is_mapped():
    unmapped = sorted(set(RUNBOOKS) - {a for a, e in ALERT_TRIGGER_MAP.items() if e["trigger"]})
    assert unmapped == [], f"runbook YAML with no ALERT_TRIGGER_MAP entry: {unmapped}"


def test_triggers_are_unique():
    triggers = [e["trigger"] for e in ALERT_TRIGGER_MAP.values() if e["trigger"]]
    assert len(triggers) == len(set(triggers))


def test_runbook_severity_matches_rule_file():
    for alert, rb in RUNBOOKS.items():
        assert rb["severity"] == RULES[alert], f"{alert}: YAML {rb['severity']} vs rule {RULES[alert]}"


def test_secret_leak_is_human_only():
    assert ALERT_TRIGGER_MAP["SecretLeakDetected"] == {
        "trigger": None, "category": "security", "human_only": True,
    }


@pytest.mark.parametrize("alert", ["ContainerHighMemory", "DataDiskHigh"])
def test_warning_runbooks_are_documented_as_never_creating_incidents(alert):
    """The severity gate is kept: these YAMLs exist for the docs and the
    harness, not because the remediator will ever see them."""
    assert RULES[alert] == "warning"
    assert ALERT_TRIGGER_MAP[alert]["trigger"]
